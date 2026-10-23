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
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
import os
import threading
from abc import ABC
from urllib.parse import urljoin

import dashscope
import google.generativeai as genai
import numpy as np
import requests
from ollama import Client
from openai import OpenAI
from zhipuai import ZhipuAI

from common.log_utils import log_exception
from common.token_utils import num_tokens_from_string, truncate, total_token_count_from_response
from common import settings
import logging
import base64


class Base(ABC):
    def __init__(self, key, model_name, **kwargs):
        """
        Constructor for abstract base class.
        Parameters are accepted for interface consistency but are not stored.
        Subclasses should implement their own initialization as needed.
        """
        pass

    def encode(self, texts: list):
        raise NotImplementedError("Please implement encode method!")

    def encode_queries(self, text: str):
        raise NotImplementedError("Please implement encode method!")


class BuiltinEmbed(Base):
    _FACTORY_NAME = "Builtin"
    MAX_TOKENS = {"Qwen/Qwen3-Embedding-0.6B": 30000, "BAAI/bge-m3": 8000, "BAAI/bge-small-en-v1.5": 500}
    _model = None
    _model_name = ""
    _max_tokens = 500
    _model_lock = threading.Lock()

    def __init__(self, key, model_name, **kwargs):
        _lineaje_payload = f"Initialize BuiltinEmbed according to settings.EMBEDDING_CFG: {settings.EMBEDDING_CFG}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in BuiltinEmbed.__init__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c174a50d58a63d1f4a5743dd2efaa645a58fec46461865b0322fdcff4a22ac4c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c174a50d58a63d1f4a5743dd2efaa645a58fec46461865b0322fdcff4a22ac4c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'line': 62, 'function': 'BuiltinEmbed.__init__'}, 'file': 'rag/llm/embedding_model.py', 'line': 62, 'function': '__init__', 'agent_name': 'BuiltinEmbed', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        embedding_cfg = settings.EMBEDDING_CFG
        if not BuiltinEmbed._model and "tei-" in os.getenv("COMPOSE_PROFILES", ""):
            with BuiltinEmbed._model_lock:
                BuiltinEmbed._model_name = settings.EMBEDDING_MDL
                BuiltinEmbed._max_tokens = BuiltinEmbed.MAX_TOKENS.get(settings.EMBEDDING_MDL, 500)
                BuiltinEmbed._model = HuggingFaceEmbed(embedding_cfg["api_key"], settings.EMBEDDING_MDL, base_url=embedding_cfg["base_url"])
        self._model = BuiltinEmbed._model
        self._model_name = BuiltinEmbed._model_name
        self._max_tokens = BuiltinEmbed._max_tokens

    def encode(self, texts: list):
        batch_size = 16
        # TEI is able to auto truncate inputs according to https://github.com/huggingface/text-embeddings-inference.
        token_count = 0
        ress = None
        for i in range(0, len(texts), batch_size):
            embeddings, token_count_delta = self._model.encode(texts[i : i + batch_size])
            token_count += token_count_delta
            if ress is None:
                ress = embeddings
            else:
                ress = np.concatenate((ress, embeddings), axis=0)
        return ress, token_count

    def encode_queries(self, text: str):
        # LINEAJE: runtime guardrail checks `text` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in BuiltinEmbed.encode_queries).
        #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `text` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:beba11544b743fb9df3bc75be559572a11922086c45384eeb93ec2af41adfaec'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:beba11544b743fb9df3bc75be559572a11922086c45384eeb93ec2af41adfaec', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'line': 88, 'function': 'BuiltinEmbed.encode_queries'}, 'file': 'rag/llm/embedding_model.py', 'line': 88, 'function': 'encode_queries', 'agent_name': 'BuiltinEmbed', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            text = _gr_client.enforce(_gr_site, text, content_type='application/json', variable_name='text', source_file=__file__, before_line=88)
        except _gr_client.GuardrailUnavailableError:
            pass
        return self._model.encode_queries(text)


class OpenAIEmbed(Base):
    _FACTORY_NAME = "OpenAI"

    def __init__(self, key, model_name="text-embedding-ada-002", base_url="https://api.openai.com/v1"):
        if not base_url:
            base_url = "https://api.openai.com/v1"
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name

    def encode(self, texts: list):
        # OpenAI requires batch size <=16
        batch_size = 16
        texts = [truncate(t, 8191) for t in texts]
        ress = []
        total_tokens = 0
        for i in range(0, len(texts), batch_size):
            _lineaje_input = texts[i : i + batch_size]
            # LINEAJE: runtime guardrail checks `_lineaje_input` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in OpenAIEmbed.encode).
            #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_input` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3ee1c3ced33eb6104f9fd1c0ef5ee55dbda53657162b8d15794762dfcf7edefc'
            _lineaje__lineaje_input_evidence = {'_lineaje_input': _lineaje_input, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3ee1c3ced33eb6104f9fd1c0ef5ee55dbda53657162b8d15794762dfcf7edefc', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='BLOCK', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Qwen', 'purl': 'pkg:aimodel/Qwen@3-Embedding-0.6B', 'version': '3-Embedding-0.6B'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'function': 'OpenAIEmbed.encode', 'line': 107}, 'destination': {'entity_type': 'llm', 'name': 'Qwen3-Embedding-0.6B', 'provider': 'qwen', 'version': ''}, 'file': 'rag/llm/embedding_model.py', 'line': 107, 'function': 'encode', 'agent_name': 'OpenAIEmbed', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:9c0f8ea815a61377'})
            try:
                _lineaje__lineaje_input_evidence = _gr_client.enforce(_gr_site, _lineaje__lineaje_input_evidence, content_type='application/json')
                _lineaje_input = _lineaje__lineaje_input_evidence.get('_lineaje_input', _lineaje_input) if isinstance(_lineaje__lineaje_input_evidence, dict) else _lineaje_input
            except _gr_client.GuardrailUnavailableError:
                pass
            res = self.client.embeddings.create(input=_lineaje_input, model=self.model_name, encoding_format="float", extra_body={"drop_params": True})
            try:
                ress.extend([d.embedding for d in res.data])
                total_tokens += total_token_count_from_response(res)
            except Exception as _e:
                log_exception(_e, res)
                raise Exception(f"Error: {res}")
        return np.array(ress), total_tokens

    def encode_queries(self, text):
        _lineaje_input = [truncate(text, 8191)]
        # LINEAJE: runtime guardrail checks `_lineaje_input` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in OpenAIEmbed.encode_queries).
        #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_input` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:032141e1826961f6bf1aa2dd7278a1d84bbc1b6cdd88d19bf73a2b6d3da961e6'
        _lineaje__lineaje_input_evidence = {'_lineaje_input': _lineaje_input, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:032141e1826961f6bf1aa2dd7278a1d84bbc1b6cdd88d19bf73a2b6d3da961e6', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='BLOCK', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Qwen', 'purl': 'pkg:aimodel/Qwen@3-Embedding-0.6B', 'version': '3-Embedding-0.6B'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'function': 'OpenAIEmbed.encode_queries', 'line': 117}, 'destination': {'entity_type': 'llm', 'name': 'Qwen3-Embedding-0.6B', 'provider': 'qwen', 'version': ''}, 'file': 'rag/llm/embedding_model.py', 'line': 117, 'function': 'encode_queries', 'agent_name': 'OpenAIEmbed', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:1f3ba6fa5c08e4d0'})
        try:
            _lineaje__lineaje_input_evidence = _gr_client.enforce(_gr_site, _lineaje__lineaje_input_evidence, content_type='application/json')
            _lineaje_input = _lineaje__lineaje_input_evidence.get('_lineaje_input', _lineaje_input) if isinstance(_lineaje__lineaje_input_evidence, dict) else _lineaje_input
        except _gr_client.GuardrailUnavailableError:
            pass
        res = self.client.embeddings.create(input=_lineaje_input, model=self.model_name, encoding_format="float",extra_body={"drop_params": True})
        try:
            return np.array(res.data[0].embedding), total_token_count_from_response(res)
        except Exception as _e:
            log_exception(_e, res)
            raise Exception(f"Error: {res}")


class LocalAIEmbed(Base):
    _FACTORY_NAME = "LocalAI"

    def __init__(self, key, model_name, base_url):
        if not base_url:
            raise ValueError("Local embedding model url cannot be None")
        base_url = urljoin(base_url, "v1")
        self.client = OpenAI(api_key="empty", base_url=base_url)
        self.model_name = model_name.split("___")[0]

    def encode(self, texts: list):
        batch_size = 16
        ress = []
        for i in range(0, len(texts), batch_size):
            _lineaje_input = texts[i : i + batch_size]
            # LINEAJE: runtime guardrail checks `_lineaje_input` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in LocalAIEmbed.encode).
            #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_input` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:411fa09a010bb663ec9a37d686f804af0869fe546224c62a40200ea757e95cf6'
            _lineaje__lineaje_input_evidence = {'_lineaje_input': _lineaje_input, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:411fa09a010bb663ec9a37d686f804af0869fe546224c62a40200ea757e95cf6', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='BLOCK', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Qwen', 'purl': 'pkg:aimodel/Qwen@3-Embedding-0.6B', 'version': '3-Embedding-0.6B'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'function': 'LocalAIEmbed.encode', 'line': 139}, 'destination': {'entity_type': 'llm', 'name': 'Qwen3-Embedding-0.6B', 'provider': 'qwen', 'version': ''}, 'file': 'rag/llm/embedding_model.py', 'line': 139, 'function': 'encode', 'agent_name': 'LocalAIEmbed', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:f4245c59acb18982'})
            try:
                _lineaje__lineaje_input_evidence = _gr_client.enforce(_gr_site, _lineaje__lineaje_input_evidence, content_type='application/json')
                _lineaje_input = _lineaje__lineaje_input_evidence.get('_lineaje_input', _lineaje_input) if isinstance(_lineaje__lineaje_input_evidence, dict) else _lineaje_input
            except _gr_client.GuardrailUnavailableError:
                pass
            res = self.client.embeddings.create(input=_lineaje_input, model=self.model_name)
            try:
                ress.extend([d.embedding for d in res.data])
            except Exception as _e:
                log_exception(_e, res)
                raise Exception(f"Error: {res}")
        # local embedding for LmStudio donot count tokens
        return np.array(ress), 1024

    def encode_queries(self, text):
        embds, cnt = self.encode([text])
        return np.array(embds[0]), cnt


class AzureEmbed(OpenAIEmbed):
    _FACTORY_NAME = "Azure-OpenAI"

    def __init__(self, key, model_name, **kwargs):
        from openai.lib.azure import AzureOpenAI

        api_key = json.loads(key).get("api_key", "")
        api_version = json.loads(key).get("api_version", "2024-02-01")
        self.client = AzureOpenAI(api_key=api_key, azure_endpoint=kwargs["base_url"], api_version=api_version)
        self.model_name = model_name


class BaiChuanEmbed(OpenAIEmbed):
    _FACTORY_NAME = "BaiChuan"

    def __init__(self, key, model_name="Baichuan-Text-Embedding", base_url="https://api.baichuan-ai.com/v1"):
        if not base_url:
            base_url = "https://api.baichuan-ai.com/v1"
        super().__init__(key, model_name, base_url)


class QWenEmbed(Base):
    _FACTORY_NAME = "Tongyi-Qianwen"

    def __init__(self, key, model_name="text_embedding_v2", **kwargs):
        self.key = key
        self.model_name = model_name

    def encode(self, texts: list):
        import time

        import dashscope

        batch_size = 4
        res = []
        token_count = 0
        texts = [truncate(t, 2048) for t in texts]
        for i in range(0, len(texts), batch_size):
            retry_max = 5
            resp = dashscope.TextEmbedding.call(model=self.model_name, input=texts[i : i + batch_size], api_key=self.key, text_type="document")
            while (resp["output"] is None or resp["output"].get("embeddings") is None) and retry_max > 0:
                time.sleep(10)
                resp = dashscope.TextEmbedding.call(model=self.model_name, input=texts[i : i + batch_size], api_key=self.key, text_type="document")
                retry_max -= 1
            if retry_max == 0 and (resp["output"] is None or resp["output"].get("embeddings") is None):
                if resp.get("message"):
                    log_exception(ValueError(f"Retry_max reached, calling embedding model failed: {resp['message']}"))
                else:
                    log_exception(ValueError("Retry_max reached, calling embedding model failed"))
                raise
            try:
                embds = [[] for _ in range(len(resp["output"]["embeddings"]))]
                for e in resp["output"]["embeddings"]:
                    embds[e["text_index"]] = e["embedding"]
                res.extend(embds)
                token_count += total_token_count_from_response(resp)
            except Exception as _e:
                log_exception(_e, resp)
                raise
        return np.array(res), token_count

    def encode_queries(self, text):
        resp = dashscope.TextEmbedding.call(model=self.model_name, input=text[:2048], api_key=self.key, text_type="query")
        try:
            return np.array(resp["output"]["embeddings"][0]["embedding"]), total_token_count_from_response(resp)
        except Exception as _e:
            log_exception(_e, resp)
            raise Exception(f"Error: {resp}")


class ZhipuEmbed(Base):
    _FACTORY_NAME = "ZHIPU-AI"

    def __init__(self, key, model_name="embedding-2", **kwargs):
        self.client = ZhipuAI(api_key=key)
        self.model_name = model_name

    def encode(self, texts: list):
        arr = []
        tks_num = 0
        MAX_LEN = -1
        if self.model_name.lower() == "embedding-2":
            MAX_LEN = 512
        if self.model_name.lower() == "embedding-3":
            MAX_LEN = 3072
        if MAX_LEN > 0:
            texts = [truncate(t, MAX_LEN) for t in texts]

        for txt in texts:
            # LINEAJE: runtime guardrail checks `txt` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in ZhipuEmbed.encode).
            #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `txt` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b5f31c997c910ec4e721ebff257dd17b43fbe7a4fdc907d3473b1718cc1261c0'
            _lineaje_txt_evidence = {'txt': txt, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b5f31c997c910ec4e721ebff257dd17b43fbe7a4fdc907d3473b1718cc1261c0', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='BLOCK', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'embedding-2', 'purl': 'pkg:aimodel/embedding-2@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'function': 'ZhipuEmbed.encode', 'line': 242}, 'destination': {'entity_type': 'llm', 'name': 'embedding-2', 'provider': '', 'version': ''}, 'file': 'rag/llm/embedding_model.py', 'line': 242, 'function': 'encode', 'agent_name': 'ZhipuEmbed', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:74baf199a9e822f1'})
            try:
                _lineaje_txt_evidence = _gr_client.enforce(_gr_site, _lineaje_txt_evidence, content_type='application/json')
                txt = _lineaje_txt_evidence.get('txt', txt) if isinstance(_lineaje_txt_evidence, dict) else txt
            except _gr_client.GuardrailUnavailableError:
                pass
            res = self.client.embeddings.create(input=txt, model=self.model_name)
            try:
                arr.append(res.data[0].embedding)
                tks_num += total_token_count_from_response(res)
            except Exception as _e:
                log_exception(_e, res)
                raise Exception(f"Error: {res}")
        return np.array(arr), tks_num

    def encode_queries(self, text):
        # LINEAJE: runtime guardrail checks `text` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in ZhipuEmbed.encode_queries).
        #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `text` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:7457aae9101a56ed5ba3a977262883a71063f2e92417e3a1f5823385cd05e08b'
        _lineaje_text_evidence = {'text': text, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7457aae9101a56ed5ba3a977262883a71063f2e92417e3a1f5823385cd05e08b', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='BLOCK', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'embedding-2', 'purl': 'pkg:aimodel/embedding-2@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'function': 'ZhipuEmbed.encode_queries', 'line': 252}, 'destination': {'entity_type': 'llm', 'name': 'embedding-2', 'provider': '', 'version': ''}, 'file': 'rag/llm/embedding_model.py', 'line': 252, 'function': 'encode_queries', 'agent_name': 'ZhipuEmbed', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:154dc308186ba6a8'})
        try:
            _lineaje_text_evidence = _gr_client.enforce(_gr_site, _lineaje_text_evidence, content_type='application/json')
            text = _lineaje_text_evidence.get('text', text) if isinstance(_lineaje_text_evidence, dict) else text
        except _gr_client.GuardrailUnavailableError:
            pass
        res = self.client.embeddings.create(input=text, model=self.model_name)
        try:
            return np.array(res.data[0].embedding), total_token_count_from_response(res)
        except Exception as _e:
            log_exception(_e, res)
            raise Exception(f"Error: {res}")


class OllamaEmbed(Base):
    _FACTORY_NAME = "Ollama"

    _special_tokens = ["<|endoftext|>"]

    def __init__(self, key, model_name, **kwargs):
        self.client = Client(host=kwargs["base_url"]) if not key or key == "x" else Client(host=kwargs["base_url"], headers={"Authorization": f"Bearer {key}"})
        self.model_name = model_name
        self.keep_alive = kwargs.get("ollama_keep_alive", int(os.environ.get("OLLAMA_KEEP_ALIVE", -1)))

    def encode(self, texts: list):
        arr = []
        tks_num = 0
        for txt in texts:
            # remove special tokens if they exist base on regex in one request
            for token in OllamaEmbed._special_tokens:
                txt = txt.replace(token, "")
            res = self.client.embeddings(prompt=txt, model=self.model_name, options={"use_mmap": True}, keep_alive=self.keep_alive)
            try:
                arr.append(res["embedding"])
            except Exception as _e:
                log_exception(_e, res)
                raise Exception(f"Error: {res}")
            tks_num += 128
        return np.array(arr), tks_num

    def encode_queries(self, text):
        # remove special tokens if they exist
        for token in OllamaEmbed._special_tokens:
            text = text.replace(token, "")
        res = self.client.embeddings(prompt=text, model=self.model_name, options={"use_mmap": True}, keep_alive=self.keep_alive)
        try:
            return np.array(res["embedding"]), 128
        except Exception as _e:
            log_exception(_e, res)
            raise Exception(f"Error: {res}")


class XinferenceEmbed(Base):
    _FACTORY_NAME = "Xinference"

    def __init__(self, key, model_name="", base_url=""):
        base_url = urljoin(base_url, "v1")
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name

    def encode(self, texts: list):
        batch_size = 16
        ress = []
        total_tokens = 0
        for i in range(0, len(texts), batch_size):
            res = None
            try:
                _lineaje_input = texts[i : i + batch_size]
                # LINEAJE: runtime guardrail checks `_lineaje_input` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in XinferenceEmbed.encode).
                #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_input` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:aa42cf977363c63695dc8e9e80261ffe10ea8312ebb7b207cc2a60d7b40592e7'
                _lineaje__lineaje_input_evidence = {'_lineaje_input': _lineaje_input, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aa42cf977363c63695dc8e9e80261ffe10ea8312ebb7b207cc2a60d7b40592e7', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='BLOCK', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'embedding-2', 'purl': 'pkg:aimodel/embedding-2@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'function': 'XinferenceEmbed.encode', 'line': 313}, 'destination': {'entity_type': 'llm', 'name': 'embedding-2', 'provider': '', 'version': ''}, 'file': 'rag/llm/embedding_model.py', 'line': 313, 'function': 'encode', 'agent_name': 'XinferenceEmbed', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:ea3366d9e724c006'})
                try:
                    _lineaje__lineaje_input_evidence = _gr_client.enforce(_gr_site, _lineaje__lineaje_input_evidence, content_type='application/json')
                    _lineaje_input = _lineaje__lineaje_input_evidence.get('_lineaje_input', _lineaje_input) if isinstance(_lineaje__lineaje_input_evidence, dict) else _lineaje_input
                except _gr_client.GuardrailUnavailableError:
                    pass
                res = self.client.embeddings.create(input=_lineaje_input, model=self.model_name)
                ress.extend([d.embedding for d in res.data])
                total_tokens += total_token_count_from_response(res)
            except Exception as _e:
                log_exception(_e, res)
                raise Exception(f"Error: {res}")
        return np.array(ress), total_tokens

    def encode_queries(self, text):
        res = None
        try:
            _lineaje_input = [text]
            # LINEAJE: runtime guardrail checks `_lineaje_input` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in XinferenceEmbed.encode_queries).
            #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_input` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b169fddbd79cf59bfcddba0ec66803bccaae6772453731a56268a34d16b62087'
            _lineaje__lineaje_input_evidence = {'_lineaje_input': _lineaje_input, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b169fddbd79cf59bfcddba0ec66803bccaae6772453731a56268a34d16b62087', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='BLOCK', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'embedding-2', 'purl': 'pkg:aimodel/embedding-2@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'function': 'XinferenceEmbed.encode_queries', 'line': 324}, 'destination': {'entity_type': 'llm', 'name': 'embedding-2', 'provider': '', 'version': ''}, 'file': 'rag/llm/embedding_model.py', 'line': 324, 'function': 'encode_queries', 'agent_name': 'XinferenceEmbed', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:b39fa63108286392'})
            try:
                _lineaje__lineaje_input_evidence = _gr_client.enforce(_gr_site, _lineaje__lineaje_input_evidence, content_type='application/json')
                _lineaje_input = _lineaje__lineaje_input_evidence.get('_lineaje_input', _lineaje_input) if isinstance(_lineaje__lineaje_input_evidence, dict) else _lineaje_input
            except _gr_client.GuardrailUnavailableError:
                pass
            res = self.client.embeddings.create(input=_lineaje_input, model=self.model_name)
            return np.array(res.data[0].embedding), total_token_count_from_response(res)
        except Exception as _e:
            log_exception(_e, res)
            raise Exception(f"Error: {res}")


class YoudaoEmbed(Base):
    _FACTORY_NAME = "Youdao"
    _client = None

    def __init__(self, key=None, model_name="maidalun1020/bce-embedding-base_v1", **kwargs):
        pass

    def encode(self, texts: list):
        batch_size = 10
        res = []
        token_count = 0
        for t in texts:
            token_count += num_tokens_from_string(t)
        for i in range(0, len(texts), batch_size):
            embds = YoudaoEmbed._client.encode(texts[i : i + batch_size])
            res.extend(embds)
        return np.array(res), token_count

    def encode_queries(self, text):
        embds = YoudaoEmbed._client.encode([text])
        return np.array(embds[0]), num_tokens_from_string(text)


class JinaMultiVecEmbed(Base):
    _FACTORY_NAME = "Jina"

    def __init__(self, key, model_name="jina-embeddings-v4", base_url="https://api.jina.ai/v1/embeddings"):
        self.base_url = "https://api.jina.ai/v1/embeddings"
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
        self.model_name = model_name

    def encode(self, texts: list[str|bytes], task="retrieval.passage"):
        batch_size = 16
        ress = []
        token_count = 0
        input = []
        for text in texts:
            if isinstance(text, str):
                input.append({"text": text})
            elif isinstance(text, bytes):
                img_b64s = None
                try:
                    base64.b64decode(text, validate=True)
                    img_b64s = text.decode('utf8')
                except Exception:
                    img_b64s = base64.b64encode(text).decode('utf8')
                input.append({"image": img_b64s})  # base64 encoded image
        for i in range(0, len(texts), batch_size):
            data = {"model": self.model_name, "input": input[i : i + batch_size]}
            if "v4" in self.model_name:
                data["return_multivector"] = True
            
            if "v3" in self.model_name or "v4" in self.model_name:
                data['task'] = task
                data['truncate'] = True

            response = requests.post(self.base_url, headers=self.headers, json=data)
            # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in JinaMultiVecEmbed.encode).
            #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3cef4eda2ba4fe2ee73618cef16627eb3b6f0cd9dc4024044bc60e947d669fe7'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3cef4eda2ba4fe2ee73618cef16627eb3b6f0cd9dc4024044bc60e947d669fe7', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'line': 387, 'function': 'JinaMultiVecEmbed.encode'}, 'file': 'rag/llm/embedding_model.py', 'line': 387, 'function': 'encode', 'agent_name': 'JinaMultiVecEmbed', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=387)
            except _gr_client.GuardrailUnavailableError:
                pass
            try:
                res = response.json()
                for d in res['data']:
                    if data.get("return_multivector", False): # v4
                        token_embs = np.asarray(d['embeddings'], dtype=np.float32)
                        chunk_emb = token_embs.mean(axis=0)
                    
                    else:
                        # v2/v3
                        chunk_emb = np.asarray(d['embedding'], dtype=np.float32)

                    ress.append(chunk_emb)

                token_count += total_token_count_from_response(res)
            except Exception as _e:
                log_exception(_e, response)
                raise Exception(f"Error: {response}")
        return np.array(ress), token_count

    def encode_queries(self, text):
        embds, cnt = self.encode([text], task="retrieval.query")
        return np.array(embds[0]), cnt


class MistralEmbed(Base):
    _FACTORY_NAME = "Mistral"

    def __init__(self, key, model_name="mistral-embed", base_url=None):
        from mistralai.client import MistralClient

        self.client = MistralClient(api_key=key)
        self.model_name = model_name

    def encode(self, texts: list):
        import time
        import random

        texts = [truncate(t, 8196) for t in texts]
        batch_size = 16
        ress = []
        token_count = 0
        for i in range(0, len(texts), batch_size):
            retry_max = 5
            while retry_max > 0:
                try:
                    res = self.client.embeddings(input=texts[i : i + batch_size], model=self.model_name)
                    ress.extend([d.embedding for d in res.data])
                    token_count += total_token_count_from_response(res)
                    break
                except Exception as _e:
                    if retry_max == 1:
                        log_exception(_e)
                    delay = random.uniform(20, 60)
                    time.sleep(delay)
                    retry_max -= 1
        return np.array(ress), token_count

    def encode_queries(self, text):
        import time
        import random
        retry_max = 5
        while retry_max > 0:
            try:
                res = self.client.embeddings(input=[truncate(text, 8196)], model=self.model_name)
                return np.array(res.data[0].embedding), total_token_count_from_response(res)
            except Exception as _e:
                if retry_max == 1:
                    log_exception(_e)
                delay = random.randint(20, 60)
                time.sleep(delay)
                retry_max -= 1


class BedrockEmbed(Base):
    _FACTORY_NAME = "Bedrock"

    def __init__(self, key, model_name, **kwargs):
        import boto3
        # `key` protocol (backend stores as JSON string in `api_key`):
        # - Must decode into a dict.
        # - Required: `auth_mode`, `bedrock_region`.
        # - Supported auth modes:
        #   - "access_key_secret": requires `bedrock_ak` + `bedrock_sk`.
        #   - "iam_role": requires `aws_role_arn` and assumes role via STS.
        #   - else: treated as "assume_role" (default AWS credential chain).
        key = json.loads(key)
        mode = key.get("auth_mode")
        if not mode:
            _lineaje_payload = "Bedrock auth_mode is not provided in the key"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in BedrockEmbed.__init__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9066c272479b8dac50c69d0120c7b2cb339c88bb512a5869d0e55da82dd69e84'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9066c272479b8dac50c69d0120c7b2cb339c88bb512a5869d0e55da82dd69e84', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'line': 476, 'function': 'BedrockEmbed.__init__'}, 'file': 'rag/llm/embedding_model.py', 'line': 476, 'function': '__init__', 'agent_name': 'BedrockEmbed', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            raise ValueError("Bedrock auth_mode must be provided in the key")

        self.bedrock_region = key.get("bedrock_region")

        self.model_name = model_name
        self.is_amazon = self.model_name.split(".")[0] == "amazon"
        self.is_cohere = self.model_name.split(".")[0] == "cohere"
        
        if mode == "access_key_secret":
            self.bedrock_ak = key.get("bedrock_ak")
            self.bedrock_sk = key.get("bedrock_sk")
            self.client = boto3.client(service_name="bedrock-runtime", region_name=self.bedrock_region, aws_access_key_id=self.bedrock_ak, aws_secret_access_key=self.bedrock_sk)
        elif mode == "iam_role":
            self.aws_role_arn = key.get("aws_role_arn")
            sts_client = boto3.client("sts", region_name=self.bedrock_region)
            resp = sts_client.assume_role(RoleArn=self.aws_role_arn, RoleSessionName="BedrockSession")
            creds = resp["Credentials"]

            self.client = boto3.client(
                service_name="bedrock-runtime",
                aws_access_key_id=creds["AccessKeyId"],
                aws_secret_access_key=creds["SecretAccessKey"],
                aws_session_token=creds["SessionToken"],
            )
        else: # assume_role
            self.client = boto3.client("bedrock-runtime", region_name=self.bedrock_region)


    def encode(self, texts: list):
        texts = [truncate(t, 8196) for t in texts]
        embeddings = []
        token_count = 0
        for text in texts:
            if self.is_amazon:
                body = {"inputText": text}
            elif self.is_cohere:
                body = {"texts": [text], "input_type": "search_document"}

            _lineaje_body = json.dumps(body)
            # LINEAJE: runtime guardrail checks `_lineaje_body` as it flows from the agent to the LLM, before it is sent to the model (in BedrockEmbed.encode).
            #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_body` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1f1f2ad4063007d9b7bb345bc576ad41da2b01159617aab0c02b80a6bba50d25'
            _lineaje__lineaje_body_evidence = {'_lineaje_body': _lineaje_body, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _lineaje_interaction_id = _gr_client.new_interaction_id()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1f1f2ad4063007d9b7bb345bc576ad41da2b01159617aab0c02b80a6bba50d25', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'mistral-embed', 'provider': 'mistral', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Mistral', 'purl': 'pkg:aimodel/Mistral@embed', 'version': 'embed'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'function': 'BedrockEmbed.encode', 'line': 515}, 'file': 'rag/llm/embedding_model.py', 'line': 515, 'function': 'encode', 'agent_name': 'BedrockEmbed', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:b189c35c0f122b58'}, interaction_id=_lineaje_interaction_id)
            try:
                _lineaje__lineaje_body_evidence = _gr_client.enforce(_gr_site, _lineaje__lineaje_body_evidence, content_type='application/json')
                _lineaje_body = _lineaje__lineaje_body_evidence.get('_lineaje_body', _lineaje_body) if isinstance(_lineaje__lineaje_body_evidence, dict) else _lineaje_body
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            response = self.client.invoke_model(modelId=self.model_name, body=_lineaje_body)
            # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in BedrockEmbed.encode).
            #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f2232137562131daebdf6f6ba59f166212312955321fe2d14ffad3e9c7fb4486'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f2232137562131daebdf6f6ba59f166212312955321fe2d14ffad3e9c7fb4486', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'mistral-embed', 'provider': 'mistral', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Mistral', 'purl': 'pkg:aimodel/Mistral@embed', 'version': 'embed'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'function': 'BedrockEmbed.encode', 'line': 515}, 'file': 'rag/llm/embedding_model.py', 'line': 515, 'function': 'encode', 'agent_name': 'BedrockEmbed', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:b189c35c0f122b58'}, interaction_id=locals().get('_lineaje_interaction_id'))
            try:
                if not hasattr(_gr_client, 'enforce_reply'):
                    __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                    raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                response = _gr_client.enforce_reply(_gr_site, response, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            try:
                model_response = json.loads(response["body"].read())
                embeddings.extend([model_response["embedding"]])
                token_count += num_tokens_from_string(text)
            except Exception as _e:
                log_exception(_e, response)

        return np.array(embeddings), token_count

    def encode_queries(self, text):
        embeddings = []
        token_count = num_tokens_from_string(text)
        if self.is_amazon:
            body = {"inputText": truncate(text, 8196)}
        elif self.is_cohere:
            body = {"texts": [truncate(text, 8196)], "input_type": "search_query"}

        _lineaje_body = json.dumps(body)
        # LINEAJE: runtime guardrail checks `_lineaje_body` as it flows from the agent to the LLM, before it is sent to the model (in BedrockEmbed.encode_queries).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_body` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3e10a25ed153fef8abeb43e3911d18cca738c7f987e45ac22b0b7f3581d1cd4d'
        _lineaje__lineaje_body_evidence = {'_lineaje_body': _lineaje_body, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3e10a25ed153fef8abeb43e3911d18cca738c7f987e45ac22b0b7f3581d1cd4d', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'mistral-embed', 'provider': 'mistral', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Mistral', 'purl': 'pkg:aimodel/Mistral@embed', 'version': 'embed'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'function': 'BedrockEmbed.encode_queries', 'line': 533}, 'file': 'rag/llm/embedding_model.py', 'line': 533, 'function': 'encode_queries', 'agent_name': 'BedrockEmbed', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:f922df0eaac2116b'}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje__lineaje_body_evidence = _gr_client.enforce(_gr_site, _lineaje__lineaje_body_evidence, content_type='application/json')
            _lineaje_body = _lineaje__lineaje_body_evidence.get('_lineaje_body', _lineaje_body) if isinstance(_lineaje__lineaje_body_evidence, dict) else _lineaje_body
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        response = self.client.invoke_model(modelId=self.model_name, body=_lineaje_body)
        # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in BedrockEmbed.encode_queries).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:485c9444fb532fe40e31290498bb664f644c90544dfac1dbb3dc822bd2458eab'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:485c9444fb532fe40e31290498bb664f644c90544dfac1dbb3dc822bd2458eab', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'mistral-embed', 'provider': 'mistral', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Mistral', 'purl': 'pkg:aimodel/Mistral@embed', 'version': 'embed'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'function': 'BedrockEmbed.encode_queries', 'line': 533}, 'file': 'rag/llm/embedding_model.py', 'line': 533, 'function': 'encode_queries', 'agent_name': 'BedrockEmbed', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:f922df0eaac2116b'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            if not hasattr(_gr_client, 'enforce_reply'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
            response = _gr_client.enforce_reply(_gr_site, response, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        try:
            model_response = json.loads(response["body"].read())
            embeddings.extend(model_response["embedding"])
        except Exception as _e:
            log_exception(_e, response)

        return np.array(embeddings), token_count


class GeminiEmbed(Base):
    _FACTORY_NAME = "Gemini"

    def __init__(self, key, model_name="models/text-embedding-004", **kwargs):
        self.key = key
        self.model_name = "models/" + model_name

    def encode(self, texts: list):
        texts = [truncate(t, 2048) for t in texts]
        token_count = sum(num_tokens_from_string(text) for text in texts)
        genai.configure(api_key=self.key)
        batch_size = 16
        ress = []
        for i in range(0, len(texts), batch_size):
            result = genai.embed_content(model=self.model_name, content=texts[i : i + batch_size], task_type="retrieval_document", title="Embedding of single string")
            try:
                ress.extend(result["embedding"])
            except Exception as _e:
                log_exception(_e, result)
                raise Exception(f"Error: {result}")
        return np.array(ress), token_count

    def encode_queries(self, text):
        genai.configure(api_key=self.key)
        result = genai.embed_content(model=self.model_name, content=truncate(text, 2048), task_type="retrieval_document", title="Embedding of single string")
        token_count = num_tokens_from_string(text)
        try:
            return np.array(result["embedding"]), token_count
        except Exception as _e:
            log_exception(_e, result)
            raise Exception(f"Error: {result}")


class NvidiaEmbed(Base):
    _FACTORY_NAME = "NVIDIA"

    def __init__(self, key, model_name, base_url="https://integrate.api.nvidia.com/v1/embeddings"):
        if not base_url:
            base_url = "https://integrate.api.nvidia.com/v1/embeddings"
        self.api_key = key
        self.base_url = base_url
        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.api_key}",
        }
        self.model_name = model_name
        if model_name == "nvidia/embed-qa-4":
            self.base_url = "https://ai.api.nvidia.com/v1/retrieval/nvidia/embeddings"
            self.model_name = "NV-Embed-QA"
        if model_name == "snowflake/arctic-embed-l":
            self.base_url = "https://ai.api.nvidia.com/v1/retrieval/snowflake/arctic-embed-l/embeddings"

    def encode(self, texts: list):
        batch_size = 16
        ress = []
        token_count = 0
        for i in range(0, len(texts), batch_size):
            payload = {
                "input": texts[i : i + batch_size],
                "input_type": "query",
                "model": self.model_name,
                "encoding_format": "float",
                "truncate": "END",
            }
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in NvidiaEmbed.encode).
            #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:a3d896e80bf7c8fadcfef42bc9bcf01a52ef050158ae6514d6a48cb056a4388a'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a3d896e80bf7c8fadcfef42bc9bcf01a52ef050158ae6514d6a48cb056a4388a', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'line': 608, 'function': 'NvidiaEmbed.encode'}, 'file': 'rag/llm/embedding_model.py', 'line': 608, 'function': 'encode', 'agent_name': 'NvidiaEmbed', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=608)
            except _gr_client.GuardrailUnavailableError:
                pass
            try:
                res = response.json()
                ress.extend([d["embedding"] for d in res["data"]])
                token_count += total_token_count_from_response(res)
            except Exception as _e:
                log_exception(_e, response)
                raise Exception(f"Error: {response}")
        return np.array(ress), token_count

    def encode_queries(self, text):
        embds, cnt = self.encode([text])
        return np.array(embds[0]), cnt


class LmStudioEmbed(LocalAIEmbed):
    _FACTORY_NAME = "LM-Studio"

    def __init__(self, key, model_name, base_url):
        if not base_url:
            raise ValueError("Local llm url cannot be None")
        base_url = urljoin(base_url, "v1")
        self.client = OpenAI(api_key="lm-studio", base_url=base_url)
        self.model_name = model_name


class OpenAI_APIEmbed(OpenAIEmbed):
    _FACTORY_NAME = ["VLLM", "OpenAI-API-Compatible"]

    def __init__(self, key, model_name, base_url):
        if not base_url:
            raise ValueError("url cannot be None")
        base_url = urljoin(base_url, "v1")
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name.split("___")[0]


class CoHereEmbed(Base):
    _FACTORY_NAME = "Cohere"

    def __init__(self, key, model_name, base_url=None):
        from cohere import Client

        self.client = Client(api_key=key)
        self.model_name = model_name

    def encode(self, texts: list):
        batch_size = 16
        ress = []
        token_count = 0
        for i in range(0, len(texts), batch_size):
            res = self.client.embed(
                texts=texts[i : i + batch_size],
                model=self.model_name,
                input_type="search_document",
                embedding_types=["float"],
            )
            try:
                ress.extend([d for d in res.embeddings.float])
                token_count += total_token_count_from_response(res)
            except Exception as _e:
                log_exception(_e, res)
                raise Exception(f"Error: {res}")
        return np.array(ress), token_count

    def encode_queries(self, text):
        res = self.client.embed(
            texts=[text],
            model=self.model_name,
            input_type="search_query",
            embedding_types=["float"],
        )
        try:
            return np.array(res.embeddings.float[0]), int(total_token_count_from_response(res))
        except Exception as _e:
            log_exception(_e, res)
            raise Exception(f"Error: {res}")


class TogetherAIEmbed(OpenAIEmbed):
    _FACTORY_NAME = "TogetherAI"

    def __init__(self, key, model_name, base_url="https://api.together.xyz/v1"):
        if not base_url:
            base_url = "https://api.together.xyz/v1"
        super().__init__(key, model_name, base_url=base_url)


class PerfXCloudEmbed(OpenAIEmbed):
    _FACTORY_NAME = "PerfXCloud"

    def __init__(self, key, model_name, base_url="https://cloud.perfxlab.cn/v1"):
        if not base_url:
            base_url = "https://cloud.perfxlab.cn/v1"
        super().__init__(key, model_name, base_url)


class UpstageEmbed(OpenAIEmbed):
    _FACTORY_NAME = "Upstage"

    def __init__(self, key, model_name, base_url="https://api.upstage.ai/v1/solar"):
        if not base_url:
            base_url = "https://api.upstage.ai/v1/solar"
        super().__init__(key, model_name, base_url)


class SILICONFLOWEmbed(Base):
    _FACTORY_NAME = "SILICONFLOW"

    def __init__(self, key, model_name, base_url="https://api.siliconflow.cn/v1/embeddings"):
        if not base_url:
            base_url = "https://api.siliconflow.cn/v1/embeddings"
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {key}",
        }
        self.base_url = base_url
        self.model_name = model_name

    def encode(self, texts: list):
        batch_size = 16
        ress = []
        token_count = 0
        for i in range(0, len(texts), batch_size):
            texts_batch = texts[i : i + batch_size]
            if self.model_name in ["BAAI/bge-large-zh-v1.5", "BAAI/bge-large-en-v1.5"]:
                # limit 512, 340 is almost safe
                texts_batch = [" " if not text.strip() else truncate(text, 256) for text in texts_batch]
            else:
                texts_batch = [" " if not text.strip() else text for text in texts_batch]

            payload = {
                "model": self.model_name,
                "input": texts_batch,
                "encoding_format": "float",
            }
            response = requests.post(self.base_url, json=payload, headers=self.headers)
            # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in SILICONFLOWEmbed.encode).
            #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:88ec57aedc032822dac9d16d66610f4517619a8d981458408773ee9eaba5853e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:88ec57aedc032822dac9d16d66610f4517619a8d981458408773ee9eaba5853e', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'line': 745, 'function': 'SILICONFLOWEmbed.encode'}, 'file': 'rag/llm/embedding_model.py', 'line': 745, 'function': 'encode', 'agent_name': 'SILICONFLOWEmbed', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=745)
            except _gr_client.GuardrailUnavailableError:
                pass
            try:
                res = response.json()
                ress.extend([d["embedding"] for d in res["data"]])
                token_count += total_token_count_from_response(res)
            except Exception as _e:
                log_exception(_e, response)
                raise Exception(f"Error: {response}")

        return np.array(ress), token_count

    def encode_queries(self, text):
        payload = {
            "model": self.model_name,
            "input": text,
            "encoding_format": "float",
        }
        response = requests.post(self.base_url, json=payload, headers=self.headers)
        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in SILICONFLOWEmbed.encode_queries).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d1626d15512a5cc5d22f931bc054da6954520d0835ccdbffc898296c20a68ac7'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d1626d15512a5cc5d22f931bc054da6954520d0835ccdbffc898296c20a68ac7', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'line': 762, 'function': 'SILICONFLOWEmbed.encode_queries'}, 'file': 'rag/llm/embedding_model.py', 'line': 762, 'function': 'encode_queries', 'agent_name': 'SILICONFLOWEmbed', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=762)
        except _gr_client.GuardrailUnavailableError:
            pass
        try:
            res = response.json()
            return np.array(res["data"][0]["embedding"]), total_token_count_from_response(res)
        except Exception as _e:
            log_exception(_e, response)
            raise Exception(f"Error: {response}")


class ReplicateEmbed(Base):
    _FACTORY_NAME = "Replicate"

    def __init__(self, key, model_name, base_url=None):
        from replicate.client import Client

        self.model_name = model_name
        self.client = Client(api_token=key)

    def encode(self, texts: list):
        batch_size = 16
        token_count = sum([num_tokens_from_string(text) for text in texts])
        ress = []
        for i in range(0, len(texts), batch_size):
            res = self.client.run(self.model_name, input={"texts": texts[i : i + batch_size]})
            ress.extend(res)
        return np.array(ress), token_count

    def encode_queries(self, text):
        res = self.client.embed(self.model_name, input={"texts": [text]})
        return np.array(res), num_tokens_from_string(text)


class BaiduYiyanEmbed(Base):
    _FACTORY_NAME = "BaiduYiyan"

    def __init__(self, key, model_name, base_url=None):
        import qianfan

        key = json.loads(key)
        ak = key.get("yiyan_ak", "")
        sk = key.get("yiyan_sk", "")
        self.client = qianfan.Embedding(ak=ak, sk=sk)
        self.model_name = model_name

    def encode(self, texts: list, batch_size=16):
        res = self.client.do(model=self.model_name, texts=texts).body
        try:
            return (
                np.array([r["embedding"] for r in res["data"]]),
                total_token_count_from_response(res),
            )
        except Exception as _e:
            log_exception(_e, res)
            raise Exception(f"Error: {res}")

    def encode_queries(self, text):
        res = self.client.do(model=self.model_name, texts=[text]).body
        try:
            return (
                np.array([r["embedding"] for r in res["data"]]),
                total_token_count_from_response(res),
            )
        except Exception as _e:
            log_exception(_e, res)
            raise Exception(f"Error: {res}")


class VoyageEmbed(Base):
    _FACTORY_NAME = "Voyage AI"

    def __init__(self, key, model_name, base_url=None):
        import voyageai

        self.client = voyageai.Client(api_key=key)
        self.model_name = model_name

    def encode(self, texts: list):
        batch_size = 16
        ress = []
        token_count = 0
        for i in range(0, len(texts), batch_size):
            res = self.client.embed(texts=texts[i : i + batch_size], model=self.model_name, input_type="document")
            try:
                ress.extend(res.embeddings)
                token_count += res.total_tokens
            except Exception as _e:
                log_exception(_e, res)
                raise Exception(f"Error: {res}")
        return np.array(ress), token_count

    def encode_queries(self, text):
        res = self.client.embed(texts=text, model=self.model_name, input_type="query")
        try:
            return np.array(res.embeddings)[0], res.total_tokens
        except Exception as _e:
            log_exception(_e, res)
            raise Exception(f"Error: {res}")


class HuggingFaceEmbed(Base):
    _FACTORY_NAME = "HuggingFace"

    def __init__(self, key, model_name, base_url=None, **kwargs):
        if not model_name:
            raise ValueError("Model name cannot be None")
        self.key = key
        self.model_name = model_name.split("___")[0]
        self.base_url = base_url or "http://127.0.0.1:8080"

    def encode(self, texts: list):
        response = requests.post(f"{self.base_url}/embed", json={"inputs": texts}, headers={"Content-Type": "application/json"})
        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in HuggingFaceEmbed.encode).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a265c01a73b12f467044323697b38ee4f39a206012715789acc33c7e388e3412'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a265c01a73b12f467044323697b38ee4f39a206012715789acc33c7e388e3412', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'line': 872, 'function': 'HuggingFaceEmbed.encode'}, 'file': 'rag/llm/embedding_model.py', 'line': 872, 'function': 'encode', 'agent_name': 'HuggingFaceEmbed', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=872)
        except _gr_client.GuardrailUnavailableError:
            pass
        if response.status_code == 200:
            embeddings = response.json()
        else:
            raise Exception(f"Error: {response.status_code} - {response.text}")
        return np.array(embeddings), sum([num_tokens_from_string(text) for text in texts])

    def encode_queries(self, text: str):
        response = requests.post(f"{self.base_url}/embed", json={"inputs": text}, headers={"Content-Type": "application/json"})
        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in HuggingFaceEmbed.encode_queries).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f8d8e57a922154ef51ba0b2a1e6cb46208dbd2ce03ebe46e5e00ff35b8c91995'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f8d8e57a922154ef51ba0b2a1e6cb46208dbd2ce03ebe46e5e00ff35b8c91995', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/embedding_model.py', 'line': 880, 'function': 'HuggingFaceEmbed.encode_queries'}, 'file': 'rag/llm/embedding_model.py', 'line': 880, 'function': 'encode_queries', 'agent_name': 'HuggingFaceEmbed', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=880)
        except _gr_client.GuardrailUnavailableError:
            pass
        if response.status_code == 200:
            embedding = response.json()[0]
            return np.array(embedding), num_tokens_from_string(text)
        else:
            raise Exception(f"Error: {response.status_code} - {response.text}")


class VolcEngineEmbed(OpenAIEmbed):
    _FACTORY_NAME = "VolcEngine"

    def __init__(self, key, model_name, base_url="https://ark.cn-beijing.volces.com/api/v3"):
        if not base_url:
            base_url = "https://ark.cn-beijing.volces.com/api/v3"
        ark_api_key = json.loads(key).get("ark_api_key", "")
        model_name = json.loads(key).get("ep_id", "") + json.loads(key).get("endpoint_id", "")
        super().__init__(ark_api_key, model_name, base_url)


class GPUStackEmbed(OpenAIEmbed):
    _FACTORY_NAME = "GPUStack"

    def __init__(self, key, model_name, base_url):
        if not base_url:
            raise ValueError("url cannot be None")
        base_url = urljoin(base_url, "v1")

        self.client = OpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name


class NovitaEmbed(SILICONFLOWEmbed):
    _FACTORY_NAME = "NovitaAI"

    def __init__(self, key, model_name, base_url="https://api.novita.ai/v3/openai/embeddings"):
        if not base_url:
            base_url = "https://api.novita.ai/v3/openai/embeddings"
        super().__init__(key, model_name, base_url)


class GiteeEmbed(SILICONFLOWEmbed):
    _FACTORY_NAME = "GiteeAI"

    def __init__(self, key, model_name, base_url="https://ai.gitee.com/v1/embeddings"):
        if not base_url:
            base_url = "https://ai.gitee.com/v1/embeddings"
        super().__init__(key, model_name, base_url)

class DeepInfraEmbed(OpenAIEmbed):
    _FACTORY_NAME = "DeepInfra"

    def __init__(self, key, model_name, base_url="https://api.deepinfra.com/v1/openai"):
        if not base_url:
            base_url = "https://api.deepinfra.com/v1/openai"
        super().__init__(key, model_name, base_url)


class Ai302Embed(Base):
    _FACTORY_NAME = "302.AI"

    def __init__(self, key, model_name, base_url="https://api.302.ai/v1/embeddings"):
        if not base_url:
            base_url = "https://api.302.ai/v1/embeddings"
        super().__init__(key, model_name, base_url)


class CometAPIEmbed(OpenAIEmbed):
    _FACTORY_NAME = "CometAPI"

    def __init__(self, key, model_name, base_url="https://api.cometapi.com/v1"):
        if not base_url:
            base_url = "https://api.cometapi.com/v1"
        super().__init__(key, model_name, base_url)

class DeerAPIEmbed(OpenAIEmbed):
    _FACTORY_NAME = "DeerAPI"

    def __init__(self, key, model_name, base_url="https://api.deerapi.com/v1"):
        if not base_url:
            base_url = "https://api.deerapi.com/v1"
        super().__init__(key, model_name, base_url)


class JiekouAIEmbed(OpenAIEmbed):
    _FACTORY_NAME = "Jiekou.AI"

    def __init__(self, key, model_name, base_url="https://api.jiekou.ai/openai/v1/embeddings"):
        if not base_url:
            base_url = "https://api.jiekou.ai/openai/v1/embeddings"
        super().__init__(key, model_name, base_url)
