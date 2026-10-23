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

import logging
import os
import time
from common.decorator import singleton
from azure.identity import ClientSecretCredential, AzureAuthorityHosts
from azure.storage.filedatalake import FileSystemClient
from common import settings


@singleton
class RAGFlowAzureSpnBlob:
    def __init__(self):
        self.conn = None
        self.account_url = os.getenv('ACCOUNT_URL', settings.AZURE["account_url"])
        self.client_id = os.getenv('CLIENT_ID', settings.AZURE["client_id"])
        self.secret = os.getenv('SECRET', settings.AZURE["secret"])
        self.tenant_id = os.getenv('TENANT_ID', settings.AZURE["tenant_id"])
        self.container_name = os.getenv('CONTAINER_NAME', settings.AZURE["container_name"])
        self.__open__()

    def __open__(self):
        try:
            if self.conn:
                self.__close__()
        except Exception:
            pass

        try:
            credentials = ClientSecretCredential(tenant_id=self.tenant_id, client_id=self.client_id, client_secret=self.secret, authority=AzureAuthorityHosts.AZURE_CHINA)
            self.conn = FileSystemClient(account_url=self.account_url, file_system_name=self.container_name, credential=credentials)
        except Exception:
            _lineaje_payload = "Fail to connect %s" % self.account_url
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowAzureSpnBlob.__open__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:5e301d053d38771f8f372bf7fe0e4acf41889f51e6f6ba2df488fbe24c20b1fc'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5e301d053d38771f8f372bf7fe0e4acf41889f51e6f6ba2df488fbe24c20b1fc', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/azure_spn_conn.py', 'line': 48, 'function': 'RAGFlowAzureSpnBlob.__open__'}, 'file': 'rag/utils/azure_spn_conn.py', 'line': 48, 'function': '__open__', 'agent_name': 'RAGFlowAzureSpnBlob', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)

    def __close__(self):
        del self.conn
        self.conn = None

    def health(self):
        _bucket, fnm, binary = "txtxtxtxt1", "txtxtxtxt1", b"_t@@@1"
        f = self.conn.create_file(fnm)
        f.append_data(binary, offset=0, length=len(binary))
        return f.flush_data(len(binary))

    def put(self, bucket, fnm, binary):
        for _ in range(3):
            try:
                f = self.conn.create_file(fnm)
                f.append_data(binary, offset=0, length=len(binary))
                return f.flush_data(len(binary))
            except Exception:
                _lineaje_payload = f"Fail put {bucket}/{fnm}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowAzureSpnBlob.put).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:9f943c009fe9cfd1d4a78602004b89aa17581e2cc56e55a153cb3d076e7aa564'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9f943c009fe9cfd1d4a78602004b89aa17581e2cc56e55a153cb3d076e7aa564', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/azure_spn_conn.py', 'line': 67, 'function': 'RAGFlowAzureSpnBlob.put'}, 'file': 'rag/utils/azure_spn_conn.py', 'line': 67, 'function': 'put', 'agent_name': 'RAGFlowAzureSpnBlob', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
        return None

    def rm(self, bucket, fnm):
        try:
            self.conn.delete_file(fnm)
        except Exception:
            _lineaje_payload = f"Fail rm {bucket}/{fnm}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowAzureSpnBlob.rm).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0664bf7224094f60c7a8a3ce302dada4fee01adeb35e74c4f57a7b8829b0bf21'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0664bf7224094f60c7a8a3ce302dada4fee01adeb35e74c4f57a7b8829b0bf21', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/azure_spn_conn.py', 'line': 77, 'function': 'RAGFlowAzureSpnBlob.rm'}, 'file': 'rag/utils/azure_spn_conn.py', 'line': 77, 'function': 'rm', 'agent_name': 'RAGFlowAzureSpnBlob', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)

    def get(self, bucket, fnm):
        for _ in range(1):
            try:
                client = self.conn.get_file_client(fnm)
                r = client.download_file()
                return r.read()
            except Exception:
                _lineaje_payload = f"fail get {bucket}/{fnm}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowAzureSpnBlob.get).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:577974134da43cb3f73039150e4dc99a78c4251e4042294348f79a9e5f36fe2a'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:577974134da43cb3f73039150e4dc99a78c4251e4042294348f79a9e5f36fe2a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/azure_spn_conn.py', 'line': 86, 'function': 'RAGFlowAzureSpnBlob.get'}, 'file': 'rag/utils/azure_spn_conn.py', 'line': 86, 'function': 'get', 'agent_name': 'RAGFlowAzureSpnBlob', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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

    def obj_exist(self, bucket, fnm):
        try:
            client = self.conn.get_file_client(fnm)
            return client.exists()
        except Exception:
            _lineaje_payload = f"Fail put {bucket}/{fnm}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowAzureSpnBlob.obj_exist).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:dcffb5adb791af1150f03824acb58bdb20a6e782155247d788e46956cf4512b8'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dcffb5adb791af1150f03824acb58bdb20a6e782155247d788e46956cf4512b8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/azure_spn_conn.py', 'line': 96, 'function': 'RAGFlowAzureSpnBlob.obj_exist'}, 'file': 'rag/utils/azure_spn_conn.py', 'line': 96, 'function': 'obj_exist', 'agent_name': 'RAGFlowAzureSpnBlob', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
        return False

    def get_presigned_url(self, bucket, fnm, expires):
        for _ in range(10):
            try:
                return self.conn.get_presigned_url("GET", bucket, fnm, expires)
            except Exception:
                _lineaje_payload = f"fail get {bucket}/{fnm}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowAzureSpnBlob.get_presigned_url).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:ad2d797b77d10c0153b613fdbd9c619efcc209a0d7f35a48dab539435d3c3572'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ad2d797b77d10c0153b613fdbd9c619efcc209a0d7f35a48dab539435d3c3572', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/azure_spn_conn.py', 'line': 104, 'function': 'RAGFlowAzureSpnBlob.get_presigned_url'}, 'file': 'rag/utils/azure_spn_conn.py', 'line': 104, 'function': 'get_presigned_url', 'agent_name': 'RAGFlowAzureSpnBlob', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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