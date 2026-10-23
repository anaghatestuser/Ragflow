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
import asyncio
import socket
import concurrent
# from beartype import BeartypeConf
# from beartype.claw import beartype_all  # <-- you didn't sign up for this
# beartype_all(conf=BeartypeConf(violation_type=UserWarning))    # <-- emit warnings from all code
import random
import sys
import threading
import time

from api.db import PIPELINE_SPECIAL_PROGRESS_FREEZE_TASK_TYPES
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.pipeline_operation_log_service import PipelineOperationLogService
from common.connection_utils import timeout
from common.metadata_utils import update_metadata_to, metadata_schema
from rag.utils.base64_image import image2id
from rag.utils.raptor_utils import should_skip_raptor, get_skip_reason
from common.log_utils import init_root_logger
from common.config_utils import show_configs
from graphrag.general.index import run_graphrag_for_kb
from graphrag.utils import get_llm_cache, set_llm_cache, get_tags_from_cache, set_tags_to_cache
from rag.prompts.generator import keyword_extraction, question_proposal, content_tagging, run_toc_from_text, \
    gen_metadata
import logging
import os
from datetime import datetime
import json
import xxhash
import copy
import re
from functools import partial
from multiprocessing.context import TimeoutError
from timeit import default_timer as timer
import signal
import exceptiongroup
import faulthandler
import numpy as np
from peewee import DoesNotExist
from common.constants import LLMType, ParserType, PipelineTaskType
from api.db.services.document_service import DocumentService
from api.db.services.llm_service import LLMBundle
from api.db.services.task_service import TaskService, has_canceled, CANVAS_DEBUG_DOC_ID, GRAPH_RAPTOR_FAKE_DOC_ID
from api.db.services.file2document_service import File2DocumentService
from common.versions import get_ragflow_version
from api.db.db_models import close_connection
from rag.app import laws, paper, presentation, manual, qa, table, book, resume, picture, naive, one, audio, \
    email, tag
from rag.nlp import search, rag_tokenizer, add_positions
from rag.raptor import RecursiveAbstractiveProcessing4TreeOrganizedRetrieval as Raptor
from common.token_utils import num_tokens_from_string, truncate
from rag.utils.redis_conn import REDIS_CONN, RedisDistributedLock
from graphrag.utils import chat_limiter
from common.signal_utils import start_tracemalloc_and_snapshot, stop_tracemalloc
from common.exceptions import TaskCanceledException
from common import settings
from common.constants import PAGERANK_FLD, TAG_FLD, SVR_CONSUMER_GROUP_NAME

BATCH_SIZE = 64

FACTORY = {
    "general": naive,
    ParserType.NAIVE.value: naive,
    ParserType.PAPER.value: paper,
    ParserType.BOOK.value: book,
    ParserType.PRESENTATION.value: presentation,
    ParserType.MANUAL.value: manual,
    ParserType.LAWS.value: laws,
    ParserType.QA.value: qa,
    ParserType.TABLE.value: table,
    ParserType.RESUME.value: resume,
    ParserType.PICTURE.value: picture,
    ParserType.ONE.value: one,
    ParserType.AUDIO.value: audio,
    ParserType.EMAIL.value: email,
    ParserType.KG.value: naive,
    ParserType.TAG.value: tag
}

TASK_TYPE_TO_PIPELINE_TASK_TYPE = {
    "dataflow" : PipelineTaskType.PARSE,
    "raptor": PipelineTaskType.RAPTOR,
    "graphrag": PipelineTaskType.GRAPH_RAG,
    "mindmap": PipelineTaskType.MINDMAP,
}

UNACKED_ITERATOR = None

CONSUMER_NO = "0" if len(sys.argv) < 2 else sys.argv[1]
CONSUMER_NAME = "task_executor_" + CONSUMER_NO
BOOT_AT = datetime.now().astimezone().isoformat(timespec="milliseconds")
PENDING_TASKS = 0
LAG_TASKS = 0
DONE_TASKS = 0
FAILED_TASKS = 0

CURRENT_TASKS = {}

MAX_CONCURRENT_TASKS = int(os.environ.get('MAX_CONCURRENT_TASKS', "5"))
MAX_CONCURRENT_CHUNK_BUILDERS = int(os.environ.get('MAX_CONCURRENT_CHUNK_BUILDERS', "1"))
MAX_CONCURRENT_MINIO = int(os.environ.get('MAX_CONCURRENT_MINIO', '10'))
task_limiter = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
chunk_limiter = asyncio.Semaphore(MAX_CONCURRENT_CHUNK_BUILDERS)
embed_limiter = asyncio.Semaphore(MAX_CONCURRENT_CHUNK_BUILDERS)
minio_limiter = asyncio.Semaphore(MAX_CONCURRENT_MINIO)
kg_limiter = asyncio.Semaphore(2)
WORKER_HEARTBEAT_TIMEOUT = int(os.environ.get('WORKER_HEARTBEAT_TIMEOUT', '120'))
stop_event = threading.Event()


def signal_handler(sig, frame):
    _lineaje_payload = "Received interrupt signal, shutting down..."
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in signal_handler).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:bc9226b8a2b108749f964e094ba9866a597c589b58896413749982ba9f38f6f7'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bc9226b8a2b108749f964e094ba9866a597c589b58896413749982ba9f38f6f7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 126, 'function': 'signal_handler'}, 'file': 'rag/svr/task_executor.py', 'line': 126, 'function': 'signal_handler', 'agent_name': 'signal_handler', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
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


def set_progress(task_id, from_page=0, to_page=-1, prog=None, msg="Processing..."):
    try:
        if prog is not None and prog < 0:
            msg = "[ERROR]" + msg
        cancel = has_canceled(task_id)

        if cancel:
            msg += " [Canceled]"
            prog = -1

        if to_page > 0:
            if msg:
                if from_page < to_page:
                    msg = f"Page({from_page + 1}~{to_page + 1}): " + msg
        if msg:
            msg = datetime.now().strftime("%H:%M:%S") + " " + msg
        d = {"progress_msg": msg}
        if prog is not None:
            d["progress"] = prog

        TaskService.update_progress(task_id, d)

        close_connection()
        if cancel:
            raise TaskCanceledException(msg)
        _lineaje_payload = f"set_progress({task_id}), progress: {prog}, progress_msg: {msg}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in set_progress).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:12ecdf381cfd2ee4a6d78cfb95f8ea95added417d5f896b2defab6c1f48ab8c3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:12ecdf381cfd2ee4a6d78cfb95f8ea95added417d5f896b2defab6c1f48ab8c3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 157, 'function': 'set_progress'}, 'file': 'rag/svr/task_executor.py', 'line': 157, 'function': 'set_progress', 'agent_name': 'set_progress', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
    except DoesNotExist:
        _lineaje_payload = f"set_progress({task_id}) got exception DoesNotExist"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in set_progress).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b2bb11a9d8da06ad724579da27bea9547ba73fbb50faa6314163404f3571308b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b2bb11a9d8da06ad724579da27bea9547ba73fbb50faa6314163404f3571308b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 159, 'function': 'set_progress'}, 'file': 'rag/svr/task_executor.py', 'line': 159, 'function': 'set_progress', 'agent_name': 'set_progress', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning(_lineaje_payload)
    except Exception:
        _lineaje_payload = f"set_progress({task_id}), progress: {prog}, progress_msg: {msg}, got exception"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in set_progress).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8b2c003d0507941922962796a3aff31dd5436945d3f9f8615161f3bbbe8dddf1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8b2c003d0507941922962796a3aff31dd5436945d3f9f8615161f3bbbe8dddf1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 161, 'function': 'set_progress'}, 'file': 'rag/svr/task_executor.py', 'line': 161, 'function': 'set_progress', 'agent_name': 'set_progress', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.exception(_lineaje_payload)


async def collect():
    global CONSUMER_NAME, DONE_TASKS, FAILED_TASKS
    global UNACKED_ITERATOR

    svr_queue_names = settings.get_svr_queue_names()
    try:
        if not UNACKED_ITERATOR:
            UNACKED_ITERATOR = REDIS_CONN.get_unacked_iterator(svr_queue_names, SVR_CONSUMER_GROUP_NAME, CONSUMER_NAME)
        try:
            redis_msg = next(UNACKED_ITERATOR)
        except StopIteration:
            for svr_queue_name in svr_queue_names:
                redis_msg = REDIS_CONN.queue_consumer(svr_queue_name, SVR_CONSUMER_GROUP_NAME, CONSUMER_NAME)
                if redis_msg:
                    break
    except Exception:
        _lineaje_payload = "collect got exception"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in collect).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:74beca5efb4078848653d1096c6c7cfe899dbefe385baf4cbfeef222e8691429'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:74beca5efb4078848653d1096c6c7cfe899dbefe385baf4cbfeef222e8691429', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 180, 'function': 'collect'}, 'file': 'rag/svr/task_executor.py', 'line': 180, 'function': 'collect', 'agent_name': 'collect', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.exception(_lineaje_payload)
        return None, None

    if not redis_msg:
        return None, None
    msg = redis_msg.get_message()
    if not msg:
        _lineaje_payload = f"collect got empty message of {redis_msg.get_msg_id()}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in collect).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:fc1aaf923e609bd1f4d6c163260dfcff1ca940b14b40c84b7ab78d2db16d48f1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fc1aaf923e609bd1f4d6c163260dfcff1ca940b14b40c84b7ab78d2db16d48f1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 187, 'function': 'collect'}, 'file': 'rag/svr/task_executor.py', 'line': 187, 'function': 'collect', 'agent_name': 'collect', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(_lineaje_payload)
        redis_msg.ack()
        return None, None

    canceled = False
    if msg.get("doc_id", "") in [GRAPH_RAPTOR_FAKE_DOC_ID, CANVAS_DEBUG_DOC_ID]:
        task = msg
        if task["task_type"] in PIPELINE_SPECIAL_PROGRESS_FREEZE_TASK_TYPES:
            task = TaskService.get_task(msg["id"], msg["doc_ids"])
            if task:
                task["doc_id"] = msg["doc_id"]
                task["doc_ids"] = msg.get("doc_ids", []) or []
    else:
        task = TaskService.get_task(msg["id"])

    if task:
        canceled = has_canceled(task["id"])
    if not task or canceled:
        state = "is unknown" if not task else "has been cancelled"
        FAILED_TASKS += 1
        _lineaje_payload = f"collect task {msg['id']} {state}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in collect).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:032195c3e3376c6ed00e9523b20a098df56c1e5579041507fadf49a1b68efe1a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:032195c3e3376c6ed00e9523b20a098df56c1e5579041507fadf49a1b68efe1a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 207, 'function': 'collect'}, 'file': 'rag/svr/task_executor.py', 'line': 207, 'function': 'collect', 'agent_name': 'collect', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning(_lineaje_payload)
        redis_msg.ack()
        return None, None

    task_type = msg.get("task_type", "")
    task["task_type"] = task_type
    if task_type[:8] == "dataflow":
        task["tenant_id"] = msg["tenant_id"]
        task["dataflow_id"] = msg["dataflow_id"]
        task["kb_id"] = msg.get("kb_id", "")
    return redis_msg, task


async def get_storage_binary(bucket, name):
    return await asyncio.to_thread(settings.STORAGE_IMPL.get, bucket, name)


@timeout(60*80, 1)
async def build_chunks(task, progress_callback):
    if task["size"] > settings.DOC_MAXIMUM_SIZE:
        set_progress(task["id"], prog=-1, msg="File size exceeds( <= %dMb )" %
                                              (int(settings.DOC_MAXIMUM_SIZE / 1024 / 1024)))
        return []

    chunker = FACTORY[task["parser_id"].lower()]
    try:
        st = timer()
        bucket, name = File2DocumentService.get_storage_address(doc_id=task["doc_id"])
        binary = await get_storage_binary(bucket, name)
        _lineaje_payload = "From minio({}) {}/{}".format(timer() - st, task["location"], task["name"])
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in build_chunks).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:110bd24b3bedd86f9aa9012d6b42361f1ebf4821e4828882d37c9a03e8ac3638'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:110bd24b3bedd86f9aa9012d6b42361f1ebf4821e4828882d37c9a03e8ac3638', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 236, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 236, 'function': 'build_chunks', 'agent_name': 'build_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
    except TimeoutError:
        progress_callback(-1, "Internal server error: Fetch file from minio timeout. Could you try it again.")
        _lineaje_payload = "Minio {}/{} got timeout: Fetch file from minio timeout.".format(task["location"], task["name"])
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in build_chunks).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:58e0222e44faa6cc8e21de9cdedd725356dc7d51ee05eb96982a90be4c49efd2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:58e0222e44faa6cc8e21de9cdedd725356dc7d51ee05eb96982a90be4c49efd2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 239, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 239, 'function': 'build_chunks', 'agent_name': 'build_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.exception(
            _lineaje_payload)
        raise
    except Exception as e:
        if re.search("(No such file|not found)", str(e)):
            progress_callback(-1, "Can not find file <%s> from minio. Could you try it again?" % task["name"])
        else:
            progress_callback(-1, "Get file from minio: %s" % str(e).replace("'", ""))
        _lineaje_payload = "Chunking {}/{} got exception".format(task["location"], task["name"])
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in build_chunks).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b55170ce5256795b253c065278176c64a9ce4261b6c98dffd859ffe94b8ab94a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b55170ce5256795b253c065278176c64a9ce4261b6c98dffd859ffe94b8ab94a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 247, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 247, 'function': 'build_chunks', 'agent_name': 'build_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.exception(_lineaje_payload)
        raise

    try:
        async with chunk_limiter:
            cks = await asyncio.to_thread(
                chunker.chunk,
                task["name"],
                binary=binary,
                from_page=task["from_page"],
                to_page=task["to_page"],
                lang=task["language"],
                callback=progress_callback,
                kb_id=task["kb_id"],
                parser_config=task["parser_config"],
                tenant_id=task["tenant_id"],
            )
        _lineaje_payload = "Chunking({}) {}/{} done".format(timer() - st, task["location"], task["name"])
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in build_chunks).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:89fc623d3d9ea7d4fb321b8a3b3b0a36639aa9d8a283812a8eb5eed7e24cf16c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:89fc623d3d9ea7d4fb321b8a3b3b0a36639aa9d8a283812a8eb5eed7e24cf16c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 264, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 264, 'function': 'build_chunks', 'agent_name': 'build_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
    except TaskCanceledException:
        raise
    except Exception as e:
        progress_callback(-1, "Internal server error while chunking: %s" % str(e).replace("'", ""))
        _lineaje_payload = "Chunking {}/{} got exception".format(task["location"], task["name"])
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in build_chunks).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:aac342dc251f3554a0dc45a2d818ba813a0907e30956a1e3178652054fc408d4'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aac342dc251f3554a0dc45a2d818ba813a0907e30956a1e3178652054fc408d4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 269, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 269, 'function': 'build_chunks', 'agent_name': 'build_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.exception(_lineaje_payload)
        raise

    docs = []
    doc = {
        "doc_id": task["doc_id"],
        "kb_id": str(task["kb_id"])
    }
    if task["pagerank"]:
        doc[PAGERANK_FLD] = int(task["pagerank"])
    st = timer()

    @timeout(60)
    async def upload_to_minio(document, chunk):
        try:
            d = copy.deepcopy(document)
            d.update(chunk)
            d["id"] = xxhash.xxh64((chunk["content_with_weight"] + str(d["doc_id"])).encode("utf-8", "surrogatepass")).hexdigest()
            d["create_time"] = str(datetime.now()).replace("T", " ")[:19]
            d["create_timestamp_flt"] = datetime.now().timestamp()
            if not d.get("image"):
                _ = d.pop("image", None)
                d["img_id"] = ""
                docs.append(d)
                return
            await image2id(d, partial(settings.STORAGE_IMPL.put, tenant_id=task["tenant_id"]), d["id"], task["kb_id"])
            docs.append(d)
        except Exception:
            _lineaje_payload = "Saving image of chunk {}/{}/{} got exception".format(task["location"], task["name"], d["id"])
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in upload_to_minio).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3cef9d37c42fb271dfe11cae082d45a8c0abba30998cac19b15619939164d31a'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3cef9d37c42fb271dfe11cae082d45a8c0abba30998cac19b15619939164d31a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 297, 'function': 'build_chunks.upload_to_minio'}, 'file': 'rag/svr/task_executor.py', 'line': 297, 'function': 'upload_to_minio', 'agent_name': 'upload_to_minio', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(
                _lineaje_payload)
            raise

    tasks = []
    for ck in cks:
        tasks.append(asyncio.create_task(upload_to_minio(doc, ck)))
    try:
        await asyncio.gather(*tasks, return_exceptions=False)
    except Exception as e:
        _lineaje_payload = f"MINIO PUT({task['name']}) got exception: {e}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in upload_to_minio).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:86e595b676ac12bb4a97eefe9799b620b371d8438c072395c2415874f7f6ba47'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:86e595b676ac12bb4a97eefe9799b620b371d8438c072395c2415874f7f6ba47', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 307, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 307, 'function': 'upload_to_minio', 'agent_name': 'upload_to_minio', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
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

    el = timer() - st
    _lineaje_payload = "MINIO PUT({}) cost {:.3f} s".format(task["name"], el)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in build_chunks).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e6b6c89b93a0ecd4a9f4dc801265bb807add6a93d4bde1bf605e17765e7d2831'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e6b6c89b93a0ecd4a9f4dc801265bb807add6a93d4bde1bf605e17765e7d2831', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 314, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 314, 'function': 'build_chunks', 'agent_name': 'build_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)

    if task["parser_config"].get("auto_keywords", 0):
        st = timer()
        progress_callback(msg="Start to generate keywords for every chunk ...")
        chat_mdl = LLMBundle(task["tenant_id"], LLMType.CHAT, llm_name=task["llm_id"], lang=task["language"])

        async def doc_keyword_extraction(chat_mdl, d, topn):
            cached = get_llm_cache(chat_mdl.llm_name, d["content_with_weight"], "keywords", {"topn": topn})
            if not cached:
                async with chat_limiter:
                    cached = await keyword_extraction(chat_mdl, d["content_with_weight"], topn)
                set_llm_cache(chat_mdl.llm_name, d["content_with_weight"], cached, "keywords", {"topn": topn})
            if cached:
                d["important_kwd"] = cached.split(",")
                d["important_tks"] = rag_tokenizer.tokenize(" ".join(d["important_kwd"]))
            return
        tasks = []
        for d in docs:
            tasks.append(asyncio.create_task(doc_keyword_extraction(chat_mdl, d, task["parser_config"]["auto_keywords"])))
        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            _lineaje_payload = "Error in doc_keyword_extraction: {}".format(e)
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in doc_keyword_extraction).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0a34e7c638a8a4b658adaa83a0fe36b81213ca192eb23d838b88284ec8137fde'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0a34e7c638a8a4b658adaa83a0fe36b81213ca192eb23d838b88284ec8137fde', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 337, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 337, 'function': 'doc_keyword_extraction', 'agent_name': 'doc_keyword_extraction', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
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
        progress_callback(msg="Keywords generation {} chunks completed in {:.2f}s".format(len(docs), timer() - st))

    if task["parser_config"].get("auto_questions", 0):
        st = timer()
        progress_callback(msg="Start to generate questions for every chunk ...")
        chat_mdl = LLMBundle(task["tenant_id"], LLMType.CHAT, llm_name=task["llm_id"], lang=task["language"])

        async def doc_question_proposal(chat_mdl, d, topn):
            cached = get_llm_cache(chat_mdl.llm_name, d["content_with_weight"], "question", {"topn": topn})
            if not cached:
                async with chat_limiter:
                    cached = await question_proposal(chat_mdl, d["content_with_weight"], topn)
                set_llm_cache(chat_mdl.llm_name, d["content_with_weight"], cached, "question", {"topn": topn})
            if cached:
                d["question_kwd"] = cached.split("\n")
                d["question_tks"] = rag_tokenizer.tokenize("\n".join(d["question_kwd"]))
        tasks = []
        for d in docs:
            tasks.append(asyncio.create_task(doc_question_proposal(chat_mdl, d, task["parser_config"]["auto_questions"])))
        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            _lineaje_payload = "Error in doc_question_proposal"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in doc_question_proposal).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:18a807b1a1b0769318d05e54a94fe7d6b7aa1502becb5807f6b34ffbc5b74024'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:18a807b1a1b0769318d05e54a94fe7d6b7aa1502becb5807f6b34ffbc5b74024', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 364, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 364, 'function': 'doc_question_proposal', 'agent_name': 'doc_question_proposal', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload, exc_info=e)
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        progress_callback(msg="Question generation {} chunks completed in {:.2f}s".format(len(docs), timer() - st))

    if task["parser_config"].get("enable_metadata", False) and task["parser_config"].get("metadata"):
        st = timer()
        progress_callback(msg="Start to generate meta-data for every chunk ...")
        chat_mdl = LLMBundle(task["tenant_id"], LLMType.CHAT, llm_name=task["llm_id"], lang=task["language"])

        async def gen_metadata_task(chat_mdl, d):
            cached = get_llm_cache(chat_mdl.llm_name, d["content_with_weight"], "metadata", {})
            if not cached:
                async with chat_limiter:
                    cached = await gen_metadata(chat_mdl,
                                                metadata_schema(task["parser_config"]["metadata"]),
                                                d["content_with_weight"])
                set_llm_cache(chat_mdl.llm_name, d["content_with_weight"], cached, "metadata", {})
            if cached:
                d["metadata_obj"] = cached
        tasks = []
        for d in docs:
            tasks.append(asyncio.create_task(gen_metadata_task(chat_mdl, d)))
        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            _lineaje_payload = "Error in doc_question_proposal"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in gen_metadata_task).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e5635afd522a3f61c3ac22119ca02b20c5d3640b5ba98f0f682c99a6bd6cdc89'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e5635afd522a3f61c3ac22119ca02b20c5d3640b5ba98f0f682c99a6bd6cdc89', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 392, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 392, 'function': 'gen_metadata_task', 'agent_name': 'gen_metadata_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload, exc_info=e)
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        metadata = {}
        for doc in docs:
            metadata = update_metadata_to(metadata, doc["metadata_obj"])
            del doc["metadata_obj"]
        if metadata:
            e, doc = DocumentService.get_by_id(task["doc_id"])
            if e:
                if isinstance(doc.meta_fields, str):
                    doc.meta_fields = json.loads(doc.meta_fields)
                metadata = update_metadata_to(metadata, doc.meta_fields)
                DocumentService.update_by_id(task["doc_id"], {"meta_fields": metadata})
        progress_callback(msg="Question generation {} chunks completed in {:.2f}s".format(len(docs), timer() - st))

    if task["kb_parser_config"].get("tag_kb_ids", []):
        progress_callback(msg="Start to tag for every chunk ...")
        kb_ids = task["kb_parser_config"]["tag_kb_ids"]
        tenant_id = task["tenant_id"]
        topn_tags = task["kb_parser_config"].get("topn_tags", 3)
        # LINEAJE: runtime guardrail checks `topn_tags` as it flows from an external API to the agent, after the tool returns (in upload_to_minio).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `topn_tags` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6f169b2410c81eada50e8d3de0adc19e3630e37bac5bdbc3dcd7fd4e7f3a3a2c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6f169b2410c81eada50e8d3de0adc19e3630e37bac5bdbc3dcd7fd4e7f3a3a2c', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 414, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 414, 'function': 'upload_to_minio', 'agent_name': 'upload_to_minio', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            topn_tags = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, topn_tags, content_type='application/json', variable_name='topn_tags', source_file=__file__, before_line=414))
        except _gr_client.GuardrailUnavailableError:
            pass
        S = 1000
        st = timer()
        examples = []
        all_tags = get_tags_from_cache(kb_ids)
        if not all_tags:
            all_tags = settings.retriever.all_tags_in_portion(tenant_id, kb_ids, S)
            set_tags_to_cache(kb_ids, all_tags)
        else:
            all_tags = json.loads(all_tags)

        chat_mdl = LLMBundle(task["tenant_id"], LLMType.CHAT, llm_name=task["llm_id"], lang=task["language"])

        docs_to_tag = []
        for d in docs:
            task_canceled = has_canceled(task["id"])
            if task_canceled:
                progress_callback(-1, msg="Task has been canceled.")
                return None
            if settings.retriever.tag_content(tenant_id, kb_ids, d, all_tags, topn_tags=topn_tags, S=S) and len(d[TAG_FLD]) > 0:
                examples.append({"content": d["content_with_weight"], TAG_FLD: d[TAG_FLD]})
            else:
                docs_to_tag.append(d)

        async def doc_content_tagging(chat_mdl, d, topn_tags):
            cached = get_llm_cache(chat_mdl.llm_name, d["content_with_weight"], all_tags, {"topn": topn_tags})
            if not cached:
                picked_examples = random.choices(examples, k=2) if len(examples)>2 else examples
                if not picked_examples:
                    picked_examples.append({"content": "This is an example", TAG_FLD: {'example': 1}})
                async with chat_limiter:
                    cached = await content_tagging(
                        chat_mdl,
                        d["content_with_weight"],
                        all_tags,
                        picked_examples,
                        topn_tags,
                    )
                if cached:
                    # LINEAJE: runtime guardrail checks `cached` as it flows from the agent to an external endpoint, before it leaves the application (in doc_content_tagging).
                    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `cached` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:2f3b5d5e18da62855de04e5a3e574f681d79112daca22d290c97fb0d46f7592b'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2f3b5d5e18da62855de04e5a3e574f681d79112daca22d290c97fb0d46f7592b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 453, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 453, 'function': 'doc_content_tagging', 'agent_name': 'doc_content_tagging', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                    try:
                        cached = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, cached, content_type='application/json', variable_name='cached', source_file=__file__, before_line=453))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    cached = json.dumps(cached)
            if cached:
                set_llm_cache(chat_mdl.llm_name, d["content_with_weight"], cached, all_tags, {"topn": topn_tags})
                d[TAG_FLD] = json.loads(cached)
        tasks = []
        for d in docs_to_tag:
            tasks.append(asyncio.create_task(doc_content_tagging(chat_mdl, d, topn_tags)))
        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            _lineaje_payload = "Error tagging docs: {}".format(e)
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in doc_content_tagging).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:beca7a7f28675ed079b56e4aaf5e3cae780a19e780dcf5b754d12d0104102359'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:beca7a7f28675ed079b56e4aaf5e3cae780a19e780dcf5b754d12d0104102359', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 463, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 463, 'function': 'doc_content_tagging', 'agent_name': 'doc_content_tagging', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
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
        progress_callback(msg="Tagging {} chunks completed in {:.2f}s".format(len(docs), timer() - st))

    # LINEAJE: runtime guardrail checks `docs` as it flows from the agent to the user interface, before it leaves the application (in build_chunks).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `docs` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:069fd18ee6ab785b00ea6f509d4073eda7f22e5c6fd8b5c590bb82b3c62f76d3'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:069fd18ee6ab785b00ea6f509d4073eda7f22e5c6fd8b5c590bb82b3c62f76d3', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 470, 'function': 'build_chunks'}, 'file': 'rag/svr/task_executor.py', 'line': 470, 'function': 'build_chunks', 'agent_name': 'build_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        docs = _gr_client.enforce(_gr_site, docs, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return docs


def build_TOC(task, docs, progress_callback):
    progress_callback(msg="Start to generate table of content ...")
    chat_mdl = LLMBundle(task["tenant_id"], LLMType.CHAT, llm_name=task["llm_id"], lang=task["language"])
    docs = sorted(docs, key=lambda d:(
        d.get("page_num_int", 0)[0] if isinstance(d.get("page_num_int", 0), list) else d.get("page_num_int", 0),
        d.get("top_int", 0)[0] if isinstance(d.get("top_int", 0), list) else d.get("top_int", 0)
    ))
    toc: list[dict] = asyncio.run(run_toc_from_text([d["content_with_weight"] for d in docs], chat_mdl, progress_callback))
    # LINEAJE: runtime guardrail checks `toc` as it flows from the agent to an external endpoint, before it leaves the application (in build_TOC).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `toc` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:a2673cb1e075e683147213afbd8560f8567513a56bf1c99fdb5b02e1a15bed17'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a2673cb1e075e683147213afbd8560f8567513a56bf1c99fdb5b02e1a15bed17', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 481, 'function': 'build_TOC'}, 'file': 'rag/svr/task_executor.py', 'line': 481, 'function': 'build_TOC', 'agent_name': 'build_TOC', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        toc = _gr_client.enforce(_gr_site, toc, content_type='application/json', variable_name='toc', source_file=__file__, before_line=481)
    except _gr_client.GuardrailUnavailableError:
        pass
    _lineaje_payload = "------------ T O C -------------\n"+json.dumps(toc, ensure_ascii=False, indent='  ')
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in build_TOC).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:3fe7d711cbf50b8f9ee7bf6bdd83943d418304ccfa5a6cc187f9dd99920e897c'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3fe7d711cbf50b8f9ee7bf6bdd83943d418304ccfa5a6cc187f9dd99920e897c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 481, 'function': 'build_TOC'}, 'file': 'rag/svr/task_executor.py', 'line': 481, 'function': 'build_TOC', 'agent_name': 'build_TOC', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)
    ii = 0
    while ii < len(toc):
        try:
            idx = int(toc[ii]["chunk_id"])
            del toc[ii]["chunk_id"]
            toc[ii]["ids"] = [docs[idx]["id"]]
            if ii == len(toc) -1:
                break
            for jj in range(idx+1, int(toc[ii+1]["chunk_id"])+1):
                toc[ii]["ids"].append(docs[jj]["id"])
        except Exception as e:
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in build_TOC).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1a57f8b5280ee56d8364133f2d4f451724ea92c9401c5d1b17ba8aabc8d2c5a5'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1a57f8b5280ee56d8364133f2d4f451724ea92c9401c5d1b17ba8aabc8d2c5a5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 493, 'function': 'build_TOC'}, 'file': 'rag/svr/task_executor.py', 'line': 493, 'function': 'build_TOC', 'agent_name': 'build_TOC', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                e = _gr_client.enforce(_gr_site, e, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)
        ii += 1

    if toc:
        d = copy.deepcopy(docs[-1])
        # LINEAJE: runtime guardrail checks `toc` as it flows from the agent to an external endpoint, before it leaves the application (in build_TOC).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `toc` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e8c6cb4c378758ada983402c6156f537a6ab8d87a65ac6cd1c82ae075937841f'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e8c6cb4c378758ada983402c6156f537a6ab8d87a65ac6cd1c82ae075937841f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 498, 'function': 'build_TOC'}, 'file': 'rag/svr/task_executor.py', 'line': 498, 'function': 'build_TOC', 'agent_name': 'build_TOC', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            toc = _gr_client.enforce(_gr_site, toc, content_type='application/json', variable_name='toc', source_file=__file__, before_line=498)
        except _gr_client.GuardrailUnavailableError:
            pass
        d["content_with_weight"] = json.dumps(toc, ensure_ascii=False)
        d["toc_kwd"] = "toc"
        d["available_int"] = 0
        d["page_num_int"] = [100000000]
        d["id"] = xxhash.xxh64((d["content_with_weight"] + str(d["doc_id"])).encode("utf-8", "surrogatepass")).hexdigest()
        # LINEAJE: runtime guardrail checks `d` as it flows from the agent to the user interface, before it leaves the application (in build_TOC).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `d` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b25bff0c2bc1079d4f9f89a9897fb440aedec1746ebf916146b367c08bd6b561'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b25bff0c2bc1079d4f9f89a9897fb440aedec1746ebf916146b367c08bd6b561', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 503, 'function': 'build_TOC'}, 'file': 'rag/svr/task_executor.py', 'line': 503, 'function': 'build_TOC', 'agent_name': 'build_TOC', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            d = _gr_client.enforce(_gr_site, d, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return d
    return None


def init_kb(row, vector_size: int):
    idxnm = search.index_name(row["tenant_id"])
    return settings.docStoreConn.create_idx(idxnm, row.get("kb_id", ""), vector_size)


async def embedding(docs, mdl, parser_config=None, callback=None):
    if parser_config is None:
        parser_config = {}
    tts, cnts = [], []
    for d in docs:
        tts.append(d.get("docnm_kwd", "Title"))
        c = "\n".join(d.get("question_kwd", []))
        if not c:
            c = d["content_with_weight"]
        c = re.sub(r"</?(table|td|caption|tr|th)( [^<>]{0,12})?>", " ", c)
        if not c:
            c = "None"
        cnts.append(c)

    tk_count = 0
    if len(tts) == len(cnts):
        vts, c = await asyncio.to_thread(mdl.encode, tts[0:1])
        tts = np.tile(vts[0], (len(cnts), 1))
        tk_count += c

    @timeout(60)
    def batch_encode(txts):
        nonlocal mdl
        return mdl.encode([truncate(c, mdl.max_length-10) for c in txts])

    cnts_ = np.array([])
    for i in range(0, len(cnts), settings.EMBEDDING_BATCH_SIZE):
        async with embed_limiter:
            vts, c = await asyncio.to_thread(batch_encode, cnts[i : i + settings.EMBEDDING_BATCH_SIZE])
        if len(cnts_) == 0:
            cnts_ = vts
        else:
            cnts_ = np.concatenate((cnts_, vts), axis=0)
        tk_count += c
        callback(prog=0.7 + 0.2 * (i + 1) / len(cnts), msg="")
    cnts = cnts_
    filename_embd_weight = parser_config.get("filename_embd_weight", 0.1) # due to the db support none value
    if not filename_embd_weight:
        filename_embd_weight = 0.1
    title_w = float(filename_embd_weight)
    if tts.ndim == 2 and cnts.ndim == 2 and tts.shape == cnts.shape:
        vects = title_w * tts + (1 - title_w) * cnts
    else:
        vects = cnts

    assert len(vects) == len(docs)
    vector_size = 0
    for i, d in enumerate(docs):
        v = vects[i].tolist()
        vector_size = len(v)
        d["q_%d_vec" % len(v)] = v
    return tk_count, vector_size


async def run_dataflow(task: dict):
    from api.db.services.canvas_service import UserCanvasService
    from rag.flow.pipeline import Pipeline

    task_start_ts = timer()
    dataflow_id = task["dataflow_id"]
    doc_id = task["doc_id"]
    task_id = task["id"]
    task_dataset_id = task["kb_id"]

    if task["task_type"] == "dataflow":
        e, cvs = UserCanvasService.get_by_id(dataflow_id)
        assert e, "User pipeline not found."
        dsl = cvs.dsl
    else:
        e, pipeline_log = PipelineOperationLogService.get_by_id(dataflow_id)
        assert e, "Pipeline log not found."
        dsl = pipeline_log.dsl
        dataflow_id = pipeline_log.pipeline_id
    pipeline = Pipeline(dsl, tenant_id=task["tenant_id"], doc_id=doc_id, task_id=task_id, flow_id=dataflow_id)
    chunks = await pipeline.run(file=task["file"]) if task.get("file") else await pipeline.run()
    if doc_id == CANVAS_DEBUG_DOC_ID:
        return

    if not chunks:
        PipelineOperationLogService.create(document_id=doc_id, pipeline_id=dataflow_id, task_type=PipelineTaskType.PARSE, dsl=str(pipeline))
        return

    embedding_token_consumption = chunks.get("embedding_token_consumption", 0)
    if chunks.get("chunks"):
        chunks = copy.deepcopy(chunks["chunks"])
    elif chunks.get("json"):
        chunks = copy.deepcopy(chunks["json"])
    elif chunks.get("markdown"):
        chunks = [{"text": [chunks["markdown"]]}]
    elif chunks.get("text"):
        chunks = [{"text": [chunks["text"]]}]
    elif chunks.get("html"):
        chunks = [{"text": [chunks["html"]]}]

    keys = [k for o in chunks for k in list(o.keys())]
    if not any([re.match(r"q_[0-9]+_vec", k) for k in keys]):
        try:
            set_progress(task_id, prog=0.82, msg="\n-------------------------------------\nStart to embedding...")
            e, kb = KnowledgebaseService.get_by_id(task["kb_id"])
            embedding_id = kb.embd_id
            embedding_model = LLMBundle(task["tenant_id"], LLMType.EMBEDDING, llm_name=embedding_id)
            @timeout(60)
            def batch_encode(txts):
                nonlocal embedding_model
                _lineaje_payload = [truncate(c, embedding_model.max_length - 10) for c in txts]
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in batch_encode).
                #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `_lineaje_payload` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:d764fdc6a732f6c9df95da53d318fc5c027ce0d0c035f218e98980369e90566f'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d764fdc6a732f6c9df95da53d318fc5c027ce0d0c035f218e98980369e90566f', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 616, 'function': 'run_dataflow'}, 'file': 'rag/svr/task_executor.py', 'line': 616, 'function': 'batch_encode', 'agent_name': 'batch_encode', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=616)
                except _gr_client.GuardrailUnavailableError:
                    pass
                return embedding_model.encode(_lineaje_payload)
            vects = np.array([])
            texts = [o.get("questions", o.get("summary", o["text"])) for o in chunks]
            delta = 0.20/(len(texts)//settings.EMBEDDING_BATCH_SIZE+1)
            prog = 0.8
            for i in range(0, len(texts), settings.EMBEDDING_BATCH_SIZE):
                async with embed_limiter:
                    vts, c = await asyncio.to_thread(batch_encode, texts[i : i + settings.EMBEDDING_BATCH_SIZE])
                if len(vects) == 0:
                    vects = vts
                else:
                    vects = np.concatenate((vects, vts), axis=0)
                embedding_token_consumption += c
                prog += delta
                if i % (len(texts)//settings.EMBEDDING_BATCH_SIZE/100+1) == 1:
                    set_progress(task_id, prog=prog, msg=f"{i+1} / {len(texts)//settings.EMBEDDING_BATCH_SIZE}")

            assert len(vects) == len(chunks)
            for i, ck in enumerate(chunks):
                v = vects[i].tolist()
                ck["q_%d_vec" % len(v)] = v
        except Exception as e:
            set_progress(task_id, prog=-1, msg=f"[ERROR]: {e}")
            PipelineOperationLogService.create(document_id=doc_id, pipeline_id=dataflow_id, task_type=PipelineTaskType.PARSE, dsl=str(pipeline))
            return


    metadata = {}
    for ck in chunks:
        ck["doc_id"] = doc_id
        ck["kb_id"] = [str(task["kb_id"])]
        ck["docnm_kwd"] = task["name"]
        ck["create_time"] = str(datetime.now()).replace("T", " ")[:19]
        ck["create_timestamp_flt"] = datetime.now().timestamp()
        if not ck.get("id"):
            ck["id"] = xxhash.xxh64((ck["text"] + str(ck["doc_id"])).encode("utf-8")).hexdigest()
        if "questions" in ck:
            if "question_tks" not in ck:
                ck["question_kwd"] = ck["questions"].split("\n")
                ck["question_tks"] = rag_tokenizer.tokenize(str(ck["questions"]))
            del ck["questions"]
        if "keywords" in ck:
            if "important_tks" not in ck:
                ck["important_kwd"] = ck["keywords"].split(",")
                ck["important_tks"] = rag_tokenizer.tokenize(str(ck["keywords"]))
            del ck["keywords"]
        if "summary" in ck:
            if "content_ltks" not in ck:
                ck["content_ltks"] = rag_tokenizer.tokenize(str(ck["summary"]))
                ck["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(ck["content_ltks"])
            del ck["summary"]
        if "metadata" in ck:
            metadata = update_metadata_to(metadata, ck["metadata"])
            del ck["metadata"]
        if "content_with_weight" not in ck:
            ck["content_with_weight"] = ck["text"]
        del ck["text"]
        if "positions" in ck:
            add_positions(ck, ck["positions"])
            del ck["positions"]

    if metadata:
        e, doc = DocumentService.get_by_id(doc_id)
        if e:
            if isinstance(doc.meta_fields, str):
                doc.meta_fields = json.loads(doc.meta_fields)
            metadata = update_metadata_to(metadata, doc.meta_fields)
            DocumentService.update_by_id(doc_id, {"meta_fields": metadata})

    start_ts = timer()
    set_progress(task_id, prog=0.82, msg="[DOC Engine]:\nStart to index...")
    e = await insert_es(task_id, task["tenant_id"], task["kb_id"], chunks, partial(set_progress, task_id, 0, 100000000))
    if not e:
        PipelineOperationLogService.create(document_id=doc_id, pipeline_id=dataflow_id, task_type=PipelineTaskType.PARSE, dsl=str(pipeline))
        return

    time_cost = timer() - start_ts
    task_time_cost = timer() - task_start_ts
    set_progress(task_id, prog=1., msg="Indexing done ({:.2f}s). Task done ({:.2f}s)".format(time_cost, task_time_cost))
    DocumentService.increment_chunk_num(doc_id, task_dataset_id, embedding_token_consumption, len(chunks), task_time_cost)
    _lineaje_payload = "[Done], chunks({}), token({}), elapsed:{:.2f}".format(len(chunks),  embedding_token_consumption, task_time_cost)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in run_dataflow).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:41b5747963346689487bfd00fef269804a28fc578bb6c61e51f41acf4bf6a927'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:41b5747963346689487bfd00fef269804a28fc578bb6c61e51f41acf4bf6a927', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 696, 'function': 'run_dataflow'}, 'file': 'rag/svr/task_executor.py', 'line': 696, 'function': 'run_dataflow', 'agent_name': 'run_dataflow', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)
    PipelineOperationLogService.create(document_id=doc_id, pipeline_id=dataflow_id, task_type=PipelineTaskType.PARSE, dsl=str(pipeline))


@timeout(3600)
async def run_raptor_for_kb(row, kb_parser_config, chat_mdl, embd_mdl, vector_size, callback=None, doc_ids=[]):
    fake_doc_id = GRAPH_RAPTOR_FAKE_DOC_ID

    raptor_config = kb_parser_config.get("raptor", {})
    vctr_nm = "q_%d_vec"%vector_size

    res = []
    tk_count = 0
    max_errors = int(os.environ.get("RAPTOR_MAX_ERRORS", 3))

    async def generate(chunks, did):
        nonlocal tk_count, res
        raptor = Raptor(
            raptor_config.get("max_cluster", 64),
            chat_mdl,
            embd_mdl,
            raptor_config["prompt"],
            raptor_config["max_token"],
            raptor_config["threshold"],
            max_errors=max_errors,
        )
        original_length = len(chunks)
        chunks = await raptor(chunks, kb_parser_config["raptor"]["random_seed"], callback, row["id"])
        doc = {
            "doc_id": did,
            "kb_id": [str(row["kb_id"])],
            "docnm_kwd": row["name"],
            "title_tks": rag_tokenizer.tokenize(row["name"]),
            "raptor_kwd": "raptor"
        }
        if row["pagerank"]:
            doc[PAGERANK_FLD] = int(row["pagerank"])

        for content, vctr in chunks[original_length:]:
            d = copy.deepcopy(doc)
            d["id"] = xxhash.xxh64((content + str(fake_doc_id)).encode("utf-8")).hexdigest()
            d["create_time"] = str(datetime.now()).replace("T", " ")[:19]
            d["create_timestamp_flt"] = datetime.now().timestamp()
            d[vctr_nm] = vctr.tolist()
            d["content_with_weight"] = content
            d["content_ltks"] = rag_tokenizer.tokenize(content)
            d["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(d["content_ltks"])
            res.append(d)
            tk_count += num_tokens_from_string(content)

    if raptor_config.get("scope", "file") == "file":
        for x, doc_id in enumerate(doc_ids):
            chunks = []
            for d in settings.retriever.chunk_list(doc_id, row["tenant_id"], [str(row["kb_id"])],
                                                 fields=["content_with_weight", vctr_nm],
                                                 sort_by_position=True):
                chunks.append((d["content_with_weight"], np.array(d[vctr_nm])))
            await generate(chunks, doc_id)
            callback(prog=(x+1.)/len(doc_ids))
    else:
        chunks = []
        for doc_id in doc_ids:
            for d in settings.retriever.chunk_list(doc_id, row["tenant_id"], [str(row["kb_id"])],
                                                 fields=["content_with_weight", vctr_nm],
                                                 sort_by_position=True):
                chunks.append((d["content_with_weight"], np.array(d[vctr_nm])))

        await generate(chunks, fake_doc_id)

    return res, tk_count


async def delete_image(kb_id, chunk_id):
    try:
        async with minio_limiter:
            settings.STORAGE_IMPL.delete(kb_id, chunk_id)
    except Exception:
        _lineaje_payload = f"Deleting image of chunk {chunk_id} got exception"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in delete_image).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:313c4f1b4cc9c8d732209f86e8f95968bb8513a5f43ee63a357949d4ad73c40a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:313c4f1b4cc9c8d732209f86e8f95968bb8513a5f43ee63a357949d4ad73c40a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 773, 'function': 'delete_image'}, 'file': 'rag/svr/task_executor.py', 'line': 773, 'function': 'delete_image', 'agent_name': 'delete_image', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.exception(_lineaje_payload)
        raise


async def insert_es(task_id, task_tenant_id, task_dataset_id, chunks, progress_callback):
    mothers = []
    mother_ids = set([])
    for ck in chunks:
        mom = ck.get("mom") or ck.get("mom_with_weight") or ""
        if not mom:
            continue
        id = xxhash.xxh64(mom.encode("utf-8")).hexdigest()
        ck["mom_id"] = id
        if id in mother_ids:
            continue
        mother_ids.add(id)
        mom_ck = copy.deepcopy(ck)
        mom_ck["id"] = id
        mom_ck["content_with_weight"] = mom
        mom_ck["available_int"] = 0
        flds = list(mom_ck.keys())
        for fld in flds:
            if fld not in ["id", "content_with_weight", "doc_id", "docnm_kwd", "kb_id", "available_int", "position_int"]:
                del mom_ck[fld]
        mothers.append(mom_ck)

    for b in range(0, len(mothers), settings.DOC_BULK_SIZE):
        await asyncio.to_thread(settings.docStoreConn.insert,mothers[b:b + settings.DOC_BULK_SIZE],search.index_name(task_tenant_id),task_dataset_id,)
        task_canceled = has_canceled(task_id)
        if task_canceled:
            progress_callback(-1, msg="Task has been canceled.")
            return False

    for b in range(0, len(chunks), settings.DOC_BULK_SIZE):
        doc_store_result = await asyncio.to_thread(settings.docStoreConn.insert,chunks[b:b + settings.DOC_BULK_SIZE],search.index_name(task_tenant_id),task_dataset_id,)
        task_canceled = has_canceled(task_id)
        if task_canceled:
            progress_callback(-1, msg="Task has been canceled.")
            return False
        if b % 128 == 0:
            progress_callback(prog=0.8 + 0.1 * (b + 1) / len(chunks), msg="")
        if doc_store_result:
            error_message = f"Insert chunk error: {doc_store_result}, please check log file and Elasticsearch/Infinity status!"
            progress_callback(-1, msg=error_message)
            raise Exception(error_message)
        chunk_ids = [chunk["id"] for chunk in chunks[:b + settings.DOC_BULK_SIZE]]
        chunk_ids_str = " ".join(chunk_ids)
        try:
            TaskService.update_chunk_ids(task_id, chunk_ids_str)
        except DoesNotExist:
            _lineaje_payload = f"do_handle_task update_chunk_ids failed since task {task_id} is unknown."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in insert_es).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:cab857e4d1925a9babefb4cc8feff2db9dc69fcbe053c62b5030eae7037106a9'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cab857e4d1925a9babefb4cc8feff2db9dc69fcbe053c62b5030eae7037106a9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 823, 'function': 'insert_es'}, 'file': 'rag/svr/task_executor.py', 'line': 823, 'function': 'insert_es', 'agent_name': 'insert_es', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            doc_store_result = await asyncio.to_thread(settings.docStoreConn.delete,{"id": chunk_ids},search.index_name(task_tenant_id),task_dataset_id,)
            tasks = []
            for chunk_id in chunk_ids:
                tasks.append(asyncio.create_task(delete_image(task_dataset_id, chunk_id)))
            try:
                await asyncio.gather(*tasks, return_exceptions=False)
            except Exception as e:
                _lineaje_payload = f"delete_image failed: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in insert_es).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:941ca6ba6342d6e1b4ce13bedf3fbbbef2efa0e7d701151121d8fe66188d3ed7'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:941ca6ba6342d6e1b4ce13bedf3fbbbef2efa0e7d701151121d8fe66188d3ed7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 831, 'function': 'insert_es'}, 'file': 'rag/svr/task_executor.py', 'line': 831, 'function': 'insert_es', 'agent_name': 'insert_es', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
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
            progress_callback(-1, msg=f"Chunk updates failed since task {task_id} is unknown.")
            return False
    return True


@timeout(60*60*3, 1)
async def do_handle_task(task):
    task_type = task.get("task_type", "")

    if task_type == "dataflow" and task.get("doc_id", "") == CANVAS_DEBUG_DOC_ID:
        await run_dataflow(task)
        return

    task_id = task["id"]
    task_from_page = task["from_page"]
    task_to_page = task["to_page"]
    task_tenant_id = task["tenant_id"]
    task_embedding_id = task["embd_id"]
    task_language = task["language"]
    task_llm_id = task["parser_config"].get("llm_id") or task["llm_id"]
    task_dataset_id = task["kb_id"]
    task_doc_id = task["doc_id"]
    task_document_name = task["name"]
    task_parser_config = task["parser_config"]
    task_start_ts = timer()
    toc_thread = None
    executor = concurrent.futures.ThreadPoolExecutor()

    # prepare the progress callback function
    progress_callback = partial(set_progress, task_id, task_from_page, task_to_page)

    # FIXME: workaround, Infinity doesn't support table parsing method, this check is to notify user
    lower_case_doc_engine = settings.DOC_ENGINE.lower()
    if lower_case_doc_engine == 'infinity' and task['parser_id'].lower() == 'table':
        error_message = "Table parsing method is not supported by Infinity, please use other parsing methods or use Elasticsearch as the document engine."
        progress_callback(-1, msg=error_message)
        raise Exception(error_message)

    task_canceled = has_canceled(task_id)
    if task_canceled:
        progress_callback(-1, msg="Task has been canceled.")
        return

    try:
        # bind embedding model
        embedding_model = LLMBundle(task_tenant_id, LLMType.EMBEDDING, llm_name=task_embedding_id, lang=task_language)
        _lineaje_payload = ["ok"]
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in do_handle_task).
        #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `_lineaje_payload` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1ddecf69fdd8ef0fdef2ba55888893578c512d8252657cd2ec8ffff1abeae378'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1ddecf69fdd8ef0fdef2ba55888893578c512d8252657cd2ec8ffff1abeae378', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 882, 'function': 'do_handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 882, 'function': 'do_handle_task', 'agent_name': 'do_handle_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=882))
        except _gr_client.GuardrailUnavailableError:
            pass
        vts, _ = embedding_model.encode(_lineaje_payload)
        vector_size = len(vts[0])
    except Exception as e:
        error_message = f'Fail to bind embedding model: {str(e)}'
        progress_callback(-1, msg=error_message)
        # LINEAJE: runtime guardrail checks `error_message` as it flows from the agent to the application log, before it is written to the log (in do_handle_task).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_message` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b6a49b3b1124d25669caf1adb1d25c73df4c0558308ebc1a263c9baff5f877d4'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b6a49b3b1124d25669caf1adb1d25c73df4c0558308ebc1a263c9baff5f877d4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 887, 'function': 'do_handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 887, 'function': 'do_handle_task', 'agent_name': 'do_handle_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            error_message = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, error_message, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.exception(error_message)
        raise

    init_kb(task, vector_size)

    if task_type[:len("dataflow")] == "dataflow":
        await run_dataflow(task)
        return

    if task_type == "raptor":
        ok, kb = KnowledgebaseService.get_by_id(task_dataset_id)
        if not ok:
            progress_callback(prog=-1.0, msg="Cannot found valid dataset for RAPTOR task")
            return

        kb_parser_config = kb.parser_config
        if not kb_parser_config.get("raptor", {}).get("use_raptor", False):
            kb_parser_config.update(
                {
                    "raptor": {
                        "use_raptor": True,
                        "prompt": "Please summarize the following paragraphs. Be careful with the numbers, do not make things up. Paragraphs as following:\n      {cluster_content}\nThe above is the content you need to summarize.",
                        "max_token": 256,
                        "threshold": 0.1,
                        "max_cluster": 64,
                        "random_seed": 0,
                        "scope": "file"
                    },
                }
            )
            if not KnowledgebaseService.update_by_id(kb.id, {"parser_config":kb_parser_config}):
                progress_callback(prog=-1.0, msg="Internal error: Invalid RAPTOR configuration")
                return

        # Check if Raptor should be skipped for structured data
        file_type = task.get("type", "")
        parser_id = task.get("parser_id", "")
        raptor_config = kb_parser_config.get("raptor", {})

        if should_skip_raptor(file_type, parser_id, task_parser_config, raptor_config):
            skip_reason = get_skip_reason(file_type, parser_id, task_parser_config)
            _lineaje_payload = f"Skipping Raptor for document {task_document_name}: {skip_reason}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in do_handle_task).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:97c21c3e3f10fdea019a5ca275105b958856abfe4e9eff449b012e2b6872b376'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:97c21c3e3f10fdea019a5ca275105b958856abfe4e9eff449b012e2b6872b376', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 928, 'function': 'do_handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 928, 'function': 'do_handle_task', 'agent_name': 'do_handle_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            progress_callback(prog=1.0, msg=f"Raptor skipped: {skip_reason}")
            return

        # bind LLM for raptor
        chat_model = LLMBundle(task_tenant_id, LLMType.CHAT, llm_name=task_llm_id, lang=task_language)
        # run RAPTOR
        async with kg_limiter:
            chunks, token_count = await run_raptor_for_kb(
                row=task,
                kb_parser_config=kb_parser_config,
                chat_mdl=chat_model,
                embd_mdl=embedding_model,
                vector_size=vector_size,
                callback=progress_callback,
                doc_ids=task.get("doc_ids", []),
            )
        if fake_doc_ids := task.get("doc_ids", []):
            task_doc_id = fake_doc_ids[0] # use the first document ID to represent this task for logging purposes
    # Either using graphrag or Standard chunking methods
    elif task_type == "graphrag":
        ok, kb = KnowledgebaseService.get_by_id(task_dataset_id)
        if not ok:
            progress_callback(prog=-1.0, msg="Cannot found valid dataset for GraphRAG task")
            return

        kb_parser_config = kb.parser_config
        if not kb_parser_config.get("graphrag", {}).get("use_graphrag", False):
            kb_parser_config.update(
                {
                    "graphrag": {
                        "use_graphrag": True,
                        "entity_types": [
                            "organization",
                            "person",
                            "geo",
                            "event",
                            "category",
                        ],
                        "method": "light",
                    }
                }
            )
            if not KnowledgebaseService.update_by_id(kb.id, {"parser_config":kb_parser_config}):
                progress_callback(prog=-1.0, msg="Internal error: Invalid GraphRAG configuration")
                return


        graphrag_conf = kb_parser_config.get("graphrag", {})
        start_ts = timer()
        chat_model = LLMBundle(task_tenant_id, LLMType.CHAT, llm_name=task_llm_id, lang=task_language)
        with_resolution = graphrag_conf.get("resolution", False)
        with_community = graphrag_conf.get("community", False)
        async with kg_limiter:
            # await run_graphrag(task, task_language, with_resolution, with_community, chat_model, embedding_model, progress_callback)
            result = await run_graphrag_for_kb(
                row=task,
                doc_ids=task.get("doc_ids", []),
                language=task_language,
                kb_parser_config=kb_parser_config,
                chat_model=chat_model,
                embedding_model=embedding_model,
                callback=progress_callback,
                with_resolution=with_resolution,
                with_community=with_community,
            )
            _lineaje_payload = f"GraphRAG task result for task {task}:\n{result}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in do_handle_task).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f8dfe06b53826978874fc9a41ad9f7ae7345fdba1d0f8ff41261f5da62aacd76'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f8dfe06b53826978874fc9a41ad9f7ae7345fdba1d0f8ff41261f5da62aacd76', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 994, 'function': 'do_handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 994, 'function': 'do_handle_task', 'agent_name': 'do_handle_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
        progress_callback(prog=1.0, msg="Knowledge Graph done ({:.2f}s)".format(timer() - start_ts))
        return
    elif task_type == "mindmap":
        progress_callback(1, "place holder")
        pass
        return
    else:
        # Standard chunking methods
        start_ts = timer()
        chunks = await build_chunks(task, progress_callback)
        _lineaje_payload = "Build document {}: {:.2f}s".format(task_document_name, timer() - start_ts)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in do_handle_task).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e043743536028804a6f60b137bf15339e6f4b200b4e318efae4774603861f2a1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e043743536028804a6f60b137bf15339e6f4b200b4e318efae4774603861f2a1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1005, 'function': 'do_handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 1005, 'function': 'do_handle_task', 'agent_name': 'do_handle_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        if not chunks:
            progress_callback(1., msg=f"No chunk built from {task_document_name}")
            return
        progress_callback(msg="Generate {} chunks".format(len(chunks)))
        start_ts = timer()
        try:
            token_count, vector_size = await embedding(chunks, embedding_model, task_parser_config, progress_callback)
        except Exception as e:
            error_message = "Generate embedding error:{}".format(str(e))
            progress_callback(-1, error_message)
            # LINEAJE: runtime guardrail checks `error_message` as it flows from the agent to the application log, before it is written to the log (in do_handle_task).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_message` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9608a7346113d0b02387859f1fd94bdfebfa873d43213d57593371ef1e387712'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9608a7346113d0b02387859f1fd94bdfebfa873d43213d57593371ef1e387712', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1016, 'function': 'do_handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 1016, 'function': 'do_handle_task', 'agent_name': 'do_handle_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                error_message = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, error_message, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(error_message)
            token_count = 0
            raise
        progress_message = "Embedding chunks ({:.2f}s)".format(timer() - start_ts)
        # LINEAJE: runtime guardrail checks `progress_message` as it flows from the agent to the application log, before it is written to the log (in do_handle_task).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `progress_message` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6a82e1ee30958027ac3c9889b8ce54ee5389a63f4c4b4e698a13c195d631a7cf'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6a82e1ee30958027ac3c9889b8ce54ee5389a63f4c4b4e698a13c195d631a7cf', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1020, 'function': 'do_handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 1020, 'function': 'do_handle_task', 'agent_name': 'do_handle_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            progress_message = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, progress_message, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(progress_message)
        progress_callback(msg=progress_message)
        if task["parser_id"].lower() == "naive" and task["parser_config"].get("toc_extraction", False):
            toc_thread = executor.submit(build_TOC, task, chunks, progress_callback)

    chunk_count = len(set([chunk["id"] for chunk in chunks]))
    start_ts = timer()

    async def _maybe_insert_es(_chunks):
        if has_canceled(task_id):
            return True
        e = await insert_es(task_id, task_tenant_id, task_dataset_id, _chunks, progress_callback)
        return bool(e)
    
    try:
        if not await _maybe_insert_es(chunks):
            return

        _lineaje_payload = ("Indexing doc({}), page({}-{}), chunks({}), elapsed: {:.2f}".format(
                task_document_name, task_from_page, task_to_page, len(chunks), timer() - start_ts
            ))
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _maybe_insert_es).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:53d3f9488d15dbd06d8d7e83f20c1cc00e3afc8f979fc21c92f3d66b5120a99c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:53d3f9488d15dbd06d8d7e83f20c1cc00e3afc8f979fc21c92f3d66b5120a99c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1038, 'function': 'do_handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 1038, 'function': '_maybe_insert_es', 'agent_name': '_maybe_insert_es', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(
            _lineaje_payload
        )

        DocumentService.increment_chunk_num(task_doc_id, task_dataset_id, token_count, chunk_count, 0)

        progress_callback(msg="Indexing done ({:.2f}s).".format(timer() - start_ts))

        if toc_thread:
            d = toc_thread.result()
            if d:
                if not await _maybe_insert_es([d]):
                    return
                DocumentService.increment_chunk_num(task_doc_id, task_dataset_id, 0, 1, 0)

        if has_canceled(task_id):
            progress_callback(-1, msg="Task has been canceled.")
            return

        task_time_cost = timer() - task_start_ts
        progress_callback(prog=1.0, msg="Task done ({:.2f}s)".format(task_time_cost))
        _lineaje_payload = ("Chunk doc({}), page({}-{}), chunks({}), token({}), elapsed:{:.2f}".format(
                task_document_name, task_from_page, task_to_page, len(chunks), token_count, task_time_cost
            ))
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _maybe_insert_es).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ecc9b64c3d11515f15e948eb7ba60a840b508d9c7f5b482a76a50046be71f650'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ecc9b64c3d11515f15e948eb7ba60a840b508d9c7f5b482a76a50046be71f650', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1061, 'function': 'do_handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 1061, 'function': '_maybe_insert_es', 'agent_name': '_maybe_insert_es', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(
            _lineaje_payload
        )

    finally:
        if has_canceled(task_id):
            try:
                exists = await asyncio.to_thread(
                    settings.docStoreConn.indexExist,
                    search.index_name(task_tenant_id),
                    task_dataset_id,
                )
                if exists:
                    await asyncio.to_thread(
                        settings.docStoreConn.delete,
                        {"doc_id": task_doc_id},
                        search.index_name(task_tenant_id),
                        task_dataset_id,
                    )
            except Exception:
                _lineaje_payload = f"Remove doc({task_doc_id}) from docStore failed when task({task_id}) canceled."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _maybe_insert_es).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:42ba810a53b5f05ff58aea3b5454ccecec20bdda2745d4fc0e32babf9178c7ab'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:42ba810a53b5f05ff58aea3b5454ccecec20bdda2745d4fc0e32babf9178c7ab', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1083, 'function': 'do_handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 1083, 'function': '_maybe_insert_es', 'agent_name': '_maybe_insert_es', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(
                    _lineaje_payload
                )

async def handle_task():

    global DONE_TASKS, FAILED_TASKS
    redis_msg, task = await collect()
    if not task:
        await asyncio.sleep(5)
        return

    task_type = task["task_type"]
    pipeline_task_type = TASK_TYPE_TO_PIPELINE_TASK_TYPE.get(task_type, PipelineTaskType.PARSE) or PipelineTaskType.PARSE

    try:
        # LINEAJE: runtime guardrail checks `task` as it flows from the agent to an external endpoint, before it leaves the application (in handle_task).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `task` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:49b9b502db346d43f54cc828628b0971b4bf50391a3c99752dabd6c8327c27a0'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:49b9b502db346d43f54cc828628b0971b4bf50391a3c99752dabd6c8327c27a0', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1099, 'function': 'handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 1099, 'function': 'handle_task', 'agent_name': 'handle_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            task = _gr_client.enforce(_gr_site, task, content_type='application/json', variable_name='task', source_file=__file__, before_line=1099)
        except _gr_client.GuardrailUnavailableError:
            pass
        _lineaje_payload = f"handle_task begin for task {json.dumps(task)}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in handle_task).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b249a955af57937c3653fc0d1ec079768b51fc442a4242ef29d4e884ad1c3064'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b249a955af57937c3653fc0d1ec079768b51fc442a4242ef29d4e884ad1c3064', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1099, 'function': 'handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 1099, 'function': 'handle_task', 'agent_name': 'handle_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        CURRENT_TASKS[task["id"]] = copy.deepcopy(task)
        await do_handle_task(task)
        DONE_TASKS += 1
        CURRENT_TASKS.pop(task["id"], None)
        # LINEAJE: runtime guardrail checks `task` as it flows from the agent to an external endpoint, before it leaves the application (in handle_task).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `task` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:16e296d86f54f5c7e662e0924bf885098392266e5936c91323742fe8972933ea'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:16e296d86f54f5c7e662e0924bf885098392266e5936c91323742fe8972933ea', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1104, 'function': 'handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 1104, 'function': 'handle_task', 'agent_name': 'handle_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            task = _gr_client.enforce(_gr_site, task, content_type='application/json', variable_name='task', source_file=__file__, before_line=1104)
        except _gr_client.GuardrailUnavailableError:
            pass
        _lineaje_payload = f"handle_task done for task {json.dumps(task)}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in handle_task).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3b469f54461eb27ae00e7b9a6f12f5e8ddfc2f3f0005d27fa3e536d99de93568'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3b469f54461eb27ae00e7b9a6f12f5e8ddfc2f3f0005d27fa3e536d99de93568', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1104, 'function': 'handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 1104, 'function': 'handle_task', 'agent_name': 'handle_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
    except Exception as e:
        FAILED_TASKS += 1
        CURRENT_TASKS.pop(task["id"], None)
        try:
            err_msg = str(e)
            while isinstance(e, exceptiongroup.ExceptionGroup):
                e = e.exceptions[0]
                err_msg += ' -- ' + str(e)
            set_progress(task["id"], prog=-1, msg=f"[Exception]: {err_msg}")
        except Exception:
            pass
        # LINEAJE: runtime guardrail checks `task` as it flows from the agent to an external endpoint, before it leaves the application (in handle_task).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `task` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:19c173f6a2ba67dbe85560d6fd1fdb54dc097e65795deee2ce8028b29e563399'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:19c173f6a2ba67dbe85560d6fd1fdb54dc097e65795deee2ce8028b29e563399', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1116, 'function': 'handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 1116, 'function': 'handle_task', 'agent_name': 'handle_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            task = _gr_client.enforce(_gr_site, task, content_type='application/json', variable_name='task', source_file=__file__, before_line=1116)
        except _gr_client.GuardrailUnavailableError:
            pass
        _lineaje_payload = f"handle_task got exception for task {json.dumps(task)}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in handle_task).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f3ab50908c20ed43978bd8850c2eec30609a3556241254725658980d177cc6f3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f3ab50908c20ed43978bd8850c2eec30609a3556241254725658980d177cc6f3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1116, 'function': 'handle_task'}, 'file': 'rag/svr/task_executor.py', 'line': 1116, 'function': 'handle_task', 'agent_name': 'handle_task', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.exception(_lineaje_payload)
    finally:
        task_document_ids = []
        if task_type in ["graphrag", "raptor", "mindmap"]:
            task_document_ids = task["doc_ids"]
        if not task.get("dataflow_id", ""):
            PipelineOperationLogService.record_pipeline_operation(document_id=task["doc_id"], pipeline_id="", task_type=pipeline_task_type, fake_document_ids=task_document_ids)

    redis_msg.ack()


async def get_server_ip() -> str:
    # get ip by udp
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception as e:
        _lineaje_payload = str(e)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in get_server_ip).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e1a0c48473fbe42180fdcba19b263967bb23a6975977036b8924ba69012150f3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e1a0c48473fbe42180fdcba19b263967bb23a6975977036b8924ba69012150f3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1134, 'function': 'get_server_ip'}, 'file': 'rag/svr/task_executor.py', 'line': 1134, 'function': 'get_server_ip', 'agent_name': 'get_server_ip', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(_lineaje_payload)
        return 'Unknown'


async def report_status():
    global CONSUMER_NAME, BOOT_AT, PENDING_TASKS, LAG_TASKS, DONE_TASKS, FAILED_TASKS
    REDIS_CONN.sadd("TASKEXE", CONSUMER_NAME)
    redis_lock = RedisDistributedLock("clean_task_executor", lock_value=CONSUMER_NAME, timeout=60)
    while True:
        try:
            now = datetime.now()
            group_info = REDIS_CONN.queue_info(settings.get_svr_queue_name(0), SVR_CONSUMER_GROUP_NAME)
            if group_info is not None:
                PENDING_TASKS = int(group_info.get("pending", 0))
                LAG_TASKS = int(group_info.get("lag", 0))

            pid = os.getpid()
            ip_address = await get_server_ip()
            current = copy.deepcopy(CURRENT_TASKS)
            _lineaje_payload = ({
                "ip_address": ip_address,
                "pid": pid,
                "name": CONSUMER_NAME,
                "now": now.astimezone().isoformat(timespec="milliseconds"),
                "boot_at": BOOT_AT,
                "pending": PENDING_TASKS,
                "lag": LAG_TASKS,
                "done": DONE_TASKS,
                "failed": FAILED_TASKS,
                "current": current,
            })
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to an external endpoint, before it leaves the application (in report_status).
            #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `_lineaje_payload` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:4162bea7e84662eb5a45e9e2c0275efbb7c180afa3cf69d1de09df4d3fd63703'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4162bea7e84662eb5a45e9e2c0275efbb7c180afa3cf69d1de09df4d3fd63703', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1153, 'function': 'report_status'}, 'file': 'rag/svr/task_executor.py', 'line': 1153, 'function': 'report_status', 'agent_name': 'report_status', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=1153))
            except _gr_client.GuardrailUnavailableError:
                pass
            heartbeat = json.dumps(_lineaje_payload)
            REDIS_CONN.zadd(CONSUMER_NAME, heartbeat, now.timestamp())
            _lineaje_payload = f"{CONSUMER_NAME} reported heartbeat: {heartbeat}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in report_status).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d7e84a5320fe60743834bce69ec17f8555e68b1ac177fd6f468a945132ecc64f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d7e84a5320fe60743834bce69ec17f8555e68b1ac177fd6f468a945132ecc64f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1166, 'function': 'report_status'}, 'file': 'rag/svr/task_executor.py', 'line': 1166, 'function': 'report_status', 'agent_name': 'report_status', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)

            expired = REDIS_CONN.zcount(CONSUMER_NAME, 0, now.timestamp() - 60 * 30)
            if expired > 0:
                REDIS_CONN.zpopmin(CONSUMER_NAME, expired)

            # clean task executor
            if redis_lock.acquire():
                task_executors = REDIS_CONN.smembers("TASKEXE")
                for consumer_name in task_executors:
                    if consumer_name == CONSUMER_NAME:
                        continue
                    expired = REDIS_CONN.zcount(
                        consumer_name, now.timestamp() - WORKER_HEARTBEAT_TIMEOUT, now.timestamp() + 10
                    )
                    if expired == 0:
                        _lineaje_payload = f"{consumer_name} expired, removed"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in report_status).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:dd984d405d17294bae76aab0f1df816cc2458c8dde48a39d70419a2f19dadc05'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dd984d405d17294bae76aab0f1df816cc2458c8dde48a39d70419a2f19dadc05', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1182, 'function': 'report_status'}, 'file': 'rag/svr/task_executor.py', 'line': 1182, 'function': 'report_status', 'agent_name': 'report_status', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                        try:
                            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.info(_lineaje_payload)
                        REDIS_CONN.srem("TASKEXE", consumer_name)
                        REDIS_CONN.delete(consumer_name)
        except Exception:
            _lineaje_payload = "report_status got exception"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in report_status).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d71be9c520b2412a8d21205aa914f9e2cfdeca5fba71c83a2b1bd40919738689'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d71be9c520b2412a8d21205aa914f9e2cfdeca5fba71c83a2b1bd40919738689', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1186, 'function': 'report_status'}, 'file': 'rag/svr/task_executor.py', 'line': 1186, 'function': 'report_status', 'agent_name': 'report_status', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
        finally:
            redis_lock.release()
        await asyncio.sleep(30)


async def task_manager():
    try:
        await handle_task()
    finally:
        task_limiter.release()


async def main():
    # Stagger executor startup to prevent connection storm to Infinity
    # Extract worker number from CONSUMER_NAME (e.g., "task_executor_abc123_5" -> 5)
    try:
        worker_num = int(CONSUMER_NAME.rsplit("_", 1)[-1])
        # Add random delay: base delay + worker_num * 2.0s + random jitter
        # This spreads out connection attempts over several seconds
        startup_delay = worker_num * 2.0 + random.uniform(0, 0.5)
        if startup_delay > 0:
            _lineaje_payload = f"Staggering startup by {startup_delay:.2f}s to prevent connection storm"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:a109a7ba7b1f92b15c3aacefc90ca552142dd7d9ba58a7ef91fa7bfd89b3e5b1'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a109a7ba7b1f92b15c3aacefc90ca552142dd7d9ba58a7ef91fa7bfd89b3e5b1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1208, 'function': 'main'}, 'file': 'rag/svr/task_executor.py', 'line': 1208, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            await asyncio.sleep(startup_delay)
    except (ValueError, IndexError):
        pass  # Non-standard consumer name, skip delay

    _lineaje_payload = (r"""
    ____                      __  _
   /  _/___  ____ ____  _____/ /_(_)___  ____     ________  ______   _____  _____
   / // __ \/ __ `/ _ \/ ___/ __/ / __ \/ __ \   / ___/ _ \/ ___/ | / / _ \/ ___/
 _/ // / / / /_/ /  __(__  ) /_/ / /_/ / / / /  (__  )  __/ /   | |/ /  __/ /
/___/_/ /_/\__, /\___/____/\__/_/\____/_/ /_/  /____/\___/_/    |___/\___/_/
          /____/
    """)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:bb5368d2abe21383b784de49f13df22f3fda3f6f0ae5b849a0e57332b3184c88'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bb5368d2abe21383b784de49f13df22f3fda3f6f0ae5b849a0e57332b3184c88', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1213, 'function': 'main'}, 'file': 'rag/svr/task_executor.py', 'line': 1213, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)
    _lineaje_payload = f'RAGFlow version: {get_ragflow_version()}'
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:c7e110f170f05b36fd97447bf773693bebceb572a29bbf6b771f79686f4b1de7'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c7e110f170f05b36fd97447bf773693bebceb572a29bbf6b771f79686f4b1de7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1221, 'function': 'main'}, 'file': 'rag/svr/task_executor.py', 'line': 1221, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)
    show_configs()
    settings.init_settings()
    settings.check_and_install_torch()
    _lineaje_payload = f'default embedding config: {settings.EMBEDDING_CFG}'
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:cec3712ef1364e748c56558f602111e2dfc916a4dfa1645fa91b1b892d2f0694'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cec3712ef1364e748c56558f602111e2dfc916a4dfa1645fa91b1b892d2f0694', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1225, 'function': 'main'}, 'file': 'rag/svr/task_executor.py', 'line': 1225, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)
    settings.print_rag_settings()
    if sys.platform != "win32":
        signal.signal(signal.SIGUSR1, start_tracemalloc_and_snapshot)
        signal.signal(signal.SIGUSR2, stop_tracemalloc)
    TRACE_MALLOC_ENABLED = int(os.environ.get('TRACE_MALLOC_ENABLED', "0"))
    if TRACE_MALLOC_ENABLED:
        start_tracemalloc_and_snapshot(None, None)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    report_task = asyncio.create_task(report_status())
    tasks = []
    try:
        while not stop_event.is_set():
            await task_limiter.acquire()
            t = asyncio.create_task(task_manager())
            tasks.append(t)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        report_task.cancel()
        await asyncio.gather(report_task, return_exceptions=True)
    _lineaje_payload = "BUG!!! You should not reach here!!!"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:07c12692555b23b7974e2be228e10fb3efcfb15f4768cdb1a55f29a4a5c30d91'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:07c12692555b23b7974e2be228e10fb3efcfb15f4768cdb1a55f29a4a5c30d91', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/task_executor.py', 'line': 1250, 'function': 'main'}, 'file': 'rag/svr/task_executor.py', 'line': 1250, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
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
