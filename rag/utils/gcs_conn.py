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

import logging
import time
import datetime
from io import BytesIO
from google.cloud import storage
from google.api_core.exceptions import NotFound
from common.decorator import singleton
from common import settings


@singleton
class RAGFlowGCS:
    def __init__(self):
        self.client = None
        self.bucket_name = None
        self.__open__()

    def __open__(self):
        try:
            if self.client:
                self.client = None
        except Exception:
            pass

        try:
            self.client = storage.Client()
            self.bucket_name = settings.GCS["bucket"]
        except Exception:
            _lineaje_payload = "Fail to connect to GCS"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.__open__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b305e03729c8914c67e445afb54f371412449b85d3cb1680eaccffc1963eb883'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b305e03729c8914c67e445afb54f371412449b85d3cb1680eaccffc1963eb883', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 44, 'function': 'RAGFlowGCS.__open__'}, 'file': 'rag/utils/gcs_conn.py', 'line': 44, 'function': '__open__', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)

    def _get_blob_path(self, folder, filename):
        """Helper to construct the path: folder/filename"""
        if not folder:
            # LINEAJE: runtime guardrail checks `filename` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowGCS._get_blob_path).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `filename` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:acf9c4b1969a96a7342d03d55c829448098492fbaaa9c70d9bb9f3047132744b'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:acf9c4b1969a96a7342d03d55c829448098492fbaaa9c70d9bb9f3047132744b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 49, 'function': 'RAGFlowGCS._get_blob_path'}, 'file': 'rag/utils/gcs_conn.py', 'line': 49, 'function': '_get_blob_path', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                filename = _gr_client.enforce(_gr_site, filename, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return filename
        return f"{folder}/{filename}"

    def health(self):
        folder, fnm, binary = "ragflow-health", "health_check", b"_t@@@1"
        try:
            bucket_obj = self.client.bucket(self.bucket_name)
            if not bucket_obj.exists():
                _lineaje_payload = f"Health check failed: Main bucket '{self.bucket_name}' does not exist."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.health).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:fec8d3922ea8b6a77f202d8d1ad1b60b2a1cc156718f092c6dc785b6a0b0be5a'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fec8d3922ea8b6a77f202d8d1ad1b60b2a1cc156718f092c6dc785b6a0b0be5a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 57, 'function': 'RAGFlowGCS.health'}, 'file': 'rag/utils/gcs_conn.py', 'line': 57, 'function': 'health', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                return False

            blob_path = self._get_blob_path(folder, fnm)
            blob = bucket_obj.blob(blob_path)
            blob.upload_from_file(BytesIO(binary), content_type='application/octet-stream')
            return True
        except Exception as e:
            _lineaje_payload = f"Health check failed: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.health).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:c1d30025e24abfec0949597fce528aa8ca564b7480ac555f2d7e837c68a6b7de'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c1d30025e24abfec0949597fce528aa8ca564b7480ac555f2d7e837c68a6b7de', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 65, 'function': 'RAGFlowGCS.health'}, 'file': 'rag/utils/gcs_conn.py', 'line': 65, 'function': 'health', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
            return False

    def put(self, bucket, fnm, binary, tenant_id=None):
        # RENAMED PARAMETER: bucket_name -> bucket (to match interface)
        for _ in range(3):
            try:
                bucket_obj = self.client.bucket(self.bucket_name)
                blob_path = self._get_blob_path(bucket, fnm)
                blob = bucket_obj.blob(blob_path)

                blob.upload_from_file(BytesIO(binary), content_type='application/octet-stream')
                return True
            except NotFound:
                _lineaje_payload = f"Fail to put: Main bucket {self.bucket_name} does not exist."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.put).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f871983259c26baec40985e93a356747021f23873e6f06b7ea4d5cd432c3acf2'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f871983259c26baec40985e93a356747021f23873e6f06b7ea4d5cd432c3acf2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 79, 'function': 'RAGFlowGCS.put'}, 'file': 'rag/utils/gcs_conn.py', 'line': 79, 'function': 'put', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                return False
            except Exception:
                _lineaje_payload = f"Fail to put {bucket}/{fnm}:"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.put).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:30542a0fc40cf0a7ecca2d47542b7e7c099f391b4717dd0d23492e3ca9eb7cc9'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:30542a0fc40cf0a7ecca2d47542b7e7c099f391b4717dd0d23492e3ca9eb7cc9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 82, 'function': 'RAGFlowGCS.put'}, 'file': 'rag/utils/gcs_conn.py', 'line': 82, 'function': 'put', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(_lineaje_payload)
                self.__open__()
                time.sleep(1)
        return False

    def rm(self, bucket, fnm, tenant_id=None):
        # RENAMED PARAMETER: bucket_name -> bucket
        try:
            bucket_obj = self.client.bucket(self.bucket_name)
            blob_path = self._get_blob_path(bucket, fnm)
            blob = bucket_obj.blob(blob_path)
            blob.delete()
        except NotFound:
            pass
        except Exception:
            _lineaje_payload = f"Fail to remove {bucket}/{fnm}:"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.rm).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9de6d1d856770ad1bdccd20ef27daad8cb875d1f5ffecaa7962c00f029e05d01'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9de6d1d856770ad1bdccd20ef27daad8cb875d1f5ffecaa7962c00f029e05d01', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 97, 'function': 'RAGFlowGCS.rm'}, 'file': 'rag/utils/gcs_conn.py', 'line': 97, 'function': 'rm', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)

    def get(self, bucket, filename, tenant_id=None):
        # RENAMED PARAMETER: bucket_name -> bucket
        for _ in range(1):
            try:
                bucket_obj = self.client.bucket(self.bucket_name)
                blob_path = self._get_blob_path(bucket, filename)
                blob = bucket_obj.blob(blob_path)
                return blob.download_as_bytes()
            except NotFound:
                _lineaje_payload = f"File not found {bucket}/{filename} in {self.bucket_name}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.get).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:9f8907a588a5940e0c673d841da569147b661ac877c91b20ea6c6531d88a705c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9f8907a588a5940e0c673d841da569147b661ac877c91b20ea6c6531d88a705c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 108, 'function': 'RAGFlowGCS.get'}, 'file': 'rag/utils/gcs_conn.py', 'line': 108, 'function': 'get', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                return None
            except Exception:
                _lineaje_payload = f"Fail to get {bucket}/{filename}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.get).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:63b28b4988a7950df57c550e1a7d4ef8df1342a1af027127eed3e14f46ba04b3'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:63b28b4988a7950df57c550e1a7d4ef8df1342a1af027127eed3e14f46ba04b3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 111, 'function': 'RAGFlowGCS.get'}, 'file': 'rag/utils/gcs_conn.py', 'line': 111, 'function': 'get', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(_lineaje_payload)
                self.__open__()
                time.sleep(1)
        return None

    def obj_exist(self, bucket, filename, tenant_id=None):
        # RENAMED PARAMETER: bucket_name -> bucket
        try:
            bucket_obj = self.client.bucket(self.bucket_name)
            blob_path = self._get_blob_path(bucket, filename)
            blob = bucket_obj.blob(blob_path)
            return blob.exists()
        except Exception:
            _lineaje_payload = f"obj_exist {bucket}/{filename} got exception"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.obj_exist).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:613c63907251909992a6025427e00d0bbeda43ac3f0aeaab3a32b4f91b883b49'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:613c63907251909992a6025427e00d0bbeda43ac3f0aeaab3a32b4f91b883b49', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 124, 'function': 'RAGFlowGCS.obj_exist'}, 'file': 'rag/utils/gcs_conn.py', 'line': 124, 'function': 'obj_exist', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
            return False

    def bucket_exists(self, bucket):
        # RENAMED PARAMETER: bucket_name -> bucket
        try:
            bucket_obj = self.client.bucket(self.bucket_name)
            return bucket_obj.exists()
        except Exception:
            _lineaje_payload = f"bucket_exist check for {self.bucket_name} got exception"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.bucket_exists).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:4b6f2f670ba03e4bf9463c3a1076fc77eab2b208865dc75861cc8e4a29689b06'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4b6f2f670ba03e4bf9463c3a1076fc77eab2b208865dc75861cc8e4a29689b06', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 133, 'function': 'RAGFlowGCS.bucket_exists'}, 'file': 'rag/utils/gcs_conn.py', 'line': 133, 'function': 'bucket_exists', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
            return False

    def get_presigned_url(self, bucket, fnm, expires, tenant_id=None):
        # RENAMED PARAMETER: bucket_name -> bucket
        for _ in range(10):
            try:
                bucket_obj = self.client.bucket(self.bucket_name)
                blob_path = self._get_blob_path(bucket, fnm)
                blob = bucket_obj.blob(blob_path)

                expiration = expires
                if isinstance(expires, int):
                    expiration = datetime.timedelta(seconds=expires)

                url = blob.generate_signed_url(
                    version="v4",
                    expiration=expiration,
                    method="GET"
                )
                # LINEAJE: runtime guardrail checks `url` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowGCS.get_presigned_url).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `url` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:4ab33a8d912061b9292d474d86457633217575dc15f4209ab23502e353557f29'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4ab33a8d912061b9292d474d86457633217575dc15f4209ab23502e353557f29', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 153, 'function': 'RAGFlowGCS.get_presigned_url'}, 'file': 'rag/utils/gcs_conn.py', 'line': 153, 'function': 'get_presigned_url', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    url = _gr_client.enforce(_gr_site, url, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return url
            except Exception:
                _lineaje_payload = f"Fail to get_presigned {bucket}/{fnm}:"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.get_presigned_url).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:c90647488911771cf88fcaef103f69b5824240067bb0fb2c5c79a9051e8b39e5'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c90647488911771cf88fcaef103f69b5824240067bb0fb2c5c79a9051e8b39e5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 155, 'function': 'RAGFlowGCS.get_presigned_url'}, 'file': 'rag/utils/gcs_conn.py', 'line': 155, 'function': 'get_presigned_url', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(_lineaje_payload)
                self.__open__()
                time.sleep(1)
        return None

    def remove_bucket(self, bucket):
        # RENAMED PARAMETER: bucket_name -> bucket
        try:
            bucket_obj = self.client.bucket(self.bucket_name)
            prefix = f"{bucket}/"

            blobs = list(self.client.list_blobs(self.bucket_name, prefix=prefix))

            if blobs:
                bucket_obj.delete_blobs(blobs)
        except Exception:
            _lineaje_payload = f"Fail to remove virtual bucket (folder) {bucket}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.remove_bucket).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:2798567f7111a426d56104dfd695e453bbf1c17d453b95cc538264cf40f3fba0'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2798567f7111a426d56104dfd695e453bbf1c17d453b95cc538264cf40f3fba0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 171, 'function': 'RAGFlowGCS.remove_bucket'}, 'file': 'rag/utils/gcs_conn.py', 'line': 171, 'function': 'remove_bucket', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)

    def copy(self, src_bucket, src_path, dest_bucket, dest_path):
        # RENAMED PARAMETERS to match original interface
        try:
            bucket_obj = self.client.bucket(self.bucket_name)

            src_blob_path = self._get_blob_path(src_bucket, src_path)
            dest_blob_path = self._get_blob_path(dest_bucket, dest_path)

            src_blob = bucket_obj.blob(src_blob_path)

            if not src_blob.exists():
                _lineaje_payload = f"Source object not found: {src_blob_path}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.copy).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:888fcd02eafac08d39cd04b2b5657b4b596ea017deef45fd7e4169d7a5485b4d'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:888fcd02eafac08d39cd04b2b5657b4b596ea017deef45fd7e4169d7a5485b4d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 184, 'function': 'RAGFlowGCS.copy'}, 'file': 'rag/utils/gcs_conn.py', 'line': 184, 'function': 'copy', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                return False

            bucket_obj.copy_blob(src_blob, bucket_obj, dest_blob_path)
            return True

        except NotFound:
            _lineaje_payload = f"Copy failed: Main bucket {self.bucket_name} does not exist."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.copy).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:284e8fc86c1b3dcfd1fd7c687fed513df03806c3fb18c553ec53d78008c4530b'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:284e8fc86c1b3dcfd1fd7c687fed513df03806c3fb18c553ec53d78008c4530b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 191, 'function': 'RAGFlowGCS.copy'}, 'file': 'rag/utils/gcs_conn.py', 'line': 191, 'function': 'copy', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            return False
        except Exception:
            _lineaje_payload = f"Fail to copy {src_bucket}/{src_path} -> {dest_bucket}/{dest_path}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.copy).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:76d6e02f2799315f30cca8515c4ba3c317860c9865290b1fb6143d35fb53129e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:76d6e02f2799315f30cca8515c4ba3c317860c9865290b1fb6143d35fb53129e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 194, 'function': 'RAGFlowGCS.copy'}, 'file': 'rag/utils/gcs_conn.py', 'line': 194, 'function': 'copy', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
            return False

    def move(self, src_bucket, src_path, dest_bucket, dest_path):
        try:
            if self.copy(src_bucket, src_path, dest_bucket, dest_path):
                self.rm(src_bucket, src_path)
                return True
            else:
                _lineaje_payload = f"Copy failed, move aborted: {src_bucket}/{src_path}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.move).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:3b261b99395dd8efd7350b6c98ecb496a5c9dd36a7cef17481a27cb5323dbd6a'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3b261b99395dd8efd7350b6c98ecb496a5c9dd36a7cef17481a27cb5323dbd6a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 203, 'function': 'RAGFlowGCS.move'}, 'file': 'rag/utils/gcs_conn.py', 'line': 203, 'function': 'move', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                return False
        except Exception:
            _lineaje_payload = f"Fail to move {src_bucket}/{src_path} -> {dest_bucket}/{dest_path}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowGCS.move).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:c6c3eef9de8edcd4949b9e0af20e7c4b8439075cd9e7c06ad8c3ea44a5555194'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c6c3eef9de8edcd4949b9e0af20e7c4b8439075cd9e7c06ad8c3ea44a5555194', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/gcs_conn.py', 'line': 206, 'function': 'RAGFlowGCS.move'}, 'file': 'rag/utils/gcs_conn.py', 'line': 206, 'function': 'move', 'agent_name': 'RAGFlowGCS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
            return False