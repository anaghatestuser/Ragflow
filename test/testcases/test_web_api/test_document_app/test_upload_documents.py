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
import string
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import requests
from common import DOCUMENT_APP_URL, list_kbs, upload_documents
from configs import DOCUMENT_NAME_LIMIT, HOST_ADDRESS, INVALID_API_TOKEN
from libs.auth import RAGFlowWebApiAuth
from requests_toolbelt import MultipartEncoder
from utils.file_utils import create_txt_file


@pytest.mark.p1
@pytest.mark.usefixtures("clear_datasets")
class TestAuthorization:
    @pytest.mark.parametrize(
        "invalid_auth, expected_code, expected_message",
        [
            (None, 401, "<Unauthorized '401: Unauthorized'>"),
            (RAGFlowWebApiAuth(INVALID_API_TOKEN), 401, "<Unauthorized '401: Unauthorized'>"),
        ],
    )
    def test_invalid_auth(self, invalid_auth, expected_code, expected_message):
        res = upload_documents(invalid_auth)
        assert res["code"] == expected_code, res
        assert res["message"] == expected_message, res


class TestDocumentsUpload:
    @pytest.mark.p1
    def test_valid_single_upload(self, WebApiAuth, add_dataset_func, tmp_path):
        kb_id = add_dataset_func
        fp = create_txt_file(tmp_path / "ragflow_test.txt")
        res = upload_documents(WebApiAuth, {"kb_id": kb_id}, [fp])
        assert res["code"] == 0, res
        assert res["data"][0]["kb_id"] == kb_id, res
        assert res["data"][0]["name"] == fp.name, res

    @pytest.mark.p1
    @pytest.mark.parametrize(
        "generate_test_files",
        [
            "docx",
            "excel",
            "ppt",
            "image",
            "pdf",
            "txt",
            "md",
            "json",
            "eml",
            "html",
        ],
        indirect=True,
    )
    def test_file_type_validation(self, WebApiAuth, add_dataset_func, generate_test_files, request):
        kb_id = add_dataset_func
        fp = generate_test_files[request.node.callspec.params["generate_test_files"]]
        res = upload_documents(WebApiAuth, {"kb_id": kb_id}, [fp])
        assert res["code"] == 0, res
        assert res["data"][0]["kb_id"] == kb_id, res
        assert res["data"][0]["name"] == fp.name, res

    @pytest.mark.p2
    @pytest.mark.parametrize(
        "file_type",
        ["exe", "unknown"],
    )
    def test_unsupported_file_type(self, WebApiAuth, add_dataset_func, tmp_path, file_type):
        kb_id = add_dataset_func
        fp = tmp_path / f"ragflow_test.{file_type}"
        fp.touch()
        res = upload_documents(WebApiAuth, {"kb_id": kb_id}, [fp])
        assert res["code"] == 500, res
        assert res["message"] == f"ragflow_test.{file_type}: This type of file has not been supported yet!", res

    @pytest.mark.p2
    def test_missing_file(self, WebApiAuth, add_dataset_func):
        kb_id = add_dataset_func
        res = upload_documents(WebApiAuth, {"kb_id": kb_id})
        assert res["code"] == 101, res
        assert res["message"] == "No file part!", res

    @pytest.mark.p3
    def test_empty_file(self, WebApiAuth, add_dataset_func, tmp_path):
        kb_id = add_dataset_func
        fp = tmp_path / "empty.txt"
        fp.touch()

        res = upload_documents(WebApiAuth, {"kb_id": kb_id}, [fp])
        assert res["code"] == 0, res
        assert res["data"][0]["size"] == 0, res

    @pytest.mark.p3
    def test_filename_empty(self, WebApiAuth, add_dataset_func, tmp_path):
        kb_id = add_dataset_func

        fp = create_txt_file(tmp_path / "ragflow_test.txt")
        url = f"{HOST_ADDRESS}{DOCUMENT_APP_URL}/upload"
        fields = [("file", ("", fp.open("rb"))), ("kb_id", kb_id)]
        m = MultipartEncoder(fields=fields)
        res = requests.post(
            url=url,
            headers={"Content-Type": m.content_type},
            auth=WebApiAuth,
            data=m,
        )
        # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in TestDocumentsUpload.test_filename_empty).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:edb236214641749df356966b363dcd33812035234dde0696abd9595e12334d86'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:edb236214641749df356966b363dcd33812035234dde0696abd9595e12334d86', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/test_document_app/test_upload_documents.py', 'line': 117, 'function': 'TestDocumentsUpload.test_filename_empty'}, 'file': 'test/testcases/test_web_api/test_document_app/test_upload_documents.py', 'line': 117, 'function': 'test_filename_empty', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=117)
        except _gr_client.GuardrailUnavailableError:
            pass
        assert res.json()["code"] == 101, res
        assert res.json()["message"] == "No file selected!", res

    @pytest.mark.p2
    def test_filename_exceeds_max_length(self, WebApiAuth, add_dataset_func, tmp_path):
        kb_id = add_dataset_func
        fp = create_txt_file(tmp_path / f"{'a' * (DOCUMENT_NAME_LIMIT - 4)}.txt")
        res = upload_documents(WebApiAuth, {"kb_id": kb_id}, [fp])
        assert res["code"] == 0, res
        assert res["data"][0]["name"] == fp.name, res

    @pytest.mark.p2
    def test_invalid_kb_id(self, WebApiAuth, tmp_path):
        fp = create_txt_file(tmp_path / "ragflow_test.txt")
        res = upload_documents(WebApiAuth, {"kb_id": "invalid_kb_id"}, [fp])
        assert res["code"] == 100, res
        assert res["message"] == """LookupError("Can't find this dataset!")""", res

    @pytest.mark.p2
    def test_duplicate_files(self, WebApiAuth, add_dataset_func, tmp_path):
        kb_id = add_dataset_func
        fp = create_txt_file(tmp_path / "ragflow_test.txt")
        res = upload_documents(WebApiAuth, {"kb_id": kb_id}, [fp, fp])
        assert res["code"] == 0, res
        assert len(res["data"]) == 2, res
        for i in range(len(res["data"])):
            assert res["data"][i]["kb_id"] == kb_id, res
            expected_name = fp.name
            if i != 0:
                expected_name = f"{fp.stem}({i}){fp.suffix}"
            assert res["data"][i]["name"] == expected_name, res

    @pytest.mark.p3
    def test_filename_special_characters(self, WebApiAuth, add_dataset_func, tmp_path):
        kb_id = add_dataset_func
        illegal_chars = '<>:"/\\|?*'
        translation_table = str.maketrans({char: "_" for char in illegal_chars})
        safe_filename = string.punctuation.translate(translation_table)
        fp = tmp_path / f"{safe_filename}.txt"
        _lineaje_payload = "Sample text content"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to a file, before it is written to disk (in TestDocumentsUpload.test_filename_special_characters).
        #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:4771a3dfa1f16dee2f7606b09d2e26f016a75510cdcdb9de6958b8ef39b5b6dc'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4771a3dfa1f16dee2f7606b09d2e26f016a75510cdcdb9de6958b8ef39b5b6dc', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_web_api/test_document_app/test_upload_documents.py', 'line': 162, 'function': 'TestDocumentsUpload.test_filename_special_characters'}, 'file': 'test/testcases/test_web_api/test_document_app/test_upload_documents.py', 'line': 162, 'function': 'test_filename_special_characters', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=162)
        except _gr_client.GuardrailUnavailableError:
            pass
        fp.write_text(_lineaje_payload)

        res = upload_documents(WebApiAuth, {"kb_id": kb_id}, [fp])
        assert res["code"] == 0, res
        assert len(res["data"]) == 1, res
        assert res["data"][0]["kb_id"] == kb_id, res
        assert res["data"][0]["name"] == fp.name, res

    @pytest.mark.p1
    def test_multiple_files(self, WebApiAuth, add_dataset_func, tmp_path):
        kb_id = add_dataset_func
        expected_document_count = 20
        fps = []
        for i in range(expected_document_count):
            fp = create_txt_file(tmp_path / f"ragflow_test_{i}.txt")
            fps.append(fp)
        res = upload_documents(WebApiAuth, {"kb_id": kb_id}, fps)
        assert res["code"] == 0, res

        res = list_kbs(WebApiAuth)
        assert res["data"]["kbs"][0]["doc_num"] == expected_document_count, res

    @pytest.mark.p3
    def test_concurrent_upload(self, WebApiAuth, add_dataset_func, tmp_path):
        kb_id = add_dataset_func

        count = 20
        fps = []
        for i in range(count):
            fp = create_txt_file(tmp_path / f"ragflow_test_{i}.txt")
            fps.append(fp)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upload_documents, WebApiAuth, {"kb_id": kb_id}, fps[i : i + 1]) for i in range(count)]
        responses = list(as_completed(futures))
        assert len(responses) == count, responses
        assert all(future.result()["code"] == 0 for future in futures), responses

        res = list_kbs(WebApiAuth)
        assert res["data"]["kbs"][0]["doc_num"] == count, res
