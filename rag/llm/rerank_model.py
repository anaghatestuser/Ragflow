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
from abc import ABC
from urllib.parse import urljoin

import httpx
import numpy as np
import requests
from yarl import URL

from common.log_utils import log_exception
from common.token_utils import num_tokens_from_string, truncate, total_token_count_from_response

class Base(ABC):
    def __init__(self, key, model_name, **kwargs):
        """
        Abstract base class constructor.
        Parameters are not stored; initialization is left to subclasses.
        """
        pass

    def similarity(self, query: str, texts: list):
        raise NotImplementedError("Please implement encode method!")


class JinaRerank(Base):
    _FACTORY_NAME = "Jina"

    def __init__(self, key, model_name="jina-reranker-v2-base-multilingual", base_url="https://api.jina.ai/v1/rerank"):
        self.base_url = "https://api.jina.ai/v1/rerank"
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
        self.model_name = model_name

    def similarity(self, query: str, texts: list):
        texts = [truncate(t, 8196) for t in texts]
        data = {"model": self.model_name, "query": query, "documents": texts, "top_n": len(texts)}
        res = requests.post(self.base_url, headers=self.headers, json=data).json()
        rank = np.zeros(len(texts), dtype=float)
        try:
            for d in res["results"]:
                rank[d["index"]] = d["relevance_score"]
        except Exception as _e:
            log_exception(_e, res)
        return rank, total_token_count_from_response(res)


class XInferenceRerank(Base):
    _FACTORY_NAME = "Xinference"

    def __init__(self, key="x", model_name="", base_url=""):
        if base_url.find("/v1") == -1:
            base_url = urljoin(base_url, "/v1/rerank")
        if base_url.find("/rerank") == -1:
            base_url = urljoin(base_url, "/v1/rerank")
        self.model_name = model_name
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json", "accept": "application/json"}
        if key and key != "x":
            self.headers["Authorization"] = f"Bearer {key}"

    def similarity(self, query: str, texts: list):
        if len(texts) == 0:
            return np.array([]), 0
        pairs = [(query, truncate(t, 4096)) for t in texts]
        token_count = 0
        for _, t in pairs:
            token_count += num_tokens_from_string(t)
        data = {"model": self.model_name, "query": query, "return_documents": "true", "return_len": "true", "documents": texts}
        res = requests.post(self.base_url, headers=self.headers, json=data).json()
        rank = np.zeros(len(texts), dtype=float)
        try:
            for d in res["results"]:
                rank[d["index"]] = d["relevance_score"]
        except Exception as _e:
            log_exception(_e, res)
        return rank, token_count


class LocalAIRerank(Base):
    _FACTORY_NAME = "LocalAI"

    def __init__(self, key, model_name, base_url):
        if base_url.find("/rerank") == -1:
            self.base_url = urljoin(base_url, "/rerank")
        else:
            self.base_url = base_url
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
        self.model_name = model_name.split("___")[0]

    def similarity(self, query: str, texts: list):
        # noway to config Ragflow , use fix setting
        texts = [truncate(t, 500) for t in texts]
        data = {
            "model": self.model_name,
            "query": query,
            "documents": texts,
            "top_n": len(texts),
        }
        token_count = 0
        for t in texts:
            token_count += num_tokens_from_string(t)
        res = requests.post(self.base_url, headers=self.headers, json=data).json()
        rank = np.zeros(len(texts), dtype=float)
        try:
            for d in res["results"]:
                rank[d["index"]] = d["relevance_score"]
        except Exception as _e:
            log_exception(_e, res)

        # Normalize the rank values to the range 0 to 1
        min_rank = np.min(rank)
        max_rank = np.max(rank)

        # Avoid division by zero if all ranks are identical
        if not np.isclose(min_rank, max_rank, atol=1e-3):
            rank = (rank - min_rank) / (max_rank - min_rank)
        else:
            rank = np.zeros_like(rank)

        return rank, token_count


class NvidiaRerank(Base):
    _FACTORY_NAME = "NVIDIA"

    def __init__(self, key, model_name, base_url="https://ai.api.nvidia.com/v1/retrieval/nvidia/"):
        if not base_url:
            base_url = "https://ai.api.nvidia.com/v1/retrieval/nvidia/"
        self.model_name = model_name

        if self.model_name == "nvidia/nv-rerankqa-mistral-4b-v3":
            self.base_url = urljoin(base_url, "nv-rerankqa-mistral-4b-v3/reranking")

        if self.model_name == "nvidia/rerank-qa-mistral-4b":
            self.base_url = urljoin(base_url, "reranking")
            self.model_name = "nv-rerank-qa-mistral-4b:1"

        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        }

    def similarity(self, query: str, texts: list):
        token_count = num_tokens_from_string(query) + sum([num_tokens_from_string(t) for t in texts])
        data = {
            "model": self.model_name,
            "query": {"text": query},
            "passages": [{"text": text} for text in texts],
            "truncate": "END",
            "top_n": len(texts),
        }
        res = requests.post(self.base_url, headers=self.headers, json=data).json()
        rank = np.zeros(len(texts), dtype=float)
        try:
            for d in res["rankings"]:
                rank[d["index"]] = d["logit"]
        except Exception as _e:
            log_exception(_e, res)
        return rank, token_count


class LmStudioRerank(Base):
    _FACTORY_NAME = "LM-Studio"

    def __init__(self, key, model_name, base_url, **kwargs):
        pass

    def similarity(self, query: str, texts: list):
        raise NotImplementedError("The LmStudioRerank has not been implement")


class OpenAI_APIRerank(Base):
    _FACTORY_NAME = "OpenAI-API-Compatible"

    def __init__(self, key, model_name, base_url):
        if base_url.find("/rerank") == -1:
            self.base_url = urljoin(base_url, "/rerank")
        else:
            self.base_url = base_url
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
        self.model_name = model_name.split("___")[0]

    def similarity(self, query: str, texts: list):
        # noway to config Ragflow , use fix setting
        texts = [truncate(t, 500) for t in texts]
        data = {
            "model": self.model_name,
            "query": query,
            "documents": texts,
            "top_n": len(texts),
        }
        token_count = 0
        for t in texts:
            token_count += num_tokens_from_string(t)
        res = requests.post(self.base_url, headers=self.headers, json=data).json()
        rank = np.zeros(len(texts), dtype=float)
        try:
            for d in res["results"]:
                rank[d["index"]] = d["relevance_score"]
        except Exception as _e:
            log_exception(_e, res)

        # Normalize the rank values to the range 0 to 1
        min_rank = np.min(rank)
        max_rank = np.max(rank)

        # Avoid division by zero if all ranks are identical
        if not np.isclose(min_rank, max_rank, atol=1e-3):
            rank = (rank - min_rank) / (max_rank - min_rank)
        else:
            rank = np.zeros_like(rank)

        return rank, token_count


class CoHereRerank(Base):
    _FACTORY_NAME = ["Cohere", "VLLM"]

    def __init__(self, key, model_name, base_url=None):
        from cohere import Client

        # Only pass base_url if it's a non-empty string, otherwise use default Cohere API endpoint
        client_kwargs = {"api_key": key}
        if base_url and base_url.strip():
            client_kwargs["base_url"] = base_url
        self.client = Client(**client_kwargs)
        self.model_name = model_name.split("___")[0]

    def similarity(self, query: str, texts: list):
        token_count = num_tokens_from_string(query) + sum([num_tokens_from_string(t) for t in texts])
        res = self.client.rerank(
            model=self.model_name,
            query=query,
            documents=texts,
            top_n=len(texts),
            return_documents=False,
        )
        rank = np.zeros(len(texts), dtype=float)
        try:
            for d in res.results:
                rank[d.index] = d.relevance_score
        except Exception as _e:
            log_exception(_e, res)
        return rank, token_count


class TogetherAIRerank(Base):
    _FACTORY_NAME = "TogetherAI"

    def __init__(self, key, model_name, base_url, **kwargs):
        pass

    def similarity(self, query: str, texts: list):
        raise NotImplementedError("The api has not been implement")


class SILICONFLOWRerank(Base):
    _FACTORY_NAME = "SILICONFLOW"

    def __init__(self, key, model_name, base_url="https://api.siliconflow.cn/v1/rerank"):
        if not base_url:
            base_url = "https://api.siliconflow.cn/v1/rerank"
        self.model_name = model_name
        self.base_url = base_url
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {key}",
        }

    def similarity(self, query: str, texts: list):
        payload = {
            "model": self.model_name,
            "query": query,
            "documents": texts,
            "top_n": len(texts),
            "return_documents": False,
            "max_chunks_per_doc": 1024,
            "overlap_tokens": 80,
        }
        response = requests.post(self.base_url, json=payload, headers=self.headers).json()
        rank = np.zeros(len(texts), dtype=float)
        try:
            for d in response["results"]:
                rank[d["index"]] = d["relevance_score"]
        except Exception as _e:
            log_exception(_e, response)
        return (
            rank,
            total_token_count_from_response(response),
        )


class BaiduYiyanRerank(Base):
    _FACTORY_NAME = "BaiduYiyan"

    def __init__(self, key, model_name, base_url=None):
        from qianfan.resources import Reranker

        key = json.loads(key)
        ak = key.get("yiyan_ak", "")
        sk = key.get("yiyan_sk", "")
        self.client = Reranker(ak=ak, sk=sk)
        self.model_name = model_name

    def similarity(self, query: str, texts: list):
        res = self.client.do(
            model=self.model_name,
            query=query,
            documents=texts,
            top_n=len(texts),
        ).body
        rank = np.zeros(len(texts), dtype=float)
        try:
            for d in res["results"]:
                rank[d["index"]] = d["relevance_score"]
        except Exception as _e:
            log_exception(_e, res)
        return rank, total_token_count_from_response(res)


class VoyageRerank(Base):
    _FACTORY_NAME = "Voyage AI"

    def __init__(self, key, model_name, base_url=None):
        import voyageai

        self.client = voyageai.Client(api_key=key)
        self.model_name = model_name

    def similarity(self, query: str, texts: list):
        if not texts:
            return np.array([]), 0
        rank = np.zeros(len(texts), dtype=float)

        res = self.client.rerank(query=query, documents=texts, model=self.model_name, top_k=len(texts))
        try:
            for r in res.results:
                rank[r.index] = r.relevance_score
        except Exception as _e:
            log_exception(_e, res)
        return rank, res.total_tokens


class QWenRerank(Base):
    _FACTORY_NAME = "Tongyi-Qianwen"

    def __init__(self, key, model_name="gte-rerank", base_url=None, **kwargs):
        import dashscope

        self.api_key = key
        self.model_name = dashscope.TextReRank.Models.gte_rerank if model_name is None else model_name

    def similarity(self, query: str, texts: list):
        from http import HTTPStatus

        import dashscope

        resp = dashscope.TextReRank.call(api_key=self.api_key, model=self.model_name, query=query, documents=texts, top_n=len(texts), return_documents=False)
        rank = np.zeros(len(texts), dtype=float)
        if resp.status_code == HTTPStatus.OK:
            try:
                for r in resp.output.results:
                    rank[r.index] = r.relevance_score
            except Exception as _e:
                log_exception(_e, resp)
            return rank, total_token_count_from_response(resp)
        else:
            raise ValueError(f"Error calling QWenRerank model {self.model_name}: {resp.status_code} - {resp.text}")


class HuggingfaceRerank(Base):
    _FACTORY_NAME = "HuggingFace"

    @staticmethod
    def post(query: str, texts: list, url="127.0.0.1"):
        exc = None
        scores = [0 for _ in range(len(texts))]
        batch_size = 8
        for i in range(0, len(texts), batch_size):
            try:
                res = requests.post(
                    f"http://{url}/rerank", headers={"Content-Type": "application/json"}, json={"query": query, "texts": texts[i : i + batch_size], "raw_scores": False, "truncate": True}
                )
                # LINEAJE: runtime guardrail checks `res` as it flows from an external API to the agent, after the tool returns (in HuggingfaceRerank.post).
                #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:cbfaad857c67e3ef60d60e47dfa1502ca99f01c1364044fcd5516f94dc7f2385'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cbfaad857c67e3ef60d60e47dfa1502ca99f01c1364044fcd5516f94dc7f2385', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/rerank_model.py', 'line': 397, 'function': 'HuggingfaceRerank.post'}, 'file': 'rag/llm/rerank_model.py', 'line': 397, 'function': 'post', 'agent_name': 'HuggingfaceRerank', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    res = _gr_client.enforce(_gr_site, res, content_type='application/json', variable_name='res', source_file=__file__, before_line=397)
                except _gr_client.GuardrailUnavailableError:
                    pass

                for o in res.json():
                    scores[o["index"] + i] = o["score"]
            except Exception as e:
                exc = e

        if exc:
            raise exc
        return np.array(scores)

    def __init__(self, key, model_name="BAAI/bge-reranker-v2-m3", base_url="http://127.0.0.1"):
        self.model_name = model_name.split("___")[0]
        self.base_url = base_url

    def similarity(self, query: str, texts: list) -> tuple[np.ndarray, int]:
        if not texts:
            return np.array([]), 0
        token_count = 0
        for t in texts:
            token_count += num_tokens_from_string(t)
        return HuggingfaceRerank.post(query, texts, self.base_url), token_count


class GPUStackRerank(Base):
    _FACTORY_NAME = "GPUStack"

    def __init__(self, key, model_name, base_url):
        if not base_url:
            raise ValueError("url cannot be None")

        self.model_name = model_name
        self.base_url = str(URL(base_url) / "v1" / "rerank")
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {key}",
        }

    def similarity(self, query: str, texts: list):
        payload = {
            "model": self.model_name,
            "query": query,
            "documents": texts,
            "top_n": len(texts),
        }

        try:
            response = requests.post(self.base_url, json=payload, headers=self.headers)
            # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in GPUStackRerank.similarity).
            #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:67ba77fec33f53794c10d8dcb11ffc89a958479866c40fbebd64b458d2491d18'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:67ba77fec33f53794c10d8dcb11ffc89a958479866c40fbebd64b458d2491d18', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/rerank_model.py', 'line': 447, 'function': 'GPUStackRerank.similarity'}, 'file': 'rag/llm/rerank_model.py', 'line': 447, 'function': 'similarity', 'agent_name': 'GPUStackRerank', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=447)
            except _gr_client.GuardrailUnavailableError:
                pass
            response.raise_for_status()
            response_json = response.json()

            rank = np.zeros(len(texts), dtype=float)

            token_count = 0
            for t in texts:
                token_count += num_tokens_from_string(t)
            try:
                for result in response_json["results"]:
                    rank[result["index"]] = result["relevance_score"]
            except Exception as _e:
                log_exception(_e, response)

            return (
                rank,
                token_count,
            )

        except httpx.HTTPStatusError as e:
            raise ValueError(f"Error calling GPUStackRerank model {self.model_name}: {e.response.status_code} - {e.response.text}")


class NovitaRerank(JinaRerank):
    _FACTORY_NAME = "NovitaAI"

    def __init__(self, key, model_name, base_url="https://api.novita.ai/v3/openai/rerank"):
        if not base_url:
            base_url = "https://api.novita.ai/v3/openai/rerank"
        super().__init__(key, model_name, base_url)


class GiteeRerank(JinaRerank):
    _FACTORY_NAME = "GiteeAI"

    def __init__(self, key, model_name, base_url="https://ai.gitee.com/v1/rerank"):
        if not base_url:
            base_url = "https://ai.gitee.com/v1/rerank"
        super().__init__(key, model_name, base_url)


class Ai302Rerank(Base):
    _FACTORY_NAME = "302.AI"

    def __init__(self, key, model_name, base_url="https://api.302.ai/v1/rerank"):
        if not base_url:
            base_url = "https://api.302.ai/v1/rerank"
        super().__init__(key, model_name, base_url)


class JiekouAIRerank(JinaRerank):
    _FACTORY_NAME = "Jiekou.AI"

    def __init__(self, key, model_name, base_url="https://api.jiekou.ai/openai/v1/rerank"):
        if not base_url:
            base_url = "https://api.jiekou.ai/openai/v1/rerank"
        super().__init__(key, model_name, base_url)
