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
from common import FILE_API_URL, list_datasets, upload_documents
from configs import DOCUMENT_NAME_LIMIT, HOST_ADDRESS, INVALID_API_TOKEN
from libs.auth import RAGFlowHttpApiAuth
from requests_toolbelt import MultipartEncoder
from utils.file_utils import create_txt_file


@pytest.mark.p1
@pytest.mark.usefixtures("clear_datasets")
class TestAuthorization:
    @pytest.mark.parametrize(
        "invalid_auth, expected_code, expected_message",
        [
            (None, 0, "`Authorization` can't be empty"),
            (
                RAGFlowHttpApiAuth(INVALID_API_TOKEN),
                109,
                "Authentication error: API key is invalid!",
            ),
        ],
    )
    def test_invalid_auth(self, invalid_auth, expected_code, expected_message):
        res = upload_documents(invalid_auth, "dataset_id")
        assert res["code"] == expected_code
        assert res["message"] == expected_message


class TestDocumentsUpload:
    @pytest.mark.p1
    def test_valid_single_upload(self, HttpApiAuth, add_dataset_func, tmp_path):
        dataset_id = add_dataset_func
        fp = create_txt_file(tmp_path / "ragflow_test.txt")
        res = upload_documents(HttpApiAuth, dataset_id, [fp])
        assert res["code"] == 0
        assert res["data"][0]["dataset_id"] == dataset_id
        assert res["data"][0]["name"] == fp.name

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
    def test_file_type_validation(self, HttpApiAuth, add_dataset_func, generate_test_files, request):
        dataset_id = add_dataset_func
        fp = generate_test_files[request.node.callspec.params["generate_test_files"]]
        res = upload_documents(HttpApiAuth, dataset_id, [fp])
        assert res["code"] == 0
        assert res["data"][0]["dataset_id"] == dataset_id
        assert res["data"][0]["name"] == fp.name

    @pytest.mark.p2
    @pytest.mark.parametrize(
        "file_type",
        ["exe", "unknown"],
    )
    def test_unsupported_file_type(self, HttpApiAuth, add_dataset_func, tmp_path, file_type):
        dataset_id = add_dataset_func
        fp = tmp_path / f"ragflow_test.{file_type}"
        fp.touch()
        res = upload_documents(HttpApiAuth, dataset_id, [fp])
        assert res["code"] == 500
        assert res["message"] == f"ragflow_test.{file_type}: This type of file has not been supported yet!"

    @pytest.mark.p2
    def test_missing_file(self, HttpApiAuth, add_dataset_func):
        dataset_id = add_dataset_func
        res = upload_documents(HttpApiAuth, dataset_id)
        assert res["code"] == 101
        assert res["message"] == "No file part!"

    @pytest.mark.p3
    def test_empty_file(self, HttpApiAuth, add_dataset_func, tmp_path):
        dataset_id = add_dataset_func
        fp = tmp_path / "empty.txt"
        fp.touch()

        res = upload_documents(HttpApiAuth, dataset_id, [fp])
        assert res["code"] == 0
        assert res["data"][0]["size"] == 0

    @pytest.mark.p3
    def test_filename_empty(self, HttpApiAuth, add_dataset_func, tmp_path):
        dataset_id = add_dataset_func
        fp = create_txt_file(tmp_path / "ragflow_test.txt")
        url = f"{HOST_ADDRESS}{FILE_API_URL}".format(dataset_id=dataset_id)
        fields = (("file", ("", fp.open("rb"))),)
        m = MultipartEncoder(fields=fields)
        res = requests.post(
            url=url,
            headers={"Content-Type": m.content_type},
            auth=HttpApiAuth,
            data=m,
        )
        # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in TestDocumentsUpload.test_filename_empty).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3d81d8fd6720c6c136e2eb215432bb413273b4a97c0fc921247d4563b8c88a20'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3d81d8fd6720c6c136e2eb215432bb413273b4a97c0fc921247d4563b8c88a20', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 120, 'function': 'TestDocumentsUpload.test_filename_empty'}, 'file': 'test/testcases/test_http_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 120, 'function': 'test_filename_empty', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=120)
        except _gr_client.GuardrailUnavailableError:
            pass
        assert res.json()["code"] == 101
        assert res.json()["message"] == "No file selected!"

    @pytest.mark.p2
    def test_filename_max_length(self, HttpApiAuth, add_dataset_func, tmp_path):
        dataset_id = add_dataset_func
        fp = create_txt_file(tmp_path / f"{'a' * (DOCUMENT_NAME_LIMIT - 4)}.txt")
        res = upload_documents(HttpApiAuth, dataset_id, [fp])
        assert res["code"] == 0
        assert res["data"][0]["name"] == fp.name

    @pytest.mark.p2
    def test_invalid_dataset_id(self, HttpApiAuth, tmp_path):
        fp = create_txt_file(tmp_path / "ragflow_test.txt")
        res = upload_documents(HttpApiAuth, "invalid_dataset_id", [fp])
        assert res["code"] == 100
        assert res["message"] == """LookupError("Can\'t find the dataset with ID invalid_dataset_id!")"""

    @pytest.mark.p2
    def test_duplicate_files(self, HttpApiAuth, add_dataset_func, tmp_path):
        dataset_id = add_dataset_func
        fp = create_txt_file(tmp_path / "ragflow_test.txt")
        res = upload_documents(HttpApiAuth, dataset_id, [fp, fp])
        assert res["code"] == 0
        assert len(res["data"]) == 2
        for i in range(len(res["data"])):
            assert res["data"][i]["dataset_id"] == dataset_id
            expected_name = fp.name
            if i != 0:
                expected_name = f"{fp.stem}({i}){fp.suffix}"
            assert res["data"][i]["name"] == expected_name

    @pytest.mark.p2
    def test_same_file_repeat(self, HttpApiAuth, add_dataset_func, tmp_path):
        dataset_id = add_dataset_func
        fp = create_txt_file(tmp_path / "ragflow_test.txt")
        for i in range(3):
            res = upload_documents(HttpApiAuth, dataset_id, [fp])
            assert res["code"] == 0
            assert len(res["data"]) == 1
            assert res["data"][0]["dataset_id"] == dataset_id
            expected_name = fp.name
            if i != 0:
                expected_name = f"{fp.stem}({i}){fp.suffix}"
            assert res["data"][0]["name"] == expected_name

    @pytest.mark.p3
    def test_filename_special_characters(self, HttpApiAuth, add_dataset_func, tmp_path):
        dataset_id = add_dataset_func
        illegal_chars = '<>:"/\\|?*'
        translation_table = str.maketrans({char: "_" for char in illegal_chars})
        safe_filename = string.punctuation.translate(translation_table)
        fp = tmp_path / f"{safe_filename}.txt"
        _lineaje_payload = "Sample text content"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to a file, before it is written to disk (in TestDocumentsUpload.test_filename_special_characters).
        #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:66392ff164cbf80495d4f000d5b2baf1b18c716078b94cb679ce01ee2154e8e9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:66392ff164cbf80495d4f000d5b2baf1b18c716078b94cb679ce01ee2154e8e9', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_http_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 179, 'function': 'TestDocumentsUpload.test_filename_special_characters'}, 'file': 'test/testcases/test_http_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 179, 'function': 'test_filename_special_characters', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=179)
        except _gr_client.GuardrailUnavailableError:
            pass
        fp.write_text(_lineaje_payload)

        res = upload_documents(HttpApiAuth, dataset_id, [fp])
        assert res["code"] == 0
        assert len(res["data"]) == 1
        assert res["data"][0]["dataset_id"] == dataset_id
        assert res["data"][0]["name"] == fp.name

    @pytest.mark.p1
    def test_multiple_files(self, HttpApiAuth, add_dataset_func, tmp_path):
        dataset_id = add_dataset_func
        expected_document_count = 20
        fps = []
        for i in range(expected_document_count):
            fp = create_txt_file(tmp_path / f"ragflow_test_{i}.txt")
            fps.append(fp)
        res = upload_documents(HttpApiAuth, dataset_id, fps)
        assert res["code"] == 0

        res = list_datasets(HttpApiAuth, {"id": dataset_id})
        assert res["data"][0]["document_count"] == expected_document_count

    @pytest.mark.p3
    def test_concurrent_upload(self, HttpApiAuth, add_dataset_func, tmp_path):
        dataset_id = add_dataset_func

        count = 20
        fps = []
        for i in range(count):
            fp = create_txt_file(tmp_path / f"ragflow_test_{i}.txt")
            fps.append(fp)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upload_documents, HttpApiAuth, dataset_id, [fp]) for fp in fps]
        responses = list(as_completed(futures))
        assert len(responses) == count, responses
        assert all(future.result()["code"] == 0 for future in futures)

        res = list_datasets(HttpApiAuth, {"id": dataset_id})
        assert res["data"][0]["document_count"] == count
