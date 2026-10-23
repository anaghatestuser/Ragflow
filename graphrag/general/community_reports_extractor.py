# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License
"""
Reference:
 - [graphrag](https://github.com/microsoft/graphrag)
"""
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


import asyncio
import logging
import json
import os
import re
from typing import Callable
from dataclasses import dataclass
import networkx as nx
import pandas as pd

from api.db.services.task_service import has_canceled
from common.exceptions import TaskCanceledException
from common.connection_utils import timeout
from graphrag.general import leiden
from graphrag.general.community_report_prompt import COMMUNITY_REPORT_PROMPT
from graphrag.general.extractor import Extractor
from graphrag.general.leiden import add_community_info2graph
from rag.llm.chat_model import Base as CompletionLLM
from graphrag.utils import perform_variable_replacements, dict_has_keys_with_types, chat_limiter
from common.token_utils import num_tokens_from_string


@dataclass
class CommunityReportsResult:
    """Community reports result class definition."""

    output: list[str]
    structured_output: list[dict]


class CommunityReportsExtractor(Extractor):
    """Community reports extractor class definition."""

    _extraction_prompt: str
    _output_formatter_prompt: str
    _max_report_length: int

    def __init__(
            self,
            llm_invoker: CompletionLLM,
            max_report_length: int | None = None,
    ):
        super().__init__(llm_invoker)
        """Init method definition."""
        self._llm = llm_invoker
        self._extraction_prompt = COMMUNITY_REPORT_PROMPT
        self._max_report_length = max_report_length or 1500

    async def __call__(self, graph: nx.Graph, callback: Callable | None = None, task_id: str = ""):
        enable_timeout_assertion = os.environ.get("ENABLE_TIMEOUT_ASSERTION")
        for node_degree in graph.degree:
            graph.nodes[str(node_degree[0])]["rank"] = int(node_degree[1])

        communities: dict[str, dict[str, list]] = leiden.run(graph, {})
        total = sum([len(comm.items()) for _, comm in communities.items()])
        res_str = []
        res_dict = []
        over, token_count = 0, 0
        @timeout(120)
        async def extract_community_report(community):
            nonlocal res_str, res_dict, over, token_count
            if task_id:
                if has_canceled(task_id):
                    _lineaje_payload = f"Task {task_id} cancelled during community report extraction."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CommunityReportsExtractor.extract_community_report).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:a6a18d23290c4ee875696aab1b3bc1b7897c0cc9fb8e3f914f1de91e426a959e'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a6a18d23290c4ee875696aab1b3bc1b7897c0cc9fb8e3f914f1de91e426a959e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/community_reports_extractor.py', 'line': 71, 'function': 'CommunityReportsExtractor.__call__.extract_community_report'}, 'file': 'graphrag/general/community_reports_extractor.py', 'line': 71, 'function': 'extract_community_report', 'agent_name': 'CommunityReportsExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)
                    raise TaskCanceledException(f"Task {task_id} was cancelled")

            cm_id, cm = community
            weight = cm["weight"]
            ents = cm["nodes"]
            if len(ents) < 2:
                return
            ent_list = [{"entity": ent, "description": graph.nodes[ent]["description"]} for ent in ents]
            ent_df = pd.DataFrame(ent_list)

            rela_list = []
            k = 0
            for i in range(0, len(ents)):
                if k >= 10000:
                    break
                for j in range(i + 1, len(ents)):
                    if k >= 10000:
                        break
                    edge = graph.get_edge_data(ents[i], ents[j])
                    if edge is None:
                        continue
                    rela_list.append({"source": ents[i], "target": ents[j], "description": edge["description"]})
                    k += 1
            rela_df = pd.DataFrame(rela_list)

            prompt_variables = {
                "entity_df": ent_df.to_csv(index_label="id"),
                "relation_df": rela_df.to_csv(index_label="id")
            }
            text = perform_variable_replacements(self._extraction_prompt, variables=prompt_variables)
            async with chat_limiter:
                try:
                    timeout = 180 if enable_timeout_assertion else 1000000000
                    response = await asyncio.wait_for(asyncio.to_thread(self._chat,text,[{"role": "user", "content": "Output:"}],{},task_id),timeout=timeout)
                except asyncio.TimeoutError:
                    _lineaje_payload = "extract_community_report._chat timeout, skipping..."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CommunityReportsExtractor.extract_community_report).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:d2bddc3945ac448ae4ae58f76143d7ca77eee3556b8520ae7846e4c97c355fa9'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d2bddc3945ac448ae4ae58f76143d7ca77eee3556b8520ae7846e4c97c355fa9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/community_reports_extractor.py', 'line': 107, 'function': 'CommunityReportsExtractor.__call__.extract_community_report'}, 'file': 'graphrag/general/community_reports_extractor.py', 'line': 107, 'function': 'extract_community_report', 'agent_name': 'CommunityReportsExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.warning(_lineaje_payload)
                    return
                except Exception as e:
                    _lineaje_payload = f"extract_community_report._chat failed: {e}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CommunityReportsExtractor.extract_community_report).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:c3069bf8952c32e69c8822ae67c42188012b78b94fbd9183e60206a1c45b3b25'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c3069bf8952c32e69c8822ae67c42188012b78b94fbd9183e60206a1c45b3b25', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/community_reports_extractor.py', 'line': 110, 'function': 'CommunityReportsExtractor.__call__.extract_community_report'}, 'file': 'graphrag/general/community_reports_extractor.py', 'line': 110, 'function': 'extract_community_report', 'agent_name': 'CommunityReportsExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.error(_lineaje_payload)
                    return
            token_count += num_tokens_from_string(text + response)
            response = re.sub(r"^[^\{]*", "", response)
            response = re.sub(r"[^\}]*$", "", response)
            response = re.sub(r"\{\{", "{", response)
            response = re.sub(r"\}\}", "}", response)
            # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the application log, before it is written to the log (in CommunityReportsExtractor.extract_community_report).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1b30466dd581a55b69abe690ebf511c00f0cf8fc8c66faba32051b71eade1a34'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1b30466dd581a55b69abe690ebf511c00f0cf8fc8c66faba32051b71eade1a34', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/community_reports_extractor.py', 'line': 117, 'function': 'CommunityReportsExtractor.__call__.extract_community_report'}, 'file': 'graphrag/general/community_reports_extractor.py', 'line': 117, 'function': 'extract_community_report', 'agent_name': 'CommunityReportsExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, response, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.debug(response)
            try:
                response = json.loads(response)
            except json.JSONDecodeError as e:
                _lineaje_payload = f"Failed to parse JSON response: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CommunityReportsExtractor.extract_community_report).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f269cd1c613de0dd492ae0e6cb694c50d8920807f876a658335abcbc03734e7c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f269cd1c613de0dd492ae0e6cb694c50d8920807f876a658335abcbc03734e7c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/community_reports_extractor.py', 'line': 121, 'function': 'CommunityReportsExtractor.__call__.extract_community_report'}, 'file': 'graphrag/general/community_reports_extractor.py', 'line': 121, 'function': 'extract_community_report', 'agent_name': 'CommunityReportsExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                _lineaje_payload = f"Response content: {response}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CommunityReportsExtractor.extract_community_report).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:409cf06f0686076e1548428a6ab545335f391afe0e0d292657eaa912fd4448ec'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:409cf06f0686076e1548428a6ab545335f391afe0e0d292657eaa912fd4448ec', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/community_reports_extractor.py', 'line': 122, 'function': 'CommunityReportsExtractor.__call__.extract_community_report'}, 'file': 'graphrag/general/community_reports_extractor.py', 'line': 122, 'function': 'extract_community_report', 'agent_name': 'CommunityReportsExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                return
            if not dict_has_keys_with_types(response, [
                        ("title", str),
                        ("summary", str),
                        ("findings", list),
                        ("rating", float),
                        ("rating_explanation", str),
                    ]):
                return
            response["weight"] = weight
            response["entities"] = ents
            add_community_info2graph(graph, ents, response["title"])
            res_str.append(self._get_text_output(response))
            res_dict.append(response)
            over += 1
            if callback:
                callback(msg=f"Communities: {over}/{total}, used tokens: {token_count}")

        st = asyncio.get_running_loop().time()
        tasks = []
        for level, comm in communities.items():
            _lineaje_payload = f"Level {level}: Community: {len(comm.keys())}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CommunityReportsExtractor.extract_community_report).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1dc95000483c659604add94fd03c8fe6241527aba8af3c7ad9d9db21f4c39b36'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1dc95000483c659604add94fd03c8fe6241527aba8af3c7ad9d9db21f4c39b36', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/community_reports_extractor.py', 'line': 144, 'function': 'CommunityReportsExtractor.__call__'}, 'file': 'graphrag/general/community_reports_extractor.py', 'line': 144, 'function': 'extract_community_report', 'agent_name': 'CommunityReportsExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            for community in comm.items():
                if task_id and has_canceled(task_id):
                    _lineaje_payload = f"Task {task_id} cancelled before community processing."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CommunityReportsExtractor.extract_community_report).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:869bd17451270d2501edc061a17c9b06b302d2a2c3d5e0901c3c191d0e3a569e'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:869bd17451270d2501edc061a17c9b06b302d2a2c3d5e0901c3c191d0e3a569e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/community_reports_extractor.py', 'line': 147, 'function': 'CommunityReportsExtractor.__call__'}, 'file': 'graphrag/general/community_reports_extractor.py', 'line': 147, 'function': 'extract_community_report', 'agent_name': 'CommunityReportsExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)
                    raise TaskCanceledException(f"Task {task_id} was cancelled")
                tasks.append(asyncio.create_task(extract_community_report(community)))
        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            _lineaje_payload = f"Error in community processing: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CommunityReportsExtractor.extract_community_report).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:65adb0e9eebd75754fa591b22c613eea73212754abe9a37a2015fb04295cbd01'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:65adb0e9eebd75754fa591b22c613eea73212754abe9a37a2015fb04295cbd01', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/community_reports_extractor.py', 'line': 153, 'function': 'CommunityReportsExtractor.__call__'}, 'file': 'graphrag/general/community_reports_extractor.py', 'line': 153, 'function': 'extract_community_report', 'agent_name': 'CommunityReportsExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
        if callback:
            callback(msg=f"Community reports done in {asyncio.get_running_loop().time() - st:.2f}s, used tokens: {token_count}")

        return CommunityReportsResult(
            structured_output=res_dict,
            output=res_str,
        )

    def _get_text_output(self, parsed_output: dict) -> str:
        title = parsed_output.get("title", "Report")
        summary = parsed_output.get("summary", "")
        findings = parsed_output.get("findings", [])

        def finding_summary(finding: dict):
            if isinstance(finding, str):
                # LINEAJE: runtime guardrail checks `finding` as it flows from the agent to the user interface, before it leaves the application (in CommunityReportsExtractor.finding_summary).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `finding` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:92b81b03cd92c99eda1702e5bfc413f8011ec390a0be684eda67dee243b7601c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:92b81b03cd92c99eda1702e5bfc413f8011ec390a0be684eda67dee243b7601c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/community_reports_extractor.py', 'line': 173, 'function': 'CommunityReportsExtractor._get_text_output.finding_summary'}, 'file': 'graphrag/general/community_reports_extractor.py', 'line': 173, 'function': 'finding_summary', 'agent_name': 'CommunityReportsExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    finding = _gr_client.enforce(_gr_site, finding, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return finding
            return finding.get("summary")

        def finding_explanation(finding: dict):
            if isinstance(finding, str):
                return ""
            return finding.get("explanation")

        report_sections = "\n\n".join(
            f"## {finding_summary(f)}\n\n{finding_explanation(f)}" for f in findings
        )
        return f"# {title}\n\n{summary}\n\n{report_sections}"
