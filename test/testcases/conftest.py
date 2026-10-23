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
import requests
from configs import EMAIL, HOST_ADDRESS, PASSWORD, VERSION, ZHIPU_AI_API_KEY

MARKER_EXPRESSIONS = {
    "p1": "p1",
    "p2": "p1 or p2",
    "p3": "p1 or p2 or p3",
}


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--level",
        action="store",
        default="p2",
        choices=list(MARKER_EXPRESSIONS.keys()),
        help=f"Test level ({'/'.join(MARKER_EXPRESSIONS)}): p1=smoke, p2=core, p3=full",
    )

    parser.addoption(
        "--client-type",
        action="store",
        default="http",
        choices=["python_sdk", "http", "web"],
        help="Test client type: 'python_sdk', 'http', 'web'",
    )


def pytest_configure(config: pytest.Config) -> None:
    level = config.getoption("--level")
    config.option.markexpr = MARKER_EXPRESSIONS[level]
    if config.option.verbose > 0:
        _lineaje_payload = f"\n[CONFIG] Active test level: {level}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in pytest_configure).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:aa800f7a584fda17497f9f6cecc84df0c380d1fdb736ff8aa1e91dc6cfc230c7'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aa800f7a584fda17497f9f6cecc84df0c380d1fdb736ff8aa1e91dc6cfc230c7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/conftest.py', 'line': 50, 'function': 'pytest_configure'}, 'file': 'test/testcases/conftest.py', 'line': 50, 'function': 'pytest_configure', 'agent_name': 'pytest_configure', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)


def register():
    url = HOST_ADDRESS + f"/{VERSION}/user/register"
    name = "qa"
    register_data = {"email": EMAIL, "nickname": name, "password": PASSWORD}
    res = requests.post(url=url, json=register_data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in register).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e0198c8ed4f2626e2f510e3c2d1f4093e44326b4e5ec217fe4b159806431dae2'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e0198c8ed4f2626e2f510e3c2d1f4093e44326b4e5ec217fe4b159806431dae2', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/conftest.py', 'line': 57, 'function': 'register'}, 'file': 'test/testcases/conftest.py', 'line': 57, 'function': 'register', 'agent_name': 'register', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=57)
    except _gr_client.GuardrailUnavailableError:
        pass
    res = res.json()
    if res.get("code") != 0 and "has already registered" not in res.get("message"):
        raise Exception(res.get("message"))


def login():
    url = HOST_ADDRESS + f"/{VERSION}/user/login"
    login_data = {"email": EMAIL, "password": PASSWORD}
    response = requests.post(url=url, json=login_data)
    # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in login).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:166033f7c41b655a07c2a99f165747aa0af83bf9544c94a8c39916d8d060543b'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:166033f7c41b655a07c2a99f165747aa0af83bf9544c94a8c39916d8d060543b', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/conftest.py', 'line': 66, 'function': 'login'}, 'file': 'test/testcases/conftest.py', 'line': 66, 'function': 'login', 'agent_name': 'login', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=66)
    except _gr_client.GuardrailUnavailableError:
        pass
    res = response.json()
    if res.get("code") != 0:
        raise Exception(res.get("message"))
    auth = response.headers["Authorization"]
    return auth


@pytest.fixture(scope="session")
def auth():
    try:
        register()
    except Exception as e:
        # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in auth).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:2a32b2b2bc4988ceaa87a4b7d6e7666d10d019823ea9a23a3392eddb28667549'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2a32b2b2bc4988ceaa87a4b7d6e7666d10d019823ea9a23a3392eddb28667549', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/conftest.py', 'line': 79, 'function': 'auth'}, 'file': 'test/testcases/conftest.py', 'line': 79, 'function': 'auth', 'agent_name': 'auth', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            e = _gr_client.enforce(_gr_site, e, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(e)
    auth = login()
    # LINEAJE: runtime guardrail checks `auth` as it flows from the agent to the user interface, before it leaves the application (in auth).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `auth` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:dbb5a8c862104dba19eaa397bc5b009f2e34aac0c4f13f59871cee7d6fe0922f'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dbb5a8c862104dba19eaa397bc5b009f2e34aac0c4f13f59871cee7d6fe0922f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/conftest.py', 'line': 81, 'function': 'auth'}, 'file': 'test/testcases/conftest.py', 'line': 81, 'function': 'auth', 'agent_name': 'auth', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        auth = _gr_client.enforce(_gr_site, auth, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return auth


@pytest.fixture(scope="session")
def token(auth):
    url = HOST_ADDRESS + f"/{VERSION}/system/new_token"
    auth = {"Authorization": auth}
    response = requests.post(url=url, headers=auth)
    # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in token).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:8f6cc3edfb1d5810e477e676597a42e5697c026244bf37e57aa5eed7a3051d0a'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8f6cc3edfb1d5810e477e676597a42e5697c026244bf37e57aa5eed7a3051d0a', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/conftest.py', 'line': 88, 'function': 'token'}, 'file': 'test/testcases/conftest.py', 'line': 88, 'function': 'token', 'agent_name': 'token', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=88)
    except _gr_client.GuardrailUnavailableError:
        pass
    res = response.json()
    if res.get("code") != 0:
        raise Exception(res.get("message"))
    return res["data"].get("token")


def get_my_llms(auth, name):
    url = HOST_ADDRESS + f"/{VERSION}/llm/my_llms"
    authorization = {"Authorization": auth}
    response = requests.get(url=url, headers=authorization)
    # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in get_my_llms).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:27345319583e182eee0884d64aa1a106cf741caae93c601ef3d8eda6acb34097'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:27345319583e182eee0884d64aa1a106cf741caae93c601ef3d8eda6acb34097', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/conftest.py', 'line': 98, 'function': 'get_my_llms'}, 'file': 'test/testcases/conftest.py', 'line': 98, 'function': 'get_my_llms', 'agent_name': 'get_my_llms', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=98)
    except _gr_client.GuardrailUnavailableError:
        pass
    res = response.json()
    if res.get("code") != 0:
        raise Exception(res.get("message"))
    if name in res.get("data"):
        return True
    return False


def add_models(auth):
    url = HOST_ADDRESS + f"/{VERSION}/llm/set_api_key"
    authorization = {"Authorization": auth}
    models_info = {
        "ZHIPU-AI": {"llm_factory": "ZHIPU-AI", "api_key": ZHIPU_AI_API_KEY},
    }

    for name, model_info in models_info.items():
        if not get_my_llms(auth, name):
            response = requests.post(url=url, headers=authorization, json=model_info)
            # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in add_models).
            #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:508760a762ed077f982f23404d3030f371bc625d65c85df9a9f758fe570f75de'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:508760a762ed077f982f23404d3030f371bc625d65c85df9a9f758fe570f75de', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/conftest.py', 'line': 116, 'function': 'add_models'}, 'file': 'test/testcases/conftest.py', 'line': 116, 'function': 'add_models', 'agent_name': 'add_models', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=116)
            except _gr_client.GuardrailUnavailableError:
                pass
            res = response.json()
            if res.get("code") != 0:
                pytest.exit(f"Critical error in add_models: {res.get('message')}")


def get_tenant_info(auth):
    url = HOST_ADDRESS + f"/{VERSION}/user/tenant_info"
    authorization = {"Authorization": auth}
    response = requests.get(url=url, headers=authorization)
    # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in get_tenant_info).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:aa867e2387621ea131df616e171e63a58b61f78eb19fa8845ac14c0391b174e0'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aa867e2387621ea131df616e171e63a58b61f78eb19fa8845ac14c0391b174e0', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/conftest.py', 'line': 125, 'function': 'get_tenant_info'}, 'file': 'test/testcases/conftest.py', 'line': 125, 'function': 'get_tenant_info', 'agent_name': 'get_tenant_info', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=125)
    except _gr_client.GuardrailUnavailableError:
        pass
    res = response.json()
    if res.get("code") != 0:
        raise Exception(res.get("message"))
    return res["data"].get("tenant_id")


@pytest.fixture(scope="session", autouse=True)
def set_tenant_info(auth):
    tenant_id = None
    try:
        add_models(auth)
        tenant_id = get_tenant_info(auth)
    except Exception as e:
        pytest.exit(f"Error in set_tenant_info: {str(e)}")
    url = HOST_ADDRESS + f"/{VERSION}/user/set_tenant_info"
    authorization = {"Authorization": auth}
    tenant_info = {
        "tenant_id": tenant_id,
        "llm_id": "glm-4-flash@ZHIPU-AI",
        "embd_id": "BAAI/bge-small-en-v1.5@Builtin",
        "img2txt_id": "",
        "asr_id": "",
        "tts_id": None,
    }
    response = requests.post(url=url, headers=authorization, json=tenant_info)
    # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in set_tenant_info).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:0f786cbd415472bc7497f779c05b165b5947d37c4b2057906cac156f52e8eb89'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0f786cbd415472bc7497f779c05b165b5947d37c4b2057906cac156f52e8eb89', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/conftest.py', 'line': 150, 'function': 'set_tenant_info'}, 'file': 'test/testcases/conftest.py', 'line': 150, 'function': 'set_tenant_info', 'agent_name': 'set_tenant_info', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=150)
    except _gr_client.GuardrailUnavailableError:
        pass
    res = response.json()
    if res.get("code") != 0:
        raise Exception(res.get("message"))
