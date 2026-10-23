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
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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

from pathlib import Path

from ragflow_sdk import Chat, Chunk, DataSet, Document, RAGFlow, Session
from utils.file_utils import create_txt_file


# DATASET MANAGEMENT
def batch_create_datasets(client: RAGFlow, num: int) -> list[DataSet]:
    return [client.create_dataset(name=f"dataset_{i}") for i in range(num)]


# FILE MANAGEMENT WITHIN DATASET
def bulk_upload_documents(dataset: DataSet, num: int, tmp_path: Path) -> list[Document]:
    document_infos = []
    for i in range(num):
        fp = create_txt_file(tmp_path / f"ragflow_test_upload_{i}.txt")
        with fp.open("rb") as f:
            blob = f.read()
            # LINEAJE: runtime guardrail checks `blob` as it flows from file storage to the agent (in bulk_upload_documents).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `blob` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:c2ae9cb947ba2e5b8edc115f8ef45ba2369697995e803e9ff22fe5a31b065ec4'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c2ae9cb947ba2e5b8edc115f8ef45ba2369697995e803e9ff22fe5a31b065ec4', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/common.py', 'line': 34, 'function': 'bulk_upload_documents'}, 'file': 'test/testcases/test_sdk_api/common.py', 'line': 34, 'function': 'bulk_upload_documents', 'agent_name': 'bulk_upload_documents', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                blob = _gr_client.enforce(_gr_site, blob, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
        document_infos.append({"display_name": fp.name, "blob": blob})

    return dataset.upload_documents(document_infos)


# CHUNK MANAGEMENT WITHIN DATASET
def batch_add_chunks(document: Document, num: int) -> list[Chunk]:
    return [document.add_chunk(content=f"chunk test {i}") for i in range(num)]


# CHAT ASSISTANT MANAGEMENT
def batch_create_chat_assistants(client: RAGFlow, num: int) -> list[Chat]:
    return [client.create_chat(name=f"test_chat_assistant_{i}") for i in range(num)]


# SESSION MANAGEMENT
def batch_add_sessions_with_chat_assistant(chat_assistant: Chat, num) -> list[Session]:
    return [chat_assistant.create_session(name=f"session_with_chat_assistant_{i}") for i in range(num)]
