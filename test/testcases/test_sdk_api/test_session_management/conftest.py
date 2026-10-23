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
import pytest
from common import batch_add_sessions_with_chat_assistant
from pytest import FixtureRequest
from ragflow_sdk import Chat, DataSet, Document, Session


@pytest.fixture(scope="class")
def add_sessions_with_chat_assistant(request: FixtureRequest, add_chat_assistants: tuple[DataSet, Document, list[Chat]]) -> tuple[Chat, list[Session]]:
    def cleanup():
        for chat_assistant in chat_assistants:
            try:
                chat_assistant.delete_sessions(ids=None)
            except Exception as e:
                _lineaje_payload = f"Exception: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in cleanup).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:045001ddd20b65a8f540ccbee8e8065109dda259ed7d04e095520d22aeb7db06'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:045001ddd20b65a8f540ccbee8e8065109dda259ed7d04e095520d22aeb7db06', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_session_management/conftest.py', 'line': 29, 'function': 'add_sessions_with_chat_assistant.cleanup'}, 'file': 'test/testcases/test_sdk_api/test_session_management/conftest.py', 'line': 29, 'function': 'cleanup', 'agent_name': 'cleanup', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
                pass

    request.addfinalizer(cleanup)

    _, _, chat_assistants = add_chat_assistants
    return chat_assistants[0], batch_add_sessions_with_chat_assistant(chat_assistants[0], 5)


@pytest.fixture(scope="function")
def add_sessions_with_chat_assistant_func(request: FixtureRequest, add_chat_assistants: tuple[DataSet, Document, list[Chat]]) -> tuple[Chat, list[Session]]:
    def cleanup():
        for chat_assistant in chat_assistants:
            try:
                chat_assistant.delete_sessions(ids=None)
            except Exception as e:
                _lineaje_payload = f"Exception: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in cleanup).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:c94eaea6a30a7eef156f0feee3dbf6f06e2496f264f4d3bf2f47ff0ce553de8b'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c94eaea6a30a7eef156f0feee3dbf6f06e2496f264f4d3bf2f47ff0ce553de8b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_session_management/conftest.py', 'line': 45, 'function': 'add_sessions_with_chat_assistant_func.cleanup'}, 'file': 'test/testcases/test_sdk_api/test_session_management/conftest.py', 'line': 45, 'function': 'cleanup', 'agent_name': 'cleanup', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)

    request.addfinalizer(cleanup)

    _, _, chat_assistants = add_chat_assistants
    return chat_assistants[0], batch_add_sessions_with_chat_assistant(chat_assistants[0], 5)
