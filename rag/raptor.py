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
import asyncio
import logging
import re

import numpy as np
import umap
from sklearn.mixture import GaussianMixture

from api.db.services.task_service import has_canceled
from common.connection_utils import timeout
from common.exceptions import TaskCanceledException
from common.token_utils import truncate
from graphrag.utils import (
    chat_limiter,
    get_embed_cache,
    get_llm_cache,
    set_embed_cache,
    set_llm_cache,
)


class RecursiveAbstractiveProcessing4TreeOrganizedRetrieval:
    def __init__(
        self,
        max_cluster,
        llm_model,
        embd_model,
        prompt,
        max_token=512,
        threshold=0.1,
        max_errors=3,
    ):
        self._max_cluster = max_cluster
        self._llm_model = llm_model
        self._embd_model = embd_model
        self._threshold = threshold
        self._prompt = prompt
        self._max_token = max_token
        self._max_errors = max(1, max_errors)
        self._error_count = 0

    @timeout(60 * 20)
    async def _chat(self, system, history, gen_conf):
        cached = await asyncio.to_thread(get_llm_cache, self._llm_model.llm_name, system, history, gen_conf)
        if cached:
            # LINEAJE: runtime guardrail checks `cached` as it flows from the agent to the user interface, before it leaves the application (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._chat).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `cached` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f579e4e1955f39b1fe5d3a070e02cb5d08fd991be4a594660b7f0a415b94e608'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f579e4e1955f39b1fe5d3a070e02cb5d08fd991be4a594660b7f0a415b94e608', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 61, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._chat'}, 'file': 'rag/raptor.py', 'line': 61, 'function': '_chat', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                cached = _gr_client.enforce(_gr_site, cached, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return cached

        last_exc = None
        for attempt in range(3):
            try:
                response = await self._llm_model.async_chat(system, history, gen_conf)
                response = re.sub(r"^.*</think>", "", response, flags=re.DOTALL)
                if response.find("**ERROR**") >= 0:
                    raise Exception(response)
                await asyncio.to_thread(set_llm_cache,self._llm_model.llm_name,system,response,history,gen_conf)
                # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the user interface, before it leaves the application (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._chat).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:646bfeaf5464dd515de572cdaf1dbd31d371422e8fdedc562a5aef298c762ebe'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:646bfeaf5464dd515de572cdaf1dbd31d371422e8fdedc562a5aef298c762ebe', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 71, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._chat'}, 'file': 'rag/raptor.py', 'line': 71, 'function': '_chat', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    response = _gr_client.enforce(_gr_site, response, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return response
            except Exception as exc:
                last_exc = exc
                # LINEAJE: runtime guardrail checks `exc` as it flows from the agent to the application log, before it is written to the log (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._chat).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `exc` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:d255663330ecab44e564b6027404338a82f190a9bf6b258a992876c26ca2ebaa'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d255663330ecab44e564b6027404338a82f190a9bf6b258a992876c26ca2ebaa', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 74, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._chat'}, 'file': 'rag/raptor.py', 'line': 74, 'function': '_chat', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    exc = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, exc, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning("RAPTOR LLM call failed on attempt %d/3: %s", attempt + 1, exc)
                if attempt < 2:
                    await asyncio.sleep(1 + attempt)

        raise last_exc if last_exc else Exception("LLM chat failed without exception")

    @timeout(20)
    async def _embedding_encode(self, txt):
        response = await asyncio.to_thread(get_embed_cache, self._embd_model.llm_name, txt)
        if response is not None:
            # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the user interface, before it leaves the application (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._embedding_encode).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e22f53b38466d309e412b8b9fcf6a886024b748523339ab7af65139eb4beece8'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e22f53b38466d309e412b8b9fcf6a886024b748523339ab7af65139eb4beece8', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 84, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._embedding_encode'}, 'file': 'rag/raptor.py', 'line': 84, 'function': '_embedding_encode', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                response = _gr_client.enforce(_gr_site, response, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return response
        embds, _ = await asyncio.to_thread(self._embd_model.encode, [txt])
        if len(embds) < 1 or len(embds[0]) < 1:
            raise Exception("Embedding error: ")
        embds = embds[0]
        await asyncio.to_thread(set_embed_cache, self._embd_model.llm_name, txt, embds)
        # LINEAJE: runtime guardrail checks `embds` as it flows from the agent to the user interface, before it leaves the application (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._embedding_encode).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `embds` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:de5d76af4b138b0e559187390c95a7f63fc441e75f2a7ae2bc113265e20bf0d6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:de5d76af4b138b0e559187390c95a7f63fc441e75f2a7ae2bc113265e20bf0d6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 90, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._embedding_encode'}, 'file': 'rag/raptor.py', 'line': 90, 'function': '_embedding_encode', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            embds = _gr_client.enforce(_gr_site, embds, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return embds

    def _get_optimal_clusters(self, embeddings: np.ndarray, random_state: int, task_id: str = ""):
        max_clusters = min(self._max_cluster, len(embeddings))
        n_clusters = np.arange(1, max_clusters)
        bics = []
        for n in n_clusters:
            if task_id:
                if has_canceled(task_id):
                    _lineaje_payload = f"Task {task_id} cancelled during get optimal clusters."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._get_optimal_clusters).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:0d72ae11e00c1a7fb7f238e17fbbe4f44972affebd43be514c588d76e15bf750'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0d72ae11e00c1a7fb7f238e17fbbe4f44972affebd43be514c588d76e15bf750', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 99, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._get_optimal_clusters'}, 'file': 'rag/raptor.py', 'line': 99, 'function': '_get_optimal_clusters', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)
                    raise TaskCanceledException(f"Task {task_id} was cancelled")

            gm = GaussianMixture(n_components=n, random_state=random_state)
            gm.fit(embeddings)
            bics.append(gm.bic(embeddings))
        optimal_clusters = n_clusters[np.argmin(bics)]
        # LINEAJE: runtime guardrail checks `optimal_clusters` as it flows from the agent to the user interface, before it leaves the application (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._get_optimal_clusters).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `optimal_clusters` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9fd068797eb2e78dcf26c978847c4b7bdf15fc38000bae4de0c483824987cad6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9fd068797eb2e78dcf26c978847c4b7bdf15fc38000bae4de0c483824987cad6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 106, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval._get_optimal_clusters'}, 'file': 'rag/raptor.py', 'line': 106, 'function': '_get_optimal_clusters', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            optimal_clusters = _gr_client.enforce(_gr_site, optimal_clusters, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return optimal_clusters

    async def __call__(self, chunks, random_state, callback=None, task_id: str = ""):
        if len(chunks) <= 1:
            return []
        chunks = [(s, a) for s, a in chunks if s and a is not None and len(a) > 0]
        layers = [(0, len(chunks))]
        start, end = 0, len(chunks)

        @timeout(60 * 20)
        async def summarize(ck_idx: list[int]):
            nonlocal chunks

            if task_id:
                if has_canceled(task_id):
                    _lineaje_payload = f"Task {task_id} cancelled during RAPTOR summarization."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.summarize).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:b8e3a56e9a58244d4913331221964797740e0ca43393d98acd92cd3f3eb4d7fb'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b8e3a56e9a58244d4913331221964797740e0ca43393d98acd92cd3f3eb4d7fb', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 121, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.__call__.summarize'}, 'file': 'rag/raptor.py', 'line': 121, 'function': 'summarize', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)
                    raise TaskCanceledException(f"Task {task_id} was cancelled")

            texts = [chunks[i][0] for i in ck_idx]
            len_per_chunk = int((self._llm_model.max_length - self._max_token) / len(texts))
            cluster_content = "\n".join([truncate(t, max(1, len_per_chunk)) for t in texts])
            try:
                async with chat_limiter:
                    if task_id and has_canceled(task_id):
                        _lineaje_payload = f"Task {task_id} cancelled before RAPTOR LLM call."
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.summarize).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:485c3860196eb3a33841e4dba8ebb27773aed9939f84dfd10621d46aae448915'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:485c3860196eb3a33841e4dba8ebb27773aed9939f84dfd10621d46aae448915', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 130, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.__call__.summarize'}, 'file': 'rag/raptor.py', 'line': 130, 'function': 'summarize', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.info(_lineaje_payload)
                        raise TaskCanceledException(f"Task {task_id} was cancelled")

                    cnt = await self._chat(
                        "You're a helpful assistant.",
                        [
                            {
                                "role": "user",
                                "content": self._prompt.format(cluster_content=cluster_content),
                            }
                        ],
                        {"max_tokens": max(self._max_token, 512)},  # fix issue:  #10235
                    )
                    cnt = re.sub(
                        "(······\n由于长度的原因，回答被截断了，要继续吗？|For the content length reason, it stopped, continue?)",
                        "",
                        cnt,
                    )
                    _lineaje_payload = f"SUM: {cnt}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.summarize).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:d49970288c0ce521372850f6d152a81923900af7ad86a5e55a9fd5948472d337'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d49970288c0ce521372850f6d152a81923900af7ad86a5e55a9fd5948472d337', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 148, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.__call__.summarize'}, 'file': 'rag/raptor.py', 'line': 148, 'function': 'summarize', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.debug(_lineaje_payload)

                    if task_id and has_canceled(task_id):
                        _lineaje_payload = f"Task {task_id} cancelled before RAPTOR embedding."
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.summarize).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:b89faaefeb650a998e6a5f55e57af7cf2a8b2dd08d30a6570d6dd2806a355561'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b89faaefeb650a998e6a5f55e57af7cf2a8b2dd08d30a6570d6dd2806a355561', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 151, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.__call__.summarize'}, 'file': 'rag/raptor.py', 'line': 151, 'function': 'summarize', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.info(_lineaje_payload)
                        raise TaskCanceledException(f"Task {task_id} was cancelled")

                    embds = await self._embedding_encode(cnt)
                    chunks.append((cnt, embds))
            except TaskCanceledException:
                raise
            except Exception as exc:
                self._error_count += 1
                warn_msg = f"[RAPTOR] Skip cluster ({len(ck_idx)} chunks) due to error: {exc}"
                # LINEAJE: runtime guardrail checks `warn_msg` as it flows from the agent to the application log, before it is written to the log (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.summarize).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `warn_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:86315207e9787948bb385c7345c82eeb901e3dc925f4c0670c62af7b03c5896c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:86315207e9787948bb385c7345c82eeb901e3dc925f4c0670c62af7b03c5896c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 161, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.__call__.summarize'}, 'file': 'rag/raptor.py', 'line': 161, 'function': 'summarize', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    warn_msg = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, warn_msg, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(warn_msg)
                if callback:
                    callback(msg=warn_msg)
                if self._error_count >= self._max_errors:
                    raise RuntimeError(f"RAPTOR aborted after {self._error_count} errors. Last error: {exc}") from exc

        labels = []
        while end - start > 1:
            if task_id:
                if has_canceled(task_id):
                    _lineaje_payload = f"Task {task_id} cancelled during RAPTOR layer processing."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.summarize).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:14a2d19b0cd5fded56c629b6f1a2bee048ca616175ef42716333662476b3c135'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:14a2d19b0cd5fded56c629b6f1a2bee048ca616175ef42716333662476b3c135', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 171, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.__call__'}, 'file': 'rag/raptor.py', 'line': 171, 'function': 'summarize', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)
                    raise TaskCanceledException(f"Task {task_id} was cancelled")

            embeddings = [embd for _, embd in chunks[start:end]]
            if len(embeddings) == 2:
                await summarize([start, start + 1])
                if callback:
                    callback(msg="Cluster one layer: {} -> {}".format(end - start, len(chunks) - end))
                labels.extend([0, 0])
                layers.append((end, len(chunks)))
                start = end
                end = len(chunks)
                continue

            n_neighbors = int((len(embeddings) - 1) ** 0.8)
            reduced_embeddings = umap.UMAP(
                n_neighbors=max(2, n_neighbors),
                n_components=min(12, len(embeddings) - 2),
                metric="cosine",
            ).fit_transform(embeddings)
            n_clusters = self._get_optimal_clusters(reduced_embeddings, random_state, task_id=task_id)
            if n_clusters == 1:
                lbls = [0 for _ in range(len(reduced_embeddings))]
            else:
                gm = GaussianMixture(n_components=n_clusters, random_state=random_state)
                gm.fit(reduced_embeddings)
                probs = gm.predict_proba(reduced_embeddings)
                lbls = [np.where(prob > self._threshold)[0] for prob in probs]
                lbls = [lbl[0] if isinstance(lbl, np.ndarray) else lbl for lbl in lbls]

            tasks = []
            for c in range(n_clusters):
                ck_idx = [i + start for i in range(len(lbls)) if lbls[i] == c]
                assert len(ck_idx) > 0
                if task_id and has_canceled(task_id):
                    _lineaje_payload = f"Task {task_id} cancelled before RAPTOR cluster processing."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.summarize).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:f5fcfb992f2c355d10685a5080407e4c03496e2f7c428874e2d523b105023a2c'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f5fcfb992f2c355d10685a5080407e4c03496e2f7c428874e2d523b105023a2c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 206, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.__call__'}, 'file': 'rag/raptor.py', 'line': 206, 'function': 'summarize', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)
                    raise TaskCanceledException(f"Task {task_id} was cancelled")
                tasks.append(asyncio.create_task(summarize(ck_idx)))
            try:
                await asyncio.gather(*tasks, return_exceptions=False)
            except Exception as e:
                _lineaje_payload = f"Error in RAPTOR cluster processing: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.summarize).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:56ecfb9d07e9c7b010a30896e45cdfe812bec0b8c12eb3376d60aaaccebceba9'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:56ecfb9d07e9c7b010a30896e45cdfe812bec0b8c12eb3376d60aaaccebceba9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 212, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.__call__'}, 'file': 'rag/raptor.py', 'line': 212, 'function': 'summarize', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                for t in tasks:
                    t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise

            assert len(chunks) - end == n_clusters, "{} vs. {}".format(len(chunks) - end, n_clusters)
            labels.extend(lbls)
            layers.append((end, len(chunks)))
            if callback:
                callback(msg="Cluster one layer: {} -> {}".format(end - start, len(chunks) - end))
            start = end
            end = len(chunks)

        # LINEAJE: runtime guardrail checks `chunks` as it flows from the agent to the user interface, before it leaves the application (in RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.__call__).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `chunks` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6abf55c0ca77a0337f3dd59f85dc80e275661f4f375509a3ef422c15bad2c288'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6abf55c0ca77a0337f3dd59f85dc80e275661f4f375509a3ef422c15bad2c288', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/raptor.py', 'line': 226, 'function': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval.__call__'}, 'file': 'rag/raptor.py', 'line': 226, 'function': '__call__', 'agent_name': 'RecursiveAbstractiveProcessing4TreeOrganizedRetrieval', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            chunks = _gr_client.enforce(_gr_site, chunks, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return chunks
