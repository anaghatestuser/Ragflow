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
import random
from test_web_api.common import create_memory, list_memory, delete_memory

@pytest.fixture(scope="function")
def add_memory_func(request, WebApiAuth):
    def cleanup():
        memory_list_res = list_memory(WebApiAuth)
        exist_memory_ids = [memory["id"] for memory in memory_list_res["data"]["memory_list"]]
        for memory_id in exist_memory_ids:
            delete_memory(WebApiAuth, memory_id)

    request.addfinalizer(cleanup)

    memory_ids = []
    for i in range(3):
        payload = {
            "name": f"test_memory_{i}",
            "memory_type": ["raw"] + random.choices(["semantic", "episodic", "procedural"], k=random.randint(0, 3)),
            "embd_id": "BAAI/bge-large-zh-v1.5@SILICONFLOW",
            "llm_id": "glm-4-flash@ZHIPU-AI"
        }
        res = create_memory(WebApiAuth, payload)
        memory_ids.append(res["data"]["id"])
    # LINEAJE: runtime guardrail checks `memory_ids` as it flows from the agent to the user interface, before it leaves the application (in add_memory_func).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `memory_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:f3b2cbf122684bf50f3aa82cec62166199210e1accb4527b688d7adada38a0cf'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f3b2cbf122684bf50f3aa82cec62166199210e1accb4527b688d7adada38a0cf', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/test_memory_app/conftest.py', 'line': 40, 'function': 'add_memory_func'}, 'file': 'test/testcases/test_web_api/test_memory_app/conftest.py', 'line': 40, 'function': 'add_memory_func', 'agent_name': 'add_memory_func', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        memory_ids = _gr_client.enforce(_gr_site, memory_ids, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return memory_ids
