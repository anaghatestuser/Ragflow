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
import itertools
import os
import re
from dataclasses import dataclass
from typing import Any, Callable

import networkx as nx

from graphrag.general.extractor import Extractor
from rag.nlp import is_english
import editdistance
from graphrag.entity_resolution_prompt import ENTITY_RESOLUTION_PROMPT
from rag.llm.chat_model import Base as CompletionLLM
from graphrag.utils import perform_variable_replacements, chat_limiter, GraphChange
from api.db.services.task_service import has_canceled
from common.exceptions import TaskCanceledException

DEFAULT_RECORD_DELIMITER = "##"
DEFAULT_ENTITY_INDEX_DELIMITER = "<|>"
DEFAULT_RESOLUTION_RESULT_DELIMITER = "&&"


@dataclass
class EntityResolutionResult:
    """Entity resolution result class definition."""
    graph: nx.Graph
    change: GraphChange


class EntityResolution(Extractor):
    """Entity resolution class definition."""

    _resolution_prompt: str
    _output_formatter_prompt: str
    _record_delimiter_key: str
    _entity_index_delimiter_key: str
    _resolution_result_delimiter_key: str

    def __init__(
            self,
            llm_invoker: CompletionLLM,
    ):
        super().__init__(llm_invoker)
        """Init method definition."""
        self._llm = llm_invoker
        self._resolution_prompt = ENTITY_RESOLUTION_PROMPT
        self._record_delimiter_key = "record_delimiter"
        self._entity_index_delimiter_key = "entity_index_delimiter"
        self._resolution_result_delimiter_key = "resolution_result_delimiter"
        self._input_text_key = "input_text"

    async def __call__(self, graph: nx.Graph,
                       subgraph_nodes: set[str],
                       prompt_variables: dict[str, Any] | None = None,
                       callback: Callable | None = None,
                       task_id: str = "") -> EntityResolutionResult:
        """Call method definition."""
        if prompt_variables is None:
            prompt_variables = {}

        # Wire defaults into the prompt variables
        self.prompt_variables = {
            **prompt_variables,
            self._record_delimiter_key: prompt_variables.get(self._record_delimiter_key)
                                        or DEFAULT_RECORD_DELIMITER,
            self._entity_index_delimiter_key: prompt_variables.get(self._entity_index_delimiter_key)
                                              or DEFAULT_ENTITY_INDEX_DELIMITER,
            self._resolution_result_delimiter_key: prompt_variables.get(self._resolution_result_delimiter_key)
                                                   or DEFAULT_RESOLUTION_RESULT_DELIMITER,
        }

        nodes = sorted(graph.nodes())
        entity_types = sorted(set(graph.nodes[node].get('entity_type', '-') for node in nodes))
        node_clusters = {entity_type: [] for entity_type in entity_types}

        for node in nodes:
            node_clusters[graph.nodes[node].get('entity_type', '-')].append(node)

        candidate_resolution = {entity_type: [] for entity_type in entity_types}
        for k, v in node_clusters.items():
            candidate_resolution[k] = [(a, b) for a, b in itertools.combinations(v, 2) if (a in subgraph_nodes or b in subgraph_nodes) and self.is_similarity(a, b)]
        num_candidates = sum([len(candidates) for _, candidates in candidate_resolution.items()])
        callback(msg=f"Identified {num_candidates} candidate pairs")
        remain_candidates_to_resolve = num_candidates

        resolution_result = set()
        resolution_result_lock = asyncio.Lock()
        resolution_batch_size = 100
        max_concurrent_tasks = 5
        semaphore = asyncio.Semaphore(max_concurrent_tasks)

        async def limited_resolve_candidate(candidate_batch, result_set, result_lock):
            nonlocal remain_candidates_to_resolve, callback
            async with semaphore:
                try:
                    enable_timeout_assertion = os.environ.get("ENABLE_TIMEOUT_ASSERTION")
                    timeout_sec = 280 if enable_timeout_assertion else 1_000_000_000

                    try:
                        await asyncio.wait_for(
                            self._resolve_candidate(candidate_batch, result_set, result_lock, task_id),
                            timeout=timeout_sec
                        )
                        remain_candidates_to_resolve -= len(candidate_batch[1])
                        callback(
                            msg=f"Resolved {len(candidate_batch[1])} pairs, "
                                f"{remain_candidates_to_resolve} remain."
                        )

                    except asyncio.TimeoutError:
                        _lineaje_payload = f"Timeout resolving {candidate_batch}, skipping..."
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EntityResolution.limited_resolve_candidate).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:f99a87ba50a6ff0f7b6f6fe6699d7273c26c871607c984aa205e364a81999b07'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f99a87ba50a6ff0f7b6f6fe6699d7273c26c871607c984aa205e364a81999b07', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/entity_resolution.py', 'line': 128, 'function': 'EntityResolution.__call__.limited_resolve_candidate'}, 'file': 'graphrag/entity_resolution.py', 'line': 128, 'function': 'limited_resolve_candidate', 'agent_name': 'EntityResolution', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.warning(_lineaje_payload)
                        remain_candidates_to_resolve -= len(candidate_batch[1])
                        callback(
                            msg=f"Failed to resolve {len(candidate_batch[1])} pairs due to timeout, skipped. "
                                f"{remain_candidates_to_resolve} remain."
                        )

                except Exception as exception:
                    _lineaje_payload = f"Error resolving candidate batch: {exception}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EntityResolution.limited_resolve_candidate).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:60620721dd93a90ef74280d292f6c3f91a83109de6ce0a0eb4be7da22d21507b'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:60620721dd93a90ef74280d292f6c3f91a83109de6ce0a0eb4be7da22d21507b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/entity_resolution.py', 'line': 136, 'function': 'EntityResolution.__call__.limited_resolve_candidate'}, 'file': 'graphrag/entity_resolution.py', 'line': 136, 'function': 'limited_resolve_candidate', 'agent_name': 'EntityResolution', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.error(_lineaje_payload)


        tasks = []
        for key, lst in candidate_resolution.items():
            if not lst:
                continue
            for i in range(0, len(lst), resolution_batch_size):
                batch = (key, lst[i:i + resolution_batch_size])
                tasks.append(limited_resolve_candidate(batch, resolution_result, resolution_result_lock))
        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            _lineaje_payload = f"Error resolving candidate pairs: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EntityResolution.limited_resolve_candidate).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:095bce583e5c0b3829da21b4407c55f122eaacf76bbff29e7158b1a2f12df78e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:095bce583e5c0b3829da21b4407c55f122eaacf76bbff29e7158b1a2f12df78e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/entity_resolution.py', 'line': 149, 'function': 'EntityResolution.__call__'}, 'file': 'graphrag/entity_resolution.py', 'line': 149, 'function': 'limited_resolve_candidate', 'agent_name': 'EntityResolution', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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

        callback(msg=f"Resolved {num_candidates} candidate pairs, {len(resolution_result)} of them are selected to merge.")

        change = GraphChange()
        connect_graph = nx.Graph()
        connect_graph.add_edges_from(resolution_result)

        async def limited_merge_nodes(graph, nodes, change):
            async with semaphore:
                await self._merge_graph_nodes(graph, nodes, change, task_id)

        tasks = []
        for sub_connect_graph in nx.connected_components(connect_graph):
            merging_nodes = list(sub_connect_graph)
            tasks.append(asyncio.create_task(limited_merge_nodes(graph, merging_nodes, change))
            )
        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            _lineaje_payload = f"Error merging nodes: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EntityResolution.limited_merge_nodes).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:349e15ccf710bd70ad19c7e34033552880098f9bc386cd5f06b81f96f0078ed1'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:349e15ccf710bd70ad19c7e34033552880098f9bc386cd5f06b81f96f0078ed1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/entity_resolution.py', 'line': 173, 'function': 'EntityResolution.__call__'}, 'file': 'graphrag/entity_resolution.py', 'line': 173, 'function': 'limited_merge_nodes', 'agent_name': 'EntityResolution', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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

        # Update pagerank
        pr = nx.pagerank(graph)
        for node_name, pagerank in pr.items():
            graph.nodes[node_name]["pagerank"] = pagerank

        return EntityResolutionResult(
            graph=graph,
            change=change,
        )

    async def _resolve_candidate(self, candidate_resolution_i: tuple[str, list[tuple[str, str]]], resolution_result: set[str], resolution_result_lock: asyncio.Lock, task_id: str = ""):
        if task_id:
            if has_canceled(task_id):
                _lineaje_payload = f"Task {task_id} cancelled during entity resolution candidate processing."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EntityResolution._resolve_candidate).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:3a8b55d5c503edcec11b8734adf33dad3f95e8af9cdea7acbbf2fed3197b8d16'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3a8b55d5c503edcec11b8734adf33dad3f95e8af9cdea7acbbf2fed3197b8d16', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/entity_resolution.py', 'line': 192, 'function': 'EntityResolution._resolve_candidate'}, 'file': 'graphrag/entity_resolution.py', 'line': 192, 'function': '_resolve_candidate', 'agent_name': 'EntityResolution', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                raise TaskCanceledException(f"Task {task_id} was cancelled")

        pair_txt = [
            f'When determining whether two {candidate_resolution_i[0]}s are the same, you should only focus on critical properties and overlook noisy factors.\n']
        for index, candidate in enumerate(candidate_resolution_i[1]):
            pair_txt.append(
                f'Question {index + 1}: name of{candidate_resolution_i[0]} A is {candidate[0]} ,name of{candidate_resolution_i[0]} B is {candidate[1]}')
        sent = 'question above' if len(pair_txt) == 1 else f'above {len(pair_txt)} questions'
        pair_txt.append(
            f'\nUse domain knowledge of {candidate_resolution_i[0]}s to help understand the text and answer the {sent} in the format: For Question i, Yes, {candidate_resolution_i[0]} A and {candidate_resolution_i[0]} B are the same {candidate_resolution_i[0]}./No, {candidate_resolution_i[0]} A and {candidate_resolution_i[0]} B are different {candidate_resolution_i[0]}s. For Question i+1, (repeat the above procedures)')
        pair_prompt = '\n'.join(pair_txt)
        variables = {
            **self.prompt_variables,
            self._input_text_key: pair_prompt
        }
        text = perform_variable_replacements(self._resolution_prompt, variables=variables)
        _lineaje_payload = f"Created resolution prompt {len(text)} bytes for {len(candidate_resolution_i[1])} entity pairs of type {candidate_resolution_i[0]}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EntityResolution._resolve_candidate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d7882b568b81419baaafa470233133708b36c0495c6cb4b076213d4bcdf1721c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d7882b568b81419baaafa470233133708b36c0495c6cb4b076213d4bcdf1721c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/entity_resolution.py', 'line': 209, 'function': 'EntityResolution._resolve_candidate'}, 'file': 'graphrag/entity_resolution.py', 'line': 209, 'function': '_resolve_candidate', 'agent_name': 'EntityResolution', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        async with chat_limiter:
            timeout_seconds = 280 if os.environ.get("ENABLE_TIMEOUT_ASSERTION") else 1000000000
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._chat,
                        text,
                        [{"role": "user", "content": "Output:"}],
                        {},
                        task_id
                    ),
                    timeout=timeout_seconds,
                )

            except asyncio.TimeoutError:
                _lineaje_payload = "_resolve_candidate._chat timeout, skipping..."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EntityResolution._resolve_candidate).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:fe3399213d938d16c5366050f2f815f3c9db27f8991c86e127bdc72ca785983e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fe3399213d938d16c5366050f2f815f3c9db27f8991c86e127bdc72ca785983e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/entity_resolution.py', 'line': 225, 'function': 'EntityResolution._resolve_candidate'}, 'file': 'graphrag/entity_resolution.py', 'line': 225, 'function': '_resolve_candidate', 'agent_name': 'EntityResolution', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                return
            except Exception as e:
                _lineaje_payload = f"_resolve_candidate._chat failed: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EntityResolution._resolve_candidate).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a9b80da79b54725a1ef5d7a3cd07ba1e4594e6dc4fc25fce4fd0c3ca50b1f8e9'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a9b80da79b54725a1ef5d7a3cd07ba1e4594e6dc4fc25fce4fd0c3ca50b1f8e9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/entity_resolution.py', 'line': 228, 'function': 'EntityResolution._resolve_candidate'}, 'file': 'graphrag/entity_resolution.py', 'line': 228, 'function': '_resolve_candidate', 'agent_name': 'EntityResolution', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                return

        _lineaje_payload = f"_resolve_candidate chat prompt: {text}\nchat response: {response}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EntityResolution._resolve_candidate).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9770ff6fe214e556d418dfa097f1dd93ee62717762f1c8d1fbc9001170daf3ce'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9770ff6fe214e556d418dfa097f1dd93ee62717762f1c8d1fbc9001170daf3ce', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/entity_resolution.py', 'line': 231, 'function': 'EntityResolution._resolve_candidate'}, 'file': 'graphrag/entity_resolution.py', 'line': 231, 'function': '_resolve_candidate', 'agent_name': 'EntityResolution', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)
        result = self._process_results(len(candidate_resolution_i[1]), response,
                                       self.prompt_variables.get(self._record_delimiter_key,
                                                            DEFAULT_RECORD_DELIMITER),
                                       self.prompt_variables.get(self._entity_index_delimiter_key,
                                                            DEFAULT_ENTITY_INDEX_DELIMITER),
                                       self.prompt_variables.get(self._resolution_result_delimiter_key,
                                                            DEFAULT_RESOLUTION_RESULT_DELIMITER))
        async with resolution_result_lock:
            for result_i in result:
                resolution_result.add(candidate_resolution_i[1][result_i[0] - 1])

    def _process_results(
            self,
            records_length: int,
            results: str,
            record_delimiter: str,
            entity_index_delimiter: str,
            resolution_result_delimiter: str
    ) -> list:
        ans_list = []
        records = [r.strip() for r in results.split(record_delimiter)]
        for record in records:
            pattern_int = fr"{re.escape(entity_index_delimiter)}(\d+){re.escape(entity_index_delimiter)}"
            match_int = re.search(pattern_int, record)
            res_int = int(str(match_int.group(1) if match_int else '0'))
            if res_int > records_length:
                continue

            pattern_bool = f"{re.escape(resolution_result_delimiter)}([a-zA-Z]+){re.escape(resolution_result_delimiter)}"
            match_bool = re.search(pattern_bool, record)
            res_bool = str(match_bool.group(1) if match_bool else '')

            if res_int and res_bool:
                if res_bool.lower() == 'yes':
                    ans_list.append((res_int, "yes"))

        # LINEAJE: runtime guardrail checks `ans_list` as it flows from the agent to the user interface, before it leaves the application (in EntityResolution._process_results).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `ans_list` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9e0c83fc68a4d15db03cfc594001b664855b32877e3a743b2d0ad81846eb2022'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9e0c83fc68a4d15db03cfc594001b664855b32877e3a743b2d0ad81846eb2022', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/entity_resolution.py', 'line': 268, 'function': 'EntityResolution._process_results'}, 'file': 'graphrag/entity_resolution.py', 'line': 268, 'function': '_process_results', 'agent_name': 'EntityResolution', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            ans_list = _gr_client.enforce(_gr_site, ans_list, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return ans_list

    def _has_digit_in_2gram_diff(self, a, b):
        def to_2gram_set(s):
            return {s[i:i+2] for i in range(len(s) - 1)}

        set_a = to_2gram_set(a)
        set_b = to_2gram_set(b)
        diff = set_a ^ set_b

        return any(any(c.isdigit() for c in pair) for pair in diff)

    def is_similarity(self, a, b):
        if self._has_digit_in_2gram_diff(a, b):
            return False

        if is_english(a) and is_english(b):
            # LINEAJE: runtime guardrail checks `a` as it flows from the agent to system, at a security decision (in EntityResolution.is_similarity).
            #   Detected: this statement moves data from the agent to system with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_029; sensitive values in `a` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:8eb79982ba156a711572b6352cf27cd3bbefa862a2aaa185fd549a677ff56d55'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8eb79982ba156a711572b6352cf27cd3bbefa862a2aaa185fd549a677ff56d55', phase='security_decision', boundary={'source': 'agent_message', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='agent', destination_type='system', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/entity_resolution.py', 'line': 285, 'function': 'EntityResolution.is_similarity'}, 'file': 'graphrag/entity_resolution.py', 'line': 285, 'function': 'is_similarity', 'agent_name': 'EntityResolution', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                a = _gr_client.enforce(_gr_site, a, content_type='application/json', variable_name='a', source_file=__file__, before_line=285)
            except _gr_client.GuardrailUnavailableError:
                pass
            if editdistance.eval(a, b) <= min(len(a), len(b)) // 2:
                return True
            return False

        a, b = set(a), set(b)
        max_l = max(len(a), len(b))
        if max_l < 4:
            return len(a & b) > 1

        return len(a & b)*1./max_l >= 0.8

