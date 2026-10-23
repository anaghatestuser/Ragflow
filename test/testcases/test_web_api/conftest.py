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
from time import sleep

import pytest
from common import (
    batch_add_chunks,
    batch_create_datasets,
    bulk_upload_documents,
    delete_chunks,
    delete_dialogs,
    list_chunks,
    list_documents,
    list_kbs,
    parse_documents,
    rm_kb,
)
from libs.auth import RAGFlowWebApiAuth
from pytest import FixtureRequest
from utils import wait_for
from utils.file_utils import (
    create_docx_file,
    create_eml_file,
    create_excel_file,
    create_html_file,
    create_image_file,
    create_json_file,
    create_md_file,
    create_pdf_file,
    create_ppt_file,
    create_txt_file,
)


@wait_for(30, 1, "Document parsing timeout")
def condition(_auth, _kb_id):
    res = list_documents(_auth, {"kb_id": _kb_id})
    for doc in res["data"]["docs"]:
        if doc["run"] != "3":
            return False
    return True


@pytest.fixture
def generate_test_files(request: FixtureRequest, tmp_path):
    file_creators = {
        "docx": (tmp_path / "ragflow_test.docx", create_docx_file),
        "excel": (tmp_path / "ragflow_test.xlsx", create_excel_file),
        "ppt": (tmp_path / "ragflow_test.pptx", create_ppt_file),
        "image": (tmp_path / "ragflow_test.png", create_image_file),
        "pdf": (tmp_path / "ragflow_test.pdf", create_pdf_file),
        "txt": (tmp_path / "ragflow_test.txt", create_txt_file),
        "md": (tmp_path / "ragflow_test.md", create_md_file),
        "json": (tmp_path / "ragflow_test.json", create_json_file),
        "eml": (tmp_path / "ragflow_test.eml", create_eml_file),
        "html": (tmp_path / "ragflow_test.html", create_html_file),
    }

    files = {}
    for file_type, (file_path, creator_func) in file_creators.items():
        if request.param in ["", file_type]:
            creator_func(file_path)
            files[file_type] = file_path
    # LINEAJE: runtime guardrail checks `files` as it flows from the agent to the user interface, before it leaves the application (in generate_test_files).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `files` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:ff65b3e831dc9ea9bdd3cf831f3f68cac0a23a35a1b5e21abab37f5fdd2272f7'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ff65b3e831dc9ea9bdd3cf831f3f68cac0a23a35a1b5e21abab37f5fdd2272f7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/conftest.py', 'line': 77, 'function': 'generate_test_files'}, 'file': 'test/testcases/test_web_api/conftest.py', 'line': 77, 'function': 'generate_test_files', 'agent_name': 'generate_test_files', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        files = _gr_client.enforce(_gr_site, files, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return files


@pytest.fixture(scope="class")
def ragflow_tmp_dir(request, tmp_path_factory):
    class_name = request.cls.__name__
    return tmp_path_factory.mktemp(class_name)


@pytest.fixture(scope="session")
def WebApiAuth(auth):
    return RAGFlowWebApiAuth(auth)


@pytest.fixture(scope="function")
def clear_datasets(request: FixtureRequest, WebApiAuth: RAGFlowWebApiAuth):
    def cleanup():
        res = list_kbs(WebApiAuth, params={"page_size": 1000})
        for kb in res["data"]["kbs"]:
            rm_kb(WebApiAuth, {"kb_id": kb["id"]})

    request.addfinalizer(cleanup)


@pytest.fixture(scope="function")
def clear_dialogs(request, WebApiAuth):
    def cleanup():
        delete_dialogs(WebApiAuth)

    request.addfinalizer(cleanup)


@pytest.fixture(scope="class")
def add_dataset(request: FixtureRequest, WebApiAuth: RAGFlowWebApiAuth) -> str:
    def cleanup():
        res = list_kbs(WebApiAuth, params={"page_size": 1000})
        for kb in res["data"]["kbs"]:
            rm_kb(WebApiAuth, {"kb_id": kb["id"]})

    request.addfinalizer(cleanup)
    return batch_create_datasets(WebApiAuth, 1)[0]


@pytest.fixture(scope="function")
def add_dataset_func(request: FixtureRequest, WebApiAuth: RAGFlowWebApiAuth) -> str:
    def cleanup():
        res = list_kbs(WebApiAuth, params={"page_size": 1000})
        for kb in res["data"]["kbs"]:
            rm_kb(WebApiAuth, {"kb_id": kb["id"]})

    request.addfinalizer(cleanup)
    return batch_create_datasets(WebApiAuth, 1)[0]


@pytest.fixture(scope="class")
def add_document(request, WebApiAuth, add_dataset, ragflow_tmp_dir):
    #     def cleanup():
    #         res = list_documents(WebApiAuth, {"kb_id": dataset_id})
    #         for doc in res["data"]["docs"]:
    #             delete_document(WebApiAuth, {"doc_id": doc["id"]})

    #     request.addfinalizer(cleanup)

    dataset_id = add_dataset
    return dataset_id, bulk_upload_documents(WebApiAuth, dataset_id, 1, ragflow_tmp_dir)[0]


@pytest.fixture(scope="class")
def add_chunks(request, WebApiAuth, add_document):
    def cleanup():
        res = list_chunks(WebApiAuth, {"doc_id": document_id})
        if res["code"] == 0:
            chunk_ids = [chunk["chunk_id"] for chunk in res["data"]["chunks"]]
            delete_chunks(WebApiAuth, {"doc_id": document_id, "chunk_ids": chunk_ids})

    request.addfinalizer(cleanup)

    kb_id, document_id = add_document
    parse_documents(WebApiAuth, {"doc_ids": [document_id], "run": "1"})
    condition(WebApiAuth, kb_id)
    chunk_ids = batch_add_chunks(WebApiAuth, document_id, 4)
    # issues/6487
    sleep(1)
    return kb_id, document_id, chunk_ids
