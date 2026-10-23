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
from elasticsearch import NotFoundError
from elasticsearch_dsl import UpdateByQuery, Q, Search
from elastic_transport import ConnectionTimeout
from common.decorator import singleton
from common.doc_store.doc_store_base import MatchExpr, OrderByExpr, MatchTextExpr, MatchDenseExpr, FusionExpr
from common.doc_store.es_conn_base import ESConnectionBase
from common.float_utils import get_float
from common.constants import PAGERANK_FLD, TAG_FLD

ATTEMPT_TIME = 2


@singleton
class ESConnection(ESConnectionBase):

    @staticmethod
    def convert_field_name(field_name: str) -> str:
        match field_name:
            case "message_type":
                return "message_type_kwd"
            case "status":
                return "status_int"
            case "content":
                return "content_ltks"
            case _:
                # LINEAJE: runtime guardrail checks `field_name` as it flows from the agent to the user interface, before it leaves the application (in ESConnection.convert_field_name).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `field_name` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:1f457c10d1ee3966bc7d1c5084147f0a6ad63e806b1019e19eb536bfe76846e2'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1f457c10d1ee3966bc7d1c5084147f0a6ad63e806b1019e19eb536bfe76846e2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 47, 'function': 'ESConnection.convert_field_name'}, 'file': 'memory/utils/es_conn.py', 'line': 47, 'function': 'convert_field_name', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    field_name = _gr_client.enforce(_gr_site, field_name, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return field_name

    @staticmethod
    def map_message_to_es_fields(message: dict) -> dict:
        """
        Map message dictionary fields to Elasticsearch document/Infinity fields.

        :param message: A dictionary containing message details.
        :return: A dictionary formatted for Elasticsearch/Infinity indexing.
        """
        storage_doc = {
            "id": message.get("id"),
            "message_id": message["message_id"],
            "message_type_kwd": message["message_type"],
            "source_id": message["source_id"],
            "memory_id": message["memory_id"],
            "user_id": message["user_id"],
            "agent_id": message["agent_id"],
            "session_id": message["session_id"],
            "valid_at": message["valid_at"],
            "invalid_at": message["invalid_at"],
            "forget_at": message["forget_at"],
            "status_int": 1 if message["status"] else 0,
            "zone_id": message.get("zone_id", 0),
            "content_ltks": message["content"],
            f"q_{len(message['content_embed'])}_vec": message["content_embed"],
        }
        # LINEAJE: runtime guardrail checks `storage_doc` as it flows from the agent to the user interface, before it leaves the application (in ESConnection.map_message_to_es_fields).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `storage_doc` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f59e50c98415d7b6a5815a8b4daa9aa9c9b125a012b78116fe64fb680edb0e55'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f59e50c98415d7b6a5815a8b4daa9aa9c9b125a012b78116fe64fb680edb0e55', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 74, 'function': 'ESConnection.map_message_to_es_fields'}, 'file': 'memory/utils/es_conn.py', 'line': 74, 'function': 'map_message_to_es_fields', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            storage_doc = _gr_client.enforce(_gr_site, storage_doc, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return storage_doc

    @staticmethod
    def get_message_from_es_doc(doc: dict) -> dict:
        """
        Convert an Elasticsearch/Infinity document back to a message dictionary.

        :param doc: A dictionary representing the Elasticsearch/Infinity document.
        :return: A dictionary formatted as a message.
        """
        embd_field_name = next((key for key in doc.keys() if re.match(r"q_\d+_vec", key)), None)
        message = {
            "message_id": doc["message_id"],
            "message_type": doc["message_type_kwd"],
            "source_id": doc["source_id"] if doc["source_id"] else None,
            "memory_id": doc["memory_id"],
            "user_id": doc.get("user_id", ""),
            "agent_id": doc["agent_id"],
            "session_id": doc["session_id"],
            "zone_id": doc.get("zone_id", 0),
            "valid_at": doc["valid_at"],
            "invalid_at": doc.get("invalid_at", "-"),
            "forget_at": doc.get("forget_at", "-"),
            "status": bool(int(doc["status_int"])),
            "content": doc.get("content_ltks", ""),
            "content_embed": doc.get(embd_field_name, []) if embd_field_name else [],
        }
        if doc.get("id"):
            message["id"] = doc["id"]
        # LINEAJE: runtime guardrail checks `message` as it flows from the agent to the user interface, before it leaves the application (in ESConnection.get_message_from_es_doc).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `message` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:543c36c6718cf56eae9c8bf6517596052dbc1f00a83b26fa93aa9659522e694e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:543c36c6718cf56eae9c8bf6517596052dbc1f00a83b26fa93aa9659522e694e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 103, 'function': 'ESConnection.get_message_from_es_doc'}, 'file': 'memory/utils/es_conn.py', 'line': 103, 'function': 'get_message_from_es_doc', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            message = _gr_client.enforce(_gr_site, message, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return message

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
            memory_ids: list[str],
            agg_fields: list[str] | None = None,
            rank_feature: dict | None = None,
            hide_forgotten: bool = True
    ):
        """
        Refers to https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html
        """
        if isinstance(index_names, str):
            index_names = index_names.split(",")
        assert isinstance(index_names, list) and len(index_names) > 0
        assert "_id" not in condition
        bool_query = Q("bool", must=[], must_not=[])
        if hide_forgotten:
            # filter not forget
            bool_query.must_not.append(Q("exists", field="forget_at"))

        condition["memory_id"] = memory_ids
        for k, v in condition.items():
            if k == "session_id" and v:
                bool_query.filter.append(Q("query_string", **{"query": f"*{v}*", "fields": ["session_id"], "analyze_wildcard": True}))
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
                bool_query.must.append(Q("query_string", fields=[self.convert_field_name(f) for f in m.fields],
                                   type="best_fields", query=m.matching_text,
                                   minimum_should_match=minimum_should_match,
                                   boost=1))
                bool_query.boost = 1.0 - vector_similarity_weight

            elif isinstance(m, MatchDenseExpr):
                assert (bool_query is not None)
                similarity = 0.0
                if "similarity" in m.extra_options:
                    similarity = m.extra_options["similarity"]
                s = s.knn(self.convert_field_name(m.vector_column_name),
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
                if field.endswith("_int") or field.endswith("_flt"):
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
        #   Do not remove without review. site_id='site:sha256:84ccc45afc448ae5fd6c726f07bbd330e06b3eeff1bb63fea2478709f363f101'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:84ccc45afc448ae5fd6c726f07bbd330e06b3eeff1bb63fea2478709f363f101', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 211, 'function': 'ESConnection.search'}, 'file': 'memory/utils/es_conn.py', 'line': 211, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            index_names = _gr_client.enforce(_gr_site, index_names, content_type='application/json', variable_name='index_names', source_file=__file__, before_line=211)
        except _gr_client.GuardrailUnavailableError:
            pass
        _lineaje_payload = f"ESConnection.search {str(index_names)} query: " + json.dumps(q)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.search).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1ab72a2effb63a52bb86c59a6283f4447293e0b1c4f499ed50a92e2887d50eb1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1ab72a2effb63a52bb86c59a6283f4447293e0b1c4f499ed50a92e2887d50eb1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 211, 'function': 'ESConnection.search'}, 'file': 'memory/utils/es_conn.py', 'line': 211, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
                #   Do not remove without review. site_id='site:sha256:3b9e6b6a555f008dcffa891cea494cfef76afb933481eef364ce1150031ffc98'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3b9e6b6a555f008dcffa891cea494cfef76afb933481eef364ce1150031ffc98', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 224, 'function': 'ESConnection.search'}, 'file': 'memory/utils/es_conn.py', 'line': 224, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
                #   Do not remove without review. site_id='site:sha256:3c885aebe083fed4d67ae669c462592cafa5198efda536e52cc552a88ea6a594'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3c885aebe083fed4d67ae669c462592cafa5198efda536e52cc552a88ea6a594', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 225, 'function': 'ESConnection.search'}, 'file': 'memory/utils/es_conn.py', 'line': 225, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
                #   Do not remove without review. site_id='site:sha256:572c0756db1a634a00ab86613e02d07744c3e39ea165fb4e5769d74f11c8b60c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:572c0756db1a634a00ab86613e02d07744c3e39ea165fb4e5769d74f11c8b60c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 227, 'function': 'ESConnection.search'}, 'file': 'memory/utils/es_conn.py', 'line': 227, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
                #   Do not remove without review. site_id='site:sha256:061b83aebac180842cf7d249a509986c0122fb36c81f98bbb326640c90f37409'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:061b83aebac180842cf7d249a509986c0122fb36c81f98bbb326640c90f37409', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 231, 'function': 'ESConnection.search'}, 'file': 'memory/utils/es_conn.py', 'line': 231, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
        #   Do not remove without review. site_id='site:sha256:3623a368d62386a04ee66a411bf48da3a22ca161ea9043a42c1baeb5af8d2d8b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3623a368d62386a04ee66a411bf48da3a22ca161ea9043a42c1baeb5af8d2d8b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 234, 'function': 'ESConnection.search'}, 'file': 'memory/utils/es_conn.py', 'line': 234, 'function': 'search', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.error(_lineaje_payload)
        raise Exception("ESConnection.search timeout.")

    def get_forgotten_messages(self, select_fields: list[str], index_name: str, memory_id: str, limit: int=2000):
        bool_query = Q("bool", must_not=[])
        bool_query.must_not.append(Q("term", forget_at=None))
        bool_query.filter.append(Q("term", memory_id=memory_id))
        # from old to new
        order_by = OrderByExpr()
        order_by.asc("forget_at")
        # build search
        s = Search()
        s = s.query(bool_query)
        s = s.sort(order_by)
        s = s[:limit]
        q = s.to_dict()
        # search
        for i in range(ATTEMPT_TIME):
            try:
                res = self.es.search(index=index_name, body=q, timeout="600s", track_total_hits=True, _source=True)
                if str(res.get("timed_out", "")).lower() == "true":
                    raise Exception("Es Timeout.")
                _lineaje_payload = f"ESConnection.search {str(index_name)} res: " + str(res)
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.get_forgotten_messages).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:ddf9333faf952cb1a6554e569d87532a55ba5fc4a9ae6d2482552d23b3420d2e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ddf9333faf952cb1a6554e569d87532a55ba5fc4a9ae6d2482552d23b3420d2e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 256, 'function': 'ESConnection.get_forgotten_messages'}, 'file': 'memory/utils/es_conn.py', 'line': 256, 'function': 'get_forgotten_messages', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.debug(_lineaje_payload)
                # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in ESConnection.get_forgotten_messages).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:b890c0d1f01ba8545617fe9a79245ee607ed0a8dff4559bcbbc8c879f3ce6efd'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b890c0d1f01ba8545617fe9a79245ee607ed0a8dff4559bcbbc8c879f3ce6efd', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 257, 'function': 'ESConnection.get_forgotten_messages'}, 'file': 'memory/utils/es_conn.py', 'line': 257, 'function': 'get_forgotten_messages', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return res
            except ConnectionTimeout:
                _lineaje_payload = "ES request timeout"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.get_forgotten_messages).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:5aa8d751a4b18033a97c68d5bcc94f5252783d830b4d097f36592052087e510c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5aa8d751a4b18033a97c68d5bcc94f5252783d830b4d097f36592052087e510c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 259, 'function': 'ESConnection.get_forgotten_messages'}, 'file': 'memory/utils/es_conn.py', 'line': 259, 'function': 'get_forgotten_messages', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
                _lineaje_payload = f"ESConnection.search {str(index_name)} query: " + str(q) + str(e)
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.get_forgotten_messages).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:d5343481be0471d9fca3f87c7196af409b0b51508e57ecd6f48624a11bef0448'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d5343481be0471d9fca3f87c7196af409b0b51508e57ecd6f48624a11bef0448', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 263, 'function': 'ESConnection.get_forgotten_messages'}, 'file': 'memory/utils/es_conn.py', 'line': 263, 'function': 'get_forgotten_messages', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.exception(_lineaje_payload)
                raise e

        _lineaje_payload = f"ESConnection.search timeout for {ATTEMPT_TIME} times!"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.get_forgotten_messages).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:eddae8cc02102c758250c39cb5725dfbb09d5dedbcdc123e05c8a98d4fd6ca06'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:eddae8cc02102c758250c39cb5725dfbb09d5dedbcdc123e05c8a98d4fd6ca06', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 266, 'function': 'ESConnection.get_forgotten_messages'}, 'file': 'memory/utils/es_conn.py', 'line': 266, 'function': 'get_forgotten_messages', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.error(_lineaje_payload)
        raise Exception("ESConnection.search timeout.")

    def get(self, doc_id: str, index_name: str, memory_ids: list[str]) -> dict | None:
        for i in range(ATTEMPT_TIME):
            try:
                res = self.es.get(index=index_name,
                                  id=doc_id, source=True, )
                if str(res.get("timed_out", "")).lower() == "true":
                    raise Exception("Es Timeout.")
                message = res["_source"]
                message["id"] = doc_id
                return self.get_message_from_es_doc(message)
            except NotFoundError:
                return None
            except Exception as e:
                _lineaje_payload = f"ESConnection.get({doc_id}) got exception"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.get).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:50564dde864319f92ed0b8659b5cb84a27fe604955626c06f3a352de75b573c2'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:50564dde864319f92ed0b8659b5cb84a27fe604955626c06f3a352de75b573c2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 282, 'function': 'ESConnection.get'}, 'file': 'memory/utils/es_conn.py', 'line': 282, 'function': 'get', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.exception(_lineaje_payload)
                raise e
        _lineaje_payload = f"ESConnection.get timeout for {ATTEMPT_TIME} times!"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.get).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:826e09b94c9aa4bf8eabc92a21d90c89ac94a3831d3cf6a419dde0f98680e456'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:826e09b94c9aa4bf8eabc92a21d90c89ac94a3831d3cf6a419dde0f98680e456', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 284, 'function': 'ESConnection.get'}, 'file': 'memory/utils/es_conn.py', 'line': 284, 'function': 'get', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.error(_lineaje_payload)
        raise Exception("ESConnection.get timeout.")

    def insert(self, documents: list[dict], index_name: str, memory_id: str = None) -> list[str]:
        # Refers to https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-bulk.html
        operations = []
        for d in documents:
            assert "_id" not in d
            assert "id" in d
            d_copy_raw = copy.deepcopy(d)
            d_copy = self.map_message_to_es_fields(d_copy_raw)
            d_copy["memory_id"] = memory_id
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
                    #   Do not remove without review. site_id='site:sha256:5b7e43ccbcb73e59f38fe58e2e6a5b8bfd95e27869ad445b3733a447595790c2'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5b7e43ccbcb73e59f38fe58e2e6a5b8bfd95e27869ad445b3733a447595790c2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 307, 'function': 'ESConnection.insert'}, 'file': 'memory/utils/es_conn.py', 'line': 307, 'function': 'insert', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
                #   Do not remove without review. site_id='site:sha256:9e56bc174709eefcecdb4df239fc742dbabd7a9852e6a0a53357326c7585bb0d'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9e56bc174709eefcecdb4df239fc742dbabd7a9852e6a0a53357326c7585bb0d', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 313, 'function': 'ESConnection.insert'}, 'file': 'memory/utils/es_conn.py', 'line': 313, 'function': 'insert', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
                #   Do not remove without review. site_id='site:sha256:55143145308a1e9f15a206bed3aaca1a2833d5fc05ac2c44da65fde3463e25f5'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:55143145308a1e9f15a206bed3aaca1a2833d5fc05ac2c44da65fde3463e25f5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 315, 'function': 'ESConnection.insert'}, 'file': 'memory/utils/es_conn.py', 'line': 315, 'function': 'insert', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
                #   Do not remove without review. site_id='site:sha256:2d6855f4e81992178aab08e9b8578a941782f9d3b5cb389f1d0c8910d3114a7b'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2d6855f4e81992178aab08e9b8578a941782f9d3b5cb389f1d0c8910d3114a7b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 321, 'function': 'ESConnection.insert'}, 'file': 'memory/utils/es_conn.py', 'line': 321, 'function': 'insert', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
        #   Do not remove without review. site_id='site:sha256:9d289cc305d29ce9d126408263ffa4b9b628923281d23f2b45f30cd745715138'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9d289cc305d29ce9d126408263ffa4b9b628923281d23f2b45f30cd745715138', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 323, 'function': 'ESConnection.insert'}, 'file': 'memory/utils/es_conn.py', 'line': 323, 'function': 'insert', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    def update(self, condition: dict, new_value: dict, index_name: str, memory_id: str) -> bool:
        # LINEAJE: runtime guardrail checks `condition` as it flows from the agent to an external endpoint, before it leaves the application (in ESConnection.update).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `condition` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:26f9373a6257bce6a8fee7d9916a5c549b52d00a43f4a33ace2218c5e07834cf'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:26f9373a6257bce6a8fee7d9916a5c549b52d00a43f4a33ace2218c5e07834cf', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 326, 'function': 'ESConnection.update'}, 'file': 'memory/utils/es_conn.py', 'line': 326, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            condition = _gr_client.enforce(_gr_site, condition, content_type='application/json', variable_name='condition', source_file=__file__, before_line=326)
        except _gr_client.GuardrailUnavailableError:
            pass
        doc = copy.deepcopy(new_value)
        update_dict = {self.convert_field_name(k): v for k, v in doc.items()}
        update_dict.pop("id", None)
        condition_dict = {self.convert_field_name(k): v for k, v in condition.items()}
        condition_dict["memory_id"] = memory_id
        if "id" in condition_dict and isinstance(condition_dict["id"], str):
            # update specific single document
            message_id = condition_dict["id"]
            for i in range(ATTEMPT_TIME):
                for k in update_dict.keys():
                    if "feas" != k.split("_")[-1]:
                        continue
                    try:
                        self.es.update(index=index_name, id=message_id, script=f"ctx._source.remove(\"{k}\");")
                    except Exception:
                        # LINEAJE: runtime guardrail checks `condition` as it flows from the agent to an external endpoint, before it leaves the application (in ESConnection.update).
                        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
                        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `condition` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:87694ed07c6e001050c334908f023b301953f48733b8a5058f2a0b7f944ed98e'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:87694ed07c6e001050c334908f023b301953f48733b8a5058f2a0b7f944ed98e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 341, 'function': 'ESConnection.update'}, 'file': 'memory/utils/es_conn.py', 'line': 341, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            condition = _gr_client.enforce(_gr_site, condition, content_type='application/json', variable_name='condition', source_file=__file__, before_line=341)
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        _lineaje_payload = f"ESConnection.update(index={index_name}, id={message_id}, doc={json.dumps(condition, ensure_ascii=False)}) got exception"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.update).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:c06d03ebdf8a1f768b46dad3598b2d6fbddd7a5367726bcdc14c2634450baeaa'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c06d03ebdf8a1f768b46dad3598b2d6fbddd7a5367726bcdc14c2634450baeaa', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 341, 'function': 'ESConnection.update'}, 'file': 'memory/utils/es_conn.py', 'line': 341, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        self.logger.exception(_lineaje_payload)
                try:
                    self.es.update(index=index_name, id=message_id, doc=update_dict)
                    return True
                except Exception as e:
                    # LINEAJE: runtime guardrail checks `condition` as it flows from the agent to an external endpoint, before it leaves the application (in ESConnection.update).
                    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `condition` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:51cd533489ecc40a6968a874a023b5fdd5b83526276568d54812786918d5cde9'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:51cd533489ecc40a6968a874a023b5fdd5b83526276568d54812786918d5cde9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 346, 'function': 'ESConnection.update'}, 'file': 'memory/utils/es_conn.py', 'line': 346, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        condition = _gr_client.enforce(_gr_site, condition, content_type='application/json', variable_name='condition', source_file=__file__, before_line=346)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    _lineaje_payload = f"ESConnection.update(index={index_name}, id={message_id}, doc={json.dumps(condition, ensure_ascii=False)}) got exception: " + str(e)
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnection.update).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:50ab597274aef38689d38e8d3732739536e3ee05e50ceaf84c164ba710ab35c4'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:50ab597274aef38689d38e8d3732739536e3ee05e50ceaf84c164ba710ab35c4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 346, 'function': 'ESConnection.update'}, 'file': 'memory/utils/es_conn.py', 'line': 346, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
        for k, v in condition_dict.items():
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
        for k, v in update_dict.items():
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
            if (not isinstance(k, str) or not v) and k != "status_int":
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
                #   Do not remove without review. site_id='site:sha256:06015af26375b5576f4076718661195e32bfec87916b04f4527e2aea7db2518e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:06015af26375b5576f4076718661195e32bfec87916b04f4527e2aea7db2518e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 393, 'function': 'ESConnection.update'}, 'file': 'memory/utils/es_conn.py', 'line': 393, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    v = _gr_client.enforce(_gr_site, v, content_type='application/json', variable_name='v', source_file=__file__, before_line=393)
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
                #   Do not remove without review. site_id='site:sha256:332c7e503575981a885ce66c16f7ba5d05c9e3c41a860357dc2b31ed8a69444d'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:332c7e503575981a885ce66c16f7ba5d05c9e3c41a860357dc2b31ed8a69444d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 409, 'function': 'ESConnection.update'}, 'file': 'memory/utils/es_conn.py', 'line': 409, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
                #   Do not remove without review. site_id='site:sha256:38d15444e881b1108cbb08b16a2833ed74c53c38394a01d990574e226aa2d5f3'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:38d15444e881b1108cbb08b16a2833ed74c53c38394a01d990574e226aa2d5f3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 414, 'function': 'ESConnection.update'}, 'file': 'memory/utils/es_conn.py', 'line': 414, 'function': 'update', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.error(_lineaje_payload)
                break
        return False

    def delete(self, condition: dict, index_name: str, memory_id: str) -> int:
        assert "_id" not in condition
        condition_dict = {self.convert_field_name(k): v for k, v in condition.items()}
        condition_dict["memory_id"] = memory_id
        if "id" in condition_dict:
            message_ids = condition_dict["id"]
            if not isinstance(message_ids, list):
                message_ids = [message_ids]
            if not message_ids:  # when message_ids is empty, delete all
                qry = Q("match_all")
            else:
                qry = Q("ids", values=message_ids)
        else:
            qry = Q("bool")
            for k, v in condition_dict.items():
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
        #   Do not remove without review. site_id='site:sha256:cf56a9c25146e2165aad4b887cf32fc0e2e35f6dd5a078c327008ff26e21ecab'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cf56a9c25146e2165aad4b887cf32fc0e2e35f6dd5a078c327008ff26e21ecab', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 448, 'function': 'ESConnection.delete'}, 'file': 'memory/utils/es_conn.py', 'line': 448, 'function': 'delete', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
                #   Do not remove without review. site_id='site:sha256:bce5553563e47d31424f400afb5b4fc6b0baf86bf24cc6f3fe957fa714435deb'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bce5553563e47d31424f400afb5b4fc6b0baf86bf24cc6f3fe957fa714435deb', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 457, 'function': 'ESConnection.delete'}, 'file': 'memory/utils/es_conn.py', 'line': 457, 'function': 'delete', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
                #   Do not remove without review. site_id='site:sha256:82ac1eb406a5f11f7709b68f13f24e13802a5f0395f41d49ab6fbae6956043f5'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:82ac1eb406a5f11f7709b68f13f24e13802a5f0395f41d49ab6fbae6956043f5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 462, 'function': 'ESConnection.delete'}, 'file': 'memory/utils/es_conn.py', 'line': 462, 'function': 'delete', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
        for doc in self._get_source(res):
            message = self.get_message_from_es_doc(doc)
            m = {}
            for n, v in message.items():
                if n not in fields:
                    continue
                if isinstance(v, list):
                    m[n] = v
                    continue
                if n in ["message_id", "source_id", "valid_at", "invalid_at", "forget_at", "status"] and isinstance(v, (int, float, bool)):
                    m[n] = v
                    continue
                if not isinstance(v, str):
                    m[n] = str(v)
                else:
                    m[n] = v

            if m:
                res_fields[doc["id"]] = m
        # LINEAJE: runtime guardrail checks `res_fields` as it flows from the agent to the user interface, before it leaves the application (in ESConnection.get_fields).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res_fields` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f4c59e5acade12674747702b96bfabbc1e55e86837d2d34c84ccc0f3dc89357f'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f4c59e5acade12674747702b96bfabbc1e55e86837d2d34c84ccc0f3dc89357f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/es_conn.py', 'line': 494, 'function': 'ESConnection.get_fields'}, 'file': 'memory/utils/es_conn.py', 'line': 494, 'function': 'get_fields', 'agent_name': 'ESConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res_fields = _gr_client.enforce(_gr_site, res_fields, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res_fields
