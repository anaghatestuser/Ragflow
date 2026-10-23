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
import re
import json
import time
import os
from abc import abstractmethod

from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch_dsl import Index
from elastic_transport import ConnectionTimeout
from common.file_utils import get_project_base_directory
from common.misc_utils import convert_bytes
from common.doc_store.doc_store_base import DocStoreConnection, OrderByExpr, MatchExpr
from rag.nlp import is_english, rag_tokenizer
from common import settings

ATTEMPT_TIME = 2


class ESConnectionBase(DocStoreConnection):
    def __init__(self, mapping_file_name: str="mapping.json", logger_name: str='ragflow.es_conn'):
        self.logger = logging.getLogger(logger_name)

        self.info = {}
        _lineaje_payload = f"Use Elasticsearch {settings.ES['hosts']} as the doc engine."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.__init__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:507f64b504683df2201b677904804d56f9b9339d5ee0d36242586e47361a9b98'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:507f64b504683df2201b677904804d56f9b9339d5ee0d36242586e47361a9b98', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 41, 'function': 'ESConnectionBase.__init__'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 41, 'function': '__init__', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)
        for _ in range(ATTEMPT_TIME):
            try:
                if self._connect():
                    break
            except Exception as e:
                _lineaje_payload = f"{str(e)}. Waiting Elasticsearch {settings.ES['hosts']} to be healthy."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.__init__).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:6068d353219b2c586481946af72333e6df9585d1288eb69b39681621f745c013'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6068d353219b2c586481946af72333e6df9585d1288eb69b39681621f745c013', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 47, 'function': 'ESConnectionBase.__init__'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 47, 'function': '__init__', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.warning(_lineaje_payload)
                time.sleep(5)

        if not self.es.ping():
            msg = f"Elasticsearch {settings.ES['hosts']} is unhealthy in 120s."
            # LINEAJE: runtime guardrail checks `msg` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.__init__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f915f08df32a617bfe4de8997c022d35e32f3a2243fa7f3e77bfeb625c6fdd8e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f915f08df32a617bfe4de8997c022d35e32f3a2243fa7f3e77bfeb625c6fdd8e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 52, 'function': 'ESConnectionBase.__init__'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 52, 'function': '__init__', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                msg = _gr_client.enforce(_gr_site, msg, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.error(msg)
            raise Exception(msg)
        v = self.info.get("version", {"number": "8.11.3"})
        v = v["number"].split(".")[0]
        if int(v) < 8:
            msg = f"Elasticsearch version must be greater than or equal to 8, current version: {v}"
            # LINEAJE: runtime guardrail checks `msg` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.__init__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:20164690ac990d074ae0cd694ceaa813e21a039dcd63b8542d2d165a71989d98'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:20164690ac990d074ae0cd694ceaa813e21a039dcd63b8542d2d165a71989d98', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 58, 'function': 'ESConnectionBase.__init__'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 58, 'function': '__init__', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                msg = _gr_client.enforce(_gr_site, msg, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.error(msg)
            raise Exception(msg)
        fp_mapping = os.path.join(get_project_base_directory(), "conf", mapping_file_name)
        if not os.path.exists(fp_mapping):
            msg = f"Elasticsearch mapping file not found at {fp_mapping}"
            # LINEAJE: runtime guardrail checks `msg` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.__init__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d8b0ad397485645e1b00457b7310d01689a6ccdc5cb34a7975288a9a3f79e684'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d8b0ad397485645e1b00457b7310d01689a6ccdc5cb34a7975288a9a3f79e684', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 63, 'function': 'ESConnectionBase.__init__'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 63, 'function': '__init__', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                msg = _gr_client.enforce(_gr_site, msg, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.error(msg)
            raise Exception(msg)
        self.mapping = json.load(open(fp_mapping, "r"))
        _lineaje_payload = f"Elasticsearch {settings.ES['hosts']} is healthy."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.__init__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e37621a1602c4a4c80b67b0e6c290fc62d6ca924329fbbc33b43a0724255bce8'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e37621a1602c4a4c80b67b0e6c290fc62d6ca924329fbbc33b43a0724255bce8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 66, 'function': 'ESConnectionBase.__init__'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 66, 'function': '__init__', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)

    def _connect(self):
        self.es = Elasticsearch(
            settings.ES["hosts"].split(","),
            basic_auth=(settings.ES["username"], settings.ES[
                "password"]) if "username" in settings.ES and "password" in settings.ES else None,
            verify_certs= settings.ES.get("verify_certs", False),
            timeout=600 )
        if self.es:
            self.info = self.es.info()
            return True
        return False

    """
    Database operations
    """

    def db_type(self) -> str:
        return "elasticsearch"

    def health(self) -> dict:
        health_dict = dict(self.es.cluster.health())
        health_dict["type"] = "elasticsearch"
        # LINEAJE: runtime guardrail checks `health_dict` as it flows from the agent to the user interface, before it leaves the application (in ESConnectionBase.health).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `health_dict` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b29129e3cea092be953ad6a5ee2e39be677e901942aaca656ee931bb5a3a40e3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b29129e3cea092be953ad6a5ee2e39be677e901942aaca656ee931bb5a3a40e3', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 90, 'function': 'ESConnectionBase.health'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 90, 'function': 'health', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            health_dict = _gr_client.enforce(_gr_site, health_dict, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return health_dict

    def get_cluster_stats(self):
        """
        curl -XGET "http://{es_host}/_cluster/stats" -H "kbn-xsrf: reporting" to view raw stats.
        """
        raw_stats = self.es.cluster.stats()
        _lineaje_payload = f"ESConnection.get_cluster_stats: {raw_stats}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.get_cluster_stats).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:27abd14e3a5287aac129a89de2e24ac5fcf1577fecf3225d5e63378bd0709352'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:27abd14e3a5287aac129a89de2e24ac5fcf1577fecf3225d5e63378bd0709352', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 97, 'function': 'ESConnectionBase.get_cluster_stats'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 97, 'function': 'get_cluster_stats', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.debug(_lineaje_payload)
        try:
            res = {
                'cluster_name': raw_stats['cluster_name'],
                'status': raw_stats['status']
            }
            indices_status = raw_stats['indices']
            res.update({
                'indices': indices_status['count'],
                'indices_shards': indices_status['shards']['total']
            })
            doc_info = indices_status['docs']
            res.update({
                'docs': doc_info['count'],
                'docs_deleted': doc_info['deleted']
            })
            store_info = indices_status['store']
            res.update({
                'store_size': convert_bytes(store_info['size_in_bytes']),
                'total_dataset_size': convert_bytes(store_info['total_data_set_size_in_bytes'])
            })
            mappings_info = indices_status['mappings']
            res.update({
                'mappings_fields': mappings_info['total_field_count'],
                'mappings_deduplicated_fields': mappings_info['total_deduplicated_field_count'],
                'mappings_deduplicated_size': convert_bytes(mappings_info['total_deduplicated_mapping_size_in_bytes'])
            })
            node_info = raw_stats['nodes']
            res.update({
                'nodes': node_info['count']['total'],
                'nodes_version': node_info['versions'],
                'os_mem': convert_bytes(node_info['os']['mem']['total_in_bytes']),
                'os_mem_used': convert_bytes(node_info['os']['mem']['used_in_bytes']),
                'os_mem_used_percent': node_info['os']['mem']['used_percent'],
                'jvm_versions': node_info['jvm']['versions'][0]['vm_version'],
                'jvm_heap_used': convert_bytes(node_info['jvm']['mem']['heap_used_in_bytes']),
                'jvm_heap_max': convert_bytes(node_info['jvm']['mem']['heap_max_in_bytes'])
            })
            # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in ESConnectionBase.get_cluster_stats).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f94276442320624c06d6ffa5f393ea4e25c250791da448e5ecd166cb7ae6edc2'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f94276442320624c06d6ffa5f393ea4e25c250791da448e5ecd166cb7ae6edc2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 135, 'function': 'ESConnectionBase.get_cluster_stats'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 135, 'function': 'get_cluster_stats', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return res

        except Exception as e:
            _lineaje_payload = f"ESConnection.get_cluster_stats: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.get_cluster_stats).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9eb64b015a05f2e0bd837ead21c6c263ddc830774a42e0d8a2789a66bf0352bc'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9eb64b015a05f2e0bd837ead21c6c263ddc830774a42e0d8a2789a66bf0352bc', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 138, 'function': 'ESConnectionBase.get_cluster_stats'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 138, 'function': 'get_cluster_stats', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.exception(_lineaje_payload)
            return None

    """
    Table operations
    """

    def create_idx(self, index_name: str, dataset_id: str, vector_size: int):
        if self.index_exist(index_name, dataset_id):
            return True
        try:
            from elasticsearch.client import IndicesClient
            return IndicesClient(self.es).create(index=index_name,
                                                 settings=self.mapping["settings"],
                                                 mappings=self.mapping["mappings"])
        except Exception:
            _lineaje_payload = "ESConnection.createIndex error %s" % index_name
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.create_idx).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:326017a6b1276005cd80576a8b1afab157e6e36feffc224e24f57c0174b97c6a'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:326017a6b1276005cd80576a8b1afab157e6e36feffc224e24f57c0174b97c6a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 154, 'function': 'ESConnectionBase.create_idx'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 154, 'function': 'create_idx', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.exception(_lineaje_payload)

    def delete_idx(self, index_name: str, dataset_id: str):
        if len(dataset_id) > 0:
            # The index need to be alive after any kb deletion since all kb under this tenant are in one index.
            return
        try:
            self.es.indices.delete(index=index_name, allow_no_indices=True)
        except NotFoundError:
            pass
        except Exception:
            _lineaje_payload = "ESConnection.deleteIdx error %s" % index_name
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.delete_idx).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:92c7335c7971aff934191c07dc7277862142cc1a12a682ffd6f335dd7eb0200d'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:92c7335c7971aff934191c07dc7277862142cc1a12a682ffd6f335dd7eb0200d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 165, 'function': 'ESConnectionBase.delete_idx'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 165, 'function': 'delete_idx', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.exception(_lineaje_payload)

    def index_exist(self, index_name: str, dataset_id: str = None) -> bool:
        s = Index(index_name, self.es)
        for i in range(ATTEMPT_TIME):
            try:
                return s.exists()
            except ConnectionTimeout:
                _lineaje_payload = "ES request timeout"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.index_exist).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:3bf6fa0e21481e50fbef124fc2d6047f2b7e6f829d4f960185285792e727835b'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3bf6fa0e21481e50fbef124fc2d6047f2b7e6f829d4f960185285792e727835b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 173, 'function': 'ESConnectionBase.index_exist'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 173, 'function': 'index_exist', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
                # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.index_exist).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:0c90c9704b9dfb742ef823fcfc58330ef07714263337a38f71fa3ab44f963f35'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0c90c9704b9dfb742ef823fcfc58330ef07714263337a38f71fa3ab44f963f35', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 178, 'function': 'ESConnectionBase.index_exist'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 178, 'function': 'index_exist', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    e = _gr_client.enforce(_gr_site, e, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.exception(e)
                break
        return False

    """
    CRUD operations
    """

    def get(self, doc_id: str, index_name: str, dataset_ids: list[str]) -> dict | None:
        for i in range(ATTEMPT_TIME):
            try:
                res = self.es.get(index=index_name,
                                  id=doc_id, source=True, )
                if str(res.get("timed_out", "")).lower() == "true":
                    raise Exception("Es Timeout.")
                doc = res["_source"]
                doc["id"] = doc_id
                # LINEAJE: runtime guardrail checks `doc` as it flows from the agent to the user interface, before it leaves the application (in ESConnectionBase.get).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `doc` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:74719ab7979b67860c46605f7dc4b71011fd8c80938392b001128d0256ce1e57'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:74719ab7979b67860c46605f7dc4b71011fd8c80938392b001128d0256ce1e57', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 195, 'function': 'ESConnectionBase.get'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 195, 'function': 'get', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    doc = _gr_client.enforce(_gr_site, doc, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return doc
            except NotFoundError:
                return None
            except Exception as e:
                _lineaje_payload = f"ESConnection.get({doc_id}) got exception"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.get).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:204f17ef663eaf85b9e1d5d8c137723b8f765052cc148644bd59f2d45cbc7674'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:204f17ef663eaf85b9e1d5d8c137723b8f765052cc148644bd59f2d45cbc7674', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 199, 'function': 'ESConnectionBase.get'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 199, 'function': 'get', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.exception(_lineaje_payload)
                raise e
        _lineaje_payload = f"ESConnection.get timeout for {ATTEMPT_TIME} times!"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.get).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d54d56efd25743be67072289465c35a81767c814d3fa794cb5374743fce1fb7d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d54d56efd25743be67072289465c35a81767c814d3fa794cb5374743fce1fb7d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 201, 'function': 'ESConnectionBase.get'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 201, 'function': 'get', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.error(_lineaje_payload)
        raise Exception("ESConnection.get timeout.")

    @abstractmethod
    def search(
            self, select_fields: list[str],
            highlight_fields: list[str],
            condition: dict,
            match_expressions: list[MatchExpr],
            order_by: OrderByExpr,
            offset: int,
            limit: int,
            index_names: str | list[str],
            dataset_ids: list[str],
            agg_fields: list[str] | None = None,
            rank_feature: dict | None = None
    ):
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def insert(self, documents: list[dict], index_name: str, dataset_id: str = None) -> list[str]:
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def update(self, condition: dict, new_value: dict, index_name: str, dataset_id: str) -> bool:
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def delete(self, condition: dict, index_name: str, dataset_id: str) -> int:
        raise NotImplementedError("Not implemented")

    """
    Helper functions for search result
    """

    def get_total(self, res):
        if isinstance(res["hits"]["total"], type({})):
            return res["hits"]["total"]["value"]
        return res["hits"]["total"]

    def get_doc_ids(self, res):
        return [d["_id"] for d in res["hits"]["hits"]]

    def _get_source(self, res):
        rr = []
        for d in res["hits"]["hits"]:
            d["_source"]["id"] = d["_id"]
            d["_source"]["_score"] = d["_score"]
            rr.append(d["_source"])
        # LINEAJE: runtime guardrail checks `rr` as it flows from the agent to the user interface, before it leaves the application (in ESConnectionBase._get_source).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `rr` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:88b853298e2cbf633393379d8aa9216ad258db745c90056ab92afa7dcd8dbfe3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:88b853298e2cbf633393379d8aa9216ad258db745c90056ab92afa7dcd8dbfe3', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 250, 'function': 'ESConnectionBase._get_source'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 250, 'function': '_get_source', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            rr = _gr_client.enforce(_gr_site, rr, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return rr

    @abstractmethod
    def get_fields(self, res, fields: list[str]) -> dict[str, dict]:
        raise NotImplementedError("Not implemented")

    def get_highlight(self, res, keywords: list[str], field_name: str):
        ans = {}
        for d in res["hits"]["hits"]:
            highlights = d.get("highlight")
            if not highlights:
                continue
            txt = "...".join([a for a in list(highlights.items())[0][1]])
            if not is_english(txt.split()):
                ans[d["_id"]] = txt
                continue

            txt = d["_source"][field_name]
            txt = re.sub(r"[\r\n]", " ", txt, flags=re.IGNORECASE | re.MULTILINE)
            txt_list = []
            for t in re.split(r"[.?!;\n]", txt):
                for w in keywords:
                    t = re.sub(r"(^|[ .?/'\"\(\)!,:;-])(%s)([ .?/'\"\(\)!,:;-])" % re.escape(w), r"\1<em>\2</em>\3", t,
                               flags=re.IGNORECASE | re.MULTILINE)
                if not re.search(r"<em>[^<>]+</em>", t, flags=re.IGNORECASE | re.MULTILINE):
                    continue
                txt_list.append(t)
            ans[d["_id"]] = "...".join(txt_list) if txt_list else "...".join([a for a in list(highlights.items())[0][1]])

        # LINEAJE: runtime guardrail checks `ans` as it flows from the agent to the user interface, before it leaves the application (in ESConnectionBase.get_highlight).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `ans` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:34ceee38a11e0d5d3eb362386026670e8486bb736fdc9e0dfaed7c35d63fa446'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:34ceee38a11e0d5d3eb362386026670e8486bb736fdc9e0dfaed7c35d63fa446', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 279, 'function': 'ESConnectionBase.get_highlight'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 279, 'function': 'get_highlight', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            ans = _gr_client.enforce(_gr_site, ans, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return ans

    def get_aggregation(self, res, field_name: str):
        agg_field = "aggs_" + field_name
        if "aggregations" not in res or agg_field not in res["aggregations"]:
            return list()
        buckets = res["aggregations"][agg_field]["buckets"]
        return [(b["key"], b["doc_count"]) for b in buckets]

    """
    SQL
    """

    def sql(self, sql: str, fetch_size: int, format: str):
        _lineaje_payload = f"ESConnection.sql get sql: {sql}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.sql).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:dbfb96a938bbe29fc875b78e5c4ce12850be0fe5167167d90572b24e76879730'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dbfb96a938bbe29fc875b78e5c4ce12850be0fe5167167d90572b24e76879730', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 293, 'function': 'ESConnectionBase.sql'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 293, 'function': 'sql', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.debug(_lineaje_payload)
        sql = re.sub(r"[ `]+", " ", sql)
        sql = sql.replace("%", "")
        replaces = []
        for r in re.finditer(r" ([a-z_]+_l?tks)( like | ?= ?)'([^']+)'", sql):
            fld, v = r.group(1), r.group(3)
            match = " MATCH({}, '{}', 'operator=OR;minimum_should_match=30%') ".format(
                fld, rag_tokenizer.fine_grained_tokenize(rag_tokenizer.tokenize(v)))
            replaces.append(
                ("{}{}'{}'".format(
                    r.group(1),
                    r.group(2),
                    r.group(3)),
                 match))

        for p, r in replaces:
            sql = sql.replace(p, r, 1)
        _lineaje_payload = f"ESConnection.sql to es: {sql}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.sql).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a0397bd5062d580900c1ee70880e88c825e939dcaf93b9fbe76b18c3657b126e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a0397bd5062d580900c1ee70880e88c825e939dcaf93b9fbe76b18c3657b126e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 310, 'function': 'ESConnectionBase.sql'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 310, 'function': 'sql', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.debug(_lineaje_payload)

        for i in range(ATTEMPT_TIME):
            try:
                res = self.es.sql.query(body={"query": sql, "fetch_size": fetch_size}, format=format,
                                        request_timeout="2s")
                # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in ESConnectionBase.sql).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:593d4d16bd686c2d92f04afa661729bd1ff4ac741a4fc94973bb063e1b5443e7'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:593d4d16bd686c2d92f04afa661729bd1ff4ac741a4fc94973bb063e1b5443e7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 316, 'function': 'ESConnectionBase.sql'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 316, 'function': 'sql', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return res
            except ConnectionTimeout:
                _lineaje_payload = "ES request timeout"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.sql).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:da12a80594e79e1f989e8ed6d9c5010be01e52cf1fd4ddc087eaf79dd9161073'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:da12a80594e79e1f989e8ed6d9c5010be01e52cf1fd4ddc087eaf79dd9161073', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 318, 'function': 'ESConnectionBase.sql'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 318, 'function': 'sql', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
                _lineaje_payload = f"ESConnection.sql got exception. SQL:\n{sql}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.sql).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:75122cfbfcac2c00ad0409b1e0badd0f5f7728c50a2af61dd7278a1892ce7934'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:75122cfbfcac2c00ad0409b1e0badd0f5f7728c50a2af61dd7278a1892ce7934', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 323, 'function': 'ESConnectionBase.sql'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 323, 'function': 'sql', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.exception(_lineaje_payload)
                raise Exception(f"SQL error: {e}\n\nSQL: {sql}")
        _lineaje_payload = f"ESConnection.sql timeout for {ATTEMPT_TIME} times!"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ESConnectionBase.sql).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:cf282cbf6e20192c1889196b3535dc67f1acd71f70654ad96d07f04ba82eae6e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cf282cbf6e20192c1889196b3535dc67f1acd71f70654ad96d07f04ba82eae6e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/es_conn_base.py', 'line': 325, 'function': 'ESConnectionBase.sql'}, 'file': 'common/doc_store/es_conn_base.py', 'line': 325, 'function': 'sql', 'agent_name': 'ESConnectionBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.error(_lineaje_payload)
        return None
