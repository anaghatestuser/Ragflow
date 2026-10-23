# Copyright (c) Lineaje, Inc. All rights reserved.
# Lineaje UnifAI guardrail  version=2.0.0-alpha
def _lineaje_load_gr_client():
    """Lineaje-added: load gr_stub_client.py without a pip dependency (missing / broken: a pass-through client)."""
    import sys as _s, importlib.util as _ilu
    from pathlib import Path as _P
    n = "_lineaje_gr_stub_client"
    if n in _s.modules: return _s.modules[n]
    try:
        h = _P(__file__).resolve().parent
        _cand = next((d / "gr_stub_client.py" for d in [h, *h.parents][:8] if (d / "gr_stub_client.py").is_file()), h / "gr_stub_client.py")
        _spec = _ilu.spec_from_file_location(n, _cand)
        _s.modules[n] = _m = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_m); return _m
    except Exception:
        _s.modules.pop(n, None)
        return type('_lineaje_gr_unavailable', (), {'STUB_API': 999999, 'GuardrailUnavailableError': type('GuardrailUnavailableError', (PermissionError,), {}), 'SiteDescriptor': staticmethod(lambda *a, **k: None), 'new_interaction_id': staticmethod(lambda *a, **k: None), 'enforce': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_request': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_reply': staticmethod(lambda _s, _p, *a, **k: _p)})

#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

# from beartype import BeartypeConf
# from beartype.claw import beartype_all  # <-- you didn't sign up for this
# beartype_all(conf=BeartypeConf(violation_type=UserWarning))    # <-- emit warnings from all code


import asyncio
import copy
import faulthandler
import logging
import os
import signal
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from typing import Any

from flask import json

from api.db.services.connector_service import ConnectorService, SyncLogsService
from api.db.services.knowledgebase_service import KnowledgebaseService
from common import settings
from common.config_utils import show_configs
from common.data_source import BlobStorageConnector, NotionConnector, DiscordConnector, GoogleDriveConnector, MoodleConnector, JiraConnector, DropboxConnector, WebDAVConnector
from common.constants import FileSource, TaskStatus
from common.data_source.config import INDEX_BATCH_SIZE
from common.data_source.confluence_connector import ConfluenceConnector
from common.data_source.gmail_connector import GmailConnector
from common.data_source.box_connector import BoxConnector
from common.data_source.interfaces import CheckpointOutputWrapper
from common.log_utils import init_root_logger
from common.signal_utils import start_tracemalloc_and_snapshot, stop_tracemalloc
from common.versions import get_ragflow_version
from box_sdk_gen import BoxOAuth, OAuthConfig, AccessToken

MAX_CONCURRENT_TASKS = int(os.environ.get("MAX_CONCURRENT_TASKS", "5"))
task_limiter = asyncio.Semaphore(MAX_CONCURRENT_TASKS)


class SyncBase:
    SOURCE_NAME: str = None

    def __init__(self, conf: dict) -> None:
        self.conf = conf

    async def __call__(self, task: dict):
        SyncLogsService.start(task["id"], task["connector_id"])

        async with task_limiter:
            try:
                await asyncio.wait_for(self._run_task_logic(task), timeout=task["timeout_secs"])

            except asyncio.TimeoutError:
                msg = f"Task timeout after {task['timeout_secs']} seconds"
                SyncLogsService.update_by_id(task["id"], {"status": TaskStatus.FAIL, "error_msg": msg})
                return

            except Exception as ex:
                msg = "\n".join([
                    "".join(traceback.format_exception_only(None, ex)).strip(),
                    "".join(traceback.format_exception(None, ex, ex.__traceback__)).strip(),
                ])
                SyncLogsService.update_by_id(task["id"], {
                    "status": TaskStatus.FAIL,
                    "full_exception_trace": msg,
                    "error_msg": str(ex)
                })
                return

        SyncLogsService.schedule(task["connector_id"], task["kb_id"], task["poll_range_start"])

    async def _run_task_logic(self, task: dict):
        document_batch_generator = await self._generate(task)

        doc_num = 0
        failed_docs = 0
        next_update = datetime(1970, 1, 1, tzinfo=timezone.utc)

        if task["poll_range_start"]:
            next_update = task["poll_range_start"]

        for document_batch in document_batch_generator: 
            if not document_batch:
                continue

            min_update = min(doc.doc_updated_at for doc in document_batch)
            max_update = max(doc.doc_updated_at for doc in document_batch)
            next_update = max(next_update, max_update)

            docs = []
            for doc in document_batch:
                d = {
                    "id": doc.id,
                    "connector_id": task["connector_id"],
                    "source": self.SOURCE_NAME,
                    "semantic_identifier": doc.semantic_identifier,
                    "extension": doc.extension,
                    "size_bytes": doc.size_bytes,
                    "doc_updated_at": doc.doc_updated_at,
                    "blob": doc.blob,
                }
                if doc.metadata:
                    d["metadata"] = doc.metadata
                docs.append(d)

            try:
                e, kb = KnowledgebaseService.get_by_id(task["kb_id"])
                err, dids = SyncLogsService.duplicate_and_parse(
                    kb, docs, task["tenant_id"],
                    f"{self.SOURCE_NAME}/{task['connector_id']}",
                    task["auto_parse"]
                )
                SyncLogsService.increase_docs(
                    task["id"], min_update, max_update,
                    len(docs), "\n".join(err), len(err)
                )

                doc_num += len(docs)

            except Exception as batch_ex:
                msg = str(batch_ex)
                code = getattr(batch_ex, "args", [None])[0]

                if code == 1267 or "collation" in msg.lower():
                    _lineaje_payload = f"Skipping {len(docs)} document(s) due to collation conflict"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in SyncBase._run_task_logic).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:68d5e99161e7ac636ef13f1b7967d23495e2f14f3e71bd7b6b2de5533da91fec'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:68d5e99161e7ac636ef13f1b7967d23495e2f14f3e71bd7b6b2de5533da91fec', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 142, 'function': 'SyncBase._run_task_logic'}, 'file': 'rag/svr/sync_data_source.py', 'line': 142, 'function': '_run_task_logic', 'agent_name': 'SyncBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.warning(_lineaje_payload)
                else:
                    _lineaje_payload = f"Error processing batch: {msg}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in SyncBase._run_task_logic).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:1fb0e9b69fa75f96f7c05fa5d64ed3921c10b4731aa19c3483c328c83afd1530'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1fb0e9b69fa75f96f7c05fa5d64ed3921c10b4731aa19c3483c328c83afd1530', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 144, 'function': 'SyncBase._run_task_logic'}, 'file': 'rag/svr/sync_data_source.py', 'line': 144, 'function': '_run_task_logic', 'agent_name': 'SyncBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.error(_lineaje_payload)

                failed_docs += len(docs)
                continue

        prefix = self._get_source_prefix()
        if failed_docs > 0:
            _lineaje_payload = f"{prefix}{doc_num} docs synchronized till {next_update} ({failed_docs} skipped)"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in SyncBase._run_task_logic).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:726a4524a1e5065a7b2784af6a3ebc65fc6c4137915dcfb92ff0074a325c558e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:726a4524a1e5065a7b2784af6a3ebc65fc6c4137915dcfb92ff0074a325c558e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 151, 'function': 'SyncBase._run_task_logic'}, 'file': 'rag/svr/sync_data_source.py', 'line': 151, 'function': '_run_task_logic', 'agent_name': 'SyncBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
        else:
            _lineaje_payload = f"{prefix}{doc_num} docs synchronized till {next_update}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in SyncBase._run_task_logic).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d57e775840008b6a5a4c31e3b866e9a4532106730144eff5af50c9947f1202a6'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d57e775840008b6a5a4c31e3b866e9a4532106730144eff5af50c9947f1202a6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 153, 'function': 'SyncBase._run_task_logic'}, 'file': 'rag/svr/sync_data_source.py', 'line': 153, 'function': '_run_task_logic', 'agent_name': 'SyncBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)

        SyncLogsService.done(task["id"], task["connector_id"])
        task["poll_range_start"] = next_update

    async def _generate(self, task: dict):
        raise NotImplementedError

    def _get_source_prefix(self):
        return ""

class _BlobLikeBase(SyncBase):
    DEFAULT_BUCKET_TYPE: str = "s3"

    async def _generate(self, task: dict):
        bucket_type = self.conf.get("bucket_type", self.DEFAULT_BUCKET_TYPE)

        self.connector = BlobStorageConnector(
            bucket_type=bucket_type,
            bucket_name=self.conf["bucket_name"],
            prefix=self.conf.get("prefix", ""),
        )
        self.connector.load_credentials(self.conf["credentials"])

        document_batch_generator = (
            self.connector.load_from_state()
            if task["reindex"] == "1" or not task["poll_range_start"]
            else self.connector.poll_source(
                task["poll_range_start"].timestamp(),
                datetime.now(timezone.utc).timestamp(),
            )
        )

        begin_info = (
            "totally"
            if task["reindex"] == "1" or not task["poll_range_start"]
            else "from {}".format(task["poll_range_start"])
        )

        _lineaje_payload = ("Connect to {}: {}(prefix/{}) {}".format(
                bucket_type,
                self.conf["bucket_name"],
                self.conf.get("prefix", ""),
                begin_info,
            ))
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _BlobLikeBase._generate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ef11e660b20224de1f0f67855a922db1e4f4ef3833ea1108a5c16ce12403237d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ef11e660b20224de1f0f67855a922db1e4f4ef3833ea1108a5c16ce12403237d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 192, 'function': '_BlobLikeBase._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 192, 'function': '_generate', 'agent_name': '_BlobLikeBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(
            _lineaje_payload
        )
        # LINEAJE: runtime guardrail checks `document_batch_generator` as it flows from the agent to the user interface, before it leaves the application (in _BlobLikeBase._generate).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `document_batch_generator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:bbe2b6c47261d12760d49ee2abc18e9d4f8bb4215f8ee89ede06f46c774b6c75'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bbe2b6c47261d12760d49ee2abc18e9d4f8bb4215f8ee89ede06f46c774b6c75', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 200, 'function': '_BlobLikeBase._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 200, 'function': '_generate', 'agent_name': '_BlobLikeBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            document_batch_generator = _gr_client.enforce(_gr_site, document_batch_generator, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return document_batch_generator

class S3(_BlobLikeBase):
    SOURCE_NAME: str = FileSource.S3
    DEFAULT_BUCKET_TYPE: str = "s3"

class R2(_BlobLikeBase):
    SOURCE_NAME: str = FileSource.R2
    DEFAULT_BUCKET_TYPE: str = "r2"

class OCI_STORAGE(_BlobLikeBase):
    SOURCE_NAME: str = FileSource.OCI_STORAGE
    DEFAULT_BUCKET_TYPE: str = "oci_storage"

class GOOGLE_CLOUD_STORAGE(_BlobLikeBase):
    SOURCE_NAME: str = FileSource.GOOGLE_CLOUD_STORAGE
    DEFAULT_BUCKET_TYPE: str = "google_cloud_storage"

class Confluence(SyncBase):
    SOURCE_NAME: str = FileSource.CONFLUENCE

    async def _generate(self, task: dict):
        from common.data_source.config import DocumentSource
        from common.data_source.interfaces import StaticCredentialsProvider

        index_mode = (self.conf.get("index_mode") or "everything").lower()
        if index_mode not in {"everything", "space", "page"}:
            index_mode = "everything"

        space = ""
        page_id = ""

        index_recursively = False
        if index_mode == "space":
            space = (self.conf.get("space") or "").strip()
            if not space:
                raise ValueError("Space Key is required when indexing a specific Confluence space.")
        elif index_mode == "page":
            page_id = (self.conf.get("page_id") or "").strip()
            if not page_id:
                raise ValueError("Page ID is required when indexing a specific Confluence page.")
            index_recursively = bool(self.conf.get("index_recursively", False))

        self.connector = ConfluenceConnector(
            wiki_base=self.conf["wiki_base"],
            is_cloud=self.conf.get("is_cloud", True),
            space=space,
            page_id=page_id,
            index_recursively=index_recursively,
        )

        credentials_provider = StaticCredentialsProvider(tenant_id=task["tenant_id"], connector_name=DocumentSource.CONFLUENCE, credential_json=self.conf["credentials"])
        self.connector.set_credentials_provider(credentials_provider)

        # Determine the time range for synchronization based on reindex or poll_range_start
        if task["reindex"] == "1" or not task["poll_range_start"]:
            start_time = 0.0
            begin_info = "totally"
        else:
            start_time = task["poll_range_start"].timestamp()
            begin_info = f"from {task['poll_range_start']}"

        end_time = datetime.now(timezone.utc).timestamp()

        raw_batch_size = self.conf.get("sync_batch_size") or self.conf.get("batch_size") or INDEX_BATCH_SIZE
        try:
            batch_size = int(raw_batch_size)
        except (TypeError, ValueError):
            batch_size = INDEX_BATCH_SIZE
        if batch_size <= 0:
            batch_size = INDEX_BATCH_SIZE

        def document_batches():
            checkpoint = self.connector.build_dummy_checkpoint()
            pending_docs = []
            iterations = 0
            iteration_limit = 100_000

            while checkpoint.has_more:
                wrapper = CheckpointOutputWrapper()
                doc_generator = wrapper(self.connector.load_from_checkpoint(start_time, end_time, checkpoint))
                for document, failure, next_checkpoint in doc_generator:
                    if failure is not None:
                        _lineaje_payload = "Confluence connector failure: %s"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Confluence.document_batches).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:633fece78feb5a8dfbbc2d32973ab7426acdc486007e926ae1556376b9459c46'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:633fece78feb5a8dfbbc2d32973ab7426acdc486007e926ae1556376b9459c46', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 283, 'function': 'Confluence._generate.document_batches'}, 'file': 'rag/svr/sync_data_source.py', 'line': 283, 'function': 'document_batches', 'agent_name': 'Confluence', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.warning(_lineaje_payload, getattr(failure, "failure_message", failure))
                        continue
                    if document is not None:
                        pending_docs.append(document)
                        if len(pending_docs) >= batch_size:
                            yield pending_docs
                            pending_docs = []
                    if next_checkpoint is not None:
                        checkpoint = next_checkpoint

                iterations += 1
                if iterations > iteration_limit:
                    raise RuntimeError("Too many iterations while loading Confluence documents.")

            if pending_docs:
                yield pending_docs

        async def async_wrapper():
            for batch in document_batches():
                yield batch
        
        _lineaje_payload = "Connect to Confluence: {} {}".format(self.conf["wiki_base"], begin_info)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Confluence._generate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b4ee819bb247a15b23a18a47688dfb6a61bf6034365cece8531124872e4f57db'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b4ee819bb247a15b23a18a47688dfb6a61bf6034365cece8531124872e4f57db', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 304, 'function': 'Confluence._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 304, 'function': '_generate', 'agent_name': 'Confluence', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        return async_wrapper()


class Notion(SyncBase):
    SOURCE_NAME: str = FileSource.NOTION

    async def _generate(self, task: dict):
        self.connector = NotionConnector(root_page_id=self.conf["root_page_id"])
        self.connector.load_credentials(self.conf["credentials"])
        document_generator = (
            self.connector.load_from_state()
            if task["reindex"] == "1" or not task["poll_range_start"]
            else self.connector.poll_source(task["poll_range_start"].timestamp(), datetime.now(timezone.utc).timestamp())
        )

        begin_info = "totally" if task["reindex"] == "1" or not task["poll_range_start"] else "from {}".format(task["poll_range_start"])
        _lineaje_payload = "Connect to Notion: root({}) {}".format(self.conf["root_page_id"], begin_info)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Notion._generate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:946c050d8ca73bf52192d2909e444a2ccad23705fdadcab27dc60712d7aaa3f9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:946c050d8ca73bf52192d2909e444a2ccad23705fdadcab27dc60712d7aaa3f9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 321, 'function': 'Notion._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 321, 'function': '_generate', 'agent_name': 'Notion', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `document_generator` as it flows from the agent to the user interface, before it leaves the application (in Notion._generate).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `document_generator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9cf07ee072e71d2499b725f713c5ba08d929310cb4711ffd003fed2abd831d8b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9cf07ee072e71d2499b725f713c5ba08d929310cb4711ffd003fed2abd831d8b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 322, 'function': 'Notion._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 322, 'function': '_generate', 'agent_name': 'Notion', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            document_generator = _gr_client.enforce(_gr_site, document_generator, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return document_generator


class Discord(SyncBase):
    SOURCE_NAME: str = FileSource.DISCORD

    async def _generate(self, task: dict):
        server_ids: str | None = self.conf.get("server_ids", None)
        # "channel1,channel2"
        channel_names: str | None = self.conf.get("channel_names", None)

        self.connector = DiscordConnector(
            server_ids=server_ids.split(",") if server_ids else [],
            channel_names=channel_names.split(",") if channel_names else [],
            start_date=datetime(1970, 1, 1, tzinfo=timezone.utc).strftime("%Y-%m-%d"),
            batch_size=self.conf.get("batch_size", 1024),
        )
        self.connector.load_credentials(self.conf["credentials"])
        document_generator = (
            self.connector.load_from_state()
            if task["reindex"] == "1" or not task["poll_range_start"]
            else self.connector.poll_source(task["poll_range_start"].timestamp(), datetime.now(timezone.utc).timestamp())
        )

        begin_info = "totally" if task["reindex"] == "1" or not task["poll_range_start"] else "from {}".format(task["poll_range_start"])
        _lineaje_payload = "Connect to Discord: servers({}),  channel({}) {}".format(server_ids, channel_names, begin_info)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Discord._generate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c550431cd292a2df397bf187529f65c1e06670f9bb7443c770d347bacd3b6581'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c550431cd292a2df397bf187529f65c1e06670f9bb7443c770d347bacd3b6581', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 347, 'function': 'Discord._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 347, 'function': '_generate', 'agent_name': 'Discord', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `document_generator` as it flows from the agent to the user interface, before it leaves the application (in Discord._generate).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `document_generator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6fcbbf4e8608019391a6277fc42f610396d268fd3394441d842f0e9659892b70'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6fcbbf4e8608019391a6277fc42f610396d268fd3394441d842f0e9659892b70', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 348, 'function': 'Discord._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 348, 'function': '_generate', 'agent_name': 'Discord', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            document_generator = _gr_client.enforce(_gr_site, document_generator, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return document_generator


class Gmail(SyncBase):
    SOURCE_NAME: str = FileSource.GMAIL

    async def _generate(self, task: dict):
        # Gmail sync reuses the generic LoadConnector/PollConnector interface
        # implemented by common.data_source.gmail_connector.GmailConnector.
        #
        # Config expectations (self.conf):
        #   credentials: Gmail / Workspace OAuth JSON (with primary admin email)
        #   batch_size:  optional, defaults to INDEX_BATCH_SIZE
        batch_size = self.conf.get("batch_size", INDEX_BATCH_SIZE)

        self.connector = GmailConnector(batch_size=batch_size)

        credentials = self.conf.get("credentials")
        if not credentials:
            raise ValueError("Gmail connector is missing credentials.")

        new_credentials = self.connector.load_credentials(credentials)
        if new_credentials:
            # Persist rotated / refreshed credentials back to connector config
            try:
                updated_conf = copy.deepcopy(self.conf)
                updated_conf["credentials"] = new_credentials
                ConnectorService.update_by_id(task["connector_id"], {"config": updated_conf})
                self.conf = updated_conf
                _lineaje_payload = "Persisted refreshed Gmail credentials for connector %s"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Gmail._generate).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:724b1edd91ffc7c56fb786745f8ded8c43d7bb465cbfdf682a5aade5c9ef829e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:724b1edd91ffc7c56fb786745f8ded8c43d7bb465cbfdf682a5aade5c9ef829e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 377, 'function': 'Gmail._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 377, 'function': '_generate', 'agent_name': 'Gmail', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(
                    _lineaje_payload,
                    task["connector_id"],
                )
            except Exception:
                _lineaje_payload = "Failed to persist refreshed Gmail credentials for connector %s"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Gmail._generate).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:b6ead1e65badfcb17842c2256e42e5524b59d1469bb021f0ba18b476d0f6e0be'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b6ead1e65badfcb17842c2256e42e5524b59d1469bb021f0ba18b476d0f6e0be', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 382, 'function': 'Gmail._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 382, 'function': '_generate', 'agent_name': 'Gmail', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(
                    _lineaje_payload,
                    task["connector_id"],
                )

        # Decide between full reindex and incremental polling by time range.
        if task["reindex"] == "1" or not task.get("poll_range_start"):
            start_time = None
            end_time = None
            begin_info = "totally"
            document_generator = self.connector.load_from_state()
        else:
            poll_start = task["poll_range_start"]
            # Defensive: if poll_start is somehow None, fall back to full load
            if poll_start is None:
                start_time = None
                end_time = None
                begin_info = "totally"
                document_generator = self.connector.load_from_state()
            else:
                start_time = poll_start.timestamp()
                end_time = datetime.now(timezone.utc).timestamp()
                begin_info = f"from {poll_start}"
                document_generator = self.connector.poll_source(start_time, end_time)

        try:
            admin_email = self.connector.primary_admin_email
        except RuntimeError:
            admin_email = "unknown"
        _lineaje_payload = f"Connect to Gmail as {admin_email} {begin_info}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Gmail._generate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e048a3d1bcca0c9a739f6453a7d5f4f1aa465b2789769adb31917b35fbaccea4'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e048a3d1bcca0c9a739f6453a7d5f4f1aa465b2789769adb31917b35fbaccea4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 411, 'function': 'Gmail._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 411, 'function': '_generate', 'agent_name': 'Gmail', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `document_generator` as it flows from the agent to the user interface, before it leaves the application (in Gmail._generate).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `document_generator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a14a76204610256e8cc1a1be66ebb1a6516a1a6d5fb6e2fcaf52baa74c8defc6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a14a76204610256e8cc1a1be66ebb1a6516a1a6d5fb6e2fcaf52baa74c8defc6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 412, 'function': 'Gmail._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 412, 'function': '_generate', 'agent_name': 'Gmail', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            document_generator = _gr_client.enforce(_gr_site, document_generator, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return document_generator


class Dropbox(SyncBase):
    SOURCE_NAME: str = FileSource.DROPBOX

    async def _generate(self, task: dict):
        self.connector = DropboxConnector(batch_size=self.conf.get("batch_size", INDEX_BATCH_SIZE))
        self.connector.load_credentials(self.conf["credentials"])

        if task["reindex"] == "1" or not task["poll_range_start"]:
            document_generator = self.connector.load_from_state()
            begin_info = "totally"
        else:
            poll_start = task["poll_range_start"]
            document_generator = self.connector.poll_source(
                poll_start.timestamp(), datetime.now(timezone.utc).timestamp()
            )
            begin_info = f"from {poll_start}"

        _lineaje_payload = f"[Dropbox] Connect to Dropbox {begin_info}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Dropbox._generate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9a1f5ba63d4ab422aa0b73fff68ba1ece24042dad61bee9c670cae2b6f071251'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9a1f5ba63d4ab422aa0b73fff68ba1ece24042dad61bee9c670cae2b6f071251', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 432, 'function': 'Dropbox._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 432, 'function': '_generate', 'agent_name': 'Dropbox', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `document_generator` as it flows from the agent to the user interface, before it leaves the application (in Dropbox._generate).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `document_generator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5c34d2a3b38cecd86b31234493a607bddaed75ac22af7c22109292145714b366'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5c34d2a3b38cecd86b31234493a607bddaed75ac22af7c22109292145714b366', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 433, 'function': 'Dropbox._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 433, 'function': '_generate', 'agent_name': 'Dropbox', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            document_generator = _gr_client.enforce(_gr_site, document_generator, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return document_generator


class GoogleDrive(SyncBase):
    SOURCE_NAME: str = FileSource.GOOGLE_DRIVE

    async def _generate(self, task: dict):
        connector_kwargs = {
            "include_shared_drives": self.conf.get("include_shared_drives", False),
            "include_my_drives": self.conf.get("include_my_drives", False),
            "include_files_shared_with_me": self.conf.get("include_files_shared_with_me", False),
            "shared_drive_urls": self.conf.get("shared_drive_urls"),
            "my_drive_emails": self.conf.get("my_drive_emails"),
            "shared_folder_urls": self.conf.get("shared_folder_urls"),
            "specific_user_emails": self.conf.get("specific_user_emails"),
            "batch_size": self.conf.get("batch_size", INDEX_BATCH_SIZE),
        }
        self.connector = GoogleDriveConnector(**connector_kwargs)
        self.connector.set_allow_images(self.conf.get("allow_images", False))

        credentials = self.conf.get("credentials")
        if not credentials:
            raise ValueError("Google Drive connector is missing credentials.")

        new_credentials = self.connector.load_credentials(credentials)
        if new_credentials:
            self._persist_rotated_credentials(task["connector_id"], new_credentials)

        if task["reindex"] == "1" or not task["poll_range_start"]:
            start_time = 0.0
            begin_info = "totally"
        else:
            start_time = task["poll_range_start"].timestamp()
            begin_info = f"from {task['poll_range_start']}"

        end_time = datetime.now(timezone.utc).timestamp()
        raw_batch_size = self.conf.get("sync_batch_size") or self.conf.get("batch_size") or INDEX_BATCH_SIZE
        try:
            batch_size = int(raw_batch_size)
        except (TypeError, ValueError):
            batch_size = INDEX_BATCH_SIZE
        if batch_size <= 0:
            batch_size = INDEX_BATCH_SIZE

        def document_batches():
            checkpoint = self.connector.build_dummy_checkpoint()
            pending_docs = []
            iterations = 0
            iteration_limit = 100_000

            while checkpoint.has_more:
                wrapper = CheckpointOutputWrapper()
                doc_generator = wrapper(self.connector.load_from_checkpoint(start_time, end_time, checkpoint))
                for document, failure, next_checkpoint in doc_generator:
                    if failure is not None:
                        _lineaje_payload = "Google Drive connector failure: %s"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDrive.document_batches).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:e55f11a5fce3cc237afbaf0377b7cfbdc16a993b0068faa8e38fa6e2503fc168'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e55f11a5fce3cc237afbaf0377b7cfbdc16a993b0068faa8e38fa6e2503fc168', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 488, 'function': 'GoogleDrive._generate.document_batches'}, 'file': 'rag/svr/sync_data_source.py', 'line': 488, 'function': 'document_batches', 'agent_name': 'GoogleDrive', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.warning(_lineaje_payload, getattr(failure, "failure_message", failure))
                        continue
                    if document is not None:
                        pending_docs.append(document)
                        if len(pending_docs) >= batch_size:
                            yield pending_docs
                            pending_docs = []
                    if next_checkpoint is not None:
                        checkpoint = next_checkpoint

                iterations += 1
                if iterations > iteration_limit:
                    raise RuntimeError("Too many iterations while loading Google Drive documents.")

            if pending_docs:
                yield pending_docs

        try:
            admin_email = self.connector.primary_admin_email
        except RuntimeError:
            admin_email = "unknown"
        _lineaje_payload = f"Connect to Google Drive as {admin_email} {begin_info}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDrive._generate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:725a065b1fddd82f735d4b4148c57b9f5d257dbae3a1bce2821e6e28350c4e84'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:725a065b1fddd82f735d4b4148c57b9f5d257dbae3a1bce2821e6e28350c4e84', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 509, 'function': 'GoogleDrive._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 509, 'function': '_generate', 'agent_name': 'GoogleDrive', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        return document_batches()

    def _persist_rotated_credentials(self, connector_id: str, credentials: dict[str, Any]) -> None:
        try:
            updated_conf = copy.deepcopy(self.conf)
            updated_conf["credentials"] = credentials
            ConnectorService.update_by_id(connector_id, {"config": updated_conf})
            self.conf = updated_conf
            # LINEAJE: runtime guardrail checks `connector_id` as it flows from the agent to the application log, before it is written to the log (in GoogleDrive._persist_rotated_credentials).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `connector_id` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9d6daa7545f5fbb57de2db423513a27054a1ec27ff74fbf0b82fbfdf671da730'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9d6daa7545f5fbb57de2db423513a27054a1ec27ff74fbf0b82fbfdf671da730', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 518, 'function': 'GoogleDrive._persist_rotated_credentials'}, 'file': 'rag/svr/sync_data_source.py', 'line': 518, 'function': '_persist_rotated_credentials', 'agent_name': 'GoogleDrive', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                connector_id = _gr_client.enforce(_gr_site, connector_id, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info("Persisted refreshed Google Drive credentials for connector %s", connector_id)
        except Exception:
            # LINEAJE: runtime guardrail checks `connector_id` as it flows from the agent to the application log, before it is written to the log (in GoogleDrive._persist_rotated_credentials).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `connector_id` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:2ad2f7ba5476eb35909de218f4839320f107cf1351d7bc10af521e8b6824546f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2ad2f7ba5476eb35909de218f4839320f107cf1351d7bc10af521e8b6824546f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 520, 'function': 'GoogleDrive._persist_rotated_credentials'}, 'file': 'rag/svr/sync_data_source.py', 'line': 520, 'function': '_persist_rotated_credentials', 'agent_name': 'GoogleDrive', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                connector_id = _gr_client.enforce(_gr_site, connector_id, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception("Failed to persist refreshed Google Drive credentials for connector %s", connector_id)


class Jira(SyncBase):
    SOURCE_NAME: str = FileSource.JIRA

    def _get_source_prefix(self):
        return "[Jira]"

    async def _generate(self, task: dict):
        connector_kwargs = {
            "jira_base_url": self.conf["base_url"],
            "project_key": self.conf.get("project_key"),
            "jql_query": self.conf.get("jql_query"),
            "batch_size": self.conf.get("batch_size", INDEX_BATCH_SIZE),
            "include_comments": self.conf.get("include_comments", True),
            "include_attachments": self.conf.get("include_attachments", False),
            "labels_to_skip": self._normalize_list(self.conf.get("labels_to_skip")),
            "comment_email_blacklist": self._normalize_list(self.conf.get("comment_email_blacklist")),
            "scoped_token": self.conf.get("scoped_token", False),
            "attachment_size_limit": self.conf.get("attachment_size_limit"),
            "timezone_offset": self.conf.get("timezone_offset"),
        }

        self.connector = JiraConnector(**connector_kwargs)

        credentials = self.conf.get("credentials")
        if not credentials:
            raise ValueError("Jira connector is missing credentials.")

        self.connector.load_credentials(credentials)
        self.connector.validate_connector_settings()

        if task["reindex"] == "1" or not task["poll_range_start"]:
            start_time = 0.0
            begin_info = "totally"
        else:
            start_time = task["poll_range_start"].timestamp()
            begin_info = f"from {task['poll_range_start']}"

        end_time = datetime.now(timezone.utc).timestamp()

        raw_batch_size = self.conf.get("sync_batch_size") or self.conf.get("batch_size") or INDEX_BATCH_SIZE
        try:
            batch_size = int(raw_batch_size)
        except (TypeError, ValueError):
            batch_size = INDEX_BATCH_SIZE
        if batch_size <= 0:
            batch_size = INDEX_BATCH_SIZE

        def document_batches():
            checkpoint = self.connector.build_dummy_checkpoint()
            pending_docs = []
            iterations = 0
            iteration_limit = 100_000

            while checkpoint.has_more:
                wrapper = CheckpointOutputWrapper()
                generator = wrapper(
                    self.connector.load_from_checkpoint(
                        start_time,
                        end_time,
                        checkpoint,
                    )
                )
                for document, failure, next_checkpoint in generator:
                    if failure is not None:
                        _lineaje_payload = f"[Jira] Jira connector failure: {getattr(failure, 'failure_message', failure)}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Jira.document_batches).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:768b84f9e9e830a99493ed6e4d8392859f109e2d7040eea47c8105f0b4713fa4'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:768b84f9e9e830a99493ed6e4d8392859f109e2d7040eea47c8105f0b4713fa4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 587, 'function': 'Jira._generate.document_batches'}, 'file': 'rag/svr/sync_data_source.py', 'line': 587, 'function': 'document_batches', 'agent_name': 'Jira', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.warning(
                            _lineaje_payload
                        )
                        continue
                    if document is not None:
                        pending_docs.append(document)
                        if len(pending_docs) >= batch_size:
                            yield pending_docs
                            pending_docs = []
                    if next_checkpoint is not None:
                        checkpoint = next_checkpoint

                iterations += 1
                if iterations > iteration_limit:
                    _lineaje_payload = f"[Jira] Task {task.get('id')} exceeded iteration limit ({iteration_limit})."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Jira.document_batches).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:bbd15f1de38838edfc77b07b9875b546f54678e0fda5725dedba35d2491b5ab4'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bbd15f1de38838edfc77b07b9875b546f54678e0fda5725dedba35d2491b5ab4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 601, 'function': 'Jira._generate.document_batches'}, 'file': 'rag/svr/sync_data_source.py', 'line': 601, 'function': 'document_batches', 'agent_name': 'Jira', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.error(_lineaje_payload)
                    raise RuntimeError("Too many iterations while loading Jira documents.")

            if pending_docs:
                yield pending_docs

        _lineaje_payload = f"[Jira] Connect to Jira {connector_kwargs['jira_base_url']} {begin_info}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Jira._generate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:50d74a676ac16e2eb0d07addc9c3b06a5e84ca9a10a0731cc99b89abc487906c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:50d74a676ac16e2eb0d07addc9c3b06a5e84ca9a10a0731cc99b89abc487906c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 607, 'function': 'Jira._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 607, 'function': '_generate', 'agent_name': 'Jira', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        return document_batches()

    @staticmethod
    def _normalize_list(values: Any) -> list[str] | None:
        if values is None:
            return None
        if isinstance(values, str):
            values = [item.strip() for item in values.split(",")]
        return [str(value).strip() for value in values if value is not None and str(value).strip()]


class SharePoint(SyncBase):
    SOURCE_NAME: str = FileSource.SHAREPOINT

    async def _generate(self, task: dict):
        pass


class Slack(SyncBase):
    SOURCE_NAME: str = FileSource.SLACK

    async def _generate(self, task: dict):
        pass


class Teams(SyncBase):
    SOURCE_NAME: str = FileSource.TEAMS

    async def _generate(self, task: dict):
        pass


class WebDAV(SyncBase):
    SOURCE_NAME: str = FileSource.WEBDAV

    async def _generate(self, task: dict):
        self.connector = WebDAVConnector(
            base_url=self.conf["base_url"],
            remote_path=self.conf.get("remote_path", "/")
        )
        self.connector.load_credentials(self.conf["credentials"])
        
        _lineaje_payload = f"Task info: reindex={task['reindex']}, poll_range_start={task['poll_range_start']}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAV._generate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:82c13e152e002178fe2037fa0b1bff38b4d47bc831611bc9442f9093945e9234'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:82c13e152e002178fe2037fa0b1bff38b4d47bc831611bc9442f9093945e9234', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 650, 'function': 'WebDAV._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 650, 'function': '_generate', 'agent_name': 'WebDAV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        
        if task["reindex"]=="1" or not task["poll_range_start"]:
            _lineaje_payload = "Using load_from_state (full sync)"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAV._generate).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ccc3b2be9e41c776c326de4274f1b94d5a4bfef033c928f09a3966f52498554c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ccc3b2be9e41c776c326de4274f1b94d5a4bfef033c928f09a3966f52498554c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 653, 'function': 'WebDAV._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 653, 'function': '_generate', 'agent_name': 'WebDAV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            document_batch_generator = self.connector.load_from_state()
            begin_info = "totally"
        else:
            start_ts = task["poll_range_start"].timestamp()
            end_ts = datetime.now(timezone.utc).timestamp()
            _lineaje_payload = f"Polling WebDAV from {task['poll_range_start']} (ts: {start_ts}) to now (ts: {end_ts})"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAV._generate).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e252e9d7be0700f51471933bcf39aff9d7393931ee0a0537864caba530aeac57'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e252e9d7be0700f51471933bcf39aff9d7393931ee0a0537864caba530aeac57', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 659, 'function': 'WebDAV._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 659, 'function': '_generate', 'agent_name': 'WebDAV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            document_batch_generator = self.connector.poll_source(start_ts, end_ts)
            begin_info = "from {}".format(task["poll_range_start"])
            
        _lineaje_payload = ("Connect to WebDAV: {}(path: {}) {}".format(
            self.conf["base_url"],
            self.conf.get("remote_path", "/"),
            begin_info
        ))
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAV._generate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:28bc5ab3f7c9b6eaf459484d580e6349a4a939b03d912e541a15d914f82ccf0d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:28bc5ab3f7c9b6eaf459484d580e6349a4a939b03d912e541a15d914f82ccf0d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 663, 'function': 'WebDAV._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 663, 'function': '_generate', 'agent_name': 'WebDAV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `document_batch_generator` as it flows from the agent to the user interface, before it leaves the application (in WebDAV._generate).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `document_batch_generator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:46d4e6a9ddb18f6454ea9c234966cb8719d42de83ee1ab10d71f6cd4992eaa58'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:46d4e6a9ddb18f6454ea9c234966cb8719d42de83ee1ab10d71f6cd4992eaa58', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 668, 'function': 'WebDAV._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 668, 'function': '_generate', 'agent_name': 'WebDAV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            document_batch_generator = _gr_client.enforce(_gr_site, document_batch_generator, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return document_batch_generator
        
class Moodle(SyncBase):
    SOURCE_NAME: str = FileSource.MOODLE

    async def _generate(self, task: dict):
        self.connector = MoodleConnector(
            moodle_url=self.conf["moodle_url"],
            batch_size=self.conf.get("batch_size", INDEX_BATCH_SIZE)
        )
        
        self.connector.load_credentials(self.conf["credentials"])

        # Determine the time range for synchronization based on reindex or poll_range_start
        if task["reindex"] == "1" or not task.get("poll_range_start"):
            document_generator = self.connector.load_from_state()
            begin_info = "totally"
        else:
            poll_start = task["poll_range_start"]
            if poll_start is None:
                document_generator = self.connector.load_from_state()
                begin_info = "totally"
            else:
                document_generator = self.connector.poll_source(
                    poll_start.timestamp(), 
                    datetime.now(timezone.utc).timestamp()
                )
                begin_info = "from {}".format(poll_start)

        _lineaje_payload = "Connect to Moodle: {} {}".format(self.conf["moodle_url"], begin_info)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Moodle._generate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:774a8ab03bd7d7f83e61d987cf5472ad3f3d01d2e837b42eef87933874f1f1a0'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:774a8ab03bd7d7f83e61d987cf5472ad3f3d01d2e837b42eef87933874f1f1a0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 697, 'function': 'Moodle._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 697, 'function': '_generate', 'agent_name': 'Moodle', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `document_generator` as it flows from the agent to the user interface, before it leaves the application (in Moodle._generate).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `document_generator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:01d28fb0b8d58044a6e3eff2569908aa591ef2100dde47c61bc40959d6e73064'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:01d28fb0b8d58044a6e3eff2569908aa591ef2100dde47c61bc40959d6e73064', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 698, 'function': 'Moodle._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 698, 'function': '_generate', 'agent_name': 'Moodle', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            document_generator = _gr_client.enforce(_gr_site, document_generator, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return document_generator


class BOX(SyncBase):
    SOURCE_NAME: str = FileSource.BOX

    async def _generate(self, task: dict):
        self.connector = BoxConnector(
            folder_id=self.conf.get("folder_id", "0"),
        )

        credential = json.loads(self.conf['credentials']['box_tokens'])

        auth = BoxOAuth(
            OAuthConfig(
                client_id=credential['client_id'],
                client_secret=credential['client_secret'],
            )
        )

        token = AccessToken(
            access_token=credential['access_token'],
            refresh_token=credential['refresh_token'],
        )    
        auth.token_storage.store(token)

        self.connector.load_credentials(auth)
        if task["reindex"] == "1" or not task["poll_range_start"]:
            document_generator = self.connector.load_from_state()
            begin_info = "totally"
        else:
            poll_start = task["poll_range_start"]
            if poll_start is None:
                document_generator = self.connector.load_from_state()
                begin_info = "totally"
            else:
                document_generator = self.connector.poll_source(
                    poll_start.timestamp(),
                    datetime.now(timezone.utc).timestamp()
                )
                begin_info = "from {}".format(poll_start)
        _lineaje_payload = "Connect to Box: folder_id({}) {}".format(self.conf["folder_id"], begin_info)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in BOX._generate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:aa4b83c49ae6202f7fd303ee3770d2c100f1d8ce642b6c8e270dfc7143d880af'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aa4b83c49ae6202f7fd303ee3770d2c100f1d8ce642b6c8e270dfc7143d880af', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 739, 'function': 'BOX._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 739, 'function': '_generate', 'agent_name': 'BOX', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `document_generator` as it flows from the agent to the user interface, before it leaves the application (in BOX._generate).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `document_generator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c1c729014d7421e1bea556d833d7bb7e00ced9d8aabe6523616542cef2e3a549'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c1c729014d7421e1bea556d833d7bb7e00ced9d8aabe6523616542cef2e3a549', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 740, 'function': 'BOX._generate'}, 'file': 'rag/svr/sync_data_source.py', 'line': 740, 'function': '_generate', 'agent_name': 'BOX', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            document_generator = _gr_client.enforce(_gr_site, document_generator, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return document_generator
    
func_factory = {
    FileSource.S3: S3,
    FileSource.R2: R2,
    FileSource.OCI_STORAGE: OCI_STORAGE,
    FileSource.GOOGLE_CLOUD_STORAGE: GOOGLE_CLOUD_STORAGE,
    FileSource.NOTION: Notion,
    FileSource.DISCORD: Discord,
    FileSource.CONFLUENCE: Confluence,
    FileSource.GMAIL: Gmail,
    FileSource.GOOGLE_DRIVE: GoogleDrive,
    FileSource.JIRA: Jira,
    FileSource.SHAREPOINT: SharePoint,
    FileSource.SLACK: Slack,
    FileSource.TEAMS: Teams,
    FileSource.MOODLE: Moodle,
    FileSource.DROPBOX: Dropbox,
    FileSource.WEBDAV: WebDAV,
    FileSource.BOX: BOX
}


async def dispatch_tasks():
    while True:
        try:
            list(SyncLogsService.list_sync_tasks()[0])
            break
        except Exception as e:
            _lineaje_payload = f"DB is not ready yet: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in dispatch_tasks).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3ecbe1022e08ed5dbec0746312929756f8a7fdcca43df2ef3e11b62761c6bfa0'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3ecbe1022e08ed5dbec0746312929756f8a7fdcca43df2ef3e11b62761c6bfa0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 769, 'function': 'dispatch_tasks'}, 'file': 'rag/svr/sync_data_source.py', 'line': 769, 'function': 'dispatch_tasks', 'agent_name': 'dispatch_tasks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            await asyncio.sleep(3)

    tasks = []
    for task in SyncLogsService.list_sync_tasks()[0]:
        if task["poll_range_start"]:
            task["poll_range_start"] = task["poll_range_start"].astimezone(timezone.utc)
        if task["poll_range_end"]:
            task["poll_range_end"] = task["poll_range_end"].astimezone(timezone.utc)

        func = func_factory[task["source"]](task["config"])
        tasks.append(asyncio.create_task(func(task)))

    try:
        await asyncio.gather(*tasks, return_exceptions=False)
    except Exception as e:
        _lineaje_payload = f"Error in dispatch_tasks: {e}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in dispatch_tasks).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:68f20635b0f53ce923803a150a965f2774037f3bd7008bfb229a673088b63d4a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:68f20635b0f53ce923803a150a965f2774037f3bd7008bfb229a673088b63d4a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 785, 'function': 'dispatch_tasks'}, 'file': 'rag/svr/sync_data_source.py', 'line': 785, 'function': 'dispatch_tasks', 'agent_name': 'dispatch_tasks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(_lineaje_payload)
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    await asyncio.sleep(1)


stop_event = threading.Event()


def signal_handler(sig, frame):
    _lineaje_payload = "Received interrupt signal, shutting down..."
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in signal_handler).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:38d7096d6552eff329d83cb35f6cea07d5b5ce5406c842c129a0ca0a217d983c'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:38d7096d6552eff329d83cb35f6cea07d5b5ce5406c842c129a0ca0a217d983c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 797, 'function': 'signal_handler'}, 'file': 'rag/svr/sync_data_source.py', 'line': 797, 'function': 'signal_handler', 'agent_name': 'signal_handler', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)
    stop_event.set()
    time.sleep(1)
    sys.exit(0)


CONSUMER_NO = "0" if len(sys.argv) < 2 else sys.argv[1]
CONSUMER_NAME = "data_sync_" + CONSUMER_NO


async def main():
    _lineaje_payload = (r"""
  _____        _           _____
 |  __ \      | |         / ____|
 | |  | | __ _| |_ __ _  | (___  _   _ _ __   ___
 | |  | |/ _` | __/ _` |  \___ \| | | | '_ \ / __|
 | |__| | (_| | || (_| |  ____) | |_| | | | | (__
 |_____/ \__,_|\__\__,_| |_____/ \__, |_| |_|\___|
                                  __/ |
                                 |___/
    """)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:b6a13517deaab8490f52e4d99ded6d2ef6f951793d4978019651c0b168709ae9'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b6a13517deaab8490f52e4d99ded6d2ef6f951793d4978019651c0b168709ae9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 808, 'function': 'main'}, 'file': 'rag/svr/sync_data_source.py', 'line': 808, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)
    _lineaje_payload = f"RAGFlow version: {get_ragflow_version()}"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:99beb15234fde6ccac88cdea8239f836bc221fc8c4cacd7780f1a1f9d6bd9b10'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:99beb15234fde6ccac88cdea8239f836bc221fc8c4cacd7780f1a1f9d6bd9b10', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 818, 'function': 'main'}, 'file': 'rag/svr/sync_data_source.py', 'line': 818, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)
    show_configs()
    settings.init_settings()
    if sys.platform != "win32":
        signal.signal(signal.SIGUSR1, start_tracemalloc_and_snapshot)
        signal.signal(signal.SIGUSR2, stop_tracemalloc)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while not stop_event.is_set():
        await dispatch_tasks()
    _lineaje_payload = "BUG!!! You should not reach here!!!"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:671374dafc8a0045fa8c4db020872e4953a7f67bd8484d80879e706a02635689'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:671374dafc8a0045fa8c4db020872e4953a7f67bd8484d80879e706a02635689', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/sync_data_source.py', 'line': 829, 'function': 'main'}, 'file': 'rag/svr/sync_data_source.py', 'line': 829, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.error(_lineaje_payload)


if __name__ == "__main__":
    faulthandler.enable()
    init_root_logger(CONSUMER_NAME)
    asyncio.run(main())
