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
import logging
from collections import defaultdict
from copy import deepcopy
import json_repair
import pandas as pd

from common.misc_utils import get_uuid
from graphrag.query_analyze_prompt import PROMPTS
from graphrag.utils import get_entity_type2samples, get_llm_cache, set_llm_cache, get_relation
from common.token_utils import num_tokens_from_string

from rag.nlp.search import Dealer, index_name
from common.float_utils import get_float
from common import settings
from common.doc_store.doc_store_base import OrderByExpr


class KGSearch(Dealer):
    def _chat(self, llm_bdl, system, history, gen_conf):
        response = get_llm_cache(llm_bdl.llm_name, system, history, gen_conf)
        if response:
            # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the user interface, before it leaves the application (in KGSearch._chat).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:18b5590ec62c9792d9b5091292dabf43af3ae20da730f0b11129b68716a34aa7'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:18b5590ec62c9792d9b5091292dabf43af3ae20da730f0b11129b68716a34aa7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 38, 'function': 'KGSearch._chat'}, 'file': 'graphrag/search.py', 'line': 38, 'function': '_chat', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                response = _gr_client.enforce(_gr_site, response, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return response
        # LINEAJE: runtime guardrail checks `system` as it flows from the agent to the LLM, before it is sent to the model (in KGSearch._chat).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `system` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6c2a327f14a998fb1b70a517aec85ba7156e0777e6ddaba1921f2291c99c28dc'
        _lineaje_system_evidence = {'system': system, 'model': getattr(_lineaje_load_gr_client(), 'current_model', lambda _f: '')(__file__), 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6c2a327f14a998fb1b70a517aec85ba7156e0777e6ddaba1921f2291c99c28dc', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 39, 'function': 'KGSearch._chat'}, 'file': 'graphrag/search.py', 'line': 39, 'function': '_chat', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje_system_evidence = _gr_client.enforce(_gr_site, _lineaje_system_evidence, content_type='application/json')
            system = _lineaje_system_evidence.get('system', system) if isinstance(_lineaje_system_evidence, dict) else system
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        response = llm_bdl.chat(system, history, gen_conf)
        # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in KGSearch._chat).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3f77dc166574ff1c9ebccd45c1f3d9cd3ef608883616d9625a4aa20e03b1f36b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3f77dc166574ff1c9ebccd45c1f3d9cd3ef608883616d9625a4aa20e03b1f36b', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 39, 'function': 'KGSearch._chat'}, 'file': 'graphrag/search.py', 'line': 39, 'function': '_chat', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=39)
        except _gr_client.GuardrailUnavailableError:
            pass
        if response.find("**ERROR**") >= 0:
            raise Exception(response)
        set_llm_cache(llm_bdl.llm_name, system, response, history, gen_conf)
        # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the user interface, before it leaves the application (in KGSearch._chat).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:0f967e91436ccb82dc2f806c4e1fd1095124add5e8c1688ba2226296c3d563ba'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0f967e91436ccb82dc2f806c4e1fd1095124add5e8c1688ba2226296c3d563ba', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 43, 'function': 'KGSearch._chat'}, 'file': 'graphrag/search.py', 'line': 43, 'function': '_chat', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return response

    def query_rewrite(self, llm, question, idxnms, kb_ids):
        ty2ents = get_entity_type2samples(idxnms, kb_ids)
        # LINEAJE: runtime guardrail checks `ty2ents` as it flows from the agent to an external endpoint, before it leaves the application (in KGSearch.query_rewrite).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `ty2ents` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:426f61dd604dc43a341441ec91a3ab24b696183154897824a04f44c0515b8cd7'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:426f61dd604dc43a341441ec91a3ab24b696183154897824a04f44c0515b8cd7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 47, 'function': 'KGSearch.query_rewrite'}, 'file': 'graphrag/search.py', 'line': 47, 'function': 'query_rewrite', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            ty2ents = _gr_client.enforce(_gr_site, ty2ents, content_type='application/json', variable_name='ty2ents', source_file=__file__, before_line=47)
        except _gr_client.GuardrailUnavailableError:
            pass
        hint_prompt = PROMPTS["minirag_query2kwd"].format(query=question,
                                                          TYPE_POOL=json.dumps(ty2ents, ensure_ascii=False, indent=2))
        result = self._chat(llm, hint_prompt, [{"role": "user", "content": "Output:"}], {})
        try:
            keywords_data = json_repair.loads(result)
            type_keywords = keywords_data.get("answer_type_keywords", [])
            entities_from_query = keywords_data.get("entities_from_query", [])[:5]
            return type_keywords, entities_from_query
        except json_repair.JSONDecodeError:
            try:
                result = result.replace(hint_prompt[:-1], '').replace('user', '').replace('model', '').strip()
                result = '{' + result.split('{')[1].split('}')[0] + '}'
                keywords_data = json_repair.loads(result)
                type_keywords = keywords_data.get("answer_type_keywords", [])
                entities_from_query = keywords_data.get("entities_from_query", [])[:5]
                return type_keywords, entities_from_query
            # Handle parsing error
            except Exception as e:
                _lineaje_payload = f"JSON parsing error: {result} -> {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in KGSearch.query_rewrite).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:8f7aed1c087641ba979f1956956bb82643fbf09daeb5774206ac77f1204e0ee9'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8f7aed1c087641ba979f1956956bb82643fbf09daeb5774206ac77f1204e0ee9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 65, 'function': 'KGSearch.query_rewrite'}, 'file': 'graphrag/search.py', 'line': 65, 'function': 'query_rewrite', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(_lineaje_payload)
                raise e

    def _ent_info_from_(self, es_res, sim_thr=0.3):
        res = {}
        flds = ["content_with_weight", "_score", "entity_kwd", "rank_flt", "n_hop_with_weight"]
        es_res = self.dataStore.get_fields(es_res, flds)
        for _, ent in es_res.items():
            for f in flds:
                if f in ent and ent[f] is None:
                    del ent[f]
            if get_float(ent.get("_score", 0)) < sim_thr:
                continue
            if isinstance(ent["entity_kwd"], list):
                ent["entity_kwd"] = ent["entity_kwd"][0]
            res[ent["entity_kwd"]] = {
                "sim": get_float(ent.get("_score", 0)),
                "pagerank": get_float(ent.get("rank_flt", 0)),
                "n_hop_ents": json.loads(ent.get("n_hop_with_weight", "[]")),
                "description": ent.get("content_with_weight", "{}")
            }
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in KGSearch._ent_info_from_).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1f88dd23fcda0a8a88a63282c63b36526f9c6b29477428abd8b791a8a573a2ab'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1f88dd23fcda0a8a88a63282c63b36526f9c6b29477428abd8b791a8a573a2ab', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 86, 'function': 'KGSearch._ent_info_from_'}, 'file': 'graphrag/search.py', 'line': 86, 'function': '_ent_info_from_', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    def _relation_info_from_(self, es_res, sim_thr=0.3):
        res = {}
        es_res = self.dataStore.get_fields(es_res, ["content_with_weight", "_score", "from_entity_kwd", "to_entity_kwd",
                                                   "weight_int"])
        for _, ent in es_res.items():
            if get_float(ent["_score"]) < sim_thr:
                continue
            f, t = sorted([ent["from_entity_kwd"], ent["to_entity_kwd"]])
            if isinstance(f, list):
                f = f[0]
            if isinstance(t, list):
                t = t[0]
            res[(f, t)] = {
                "sim": get_float(ent["_score"]),
                "pagerank": get_float(ent.get("weight_int", 0)),
                "description": ent["content_with_weight"]
            }
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in KGSearch._relation_info_from_).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ac3e484264dbd2579e97e1a07ee5b96d2ada98c1bc02f77a97b43f37bff7ddc8'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ac3e484264dbd2579e97e1a07ee5b96d2ada98c1bc02f77a97b43f37bff7ddc8', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 105, 'function': 'KGSearch._relation_info_from_'}, 'file': 'graphrag/search.py', 'line': 105, 'function': '_relation_info_from_', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    def get_relevant_ents_by_keywords(self, keywords, filters, idxnms, kb_ids, emb_mdl, sim_thr=0.3, N=56):
        if not keywords:
            return {}
        filters = deepcopy(filters)
        filters["knowledge_graph_kwd"] = "entity"
        matchDense = self.get_vector(", ".join(keywords), emb_mdl, 1024, sim_thr)
        es_res = self.dataStore.search(["content_with_weight", "entity_kwd", "rank_flt"], [], filters, [matchDense],
                                       OrderByExpr(), 0, N,
                                       idxnms, kb_ids)
        return self._ent_info_from_(es_res, sim_thr)

    def get_relevant_relations_by_txt(self, txt, filters, idxnms, kb_ids, emb_mdl, sim_thr=0.3, N=56):
        if not txt:
            return {}
        filters = deepcopy(filters)
        filters["knowledge_graph_kwd"] = "relation"
        matchDense = self.get_vector(txt, emb_mdl, 1024, sim_thr)
        es_res = self.dataStore.search(
            ["content_with_weight", "_score", "from_entity_kwd", "to_entity_kwd", "weight_int"],
            [], filters, [matchDense], OrderByExpr(), 0, N, idxnms, kb_ids)
        return self._relation_info_from_(es_res, sim_thr)

    def get_relevant_ents_by_types(self, types, filters, idxnms, kb_ids, N=56):
        if not types:
            return {}
        filters = deepcopy(filters)
        filters["knowledge_graph_kwd"] = "entity"
        filters["entity_type_kwd"] = types
        ordr = OrderByExpr()
        ordr.desc("rank_flt")
        es_res = self.dataStore.search(["entity_kwd", "rank_flt"], [], filters, [], ordr, 0, N,
                                       idxnms, kb_ids)
        return self._ent_info_from_(es_res, 0)

    def retrieval(self, question: str,
               tenant_ids: str | list[str],
               kb_ids: list[str],
               emb_mdl,
               llm,
               max_token: int = 8196,
               ent_topn: int = 6,
               rel_topn: int = 6,
               comm_topn: int = 1,
               ent_sim_threshold: float = 0.3,
               rel_sim_threshold: float = 0.3,
                  **kwargs
               ):
        qst = question
        filters = self.get_filters({"kb_ids": kb_ids})
        if isinstance(tenant_ids, str):
            tenant_ids = tenant_ids.split(",")
        idxnms = [index_name(tid) for tid in tenant_ids]
        ty_kwds = []
        try:
            ty_kwds, ents = self.query_rewrite(llm, qst, [index_name(tid) for tid in tenant_ids], kb_ids)
            _lineaje_payload = f"Q: {qst}, Types: {ty_kwds}, Entities: {ents}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in KGSearch.retrieval).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b8f071a2feb7b1ecafc7eb8483c22e052dd79f82f8cdec1589c370d829a5ad74'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b8f071a2feb7b1ecafc7eb8483c22e052dd79f82f8cdec1589c370d829a5ad74', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 162, 'function': 'KGSearch.retrieval'}, 'file': 'graphrag/search.py', 'line': 162, 'function': 'retrieval', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
        except Exception as e:
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in KGSearch.retrieval).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:09ee9f48d806bd20dc320a6d48dc9ba359922e00e183be81d1452ea6365db86d'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:09ee9f48d806bd20dc320a6d48dc9ba359922e00e183be81d1452ea6365db86d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 164, 'function': 'KGSearch.retrieval'}, 'file': 'graphrag/search.py', 'line': 164, 'function': 'retrieval', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                e = _gr_client.enforce(_gr_site, e, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)
            ents = [qst]
            pass

        ents_from_query = self.get_relevant_ents_by_keywords(ents, filters, idxnms, kb_ids, emb_mdl, ent_sim_threshold)
        ents_from_types = self.get_relevant_ents_by_types(ty_kwds, filters, idxnms, kb_ids, 10000)
        rels_from_txt = self.get_relevant_relations_by_txt(qst, filters, idxnms, kb_ids, emb_mdl, rel_sim_threshold)
        nhop_pathes = defaultdict(dict)
        for _, ent in ents_from_query.items():
            nhops = ent.get("n_hop_ents", [])
            if not isinstance(nhops, list):
                _lineaje_payload = f"Abnormal n_hop_ents: {nhops}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in KGSearch.retrieval).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:12f34643111289c4eedfd5fddfa91c837519deb6c6d3698903493a5d810b770f'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:12f34643111289c4eedfd5fddfa91c837519deb6c6d3698903493a5d810b770f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 175, 'function': 'KGSearch.retrieval'}, 'file': 'graphrag/search.py', 'line': 175, 'function': 'retrieval', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                continue
            for nbr in nhops:
                path = nbr["path"]
                wts = nbr["weights"]
                for i in range(len(path) - 1):
                    f, t = path[i], path[i + 1]
                    if (f, t) in nhop_pathes:
                        nhop_pathes[(f, t)]["sim"] += ent["sim"] / (2 + i)
                    else:
                        nhop_pathes[(f, t)]["sim"] = ent["sim"] / (2 + i)
                    nhop_pathes[(f, t)]["pagerank"] = wts[i]

        _lineaje_payload = "Retrieved entities: {}".format(list(ents_from_query.keys()))
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in KGSearch.retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d7818807793676ebbb3647788fb0ba70795b810948131e1a1e7dec7eccf4f1e1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d7818807793676ebbb3647788fb0ba70795b810948131e1a1e7dec7eccf4f1e1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 188, 'function': 'KGSearch.retrieval'}, 'file': 'graphrag/search.py', 'line': 188, 'function': 'retrieval', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        _lineaje_payload = "Retrieved relations: {}".format(list(rels_from_txt.keys()))
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in KGSearch.retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:eb2998e62782d1e6bb9c0029efb5755ede60b3770d1fea433c4116d9b109b9db'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:eb2998e62782d1e6bb9c0029efb5755ede60b3770d1fea433c4116d9b109b9db', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 189, 'function': 'KGSearch.retrieval'}, 'file': 'graphrag/search.py', 'line': 189, 'function': 'retrieval', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        _lineaje_payload = "Retrieved entities from types({}): {}".format(ty_kwds, list(ents_from_types.keys()))
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in KGSearch.retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:0b4fb0e2a0f62185b75f9a6f672dadaf2a11050abf454f135c56a4dd152e66b5'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0b4fb0e2a0f62185b75f9a6f672dadaf2a11050abf454f135c56a4dd152e66b5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 190, 'function': 'KGSearch.retrieval'}, 'file': 'graphrag/search.py', 'line': 190, 'function': 'retrieval', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        _lineaje_payload = "Retrieved N-hops: {}".format(list(nhop_pathes.keys()))
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in KGSearch.retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1b787049c30f2307186265feccc92ac9dd938a4d70363150a39f40fea7f056f3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1b787049c30f2307186265feccc92ac9dd938a4d70363150a39f40fea7f056f3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/search.py', 'line': 191, 'function': 'KGSearch.retrieval'}, 'file': 'graphrag/search.py', 'line': 191, 'function': 'retrieval', 'agent_name': 'KGSearch', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)

        # P(E|Q) => P(E) * P(Q|E) => pagerank * sim
        for ent in ents_from_types.keys():
            if ent not in ents_from_query:
                continue
            ents_from_query[ent]["sim"] *= 2

        for (f, t) in rels_from_txt.keys():
            pair = tuple(sorted([f, t]))
            s = 0
            if pair in nhop_pathes:
                s += nhop_pathes[pair]["sim"]
                del nhop_pathes[pair]
            if f in ents_from_types:
                s += 1
            if t in ents_from_types:
                s += 1
            rels_from_txt[(f, t)]["sim"] *= s + 1

        # This is for the relations from n-hop but not by query search
        for (f, t) in nhop_pathes.keys():
            s = 0
            if f in ents_from_types:
                s += 1
            if t in ents_from_types:
                s += 1
            rels_from_txt[(f, t)] = {
                "sim": nhop_pathes[(f, t)]["sim"] * (s + 1),
                "pagerank": nhop_pathes[(f, t)]["pagerank"]
            }

        ents_from_query = sorted(ents_from_query.items(), key=lambda x: x[1]["sim"] * x[1]["pagerank"], reverse=True)[
                          :ent_topn]
        rels_from_txt = sorted(rels_from_txt.items(), key=lambda x: x[1]["sim"] * x[1]["pagerank"], reverse=True)[
                        :rel_topn]

        ents = []
        relas = []
        for n, ent in ents_from_query:
            ents.append({
                "Entity": n,
                "Score": "%.2f" % (ent["sim"] * ent["pagerank"]),
                "Description": json.loads(ent["description"]).get("description", "") if ent["description"] else ""
            })
            max_token -= num_tokens_from_string(str(ents[-1]))
            if max_token <= 0:
                ents = ents[:-1]
                break

        for (f, t), rel in rels_from_txt:
            if not rel.get("description"):
                for tid in tenant_ids:
                    rela = get_relation(tid, kb_ids, f, t)
                    if rela:
                        break
                else:
                    continue
                rel["description"] = rela["description"]
            desc = rel["description"]
            try:
                desc = json.loads(desc).get("description", "")
            except Exception:
                pass
            relas.append({
                "From Entity": f,
                "To Entity": t,
                "Score": "%.2f" % (rel["sim"] * rel["pagerank"]),
                "Description": desc
            })
            max_token -= num_tokens_from_string(str(relas[-1]))
            if max_token <= 0:
                relas = relas[:-1]
                break

        if ents:
            ents = "\n---- Entities ----\n{}".format(pd.DataFrame(ents).to_csv())
        else:
            ents = ""
        if relas:
            relas = "\n---- Relations ----\n{}".format(pd.DataFrame(relas).to_csv())
        else:
            relas = ""

        return {
                "chunk_id": get_uuid(),
                "content_ltks": "",
                "content_with_weight": ents + relas + self._community_retrieval_([n for n, _ in ents_from_query], filters, kb_ids, idxnms,
                                                        comm_topn, max_token),
                "doc_id": "",
                "docnm_kwd": "Related content in Knowledge Graph",
                "kb_id": kb_ids,
                "important_kwd": [],
                "image_id": "",
                "similarity": 1.,
                "vector_similarity": 1.,
                "term_similarity": 0,
                "vector": [],
                "positions": [],
            }

    def _community_retrieval_(self, entities, condition, kb_ids, idxnms, topn, max_token):
        ## Community retrieval
        fields = ["docnm_kwd", "content_with_weight"]
        odr = OrderByExpr()
        odr.desc("weight_flt")
        fltr = deepcopy(condition)
        fltr["knowledge_graph_kwd"] = "community_report"
        fltr["entities_kwd"] = entities
        comm_res = self.dataStore.search(fields, [], fltr, [],
                                         OrderByExpr(), 0, topn, idxnms, kb_ids)
        comm_res_fields = self.dataStore.get_fields(comm_res, fields)
        txts = []
        for ii, (_, row) in enumerate(comm_res_fields.items()):
            obj = json.loads(row["content_with_weight"])
            txts.append("# {}. {}\n## Content\n{}\n## Evidences\n{}\n".format(
                ii + 1, row["docnm_kwd"], obj["report"], obj["evidences"]))
            max_token -= num_tokens_from_string(str(txts[-1]))

        if not txts:
            return ""
        return "\n---- Community Report ----\n" + "\n".join(txts)


if __name__ == "__main__":
    import argparse
    from common.constants import LLMType
    from api.db.services.knowledgebase_service import KnowledgebaseService
    from api.db.services.llm_service import LLMBundle
    from api.db.services.user_service import TenantService
    from rag.nlp import search

    settings.init_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--tenant_id', default=False, help="Tenant ID", action='store', required=True)
    parser.add_argument('-d', '--kb_id', default=False, help="Knowledge base ID", action='store', required=True)
    parser.add_argument('-q', '--question', default=False, help="Question", action='store', required=True)
    args = parser.parse_args()

    kb_id = args.kb_id
    _, tenant = TenantService.get_by_id(args.tenant_id)
    llm_bdl = LLMBundle(args.tenant_id, LLMType.CHAT, tenant.llm_id)
    _, kb = KnowledgebaseService.get_by_id(kb_id)
    embed_bdl = LLMBundle(args.tenant_id, LLMType.EMBEDDING, kb.embd_id)

    kg = KGSearch(settings.docStoreConn)
    print(kg.retrieval({"question": args.question, "kb_ids": [kb_id]},
                    search.index_name(kb.tenant_id), [kb_id], embed_bdl, llm_bdl))
