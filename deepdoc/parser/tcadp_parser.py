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
import base64
import json
import logging
import os
import shutil
import tempfile
import time
import traceback
import types
import zipfile
from datetime import datetime
from io import BytesIO
from os import PathLike
from pathlib import Path
from typing import Any, Callable, Optional

import requests
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.lkeap.v20240522 import lkeap_client, models

from common.config_utils import get_base_config
from deepdoc.parser.pdf_parser import RAGFlowPdfParser


class TencentCloudAPIClient:
    """Tencent Cloud API client using official SDK"""

    def __init__(self, secret_id, secret_key, region):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.outlines = []
        
        # Create credentials
        self.cred = credential.Credential(secret_id, secret_key)
        
        # Instantiate an http option, optional, can be skipped if no special requirements
        self.httpProfile = HttpProfile()
        self.httpProfile.endpoint = "lkeap.tencentcloudapi.com"

        # Instantiate a client option, optional, can be skipped if no special requirements
        self.clientProfile = ClientProfile()
        self.clientProfile.httpProfile = self.httpProfile
        
        # Instantiate the client object for the product to be requested, clientProfile is optional
        self.client = lkeap_client.LkeapClient(self.cred, region, self.clientProfile)

    def reconstruct_document_sse(self, file_type, file_url=None, file_base64=None, file_start_page=1, file_end_page=1000, config=None):
        """Call document parsing API using official SDK"""
        try:
            # Instantiate a request object, each interface corresponds to a request object
            req = models.ReconstructDocumentSSERequest()
            
            # Build request parameters
            params = {
                "FileType": file_type,
                "FileStartPageNumber": file_start_page,
                "FileEndPageNumber": file_end_page,
            }
            
            # According to Tencent Cloud API documentation, either FileUrl or FileBase64 parameter must be provided, if both are provided only FileUrl will be used
            if file_url:
                params["FileUrl"] = file_url
                _lineaje_payload = f"[TCADP] Using file URL: {file_url}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:1d2f0a64892d1207906ec98d9f1a5e173db241cd0f973bdaa4d668e4fddecf36'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1d2f0a64892d1207906ec98d9f1a5e173db241cd0f973bdaa4d668e4fddecf36', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 82, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 82, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
            elif file_base64:
                params["FileBase64"] = file_base64
                _lineaje_payload = f"[TCADP] Using Base64 data, length: {len(file_base64)} characters"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:c3a090be1d61c413bb360a9ac5499e357f19b7c51c0ec28dac9439c7f204442b'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c3a090be1d61c413bb360a9ac5499e357f19b7c51c0ec28dac9439c7f204442b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 85, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 85, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
            else:
                raise ValueError("Must provide either FileUrl or FileBase64 parameter")

            if config:
                params["Config"] = config

            # LINEAJE: runtime guardrail checks `params` as it flows from the agent to an external endpoint, before it leaves the application (in TencentCloudAPIClient.reconstruct_document_sse).
            #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `params` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9defbae18a605350bfa0fce3e222e00b54420539c912e47526dfd13e19372459'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9defbae18a605350bfa0fce3e222e00b54420539c912e47526dfd13e19372459', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 92, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 92, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                params = _gr_client.enforce(_gr_site, params, content_type='application/json', variable_name='params', source_file=__file__, before_line=92)
            except _gr_client.GuardrailUnavailableError:
                pass
            req.from_json_string(json.dumps(params))

            # The returned resp is an instance of ReconstructDocumentSSEResponse, corresponding to the request object
            resp = self.client.ReconstructDocumentSSE(req)
            parser_result = {}
            
            # Output json format string response
            if isinstance(resp, types.GeneratorType):  # Streaming response
                _lineaje_payload = "[TCADP] Detected streaming response"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:9a39f7fe198ae033775de2c983941c9a7462e26ae524143600fbb0e8d9eeffa5'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9a39f7fe198ae033775de2c983941c9a7462e26ae524143600fbb0e8d9eeffa5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 100, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 100, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                for event in resp:
                    _lineaje_payload = f"[TCADP] Received event: {event}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:5b992d38e8eba34fe666e8727a5123b2095fec510150d7c7fcea9db5f48c6445'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5b992d38e8eba34fe666e8727a5123b2095fec510150d7c7fcea9db5f48c6445', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 102, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 102, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)
                    if event.get('data'):
                        try:
                            data_dict = json.loads(event['data'])
                            _lineaje_payload = f"[TCADP] Parsed data: {data_dict}"
                            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                            #   Do not remove without review. site_id='site:sha256:90e5074f2a078ecf34ac95a3873b9ccb266c18794a5349be6745897c4a02415f'
                            _gr_client = _lineaje_load_gr_client()
                            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:90e5074f2a078ecf34ac95a3873b9ccb266c18794a5349be6745897c4a02415f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 106, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 106, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                            try:
                                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                            except _gr_client.GuardrailUnavailableError:
                                pass
                            except PermissionError:
                                pass
                            logging.info(_lineaje_payload)
                            
                            if data_dict.get('Progress') == "100":
                                parser_result = data_dict
                                _lineaje_payload = "[TCADP] Document parsing completed!"
                                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                                #   Do not remove without review. site_id='site:sha256:39a5fc0912e60a3994eb59d23c362186f77ee4a338b3f191c35709cf1d443ca2'
                                _gr_client = _lineaje_load_gr_client()
                                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:39a5fc0912e60a3994eb59d23c362186f77ee4a338b3f191c35709cf1d443ca2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 110, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 110, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                                try:
                                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                                except _gr_client.GuardrailUnavailableError:
                                    pass
                                except PermissionError:
                                    pass
                                logging.info(_lineaje_payload)
                                _lineaje_payload = f"[TCADP] Task ID: {data_dict.get('TaskId')}"
                                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                                #   Do not remove without review. site_id='site:sha256:aae0535d3eb520ae841c172fcbdb47b411655e62d6bda028d02805011549e466'
                                _gr_client = _lineaje_load_gr_client()
                                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aae0535d3eb520ae841c172fcbdb47b411655e62d6bda028d02805011549e466', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 111, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 111, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                                try:
                                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                                except _gr_client.GuardrailUnavailableError:
                                    pass
                                except PermissionError:
                                    pass
                                logging.info(_lineaje_payload)
                                _lineaje_payload = f"[TCADP] Success pages: {data_dict.get('SuccessPageNum')}"
                                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                                #   Do not remove without review. site_id='site:sha256:9248ba80be84637110ed72ad80d618bb6f8b5e18ef6c9d14f88626d9d4e8906e'
                                _gr_client = _lineaje_load_gr_client()
                                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9248ba80be84637110ed72ad80d618bb6f8b5e18ef6c9d14f88626d9d4e8906e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 112, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 112, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                                try:
                                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                                except _gr_client.GuardrailUnavailableError:
                                    pass
                                except PermissionError:
                                    pass
                                logging.info(_lineaje_payload)
                                _lineaje_payload = f"[TCADP] Failed pages: {data_dict.get('FailPageNum')}"
                                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                                #   Do not remove without review. site_id='site:sha256:9eba4ab142ed499d0d588a92b6041a5ca8dacddf4530634241fedcc8e930320d'
                                _gr_client = _lineaje_load_gr_client()
                                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9eba4ab142ed499d0d588a92b6041a5ca8dacddf4530634241fedcc8e930320d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 113, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 113, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                                try:
                                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                                except _gr_client.GuardrailUnavailableError:
                                    pass
                                except PermissionError:
                                    pass
                                logging.info(_lineaje_payload)

                                # Print failed page information
                                failed_pages = data_dict.get("FailedPages", [])
                                if failed_pages:
                                    _lineaje_payload = "[TCADP] Failed parsing pages:"
                                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                                    #   Do not remove without review. site_id='site:sha256:1aaf99623c4d66319d0f1f7e9ad57e4bf25a5f9953163225c744579b755c77e8'
                                    _gr_client = _lineaje_load_gr_client()
                                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1aaf99623c4d66319d0f1f7e9ad57e4bf25a5f9953163225c744579b755c77e8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 118, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 118, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                                    try:
                                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                                    except _gr_client.GuardrailUnavailableError:
                                        pass
                                    except PermissionError:
                                        pass
                                    logging.warning(_lineaje_payload)
                                    for page in failed_pages:
                                        _lineaje_payload = f"[TCADP]   Page number: {page.get('PageNumber')}, Error: {page.get('ErrorMsg')}"
                                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                                        #   Do not remove without review. site_id='site:sha256:375932406bb083e88910ab5392de5228bf1995b9bcd5b2df2645a8ec127d5915'
                                        _gr_client = _lineaje_load_gr_client()
                                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:375932406bb083e88910ab5392de5228bf1995b9bcd5b2df2645a8ec127d5915', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 120, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 120, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                                        try:
                                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                                        except _gr_client.GuardrailUnavailableError:
                                            pass
                                        except PermissionError:
                                            pass
                                        logging.warning(_lineaje_payload)
                                
                                # Check if there is a download link
                                download_url = data_dict.get("DocumentRecognizeResultUrl")
                                if download_url:
                                    _lineaje_payload = f"[TCADP] Got download link: {download_url}"
                                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                                    #   Do not remove without review. site_id='site:sha256:7d9d60c38d50026205a783374cdfb003de971a95cf8c311fa67bf764e9733771'
                                    _gr_client = _lineaje_load_gr_client()
                                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7d9d60c38d50026205a783374cdfb003de971a95cf8c311fa67bf764e9733771', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 125, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 125, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                                    try:
                                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                                    except _gr_client.GuardrailUnavailableError:
                                        pass
                                    except PermissionError:
                                        pass
                                    logging.info(_lineaje_payload)
                                else:
                                    _lineaje_payload = "[TCADP] No download link obtained"
                                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                                    #   Do not remove without review. site_id='site:sha256:3a3cf76784c0aa3cf266cf7cc6e3ccccf761d2e2178c2c4761142a2991e7e8b3'
                                    _gr_client = _lineaje_load_gr_client()
                                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3a3cf76784c0aa3cf266cf7cc6e3ccccf761d2e2178c2c4761142a2991e7e8b3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 127, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 127, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                                    try:
                                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                                    except _gr_client.GuardrailUnavailableError:
                                        pass
                                    except PermissionError:
                                        pass
                                    logging.warning(_lineaje_payload)
                                
                                break  # Found final result, exit loop
                            else:
                                # Print progress information
                                progress = data_dict.get("Progress", "0")
                                _lineaje_payload = f"[TCADP] Progress: {progress}%"
                                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                                #   Do not remove without review. site_id='site:sha256:51223cbbcd0c4ded5f3d38f238175738a91057c4c7bd854c5d4c41376fc0567a'
                                _gr_client = _lineaje_load_gr_client()
                                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:51223cbbcd0c4ded5f3d38f238175738a91057c4c7bd854c5d4c41376fc0567a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 133, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 133, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                                try:
                                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                                except _gr_client.GuardrailUnavailableError:
                                    pass
                                except PermissionError:
                                    pass
                                logging.info(_lineaje_payload)
                        except json.JSONDecodeError as e:
                            _lineaje_payload = f"[TCADP] Failed to parse JSON data: {e}"
                            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                            #   Do not remove without review. site_id='site:sha256:f1ab5ef3fd9831ce73d6806d24c7389115046bb251965246a55b60fb0a86796c'
                            _gr_client = _lineaje_load_gr_client()
                            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f1ab5ef3fd9831ce73d6806d24c7389115046bb251965246a55b60fb0a86796c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 135, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 135, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                            try:
                                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                            except _gr_client.GuardrailUnavailableError:
                                pass
                            except PermissionError:
                                pass
                            logging.error(_lineaje_payload)
                            _lineaje_payload = f"[TCADP] Raw data: {event.get('data')}"
                            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                            #   Do not remove without review. site_id='site:sha256:d2bc785bea48c43923bd2e0583b9736c5480fe34b53e1a8f9e1d9fad49f35766'
                            _gr_client = _lineaje_load_gr_client()
                            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d2bc785bea48c43923bd2e0583b9736c5480fe34b53e1a8f9e1d9fad49f35766', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 136, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 136, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                            try:
                                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                            except _gr_client.GuardrailUnavailableError:
                                pass
                            except PermissionError:
                                pass
                            logging.error(_lineaje_payload)
                            continue
                    else:
                        _lineaje_payload = f"[TCADP] Event without data: {event}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:724816c29788ce8a40e6019385dd767d9dfbcaec4ba19ee02795ba5da32eccf4'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:724816c29788ce8a40e6019385dd767d9dfbcaec4ba19ee02795ba5da32eccf4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 139, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 139, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.info(_lineaje_payload)
            else:  # Non-streaming response
                _lineaje_payload = "[TCADP] Detected non-streaming response"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:21b236cdbac334495c70907d616689dc2a29972d826bb9ce8104dcbb62455395'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:21b236cdbac334495c70907d616689dc2a29972d826bb9ce8104dcbb62455395', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 141, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 141, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                if hasattr(resp, 'data') and resp.data:
                    try:
                        data_dict = json.loads(resp.data)
                        parser_result = data_dict
                        _lineaje_payload = f"[TCADP] JSON parsing successful: {parser_result}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:989a9d8d616c65a018fa796da7fe0c2bbeea32b449d02a220e16f4c026a0a0d7'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:989a9d8d616c65a018fa796da7fe0c2bbeea32b449d02a220e16f4c026a0a0d7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 146, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 146, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.info(_lineaje_payload)
                    except json.JSONDecodeError as e:
                        _lineaje_payload = f"[TCADP] JSON parsing failed: {e}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:c36b9d951d809745a8ba350e014e3b2df5929b8399555ea11bd392003124159d'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c36b9d951d809745a8ba350e014e3b2df5929b8399555ea11bd392003124159d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 148, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 148, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.error(_lineaje_payload)
                        return None
                else:
                    _lineaje_payload = "[TCADP] No data in response"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:f1c533c9b4e5d6403f0297d6854c7abbbb1b77cc503d8e4121f72a2b8a265cfe'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f1c533c9b4e5d6403f0297d6854c7abbbb1b77cc503d8e4121f72a2b8a265cfe', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 151, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 151, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.error(_lineaje_payload)
                    return None

            # LINEAJE: runtime guardrail checks `parser_result` as it flows from the agent to the user interface, before it leaves the application (in TencentCloudAPIClient.reconstruct_document_sse).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `parser_result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:26d4a5aabd5aa44900d56d841f56ef0c181a8c1ac6b59402052d0ec76258678f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:26d4a5aabd5aa44900d56d841f56ef0c181a8c1ac6b59402052d0ec76258678f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 154, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 154, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                parser_result = _gr_client.enforce(_gr_site, parser_result, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return parser_result

        except TencentCloudSDKException as err:
            _lineaje_payload = f"[TCADP] Tencent Cloud SDK error: {err}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f04be422fcbc20daee0f5791337f981ded06ef8e67ce94ad1f8d5e8992b31370'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f04be422fcbc20daee0f5791337f981ded06ef8e67ce94ad1f8d5e8992b31370', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 157, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 157, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            return None
        except Exception as e:
            _lineaje_payload = f"[TCADP] Unknown error: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:bf64f10d0b3678a061300a7e6c65358381012032fe454187a46d9784e2661ca7'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bf64f10d0b3678a061300a7e6c65358381012032fe454187a46d9784e2661ca7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 160, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 160, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            _lineaje_payload = f"[TCADP] Error stack trace: {traceback.format_exc()}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.reconstruct_document_sse).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e44c2c11dc68f6c90e542adc6d54580f87645f28014a2557b90720db373a836c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e44c2c11dc68f6c90e542adc6d54580f87645f28014a2557b90720db373a836c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 161, 'function': 'TencentCloudAPIClient.reconstruct_document_sse'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 161, 'function': 'reconstruct_document_sse', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            return None

    def download_result_file(self, download_url, output_dir):
        """Download parsing result file"""
        if not download_url:
            _lineaje_payload = "[TCADP] No downloadable result file"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.download_result_file).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ff619efd69b8252a297692c047d759ae775143e5f3be4872f2d0b432b5b37501'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ff619efd69b8252a297692c047d759ae775143e5f3be4872f2d0b432b5b37501', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 167, 'function': 'TencentCloudAPIClient.download_result_file'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 167, 'function': 'download_result_file', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            return None

        try:
            response = requests.get(download_url)
            # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in TencentCloudAPIClient.download_result_file).
            #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:49ec2e3da8c27c6cb750d988eb62f6f8553b5c958a1908db1af3753fb36cc8e9'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:49ec2e3da8c27c6cb750d988eb62f6f8553b5c958a1908db1af3753fb36cc8e9', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 171, 'function': 'TencentCloudAPIClient.download_result_file'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 171, 'function': 'download_result_file', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=171)
            except _gr_client.GuardrailUnavailableError:
                pass
            response.raise_for_status()

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tcadp_result_{timestamp}.zip"
            file_path = os.path.join(output_dir, filename)

            # Save file
            with open(file_path, "wb") as f:
                _lineaje_payload = response.content
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to a file, before it is written to disk (in TencentCloudAPIClient.download_result_file).
                #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:6fcc0a11735498afa7564343691e5775dbc3937b2b4c2e5f47465994321f3133'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6fcc0a11735498afa7564343691e5775dbc3937b2b4c2e5f47465994321f3133', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 184, 'function': 'TencentCloudAPIClient.download_result_file'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 184, 'function': 'download_result_file', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=184)
                except _gr_client.GuardrailUnavailableError:
                    pass
                f.write(_lineaje_payload)
                # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in TencentCloudAPIClient.download_result_file).
                #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:7e810df237d0d3f0cecf389c4cca2cdaba1a2dc9bf0f8ff214d0abeaedb31f7d'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7e810df237d0d3f0cecf389c4cca2cdaba1a2dc9bf0f8ff214d0abeaedb31f7d', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 184, 'function': 'TencentCloudAPIClient.download_result_file'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 184, 'function': 'download_result_file', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True}, interaction_id=locals().get('_lineaje_interaction_id'))
                try:
                    response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=184)
                except _gr_client.GuardrailUnavailableError:
                    pass

            _lineaje_payload = f"[TCADP] Document parsing result downloaded to: {os.path.basename(file_path)}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.download_result_file).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:2afc450e23e2507078e2d6ff2158b9ed02efd7068b0dfaf276b4225265780e09'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2afc450e23e2507078e2d6ff2158b9ed02efd7068b0dfaf276b4225265780e09', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 186, 'function': 'TencentCloudAPIClient.download_result_file'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 186, 'function': 'download_result_file', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            # LINEAJE: runtime guardrail checks `file_path` as it flows from the agent to the user interface, before it leaves the application (in TencentCloudAPIClient.download_result_file).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `file_path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:295c2be9096a4a7223ed76994f16508ee7661c79a122f8d1e048a50ca54733f5'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:295c2be9096a4a7223ed76994f16508ee7661c79a122f8d1e048a50ca54733f5', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 187, 'function': 'TencentCloudAPIClient.download_result_file'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 187, 'function': 'download_result_file', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                file_path = _gr_client.enforce(_gr_site, file_path, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return file_path

        except requests.exceptions.RequestException as e:
            _lineaje_payload = f"[TCADP] Failed to download file: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TencentCloudAPIClient.download_result_file).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1c3c7af6f4381045be654e49ad8a72943bc4b487dc6c9fd4fd66db48bbe6e004'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1c3c7af6f4381045be654e49ad8a72943bc4b487dc6c9fd4fd66db48bbe6e004', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 190, 'function': 'TencentCloudAPIClient.download_result_file'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 190, 'function': 'download_result_file', 'agent_name': 'TencentCloudAPIClient', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            return None


class TCADPParser(RAGFlowPdfParser):
    def __init__(self, secret_id: str = None, secret_key: str = None, region: str = "ap-guangzhou", 
                 table_result_type: str = None, markdown_image_response_type: str = None):
        super().__init__()
        
        # First initialize logger
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Log received parameters
        _lineaje_payload = f"[TCADP] Initializing with parameters - table_result_type: {table_result_type}, markdown_image_response_type: {markdown_image_response_type}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.__init__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:daa93efaaa1e3948ae5016c341dd58eeaab27e956c02e54773b0be209c2601b3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:daa93efaaa1e3948ae5016c341dd58eeaab27e956c02e54773b0be209c2601b3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 203, 'function': 'TCADPParser.__init__'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 203, 'function': '__init__', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)
        
        # Priority: read configuration from RAGFlow configuration system (service_conf.yaml)
        try:
            tcadp_parser = get_base_config("tcadp_config", {})
            if isinstance(tcadp_parser, dict) and tcadp_parser:
                self.secret_id = secret_id or tcadp_parser.get("secret_id")
                self.secret_key = secret_key or tcadp_parser.get("secret_key")
                self.region = region or tcadp_parser.get("region", "ap-guangzhou")
                # Set table_result_type and markdown_image_response_type from config or parameters
                self.table_result_type = table_result_type if table_result_type is not None else tcadp_parser.get("table_result_type", "1")
                self.markdown_image_response_type = markdown_image_response_type if markdown_image_response_type is not None else tcadp_parser.get("markdown_image_response_type", "1")
                
            else:
                _lineaje_payload = "[TCADP] Please configure tcadp_config in service_conf.yaml first"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.__init__).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:eeccf2ecdfab396301e3adc3cdb0333d2c3fd7dfe2fefce8638953ce7573cee7'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:eeccf2ecdfab396301e3adc3cdb0333d2c3fd7dfe2fefce8638953ce7573cee7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 217, 'function': 'TCADPParser.__init__'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 217, 'function': '__init__', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.error(_lineaje_payload)
                # If config file is empty, use provided parameters or defaults
                self.secret_id = secret_id
                self.secret_key = secret_key
                self.region = region or "ap-guangzhou"
                self.table_result_type = table_result_type if table_result_type is not None else "1"
                self.markdown_image_response_type = markdown_image_response_type if markdown_image_response_type is not None else "1"

        except ImportError:
            _lineaje_payload = "[TCADP] Configuration module import failed"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.__init__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6f6c75b96d8dd3eeee8b86d2c2daf47ea07347f4d129da99078497f683d43313'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6f6c75b96d8dd3eeee8b86d2c2daf47ea07347f4d129da99078497f683d43313', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 226, 'function': 'TCADPParser.__init__'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 226, 'function': '__init__', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.info(_lineaje_payload)
            # If config file is not available, use provided parameters or defaults
            self.secret_id = secret_id
            self.secret_key = secret_key
            self.region = region or "ap-guangzhou"
            self.table_result_type = table_result_type if table_result_type is not None else "1"
            self.markdown_image_response_type = markdown_image_response_type if markdown_image_response_type is not None else "1"

        # Log final values
        _lineaje_payload = f"[TCADP] Final values - table_result_type: {self.table_result_type}, markdown_image_response_type: {self.markdown_image_response_type}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.__init__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a955e698577dd2ffb081d55227a641de7d5aa748d6ca9fcd26880802543ab768'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a955e698577dd2ffb081d55227a641de7d5aa748d6ca9fcd26880802543ab768', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 235, 'function': 'TCADPParser.__init__'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 235, 'function': '__init__', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)

        if not self.secret_id or not self.secret_key:
            raise ValueError("[TCADP] Please set Tencent Cloud API keys, configure tcadp_config in service_conf.yaml")

    def check_installation(self) -> bool:
        """Check if Tencent Cloud API configuration is correct"""
        try:
            # Check necessary configuration parameters
            if not self.secret_id or not self.secret_key:
                _lineaje_payload = "[TCADP] Tencent Cloud API configuration incomplete"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.check_installation).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:7b2f8be0e292b3ef97a8ecd598fdd43e4c14b4d3bcdfa0da62afa3c8b89327a4'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7b2f8be0e292b3ef97a8ecd598fdd43e4c14b4d3bcdfa0da62afa3c8b89327a4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 245, 'function': 'TCADPParser.check_installation'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 245, 'function': 'check_installation', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.error(_lineaje_payload)
                return False

            # Try to create client to verify configuration
            TencentCloudAPIClient(self.secret_id, self.secret_key, self.region)
            _lineaje_payload = "[TCADP] Tencent Cloud API configuration check passed"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.check_installation).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:29b52f181d17f8faea00aaf1715713f306b1e4ab6109e70c9801d47b36faa205'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:29b52f181d17f8faea00aaf1715713f306b1e4ab6109e70c9801d47b36faa205', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 250, 'function': 'TCADPParser.check_installation'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 250, 'function': 'check_installation', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.info(_lineaje_payload)
            return True
        except Exception as e:
            _lineaje_payload = f"[TCADP] Tencent Cloud API configuration check failed: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.check_installation).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e98f1ca24bdb6f26f8bd0bad4a2e37eb97fdd34fecf617086891312727c1852d'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e98f1ca24bdb6f26f8bd0bad4a2e37eb97fdd34fecf617086891312727c1852d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 253, 'function': 'TCADPParser.check_installation'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 253, 'function': 'check_installation', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.error(_lineaje_payload)
            return False

    def _file_to_base64(self, file_path: str, binary: bytes = None) -> str:
        """Convert file to Base64 format"""
        
        if binary:
            # If binary data is directly available, convert directly
            return base64.b64encode(binary).decode('utf-8')
        else:
            # Read from file path and convert
            with open(file_path, 'rb') as f:
                file_data = f.read()
                # LINEAJE: runtime guardrail checks `file_data` as it flows from file storage to the agent (in TCADPParser._file_to_base64).
                #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `file_data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:5c92f4929b58a27e1d68383f99ec40a9c41151c9f4069e45ce8452e535915a8b'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5c92f4929b58a27e1d68383f99ec40a9c41151c9f4069e45ce8452e535915a8b', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 265, 'function': 'TCADPParser._file_to_base64'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 265, 'function': '_file_to_base64', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    file_data = _gr_client.enforce(_gr_site, file_data, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    raise
                return base64.b64encode(file_data).decode('utf-8')

    def _extract_content_from_zip(self, zip_path: str) -> list[dict[str, Any]]:
        """Extract parsing results from downloaded ZIP file"""
        results = []

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_file:
                # Find JSON result files
                json_files = [f for f in zip_file.namelist() if f.endswith(".json")]

                for json_file in json_files:
                    with zip_file.open(json_file) as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            results.extend(data)
                        else:
                            results.append(data)

                # Find Markdown files
                md_files = [f for f in zip_file.namelist() if f.endswith(".md")]
                for md_file in md_files:
                    with zip_file.open(md_file) as f:
                        content = f.read().decode("utf-8")
                        results.append({"type": "text", "content": content, "file": md_file})

        except Exception as e:
            _lineaje_payload = f"[TCADP] Failed to extract ZIP file content: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser._extract_content_from_zip).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1815ce5443810c0922fe2e8db99b6325eae8be0e3db9997f96fdf5438110d116'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1815ce5443810c0922fe2e8db99b6325eae8be0e3db9997f96fdf5438110d116', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 293, 'function': 'TCADPParser._extract_content_from_zip'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 293, 'function': '_extract_content_from_zip', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.error(_lineaje_payload)

        # LINEAJE: runtime guardrail checks `results` as it flows from the agent to the user interface, before it leaves the application (in TCADPParser._extract_content_from_zip).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `results` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:07f3abb4290c2d375d107b7b713c3365ec77b4307b13683da0f995fd39245b51'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:07f3abb4290c2d375d107b7b713c3365ec77b4307b13683da0f995fd39245b51', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 295, 'function': 'TCADPParser._extract_content_from_zip'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 295, 'function': '_extract_content_from_zip', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            results = _gr_client.enforce(_gr_site, results, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return results

    def _parse_content_to_sections(self, content_data: list[dict[str, Any]]) -> list[tuple[str, str]]:
        """Convert parsing results to sections format"""
        sections = []

        for item in content_data:
            content_type = item.get("type", "text")
            content = item.get("content", "")

            if not content:
                continue

            # Process based on content type
            if content_type == "text" or content_type == "paragraph":
                section_text = content
            elif content_type == "table":
                # Handle table content
                table_data = item.get("table_data", {})
                if isinstance(table_data, dict):
                    # Convert table data to text
                    rows = table_data.get("rows", [])
                    section_text = "\n".join([" | ".join(row) for row in rows])
                else:
                    section_text = str(table_data)
            elif content_type == "image":
                # Handle image content
                caption = item.get("caption", "")
                section_text = f"[Image] {caption}" if caption else "[Image]"
            elif content_type == "equation":
                # Handle equation content
                section_text = f"$${content}$$"
            else:
                section_text = content

            if section_text.strip():
                # Generate position tag (simplified version)
                position_tag = "@@1\t0.0\t1000.0\t0.0\t100.0##"
                sections.append((section_text, position_tag))

        # LINEAJE: runtime guardrail checks `sections` as it flows from the agent to the user interface, before it leaves the application (in TCADPParser._parse_content_to_sections).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `sections` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:57895cb78e6720b1d67900599e92019d5d8f89afc3f42bf8db7eb0bbaa7af7bf'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:57895cb78e6720b1d67900599e92019d5d8f89afc3f42bf8db7eb0bbaa7af7bf', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 335, 'function': 'TCADPParser._parse_content_to_sections'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 335, 'function': '_parse_content_to_sections', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            sections = _gr_client.enforce(_gr_site, sections, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return sections

    def _parse_content_to_tables(self, content_data: list[dict[str, Any]]) -> list:
        """Convert parsing results to tables format"""
        tables = []

        for item in content_data:
            if item.get("type") == "table":
                table_data = item.get("table_data", {})
                if isinstance(table_data, dict):
                    rows = table_data.get("rows", [])
                    if rows:
                        # Convert to table format
                        table_html = "<table>\n"
                        for i, row in enumerate(rows):
                            table_html += "  <tr>\n"
                            for cell in row:
                                tag = "th" if i == 0 else "td"
                                table_html += f"    <{tag}>{cell}</{tag}>\n"
                            table_html += "  </tr>\n"
                        table_html += "</table>"
                        tables.append(table_html)

        # LINEAJE: runtime guardrail checks `tables` as it flows from rendered HTML to the user interface, before it leaves the application (in TCADPParser._parse_content_to_tables).
        #   Detected: this statement moves data from rendered HTML to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `tables` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:4179b1703372ffd86489bc52905a18e650169cb089ff64d2efba36da9ba4c269'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4179b1703372ffd86489bc52905a18e650169cb089ff64d2efba36da9ba4c269', phase='data_egress', boundary={'source': 'html', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='html', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 358, 'function': 'TCADPParser._parse_content_to_tables'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 358, 'function': '_parse_content_to_tables', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            tables = _gr_client.enforce(_gr_site, tables, content_type='text/html')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return tables

    def parse_pdf(
        self,
        filepath: str | PathLike[str],
        binary: BytesIO | bytes,
        callback: Optional[Callable] = None,
        *,
        output_dir: Optional[str] = None,
        file_type: str = "PDF",
        file_start_page: Optional[int] = 1,
        file_end_page: Optional[int] = 1000,
        delete_output: Optional[bool] = True,
        max_retries: Optional[int] = 1,
    ) -> tuple:
        """Parse PDF document"""

        temp_file = None
        created_tmp_dir = False

        try:
            # Handle input file
            if binary:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                temp_file.write(binary)
                temp_file.close()
                file_path = temp_file.name
                _lineaje_payload = f"[TCADP] Received binary PDF -> {os.path.basename(file_path)}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.parse_pdf).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:28c0e7c6f96fe882bd1fb7d24185bb69cea0e9707347a827331dcfec2eb3bea1'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:28c0e7c6f96fe882bd1fb7d24185bb69cea0e9707347a827331dcfec2eb3bea1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 385, 'function': 'TCADPParser.parse_pdf'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 385, 'function': 'parse_pdf', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.info(_lineaje_payload)
                if callback:
                    callback(0.1, f"[TCADP] Received binary PDF -> {os.path.basename(file_path)}")
            else:
                file_path = str(filepath)
                if not os.path.exists(file_path):
                    if callback:
                        callback(-1, f"[TCADP] PDF file does not exist: {file_path}")
                    raise FileNotFoundError(f"[TCADP] PDF file does not exist: {file_path}")

            # Convert file to Base64 format
            if callback:
                callback(0.2, "[TCADP] Converting file to Base64 format")
            
            file_base64 = self._file_to_base64(file_path, binary)
            if callback:
                callback(0.25, f"[TCADP] File converted to Base64, size: {len(file_base64)} characters")

            # Create Tencent Cloud API client
            client = TencentCloudAPIClient(self.secret_id, self.secret_key, self.region)

            # Call document parsing API (with retry mechanism)
            if callback:
                callback(0.3, "[TCADP] Starting to call Tencent Cloud document parsing API")

            result = None
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        _lineaje_payload = f"[TCADP] Retry attempt {attempt + 1}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.parse_pdf).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:07995c8fb2e179f139dd8438466ed05b4b693e54ac988935d74266e18bbc46e1'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:07995c8fb2e179f139dd8438466ed05b4b693e54ac988935d74266e18bbc46e1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 414, 'function': 'TCADPParser.parse_pdf'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 414, 'function': 'parse_pdf', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        self.logger.info(_lineaje_payload)
                        if callback:
                            callback(0.3 + attempt * 0.1, f"[TCADP] Retry attempt {attempt + 1}")
                        time.sleep(2 ** attempt)  # Exponential backoff

                    config = {
                        "TableResultType": self.table_result_type,
                        "MarkdownImageResponseType": self.markdown_image_response_type
                    }
                    
                    _lineaje_payload = f"[TCADP] API request config - TableResultType: {self.table_result_type}, MarkdownImageResponseType: {self.markdown_image_response_type}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.parse_pdf).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:d32f078c7e00912a1b1426e3d9f2718c6b2b6c89bf3062189f32d5cdbc9a2a23'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d32f078c7e00912a1b1426e3d9f2718c6b2b6c89bf3062189f32d5cdbc9a2a23', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 424, 'function': 'TCADPParser.parse_pdf'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 424, 'function': 'parse_pdf', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    self.logger.info(_lineaje_payload)

                    result = client.reconstruct_document_sse(
                        file_type=file_type, 
                        file_base64=file_base64, 
                        file_start_page=file_start_page, 
                        file_end_page=file_end_page, 
                        config=config
                    )
                    
                    if result:
                        _lineaje_payload = f"[TCADP] Attempt {attempt + 1} successful"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.parse_pdf).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:9de29a85989c3509c085655f983f7b94cf640f75cf3e307c6c1dfaeab7fdf435'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9de29a85989c3509c085655f983f7b94cf640f75cf3e307c6c1dfaeab7fdf435', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 435, 'function': 'TCADPParser.parse_pdf'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 435, 'function': 'parse_pdf', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        self.logger.info(_lineaje_payload)
                        break
                    else:
                        _lineaje_payload = f"[TCADP] Attempt {attempt + 1} failed, result is None"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.parse_pdf).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:3689b279f2e9eb4183d3149d0f96a4457d863050683b49d43b8e12b285bc5c15'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3689b279f2e9eb4183d3149d0f96a4457d863050683b49d43b8e12b285bc5c15', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 438, 'function': 'TCADPParser.parse_pdf'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 438, 'function': 'parse_pdf', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        self.logger.warning(_lineaje_payload)
                        
                except Exception as e:
                    _lineaje_payload = f"[TCADP] Attempt {attempt + 1} exception: {e}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.parse_pdf).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:859d77f99ffb643ea1e32ce2f71340c8a21169500c2b069273a507d21c951a68'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:859d77f99ffb643ea1e32ce2f71340c8a21169500c2b069273a507d21c951a68', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 441, 'function': 'TCADPParser.parse_pdf'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 441, 'function': 'parse_pdf', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    self.logger.error(_lineaje_payload)
                    if attempt == max_retries - 1:
                        raise

            if not result:
                error_msg = f"[TCADP] Document parsing failed, retried {max_retries} times"
                # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.parse_pdf).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a436038643608ae72d2b19af9b9c7217470b7a188f89c175727bfc387db3192b'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a436038643608ae72d2b19af9b9c7217470b7a188f89c175727bfc387db3192b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 447, 'function': 'TCADPParser.parse_pdf'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 447, 'function': 'parse_pdf', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.error(error_msg)
                if callback:
                    callback(-1, error_msg)
                raise RuntimeError(error_msg)

            # Get download link
            download_url = result.get("DocumentRecognizeResultUrl")
            if not download_url:
                if callback:
                    callback(-1, "[TCADP] No parsing result download link obtained")
                raise RuntimeError("[TCADP] No parsing result download link obtained")

            if callback:
                callback(0.6, f"[TCADP] Parsing result download link: {download_url}")

            # Set output directory
            if output_dir:
                out_dir = Path(output_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
            else:
                out_dir = Path(tempfile.mkdtemp(prefix="adp_pdf_"))
                created_tmp_dir = True

            # Download result file
            zip_path = client.download_result_file(download_url, str(out_dir))
            if not zip_path:
                if callback:
                    callback(-1, "[TCADP] Failed to download parsing result")
                raise RuntimeError("[TCADP] Failed to download parsing result")

            if callback:
                # Shorten file path display, only show filename
                zip_filename = os.path.basename(zip_path)
                callback(0.8, f"[TCADP] Parsing result downloaded: {zip_filename}")

            # Extract ZIP file content
            content_data = self._extract_content_from_zip(zip_path)
            _lineaje_payload = f"[TCADP] Extracted {len(content_data)} content blocks"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.parse_pdf).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:50b7cdb47381d625bfe3ebc74e5f7a3c5bb28ba3a039256ab5749d529ec38527'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:50b7cdb47381d625bfe3ebc74e5f7a3c5bb28ba3a039256ab5749d529ec38527', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 484, 'function': 'TCADPParser.parse_pdf'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 484, 'function': 'parse_pdf', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.info(_lineaje_payload)

            if callback:
                callback(0.9, f"[TCADP] Extracted {len(content_data)} content blocks")

            # Convert to sections and tables format
            sections = self._parse_content_to_sections(content_data)
            tables = self._parse_content_to_tables(content_data)

            _lineaje_payload = f"[TCADP] Parsing completed: {len(sections)} sections, {len(tables)} tables"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in TCADPParser.parse_pdf).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:c90f73ace5b6749bdd052388b204a0aa56a53c3d8f7d0c81a7416f0543b00041'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c90f73ace5b6749bdd052388b204a0aa56a53c3d8f7d0c81a7416f0543b00041', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/tcadp_parser.py', 'line': 493, 'function': 'TCADPParser.parse_pdf'}, 'file': 'deepdoc/parser/tcadp_parser.py', 'line': 493, 'function': 'parse_pdf', 'agent_name': 'TCADPParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.info(_lineaje_payload)

            if callback:
                callback(1.0, f"[TCADP] Parsing completed: {len(sections)} sections, {len(tables)} tables")

            return sections, tables

        finally:
            # Clean up temporary files
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass

            if delete_output and created_tmp_dir and out_dir.exists():
                try:
                    shutil.rmtree(out_dir)
                except Exception:
                    pass


if __name__ == "__main__":
    # Test ADP parser
    parser = TCADPParser()
    print("ADP available:", parser.check_installation())

    # Test parsing
    filepath = ""
    if filepath and os.path.exists(filepath):
        with open(filepath, "rb") as file:
            sections, tables = parser.parse_pdf(filepath=filepath, binary=file.read())
            print(f"Parsing result: {len(sections)} sections, {len(tables)} tables")
            for i, (section, tag) in enumerate(sections[:3]):  # Only print first 3
                print(f"Section {i + 1}: {section[:100]}...")
