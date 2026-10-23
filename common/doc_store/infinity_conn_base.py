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

import logging
import os
import re
import json
import time
from abc import abstractmethod

import infinity
from infinity.common import ConflictType
from infinity.index import IndexInfo, IndexType
from infinity.connection_pool import ConnectionPool
from infinity.errors import ErrorCode
import pandas as pd
from common.file_utils import get_project_base_directory
from rag.nlp import is_english
from common import settings
from common.doc_store.doc_store_base import DocStoreConnection, MatchExpr, OrderByExpr


class InfinityConnectionBase(DocStoreConnection):
    def __init__(self, mapping_file_name: str="infinity_mapping.json", logger_name: str="ragflow.infinity_conn"):
        self.dbName = settings.INFINITY.get("db_name", "default_db")
        self.mapping_file_name = mapping_file_name
        self.logger = logging.getLogger(logger_name)
        infinity_uri = settings.INFINITY["uri"]
        if ":" in infinity_uri:
            host, port = infinity_uri.split(":")
            infinity_uri = infinity.common.NetworkAddress(host, int(port))
        self.connPool = None
        _lineaje_payload = f"Use Infinity {infinity_uri} as the doc engine."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnectionBase.__init__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3771df0559290562a8c6a148935413066bac3da2a5691ac8e5d1ca3966da6b7d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3771df0559290562a8c6a148935413066bac3da2a5691ac8e5d1ca3966da6b7d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 46, 'function': 'InfinityConnectionBase.__init__'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 46, 'function': '__init__', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)
        for _ in range(24):
            try:
                conn_pool = ConnectionPool(infinity_uri, max_size=4)
                inf_conn = conn_pool.get_conn()
                res = inf_conn.show_current_node()
                if res.error_code == ErrorCode.OK and res.server_status in ["started", "alive"]:
                    self._migrate_db(inf_conn)
                    self.connPool = conn_pool
                    conn_pool.release_conn(inf_conn)
                    break
                conn_pool.release_conn(inf_conn)
                _lineaje_payload = f"Infinity status: {res.server_status}. Waiting Infinity {infinity_uri} to be healthy."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnectionBase.__init__).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:d8c35dd0602b80f0b2f6742fb93f240e7e3fe3a1a07d955d08f85b82e5e4302e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d8c35dd0602b80f0b2f6742fb93f240e7e3fe3a1a07d955d08f85b82e5e4302e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 58, 'function': 'InfinityConnectionBase.__init__'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 58, 'function': '__init__', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.warning(_lineaje_payload)
                time.sleep(5)
            except Exception as e:
                _lineaje_payload = f"{str(e)}. Waiting Infinity {infinity_uri} to be healthy."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnectionBase.__init__).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:e94d95950cfb233b3bee16e8edb26fcfb5ce62a422d97ac082129c522ee43a61'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e94d95950cfb233b3bee16e8edb26fcfb5ce62a422d97ac082129c522ee43a61', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 61, 'function': 'InfinityConnectionBase.__init__'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 61, 'function': '__init__', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.warning(_lineaje_payload)
                time.sleep(5)
        if self.connPool is None:
            msg = f"Infinity {infinity_uri} is unhealthy in 120s."
            # LINEAJE: runtime guardrail checks `msg` as it flows from the agent to the application log, before it is written to the log (in InfinityConnectionBase.__init__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:78ca512e57c238d695ae209efa6eb922ef838550191d47f4a876bb5541e42a50'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:78ca512e57c238d695ae209efa6eb922ef838550191d47f4a876bb5541e42a50', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 65, 'function': 'InfinityConnectionBase.__init__'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 65, 'function': '__init__', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                msg = _gr_client.enforce(_gr_site, msg, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.error(msg)
            raise Exception(msg)
        _lineaje_payload = f"Infinity {infinity_uri} is healthy."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnectionBase.__init__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:769dcc1c6280fa3aa456a8e67af6d1c2a412538720c2a727580b3fe0614fbb76'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:769dcc1c6280fa3aa456a8e67af6d1c2a412538720c2a727580b3fe0614fbb76', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 67, 'function': 'InfinityConnectionBase.__init__'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 67, 'function': '__init__', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)

    def _migrate_db(self, inf_conn):
        inf_db = inf_conn.create_database(self.dbName, ConflictType.Ignore)
        fp_mapping = os.path.join(get_project_base_directory(), "conf", self.mapping_file_name)
        if not os.path.exists(fp_mapping):
            raise Exception(f"Mapping file not found at {fp_mapping}")
        schema = json.load(open(fp_mapping))
        table_names = inf_db.list_tables().table_names
        for table_name in table_names:
            inf_table = inf_db.get_table(table_name)
            index_names = inf_table.list_indexes().index_names
            if "q_vec_idx" not in index_names:
                # Skip tables not created by me
                continue
            column_names = inf_table.show_columns()["name"]
            column_names = set(column_names)
            for field_name, field_info in schema.items():
                if field_name in column_names:
                    continue
                res = inf_table.add_columns({field_name: field_info})
                assert res.error_code == infinity.ErrorCode.OK
                _lineaje_payload = f"INFINITY added following column to table {table_name}: {field_name} {field_info}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnectionBase._migrate_db).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:01e8e4bdabb66d279ccfa1a13073f6a8fe27db50883b337a2677106d9ab6f11a'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:01e8e4bdabb66d279ccfa1a13073f6a8fe27db50883b337a2677106d9ab6f11a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 89, 'function': 'InfinityConnectionBase._migrate_db'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 89, 'function': '_migrate_db', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.info(_lineaje_payload)
                if field_info["type"] != "varchar" or "analyzer" not in field_info:
                    continue
                analyzers = field_info["analyzer"]
                if isinstance(analyzers, str):
                    analyzers = [analyzers]
                for analyzer in analyzers:
                    inf_table.create_index(
                        f"ft_{re.sub(r'[^a-zA-Z0-9]', '_', field_name)}_{re.sub(r'[^a-zA-Z0-9]', '_', analyzer)}",
                        IndexInfo(field_name, IndexType.FullText, {"ANALYZER": analyzer}),
                        ConflictType.Ignore,
                    )

    """
    Dataframe and fields convert
    """

    @staticmethod
    @abstractmethod
    def field_keyword(field_name: str):
        # judge keyword or not, such as "*_kwd" tag-like columns.
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def convert_select_fields(self, output_fields: list[str]) -> list[str]:
        # rm _kwd, _tks, _sm_tks, _with_weight suffix in field name.
        raise NotImplementedError("Not implemented")

    @staticmethod
    @abstractmethod
    def convert_matching_field(field_weight_str: str) -> str:
        # convert matching field to
        raise NotImplementedError("Not implemented")

    @staticmethod
    def list2str(lst: str | list, sep: str = " ") -> str:
        if isinstance(lst, str):
            # LINEAJE: runtime guardrail checks `lst` as it flows from the agent to the user interface, before it leaves the application (in InfinityConnectionBase.list2str).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `lst` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0b99f1e93775658a511267c8b2419838fb2901e96bb79a3d761816d0ec304dc8'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0b99f1e93775658a511267c8b2419838fb2901e96bb79a3d761816d0ec304dc8', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 126, 'function': 'InfinityConnectionBase.list2str'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 126, 'function': 'list2str', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                lst = _gr_client.enforce(_gr_site, lst, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return lst
        return sep.join(lst)

    def equivalent_condition_to_str(self, condition: dict, table_instance=None) -> str | None:
        assert "_id" not in condition
        columns = {}
        if table_instance:
            for n, ty, de, _ in table_instance.show_columns().rows():
                columns[n] = (ty, de)

        def exists(cln):
            nonlocal columns
            assert cln in columns, f"'{cln}' should be in '{columns}'."
            ty, de = columns[cln]
            if ty.lower().find("cha"):
                if not de:
                    de = ""
                return f" {cln}!='{de}' "
            return f"{cln}!={de}"

        cond = list()
        for k, v in condition.items():
            if not isinstance(k, str) or not v:
                continue
            if self.field_keyword(k):
                if isinstance(v, list):
                    inCond = list()
                    for item in v:
                        if isinstance(item, str):
                            item = item.replace("'", "''")
                        inCond.append(f"filter_fulltext('{self.convert_matching_field(k)}', '{item}')")
                    if inCond:
                        strInCond = " or ".join(inCond)
                        strInCond = f"({strInCond})"
                        cond.append(strInCond)
                else:
                    cond.append(f"filter_fulltext('{self.convert_matching_field(k)}', '{v}')")
            elif isinstance(v, list):
                inCond = list()
                for item in v:
                    if isinstance(item, str):
                        item = item.replace("'", "''")
                        inCond.append(f"'{item}'")
                    else:
                        inCond.append(str(item))
                if inCond:
                    strInCond = ", ".join(inCond)
                    strInCond = f"{k} IN ({strInCond})"
                    cond.append(strInCond)
            elif k == "must_not":
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        if kk == "exists":
                            cond.append("NOT (%s)" % exists(vv))
            elif isinstance(v, str):
                cond.append(f"{k}='{v}'")
            elif k == "exists":
                cond.append(exists(v))
            else:
                cond.append(f"{k}={str(v)}")
        return " AND ".join(cond) if cond else "1=1"

    @staticmethod
    def concat_dataframes(df_list: list[pd.DataFrame], select_fields: list[str]) -> pd.DataFrame:
        df_list2 = [df for df in df_list if not df.empty]
        if df_list2:
            return pd.concat(df_list2, axis=0).reset_index(drop=True)

        schema = []
        for field_name in select_fields:
            if field_name == "score()":  # Workaround: fix schema is changed to score()
                schema.append("SCORE")
            elif field_name == "similarity()":  # Workaround: fix schema is changed to similarity()
                schema.append("SIMILARITY")
            else:
                schema.append(field_name)
        return pd.DataFrame(columns=schema)

    """
    Database operations
    """

    def db_type(self) -> str:
        return "infinity"

    def health(self) -> dict:
        """
        Return the health status of the database.
        """
        inf_conn = self.connPool.get_conn()
        res = inf_conn.show_current_node()
        self.connPool.release_conn(inf_conn)
        res2 = {
            "type": "infinity",
            "status": "green" if res.error_code == 0 and res.server_status in ["started", "alive"] else "red",
            "error": res.error_msg,
        }
        # LINEAJE: runtime guardrail checks `res2` as it flows from the agent to the user interface, before it leaves the application (in InfinityConnectionBase.health).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res2` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:dd25844f9d7b479e198a3365d6a254f70846aa748748d3a16db0302aede1eca8'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dd25844f9d7b479e198a3365d6a254f70846aa748748d3a16db0302aede1eca8', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 223, 'function': 'InfinityConnectionBase.health'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 223, 'function': 'health', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res2 = _gr_client.enforce(_gr_site, res2, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res2

    """
    Table operations
    """

    def create_idx(self, index_name: str, dataset_id: str, vector_size: int):
        table_name = f"{index_name}_{dataset_id}"
        inf_conn = self.connPool.get_conn()
        inf_db = inf_conn.create_database(self.dbName, ConflictType.Ignore)

        fp_mapping = os.path.join(get_project_base_directory(), "conf", self.mapping_file_name)
        if not os.path.exists(fp_mapping):
            raise Exception(f"Mapping file not found at {fp_mapping}")
        schema = json.load(open(fp_mapping))
        vector_name = f"q_{vector_size}_vec"
        schema[vector_name] = {"type": f"vector,{vector_size},float"}
        inf_table = inf_db.create_table(
            table_name,
            schema,
            ConflictType.Ignore,
        )
        inf_table.create_index(
            "q_vec_idx",
            IndexInfo(
                vector_name,
                IndexType.Hnsw,
                {
                    "M": "16",
                    "ef_construction": "50",
                    "metric": "cosine",
                    "encode": "lvq",
                },
            ),
            ConflictType.Ignore,
        )
        for field_name, field_info in schema.items():
            if field_info["type"] != "varchar" or "analyzer" not in field_info:
                continue
            analyzers = field_info["analyzer"]
            if isinstance(analyzers, str):
                analyzers = [analyzers]
            for analyzer in analyzers:
                inf_table.create_index(
                    f"ft_{re.sub(r'[^a-zA-Z0-9]', '_', field_name)}_{re.sub(r'[^a-zA-Z0-9]', '_', analyzer)}",
                    IndexInfo(field_name, IndexType.FullText, {"ANALYZER": analyzer}),
                    ConflictType.Ignore,
                )
        self.connPool.release_conn(inf_conn)
        _lineaje_payload = f"INFINITY created table {table_name}, vector size {vector_size}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnectionBase.create_idx).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8481d10ec80aef04c9d8d34224147ea8e499f5a392b918bb06be24f2bc51b690'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8481d10ec80aef04c9d8d34224147ea8e499f5a392b918bb06be24f2bc51b690', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 272, 'function': 'InfinityConnectionBase.create_idx'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 272, 'function': 'create_idx', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)
        return True

    def delete_idx(self, index_name: str, dataset_id: str):
        table_name = f"{index_name}_{dataset_id}"
        inf_conn = self.connPool.get_conn()
        db_instance = inf_conn.get_database(self.dbName)
        db_instance.drop_table(table_name, ConflictType.Ignore)
        self.connPool.release_conn(inf_conn)
        _lineaje_payload = f"INFINITY dropped table {table_name}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnectionBase.delete_idx).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:87a8ea29c590cfee4728e977a1f74c6376e29d157090c342f10e4d9be02f02d9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:87a8ea29c590cfee4728e977a1f74c6376e29d157090c342f10e4d9be02f02d9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 281, 'function': 'InfinityConnectionBase.delete_idx'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 281, 'function': 'delete_idx', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)

    def index_exist(self, index_name: str, dataset_id: str) -> bool:
        table_name = f"{index_name}_{dataset_id}"
        try:
            inf_conn = self.connPool.get_conn()
            db_instance = inf_conn.get_database(self.dbName)
            _ = db_instance.get_table(table_name)
            self.connPool.release_conn(inf_conn)
            return True
        except Exception as e:
            _lineaje_payload = f"INFINITY indexExist {str(e)}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnectionBase.index_exist).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b0a61834f4692038767e8994a26c9e84ae77f1dc070515e84730480088ae125e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b0a61834f4692038767e8994a26c9e84ae77f1dc070515e84730480088ae125e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 292, 'function': 'InfinityConnectionBase.index_exist'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 292, 'function': 'index_exist', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.warning(_lineaje_payload)
        return False

    """
    CRUD operations
    """

    @abstractmethod
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
        dataset_ids: list[str],
        agg_fields: list[str] | None = None,
        rank_feature: dict | None = None,
    ) -> tuple[pd.DataFrame, int]:
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def get(self, doc_id: str, index_name: str, knowledgebase_ids: list[str]) -> dict | None:
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def insert(self, documents: list[dict], index_name: str, dataset_ids: str = None) -> list[str]:
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def update(self, condition: dict, new_value: dict, index_name: str, dataset_id: str) -> bool:
        raise NotImplementedError("Not implemented")

    def delete(self, condition: dict, index_name: str, dataset_id: str) -> int:
        inf_conn = self.connPool.get_conn()
        db_instance = inf_conn.get_database(self.dbName)
        table_name = f"{index_name}_{dataset_id}"
        try:
            table_instance = db_instance.get_table(table_name)
        except Exception:
            _lineaje_payload = f"Skipped deleting from table {table_name} since the table doesn't exist."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnectionBase.delete).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:8a488e5b300dc800eafff1132900dcd09ed05d10c0a0f6f4897dbabd6118c48b'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8a488e5b300dc800eafff1132900dcd09ed05d10c0a0f6f4897dbabd6118c48b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 335, 'function': 'InfinityConnectionBase.delete'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 335, 'function': 'delete', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.warning(_lineaje_payload)
            return 0
        filter = self.equivalent_condition_to_str(condition, table_instance)
        _lineaje_payload = f"INFINITY delete table {table_name}, filter {filter}."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in InfinityConnectionBase.delete).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5ad4fe72d06d6c0cdfbab84884e0ff1b15b04bef3bd1f1c37eb6c2a8d409e132'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5ad4fe72d06d6c0cdfbab84884e0ff1b15b04bef3bd1f1c37eb6c2a8d409e132', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 338, 'function': 'InfinityConnectionBase.delete'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 338, 'function': 'delete', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.debug(_lineaje_payload)
        res = table_instance.delete(filter)
        self.connPool.release_conn(inf_conn)
        return res.deleted_rows

    """
    Helper functions for search result
    """

    def get_total(self, res: tuple[pd.DataFrame, int] | pd.DataFrame) -> int:
        if isinstance(res, tuple):
            return res[1]
        return len(res)

    def get_doc_ids(self, res: tuple[pd.DataFrame, int] | pd.DataFrame) -> list[str]:
        if isinstance(res, tuple):
            res = res[0]
        return list(res["id"])

    @abstractmethod
    def get_fields(self, res: tuple[pd.DataFrame, int] | pd.DataFrame, fields: list[str]) -> dict[str, dict]:
        raise NotImplementedError("Not implemented")

    def get_highlight(self, res: tuple[pd.DataFrame, int] | pd.DataFrame, keywords: list[str], field_name: str):
        if isinstance(res, tuple):
            res = res[0]
        ans = {}
        num_rows = len(res)
        column_id = res["id"]
        if field_name not in res:
            return {}
        for i in range(num_rows):
            id = column_id[i]
            txt = res[field_name][i]
            if re.search(r"<em>[^<>]+</em>", txt, flags=re.IGNORECASE | re.MULTILINE):
                ans[id] = txt
                continue
            txt = re.sub(r"[\r\n]", " ", txt, flags=re.IGNORECASE | re.MULTILINE)
            txt_list = []
            for t in re.split(r"[.?!;\n]", txt):
                if is_english([t]):
                    for w in keywords:
                        t = re.sub(
                            r"(^|[ .?/'\"\(\)!,:;-])(%s)([ .?/'\"\(\)!,:;-])" % re.escape(w),
                            r"\1<em>\2</em>\3",
                            t,
                            flags=re.IGNORECASE | re.MULTILINE,
                        )
                else:
                    for w in sorted(keywords, key=len, reverse=True):
                        t = re.sub(
                            re.escape(w),
                            f"<em>{w}</em>",
                            t,
                            flags=re.IGNORECASE | re.MULTILINE,
                        )
                if not re.search(r"<em>[^<>]+</em>", t, flags=re.IGNORECASE | re.MULTILINE):
                    continue
                txt_list.append(t)
            if txt_list:
                ans[id] = "...".join(txt_list)
            else:
                ans[id] = txt
        # LINEAJE: runtime guardrail checks `ans` as it flows from the agent to the user interface, before it leaves the application (in InfinityConnectionBase.get_highlight).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `ans` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8a9fc3912f50ed3a491f0374aaa845aea5466b9d598a999cb11b67b6d741732d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8a9fc3912f50ed3a491f0374aaa845aea5466b9d598a999cb11b67b6d741732d', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/infinity_conn_base.py', 'line': 401, 'function': 'InfinityConnectionBase.get_highlight'}, 'file': 'common/doc_store/infinity_conn_base.py', 'line': 401, 'function': 'get_highlight', 'agent_name': 'InfinityConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            ans = _gr_client.enforce(_gr_site, ans, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return ans

    def get_aggregation(self, res: tuple[pd.DataFrame, int] | pd.DataFrame, field_name: str):
        """
        Manual aggregation for tag fields since Infinity doesn't provide native aggregation
        """
        from collections import Counter

        # Extract DataFrame from result
        if isinstance(res, tuple):
            df, _ = res
        else:
            df = res

        if df.empty or field_name not in df.columns:
            return []

        # Aggregate tag counts
        tag_counter = Counter()

        for value in df[field_name]:
            if pd.isna(value) or not value:
                continue

            # Handle different tag formats
            if isinstance(value, str):
                # Split by ### for tag_kwd field or comma for other formats
                if field_name == "tag_kwd" and "###" in value:
                    tags = [tag.strip() for tag in value.split("###") if tag.strip()]
                else:
                    # Try comma separation as fallback
                    tags = [tag.strip() for tag in value.split(",") if tag.strip()]

                for tag in tags:
                    if tag:  # Only count non-empty tags
                        tag_counter[tag] += 1
            elif isinstance(value, list):
                # Handle list format
                for tag in value:
                    if tag and isinstance(tag, str):
                        tag_counter[tag.strip()] += 1

        # Return as list of [tag, count] pairs, sorted by count descending
        return [[tag, count] for tag, count in tag_counter.most_common()]

    """
    SQL
    """

    def sql(self, sql: str, fetch_size: int, format: str):
        raise NotImplementedError("Not implemented")
