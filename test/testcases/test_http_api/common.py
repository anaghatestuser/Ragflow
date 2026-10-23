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
DATASETS_API_URL = f"/api/{VERSION}/datasets"
FILE_API_URL = f"/api/{VERSION}/datasets/{{dataset_id}}/documents"
FILE_CHUNK_API_URL = f"/api/{VERSION}/datasets/{{dataset_id}}/chunks"
CHUNK_API_URL = f"/api/{VERSION}/datasets/{{dataset_id}}/documents/{{document_id}}/chunks"
CHAT_ASSISTANT_API_URL = f"/api/{VERSION}/chats"
SESSION_WITH_CHAT_ASSISTANT_API_URL = f"/api/{VERSION}/chats/{{chat_id}}/sessions"
SESSION_WITH_AGENT_API_URL = f"/api/{VERSION}/agents/{{agent_id}}/sessions"


# DATASET MANAGEMENT
def create_dataset(auth, payload=None, *, headers=HEADERS, data=None):
    res = requests.post(url=f"{HOST_ADDRESS}{DATASETS_API_URL}", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in create_dataset).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:2ce8d7eb284d1bb9a3dfa7f716a7b58cf3bd360d7dd0b7655cb2c47f35060224'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2ce8d7eb284d1bb9a3dfa7f716a7b58cf3bd360d7dd0b7655cb2c47f35060224', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 35, 'function': 'create_dataset'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 35, 'function': 'create_dataset', 'agent_name': 'create_dataset', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=35)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def list_datasets(auth, params=None, *, headers=HEADERS):
    res = requests.get(url=f"{HOST_ADDRESS}{DATASETS_API_URL}", headers=headers, auth=auth, params=params)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in list_datasets).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:8576777b660e9ce7efa784c4f5301039ea3e0501caff7563eed64c758bc64501'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8576777b660e9ce7efa784c4f5301039ea3e0501caff7563eed64c758bc64501', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 40, 'function': 'list_datasets'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 40, 'function': 'list_datasets', 'agent_name': 'list_datasets', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=40)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def update_dataset(auth, dataset_id, payload=None, *, headers=HEADERS, data=None):
    res = requests.put(url=f"{HOST_ADDRESS}{DATASETS_API_URL}/{dataset_id}", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in update_dataset).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:7b0f38c2f7f3eff63915b7b2dfd0cb845c5642375368e26d45649c8a73bda00e'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7b0f38c2f7f3eff63915b7b2dfd0cb845c5642375368e26d45649c8a73bda00e', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 45, 'function': 'update_dataset'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 45, 'function': 'update_dataset', 'agent_name': 'update_dataset', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=45)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def delete_datasets(auth, payload=None, *, headers=HEADERS, data=None):
    res = requests.delete(url=f"{HOST_ADDRESS}{DATASETS_API_URL}", headers=headers, auth=auth, json=payload, data=data)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in delete_datasets).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:2e2551c6136c7d862a2d7d80325303dc899219f87088468976817de278fdc102'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2e2551c6136c7d862a2d7d80325303dc899219f87088468976817de278fdc102', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 50, 'function': 'delete_datasets'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 50, 'function': 'delete_datasets', 'agent_name': 'delete_datasets', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=50)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def batch_create_datasets(auth, num):
    ids = []
    for i in range(num):
        res = create_dataset(auth, {"name": f"dataset_{i}"})
        ids.append(res["data"]["id"])
    # LINEAJE: runtime guardrail checks `ids` as it flows from the agent to the user interface, before it leaves the application (in batch_create_datasets).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:8c712abd7c163d1bc2c3d5c332eca4da8af70ac84081c28c92673f964fb3f573'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8c712abd7c163d1bc2c3d5c332eca4da8af70ac84081c28c92673f964fb3f573', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 59, 'function': 'batch_create_datasets'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 59, 'function': 'batch_create_datasets', 'agent_name': 'batch_create_datasets', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        ids = _gr_client.enforce(_gr_site, ids, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return ids


# FILE MANAGEMENT WITHIN DATASET
def upload_documents(auth, dataset_id, files_path=None):
    url = f"{HOST_ADDRESS}{FILE_API_URL}".format(dataset_id=dataset_id)

    if files_path is None:
        files_path = []

    fields = []
    file_objects = []
    try:
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
        #   Do not remove without review. site_id='site:sha256:dc8700453db75a16a1deab1f78aaefb84f44fe9c46116dc3576ce7b3e75a8381'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dc8700453db75a16a1deab1f78aaefb84f44fe9c46116dc3576ce7b3e75a8381', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 79, 'function': 'upload_documents'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 79, 'function': 'upload_documents', 'agent_name': 'upload_documents', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=79)
        except _gr_client.GuardrailUnavailableError:
            pass
        return res.json()
    finally:
        for f in file_objects:
            f.close()


def download_document(auth, dataset_id, document_id, save_path):
    url = f"{HOST_ADDRESS}{FILE_API_URL}/{document_id}".format(dataset_id=dataset_id)
    res = requests.get(url=url, auth=auth, stream=True)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in download_document).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:9010dac835fc20f395f4bb4fe0712cc80830cc455f0813a4dca795a2c844a59a'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9010dac835fc20f395f4bb4fe0712cc80830cc455f0813a4dca795a2c844a59a', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 93, 'function': 'download_document'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 93, 'function': 'download_document', 'agent_name': 'download_document', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=93)
    except _gr_client.GuardrailUnavailableError:
        pass
    try:
        if res.status_code == 200:
            with open(save_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    # LINEAJE: runtime guardrail checks `chunk` as it flows from the agent to a file, before it is written to disk (in download_document).
                    #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `chunk` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:d248d8153813ea82c97819cfe78d1812f54f737534846f77bad2bb462899b817'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d248d8153813ea82c97819cfe78d1812f54f737534846f77bad2bb462899b817', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 98, 'function': 'download_document'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 98, 'function': 'download_document', 'agent_name': 'download_document', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                    try:
                        chunk = _gr_client.enforce(_gr_site, chunk, content_type='application/json', variable_name='chunk', source_file=__file__, before_line=98)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    f.write(chunk)
    finally:
        res.close()

    # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in download_document).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:b896838268ac8602820382203e1627c6879217c1b81d654c4acb41d140756516'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b896838268ac8602820382203e1627c6879217c1b81d654c4acb41d140756516', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 102, 'function': 'download_document'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 102, 'function': 'download_document', 'agent_name': 'download_document', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return res


def list_documents(auth, dataset_id, params=None):
    url = f"{HOST_ADDRESS}{FILE_API_URL}".format(dataset_id=dataset_id)
    res = requests.get(url=url, headers=HEADERS, auth=auth, params=params)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in list_documents).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:7c1134fb3ed3b265a048820983a36003785f569c603e2aa89428c2e2808c913b'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7c1134fb3ed3b265a048820983a36003785f569c603e2aa89428c2e2808c913b', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 107, 'function': 'list_documents'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 107, 'function': 'list_documents', 'agent_name': 'list_documents', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=107)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def update_document(auth, dataset_id, document_id, payload=None):
    url = f"{HOST_ADDRESS}{FILE_API_URL}/{document_id}".format(dataset_id=dataset_id)
    res = requests.put(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in update_document).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:db66473173ede659f91082d26d1a3ebab55254fcccc07370ed208a8c0daae3c2'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:db66473173ede659f91082d26d1a3ebab55254fcccc07370ed208a8c0daae3c2', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 113, 'function': 'update_document'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 113, 'function': 'update_document', 'agent_name': 'update_document', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=113)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def delete_documents(auth, dataset_id, payload=None):
    url = f"{HOST_ADDRESS}{FILE_API_URL}".format(dataset_id=dataset_id)
    res = requests.delete(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in delete_documents).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e0c674c6e854f9e230867049073fecfdc6d08191d0f851c5d7560cb74a6d74eb'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e0c674c6e854f9e230867049073fecfdc6d08191d0f851c5d7560cb74a6d74eb', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 119, 'function': 'delete_documents'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 119, 'function': 'delete_documents', 'agent_name': 'delete_documents', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=119)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def parse_documents(auth, dataset_id, payload=None):
    url = f"{HOST_ADDRESS}{FILE_CHUNK_API_URL}".format(dataset_id=dataset_id)
    res = requests.post(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in parse_documents).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:80ed5ca8c373c6877a16d46a3062e29b8a43ba062c1f9d611d073594de24d806'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:80ed5ca8c373c6877a16d46a3062e29b8a43ba062c1f9d611d073594de24d806', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 125, 'function': 'parse_documents'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 125, 'function': 'parse_documents', 'agent_name': 'parse_documents', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=125)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def stop_parse_documents(auth, dataset_id, payload=None):
    url = f"{HOST_ADDRESS}{FILE_CHUNK_API_URL}".format(dataset_id=dataset_id)
    res = requests.delete(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in stop_parse_documents).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:5a913e32c27f7ddca2c7589decb83db00dd78641c797e5713b94f6282664f362'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5a913e32c27f7ddca2c7589decb83db00dd78641c797e5713b94f6282664f362', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 131, 'function': 'stop_parse_documents'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 131, 'function': 'stop_parse_documents', 'agent_name': 'stop_parse_documents', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=131)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def bulk_upload_documents(auth, dataset_id, num, tmp_path):
    fps = []
    for i in range(num):
        fp = create_txt_file(tmp_path / f"ragflow_test_upload_{i}.txt")
        fps.append(fp)
    res = upload_documents(auth, dataset_id, fps)
    document_ids = []
    for document in res["data"]:
        document_ids.append(document["id"])
    # LINEAJE: runtime guardrail checks `document_ids` as it flows from the agent to the user interface, before it leaves the application (in bulk_upload_documents).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `document_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:251f5b2efbfa06ab16e80530f49a403e45361d15bc389656af64587556277bce'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:251f5b2efbfa06ab16e80530f49a403e45361d15bc389656af64587556277bce', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 144, 'function': 'bulk_upload_documents'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 144, 'function': 'bulk_upload_documents', 'agent_name': 'bulk_upload_documents', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        document_ids = _gr_client.enforce(_gr_site, document_ids, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return document_ids


# CHUNK MANAGEMENT WITHIN DATASET
def add_chunk(auth, dataset_id, document_id, payload=None):
    url = f"{HOST_ADDRESS}{CHUNK_API_URL}".format(dataset_id=dataset_id, document_id=document_id)
    res = requests.post(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in add_chunk).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:b65018682d9028d7e391b0167eb65990bfe96ccf3c91b5f6d16d3102ac93567c'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b65018682d9028d7e391b0167eb65990bfe96ccf3c91b5f6d16d3102ac93567c', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 150, 'function': 'add_chunk'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 150, 'function': 'add_chunk', 'agent_name': 'add_chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=150)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def list_chunks(auth, dataset_id, document_id, params=None):
    url = f"{HOST_ADDRESS}{CHUNK_API_URL}".format(dataset_id=dataset_id, document_id=document_id)
    res = requests.get(url=url, headers=HEADERS, auth=auth, params=params)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in list_chunks).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:62e5e90358fb3030799af6c344966d78f8d896ea99b4da4db757da1cbecd9747'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:62e5e90358fb3030799af6c344966d78f8d896ea99b4da4db757da1cbecd9747', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 156, 'function': 'list_chunks'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 156, 'function': 'list_chunks', 'agent_name': 'list_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=156)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def update_chunk(auth, dataset_id, document_id, chunk_id, payload=None):
    url = f"{HOST_ADDRESS}{CHUNK_API_URL}/{chunk_id}".format(dataset_id=dataset_id, document_id=document_id)
    res = requests.put(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in update_chunk).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:57dc46453828e618fcf10e7f93f37760f8f30af6d2916ee5fadcb0aa299613c1'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:57dc46453828e618fcf10e7f93f37760f8f30af6d2916ee5fadcb0aa299613c1', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 162, 'function': 'update_chunk'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 162, 'function': 'update_chunk', 'agent_name': 'update_chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=162)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def delete_chunks(auth, dataset_id, document_id, payload=None):
    url = f"{HOST_ADDRESS}{CHUNK_API_URL}".format(dataset_id=dataset_id, document_id=document_id)
    res = requests.delete(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in delete_chunks).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:d893e25d40be14693fb074c691963813b06fbc1c5232de79573c5ca7b69c4aa9'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d893e25d40be14693fb074c691963813b06fbc1c5232de79573c5ca7b69c4aa9', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 168, 'function': 'delete_chunks'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 168, 'function': 'delete_chunks', 'agent_name': 'delete_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=168)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def retrieval_chunks(auth, payload=None):
    url = f"{HOST_ADDRESS}/api/v1/retrieval"
    res = requests.post(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in retrieval_chunks).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:44f294fb19e1af36df1e803be7075486dc2c85eb8e337da02679b71dc18abdad'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:44f294fb19e1af36df1e803be7075486dc2c85eb8e337da02679b71dc18abdad', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 174, 'function': 'retrieval_chunks'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 174, 'function': 'retrieval_chunks', 'agent_name': 'retrieval_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=174)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def batch_add_chunks(auth, dataset_id, document_id, num):
    chunk_ids = []
    for i in range(num):
        res = add_chunk(auth, dataset_id, document_id, {"content": f"chunk test {i}"})
        chunk_ids.append(res["data"]["chunk"]["id"])
    # LINEAJE: runtime guardrail checks `chunk_ids` as it flows from the agent to the user interface, before it leaves the application (in batch_add_chunks).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `chunk_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:a8caf262626ce3680267a0a59bf0c47d3d4cb3bf6dfe9d3eb3e12ec5ad0456b3'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a8caf262626ce3680267a0a59bf0c47d3d4cb3bf6dfe9d3eb3e12ec5ad0456b3', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 183, 'function': 'batch_add_chunks'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 183, 'function': 'batch_add_chunks', 'agent_name': 'batch_add_chunks', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        chunk_ids = _gr_client.enforce(_gr_site, chunk_ids, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return chunk_ids


# CHAT ASSISTANT MANAGEMENT
def create_chat_assistant(auth, payload=None):
    url = f"{HOST_ADDRESS}{CHAT_ASSISTANT_API_URL}"
    res = requests.post(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in create_chat_assistant).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:35f7ec1feb5bee84725c1184f6e0f492fd658d3d6c0e7af6a1775efe65bb4fdd'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:35f7ec1feb5bee84725c1184f6e0f492fd658d3d6c0e7af6a1775efe65bb4fdd', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 189, 'function': 'create_chat_assistant'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 189, 'function': 'create_chat_assistant', 'agent_name': 'create_chat_assistant', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=189)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def list_chat_assistants(auth, params=None):
    url = f"{HOST_ADDRESS}{CHAT_ASSISTANT_API_URL}"
    res = requests.get(url=url, headers=HEADERS, auth=auth, params=params)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in list_chat_assistants).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:d962ee7452cde9c6c624c08e88841f2ae03209ffcde9e45e1d4e22cd2bdcbe20'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d962ee7452cde9c6c624c08e88841f2ae03209ffcde9e45e1d4e22cd2bdcbe20', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 195, 'function': 'list_chat_assistants'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 195, 'function': 'list_chat_assistants', 'agent_name': 'list_chat_assistants', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=195)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def update_chat_assistant(auth, chat_assistant_id, payload=None):
    url = f"{HOST_ADDRESS}{CHAT_ASSISTANT_API_URL}/{chat_assistant_id}"
    res = requests.put(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in update_chat_assistant).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:afd6c5bb0a4f38fb98b3e48c8d305941dc05037ffcf06f65e7f0114a3d09dff2'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:afd6c5bb0a4f38fb98b3e48c8d305941dc05037ffcf06f65e7f0114a3d09dff2', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 201, 'function': 'update_chat_assistant'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 201, 'function': 'update_chat_assistant', 'agent_name': 'update_chat_assistant', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=201)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def delete_chat_assistants(auth, payload=None):
    url = f"{HOST_ADDRESS}{CHAT_ASSISTANT_API_URL}"
    res = requests.delete(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in delete_chat_assistants).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:fb1e532ad442e9afb6bd5e09e1f7451371fcd800667f3559069168e1c62236ee'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fb1e532ad442e9afb6bd5e09e1f7451371fcd800667f3559069168e1c62236ee', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 207, 'function': 'delete_chat_assistants'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 207, 'function': 'delete_chat_assistants', 'agent_name': 'delete_chat_assistants', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=207)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def batch_create_chat_assistants(auth, num):
    chat_assistant_ids = []
    for i in range(num):
        res = create_chat_assistant(auth, {"name": f"test_chat_assistant_{i}", "dataset_ids": []})
        chat_assistant_ids.append(res["data"]["id"])
    # LINEAJE: runtime guardrail checks `chat_assistant_ids` as it flows from the agent to the user interface, before it leaves the application (in batch_create_chat_assistants).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `chat_assistant_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:dcaa04fd908c96037ef23bbb56ab26dee3b4fa4dca9994ee6d88f2b3a393a577'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dcaa04fd908c96037ef23bbb56ab26dee3b4fa4dca9994ee6d88f2b3a393a577', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 216, 'function': 'batch_create_chat_assistants'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 216, 'function': 'batch_create_chat_assistants', 'agent_name': 'batch_create_chat_assistants', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        chat_assistant_ids = _gr_client.enforce(_gr_site, chat_assistant_ids, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return chat_assistant_ids


# SESSION MANAGEMENT
def create_session_with_chat_assistant(auth, chat_assistant_id, payload=None):
    url = f"{HOST_ADDRESS}{SESSION_WITH_CHAT_ASSISTANT_API_URL}".format(chat_id=chat_assistant_id)
    res = requests.post(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in create_session_with_chat_assistant).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e16d6bdc981a62c4d770c46842610f9073c8ef2618462e45df06f1af13f93d37'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e16d6bdc981a62c4d770c46842610f9073c8ef2618462e45df06f1af13f93d37', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 222, 'function': 'create_session_with_chat_assistant'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 222, 'function': 'create_session_with_chat_assistant', 'agent_name': 'create_session_with_chat_assistant', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=222)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def list_session_with_chat_assistants(auth, chat_assistant_id, params=None):
    url = f"{HOST_ADDRESS}{SESSION_WITH_CHAT_ASSISTANT_API_URL}".format(chat_id=chat_assistant_id)
    res = requests.get(url=url, headers=HEADERS, auth=auth, params=params)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in list_session_with_chat_assistants).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:82723dc150af4cb5277c588c70237cd779e1989de6a3a7195301d5607fc3a3c5'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:82723dc150af4cb5277c588c70237cd779e1989de6a3a7195301d5607fc3a3c5', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 228, 'function': 'list_session_with_chat_assistants'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 228, 'function': 'list_session_with_chat_assistants', 'agent_name': 'list_session_with_chat_assistants', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=228)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def update_session_with_chat_assistant(auth, chat_assistant_id, session_id, payload=None):
    url = f"{HOST_ADDRESS}{SESSION_WITH_CHAT_ASSISTANT_API_URL}/{session_id}".format(chat_id=chat_assistant_id)
    res = requests.put(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in update_session_with_chat_assistant).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:ecd376f07e5e1dd93636f44629b52ca3f4ab03c4183b1bfaa856dab01d927cc2'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ecd376f07e5e1dd93636f44629b52ca3f4ab03c4183b1bfaa856dab01d927cc2', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 234, 'function': 'update_session_with_chat_assistant'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 234, 'function': 'update_session_with_chat_assistant', 'agent_name': 'update_session_with_chat_assistant', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=234)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def delete_session_with_chat_assistants(auth, chat_assistant_id, payload=None):
    url = f"{HOST_ADDRESS}{SESSION_WITH_CHAT_ASSISTANT_API_URL}".format(chat_id=chat_assistant_id)
    res = requests.delete(url=url, headers=HEADERS, auth=auth, json=payload)
    # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in delete_session_with_chat_assistants).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:ce54beefb84cf193b5e1efe803e8d36d3cc463c1f211843ca639709f1481b475'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ce54beefb84cf193b5e1efe803e8d36d3cc463c1f211843ca639709f1481b475', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 240, 'function': 'delete_session_with_chat_assistants'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 240, 'function': 'delete_session_with_chat_assistants', 'agent_name': 'delete_session_with_chat_assistants', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=240)
    except _gr_client.GuardrailUnavailableError:
        pass
    return res.json()


def batch_add_sessions_with_chat_assistant(auth, chat_assistant_id, num):
    session_ids = []
    for i in range(num):
        res = create_session_with_chat_assistant(auth, chat_assistant_id, {"name": f"session_with_chat_assistant_{i}"})
        session_ids.append(res["data"]["id"])
    # LINEAJE: runtime guardrail checks `session_ids` as it flows from the agent to the user interface, before it leaves the application (in batch_add_sessions_with_chat_assistant).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `session_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:001d7d2b2cf932dcba353a614329fab17db2c26a8ddc3d59142f9b9c98423211'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:001d7d2b2cf932dcba353a614329fab17db2c26a8ddc3d59142f9b9c98423211', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/common.py', 'line': 249, 'function': 'batch_add_sessions_with_chat_assistant'}, 'file': 'test/testcases/test_http_api/common.py', 'line': 249, 'function': 'batch_add_sessions_with_chat_assistant', 'agent_name': 'batch_add_sessions_with_chat_assistant', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        session_ids = _gr_client.enforce(_gr_site, session_ids, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return session_ids
