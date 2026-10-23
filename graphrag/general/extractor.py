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
import asyncio
import logging
import os
import re
from collections import Counter, defaultdict
from copy import deepcopy
from typing import Callable

import networkx as nx

from api.db.services.task_service import has_canceled
from common.connection_utils import timeout
from common.token_utils import truncate
from graphrag.general.graph_prompt import SUMMARIZE_DESCRIPTIONS_PROMPT
from graphrag.utils import (
    GraphChange,
    chat_limiter,
    flat_uniq_list,
    get_from_to,
    get_llm_cache,
    handle_single_entity_extraction,
    handle_single_relationship_extraction,
    set_llm_cache,
    split_string_by_multi_markers,
)
from rag.llm.chat_model import Base as CompletionLLM
from rag.prompts.generator import message_fit_in
from common.exceptions import TaskCanceledException

GRAPH_FIELD_SEP = "<SEP>"
DEFAULT_ENTITY_TYPES = ["organization", "person", "geo", "event", "category"]
ENTITY_EXTRACTION_MAX_GLEANINGS = 2
MAX_CONCURRENT_PROCESS_AND_EXTRACT_CHUNK = int(os.environ.get("MAX_CONCURRENT_PROCESS_AND_EXTRACT_CHUNK", 10))


class Extractor:
    _llm: CompletionLLM

    def __init__(
        self,
        llm_invoker: CompletionLLM,
        language: str | None = "English",
        entity_types: list[str] | None = None,
    ):
        self._llm = llm_invoker
        self._language = language
        self._entity_types = entity_types or DEFAULT_ENTITY_TYPES

    @timeout(60 * 20)
    def _chat(self, system, history, gen_conf={}, task_id=""):
        hist = deepcopy(history)
        conf = deepcopy(gen_conf)
        response = get_llm_cache(self._llm.llm_name, system, hist, conf)
        if response:
            # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the user interface, before it leaves the application (in Extractor._chat).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:082a4982b3f6bb2531baccc85d3fc3fe247d36e0b271db02d34e3ef7f5164112'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:082a4982b3f6bb2531baccc85d3fc3fe247d36e0b271db02d34e3ef7f5164112', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 70, 'function': 'Extractor._chat'}, 'file': 'graphrag/general/extractor.py', 'line': 70, 'function': '_chat', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                response = _gr_client.enforce(_gr_site, response, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return response
        _, system_msg = message_fit_in([{"role": "system", "content": system}], int(self._llm.max_length * 0.92))
        response = ""
        for attempt in range(3):
            if task_id:
                if has_canceled(task_id):
                    _lineaje_payload = f"Task {task_id} cancelled during entity resolution candidate processing."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Extractor._chat).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:b7b6a5c06b763adeffc8d826fc7f0fb87f1c15404a36b2c331785a3c25382878'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b7b6a5c06b763adeffc8d826fc7f0fb87f1c15404a36b2c331785a3c25382878', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 76, 'function': 'Extractor._chat'}, 'file': 'graphrag/general/extractor.py', 'line': 76, 'function': '_chat', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)
                    raise TaskCanceledException(f"Task {task_id} was cancelled")
            try:
                response = asyncio.run(self._llm.async_chat(system_msg[0]["content"], hist, conf))
                response = re.sub(r"^.*</think>", "", response, flags=re.DOTALL)
                if response.find("**ERROR**") >= 0:
                    raise Exception(response)
                set_llm_cache(self._llm.llm_name, system, response, history, gen_conf)
                break
            except Exception as e:
                # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in Extractor._chat).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a6082a2974f8a94dfa2eea68d20464d00aecd4bbf0be0079e0171838bfb59035'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a6082a2974f8a94dfa2eea68d20464d00aecd4bbf0be0079e0171838bfb59035', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 86, 'function': 'Extractor._chat'}, 'file': 'graphrag/general/extractor.py', 'line': 86, 'function': '_chat', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    e = _gr_client.enforce(_gr_site, e, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(e)
                if attempt == 2:
                    raise

        # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the user interface, before it leaves the application (in Extractor._chat).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e7988fb44da1f09dd928377baa930060be5926faea13a77dd2782f0e9c9dff43'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e7988fb44da1f09dd928377baa930060be5926faea13a77dd2782f0e9c9dff43', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 90, 'function': 'Extractor._chat'}, 'file': 'graphrag/general/extractor.py', 'line': 90, 'function': '_chat', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return response

    def _entities_and_relations(self, chunk_key: str, records: list, tuple_delimiter: str):
        maybe_nodes = defaultdict(list)
        maybe_edges = defaultdict(list)
        ent_types = [t.lower() for t in self._entity_types]
        for record in records:
            record_attributes = split_string_by_multi_markers(record, [tuple_delimiter])

            if_entities = handle_single_entity_extraction(record_attributes, chunk_key)
            if if_entities is not None and if_entities.get("entity_type", "unknown").lower() in ent_types:
                maybe_nodes[if_entities["entity_name"]].append(if_entities)
                continue

            if_relation = handle_single_relationship_extraction(record_attributes, chunk_key)
            if if_relation is not None:
                maybe_edges[(if_relation["src_id"], if_relation["tgt_id"])].append(if_relation)
        return dict(maybe_nodes), dict(maybe_edges)

    async def __call__(self, doc_id: str, chunks: list[str], callback: Callable | None = None, task_id: str = ""):
        self.callback = callback
        start_ts = asyncio.get_running_loop().time()

        async def extract_all(doc_id, chunks, max_concurrency=MAX_CONCURRENT_PROCESS_AND_EXTRACT_CHUNK, task_id=""):
            out_results = []
            error_count = 0
            max_errors = int(os.environ.get("GRAPHRAG_MAX_ERRORS", 3))

            limiter = asyncio.Semaphore(max_concurrency)

            async def worker(chunk_key_dp: tuple[str, str], idx: int, total: int, task_id=""):
                nonlocal error_count
                async with limiter:

                    if task_id and has_canceled(task_id):
                        raise TaskCanceledException(f"Task {task_id} was cancelled during entity extraction")

                    try:
                        await self._process_single_content(chunk_key_dp, idx, total, out_results, task_id)
                    except Exception as e:
                        error_count += 1
                        error_msg = f"Error processing chunk {idx + 1}/{total}: {str(e)}"
                        # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in Extractor.worker).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:cd5413cad1115547533ebca100e85261c20aa01657a69f2866f795db0251a384'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cd5413cad1115547533ebca100e85261c20aa01657a69f2866f795db0251a384', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 132, 'function': 'Extractor.__call__.extract_all.worker'}, 'file': 'graphrag/general/extractor.py', 'line': 132, 'function': 'worker', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            error_msg = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, error_msg, content_type='application/json'))
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.warning(error_msg)
                        if self.callback:
                            self.callback(msg=error_msg)

                        if error_count > max_errors:
                            raise Exception(f"Maximum error count ({max_errors}) reached. Last errors: {str(e)}")

            tasks = [
                asyncio.create_task(worker((doc_id, ck), i, len(chunks), task_id))
                for i, ck in enumerate(chunks)
            ]

            try:
                await asyncio.gather(*tasks, return_exceptions=False)
            except Exception as e:
                _lineaje_payload = f"Error in worker: {str(e)}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Extractor.worker).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:3a25f39c1331f8f67b6acf451dfebb73826b7ea403f8556e08534da9e00a08b2'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3a25f39c1331f8f67b6acf451dfebb73826b7ea403f8556e08534da9e00a08b2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 147, 'function': 'Extractor.__call__.extract_all'}, 'file': 'graphrag/general/extractor.py', 'line': 147, 'function': 'worker', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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

            if error_count > 0:
                warning_msg = f"Completed with {error_count} errors (out of {len(chunks)} chunks processed)"
                # LINEAJE: runtime guardrail checks `warning_msg` as it flows from the agent to the application log, before it is written to the log (in Extractor.worker).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `warning_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:2976a890a64a16d7c6e95f56decb0dc01d44b3053245c0d13fc6c20fb2b1c083'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2976a890a64a16d7c6e95f56decb0dc01d44b3053245c0d13fc6c20fb2b1c083', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 155, 'function': 'Extractor.__call__.extract_all'}, 'file': 'graphrag/general/extractor.py', 'line': 155, 'function': 'worker', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    warning_msg = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, warning_msg, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(warning_msg)
                if self.callback:
                    self.callback(msg=warning_msg)

            # LINEAJE: runtime guardrail checks `out_results` as it flows from the agent to the user interface, before it leaves the application (in Extractor.extract_all).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `out_results` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d5821a1bb37e2137e6da47df33a657f79c3fef75af390ddbb2e4a97008f14803'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d5821a1bb37e2137e6da47df33a657f79c3fef75af390ddbb2e4a97008f14803', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 159, 'function': 'Extractor.__call__.extract_all'}, 'file': 'graphrag/general/extractor.py', 'line': 159, 'function': 'extract_all', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                out_results = _gr_client.enforce(_gr_site, out_results, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return out_results

        if task_id and has_canceled(task_id):
            raise TaskCanceledException(f"Task {task_id} was cancelled before entity extraction")

        out_results = await extract_all(doc_id, chunks, max_concurrency=MAX_CONCURRENT_PROCESS_AND_EXTRACT_CHUNK, task_id=task_id)

        if task_id and has_canceled(task_id):
            raise TaskCanceledException(f"Task {task_id} was cancelled after entity extraction")

        maybe_nodes = defaultdict(list)
        maybe_edges = defaultdict(list)
        sum_token_count = 0
        for m_nodes, m_edges, token_count in out_results:
            for k, v in m_nodes.items():
                maybe_nodes[k].extend(v)
            for k, v in m_edges.items():
                maybe_edges[tuple(sorted(k))].extend(v)
            sum_token_count += token_count
        now = asyncio.get_running_loop().time()
        if self.callback:
            self.callback(msg=f"Entities and relationships extraction done, {len(maybe_nodes)} nodes, {len(maybe_edges)} edges, {sum_token_count} tokens, {now - start_ts:.2f}s.")
        start_ts = now
        _lineaje_payload = "Entities merging..."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Extractor.__call__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:12fdf205657b1b493cfcc9b35dc06875de15ca53752267dc4f6eece02d4f4ac8'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:12fdf205657b1b493cfcc9b35dc06875de15ca53752267dc4f6eece02d4f4ac8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 182, 'function': 'Extractor.__call__'}, 'file': 'graphrag/general/extractor.py', 'line': 182, 'function': '__call__', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        all_entities_data = []

        if task_id and has_canceled(task_id):
            raise TaskCanceledException(f"Task {task_id} was cancelled before nodes merging")

        tasks = [
            asyncio.create_task(self._merge_nodes(en_nm, ents, all_entities_data, task_id))
            for en_nm, ents in maybe_nodes.items()
        ]
        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            _lineaje_payload = f"Error merging nodes: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Extractor.extract_all).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:09872da280d469309460e12aacddd10f1997db4698768a20ad2b96a5698a74eb'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:09872da280d469309460e12aacddd10f1997db4698768a20ad2b96a5698a74eb', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 195, 'function': 'Extractor.__call__'}, 'file': 'graphrag/general/extractor.py', 'line': 195, 'function': 'extract_all', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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

        if task_id and has_canceled(task_id):
            raise TaskCanceledException(f"Task {task_id} was cancelled after nodes merging")

        now = asyncio.get_running_loop().time()
        if self.callback:
            self.callback(msg=f"Entities merging done, {now - start_ts:.2f}s.")

        start_ts = now
        _lineaje_payload = "Relationships merging..."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Extractor.__call__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:66c1434a09a8a48366f03641b7103617b31dc7d284e3e8ac83ec70521ab57a7c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:66c1434a09a8a48366f03641b7103617b31dc7d284e3e8ac83ec70521ab57a7c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 209, 'function': 'Extractor.__call__'}, 'file': 'graphrag/general/extractor.py', 'line': 209, 'function': '__call__', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        all_relationships_data = []

        if task_id and has_canceled(task_id):
            raise TaskCanceledException(f"Task {task_id} was cancelled before relationships merging")

        tasks = []
        for (src, tgt), rels in maybe_edges.items():
            tasks.append(
                asyncio.create_task(
                    self._merge_edges(src, tgt, rels, all_relationships_data, task_id)
                )
            )
        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            _lineaje_payload = f"Error during relationships merging: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Extractor.extract_all).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0efbc701d0f457fec91c9882590f3f42facfa3065841c636f3c80837623500b5'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0efbc701d0f457fec91c9882590f3f42facfa3065841c636f3c80837623500b5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 225, 'function': 'Extractor.__call__'}, 'file': 'graphrag/general/extractor.py', 'line': 225, 'function': 'extract_all', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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

        if task_id and has_canceled(task_id):
            raise TaskCanceledException(f"Task {task_id} was cancelled after relationships merging")

        now = asyncio.get_running_loop().time()
        if self.callback:
            self.callback(msg=f"Relationships merging done, {now - start_ts:.2f}s.")

        if not len(all_entities_data) and not len(all_relationships_data):
            _lineaje_payload = "Didn't extract any entities and relationships, maybe your LLM is not working"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Extractor.extract_all).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:8fbf7643a11a32453281f70de24d85bc2c4d0c5eab96691c3931b4df8b8d98e2'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8fbf7643a11a32453281f70de24d85bc2c4d0c5eab96691c3931b4df8b8d98e2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 239, 'function': 'Extractor.__call__'}, 'file': 'graphrag/general/extractor.py', 'line': 239, 'function': 'extract_all', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)

        if not len(all_entities_data):
            _lineaje_payload = "Didn't extract any entities"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Extractor.extract_all).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ab2707d78ee3de02b03361d5afa0f6b56c45189ee53a28584152f44ea68896f8'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ab2707d78ee3de02b03361d5afa0f6b56c45189ee53a28584152f44ea68896f8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 242, 'function': 'Extractor.__call__'}, 'file': 'graphrag/general/extractor.py', 'line': 242, 'function': 'extract_all', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
        if not len(all_relationships_data):
            _lineaje_payload = "Didn't extract any relationships"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Extractor.extract_all).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:5c743cdd22f2569ff7b5988120a8418d51181004ff8c3484db994b3395cd0779'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5c743cdd22f2569ff7b5988120a8418d51181004ff8c3484db994b3395cd0779', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 244, 'function': 'Extractor.__call__'}, 'file': 'graphrag/general/extractor.py', 'line': 244, 'function': 'extract_all', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)

        return all_entities_data, all_relationships_data

    async def _merge_nodes(self, entity_name: str, entities: list[dict], all_relationships_data, task_id=""):
        if task_id and has_canceled(task_id):
            raise TaskCanceledException(f"Task {task_id} was cancelled during merge nodes")

        if not entities:
            return
        entity_type = sorted(
            Counter([dp["entity_type"] for dp in entities]).items(),
            key=lambda x: x[1],
            reverse=True,
        )[0][0]
        description = GRAPH_FIELD_SEP.join(sorted(set([dp["description"] for dp in entities])))
        already_source_ids = flat_uniq_list(entities, "source_id")
        description = await self._handle_entity_relation_summary(entity_name, description, task_id=task_id)
        node_data = dict(
            entity_type=entity_type,
            description=description,
            source_id=already_source_ids,
        )
        node_data["entity_name"] = entity_name
        all_relationships_data.append(node_data)

    async def _merge_edges(self, src_id: str, tgt_id: str, edges_data: list[dict], all_relationships_data=None, task_id=""):
        if not edges_data:
            return
        weight = sum([edge["weight"] for edge in edges_data])
        description = GRAPH_FIELD_SEP.join(sorted(set([edge["description"] for edge in edges_data])))
        description = await self._handle_entity_relation_summary(f"{src_id} -> {tgt_id}", description, task_id=task_id)
        keywords = flat_uniq_list(edges_data, "keywords")
        source_id = flat_uniq_list(edges_data, "source_id")
        edge_data = dict(src_id=src_id, tgt_id=tgt_id, description=description, keywords=keywords, weight=weight, source_id=source_id)
        all_relationships_data.append(edge_data)

    async def _merge_graph_nodes(self, graph: nx.Graph, nodes: list[str], change: GraphChange, task_id=""):
        if task_id and has_canceled(task_id):
            raise TaskCanceledException(f"Task {task_id} was cancelled during merge graph nodes")

        if len(nodes) <= 1:
            return
        change.added_updated_nodes.add(nodes[0])
        change.removed_nodes.update(nodes[1:])
        nodes_set = set(nodes)
        node0_attrs = graph.nodes[nodes[0]]
        node0_neighbors = set(graph.neighbors(nodes[0]))
        for node1 in nodes[1:]:
            if task_id and has_canceled(task_id):
                raise TaskCanceledException(f"Task {task_id} was cancelled during merge_graph nodes")

            # Merge two nodes, keep "entity_name", "entity_type", "page_rank" unchanged.
            node1_attrs = graph.nodes[node1]
            node0_attrs["description"] += f"{GRAPH_FIELD_SEP}{node1_attrs['description']}"
            node0_attrs["source_id"] = sorted(set(node0_attrs["source_id"] + node1_attrs["source_id"]))
            for neighbor in graph.neighbors(node1):
                change.removed_edges.add(get_from_to(node1, neighbor))
                if neighbor not in nodes_set:
                    edge1_attrs = graph.get_edge_data(node1, neighbor)
                    if neighbor in node0_neighbors:
                        # Merge two edges
                        change.added_updated_edges.add(get_from_to(nodes[0], neighbor))
                        edge0_attrs = graph.get_edge_data(nodes[0], neighbor)
                        edge0_attrs["weight"] += edge1_attrs["weight"]
                        edge0_attrs["description"] += f"{GRAPH_FIELD_SEP}{edge1_attrs['description']}"
                        for attr in ["keywords", "source_id"]:
                            edge0_attrs[attr] = sorted(set(edge0_attrs[attr] + edge1_attrs[attr]))
                        edge0_attrs["description"] = await self._handle_entity_relation_summary(f"({nodes[0]}, {neighbor})", edge0_attrs["description"], task_id=task_id)
                        graph.add_edge(nodes[0], neighbor, **edge0_attrs)
                    else:
                        graph.add_edge(nodes[0], neighbor, **edge1_attrs)
            graph.remove_node(node1)
        node0_attrs["description"] = await self._handle_entity_relation_summary(nodes[0], node0_attrs["description"], task_id=task_id)
        graph.nodes[nodes[0]].update(node0_attrs)

    async def _handle_entity_relation_summary(self, entity_or_relation_name: str, description: str, task_id="") -> str:
        if task_id and has_canceled(task_id):
            raise TaskCanceledException(f"Task {task_id} was cancelled during summary handling")

        summary_max_tokens = 512
        use_description = truncate(description, summary_max_tokens)
        description_list = use_description.split(GRAPH_FIELD_SEP)
        if len(description_list) <= 12:
            # LINEAJE: runtime guardrail checks `use_description` as it flows from the agent to the user interface, before it leaves the application (in Extractor._handle_entity_relation_summary).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `use_description` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0e818d1b8ca8cc90a9b535a4ea8ae942df6b92274ef5559386d0082399ae69c5'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0e818d1b8ca8cc90a9b535a4ea8ae942df6b92274ef5559386d0082399ae69c5', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 328, 'function': 'Extractor._handle_entity_relation_summary'}, 'file': 'graphrag/general/extractor.py', 'line': 328, 'function': '_handle_entity_relation_summary', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                use_description = _gr_client.enforce(_gr_site, use_description, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return use_description
        prompt_template = SUMMARIZE_DESCRIPTIONS_PROMPT
        context_base = dict(
            entity_name=entity_or_relation_name,
            description_list=description_list,
            language=self._language,
        )
        use_prompt = prompt_template.format(**context_base)
        _lineaje_payload = f"Trigger summary: {entity_or_relation_name}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Extractor._handle_entity_relation_summary).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:716797c1a008ca1c62ea8347317fdaaa6f7635a378f4b3c477464a55805659e2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:716797c1a008ca1c62ea8347317fdaaa6f7635a378f4b3c477464a55805659e2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 336, 'function': 'Extractor._handle_entity_relation_summary'}, 'file': 'graphrag/general/extractor.py', 'line': 336, 'function': '_handle_entity_relation_summary', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)

        if task_id and has_canceled(task_id):
            raise TaskCanceledException(f"Task {task_id} was cancelled during summary handling")

        async with chat_limiter:
            summary = await asyncio.to_thread(self._chat, "", [{"role": "user", "content": use_prompt}], {}, task_id)
        # LINEAJE: runtime guardrail checks `summary` as it flows from the agent to the user interface, before it leaves the application (in Extractor._handle_entity_relation_summary).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `summary` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ea4483484321407e6f008ee31744ee96f36aa2798d67d7c53225934b08cc6657'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ea4483484321407e6f008ee31744ee96f36aa2798d67d7c53225934b08cc6657', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/extractor.py', 'line': 343, 'function': 'Extractor._handle_entity_relation_summary'}, 'file': 'graphrag/general/extractor.py', 'line': 343, 'function': '_handle_entity_relation_summary', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            summary = _gr_client.enforce(_gr_site, summary, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return summary
