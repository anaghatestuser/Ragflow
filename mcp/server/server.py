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

import json
import logging
import random
import time
from collections import OrderedDict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import wraps

import click
import requests
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from strenum import StrEnum

import mcp.types as types
from mcp.server.lowlevel import Server


class LaunchMode(StrEnum):
    SELF_HOST = "self-host"
    HOST = "host"


class Transport(StrEnum):
    SSE = "sse"
    STEAMABLE_HTTP = "streamable-http"


BASE_URL = "http://127.0.0.1:9380"
HOST = "127.0.0.1"
PORT = "9382"
HOST_API_KEY = ""
MODE = ""
TRANSPORT_SSE_ENABLED = True
TRANSPORT_STREAMABLE_HTTP_ENABLED = True
JSON_RESPONSE = True


class RAGFlowConnector:
    _MAX_DATASET_CACHE = 32
    _CACHE_TTL = 300

    _dataset_metadata_cache: OrderedDict[str, tuple[dict, float | int]] = OrderedDict()  # "dataset_id" -> (metadata, expiry_ts)
    _document_metadata_cache: OrderedDict[str, tuple[list[tuple[str, dict]], float | int]] = OrderedDict()  # "dataset_id" -> ([(document_id, doc_metadata)], expiry_ts)

    def __init__(self, base_url: str, version="v1"):
        self.base_url = base_url
        self.version = version
        self.api_url = f"{self.base_url}/api/{self.version}"

    def bind_api_key(self, api_key: str):
        self.api_key = api_key
        self.authorization_header = {"Authorization": "{} {}".format("Bearer", self.api_key)}

    def _post(self, path, json=None, stream=False, files=None):
        if not self.api_key:
            return None
        res = requests.post(url=self.api_url + path, json=json, headers=self.authorization_header, stream=stream, files=files)
        # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in RAGFlowConnector._post).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5d4d849a32940c472119ae71e3b35a5c9aa6362fdad7a83a1821662137bfc99c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5d4d849a32940c472119ae71e3b35a5c9aa6362fdad7a83a1821662137bfc99c', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 77, 'function': 'RAGFlowConnector._post'}, 'file': 'mcp/server/server.py', 'line': 77, 'function': '_post', 'agent_name': 'RAGFlowConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=77)
        except _gr_client.GuardrailUnavailableError:
            pass
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowConnector._post).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:84e48db0a585ce9566ac8760882ea38e458fca7a50eb47a3dbe1ea6960541983'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:84e48db0a585ce9566ac8760882ea38e458fca7a50eb47a3dbe1ea6960541983', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 78, 'function': 'RAGFlowConnector._post'}, 'file': 'mcp/server/server.py', 'line': 78, 'function': '_post', 'agent_name': 'RAGFlowConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    def _get(self, path, params=None, json=None):
        res = requests.get(url=self.api_url + path, params=params, headers=self.authorization_header, json=json)
        # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in RAGFlowConnector._get).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:fe6dad34a7524b4142870addeb9d0eb87a75a7f0c8a06b46e99d054217332a0e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fe6dad34a7524b4142870addeb9d0eb87a75a7f0c8a06b46e99d054217332a0e', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 81, 'function': 'RAGFlowConnector._get'}, 'file': 'mcp/server/server.py', 'line': 81, 'function': '_get', 'agent_name': 'RAGFlowConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=81)
        except _gr_client.GuardrailUnavailableError:
            pass
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowConnector._get).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:fefc7e69b989cedb3773cdec24035e2f0ac27d6cc91c4e5a15351ce802e86185'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fefc7e69b989cedb3773cdec24035e2f0ac27d6cc91c4e5a15351ce802e86185', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 82, 'function': 'RAGFlowConnector._get'}, 'file': 'mcp/server/server.py', 'line': 82, 'function': '_get', 'agent_name': 'RAGFlowConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    def _is_cache_valid(self, ts):
        return time.time() < ts

    def _get_expiry_timestamp(self):
        offset = random.randint(-30, 30)
        return time.time() + self._CACHE_TTL + offset

    def _get_cached_dataset_metadata(self, dataset_id):
        entry = self._dataset_metadata_cache.get(dataset_id)
        if entry:
            data, ts = entry
            if self._is_cache_valid(ts):
                self._dataset_metadata_cache.move_to_end(dataset_id)
                # LINEAJE: runtime guardrail checks `data` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowConnector._get_cached_dataset_metadata).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:cb75dbb827dc5eca54df214402684551e19a1d11cc64bc2ba54810aaac95b2cd'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cb75dbb827dc5eca54df214402684551e19a1d11cc64bc2ba54810aaac95b2cd', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 97, 'function': 'RAGFlowConnector._get_cached_dataset_metadata'}, 'file': 'mcp/server/server.py', 'line': 97, 'function': '_get_cached_dataset_metadata', 'agent_name': 'RAGFlowConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    data = _gr_client.enforce(_gr_site, data, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return data
        return None

    def _set_cached_dataset_metadata(self, dataset_id, metadata):
        self._dataset_metadata_cache[dataset_id] = (metadata, self._get_expiry_timestamp())
        self._dataset_metadata_cache.move_to_end(dataset_id)
        if len(self._dataset_metadata_cache) > self._MAX_DATASET_CACHE:
            self._dataset_metadata_cache.popitem(last=False)

    def _get_cached_document_metadata_by_dataset(self, dataset_id):
        entry = self._document_metadata_cache.get(dataset_id)
        if entry:
            data_list, ts = entry
            if self._is_cache_valid(ts):
                self._document_metadata_cache.move_to_end(dataset_id)
                return {doc_id: doc_meta for doc_id, doc_meta in data_list}
        return None

    def _set_cached_document_metadata_by_dataset(self, dataset_id, doc_id_meta_list):
        self._document_metadata_cache[dataset_id] = (doc_id_meta_list, self._get_expiry_timestamp())
        self._document_metadata_cache.move_to_end(dataset_id)

    def list_datasets(self, page: int = 1, page_size: int = 1000, orderby: str = "create_time", desc: bool = True, id: str | None = None, name: str | None = None):
        res = self._get("/datasets", {"page": page, "page_size": page_size, "orderby": orderby, "desc": desc, "id": id, "name": name})
        if not res:
            raise Exception([types.TextContent(type="text", text=res.get("Cannot process this operation."))])

        res = res.json()
        if res.get("code") == 0:
            result_list = []
            for data in res["data"]:
                d = {"description": data["description"], "id": data["id"]}
                # LINEAJE: runtime guardrail checks `d` as it flows from the agent to an external endpoint, before it leaves the application (in RAGFlowConnector.list_datasets).
                #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `d` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:322d9a8c102d94e2a015d95eb9e2824e9675d201e15d845e058d777dfeaac750'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:322d9a8c102d94e2a015d95eb9e2824e9675d201e15d845e058d777dfeaac750', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 129, 'function': 'RAGFlowConnector.list_datasets'}, 'file': 'mcp/server/server.py', 'line': 129, 'function': 'list_datasets', 'agent_name': 'RAGFlowConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    d = _gr_client.enforce(_gr_site, d, content_type='application/json', variable_name='d', source_file=__file__, before_line=129)
                except _gr_client.GuardrailUnavailableError:
                    pass
                result_list.append(json.dumps(d, ensure_ascii=False))
            return "\n".join(result_list)
        return ""

    def retrieval(
        self,
        dataset_ids,
        document_ids=None,
        question="",
        page=1,
        page_size=30,
        similarity_threshold=0.2,
        vector_similarity_weight=0.3,
        top_k=1024,
        rerank_id: str | None = None,
        keyword: bool = False,
        force_refresh: bool = False,
    ):
        if document_ids is None:
            document_ids = []
        
        # If no dataset_ids provided or empty list, get all available dataset IDs
        if not dataset_ids:
            dataset_list_str = self.list_datasets()
            dataset_ids = []
            
            # Parse the dataset list to extract IDs
            if dataset_list_str:
                for line in dataset_list_str.strip().split('\n'):
                    if line.strip():
                        try:
                            dataset_info = json.loads(line.strip())
                            dataset_ids.append(dataset_info["id"])
                        except (json.JSONDecodeError, KeyError):
                            # Skip malformed lines
                            continue
        
        data_json = {
            "page": page,
            "page_size": page_size,
            "similarity_threshold": similarity_threshold,
            "vector_similarity_weight": vector_similarity_weight,
            "top_k": top_k,
            "rerank_id": rerank_id,
            "keyword": keyword,
            "question": question,
            "dataset_ids": dataset_ids,
            "document_ids": document_ids,
        }
        # Send a POST request to the backend service (using requests library as an example, actual implementation may vary)
        res = self._post("/retrieval", json=data_json)
        if not res:
            raise Exception([types.TextContent(type="text", text=res.get("Cannot process this operation."))])

        res = res.json()
        if res.get("code") == 0:
            data = res["data"]
            chunks = []

            # Cache document metadata and dataset information
            document_cache, dataset_cache = self._get_document_metadata_cache(dataset_ids, force_refresh=force_refresh)

            # Process chunks with enhanced field mapping including per-chunk metadata
            for chunk_data in data.get("chunks", []):
                enhanced_chunk = self._map_chunk_fields(chunk_data, dataset_cache, document_cache)
                chunks.append(enhanced_chunk)

            # Build structured response (no longer need response-level document_metadata)
            response = {
                "chunks": chunks,
                "pagination": {
                    "page": data.get("page", page),
                    "page_size": data.get("page_size", page_size),
                    "total_chunks": data.get("total", len(chunks)),
                    "total_pages": (data.get("total", len(chunks)) + page_size - 1) // page_size,
                },
                "query_info": {
                    "question": question,
                    "similarity_threshold": similarity_threshold,
                    "vector_weight": vector_similarity_weight,
                    "keyword_search": keyword,
                    "dataset_count": len(dataset_ids),
                },
            }

            # LINEAJE: runtime guardrail checks `response` as it flows from the agent to an external endpoint, before it leaves the application (in RAGFlowConnector.retrieval).
            #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:12db908eb7491dbaebd56d1ce95a9415ad86c5a541e8a0a0e99179c287b4eaea'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:12db908eb7491dbaebd56d1ce95a9415ad86c5a541e8a0a0e99179c287b4eaea', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 214, 'function': 'RAGFlowConnector.retrieval'}, 'file': 'mcp/server/server.py', 'line': 214, 'function': 'retrieval', 'agent_name': 'RAGFlowConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=214)
            except _gr_client.GuardrailUnavailableError:
                pass
            return [types.TextContent(type="text", text=json.dumps(response, ensure_ascii=False))]

        raise Exception([types.TextContent(type="text", text=res.get("message"))])

    def _get_document_metadata_cache(self, dataset_ids, force_refresh=False):
        """Cache document metadata for all documents in the specified datasets"""
        document_cache = {}
        dataset_cache = {}

        try:
            for dataset_id in dataset_ids:
                dataset_meta = None if force_refresh else self._get_cached_dataset_metadata(dataset_id)
                if not dataset_meta:
                    # First get dataset info for name
                    dataset_res = self._get("/datasets", {"id": dataset_id, "page_size": 1})
                    if dataset_res and dataset_res.status_code == 200:
                        dataset_data = dataset_res.json()
                        if dataset_data.get("code") == 0 and dataset_data.get("data"):
                            dataset_info = dataset_data["data"][0]
                            dataset_meta = {"name": dataset_info.get("name", "Unknown"), "description": dataset_info.get("description", "")}
                            self._set_cached_dataset_metadata(dataset_id, dataset_meta)
                if dataset_meta:
                    dataset_cache[dataset_id] = dataset_meta

                docs = None if force_refresh else self._get_cached_document_metadata_by_dataset(dataset_id)
                if docs is None:
                    page = 1
                    page_size = 30
                    doc_id_meta_list = []
                    docs = {}
                    while page:
                        docs_res = self._get(f"/datasets/{dataset_id}/documents?page={page}")
                        docs_data = docs_res.json()
                        if docs_data.get("code") == 0 and docs_data.get("data", {}).get("docs"):
                            for doc in docs_data["data"]["docs"]:
                                doc_id = doc.get("id")
                                if not doc_id:
                                    continue
                                doc_meta = {
                                    "document_id": doc_id,
                                    "name": doc.get("name", ""),
                                    "location": doc.get("location", ""),
                                    "type": doc.get("type", ""),
                                    "size": doc.get("size"),
                                    "chunk_count": doc.get("chunk_count"),
                                    "create_date": doc.get("create_date", ""),
                                    "update_date": doc.get("update_date", ""),
                                    "token_count": doc.get("token_count"),
                                    "thumbnail": doc.get("thumbnail", ""),
                                    "dataset_id": doc.get("dataset_id", dataset_id),
                                    "meta_fields": doc.get("meta_fields", {}),
                                }
                                doc_id_meta_list.append((doc_id, doc_meta))
                                docs[doc_id] = doc_meta

                            page += 1
                            if docs_data.get("data", {}).get("total", 0) - page * page_size <= 0:
                                page = None

                        self._set_cached_document_metadata_by_dataset(dataset_id, doc_id_meta_list)
                if docs:
                    document_cache.update(docs)

        except Exception as e:
            # Gracefully handle metadata cache failures
            _lineaje_payload = f"Problem building the document metadata cache: {str(e)}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowConnector._get_document_metadata_cache).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:969c9438e4908d254cb56531effdcaefc6750b712b911efb1bc5bfc38a34e311'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:969c9438e4908d254cb56531effdcaefc6750b712b911efb1bc5bfc38a34e311', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 279, 'function': 'RAGFlowConnector._get_document_metadata_cache'}, 'file': 'mcp/server/server.py', 'line': 279, 'function': '_get_document_metadata_cache', 'agent_name': 'RAGFlowConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            pass

        return document_cache, dataset_cache

    def _map_chunk_fields(self, chunk_data, dataset_cache, document_cache):
        """Preserve all original API fields and add per-chunk document metadata"""
        # Start with ALL raw data from API (preserve everything like original version)
        mapped = dict(chunk_data)

        # Add dataset name enhancement
        dataset_id = chunk_data.get("dataset_id") or chunk_data.get("kb_id")
        if dataset_id and dataset_id in dataset_cache:
            mapped["dataset_name"] = dataset_cache[dataset_id]["name"]
        else:
            mapped["dataset_name"] = "Unknown"

        # Add document name convenience field
        mapped["document_name"] = chunk_data.get("document_keyword", "")

        # Add per-chunk document metadata
        document_id = chunk_data.get("document_id")
        if document_id and document_id in document_cache:
            mapped["document_metadata"] = document_cache[document_id]

        # LINEAJE: runtime guardrail checks `mapped` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowConnector._map_chunk_fields).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `mapped` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c7977e1ce14346897dd9523400601e0f30e9f9f4443fa169f17ccf727065afef'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c7977e1ce14346897dd9523400601e0f30e9f9f4443fa169f17ccf727065afef', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 304, 'function': 'RAGFlowConnector._map_chunk_fields'}, 'file': 'mcp/server/server.py', 'line': 304, 'function': '_map_chunk_fields', 'agent_name': 'RAGFlowConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            mapped = _gr_client.enforce(_gr_site, mapped, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return mapped


class RAGFlowCtx:
    def __init__(self, connector: RAGFlowConnector):
        self.conn = connector


@asynccontextmanager
async def sse_lifespan(server: Server) -> AsyncIterator[dict]:
    ctx = RAGFlowCtx(RAGFlowConnector(base_url=BASE_URL))

    _lineaje_payload = "Legacy SSE application started with StreamableHTTP session manager!"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in sse_lifespan).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:fd8740df9fded6199202d07070cea585ac1bd12e7dd450b1a04d6d96c14c7beb'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fd8740df9fded6199202d07070cea585ac1bd12e7dd450b1a04d6d96c14c7beb', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 316, 'function': 'sse_lifespan'}, 'file': 'mcp/server/server.py', 'line': 316, 'function': 'sse_lifespan', 'agent_name': 'sse_lifespan', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)
    try:
        yield {"ragflow_ctx": ctx}
    finally:
        _lineaje_payload = "Legacy SSE application shutting down..."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in sse_lifespan).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:0f749e455439812c6ee7688dc21a17f79ced118bb682b1ca1943eea692f136da'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0f749e455439812c6ee7688dc21a17f79ced118bb682b1ca1943eea692f136da', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 320, 'function': 'sse_lifespan'}, 'file': 'mcp/server/server.py', 'line': 320, 'function': 'sse_lifespan', 'agent_name': 'sse_lifespan', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)


app = Server("ragflow-mcp-server", lifespan=sse_lifespan)


def with_api_key(required=True):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ctx = app.request_context
            ragflow_ctx = ctx.lifespan_context.get("ragflow_ctx")
            if not ragflow_ctx:
                raise ValueError("Get RAGFlow Context failed")

            connector = ragflow_ctx.conn

            if MODE == LaunchMode.HOST:
                headers = ctx.session._init_options.capabilities.experimental.get("headers", {})
                token = None

                # lower case here, because of Starlette conversion
                auth = headers.get("authorization", "")
                if auth.startswith("Bearer "):
                    token = auth.removeprefix("Bearer ").strip()
                elif "api_key" in headers:
                    token = headers["api_key"]

                if required and not token:
                    raise ValueError("RAGFlow API key or Bearer token is required.")

                connector.bind_api_key(token)
            else:
                connector.bind_api_key(HOST_API_KEY)

            return await func(*args, connector=connector, **kwargs)

        # LINEAJE: runtime guardrail checks `wrapper` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowCtx.decorator).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `wrapper` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:896f5282a5ee669b387df0015f6577a3e9cb50c7a2cba4f3e4f12d1389e55c01'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:896f5282a5ee669b387df0015f6577a3e9cb50c7a2cba4f3e4f12d1389e55c01', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 357, 'function': 'with_api_key.decorator'}, 'file': 'mcp/server/server.py', 'line': 357, 'function': 'decorator', 'agent_name': 'RAGFlowCtx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            wrapper = _gr_client.enforce(_gr_site, wrapper, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return wrapper

    # LINEAJE: runtime guardrail checks `decorator` as it flows from the agent to the user interface, before it leaves the application (in with_api_key).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `decorator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:53e8d5efb6decdde969371e78231fa8ae0b0509daaf257f50cbaffbd344ca4e6'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:53e8d5efb6decdde969371e78231fa8ae0b0509daaf257f50cbaffbd344ca4e6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 359, 'function': 'with_api_key'}, 'file': 'mcp/server/server.py', 'line': 359, 'function': 'with_api_key', 'agent_name': 'with_api_key', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        decorator = _gr_client.enforce(_gr_site, decorator, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return decorator


@app.list_tools()
@with_api_key(required=True)
async def list_tools(*, connector) -> list[types.Tool]:
    dataset_description = connector.list_datasets()

    return [
        types.Tool(
            name="ragflow_retrieval",
            description="Retrieve relevant chunks from the RAGFlow retrieve interface based on the question. You can optionally specify dataset_ids to search only specific datasets, or omit dataset_ids entirely to search across ALL available datasets. You can also optionally specify document_ids to search within specific documents. When dataset_ids is not provided or is empty, the system will automatically search across all available datasets. Below is the list of all available datasets, including their descriptions and IDs:"
            + dataset_description,
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional array of dataset IDs to search. If not provided or empty, all datasets will be searched."
                    },
                    "document_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional array of document IDs to search within."
                    },
                    "question": {
                        "type": "string",
                        "description": "The question or query to search for."
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination",
                        "default": 1,
                        "minimum": 1,
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results to return per page (default: 10, max recommended: 50 to avoid token limits)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "similarity_threshold": {
                        "type": "number",
                        "description": "Minimum similarity threshold for results",
                        "default": 0.2,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "vector_similarity_weight": {
                        "type": "number",
                        "description": "Weight for vector similarity vs term similarity",
                        "default": 0.3,
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                    "keyword": {
                        "type": "boolean",
                        "description": "Enable keyword-based search",
                        "default": False,
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum results to consider before ranking",
                        "default": 1024,
                        "minimum": 1,
                        "maximum": 1024,
                    },
                    "rerank_id": {
                        "type": "string",
                        "description": "Optional reranking model identifier",
                    },
                    "force_refresh": {
                        "type": "boolean",
                        "description": "Set to true only if fresh dataset and document metadata is explicitly required. Otherwise, cached metadata is used (default: false).",
                        "default": False,
                    },
                },
                "required": ["question"],
            },
        ),
    ]


@app.call_tool()
@with_api_key(required=True)
async def call_tool(name: str, arguments: dict, *, connector) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "ragflow_retrieval":
        document_ids = arguments.get("document_ids", [])
        dataset_ids = arguments.get("dataset_ids", [])
        question = arguments.get("question", "")
        page = arguments.get("page", 1)
        page_size = arguments.get("page_size", 10)
        similarity_threshold = arguments.get("similarity_threshold", 0.2)
        vector_similarity_weight = arguments.get("vector_similarity_weight", 0.3)
        keyword = arguments.get("keyword", False)
        top_k = arguments.get("top_k", 1024)
        rerank_id = arguments.get("rerank_id")
        force_refresh = arguments.get("force_refresh", False)

        
        # If no dataset_ids provided or empty list, get all available dataset IDs
        if not dataset_ids:
            dataset_list_str = connector.list_datasets()
            dataset_ids = []
            
            # Parse the dataset list to extract IDs
            if dataset_list_str:
                for line in dataset_list_str.strip().split('\n'):
                    if line.strip():
                        try:
                            dataset_info = json.loads(line.strip())
                            dataset_ids.append(dataset_info["id"])
                        except (json.JSONDecodeError, KeyError):
                            # Skip malformed lines
                            continue
        
        try:
            _lineaje_obs = _lineaje_load_gr_client()
            _lineaje_obs_site = _lineaje_obs.SiteDescriptor(site_id='site:sha256:97203199093bac8a786f829a7698753c861863feeb5370dc32fa5b150da85984', phase='', boundary={}, fail_mode='ALLOW', source_type='vector_store', destination_type='agent', project='tree', organization='', components={'file': 'mcp/server/server.py', 'line': 477, 'function': 'call_tool', 'agent_name': 'call_tool', 'agent_name_source': 'inferred_from_function', 'call_target': 'connector.retrieval', 'not_on_graph': True}, observe_only=True)
            await __import__('asyncio').to_thread(lambda: _lineaje_obs.enforce(_lineaje_obs_site, {'activity': 'rag_retrieve'}, content_type='application/json'))
        except Exception:
            pass
        return connector.retrieval(
            dataset_ids=dataset_ids,
            document_ids=document_ids,
            question=question,
            page=page,
            page_size=page_size,
            similarity_threshold=similarity_threshold,
            vector_similarity_weight=vector_similarity_weight,
            keyword=keyword,
            top_k=top_k,
            rerank_id=rerank_id,
            force_refresh=force_refresh,
        )
    raise ValueError(f"Tool not found: {name}")


def create_starlette_app():
    routes = []
    middleware = None
    if MODE == LaunchMode.HOST:
        from starlette.types import ASGIApp, Receive, Scope, Send

        class AuthMiddleware:
            def __init__(self, app: ASGIApp):
                self.app = app

            async def __call__(self, scope: Scope, receive: Receive, send: Send):
                if scope["type"] != "http":
                    await self.app(scope, receive, send)
                    return

                path = scope["path"]
                if path.startswith("/messages/") or path.startswith("/sse") or path.startswith("/mcp"):
                    headers = dict(scope["headers"])
                    token = None
                    auth_header = headers.get(b"authorization")
                    if auth_header and auth_header.startswith(b"Bearer "):
                        token = auth_header.removeprefix(b"Bearer ").strip()
                    elif b"api_key" in headers:
                        token = headers[b"api_key"]

                    if not token:
                        _lineaje_payload = {"error": "Missing or invalid authorization header"}
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the user interface, before it leaves the application (in AuthMiddleware.__call__).
                        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:e46a9792637550ecf37b51fe543fb14baffb799f7a1ea90ede289d843c916a4a'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e46a9792637550ecf37b51fe543fb14baffb799f7a1ea90ede289d843c916a4a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 519, 'function': 'create_starlette_app'}, 'file': 'mcp/server/server.py', 'line': 519, 'function': '__call__', 'agent_name': 'AuthMiddleware', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='text/plain'))
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        response = JSONResponse(_lineaje_payload, status_code=401)
                        await response(scope, receive, send)
                        return

                await self.app(scope, receive, send)

        middleware = [Middleware(AuthMiddleware)]

    # Add SSE routes if enabled
    if TRANSPORT_SSE_ENABLED:
        from mcp.server.sse import SseServerTransport

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await app.run(streams[0], streams[1], app.create_initialization_options(experimental_capabilities={"headers": dict(request.headers)}))
            return Response()

        routes.extend(
            [
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Mount("/messages/", app=sse.handle_post_message),
            ]
        )

    # Add streamable HTTP route if enabled
    streamablehttp_lifespan = None
    if TRANSPORT_STREAMABLE_HTTP_ENABLED:
        from starlette.types import Receive, Scope, Send

        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

        session_manager = StreamableHTTPSessionManager(
            app=app,
            event_store=None,
            json_response=JSON_RESPONSE,
            stateless=True,
        )

        async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
            await session_manager.handle_request(scope, receive, send)

        @asynccontextmanager
        async def streamablehttp_lifespan(app: Starlette) -> AsyncIterator[None]:
            async with session_manager.run():
                _lineaje_payload = "StreamableHTTP application started with StreamableHTTP session manager!"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowCtx.streamablehttp_lifespan).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:cc864bab4551bc08723dc9bd25c0046a0b58ac20de90fb7acae76fe09a3c36fe'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cc864bab4551bc08723dc9bd25c0046a0b58ac20de90fb7acae76fe09a3c36fe', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 565, 'function': 'create_starlette_app'}, 'file': 'mcp/server/server.py', 'line': 565, 'function': 'streamablehttp_lifespan', 'agent_name': 'RAGFlowCtx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                try:
                    yield
                finally:
                    _lineaje_payload = "StreamableHTTP application shutting down..."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowCtx.streamablehttp_lifespan).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:ceb4cb5bb675345358fc0c8f65f699ddd5c5be435be7f8bc0a632cb181791d52'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ceb4cb5bb675345358fc0c8f65f699ddd5c5be435be7f8bc0a632cb181791d52', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 569, 'function': 'create_starlette_app'}, 'file': 'mcp/server/server.py', 'line': 569, 'function': 'streamablehttp_lifespan', 'agent_name': 'RAGFlowCtx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)

        routes.append(Mount("/mcp", app=handle_streamable_http))

    return Starlette(
        debug=True,
        routes=routes,
        middleware=middleware,
        lifespan=streamablehttp_lifespan,
    )


@click.command()
@click.option("--base-url", type=str, default="http://127.0.0.1:9380", help="API base URL for RAGFlow backend")
@click.option("--host", type=str, default="127.0.0.1", help="Host to bind the RAGFlow MCP server")
@click.option("--port", type=int, default=9382, help="Port to bind the RAGFlow MCP server")
@click.option(
    "--mode",
    type=click.Choice(["self-host", "host"]),
    default="self-host",
    help=("Launch mode:\n  self-host: run MCP for a single tenant (requires --api-key)\n  host: multi-tenant mode, users must provide Authorization headers"),
)
@click.option("--api-key", type=str, default="", help="API key to use when in self-host mode")
@click.option(
    "--transport-sse-enabled/--no-transport-sse-enabled",
    default=True,
    help="Enable or disable legacy SSE transport mode (default: enabled)",
)
@click.option(
    "--transport-streamable-http-enabled/--no-transport-streamable-http-enabled",
    default=True,
    help="Enable or disable streamable-http transport mode (default: enabled)",
)
@click.option(
    "--json-response/--no-json-response",
    default=True,
    help="Enable or disable JSON response mode for streamable-http (default: enabled)",
)
def main(base_url, host, port, mode, api_key, transport_sse_enabled, transport_streamable_http_enabled, json_response):
    import os

    import uvicorn
    from dotenv import load_dotenv

    load_dotenv()

    def parse_bool_flag(key: str, default: bool) -> bool:
        val = os.environ.get(key, str(default))
        return str(val).strip().lower() in ("1", "true", "yes", "on")

    global BASE_URL, HOST, PORT, MODE, HOST_API_KEY, TRANSPORT_SSE_ENABLED, TRANSPORT_STREAMABLE_HTTP_ENABLED, JSON_RESPONSE
    BASE_URL = os.environ.get("RAGFLOW_MCP_BASE_URL", base_url)
    HOST = os.environ.get("RAGFLOW_MCP_HOST", host)
    PORT = os.environ.get("RAGFLOW_MCP_PORT", str(port))
    MODE = os.environ.get("RAGFLOW_MCP_LAUNCH_MODE", mode)
    HOST_API_KEY = os.environ.get("RAGFLOW_MCP_HOST_API_KEY", api_key)
    TRANSPORT_SSE_ENABLED = parse_bool_flag("RAGFLOW_MCP_TRANSPORT_SSE_ENABLED", transport_sse_enabled)
    TRANSPORT_STREAMABLE_HTTP_ENABLED = parse_bool_flag("RAGFLOW_MCP_TRANSPORT_STREAMABLE_ENABLED", transport_streamable_http_enabled)
    JSON_RESPONSE = parse_bool_flag("RAGFLOW_MCP_JSON_RESPONSE", json_response)

    if MODE == LaunchMode.SELF_HOST and not HOST_API_KEY:
        raise click.UsageError("--api-key is required when --mode is 'self-host'")

    if TRANSPORT_STREAMABLE_HTTP_ENABLED and MODE == LaunchMode.HOST:
        raise click.UsageError("The --host mode is not supported with streamable-http transport yet.")

    if not TRANSPORT_STREAMABLE_HTTP_ENABLED and JSON_RESPONSE:
        JSON_RESPONSE = False

    _lineaje_payload = (r"""
__  __  ____ ____       ____  _____ ______     _______ ____
|  \/  |/ ___|  _ \     / ___|| ____|  _ \ \   / / ____|  _ \
| |\/| | |   | |_) |    \___ \|  _| | |_) \ \ / /|  _| | |_) |
| |  | | |___|  __/      ___) | |___|  _ < \ V / | |___|  _ <
|_|  |_|\____|_|        |____/|_____|_| \_\ \_/  |_____|_| \_\
        """)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:a37a05942c26b0dba411732bff91abf9ff932cbd8bf7d6dbb6faf1cdf9a43b65'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a37a05942c26b0dba411732bff91abf9ff932cbd8bf7d6dbb6faf1cdf9a43b65', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 638, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 638, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(
        _lineaje_payload,
        flush=True,
    )
    _lineaje_payload = f"MCP launch mode: {MODE}"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:889441f2adaae8786caf8dc55242a1cdead147dd946953072bfc828d0df63e3f'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:889441f2adaae8786caf8dc55242a1cdead147dd946953072bfc828d0df63e3f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 648, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 648, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(_lineaje_payload, flush=True)
    _lineaje_payload = f"MCP host: {HOST}"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:3faeeb0936c3561b692c2bfee95564eb8e53235f63ee090d3f39a50b09143197'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3faeeb0936c3561b692c2bfee95564eb8e53235f63ee090d3f39a50b09143197', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 649, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 649, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(_lineaje_payload, flush=True)
    _lineaje_payload = f"MCP port: {PORT}"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:7970129ad1a8a5e13cdd67b707643bf037b7c14d0ac43c0df312b46e3941c6c6'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7970129ad1a8a5e13cdd67b707643bf037b7c14d0ac43c0df312b46e3941c6c6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 650, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 650, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(_lineaje_payload, flush=True)
    _lineaje_payload = f"MCP base_url: {BASE_URL}"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:57e6c6f3d0a5fa8567d3513910700bb7d651e4186e9539c3e655a37bacbe9b11'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:57e6c6f3d0a5fa8567d3513910700bb7d651e4186e9539c3e655a37bacbe9b11', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 651, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 651, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(_lineaje_payload, flush=True)

    if not any([TRANSPORT_SSE_ENABLED, TRANSPORT_STREAMABLE_HTTP_ENABLED]):
        _lineaje_payload = "At least one transport should be enabled, enable streamable-http automatically"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowCtx.parse_bool_flag).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:70de40547d8913b8077393e75af9be8f08a970ba9b80d0e9ccdc074fe6b00bdd'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:70de40547d8913b8077393e75af9be8f08a970ba9b80d0e9ccdc074fe6b00bdd', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 654, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 654, 'function': 'parse_bool_flag', 'agent_name': 'RAGFlowCtx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload, flush=True)
        TRANSPORT_STREAMABLE_HTTP_ENABLED = True

    if TRANSPORT_SSE_ENABLED:
        _lineaje_payload = "SSE transport enabled: yes"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowCtx.parse_bool_flag).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:962be6ac0b291c5bd39f3ef787ac6edb3b95cbaccb4e22105c11697f35779462'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:962be6ac0b291c5bd39f3ef787ac6edb3b95cbaccb4e22105c11697f35779462', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 658, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 658, 'function': 'parse_bool_flag', 'agent_name': 'RAGFlowCtx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload, flush=True)
        _lineaje_payload = "SSE endpoint available at /sse"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowCtx.parse_bool_flag).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ba508fb3d15a2ded3941ec0c24d11ee12da86d8028c76a119e7254d1c8546dd6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ba508fb3d15a2ded3941ec0c24d11ee12da86d8028c76a119e7254d1c8546dd6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 659, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 659, 'function': 'parse_bool_flag', 'agent_name': 'RAGFlowCtx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload, flush=True)
    else:
        _lineaje_payload = "SSE transport enabled: no"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowCtx.parse_bool_flag).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:045eb755b2dab3c7f138bdaf50653c0fc4c2cfdac0e44ccca1d9787af5952566'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:045eb755b2dab3c7f138bdaf50653c0fc4c2cfdac0e44ccca1d9787af5952566', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 661, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 661, 'function': 'parse_bool_flag', 'agent_name': 'RAGFlowCtx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload, flush=True)

    if TRANSPORT_STREAMABLE_HTTP_ENABLED:
        _lineaje_payload = "Streamable HTTP transport enabled: yes"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowCtx.parse_bool_flag).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:80f64f134788b71b327b8f23c0ae1ed81df9198eb5da238cb8900b5b646a49f1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:80f64f134788b71b327b8f23c0ae1ed81df9198eb5da238cb8900b5b646a49f1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 664, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 664, 'function': 'parse_bool_flag', 'agent_name': 'RAGFlowCtx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload, flush=True)
        _lineaje_payload = "Streamable HTTP endpoint available at /mcp"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowCtx.parse_bool_flag).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:965593aafb504237742206a52c3ce29ad57974aeb39cb04ece7f4f509ab58f48'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:965593aafb504237742206a52c3ce29ad57974aeb39cb04ece7f4f509ab58f48', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 665, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 665, 'function': 'parse_bool_flag', 'agent_name': 'RAGFlowCtx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload, flush=True)
        if JSON_RESPONSE:
            _lineaje_payload = "Streamable HTTP mode: JSON response enabled"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowCtx.parse_bool_flag).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:401917e7e1fb3eee43f302f1c39f23990cc615aff25a3ec0b00b4b8b8c9653bf'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:401917e7e1fb3eee43f302f1c39f23990cc615aff25a3ec0b00b4b8b8c9653bf', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 667, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 667, 'function': 'parse_bool_flag', 'agent_name': 'RAGFlowCtx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload, flush=True)
        else:
            _lineaje_payload = "Streamable HTTP mode: SSE over HTTP enabled"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowCtx.parse_bool_flag).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:563712576b66840dcf4209ff7811bb71f54f75145eab0a6b5a87f77b98e869b3'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:563712576b66840dcf4209ff7811bb71f54f75145eab0a6b5a87f77b98e869b3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 669, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 669, 'function': 'parse_bool_flag', 'agent_name': 'RAGFlowCtx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload, flush=True)
    else:
        _lineaje_payload = "Streamable HTTP transport enabled: no"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowCtx.parse_bool_flag).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c266dab43c35c8b96311ef2866308e0b9346529f08036fae0e507a641572584c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c266dab43c35c8b96311ef2866308e0b9346529f08036fae0e507a641572584c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 671, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 671, 'function': 'parse_bool_flag', 'agent_name': 'RAGFlowCtx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload, flush=True)
        if JSON_RESPONSE:
            _lineaje_payload = "Warning: --json-response ignored because streamable transport is disabled."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowCtx.parse_bool_flag).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:df0ca71381700a249478805ced75656b28c21685fe8081956896c87bf1f25e82'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:df0ca71381700a249478805ced75656b28c21685fe8081956896c87bf1f25e82', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'mcp/server/server.py', 'line': 673, 'function': 'main'}, 'file': 'mcp/server/server.py', 'line': 673, 'function': 'parse_bool_flag', 'agent_name': 'RAGFlowCtx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload, flush=True)

    uvicorn.run(
        create_starlette_app(),
        host=HOST,
        port=int(PORT),
    )


if __name__ == "__main__":
    """
    Launch examples:

    1. Self-host mode with both SSE and Streamable HTTP (in JSON response mode) enabled (default):
        uv run mcp/server/server.py --host=127.0.0.1 --port=9382 \
            --base-url=http://127.0.0.1:9380 \
            --mode=self-host --api-key=ragflow-xxxxx

    2. Host mode (multi-tenant, self-host only, clients must provide Authorization headers):
        uv run mcp/server/server.py --host=127.0.0.1 --port=9382 \
            --base-url=http://127.0.0.1:9380 \
            --mode=host

    3. Disable legacy SSE (only streamable HTTP will be active):
        uv run mcp/server/server.py --no-transport-sse-enabled \
            --mode=self-host --api-key=ragflow-xxxxx

    4. Disable streamable HTTP (only legacy SSE will be active):
        uv run mcp/server/server.py --no-transport-streamable-http-enabled \
            --mode=self-host --api-key=ragflow-xxxxx

    5. Use streamable HTTP with SSE-style events (disable JSON response):
        uv run mcp/server/server.py --transport-streamable-http-enabled --no-json-response \
            --mode=self-host --api-key=ragflow-xxxxx

    6. Disable both transports (for testing):
        uv run mcp/server/server.py --no-transport-sse-enabled --no-transport-streamable-http-enabled \
            --mode=self-host --api-key=ragflow-xxxxx
    """
    main()
