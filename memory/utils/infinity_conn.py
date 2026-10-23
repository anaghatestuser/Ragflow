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
import copy
from infinity.common import InfinityException, SortType
from infinity.errors import ErrorCode

from common.decorator import singleton
import pandas as pd
from common.constants import PAGERANK_FLD, TAG_FLD
from common.doc_store.doc_store_base import MatchExpr, MatchTextExpr, MatchDenseExpr, FusionExpr, OrderByExpr
from common.doc_store.infinity_conn_base import InfinityConnectionBase
from common.time_utils import date_string_to_timestamp


@singleton
class InfinityConnection(InfinityConnectionBase):
    def __init__(self):
        super().__init__()
        self.mapping_file_name = "message_infinity_mapping.json"

    """
    Dataframe and fields convert
    """

    @staticmethod
    def field_keyword(field_name: str):
        # no keywords right now
        return False

    @staticmethod
    def convert_message_field_to_infinity(field_name: str):
        match field_name:
            case "message_type":
                return "message_type_kwd"
            case "status":
                return "status_int"
            case _:
                # LINEAJE: runtime guardrail checks `field_name` as it flows from the agent to the user interface, before it leaves the application (in InfinityConnection.convert_message_field_to_infinity).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `field_name` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:34302acce0f3b46a3b64175bf5ec8a26cbb46cc9207f4b6d955307565032a29c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:34302acce0f3b46a3b64175bf5ec8a26cbb46cc9207f4b6d955307565032a29c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 54, 'function': 'InfinityConnection.convert_message_field_to_infinity'}, 'file': 'memory/utils/infinity_conn.py', 'line': 54, 'function': 'convert_message_field_to_infinity', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    field_name = _gr_client.enforce(_gr_site, field_name, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return field_name

    @staticmethod
    def convert_infinity_field_to_message(field_name: str):
        if field_name.startswith("message_type"):
            return "message_type"
        if field_name.startswith("status"):
            return "status"
        if re.match(r"q_\d+_vec", field_name):
            return "content_embed"
        # LINEAJE: runtime guardrail checks `field_name` as it flows from the agent to the user interface, before it leaves the application (in InfinityConnection.convert_infinity_field_to_message).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `field_name` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:dbc19101141a23daed90f1f21eadfcb5e23ca0376e1d9f039c2756b2fbe82f51'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dbc19101141a23daed90f1f21eadfcb5e23ca0376e1d9f039c2756b2fbe82f51', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 64, 'function': 'InfinityConnection.convert_infinity_field_to_message'}, 'file': 'memory/utils/infinity_conn.py', 'line': 64, 'function': 'convert_infinity_field_to_message', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            field_name = _gr_client.enforce(_gr_site, field_name, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return field_name

    def convert_select_fields(self, output_fields: list[str]) -> list[str]:
        return list({self.convert_message_field_to_infinity(f) for f in output_fields})

    @staticmethod
    def convert_matching_field(field_weight_str: str) -> str:
        tokens = field_weight_str.split("^")
        field = tokens[0]
        if field == "content":
            field = "content@ft_contentm_rag_fine"
        tokens[0] = field
        return "^".join(tokens)

    @staticmethod
    def convert_condition_and_order_field(field_name: str):
        match field_name:
            case "message_type":
                return "message_type_kwd"
            case "status":
                return "status_int"
            case "valid_at":
                return "valid_at_flt"
            case "invalid_at":
                return "invalid_at_flt"
            case "forget_at":
                return "forget_at_flt"
            case _:
                # LINEAJE: runtime guardrail checks `field_name` as it flows from the agent to the user interface, before it leaves the application (in InfinityConnection.convert_condition_and_order_field).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `field_name` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:0a70ab4593dcec3f0c1d1ad8574b806763ebe2863b5ed6711b2a964b8f0848a9'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0a70ab4593dcec3f0c1d1ad8574b806763ebe2863b5ed6711b2a964b8f0848a9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 92, 'function': 'InfinityConnection.convert_condition_and_order_field'}, 'file': 'memory/utils/infinity_conn.py', 'line': 92, 'function': 'convert_condition_and_order_field', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    field_name = _gr_client.enforce(_gr_site, field_name, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return field_name

    """
    CRUD operations
    """

    def search(
        self,
        select_fields: list[str],
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
        hide_forgotten: bool = True,
    ) -> tuple[pd.DataFrame, int]:
        """
        BUG: Infinity returns empty for a highlight field if the query string doesn't use that field.
        """
        if isinstance(index_names, str):
            index_names = index_names.split(",")
        assert isinstance(index_names, list) and len(index_names) > 0
        inf_conn = self.connPool.get_conn()
        db_instance = inf_conn.get_database(self.dbName)
        df_list = list()
        table_list = list()
        if hide_forgotten:
            condition.update({"must_not": {"exists": "forget_at_flt"}})
        output = select_fields.copy()
        output = self.convert_select_fields(output)
        if agg_fields is None:
            agg_fields = []
        for essential_field in ["id"] + agg_fields:
            if essential_field not in output:
                output.append(essential_field)
        score_func = ""
        score_column = ""
        for matchExpr in match_expressions:
            if isinstance(matchExpr, MatchTextExpr):
                score_func = "score()"
                score_column = "SCORE"
                break
        if not score_func:
            for matchExpr in match_expressions:
                if isinstance(matchExpr, MatchDenseExpr):
                    score_func = "similarity()"
                    score_column = "SIMILARITY"
                    break
        if match_expressions:
            if score_func not in output:
                output.append(score_func)
            if PAGERANK_FLD not in output:
                output.append(PAGERANK_FLD)
        output = [f for f in output if f != "_score"]
        if limit <= 0:
            # ElasticSearch default limit is 10000
            limit = 10000

        # Prepare expressions common to all tables
        filter_cond = None
        filter_fulltext = ""
        if condition:
            condition_dict = {self.convert_condition_and_order_field(k): v for k, v in condition.items()}
            table_found = False
            for indexName in index_names:
                for mem_id in memory_ids:
                    table_name = f"{indexName}_{mem_id}"
                    try:
                        filter_cond = self.equivalent_condition_to_str(condition_dict, db_instance.get_table(table_name))
                        table_found = True
                        break
                    except Exception:
                        pass
                if table_found:
                    break
            if not table_found:
                _lineaje_payload = f"No valid tables found for indexNames {index_names} and memoryIds {memory_ids}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnection.search).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f79c0a7246137e8895a1b3255f678fc16c9fc93b307bbd27bc284da3d143049e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f79c0a7246137e8895a1b3255f678fc16c9fc93b307bbd27bc284da3d143049e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 173, 'function': 'InfinityConnection.search'}, 'file': 'memory/utils/infinity_conn.py', 'line': 173, 'function': 'search', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.error(_lineaje_payload)
                return pd.DataFrame(), 0

        for matchExpr in match_expressions:
            if isinstance(matchExpr, MatchTextExpr):
                if filter_cond and "filter" not in matchExpr.extra_options:
                    matchExpr.extra_options.update({"filter": filter_cond})
                matchExpr.fields = [self.convert_matching_field(field) for field in matchExpr.fields]
                fields = ",".join(matchExpr.fields)
                filter_fulltext = f"filter_fulltext('{fields}', '{matchExpr.matching_text}')"
                if filter_cond:
                    filter_fulltext = f"({filter_cond}) AND {filter_fulltext}"
                minimum_should_match = matchExpr.extra_options.get("minimum_should_match", 0.0)
                if isinstance(minimum_should_match, float):
                    str_minimum_should_match = str(int(minimum_should_match * 100)) + "%"
                    matchExpr.extra_options["minimum_should_match"] = str_minimum_should_match

                # Add rank_feature support
                if rank_feature and "rank_features" not in matchExpr.extra_options:
                    # Convert rank_feature dict to Infinity's rank_features string format
                    # Format: "field^feature_name^weight,field^feature_name^weight"
                    rank_features_list = []
                    for feature_name, weight in rank_feature.items():
                        # Use TAG_FLD as the field containing rank features
                        rank_features_list.append(f"{TAG_FLD}^{feature_name}^{weight}")
                    if rank_features_list:
                        matchExpr.extra_options["rank_features"] = ",".join(rank_features_list)

                for k, v in matchExpr.extra_options.items():
                    if not isinstance(v, str):
                        matchExpr.extra_options[k] = str(v)
                _lineaje_payload = f"INFINITY search MatchTextExpr: {json.dumps(matchExpr.__dict__)}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnection.search).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:ffedacb2af094e91599c43db3810b53fbc663114e594c2c7628c033a00bcda98'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ffedacb2af094e91599c43db3810b53fbc663114e594c2c7628c033a00bcda98', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 204, 'function': 'InfinityConnection.search'}, 'file': 'memory/utils/infinity_conn.py', 'line': 204, 'function': 'search', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.debug(_lineaje_payload)
            elif isinstance(matchExpr, MatchDenseExpr):
                if filter_fulltext and "filter" not in matchExpr.extra_options:
                    matchExpr.extra_options.update({"filter": filter_fulltext})
                for k, v in matchExpr.extra_options.items():
                    if not isinstance(v, str):
                        matchExpr.extra_options[k] = str(v)
                similarity = matchExpr.extra_options.get("similarity")
                if similarity:
                    matchExpr.extra_options["threshold"] = similarity
                    del matchExpr.extra_options["similarity"]
                _lineaje_payload = f"INFINITY search MatchDenseExpr: {json.dumps(matchExpr.__dict__)}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnection.search).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:95986ce0394d3dae4198e6a05426075b071590f523adaf4b811abfa08ed1d61e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:95986ce0394d3dae4198e6a05426075b071590f523adaf4b811abfa08ed1d61e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 215, 'function': 'InfinityConnection.search'}, 'file': 'memory/utils/infinity_conn.py', 'line': 215, 'function': 'search', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.debug(_lineaje_payload)
            elif isinstance(matchExpr, FusionExpr):
                _lineaje_payload = f"INFINITY search FusionExpr: {json.dumps(matchExpr.__dict__)}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnection.search).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a58cb5107e364ea44659d16b17164a863dcbae98e3f4e1813d10ba1eef7799b9'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a58cb5107e364ea44659d16b17164a863dcbae98e3f4e1813d10ba1eef7799b9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 217, 'function': 'InfinityConnection.search'}, 'file': 'memory/utils/infinity_conn.py', 'line': 217, 'function': 'search', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.debug(_lineaje_payload)

        order_by_expr_list = list()
        if order_by.fields:
            for order_field in order_by.fields:
                order_field_name = self.convert_condition_and_order_field(order_field[0])
                if order_field[1] == 0:
                    order_by_expr_list.append((order_field_name, SortType.Asc))
                else:
                    order_by_expr_list.append((order_field_name, SortType.Desc))

        total_hits_count = 0
        # Scatter search tables and gather the results
        for indexName in index_names:
            for memory_id in memory_ids:
                table_name = f"{indexName}_{memory_id}"
                try:
                    table_instance = db_instance.get_table(table_name)
                except Exception:
                    continue
                table_list.append(table_name)
                builder = table_instance.output(output)
                if len(match_expressions) > 0:
                    for matchExpr in match_expressions:
                        if isinstance(matchExpr, MatchTextExpr):
                            fields = ",".join(matchExpr.fields)
                            builder = builder.match_text(
                                fields,
                                matchExpr.matching_text,
                                matchExpr.topn,
                                matchExpr.extra_options.copy(),
                            )
                        elif isinstance(matchExpr, MatchDenseExpr):
                            builder = builder.match_dense(
                                matchExpr.vector_column_name,
                                matchExpr.embedding_data,
                                matchExpr.embedding_data_type,
                                matchExpr.distance_type,
                                matchExpr.topn,
                                matchExpr.extra_options.copy(),
                            )
                        elif isinstance(matchExpr, FusionExpr):
                            builder = builder.fusion(matchExpr.method, matchExpr.topn, matchExpr.fusion_params)
                else:
                    if filter_cond and len(filter_cond) > 0:
                        builder.filter(filter_cond)
                if order_by.fields:
                    builder.sort(order_by_expr_list)
                builder.offset(offset).limit(limit)
                mem_res, extra_result = builder.option({"total_hits_count": True}).to_df()
                if extra_result:
                    total_hits_count += int(extra_result["total_hits_count"])
                _lineaje_payload = f"INFINITY search table: {str(table_name)}, result: {str(mem_res)}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnection.search).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:21bc342520ce23399c54decdf7eff5f35c77f3202843c4d3043cd6756edf524c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:21bc342520ce23399c54decdf7eff5f35c77f3202843c4d3043cd6756edf524c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 269, 'function': 'InfinityConnection.search'}, 'file': 'memory/utils/infinity_conn.py', 'line': 269, 'function': 'search', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.debug(_lineaje_payload)
                df_list.append(mem_res)
        self.connPool.release_conn(inf_conn)
        res = self.concat_dataframes(df_list, output)
        if match_expressions:
            res["_score"] = res[score_column] + res[PAGERANK_FLD]
            res = res.sort_values(by="_score", ascending=False).reset_index(drop=True)
            res = res.head(limit)
        _lineaje_payload = f"INFINITY search final result: {str(res)}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnection.search).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:138a72f02bf97994522b22168330962c2b62c183316b583a3cfa1b9b401234ff'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:138a72f02bf97994522b22168330962c2b62c183316b583a3cfa1b9b401234ff', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 277, 'function': 'InfinityConnection.search'}, 'file': 'memory/utils/infinity_conn.py', 'line': 277, 'function': 'search', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.debug(_lineaje_payload)
        return res, total_hits_count

    def get_forgotten_messages(self, select_fields: list[str], index_name: str, memory_id: str, limit: int=2000):
        condition = {"memory_id": memory_id, "exists": "forget_at_flt"}
        order_by = OrderByExpr()
        order_by.asc("forget_at_flt")
        # query
        inf_conn = self.connPool.get_conn()
        db_instance = inf_conn.get_database(self.dbName)
        table_name = f"{index_name}_{memory_id}"
        table_instance = db_instance.get_table(table_name)
        output_fields = [self.convert_message_field_to_infinity(f) for f in select_fields]
        builder = table_instance.output(output_fields)
        filter_cond = self.equivalent_condition_to_str(condition, db_instance.get_table(table_name))
        builder.filter(filter_cond)
        order_by_expr_list = list()
        if order_by.fields:
            for order_field in order_by.fields:
                order_field_name = self.convert_condition_and_order_field(order_field[0])
                if order_field[1] == 0:
                    order_by_expr_list.append((order_field_name, SortType.Asc))
                else:
                    order_by_expr_list.append((order_field_name, SortType.Desc))
        builder.sort(order_by_expr_list)
        builder.offset(0).limit(limit)
        mem_res, _ = builder.option({"total_hits_count": True}).to_df()
        res = self.concat_dataframes(mem_res, output_fields)
        res.head(limit)
        self.connPool.release_conn(inf_conn)
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in InfinityConnection.get_forgotten_messages).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e7efd4c4a0f2c66294ca318f5945240c4171efe504bf30ef7deddf201d4224d3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e7efd4c4a0f2c66294ca318f5945240c4171efe504bf30ef7deddf201d4224d3', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 307, 'function': 'InfinityConnection.get_forgotten_messages'}, 'file': 'memory/utils/infinity_conn.py', 'line': 307, 'function': 'get_forgotten_messages', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    def get(self, message_id: str, index_name: str, memory_ids: list[str]) -> dict | None:
        inf_conn = self.connPool.get_conn()
        db_instance = inf_conn.get_database(self.dbName)
        df_list = list()
        assert isinstance(memory_ids, list)
        table_list = list()
        for memoryId in memory_ids:
            table_name = f"{index_name}_{memoryId}"
            table_list.append(table_name)
            try:
                table_instance = db_instance.get_table(table_name)
            except Exception:
                _lineaje_payload = f"Table not found: {table_name}, this memory isn't created in Infinity. Maybe it is created in other document engine."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnection.get).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:6c41dd5a1705dad0fc6989d0cc228cfa526832770d7f2a14f3bdd6cdccded73a'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6c41dd5a1705dad0fc6989d0cc228cfa526832770d7f2a14f3bdd6cdccded73a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 321, 'function': 'InfinityConnection.get'}, 'file': 'memory/utils/infinity_conn.py', 'line': 321, 'function': 'get', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.warning(_lineaje_payload)
                continue
            mem_res, _ = table_instance.output(["*"]).filter(f"id = '{message_id}'").to_df()
            _lineaje_payload = f"INFINITY get table: {str(table_list)}, result: {str(mem_res)}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnection.get).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e5a50059757a9ed4fc6b5986ac6523fe1f0bd5a993f88f5cc68d6ec0a5964517'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e5a50059757a9ed4fc6b5986ac6523fe1f0bd5a993f88f5cc68d6ec0a5964517', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 324, 'function': 'InfinityConnection.get'}, 'file': 'memory/utils/infinity_conn.py', 'line': 324, 'function': 'get', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.debug(_lineaje_payload)
            df_list.append(mem_res)
        self.connPool.release_conn(inf_conn)
        res = self.concat_dataframes(df_list, ["id"])
        fields = set(res.columns.tolist())
        res_fields = self.get_fields(res, list(fields))
        return res_fields.get(message_id, None)

    def insert(self, documents: list[dict], index_name: str, memory_id: str = None) -> list[str]:
        if not documents:
            return []
        inf_conn = self.connPool.get_conn()
        db_instance = inf_conn.get_database(self.dbName)
        table_name = f"{index_name}_{memory_id}"
        vector_size = int(len(documents[0]["content_embed"]))
        try:
            table_instance = db_instance.get_table(table_name)
        except InfinityException as e:
            # src/common/status.cppm, kTableNotExist = 3022
            if e.error_code != ErrorCode.TABLE_NOT_EXIST:
                raise
            if vector_size == 0:
                raise ValueError("Cannot infer vector size from documents")
            self.create_idx(index_name, memory_id, vector_size)
            table_instance = db_instance.get_table(table_name)

        # embedding fields can't have a default value....
        embedding_columns = []
        table_columns = table_instance.show_columns().rows()
        for n, ty, _, _ in table_columns:
            r = re.search(r"Embedding\([a-z]+,([0-9]+)\)", ty)
            if not r:
                continue
            embedding_columns.append((n, int(r.group(1))))

        docs = copy.deepcopy(documents)
        for d in docs:
            assert "_id" not in d
            assert "id" in d
            for k, v in list(d.items()):
                field_name = self.convert_message_field_to_infinity(k)
                if field_name in ["valid_at", "invalid_at", "forget_at"]:
                    d[f"{field_name}_flt"] = date_string_to_timestamp(v) if v else 0
                    if v is None:
                        d[field_name] = ""
                elif self.field_keyword(k):
                    if isinstance(v, list):
                        d[k] = "###".join(v)
                    else:
                        d[k] = v
                elif k == "memory_id":
                    if isinstance(d[k], list):
                        d[k] = d[k][0]  # since d[k] is a list, but we need a str
                elif field_name == "content_embed":
                    d[f"q_{vector_size}_vec"] = d["content_embed"]
                    d.pop("content_embed")
                else:
                    d[field_name] = v
                if k != field_name:
                    d.pop(k)

            for n, vs in embedding_columns:
                if n in d:
                    continue
                d[n] = [0] * vs
        ids = ["'{}'".format(d["id"]) for d in docs]
        str_ids = ", ".join(ids)
        str_filter = f"id IN ({str_ids})"
        table_instance.delete(str_filter)
        table_instance.insert(docs)
        self.connPool.release_conn(inf_conn)
        _lineaje_payload = f"INFINITY inserted into {table_name} {str_ids}."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnection.insert).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:61e3695ceb8d219484825e59d0d1b9ee4f4836e3470da25f72d32b3db4a6b8f2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:61e3695ceb8d219484825e59d0d1b9ee4f4836e3470da25f72d32b3db4a6b8f2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 395, 'function': 'InfinityConnection.insert'}, 'file': 'memory/utils/infinity_conn.py', 'line': 395, 'function': 'insert', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.debug(_lineaje_payload)
        return []

    def update(self, condition: dict, new_value: dict, index_name: str, memory_id: str) -> bool:
        inf_conn = self.connPool.get_conn()
        db_instance = inf_conn.get_database(self.dbName)
        table_name = f"{index_name}_{memory_id}"
        table_instance = db_instance.get_table(table_name)

        columns = {}
        if table_instance:
            for n, ty, de, _ in table_instance.show_columns().rows():
                columns[n] = (ty, de)
        condition_dict = {self.convert_condition_and_order_field(k): v for k, v in condition.items()}
        filter = self.equivalent_condition_to_str(condition_dict, table_instance)
        update_dict = {self.convert_message_field_to_infinity(k): v for k, v in new_value.items()}
        date_floats = {}
        for k, v in update_dict.items():
            if k in ["valid_at", "invalid_at", "forget_at"]:
                date_floats[f"{k}_flt"] = date_string_to_timestamp(v) if v else 0
            elif self.field_keyword(k):
                if isinstance(v, list):
                    update_dict[k] = "###".join(v)
                else:
                    update_dict[k] = v
            elif k == "memory_id":
                if isinstance(update_dict[k], list):
                    update_dict[k] = update_dict[k][0]  # since d[k] is a list, but we need a str
            else:
                update_dict[k] = v
        if date_floats:
            update_dict.update(date_floats)

        _lineaje_payload = f"INFINITY update table {table_name}, filter {filter}, newValue {new_value}."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnection.update).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1ecc25344fef3f6a3f152e6aac23b933615781d6ade3846a95bd56f3c1bf2443'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1ecc25344fef3f6a3f152e6aac23b933615781d6ade3846a95bd56f3c1bf2443', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/utils/infinity_conn.py', 'line': 428, 'function': 'InfinityConnection.update'}, 'file': 'memory/utils/infinity_conn.py', 'line': 428, 'function': 'update', 'agent_name': 'InfinityConnection', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.debug(_lineaje_payload)
        table_instance.update(filter, update_dict)
        self.connPool.release_conn(inf_conn)
        return True

    """
    Helper functions for search result
    """

    def get_fields(self, res: tuple[pd.DataFrame, int] | pd.DataFrame, fields: list[str]) -> dict[str, dict]:
        if isinstance(res, tuple):
            res = res[0]
        if not fields:
            return {}
        fields_all = fields.copy()
        fields_all.append("id")
        fields_all = {self.convert_message_field_to_infinity(f) for f in fields_all}

        column_map = {col.lower(): col for col in res.columns}
        matched_columns = {column_map[col.lower()]: col for col in fields_all if col.lower() in column_map}
        none_columns = [col for col in fields_all if col.lower() not in column_map]

        res2 = res[matched_columns.keys()]
        res2 = res2.rename(columns=matched_columns)
        res2.drop_duplicates(subset=["id"], inplace=True)

        for column in list(res2.columns):
            k = column.lower()
            if self.field_keyword(k):
                res2[column] = res2[column].apply(lambda v: [kwd for kwd in v.split("###") if kwd])
            else:
                pass
        for column in ["content"]:
            if column in res2:
                del res2[column]
        for column in none_columns:
            res2[column] = None

        res_dict = res2.set_index("id").to_dict(orient="index")
        return {_id: {self.convert_infinity_field_to_message(k): v for k, v in doc.items()} for _id, doc in res_dict.items()}
