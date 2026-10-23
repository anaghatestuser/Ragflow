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
import threading
from enum import Enum

from pydantic import BaseModel
from typing import Any
from common.config_utils import read_config
from urllib.parse import urlparse


class BaseConfig(BaseModel):
    id: int
    name: str
    host: str
    port: int
    service_type: str
    detail_func_name: str

    def to_dict(self) -> dict[str, Any]:
        return {'id': self.id, 'name': self.name, 'host': self.host, 'port': self.port,
                'service_type': self.service_type}


class ServiceConfigs:
    configs = list[BaseConfig]

    def __init__(self):
        self.configs = []
        self.lock = threading.Lock()


SERVICE_CONFIGS = ServiceConfigs


class ServiceType(Enum):
    METADATA = "metadata"
    RETRIEVAL = "retrieval"
    MESSAGE_QUEUE = "message_queue"
    RAGFLOW_SERVER = "ragflow_server"
    TASK_EXECUTOR = "task_executor"
    FILE_STORE = "file_store"


class MetaConfig(BaseConfig):
    meta_type: str

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if 'extra' not in result:
            result['extra'] = dict()
        extra_dict = result['extra'].copy()
        extra_dict['meta_type'] = self.meta_type
        result['extra'] = extra_dict
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in MetaConfig.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3128d6543bf99a76cf777c1b52ebe53ea0eb7fd846d4f304c250aeaf920cdaee'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3128d6543bf99a76cf777c1b52ebe53ea0eb7fd846d4f304c250aeaf920cdaee', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 71, 'function': 'MetaConfig.to_dict'}, 'file': 'admin/server/config.py', 'line': 71, 'function': 'to_dict', 'agent_name': 'MetaConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result


class MySQLConfig(MetaConfig):
    username: str
    password: str

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if 'extra' not in result:
            result['extra'] = dict()
        extra_dict = result['extra'].copy()
        extra_dict['username'] = self.username
        extra_dict['password'] = self.password
        result['extra'] = extra_dict
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in MySQLConfig.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9ba29aed153284a71debeccdc335b63e5174d94d89566a8e01a48b9258252c70'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9ba29aed153284a71debeccdc335b63e5174d94d89566a8e01a48b9258252c70', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 86, 'function': 'MySQLConfig.to_dict'}, 'file': 'admin/server/config.py', 'line': 86, 'function': 'to_dict', 'agent_name': 'MySQLConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result


class PostgresConfig(MetaConfig):

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if 'extra' not in result:
            result['extra'] = dict()
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in PostgresConfig.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6de8a02afe035400f85d06873f348d94bd7de3a68b7e68245d5ee62f4191f45c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6de8a02afe035400f85d06873f348d94bd7de3a68b7e68245d5ee62f4191f45c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 95, 'function': 'PostgresConfig.to_dict'}, 'file': 'admin/server/config.py', 'line': 95, 'function': 'to_dict', 'agent_name': 'PostgresConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result


class RetrievalConfig(BaseConfig):
    retrieval_type: str

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if 'extra' not in result:
            result['extra'] = dict()
        extra_dict = result['extra'].copy()
        extra_dict['retrieval_type'] = self.retrieval_type
        result['extra'] = extra_dict
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in RetrievalConfig.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:009b031852ce8c661ec7ddf9ccf5446795d742b9af2e32b9ea1ce5a98d5afe61'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:009b031852ce8c661ec7ddf9ccf5446795d742b9af2e32b9ea1ce5a98d5afe61', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 108, 'function': 'RetrievalConfig.to_dict'}, 'file': 'admin/server/config.py', 'line': 108, 'function': 'to_dict', 'agent_name': 'RetrievalConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result


class InfinityConfig(RetrievalConfig):
    db_name: str

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if 'extra' not in result:
            result['extra'] = dict()
        extra_dict = result['extra'].copy()
        extra_dict['db_name'] = self.db_name
        result['extra'] = extra_dict
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in InfinityConfig.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9df27fcb81977a44ae666457ca967be318265183201a9c0eed7d3f53a21a229d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9df27fcb81977a44ae666457ca967be318265183201a9c0eed7d3f53a21a229d', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 121, 'function': 'InfinityConfig.to_dict'}, 'file': 'admin/server/config.py', 'line': 121, 'function': 'to_dict', 'agent_name': 'InfinityConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result


class ElasticsearchConfig(RetrievalConfig):
    username: str
    password: str

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if 'extra' not in result:
            result['extra'] = dict()
        extra_dict = result['extra'].copy()
        extra_dict['username'] = self.username
        extra_dict['password'] = self.password
        result['extra'] = extra_dict
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in ElasticsearchConfig.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:06980e6dbc998172fed0f04967162fef9d234bade972475111b3f5e431d11e9c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:06980e6dbc998172fed0f04967162fef9d234bade972475111b3f5e431d11e9c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 136, 'function': 'ElasticsearchConfig.to_dict'}, 'file': 'admin/server/config.py', 'line': 136, 'function': 'to_dict', 'agent_name': 'ElasticsearchConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result


class MessageQueueConfig(BaseConfig):
    mq_type: str

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if 'extra' not in result:
            result['extra'] = dict()
        extra_dict = result['extra'].copy()
        extra_dict['mq_type'] = self.mq_type
        result['extra'] = extra_dict
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in MessageQueueConfig.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e926ba682303d048ac89c1cb762ab2919d05faf59b50b6b1f1a250673a531ed0'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e926ba682303d048ac89c1cb762ab2919d05faf59b50b6b1f1a250673a531ed0', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 149, 'function': 'MessageQueueConfig.to_dict'}, 'file': 'admin/server/config.py', 'line': 149, 'function': 'to_dict', 'agent_name': 'MessageQueueConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result


class RedisConfig(MessageQueueConfig):
    database: int
    password: str

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if 'extra' not in result:
            result['extra'] = dict()
        extra_dict = result['extra'].copy()
        extra_dict['database'] = self.database
        extra_dict['password'] = self.password
        result['extra'] = extra_dict
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in RedisConfig.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:28ecebe0d9f06cbbaee9ebe461fa9e748c394bb7f174b0c00a0c60102b021e63'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:28ecebe0d9f06cbbaee9ebe461fa9e748c394bb7f174b0c00a0c60102b021e63', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 164, 'function': 'RedisConfig.to_dict'}, 'file': 'admin/server/config.py', 'line': 164, 'function': 'to_dict', 'agent_name': 'RedisConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result


class RabbitMQConfig(MessageQueueConfig):

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if 'extra' not in result:
            result['extra'] = dict()
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in RabbitMQConfig.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:71d56b21c3c2a7858aee74e98e1df8ffc7f4a78c055c48b4d2cbf8a197bfceae'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:71d56b21c3c2a7858aee74e98e1df8ffc7f4a78c055c48b4d2cbf8a197bfceae', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 173, 'function': 'RabbitMQConfig.to_dict'}, 'file': 'admin/server/config.py', 'line': 173, 'function': 'to_dict', 'agent_name': 'RabbitMQConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result


class RAGFlowServerConfig(BaseConfig):

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if 'extra' not in result:
            result['extra'] = dict()
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowServerConfig.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:43d6691e6b1f749f9a8f8a7747db2e8c3737d8b0b4d0d909a2bf526d5ca6e49b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:43d6691e6b1f749f9a8f8a7747db2e8c3737d8b0b4d0d909a2bf526d5ca6e49b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 182, 'function': 'RAGFlowServerConfig.to_dict'}, 'file': 'admin/server/config.py', 'line': 182, 'function': 'to_dict', 'agent_name': 'RAGFlowServerConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result


class TaskExecutorConfig(BaseConfig):
    message_queue_type: str

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if 'extra' not in result:
            result['extra'] = dict()
        result['extra']['message_queue_type'] = self.message_queue_type
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in TaskExecutorConfig.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:29a2d295d8dbf672149b555d0ba834a5a0d3545e4c697b11a0b38ee0ecc99764'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:29a2d295d8dbf672149b555d0ba834a5a0d3545e4c697b11a0b38ee0ecc99764', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 193, 'function': 'TaskExecutorConfig.to_dict'}, 'file': 'admin/server/config.py', 'line': 193, 'function': 'to_dict', 'agent_name': 'TaskExecutorConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result


class FileStoreConfig(BaseConfig):
    store_type: str

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if 'extra' not in result:
            result['extra'] = dict()
        extra_dict = result['extra'].copy()
        extra_dict['store_type'] = self.store_type
        result['extra'] = extra_dict
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in FileStoreConfig.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d5093aea501af3c18db10bab276fee16fe24ad31e2fa8f8699e6bcb28e918aad'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d5093aea501af3c18db10bab276fee16fe24ad31e2fa8f8699e6bcb28e918aad', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 206, 'function': 'FileStoreConfig.to_dict'}, 'file': 'admin/server/config.py', 'line': 206, 'function': 'to_dict', 'agent_name': 'FileStoreConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result


class MinioConfig(FileStoreConfig):
    user: str
    password: str

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if 'extra' not in result:
            result['extra'] = dict()
        extra_dict = result['extra'].copy()
        extra_dict['user'] = self.user
        extra_dict['password'] = self.password
        result['extra'] = extra_dict
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in MinioConfig.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8f635337d16881db046300bee18e6399139b64aa54ee11f1f951c6d6522f2170'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8f635337d16881db046300bee18e6399139b64aa54ee11f1f951c6d6522f2170', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 221, 'function': 'MinioConfig.to_dict'}, 'file': 'admin/server/config.py', 'line': 221, 'function': 'to_dict', 'agent_name': 'MinioConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result


def load_configurations(config_path: str) -> list[BaseConfig]:
    raw_configs = read_config(config_path)
    configurations = []
    ragflow_count = 0
    id_count = 0
    for k, v in raw_configs.items():
        match k:
            case "ragflow":
                name: str = f'ragflow_{ragflow_count}'
                host: str = v['host']
                http_port: int = v['http_port']
                config = RAGFlowServerConfig(id=id_count, name=name, host=host, port=http_port,
                                             service_type="ragflow_server",
                                             detail_func_name="check_ragflow_server_alive")
                configurations.append(config)
                id_count += 1
            case "es":
                name: str = 'elasticsearch'
                url = v['hosts']
                parsed = urlparse(url)
                host: str = parsed.hostname
                port: int = parsed.port
                username: str = v.get('username')
                password: str = v.get('password')
                config = ElasticsearchConfig(id=id_count, name=name, host=host, port=port, service_type="retrieval",
                                             retrieval_type="elasticsearch",
                                             username=username, password=password,
                                             detail_func_name="get_es_cluster_stats")
                configurations.append(config)
                id_count += 1

            case "infinity":
                name: str = 'infinity'
                url = v['uri']
                parts = url.split(':', 1)
                host = parts[0]
                port = int(parts[1])
                database: str = v.get('db_name', 'default_db')
                config = InfinityConfig(id=id_count, name=name, host=host, port=port, service_type="retrieval",
                                        retrieval_type="infinity",
                                        db_name=database, detail_func_name="get_infinity_status")
                configurations.append(config)
                id_count += 1
            case "minio":
                name: str = 'minio'
                url = v['host']
                parts = url.split(':', 1)
                host = parts[0]
                port = int(parts[1])
                user = v.get('user')
                password = v.get('password')
                config = MinioConfig(id=id_count, name=name, host=host, port=port, user=user, password=password,
                                     service_type="file_store",
                                     store_type="minio", detail_func_name="check_minio_alive")
                configurations.append(config)
                id_count += 1
            case "redis":
                name: str = 'redis'
                url = v['host']
                parts = url.split(':', 1)
                host = parts[0]
                port = int(parts[1])
                password = v.get('password')
                db: int = v.get('db')
                config = RedisConfig(id=id_count, name=name, host=host, port=port, password=password, database=db,
                                     service_type="message_queue", mq_type="redis", detail_func_name="get_redis_info")
                configurations.append(config)
                id_count += 1
            case "mysql":
                name: str = 'mysql'
                host: str = v.get('host')
                port: int = v.get('port')
                username = v.get('user')
                password = v.get('password')
                config = MySQLConfig(id=id_count, name=name, host=host, port=port, username=username, password=password,
                                     service_type="meta_data", meta_type="mysql", detail_func_name="get_mysql_status")
                configurations.append(config)
                id_count += 1
            case "admin":
                pass
            case "task_executor":
                name: str = 'task_executor'
                host: str = v.get('host', '')
                port: int = v.get('port', 0)
                message_queue_type: str = v.get('message_queue_type')
                config = TaskExecutorConfig(id=id_count, name=name, host=host, port=port, message_queue_type=message_queue_type,
                                            service_type="task_executor", detail_func_name="check_task_executor_alive")
                configurations.append(config)
                id_count += 1
            case _:
                _lineaje_payload = f"Unknown configuration key: {k}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in load_configurations).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:c717843afc0329a0a31877dbacd3b6bf3d1fed18e19367c0f5e0e0495db859fd'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c717843afc0329a0a31877dbacd3b6bf3d1fed18e19367c0f5e0e0495db859fd', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 314, 'function': 'load_configurations'}, 'file': 'admin/server/config.py', 'line': 314, 'function': 'load_configurations', 'agent_name': 'load_configurations', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                continue

    # LINEAJE: runtime guardrail checks `configurations` as it flows from the agent to the user interface, before it leaves the application (in load_configurations).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `configurations` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:588c7dbc883e1b09a851728b6ad7d03f1b484645495075f414284d999154afdd'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:588c7dbc883e1b09a851728b6ad7d03f1b484645495075f414284d999154afdd', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/config.py', 'line': 317, 'function': 'load_configurations'}, 'file': 'admin/server/config.py', 'line': 317, 'function': 'load_configurations', 'agent_name': 'load_configurations', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        configurations = _gr_client.enforce(_gr_site, configurations, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return configurations
