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
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from common import bulk_upload_documents
from utils import compare_by_hash


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
def test_file_type_validation(add_dataset, generate_test_files, request):
    dataset = add_dataset
    fp = generate_test_files[request.node.callspec.params["generate_test_files"]]
    with fp.open("rb") as f:
        blob = f.read()
        # LINEAJE: runtime guardrail checks `blob` as it flows from file storage to the agent (in test_file_type_validation).
        #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `blob` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:400ebb6a1e5408290a95c6409564686ea0f0ce3bc27ef83804f75d7bc46bbc67'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:400ebb6a1e5408290a95c6409564686ea0f0ce3bc27ef83804f75d7bc46bbc67', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_download_document.py', 'line': 44, 'function': 'test_file_type_validation'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_download_document.py', 'line': 44, 'function': 'test_file_type_validation', 'agent_name': 'test_file_type_validation', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            blob = _gr_client.enforce(_gr_site, blob, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise

    documents = dataset.upload_documents([{"display_name": fp.name, "blob": blob}])

    for document in documents:
        with fp.with_stem("ragflow_test_download").open("wb") as f:
            _lineaje_payload = document.download()
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to a file, before it is written to disk (in test_file_type_validation).
            #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b58bde87bf3a4e80b113d68f5bf56a86aa3c0e4b6b3ec5eb224224105f5b4634'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b58bde87bf3a4e80b113d68f5bf56a86aa3c0e4b6b3ec5eb224224105f5b4634', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_download_document.py', 'line': 50, 'function': 'test_file_type_validation'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_download_document.py', 'line': 50, 'function': 'test_file_type_validation', 'agent_name': 'test_file_type_validation', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=50)
            except _gr_client.GuardrailUnavailableError:
                pass
            f.write(_lineaje_payload)

        assert compare_by_hash(fp, fp.with_stem("ragflow_test_download"))


class TestDocumentDownload:
    @pytest.mark.p3
    def test_same_file_repeat(self, add_documents, tmp_path, ragflow_tmp_dir):
        num = 5
        _, documents = add_documents

        for i in range(num):
            download_path = tmp_path / f"ragflow_test_download_{i}.txt"
            with download_path.open("wb") as f:
                _lineaje_payload = documents[0].download()
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to a file, before it is written to disk (in TestDocumentDownload.test_same_file_repeat).
                #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:ddce2813a2bf46049d8248ab12c228a23e0f806881d8f2d49782940ff61320cb'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ddce2813a2bf46049d8248ab12c228a23e0f806881d8f2d49782940ff61320cb', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_download_document.py', 'line': 64, 'function': 'TestDocumentDownload.test_same_file_repeat'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_download_document.py', 'line': 64, 'function': 'test_same_file_repeat', 'agent_name': 'TestDocumentDownload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=64)
                except _gr_client.GuardrailUnavailableError:
                    pass
                f.write(_lineaje_payload)
            assert compare_by_hash(ragflow_tmp_dir / "ragflow_test_upload_0.txt", download_path), f"Downloaded file {i} does not match original"


@pytest.mark.p3
def test_concurrent_download(add_dataset, tmp_path):
    count = 20
    dataset = add_dataset
    documents = bulk_upload_documents(dataset, count, tmp_path)

    def download_doc(document, i):
        download_path = tmp_path / f"ragflow_test_download_{i}.txt"
        with download_path.open("wb") as f:
            _lineaje_payload = document.download()
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to a file, before it is written to disk (in TestDocumentDownload.download_doc).
            #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:4240e176fb02e80819ebadceb8d6eeeb8d445889f7ed1f1020ccb4798d151032'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4240e176fb02e80819ebadceb8d6eeeb8d445889f7ed1f1020ccb4798d151032', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_download_document.py', 'line': 77, 'function': 'test_concurrent_download.download_doc'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_download_document.py', 'line': 77, 'function': 'download_doc', 'agent_name': 'TestDocumentDownload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=77)
            except _gr_client.GuardrailUnavailableError:
                pass
            f.write(_lineaje_payload)
        # assert compare_by_hash(tmp_path / f"ragflow_test_upload_{i}.txt", download_path), str(download_path)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(download_doc, documents[i], i) for i in range(count)]
    responses = list(as_completed(futures))
    assert len(responses) == count, responses

    for i in range(count):
        assert compare_by_hash(
            tmp_path / f"ragflow_test_upload_{i}.txt",
            tmp_path / f"ragflow_test_download_{i}.txt",
        )
