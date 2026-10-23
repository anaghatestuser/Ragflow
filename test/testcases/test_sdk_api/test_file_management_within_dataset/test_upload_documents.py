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
from configs import DOCUMENT_NAME_LIMIT
from utils.file_utils import create_txt_file


class TestDocumentsUpload:
    @pytest.mark.p1
    def test_valid_single_upload(self, add_dataset_func, tmp_path):
        dataset = add_dataset_func
        fp = create_txt_file(tmp_path / "ragflow_test.txt")
        with fp.open("rb") as f:
            blob = f.read()
            # LINEAJE: runtime guardrail checks `blob` as it flows from file storage to the agent (in TestDocumentsUpload.test_valid_single_upload).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `blob` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3d1b8d1ebcef826398a1984d2de0837d025833cf3092f6950884550af436b594'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3d1b8d1ebcef826398a1984d2de0837d025833cf3092f6950884550af436b594', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 30, 'function': 'TestDocumentsUpload.test_valid_single_upload'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 30, 'function': 'test_valid_single_upload', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                blob = _gr_client.enforce(_gr_site, blob, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise

        documents = dataset.upload_documents([{"display_name": fp.name, "blob": blob}])
        for document in documents:
            assert document.dataset_id == dataset.id, str(document)
            assert document.name == fp.name, str(document)

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
    def test_file_type_validation(self, add_dataset_func, generate_test_files, request):
        dataset = add_dataset_func
        fp = generate_test_files[request.node.callspec.params["generate_test_files"]]

        with fp.open("rb") as f:
            blob = f.read()
            # LINEAJE: runtime guardrail checks `blob` as it flows from file storage to the agent (in TestDocumentsUpload.test_file_type_validation).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `blob` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3367a47ec044aefe7a6e585d15ef73fd33afcf6464c7739ccef4ece4c1da62fa'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3367a47ec044aefe7a6e585d15ef73fd33afcf6464c7739ccef4ece4c1da62fa', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 59, 'function': 'TestDocumentsUpload.test_file_type_validation'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 59, 'function': 'test_file_type_validation', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                blob = _gr_client.enforce(_gr_site, blob, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise

        documents = dataset.upload_documents([{"display_name": fp.name, "blob": blob}])
        for document in documents:
            assert document.dataset_id == dataset.id, str(document)
            assert document.name == fp.name, str(document)

    @pytest.mark.p2
    @pytest.mark.parametrize(
        "file_type",
        ["exe", "unknown"],
    )
    def test_unsupported_file_type(self, add_dataset_func, tmp_path, file_type):
        dataset = add_dataset_func
        fp = tmp_path / f"ragflow_test.{file_type}"
        fp.touch()

        with fp.open("rb") as f:
            blob = f.read()
            # LINEAJE: runtime guardrail checks `blob` as it flows from file storage to the agent (in TestDocumentsUpload.test_unsupported_file_type).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `blob` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:28d9adcb3ff7e0bee1f4322bebd206bf47f63e0853ca34a6ef6a06f835e76584'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:28d9adcb3ff7e0bee1f4322bebd206bf47f63e0853ca34a6ef6a06f835e76584', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 77, 'function': 'TestDocumentsUpload.test_unsupported_file_type'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 77, 'function': 'test_unsupported_file_type', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                blob = _gr_client.enforce(_gr_site, blob, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise

        with pytest.raises(Exception) as exception_info:
            dataset.upload_documents([{"display_name": fp.name, "blob": blob}])
        assert str(exception_info.value) == f"ragflow_test.{file_type}: This type of file has not been supported yet!", str(exception_info.value)

    @pytest.mark.p2
    def test_missing_file(self, add_dataset_func):
        dataset = add_dataset_func
        with pytest.raises(Exception) as exception_info:
            dataset.upload_documents([])
        assert str(exception_info.value) == "No file part!", str(exception_info.value)

    @pytest.mark.p3
    def test_empty_file(self, add_dataset_func, tmp_path):
        dataset = add_dataset_func
        fp = tmp_path / "empty.txt"
        fp.touch()

        with fp.open("rb") as f:
            blob = f.read()
            # LINEAJE: runtime guardrail checks `blob` as it flows from file storage to the agent (in TestDocumentsUpload.test_empty_file).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `blob` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:cb1b6fca81c5c4e79e00eb01ef696321a2dc493bd1769d31014e07d80443b881'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cb1b6fca81c5c4e79e00eb01ef696321a2dc493bd1769d31014e07d80443b881', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 97, 'function': 'TestDocumentsUpload.test_empty_file'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 97, 'function': 'test_empty_file', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                blob = _gr_client.enforce(_gr_site, blob, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise

        documents = dataset.upload_documents([{"display_name": fp.name, "blob": blob}])
        for document in documents:
            assert document.size == 0, str(document)

    @pytest.mark.p3
    def test_filename_empty(self, add_dataset_func, tmp_path):
        dataset = add_dataset_func
        fp = create_txt_file(tmp_path / "ragflow_test.txt")

        with fp.open("rb") as f:
            blob = f.read()
            # LINEAJE: runtime guardrail checks `blob` as it flows from file storage to the agent (in TestDocumentsUpload.test_filename_empty).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `blob` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:302a58cf114301017f2b05d435c6cc8c0322c04e3b3ccb06566a71a6e42ec836'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:302a58cf114301017f2b05d435c6cc8c0322c04e3b3ccb06566a71a6e42ec836', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 109, 'function': 'TestDocumentsUpload.test_filename_empty'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 109, 'function': 'test_filename_empty', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                blob = _gr_client.enforce(_gr_site, blob, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise

        with pytest.raises(Exception) as exception_info:
            dataset.upload_documents([{"display_name": "", "blob": blob}])
        assert str(exception_info.value) == "No file selected!", str(exception_info.value)

    @pytest.mark.p2
    def test_filename_max_length(self, add_dataset_func, tmp_path):
        dataset = add_dataset_func
        fp = create_txt_file(tmp_path / f"{'a' * (DOCUMENT_NAME_LIMIT - 4)}.txt")

        with fp.open("rb") as f:
            blob = f.read()
            # LINEAJE: runtime guardrail checks `blob` as it flows from file storage to the agent (in TestDocumentsUpload.test_filename_max_length).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `blob` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:980dcc4adc24c9b15e7cb19eb3142055377902c86b9dbb283eb05f430e56ffaf'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:980dcc4adc24c9b15e7cb19eb3142055377902c86b9dbb283eb05f430e56ffaf', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 121, 'function': 'TestDocumentsUpload.test_filename_max_length'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 121, 'function': 'test_filename_max_length', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                blob = _gr_client.enforce(_gr_site, blob, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise

        documents = dataset.upload_documents([{"display_name": fp.name, "blob": blob}])
        for document in documents:
            assert document.dataset_id == dataset.id, str(document)
            assert document.name == fp.name, str(document)

    @pytest.mark.p2
    def test_duplicate_files(self, add_dataset_func, tmp_path):
        dataset = add_dataset_func
        fp = create_txt_file(tmp_path / "ragflow_test.txt")

        with fp.open("rb") as f:
            blob = f.read()
            # LINEAJE: runtime guardrail checks `blob` as it flows from file storage to the agent (in TestDocumentsUpload.test_duplicate_files).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `blob` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:47099d4e25fd815c7b159b620974f859284285388dbf8e7abb6a34ea9973b9b5'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:47099d4e25fd815c7b159b620974f859284285388dbf8e7abb6a34ea9973b9b5', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 134, 'function': 'TestDocumentsUpload.test_duplicate_files'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 134, 'function': 'test_duplicate_files', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                blob = _gr_client.enforce(_gr_site, blob, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise

        documents = dataset.upload_documents([{"display_name": fp.name, "blob": blob}, {"display_name": fp.name, "blob": blob}])

        assert len(documents) == 2, str(documents)
        for i, document in enumerate(documents):
            assert document.dataset_id == dataset.id, str(document)
            expected_name = fp.name if i == 0 else f"{fp.stem}({i}){fp.suffix}"
            assert document.name == expected_name, str(document)

    @pytest.mark.p2
    def test_same_file_repeat(self, add_dataset_func, tmp_path):
        dataset = add_dataset_func
        fp = create_txt_file(tmp_path / "ragflow_test.txt")

        with fp.open("rb") as f:
            blob = f.read()
            # LINEAJE: runtime guardrail checks `blob` as it flows from file storage to the agent (in TestDocumentsUpload.test_same_file_repeat).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `blob` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:cfe8d6710e63a45d4045dfad9c1073d77fe4e33c98733762b76c158b9739d175'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cfe8d6710e63a45d4045dfad9c1073d77fe4e33c98733762b76c158b9739d175', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 150, 'function': 'TestDocumentsUpload.test_same_file_repeat'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 150, 'function': 'test_same_file_repeat', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                blob = _gr_client.enforce(_gr_site, blob, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise

        for i in range(3):
            documents = dataset.upload_documents([{"display_name": fp.name, "blob": blob}])
            assert len(documents) == 1, str(documents)
            document = documents[0]
            assert document.dataset_id == dataset.id, str(document)
            expected_name = fp.name if i == 0 else f"{fp.stem}({i}){fp.suffix}"
            assert document.name == expected_name, str(document)

    @pytest.mark.p3
    def test_filename_special_characters(self, add_dataset_func, tmp_path):
        dataset = add_dataset_func
        illegal_chars = '<>:"/\\|?*'
        translation_table = str.maketrans({char: "_" for char in illegal_chars})
        safe_filename = string.punctuation.translate(translation_table)
        fp = tmp_path / f"{safe_filename}.txt"
        _lineaje_payload = "Sample text content"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to a file, before it is written to disk (in TestDocumentsUpload.test_filename_special_characters).
        #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:4d570d307686b0fcd4ce17fb1a269fbae38dbb16f72c7f6eb1fe40b434cdb410'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4d570d307686b0fcd4ce17fb1a269fbae38dbb16f72c7f6eb1fe40b434cdb410', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 167, 'function': 'TestDocumentsUpload.test_filename_special_characters'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 167, 'function': 'test_filename_special_characters', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=167)
        except _gr_client.GuardrailUnavailableError:
            pass
        fp.write_text(_lineaje_payload)

        with fp.open("rb") as f:
            blob = f.read()
            # LINEAJE: runtime guardrail checks `blob` as it flows from file storage to the agent (in TestDocumentsUpload.test_filename_special_characters).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `blob` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6792c8a48c9a753b09d21f7b50f5c6ccf624adc382804d30c5342a6e7eb7d65e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6792c8a48c9a753b09d21f7b50f5c6ccf624adc382804d30c5342a6e7eb7d65e', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 170, 'function': 'TestDocumentsUpload.test_filename_special_characters'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 170, 'function': 'test_filename_special_characters', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                blob = _gr_client.enforce(_gr_site, blob, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise

        documents = dataset.upload_documents([{"display_name": fp.name, "blob": blob}])
        assert len(documents) == 1, str(documents)
        document = documents[0]
        assert document.dataset_id == dataset.id, str(document)
        assert document.name == fp.name, str(document)

    @pytest.mark.p1
    def test_multiple_files(self, client, add_dataset_func, tmp_path):
        dataset = add_dataset_func
        expected_document_count = 20
        document_infos = []
        for i in range(expected_document_count):
            fp = create_txt_file(tmp_path / f"ragflow_test_upload_{i}.txt")
            with fp.open("rb") as f:
                blob = f.read()
                # LINEAJE: runtime guardrail checks `blob` as it flows from file storage to the agent (in TestDocumentsUpload.test_multiple_files).
                #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `blob` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:1007b8b5a7ef2b742454fe549d58cdd2f3a1bb1f1312dce3d52dbd78d4f2a75f'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1007b8b5a7ef2b742454fe549d58cdd2f3a1bb1f1312dce3d52dbd78d4f2a75f', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 186, 'function': 'TestDocumentsUpload.test_multiple_files'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 186, 'function': 'test_multiple_files', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    blob = _gr_client.enforce(_gr_site, blob, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    raise
            document_infos.append({"display_name": fp.name, "blob": blob})
        # LINEAJE: runtime guardrail checks `document_infos` as it flows from rag source to the RAG pipeline, before the tool runs (in TestDocumentsUpload.test_multiple_files).
        #   Detected: this statement moves data from rag source to the RAG pipeline with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `document_infos` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f99fa09db88cf56e31a922586fe22ffe4959bf1fd01e18b79ddc96c47858a622'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f99fa09db88cf56e31a922586fe22ffe4959bf1fd01e18b79ddc96c47858a622', phase='pre_tool', boundary={'source': 'rag_source', 'sink': 'rag_pipeline'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_source', destination_type='rag_pipeline', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 188, 'function': 'TestDocumentsUpload.test_multiple_files'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 188, 'function': 'test_multiple_files', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            document_infos = _gr_client.enforce(_gr_site, document_infos, content_type='application/json', variable_name='document_infos', source_file=__file__, before_line=188)
        except _gr_client.GuardrailUnavailableError:
            pass
        documents = dataset.upload_documents(document_infos)
        assert len(documents) == expected_document_count, str(documents)

        retrieved_dataset = client.get_dataset(name=dataset.name)
        assert retrieved_dataset.document_count == expected_document_count, str(retrieved_dataset)

    @pytest.mark.p3
    def test_concurrent_upload(self, client, add_dataset_func, tmp_path):
        dataset = add_dataset_func
        count = 20
        fps = [create_txt_file(tmp_path / f"ragflow_test_{i}.txt") for i in range(count)]

        def upload_file(fp):
            with fp.open("rb") as f:
                blob = f.read()
                # LINEAJE: runtime guardrail checks `blob` as it flows from file storage to the agent (in TestDocumentsUpload.upload_file).
                #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `blob` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:e35c254b2ae95991fbfe13dabf473d60280299dd61c92d2ed37649b68875b8a1'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e35c254b2ae95991fbfe13dabf473d60280299dd61c92d2ed37649b68875b8a1', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 202, 'function': 'TestDocumentsUpload.test_concurrent_upload.upload_file'}, 'file': 'test/testcases/test_sdk_api/test_file_management_within_dataset/test_upload_documents.py', 'line': 202, 'function': 'upload_file', 'agent_name': 'TestDocumentsUpload', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    blob = _gr_client.enforce(_gr_site, blob, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    raise
            return dataset.upload_documents([{"display_name": fp.name, "blob": blob}])

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(upload_file, fp) for fp in fps]
        responses = list(as_completed(futures))
        assert len(responses) == count, responses

        retrieved_dataset = client.get_dataset(name=dataset.name)
        assert retrieved_dataset.document_count == count, str(retrieved_dataset)
