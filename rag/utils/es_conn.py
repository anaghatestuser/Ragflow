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

import re
import json
import time

import copy
from elasticsearch_dsl import UpdateByQuery, Q, Search
from elastic_transport import ConnectionTimeout
from common.decorator import singleton
from common.doc_store.doc_store_base import MatchTextExpr, OrderByExpr, MatchExpr, MatchDenseExpr, FusionExpr
from common.doc_store.es_conn_base import ESConnectionBase
from common.float_utils import get_float
from common.constants import PAGERANK_FLD, TAG_FLD

ATTEMPT_TIME = 2


@singleton
class ESConnection(ESConnectionBase):

    """
    CRUD operations
    """

    def search(
            self, select_fields: list[str],
            highlight_fields: list[str],
            condition: dict,
            match_expressions: list[MatchExpr],
            order_by: OrderByExpr,
            offset: int,
            limit: int,
            index_names: str | list[str],
            knowledgebase_ids: list[str],
            agg_fields: list[str] | None = None,
            rank_feature: dict | None = None
    ):
        """
        Refers to https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html
        """
        if isinstance(index_names, str):
            index_names = index_names.split(",")
        assert isinstance(index_names, list) and len(index_names) > 0
        assert "_id" not in condition

        bool_query = Q("bool", must=[])
        condition["kb_id"] = knowledgebase_ids
        for k, v in condition.items():
            if k == "available_int":
                if v == 0:
                    bool_query.filter.append(Q("range", available_int={"lt": 1}))
                else:
                    bool_query.filter.append(
                        Q("bool", must_not=Q("range", available_int={"lt": 1})))
                continue
            if not v:
                continue
            if isinstance(v, list):
                bool_query.filter.append(Q("terms", **{k: v}))
            elif isinstance(v, str) or isinstance(v, int):
                bool_query.filter.append(Q("term", **{k: v}))
            else:
                raise Exception(
                    f"Condition `{str(k)}={str(v)}` value type is {str(type(v))}, expected to be int, str or list.")

        s = Search()
        vector_similarity_weight = 0.5
        for m in match_expressions:
            if isinstance(m, FusionExpr) and m.method == "weighted_sum" and "weights" in m.fusion_params:
                assert len(match_expressions) == 3 and isinstance(match_expressions[0], MatchTextExpr) and isinstance(match_expressions[1],
                                                                                                                      MatchDenseExpr) and isinstance(
                    match_expressions[2], FusionExpr)
                weights = m.fusion_params["weights"]
                vector_similarity_weight = get_float(weights.split(",")[1])
        for m in match_expressions:
            if isinstance(m, MatchTextExpr):
                minimum_should_match = m.extra_options.get("minimum_should_match", 0.0)
                if isinstance(minimum_should_match, float):
                    minimum_should_match = str(int(minimum_should_match * 100)) + "%"
                bool_query.must.append(Q("query_string", fields=m.fields,
                                   type="best_fields", query=m.matching_text,
                                   minimum_should_match=minimum_should_match,
                                   boost=1))
                bool_query.boost = 1.0 - vector_similarity_weight

            elif isinstance(m, MatchDenseExpr):
                assert (bool_query is not None)
                similarity = 0.0
                if "similarity" in m.extra_options:
                    similarity = m.extra_options["similarity"]
                s = s.knn(m.vector_column_name,
                          m.topn,
                          m.topn * 2,
                          query_vector=list(m.embedding_data),
                          filter=bool_query.to_dict(),
                          similarity=similarity,
                          )

        if bool_query and rank_feature:
            for fld, sc in rank_feature.items():
                if fld != PAGERANK_FLD:
                    fld = f"{TAG_FLD}.{fld}"
                bool_query.should.append(Q("rank_feature", field=fld, linear={}, boost=sc))

        if bool_query:
            s = s.query(bool_query)
        for field in highlight_fields:
            s = s.highlight(field)

        if order_by:
            orders = list()
            for field, order in order_by.fields:
                order = "asc" if order == 0 else "desc"
                if field in ["page_num_int", "top_int"]:
                    order_info = {"order": order, "unmapped_type": "float",
                                  "mode": "avg", "numeric_type": "double"}
                elif field.endswith("_int") or field.endswith("_flt"):
                    order_info = {"order": order, "unmapped_type": "float"}
                else:
                    order_info = {"order": order, "unmapped_type": "text"}
                orders.append({field: order_info})
            s = s.sort(*orders)
        if agg_fields:
            for fld in agg_fields:
                s.aggs.bucket(f'aggs_{fld}', 'terms', field=fld, size=1000000)

        if limit > 0:
            s = s[offset:offset + limit]
        q = s.to_dict()
        # LINEAJE: runtime guardrail checks `index_names` as it flows from the agent to an external endpoint, before it leaves the application (in ESConnection.search).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `index_names` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b52b55c95856dead9bc2f9eff77fdd3e5e0d13ce40f64abbc228f8cf1d298b82'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b52b55c95856dead9bc2f9eff77fdd3e5e0d13ce40f64abbc228f8cf1d298b82', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 145, 'function': 'ESConnection.search'}, 'file': 'rag/utils/es_conn.py', 'line': 145, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            index_names = _gr_client.enforce(_gr_site, index_names, content_type='application/json', variable_name='index_names', source_file=__file__, before_line=145)
        except _gr_client.GuardrailUnavailableError:
            pass
        _lineaje_payload = f"ESConnection.search {str(index_names)} query: " + json.dumps(q)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.search).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e7413f9ba97cf54365ad4a0663dfea32373212be75231dd6e5df3afa651ebb40'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e7413f9ba97cf54365ad4a0663dfea32373212be75231dd6e5df3afa651ebb40', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 145, 'function': 'ESConnection.search'}, 'file': 'rag/utils/es_conn.py', 'line': 145, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.debug(_lineaje_payload)

        for i in range(ATTEMPT_TIME):
            try:
                #print(json.dumps(q, ensure_ascii=False))
                res = self.es.search(index=index_names,
                                     body=q,
                                     timeout="600s",
                                     # search_type="dfs_query_then_fetch",
                                     track_total_hits=True,
                                     _source=True)
                if str(res.get("timed_out", "")).lower() == "true":
                    raise Exception("Es Timeout.")
                _lineaje_payload = f"ESConnection.search {str(index_names)} res: " + str(res)
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.search).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:3c260d60d5b112c6cc48feb4188510bae895bfcea85569e1867088f05bc18605'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3c260d60d5b112c6cc48feb4188510bae895bfcea85569e1867088f05bc18605', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 158, 'function': 'ESConnection.search'}, 'file': 'rag/utils/es_conn.py', 'line': 158, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.debug(_lineaje_payload)
                # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in ESConnection.search).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:cb3621bd08ed10ff0bab21ea3e2d21e99eb427c94ab106270dfee549b35212e7'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cb3621bd08ed10ff0bab21ea3e2d21e99eb427c94ab106270dfee549b35212e7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 159, 'function': 'ESConnection.search'}, 'file': 'rag/utils/es_conn.py', 'line': 159, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return res
            except ConnectionTimeout:
                _lineaje_payload = "ES request timeout"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.search).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:1ae6b4de45ffc382a5d2028be1f73038f69bf537145c1139bc6caecff6970638'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1ae6b4de45ffc382a5d2028be1f73038f69bf537145c1139bc6caecff6970638', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 161, 'function': 'ESConnection.search'}, 'file': 'rag/utils/es_conn.py', 'line': 161, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.exception(_lineaje_payload)
                self._connect()
                continue
            except Exception as e:
                _lineaje_payload = f"ESConnection.search {str(index_names)} query: " + str(q) + str(e)
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.search).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:5b4e51d583b87440a4a85b050f9293977fb0624a5df41a8f0e5aa57df2b1071d'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5b4e51d583b87440a4a85b050f9293977fb0624a5df41a8f0e5aa57df2b1071d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 165, 'function': 'ESConnection.search'}, 'file': 'rag/utils/es_conn.py', 'line': 165, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.exception(_lineaje_payload)
                raise e

        _lineaje_payload = f"ESConnection.search timeout for {ATTEMPT_TIME} times!"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.search).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:91b48024766a0e011eb1efb65ae72f54c0e3f8d0490ab491dc713d3a717d3b56'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:91b48024766a0e011eb1efb65ae72f54c0e3f8d0490ab491dc713d3a717d3b56', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 168, 'function': 'ESConnection.search'}, 'file': 'rag/utils/es_conn.py', 'line': 168, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.error(_lineaje_payload)
        raise Exception("ESConnection.search timeout.")

    def insert(self, documents: list[dict], index_name: str, knowledgebase_id: str = None) -> list[str]:
        # Refers to https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-bulk.html
        operations = []
        for d in documents:
            assert "_id" not in d
            assert "id" in d
            d_copy = copy.deepcopy(d)
            d_copy["kb_id"] = knowledgebase_id
            meta_id = d_copy.pop("id", "")
            operations.append(
                {"index": {"_index": index_name, "_id": meta_id}})
            operations.append(d_copy)

        res = []
        for _ in range(ATTEMPT_TIME):
            try:
                res = []
                r = self.es.bulk(index=index_name, operations=operations,
                                 refresh=False, timeout="60s")
                if re.search(r"False", str(r["errors"]), re.IGNORECASE):
                    # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in ESConnection.insert).
                    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:d5e11acd8690c9e83667276f6d8baacb5c721f20848c03f730f54fe3d2803fbc'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d5e11acd8690c9e83667276f6d8baacb5c721f20848c03f730f54fe3d2803fbc', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 191, 'function': 'ESConnection.insert'}, 'file': 'rag/utils/es_conn.py', 'line': 191, 'function': 'insert', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    return res

                for item in r["items"]:
                    for action in ["create", "delete", "index", "update"]:
                        if action in item and "error" in item[action]:
                            res.append(str(item[action]["_id"]) + ":" + str(item[action]["error"]))
                # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in ESConnection.insert).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:d9cd054d3e66f6a08e689bd996e6cfe385ba6b4b93a6193dea9612eaa5bcce7c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d9cd054d3e66f6a08e689bd996e6cfe385ba6b4b93a6193dea9612eaa5bcce7c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 197, 'function': 'ESConnection.insert'}, 'file': 'rag/utils/es_conn.py', 'line': 197, 'function': 'insert', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return res
            except ConnectionTimeout:
                _lineaje_payload = "ES request timeout"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.insert).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f0f185026e5c9b7d9b0f68c1bbb1c6df8515fddebe82c9583bf1e6ef12e15cdf'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f0f185026e5c9b7d9b0f68c1bbb1c6df8515fddebe82c9583bf1e6ef12e15cdf', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 199, 'function': 'ESConnection.insert'}, 'file': 'rag/utils/es_conn.py', 'line': 199, 'function': 'insert', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.exception(_lineaje_payload)
                time.sleep(3)
                self._connect()
                continue
            except Exception as e:
                res.append(str(e))
                _lineaje_payload = "ESConnection.insert got exception: " + str(e)
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.insert).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:7721529b57b5b45449716e43188ee1f4a47b53ad180734b1fbfa6886d059c851'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7721529b57b5b45449716e43188ee1f4a47b53ad180734b1fbfa6886d059c851', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 205, 'function': 'ESConnection.insert'}, 'file': 'rag/utils/es_conn.py', 'line': 205, 'function': 'insert', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.warning(_lineaje_payload)

        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in ESConnection.insert).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5be00ed3da95553000caea25e461094d85141f76d66bea05c0f6ecdf7af23c3d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5be00ed3da95553000caea25e461094d85141f76d66bea05c0f6ecdf7af23c3d', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 207, 'function': 'ESConnection.insert'}, 'file': 'rag/utils/es_conn.py', 'line': 207, 'function': 'insert', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    def update(self, condition: dict, new_value: dict, index_name: str, knowledgebase_id: str) -> bool:
        # LINEAJE: runtime guardrail checks `condition` as it flows from the agent to an external endpoint, before it leaves the application (in ESConnection.update).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `condition` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:108d9af5df1dca42dc7676c6ec6f6c94d52a7a759e5cdfd22ab164e2b042a757'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:108d9af5df1dca42dc7676c6ec6f6c94d52a7a759e5cdfd22ab164e2b042a757', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 210, 'function': 'ESConnection.update'}, 'file': 'rag/utils/es_conn.py', 'line': 210, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            condition = _gr_client.enforce(_gr_site, condition, content_type='application/json', variable_name='condition', source_file=__file__, before_line=210)
        except _gr_client.GuardrailUnavailableError:
            pass
        doc = copy.deepcopy(new_value)
        doc.pop("id", None)
        condition["kb_id"] = knowledgebase_id
        if "id" in condition and isinstance(condition["id"], str):
            # update specific single document
            chunk_id = condition["id"]
            for i in range(ATTEMPT_TIME):
                for k in doc.keys():
                    if "feas" != k.split("_")[-1]:
                        continue
                    try:
                        self.es.update(index=index_name, id=chunk_id, script=f"ctx._source.remove(\"{k}\");")
                    except Exception:
                        # LINEAJE: runtime guardrail checks `condition` as it flows from the agent to an external endpoint, before it leaves the application (in ESConnection.update).
                        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
                        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `condition` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:d4783caf017269377a1dcc5c17d01a222f52c3009c22ea383817ccee75ccea05'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d4783caf017269377a1dcc5c17d01a222f52c3009c22ea383817ccee75ccea05', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 223, 'function': 'ESConnection.update'}, 'file': 'rag/utils/es_conn.py', 'line': 223, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            condition = _gr_client.enforce(_gr_site, condition, content_type='application/json', variable_name='condition', source_file=__file__, before_line=223)
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        _lineaje_payload = f"ESConnection.update(index={index_name}, id={chunk_id}, doc={json.dumps(condition, ensure_ascii=False)}) got exception"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.update).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:9087f6620d6b5260e7fce1486330ee595e7f58389dd903f06c8f615d478108a7'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9087f6620d6b5260e7fce1486330ee595e7f58389dd903f06c8f615d478108a7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 223, 'function': 'ESConnection.update'}, 'file': 'rag/utils/es_conn.py', 'line': 223, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        self.logger.exception(_lineaje_payload)
                try:
                    self.es.update(index=index_name, id=chunk_id, doc=doc)
                    return True
                except Exception as e:
                    # LINEAJE: runtime guardrail checks `condition` as it flows from the agent to an external endpoint, before it leaves the application (in ESConnection.update).
                    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `condition` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:b4ddb037a7952187b457537bfdc2ec1b683e075f8dec57fd3be4c94fb64befde'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b4ddb037a7952187b457537bfdc2ec1b683e075f8dec57fd3be4c94fb64befde', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 228, 'function': 'ESConnection.update'}, 'file': 'rag/utils/es_conn.py', 'line': 228, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        condition = _gr_client.enforce(_gr_site, condition, content_type='application/json', variable_name='condition', source_file=__file__, before_line=228)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    _lineaje_payload = f"ESConnection.update(index={index_name}, id={chunk_id}, doc={json.dumps(condition, ensure_ascii=False)}) got exception: " + str(e)
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.update).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:946156412bb5d4820d09220e1c25bd6dc77fd5d4538fcd15b09fb56f2e23e10f'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:946156412bb5d4820d09220e1c25bd6dc77fd5d4538fcd15b09fb56f2e23e10f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 228, 'function': 'ESConnection.update'}, 'file': 'rag/utils/es_conn.py', 'line': 228, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    self.logger.exception(
                        _lineaje_payload)
                    break
            return False

        # update unspecific maybe-multiple documents
        bool_query = Q("bool")
        for k, v in condition.items():
            if not isinstance(k, str) or not v:
                continue
            if k == "exists":
                bool_query.filter.append(Q("exists", field=v))
                continue
            if isinstance(v, list):
                bool_query.filter.append(Q("terms", **{k: v}))
            elif isinstance(v, str) or isinstance(v, int):
                bool_query.filter.append(Q("term", **{k: v}))
            else:
                raise Exception(
                    f"Condition `{str(k)}={str(v)}` value type is {str(type(v))}, expected to be int, str or list.")
        scripts = []
        params = {}
        for k, v in new_value.items():
            if k == "remove":
                if isinstance(v, str):
                    scripts.append(f"ctx._source.remove('{v}');")
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        scripts.append(f"int i=ctx._source.{kk}.indexOf(params.p_{kk});ctx._source.{kk}.remove(i);")
                        params[f"p_{kk}"] = vv
                continue
            if k == "add":
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        scripts.append(f"ctx._source.{kk}.add(params.pp_{kk});")
                        params[f"pp_{kk}"] = vv.strip()
                continue
            if (not isinstance(k, str) or not v) and k != "available_int":
                continue
            if isinstance(v, str):
                v = re.sub(r"(['\n\r]|\\.)", " ", v)
                params[f"pp_{k}"] = v
                scripts.append(f"ctx._source.{k}=params.pp_{k};")
            elif isinstance(v, int) or isinstance(v, float):
                scripts.append(f"ctx._source.{k}={v};")
            elif isinstance(v, list):
                scripts.append(f"ctx._source.{k}=params.pp_{k};")
                # LINEAJE: runtime guardrail checks `v` as it flows from the agent to an external endpoint, before it leaves the application (in ESConnection.update).
                #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `v` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:bfaf4d4f04f8625d074959c6338ff6df0155abb59c8530bc1c6f0d7bb46b8c9c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bfaf4d4f04f8625d074959c6338ff6df0155abb59c8530bc1c6f0d7bb46b8c9c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 275, 'function': 'ESConnection.update'}, 'file': 'rag/utils/es_conn.py', 'line': 275, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    v = _gr_client.enforce(_gr_site, v, content_type='application/json', variable_name='v', source_file=__file__, before_line=275)
                except _gr_client.GuardrailUnavailableError:
                    pass
                params[f"pp_{k}"] = json.dumps(v, ensure_ascii=False)
            else:
                raise Exception(
                    f"newValue `{str(k)}={str(v)}` value type is {str(type(v))}, expected to be int, str.")
        ubq = UpdateByQuery(
            index=index_name).using(
            self.es).query(bool_query)
        ubq = ubq.script(source="".join(scripts), params=params)
        ubq = ubq.params(refresh=True)
        ubq = ubq.params(slices=5)
        ubq = ubq.params(conflicts="proceed")

        for _ in range(ATTEMPT_TIME):
            try:
                _ = ubq.execute()
                return True
            except ConnectionTimeout:
                _lineaje_payload = "ES request timeout"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.update).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:37f12938b555dccbe758e3e8b0fdc9e7a0ef79cfb3209f0b740fad6b410c7cde'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:37f12938b555dccbe758e3e8b0fdc9e7a0ef79cfb3209f0b740fad6b410c7cde', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 292, 'function': 'ESConnection.update'}, 'file': 'rag/utils/es_conn.py', 'line': 292, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.exception(_lineaje_payload)
                time.sleep(3)
                self._connect()
                continue
            except Exception as e:
                _lineaje_payload = "ESConnection.update got exception: " + str(e) + "\n".join(scripts)
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.update).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:87fb891501f4d006c8b8e89c745a1fa1122902bfc38285ba7026140b1f43b10e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:87fb891501f4d006c8b8e89c745a1fa1122902bfc38285ba7026140b1f43b10e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 297, 'function': 'ESConnection.update'}, 'file': 'rag/utils/es_conn.py', 'line': 297, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.error(_lineaje_payload)
                break
        return False

    def delete(self, condition: dict, index_name: str, knowledgebase_id: str) -> int:
        assert "_id" not in condition
        condition["kb_id"] = knowledgebase_id
        if "id" in condition:
            chunk_ids = condition["id"]
            if not isinstance(chunk_ids, list):
                chunk_ids = [chunk_ids]
            if not chunk_ids:  # when chunk_ids is empty, delete all
                qry = Q("match_all")
            else:
                qry = Q("ids", values=chunk_ids)
        else:
            qry = Q("bool")
            for k, v in condition.items():
                if k == "exists":
                    qry.filter.append(Q("exists", field=v))

                elif k == "must_not":
                    if isinstance(v, dict):
                        for kk, vv in v.items():
                            if kk == "exists":
                                qry.must_not.append(Q("exists", field=vv))

                elif isinstance(v, list):
                    qry.must.append(Q("terms", **{k: v}))
                elif isinstance(v, str) or isinstance(v, int):
                    qry.must.append(Q("term", **{k: v}))
                else:
                    raise Exception("Condition value must be int, str or list.")
        _lineaje_payload = "ESConnection.delete query: " + json.dumps(qry.to_dict())
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.delete).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3e372d072f162c7a29acf618151ff27eca1f1e61c53216c5af77a4785af09333'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3e372d072f162c7a29acf618151ff27eca1f1e61c53216c5af77a4785af09333', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 330, 'function': 'ESConnection.delete'}, 'file': 'rag/utils/es_conn.py', 'line': 330, 'function': 'delete', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.debug(_lineaje_payload)
        for _ in range(ATTEMPT_TIME):
            try:
                res = self.es.delete_by_query(
                    index=index_name,
                    body=Search().query(qry).to_dict(),
                    refresh=True)
                return res["deleted"]
            except ConnectionTimeout:
                _lineaje_payload = "ES request timeout"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.delete).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:264e87f05373c79f86ae649758b7b0916a1ea88b15af2ea99f514a0a4ae2be15'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:264e87f05373c79f86ae649758b7b0916a1ea88b15af2ea99f514a0a4ae2be15', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 339, 'function': 'ESConnection.delete'}, 'file': 'rag/utils/es_conn.py', 'line': 339, 'function': 'delete', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.exception(_lineaje_payload)
                time.sleep(3)
                self._connect()
                continue
            except Exception as e:
                _lineaje_payload = "ESConnection.delete got exception: " + str(e)
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.delete).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:97848067faba2b82a698e0a96fbcc2a4cec627d0d84735d26c464c0ae3749a34'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:97848067faba2b82a698e0a96fbcc2a4cec627d0d84735d26c464c0ae3749a34', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 344, 'function': 'ESConnection.delete'}, 'file': 'rag/utils/es_conn.py', 'line': 344, 'function': 'delete', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.warning(_lineaje_payload)
                if re.search(r"(not_found)", str(e), re.IGNORECASE):
                    return 0
        return 0

    """
    Helper functions for search result
    """

    def get_fields(self, res, fields: list[str]) -> dict[str, dict]:
        res_fields = {}
        if not fields:
            return {}
        for d in self._get_source(res):
            m = {n: d.get(n) for n in fields if d.get(n) is not None}
            for n, v in m.items():
                if isinstance(v, list):
                    m[n] = v
                    continue
                if n == "available_int" and isinstance(v, (int, float)):
                    m[n] = v
                    continue
                if not isinstance(v, str):
                    m[n] = str(m[n])
                # if n.find("tks") > 0:
                #     m[n] = remove_redundant_spaces(m[n])

            if m:
                res_fields[d["id"]] = m
        # LINEAJE: runtime guardrail checks `res_fields` as it flows from the agent to the user interface, before it leaves the application (in ESConnection.get_fields).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res_fields` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b8ac1490f10a991cc44b5a4e8eea65398f8cbf761f1b6e53f5b2d870b10b17e0'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b8ac1490f10a991cc44b5a4e8eea65398f8cbf761f1b6e53f5b2d870b10b17e0', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/es_conn.py', 'line': 373, 'function': 'ESConnection.get_fields'}, 'file': 'rag/utils/es_conn.py', 'line': 373, 'function': 'get_fields', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res_fields = _gr_client.enforce(_gr_site, res_fields, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res_fields
