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
from werkzeug.security import check_password_hash
from common.constants import ActiveEnum
from api.db.services import UserService
from api.db.joint_services.user_account_service import create_new_user, delete_user_data
from api.db.services.canvas_service import UserCanvasService
from api.db.services.user_service import TenantService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.utils.crypt import decrypt
from api.utils import health_utils

from api.common.exceptions import AdminException, UserAlreadyExistsError, UserNotFoundError
from config import SERVICE_CONFIGS


class UserMgr:
    @staticmethod
    def get_all_users():
        users = UserService.get_all_users()
        result = []
        for user in users:
            result.append({
                'email': user.email,
                'nickname': user.nickname,
                'create_date': user.create_date,
                'is_active': user.is_active,
                'is_superuser': user.is_superuser,
            })
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in UserMgr.get_all_users).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:7a8d75e9c371b397872e198a8b0c39a7fd8923de9ea131f248ef6aff33374fa3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7a8d75e9c371b397872e198a8b0c39a7fd8923de9ea131f248ef6aff33374fa3', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/services.py', 'line': 45, 'function': 'UserMgr.get_all_users'}, 'file': 'admin/server/services.py', 'line': 45, 'function': 'get_all_users', 'agent_name': 'UserMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result

    @staticmethod
    def get_user_details(username):
        # use email to query
        users = UserService.query_user_by_email(username)
        result = []
        for user in users:
            result.append({
                'avatar': user.avatar,
                'email': user.email,
                'language': user.language,
                'last_login_time': user.last_login_time,
                'is_active': user.is_active,
                'is_anonymous': user.is_anonymous,
                'login_channel': user.login_channel,
                'status': user.status,
                'is_superuser': user.is_superuser,
                'create_date': user.create_date,
                'update_date': user.update_date
            })
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in UserMgr.get_user_details).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:326b58eaebe359d69626c824a5440f9717c00db238245b39bb651c0107932cd6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:326b58eaebe359d69626c824a5440f9717c00db238245b39bb651c0107932cd6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/services.py', 'line': 66, 'function': 'UserMgr.get_user_details'}, 'file': 'admin/server/services.py', 'line': 66, 'function': 'get_user_details', 'agent_name': 'UserMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result

    @staticmethod
    def create_user(username, password, role="user") -> dict:
        # Validate the email address
        if not re.match(r"^[\w\._-]+@([\w_-]+\.)+[\w-]{2,}$", username):
            raise AdminException(f"Invalid email address: {username}!")
        # Check if the email address is already used
        if UserService.query(email=username):
            raise UserAlreadyExistsError(username)
        # Construct user info data
        user_info_dict = {
            "email": username,
            "nickname": "",  # ask user to edit it manually in settings.
            "password": decrypt(password),
            "login_channel": "password",
            "is_superuser": role == "admin",
        }
        return create_new_user(user_info_dict)

    @staticmethod
    def delete_user(username):
        # use email to delete
        user_list = UserService.query_user_by_email(username)
        if not user_list:
            raise UserNotFoundError(username)
        if len(user_list) > 1:
            raise AdminException(f"Exist more than 1 user: {username}!")
        usr = user_list[0]
        return delete_user_data(usr.id)

    @staticmethod
    def update_user_password(username, new_password) -> str:
        # use email to find user. check exist and unique.
        user_list = UserService.query_user_by_email(username)
        if not user_list:
            raise UserNotFoundError(username)
        elif len(user_list) > 1:
            raise AdminException(f"Exist more than 1 user: {username}!")
        # check new_password different from old.
        usr = user_list[0]
        psw = decrypt(new_password)
        if check_password_hash(usr.password, psw):
            return "Same password, no need to update!"
        # update password
        UserService.update_user_password(usr.id, psw)
        return "Password updated successfully!"

    @staticmethod
    def update_user_activate_status(username, activate_status: str):
        # use email to find user. check exist and unique.
        user_list = UserService.query_user_by_email(username)
        if not user_list:
            raise UserNotFoundError(username)
        elif len(user_list) > 1:
            raise AdminException(f"Exist more than 1 user: {username}!")
        # check activate status different from new
        usr = user_list[0]
        # format activate_status before handle
        _activate_status = activate_status.lower()
        target_status = {
            'on': ActiveEnum.ACTIVE.value,
            'off': ActiveEnum.INACTIVE.value,
        }.get(_activate_status)
        # LINEAJE: runtime guardrail checks `target_status` as it flows from an external API to the agent, after the tool returns (in UserMgr.update_user_activate_status).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `target_status` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f92a2a9512437bd7ebe734b26b42939f674707e01bb85d28e6afc4106a719557'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f92a2a9512437bd7ebe734b26b42939f674707e01bb85d28e6afc4106a719557', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/services.py', 'line': 126, 'function': 'UserMgr.update_user_activate_status'}, 'file': 'admin/server/services.py', 'line': 126, 'function': 'update_user_activate_status', 'agent_name': 'UserMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            target_status = _gr_client.enforce(_gr_site, target_status, content_type='application/json', variable_name='target_status', source_file=__file__, before_line=126)
        except _gr_client.GuardrailUnavailableError:
            pass
        if not target_status:
            raise AdminException(f"Invalid activate_status: {activate_status}")
        if target_status == usr.is_active:
            return f"User activate status is already {_activate_status}!"
        # update is_active
        UserService.update_user(usr.id, {"is_active": target_status})
        return f"Turn {_activate_status} user activate status successfully!"


class UserServiceMgr:

    @staticmethod
    def get_user_datasets(username):
        # use email to find user.
        user_list = UserService.query_user_by_email(username)
        if not user_list:
            raise UserNotFoundError(username)
        elif len(user_list) > 1:
            raise AdminException(f"Exist more than 1 user: {username}!")
        # find tenants
        usr = user_list[0]
        tenants = TenantService.get_joined_tenants_by_user_id(usr.id)
        tenant_ids = [m["tenant_id"] for m in tenants]
        # filter permitted kb and owned kb
        return KnowledgebaseService.get_all_kb_by_tenant_ids(tenant_ids, usr.id)

    @staticmethod
    def get_user_agents(username):
        # use email to find user.
        user_list = UserService.query_user_by_email(username)
        if not user_list:
            raise UserNotFoundError(username)
        elif len(user_list) > 1:
            raise AdminException(f"Exist more than 1 user: {username}!")
        # find tenants
        usr = user_list[0]
        tenants = TenantService.get_joined_tenants_by_user_id(usr.id)
        tenant_ids = [m["tenant_id"] for m in tenants]
        # filter permitted agents and owned agents
        res = UserCanvasService.get_all_agents_by_tenant_ids(tenant_ids, usr.id)
        return [{
            'title': r['title'],
            'permission': r['permission'],
            'canvas_category': r['canvas_category'].split('_')[0],
            'avatar': r['avatar']
        } for r in res]


class ServiceMgr:

    @staticmethod
    def get_all_services():
        result = []
        configs = SERVICE_CONFIGS.configs
        for service_id, config in enumerate(configs):
            config_dict = config.to_dict()
            try:
                service_detail = ServiceMgr.get_service_details(service_id)
                if "status" in service_detail:
                    config_dict['status'] = service_detail['status']
                else:
                    config_dict['status'] = 'timeout'
            except Exception as e:
                _lineaje_payload = f"Can't get service details, error: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ServiceMgr.get_all_services).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:7d4c00cca4e16501d09fd7f4c9ac215e743c39ead93ee161b76b35a4f12438a5'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7d4c00cca4e16501d09fd7f4c9ac215e743c39ead93ee161b76b35a4f12438a5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/services.py', 'line': 193, 'function': 'ServiceMgr.get_all_services'}, 'file': 'admin/server/services.py', 'line': 193, 'function': 'get_all_services', 'agent_name': 'ServiceMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                config_dict['status'] = 'timeout'
            if not config_dict['host']:
                config_dict['host'] = '-'
            if not config_dict['port']:
                config_dict['port'] = '-'
            result.append(config_dict)
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in ServiceMgr.get_all_services).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6321d8690a4d8698476df7390ef65020d1327dee80e670fc4353d47f0efbdbc7'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6321d8690a4d8698476df7390ef65020d1327dee80e670fc4353d47f0efbdbc7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/services.py', 'line': 200, 'function': 'ServiceMgr.get_all_services'}, 'file': 'admin/server/services.py', 'line': 200, 'function': 'get_all_services', 'agent_name': 'ServiceMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result

    @staticmethod
    def get_services_by_type(service_type_str: str):
        raise AdminException("get_services_by_type: not implemented")

    @staticmethod
    def get_service_details(service_id: int):
        service_idx = int(service_id)
        configs = SERVICE_CONFIGS.configs
        if service_idx < 0 or service_idx >= len(configs):
            raise AdminException(f"invalid service_index: {service_idx}")

        service_config = configs[service_idx]
        service_info = {'name': service_config.name, 'detail_func_name': service_config.detail_func_name}

        detail_func = getattr(health_utils, service_info.get('detail_func_name'))
        res = detail_func()
        res.update({'service_name': service_info.get('name')})
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in ServiceMgr.get_service_details).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:0127ecca41915bf670439a862aebc2784cb65bb5c3e6868558862d202b91d5da'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0127ecca41915bf670439a862aebc2784cb65bb5c3e6868558862d202b91d5da', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/services.py', 'line': 219, 'function': 'ServiceMgr.get_service_details'}, 'file': 'admin/server/services.py', 'line': 219, 'function': 'get_service_details', 'agent_name': 'ServiceMgr', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    @staticmethod
    def shutdown_service(service_id: int):
        raise AdminException("shutdown_service: not implemented")

    @staticmethod
    def restart_service(service_id: int):
        raise AdminException("restart_service: not implemented")
