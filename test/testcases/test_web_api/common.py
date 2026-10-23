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

import requests
from configs import HOST_ADDRESS, VERSION
from requests_toolbelt import MultipartEncoder
from utils.file_utils import create_txt_file

HEADERS = {"Content-Type": "application/json"}

KB_APP_URL = f"/{VERSION}/kb"
DOCUMENT_APP_URL = f"/{VERSION}/document"
CHUNK_API_URL = f"/{VERSION}/chunk"
DIALOG_APP_URL = f"/{VERSION}/dialog"
# SESSION_WITH_CHAT_ASSISTANT_API_URL = "/api/v1/chats/{chat_id}/sessions"
# SESSION_WITH_AGENT_API_URL = "/api/v1/agents/{agent_id}/sessions"
MEMORY_API_URL = f"/{VERSION}/memories"


# KB APP
def create_kb(auth, payload=None, *, headers=HEADERS, data=None):
    res = requests.post(url=f"{HOST_ADDRESS}{KB_APP_URL}/create", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in create_kb).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:199cc6f8440f999e1a85e25ec393ed998f48abfb20a54b0bc324df2156116e43'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:199cc6f8440f999e1a85e25ec393ed998f48abfb20a54b0bc324df2156116e43', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 36, 'function': 'create_kb'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 36, 'function': 'create_kb', 'agent_name': 'create_kb', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=36)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def list_kbs(auth, params=None, payload=None, *, headers=HEADERS, data=None):
    if payload is None:
        payload = {}
    res = requests.post(url=f"{HOST_ADDRESS}{KB_APP_URL}/list", headers=headers, auth=auth, params=params, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in list_kbs).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:2822450205e3a40c532d963d36446d577c825f713f8aaad4d189ffbb56457bc3'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2822450205e3a40c532d963d36446d577c825f713f8aaad4d189ffbb56457bc3', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 43, 'function': 'list_kbs'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 43, 'function': 'list_kbs', 'agent_name': 'list_kbs', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=43)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def update_kb(auth, payload=None, *, headers=HEADERS, data=None):
    res = requests.post(url=f"{HOST_ADDRESS}{KB_APP_URL}/update", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in update_kb).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:055cc16756dcdbd77167d61183170b4d7db70efd23015fdc2c23b681aedd8cdb'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:055cc16756dcdbd77167d61183170b4d7db70efd23015fdc2c23b681aedd8cdb', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 48, 'function': 'update_kb'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 48, 'function': 'update_kb', 'agent_name': 'update_kb', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=48)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def rm_kb(auth, payload=None, *, headers=HEADERS, data=None):
    res = requests.post(url=f"{HOST_ADDRESS}{KB_APP_URL}/rm", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in rm_kb).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:baabc66cb7df0b781c465aa42f7de9eb6143c9294c2b50b93203b7870e0da374'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:baabc66cb7df0b781c465aa42f7de9eb6143c9294c2b50b93203b7870e0da374', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 53, 'function': 'rm_kb'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 53, 'function': 'rm_kb', 'agent_name': 'rm_kb', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=53)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def detail_kb(auth, params=None, *, headers=HEADERS):
    res = requests.get(url=f"{HOST_ADDRESS}{KB_APP_URL}/detail", headers=headers, auth=auth, params=params)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in detail_kb).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:b5af08c2d96010852037f615621f55bccd7717958d8625cee454baaf967ea88e'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b5af08c2d96010852037f615621f55bccd7717958d8625cee454baaf967ea88e', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 58, 'function': 'detail_kb'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 58, 'function': 'detail_kb', 'agent_name': 'detail_kb', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=58)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def list_tags_from_kbs(auth, params=None, *, headers=HEADERS):
    res = requests.get(url=f"{HOST_ADDRESS}{KB_APP_URL}/tags", headers=headers, auth=auth, params=params)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in list_tags_from_kbs).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:627446669c796abe61fd9a0aadf5d0e3c4c4293cdb618571771247b021a68da5'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:627446669c796abe61fd9a0aadf5d0e3c4c4293cdb618571771247b021a68da5', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 63, 'function': 'list_tags_from_kbs'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 63, 'function': 'list_tags_from_kbs', 'agent_name': 'list_tags_from_kbs', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=63)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def list_tags(auth, dataset_id, params=None, *, headers=HEADERS):
    res = requests.get(url=f"{HOST_ADDRESS}{KB_APP_URL}/{dataset_id}/tags", headers=headers, auth=auth, params=params)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in list_tags).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:74bee2f891540149c45e11e70d256d788680d44ecbb62b521a142b173b8ec1bd'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:74bee2f891540149c45e11e70d256d788680d44ecbb62b521a142b173b8ec1bd', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 68, 'function': 'list_tags'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 68, 'function': 'list_tags', 'agent_name': 'list_tags', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=68)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def rm_tags(auth, dataset_id, payload=None, *, headers=HEADERS, data=None):
    res = requests.post(url=f"{HOST_ADDRESS}{KB_APP_URL}/{dataset_id}/rm_tags", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in rm_tags).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:08b3cfde2009114bea0f498ffb93abc6429574e8ca6b4687df2b03381e50ea15'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:08b3cfde2009114bea0f498ffb93abc6429574e8ca6b4687df2b03381e50ea15', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 73, 'function': 'rm_tags'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 73, 'function': 'rm_tags', 'agent_name': 'rm_tags', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=73)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def rename_tags(auth, dataset_id, payload=None, *, headers=HEADERS, data=None):
    res = requests.post(url=f"{HOST_ADDRESS}{KB_APP_URL}/{dataset_id}/rename_tags", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in rename_tags).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:0081d70c83308605521c13c7784541df1f82af5868c8fae51155704172001d42'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0081d70c83308605521c13c7784541df1f82af5868c8fae51155704172001d42', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 78, 'function': 'rename_tags'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 78, 'function': 'rename_tags', 'agent_name': 'rename_tags', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=78)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def knowledge_graph(auth, dataset_id, params=None, *, headers=HEADERS):
    res = requests.get(url=f"{HOST_ADDRESS}{KB_APP_URL}/{dataset_id}/knowledge_graph", headers=headers, auth=auth, params=params)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in knowledge_graph).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:597a2cf90929aa84ce24eae9f2e3b3072dd397f2be8992be14f85ad08e81ffa8'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:597a2cf90929aa84ce24eae9f2e3b3072dd397f2be8992be14f85ad08e81ffa8', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 83, 'function': 'knowledge_graph'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 83, 'function': 'knowledge_graph', 'agent_name': 'knowledge_graph', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=83)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def delete_knowledge_graph(auth, dataset_id, payload=None, *, headers=HEADERS, data=None):
    res = requests.delete(url=f"{HOST_ADDRESS}{KB_APP_URL}/{dataset_id}/delete_knowledge_graph", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in delete_knowledge_graph).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:ccd18ad1d8d2167a2792a9a7af2ab73df8011fe04f03b2756bb917eb7b793cc5'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ccd18ad1d8d2167a2792a9a7af2ab73df8011fe04f03b2756bb917eb7b793cc5', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 88, 'function': 'delete_knowledge_graph'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 88, 'function': 'delete_knowledge_graph', 'agent_name': 'delete_knowledge_graph', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=88)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def batch_create_datasets(auth, num):
    ids = []
    for i in range(num):
        res = create_kb(auth, {"name": f"kb_{i}"})
        ids.append(res["data"]["kb_id"])
    # LINEAJE: runtime guardrail checks `ids` as it flows from the agent to the user interface, before it leaves the application (in batch_create_datasets).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:40a3492dc0ee2c48b912e8ef0f866e9c2b032ae9063afd6cc75959924f2a75d8'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:40a3492dc0ee2c48b912e8ef0f866e9c2b032ae9063afd6cc75959924f2a75d8', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 97, 'function': 'batch_create_datasets'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 97, 'function': 'batch_create_datasets', 'agent_name': 'batch_create_datasets', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        ids = _gr_client.enforce(_gr_site, ids, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return ids


# DOCUMENT APP
def upload_documents(auth, payload=None, files_path=None):
    url = f"{HOST_ADDRESS}{DOCUMENT_APP_URL}/upload"

    if files_path is None:
        files_path = []

    fields = []
    file_objects = []
    try:
        if payload:
            for k, v in payload.items():
                fields.append((k, str(v)))

        for fp in files_path:
            p = Path(fp)
            f = p.open("rb")
            fields.append(("file", (p.name, f)))
            file_objects.append(f)
        m = MultipartEncoder(fields=fields)

        res = requests.post(
            url=url,
            headers={"Content-Type": m.content_type},
            auth=auth,
            data=m,
        )
        # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in upload_documents).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:2840a7ff141fcb92a972ab44266eeacdf59ab601514e78638655659c128e25e1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2840a7ff141fcb92a972ab44266eeacdf59ab601514e78638655659c128e25e1', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 121, 'function': 'upload_documents'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 121, 'function': 'upload_documents', 'agent_name': 'upload_documents', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=121)
        except _gr_client.GuardrailUnavailableError:
            pass
        return res.json()
    finally:
        for f in file_objects:
            f.close()


def create_document(auth, payload=None, *, headers=HEADERS, data=None):
    res = requests.post(url=f"{HOST_ADDRESS}{DOCUMENT_APP_URL}/create", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in create_document).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:b221418113dbeba6cbab87c0cdc74f4db8145ebe7ec2e1c16c7b7ac98ef3681c'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b221418113dbeba6cbab87c0cdc74f4db8145ebe7ec2e1c16c7b7ac98ef3681c', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 134, 'function': 'create_document'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 134, 'function': 'create_document', 'agent_name': 'create_document', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=134)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def list_documents(auth, params=None, payload=None, *, headers=HEADERS, data=None):
    if payload is None:
        payload = {}
    res = requests.post(url=f"{HOST_ADDRESS}{DOCUMENT_APP_URL}/list", headers=headers, auth=auth, params=params, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in list_documents).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:71d3958084c4a374ae89eed2590bd272179fe8da01845b70696cded8aad859a7'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:71d3958084c4a374ae89eed2590bd272179fe8da01845b70696cded8aad859a7', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 141, 'function': 'list_documents'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 141, 'function': 'list_documents', 'agent_name': 'list_documents', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=141)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def delete_document(auth, payload=None, *, headers=HEADERS, data=None):
    res = requests.post(url=f"{HOST_ADDRESS}{DOCUMENT_APP_URL}/rm", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in delete_document).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:9330179cd59d0d6ca16c1d49ab1be0767664aa489043c2d0f67768e0c240ddde'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9330179cd59d0d6ca16c1d49ab1be0767664aa489043c2d0f67768e0c240ddde', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 146, 'function': 'delete_document'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 146, 'function': 'delete_document', 'agent_name': 'delete_document', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=146)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def parse_documents(auth, payload=None, *, headers=HEADERS, data=None):
    res = requests.post(url=f"{HOST_ADDRESS}{DOCUMENT_APP_URL}/run", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in parse_documents).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:6a0c69e347c3889a8165c572dc7e7512a9c581497c5b88f46b76604ab1604f9d'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6a0c69e347c3889a8165c572dc7e7512a9c581497c5b88f46b76604ab1604f9d', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 151, 'function': 'parse_documents'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 151, 'function': 'parse_documents', 'agent_name': 'parse_documents', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=151)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def bulk_upload_documents(auth, kb_id, num, tmp_path):
    fps = []
    for i in range(num):
        fp = create_txt_file(tmp_path / f"ragflow_test_upload_{i}.txt")
        fps.append(fp)

    res = upload_documents(auth, {"kb_id": kb_id}, fps)
    document_ids = []
    for document in res["data"]:
        document_ids.append(document["id"])
    # LINEAJE: runtime guardrail checks `document_ids` as it flows from the agent to the user interface, before it leaves the application (in bulk_upload_documents).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `document_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:f6c38c8260a7246797365ac089db7f92e9d8a82b92a7b2745aec4e91bb6f2c2c'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f6c38c8260a7246797365ac089db7f92e9d8a82b92a7b2745aec4e91bb6f2c2c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 165, 'function': 'bulk_upload_documents'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 165, 'function': 'bulk_upload_documents', 'agent_name': 'bulk_upload_documents', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        document_ids = _gr_client.enforce(_gr_site, document_ids, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return document_ids


# CHUNK APP
def add_chunk(auth, payload=None, *, headers=HEADERS, data=None):
    res = requests.post(url=f"{HOST_ADDRESS}{CHUNK_API_URL}/create", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in add_chunk).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:601f923df425a12f546684dbd8e58a740921c0a3170382071d578ace262ed50d'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:601f923df425a12f546684dbd8e58a740921c0a3170382071d578ace262ed50d', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 170, 'function': 'add_chunk'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 170, 'function': 'add_chunk', 'agent_name': 'add_chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=170)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def list_chunks(auth, payload=None, *, headers=HEADERS):
    res = requests.post(url=f"{HOST_ADDRESS}{CHUNK_API_URL}/list", headers=headers, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in list_chunks).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:a5977027e605b8643c7612f42f426ecb803a236a2e6d2be3c76ff361e770d3d0'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a5977027e605b8643c7612f42f426ecb803a236a2e6d2be3c76ff361e770d3d0', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 175, 'function': 'list_chunks'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 175, 'function': 'list_chunks', 'agent_name': 'list_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=175)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def get_chunk(auth, params=None, *, headers=HEADERS):
    res = requests.get(url=f"{HOST_ADDRESS}{CHUNK_API_URL}/get", headers=headers, auth=auth, params=params)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in get_chunk).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:2e7459ea8c3d534c8d48bc319679094fb7d9fa3d7e344280087f5af03e7af27f'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2e7459ea8c3d534c8d48bc319679094fb7d9fa3d7e344280087f5af03e7af27f', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 180, 'function': 'get_chunk'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 180, 'function': 'get_chunk', 'agent_name': 'get_chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=180)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def update_chunk(auth, payload=None, *, headers=HEADERS):
    res = requests.post(url=f"{HOST_ADDRESS}{CHUNK_API_URL}/set", headers=headers, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in update_chunk).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:cb8d37e46500c8814c70223b93fb5a5b5e2b8f93a408c4cdc7b6c6f3e2660596'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cb8d37e46500c8814c70223b93fb5a5b5e2b8f93a408c4cdc7b6c6f3e2660596', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 185, 'function': 'update_chunk'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 185, 'function': 'update_chunk', 'agent_name': 'update_chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=185)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def delete_chunks(auth, payload=None, *, headers=HEADERS):
    res = requests.post(url=f"{HOST_ADDRESS}{CHUNK_API_URL}/rm", headers=headers, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in delete_chunks).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:2e3c3a66050565d2e276642fd60aa82fb3a81461620664ec7cba5ee7985cc922'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2e3c3a66050565d2e276642fd60aa82fb3a81461620664ec7cba5ee7985cc922', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 190, 'function': 'delete_chunks'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 190, 'function': 'delete_chunks', 'agent_name': 'delete_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=190)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def retrieval_chunks(auth, payload=None, *, headers=HEADERS):
    res = requests.post(url=f"{HOST_ADDRESS}{CHUNK_API_URL}/retrieval_test", headers=headers, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in retrieval_chunks).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:edd2a928ac643c6bcf18ad5d696d678091568e2a84c8d30637905a418b3a0ae3'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:edd2a928ac643c6bcf18ad5d696d678091568e2a84c8d30637905a418b3a0ae3', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 195, 'function': 'retrieval_chunks'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 195, 'function': 'retrieval_chunks', 'agent_name': 'retrieval_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=195)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def batch_add_chunks(auth, doc_id, num):
    chunk_ids = []
    for i in range(num):
        res = add_chunk(auth, {"doc_id": doc_id, "content_with_weight": f"chunk test {i}"})
        chunk_ids.append(res["data"]["chunk_id"])
    # LINEAJE: runtime guardrail checks `chunk_ids` as it flows from the agent to the user interface, before it leaves the application (in batch_add_chunks).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `chunk_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:bc9074ae8a23daedf907d504209cf13a38020a66265481298ff032f9bc6ba85a'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bc9074ae8a23daedf907d504209cf13a38020a66265481298ff032f9bc6ba85a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 204, 'function': 'batch_add_chunks'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 204, 'function': 'batch_add_chunks', 'agent_name': 'batch_add_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        chunk_ids = _gr_client.enforce(_gr_site, chunk_ids, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return chunk_ids


# DIALOG APP
def create_dialog(auth, payload=None, *, headers=HEADERS, data=None):
    res = requests.post(url=f"{HOST_ADDRESS}{DIALOG_APP_URL}/set", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in create_dialog).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:f29c45cc3bac5eb5e0a04ef3981363033c683a647913e691aca7c21bc39ea317'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f29c45cc3bac5eb5e0a04ef3981363033c683a647913e691aca7c21bc39ea317', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 209, 'function': 'create_dialog'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 209, 'function': 'create_dialog', 'agent_name': 'create_dialog', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=209)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def update_dialog(auth, payload=None, *, headers=HEADERS, data=None):
    res = requests.post(url=f"{HOST_ADDRESS}{DIALOG_APP_URL}/set", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in update_dialog).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:3a263da7f02cb81659362dacbc95bdf82aef7787d95941b922332408af61a30f'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3a263da7f02cb81659362dacbc95bdf82aef7787d95941b922332408af61a30f', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 214, 'function': 'update_dialog'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 214, 'function': 'update_dialog', 'agent_name': 'update_dialog', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=214)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def get_dialog(auth, params=None, *, headers=HEADERS):
    res = requests.get(url=f"{HOST_ADDRESS}{DIALOG_APP_URL}/get", headers=headers, auth=auth, params=params)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in get_dialog).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e26caab43d429fc2afea61426550a645833db746aa4dd9d0ca11c9813b3012a3'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e26caab43d429fc2afea61426550a645833db746aa4dd9d0ca11c9813b3012a3', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 219, 'function': 'get_dialog'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 219, 'function': 'get_dialog', 'agent_name': 'get_dialog', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=219)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def list_dialogs(auth, *, headers=HEADERS):
    res = requests.get(url=f"{HOST_ADDRESS}{DIALOG_APP_URL}/list", headers=headers, auth=auth)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in list_dialogs).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:64f329d90cc9fa7f6cac751690872b51368b2b6cdc3beb68a179f8ad84765b42'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:64f329d90cc9fa7f6cac751690872b51368b2b6cdc3beb68a179f8ad84765b42', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 224, 'function': 'list_dialogs'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 224, 'function': 'list_dialogs', 'agent_name': 'list_dialogs', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=224)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def delete_dialog(auth, payload=None, *, headers=HEADERS, data=None):
    res = requests.post(url=f"{HOST_ADDRESS}{DIALOG_APP_URL}/rm", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in delete_dialog).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:6a4eae724eab2fb46eeaac580c34e6a6c07823d1a3fcadcd9df2400c8f76a9e0'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6a4eae724eab2fb46eeaac580c34e6a6c07823d1a3fcadcd9df2400c8f76a9e0', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 229, 'function': 'delete_dialog'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 229, 'function': 'delete_dialog', 'agent_name': 'delete_dialog', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=229)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def batch_create_dialogs(auth, num, kb_ids=None):
    if kb_ids is None:
        kb_ids = []

    dialog_ids = []
    for i in range(num):
        payload = {
            "name": f"dialog_{i}",
            "description": f"Test dialog {i}",
            "kb_ids": kb_ids,
            "prompt_config": {"system": "You are a helpful assistant. Use the following knowledge to answer questions: {knowledge}", "parameters": [{"key": "knowledge", "optional": False}]},
            "top_n": 6,
            "top_k": 1024,
            "similarity_threshold": 0.1,
            "vector_similarity_weight": 0.3,
            "llm_setting": {"model": "gpt-3.5-turbo", "temperature": 0.7},
        }
        res = create_dialog(auth, payload)
        if res["code"] == 0:
            dialog_ids.append(res["data"]["id"])
    # LINEAJE: runtime guardrail checks `dialog_ids` as it flows from the agent to the user interface, before it leaves the application (in batch_create_dialogs).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `dialog_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:ac0a2f4b59cfb477e409a662d4445bace097acd70a33efa9fca2a33b23242d95'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ac0a2f4b59cfb477e409a662d4445bace097acd70a33efa9fca2a33b23242d95', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 253, 'function': 'batch_create_dialogs'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 253, 'function': 'batch_create_dialogs', 'agent_name': 'batch_create_dialogs', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        dialog_ids = _gr_client.enforce(_gr_site, dialog_ids, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return dialog_ids


def delete_dialogs(auth):
    res = list_dialogs(auth)
    if res["code"] == 0 and res["data"]:
        dialog_ids = [dialog["id"] for dialog in res["data"]]
        if dialog_ids:
            delete_dialog(auth, {"dialog_ids": dialog_ids})

# MEMORY APP
def create_memory(auth, payload=None):
    url = f"{HOST_ADDRESS}{MEMORY_API_URL}"
    res = requests.post(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in create_memory).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:f6d66ff4e2d2dea06db9ff5b0c65213121001b205e2366cfdd9156f1b01bdac9'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f6d66ff4e2d2dea06db9ff5b0c65213121001b205e2366cfdd9156f1b01bdac9', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 266, 'function': 'create_memory'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 266, 'function': 'create_memory', 'agent_name': 'create_memory', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=266)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def update_memory(auth, memory_id:str, payload=None):
    url = f"{HOST_ADDRESS}{MEMORY_API_URL}/{memory_id}"
    res = requests.put(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in update_memory).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:5e7f0a1280a947f76a1fbd8f9eac2d3ff7f5accf14075ca11b7411885180abd8'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5e7f0a1280a947f76a1fbd8f9eac2d3ff7f5accf14075ca11b7411885180abd8', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 272, 'function': 'update_memory'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 272, 'function': 'update_memory', 'agent_name': 'update_memory', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=272)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def delete_memory(auth, memory_id:str):
    url = f"{HOST_ADDRESS}{MEMORY_API_URL}/{memory_id}"
    res = requests.delete(url=url, headers=HEADERS, auth=auth)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in delete_memory).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:d43b366f567a0a15bbb4b155267e10d84ba705e5e1d6dbded5ac53b04d866bc8'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d43b366f567a0a15bbb4b155267e10d84ba705e5e1d6dbded5ac53b04d866bc8', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 278, 'function': 'delete_memory'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 278, 'function': 'delete_memory', 'agent_name': 'delete_memory', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=278)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def list_memory(auth, params=None):
    url = f"{HOST_ADDRESS}{MEMORY_API_URL}"
    if params:
        query_parts = []
        for key, value in params.items():
            if isinstance(value, list):
                for item in value:
                    query_parts.append(f"{key}={item}")
            else:
                query_parts.append(f"{key}={value}")
        query_string = "&".join(query_parts)
        url = f"{url}?{query_string}"
    res = requests.get(url=url, headers=HEADERS, auth=auth)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in list_memory).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:6a5aa8807c5d9cd9fd88e32ea6ee1e8549a716824b9b081151dc7c91ffedf5c0'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6a5aa8807c5d9cd9fd88e32ea6ee1e8549a716824b9b081151dc7c91ffedf5c0', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 294, 'function': 'list_memory'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 294, 'function': 'list_memory', 'agent_name': 'list_memory', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=294)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def get_memory_config(auth, memory_id:str):
    url = f"{HOST_ADDRESS}{MEMORY_API_URL}/{memory_id}/config"
    res = requests.get(url=url, headers=HEADERS, auth=auth)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in get_memory_config).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:c4840175d53e074a92681fa27f5cbe95bf542104852d91e992c19b105d7907d3'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c4840175d53e074a92681fa27f5cbe95bf542104852d91e992c19b105d7907d3', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/common.py', 'line': 300, 'function': 'get_memory_config'}, 'file': 'test/testcases/test_web_api/common.py', 'line': 300, 'function': 'get_memory_config', 'agent_name': 'get_memory_config', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=300)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()
