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

from typing import Dict, Any

from api.common.exceptions import AdminException


class RoleMgr:
    @staticmethod
    def create_role(role_name: str, description: str):
        error_msg = f"not implement: create role: {role_name}, description: {description}"
        # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in RoleMgr.create_role).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b7cea94d54ad9da9f1d53af98ad9ab8f53d501f6a5e4232db4f311aff8feab94'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b7cea94d54ad9da9f1d53af98ad9ab8f53d501f6a5e4232db4f311aff8feab94', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/roles.py', 'line': 27, 'function': 'RoleMgr.create_role'}, 'file': 'admin/server/roles.py', 'line': 27, 'function': 'create_role', 'agent_name': 'RoleMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(error_msg)
        raise AdminException(error_msg)

    @staticmethod
    def update_role_description(role_name: str, description: str) -> Dict[str, Any]:
        error_msg = f"not implement: update role: {role_name} with description: {description}"
        # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in RoleMgr.update_role_description).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:53bef9e81887658780256e487113d39607c9d4494845bf2dfcb87025a4220a63'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:53bef9e81887658780256e487113d39607c9d4494845bf2dfcb87025a4220a63', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/roles.py', 'line': 33, 'function': 'RoleMgr.update_role_description'}, 'file': 'admin/server/roles.py', 'line': 33, 'function': 'update_role_description', 'agent_name': 'RoleMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(error_msg)
        raise AdminException(error_msg)

    @staticmethod
    def delete_role(role_name: str) -> Dict[str, Any]:
        error_msg = f"not implement: drop role: {role_name}"
        # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in RoleMgr.delete_role).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:76b4c873652a8a60836e11b648d50422c690cf0c0fd7028459cd8fb1b38438f7'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:76b4c873652a8a60836e11b648d50422c690cf0c0fd7028459cd8fb1b38438f7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/roles.py', 'line': 39, 'function': 'RoleMgr.delete_role'}, 'file': 'admin/server/roles.py', 'line': 39, 'function': 'delete_role', 'agent_name': 'RoleMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(error_msg)
        raise AdminException(error_msg)

    @staticmethod
    def list_roles() -> Dict[str, Any]:
        error_msg = "not implement: list roles"
        # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in RoleMgr.list_roles).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f06ed93411685b8e8a411c3cee535d712d89186792ba0692368de18d3f13a35a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f06ed93411685b8e8a411c3cee535d712d89186792ba0692368de18d3f13a35a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/roles.py', 'line': 45, 'function': 'RoleMgr.list_roles'}, 'file': 'admin/server/roles.py', 'line': 45, 'function': 'list_roles', 'agent_name': 'RoleMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(error_msg)
        raise AdminException(error_msg)

    @staticmethod
    def get_role_permission(role_name: str) -> Dict[str, Any]:
        error_msg = f"not implement: show role {role_name}"
        # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in RoleMgr.get_role_permission).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:91a1f70c0494c57dc96602f85a2ac9f6c52265421b767621b471d5110dd55256'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:91a1f70c0494c57dc96602f85a2ac9f6c52265421b767621b471d5110dd55256', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/roles.py', 'line': 51, 'function': 'RoleMgr.get_role_permission'}, 'file': 'admin/server/roles.py', 'line': 51, 'function': 'get_role_permission', 'agent_name': 'RoleMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(error_msg)
        raise AdminException(error_msg)

    @staticmethod
    def grant_role_permission(role_name: str, actions: list, resource: str) -> Dict[str, Any]:
        error_msg = f"not implement: grant role {role_name} actions: {actions} on {resource}"
        # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in RoleMgr.grant_role_permission).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b48c816f779764dffe8405bc405934ddaa537b4664984dbeaf6d0cf84e26019d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b48c816f779764dffe8405bc405934ddaa537b4664984dbeaf6d0cf84e26019d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/roles.py', 'line': 57, 'function': 'RoleMgr.grant_role_permission'}, 'file': 'admin/server/roles.py', 'line': 57, 'function': 'grant_role_permission', 'agent_name': 'RoleMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(error_msg)
        raise AdminException(error_msg)

    @staticmethod
    def revoke_role_permission(role_name: str, actions: list, resource: str) -> Dict[str, Any]:
        error_msg = f"not implement: revoke role {role_name} actions: {actions} on {resource}"
        # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in RoleMgr.revoke_role_permission).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6986a8e11c411eaaa07dcef8982ebaeedc72a6f0b85c9052a17bf4fa8f21a618'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6986a8e11c411eaaa07dcef8982ebaeedc72a6f0b85c9052a17bf4fa8f21a618', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/roles.py', 'line': 63, 'function': 'RoleMgr.revoke_role_permission'}, 'file': 'admin/server/roles.py', 'line': 63, 'function': 'revoke_role_permission', 'agent_name': 'RoleMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(error_msg)
        raise AdminException(error_msg)

    @staticmethod
    def update_user_role(user_name: str, role_name: str) -> Dict[str, Any]:
        error_msg = f"not implement: update user role: {user_name} to role {role_name}"
        # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in RoleMgr.update_user_role).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ee8c171cf47abfe2f44ff8a83c0d117e13393630d71f8f51b23ba11d8a0430f3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ee8c171cf47abfe2f44ff8a83c0d117e13393630d71f8f51b23ba11d8a0430f3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/roles.py', 'line': 69, 'function': 'RoleMgr.update_user_role'}, 'file': 'admin/server/roles.py', 'line': 69, 'function': 'update_user_role', 'agent_name': 'RoleMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(error_msg)
        raise AdminException(error_msg)

    @staticmethod
    def get_user_permission(user_name: str) -> Dict[str, Any]:
        error_msg = f"not implement: get user permission: {user_name}"
        # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in RoleMgr.get_user_permission).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9d916245179f61e6d247740201545cd88db15db54070e695993e94ea442190da'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9d916245179f61e6d247740201545cd88db15db54070e695993e94ea442190da', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/roles.py', 'line': 75, 'function': 'RoleMgr.get_user_permission'}, 'file': 'admin/server/roles.py', 'line': 75, 'function': 'get_user_permission', 'agent_name': 'RoleMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(error_msg)
        raise AdminException(error_msg)
