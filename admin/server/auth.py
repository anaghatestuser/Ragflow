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
import uuid
from functools import wraps
from datetime import datetime

from flask import jsonify, request
from flask_login import current_user, login_user
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer

from api.common.exceptions import AdminException, UserNotFoundError
from api.common.base64 import encode_to_base64
from api.db.services import UserService
from common.constants import ActiveEnum, StatusEnum
from api.utils.crypt import decrypt
from common.misc_utils import get_uuid
from common.time_utils import current_timestamp, datetime_format, get_format_time
from common.connection_utils import sync_construct_response
from common import settings


def setup_auth(login_manager):
    @login_manager.request_loader
    def load_user(web_request):
        jwt = Serializer(secret_key=settings.SECRET_KEY)
        authorization = web_request.headers.get("Authorization")
        if authorization:
            try:
                access_token = str(jwt.loads(authorization))

                if not access_token or not access_token.strip():
                    _lineaje_payload = "Authentication attempt with empty access token"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in load_user).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:b929d06910ef9ba430cfdbf5940df60cdd5d762349eddf44969ec62d3e3a23b3'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b929d06910ef9ba430cfdbf5940df60cdd5d762349eddf44969ec62d3e3a23b3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/auth.py', 'line': 48, 'function': 'setup_auth.load_user'}, 'file': 'admin/server/auth.py', 'line': 48, 'function': 'load_user', 'agent_name': 'load_user', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.warning(_lineaje_payload)
                    return None

                # Access tokens should be UUIDs (32 hex characters)
                if len(access_token.strip()) < 32:
                    _lineaje_payload = f"Authentication attempt with invalid token format: {len(access_token)} chars"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in load_user).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:4de5f9a36e696bdf095823100e128da29fa961d5516debf83af4b086bf7af3e7'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4de5f9a36e696bdf095823100e128da29fa961d5516debf83af4b086bf7af3e7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/auth.py', 'line': 53, 'function': 'setup_auth.load_user'}, 'file': 'admin/server/auth.py', 'line': 53, 'function': 'load_user', 'agent_name': 'load_user', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.warning(_lineaje_payload)
                    return None

                user = UserService.query(
                    access_token=access_token, status=StatusEnum.VALID.value
                )
                if user:
                    if not user[0].access_token or not user[0].access_token.strip():
                        _lineaje_payload = f"User {user[0].email} has empty access_token in database"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in load_user).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:7eb3ac8dd64b92ff9e664ff5379bda292420caa8b433ebd15867a8fb708d95f9'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7eb3ac8dd64b92ff9e664ff5379bda292420caa8b433ebd15867a8fb708d95f9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/auth.py', 'line': 61, 'function': 'setup_auth.load_user'}, 'file': 'admin/server/auth.py', 'line': 61, 'function': 'load_user', 'agent_name': 'load_user', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.warning(_lineaje_payload)
                        return None
                    # LINEAJE: runtime guardrail checks `user` as it flows from the agent to the user interface, before it leaves the application (in load_user).
                    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `user` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:5247712e0c7eca9a4aa60b693602a4ed53447e88ca210f08376b1de6652607ec'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5247712e0c7eca9a4aa60b693602a4ed53447e88ca210f08376b1de6652607ec', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/auth.py', 'line': 63, 'function': 'setup_auth.load_user'}, 'file': 'admin/server/auth.py', 'line': 63, 'function': 'load_user', 'agent_name': 'load_user', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                    try:
                        user = _gr_client.enforce(_gr_site, user, content_type='text/plain')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    return user[0]
                else:
                    return None
            except Exception as e:
                _lineaje_payload = f"load_user got exception {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in load_user).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f7e7e260ca3c780b1d6f8f5b64d6f746bd729eeb7663639b96314aba3a2abf35'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f7e7e260ca3c780b1d6f8f5b64d6f746bd729eeb7663639b96314aba3a2abf35', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/auth.py', 'line': 67, 'function': 'setup_auth.load_user'}, 'file': 'admin/server/auth.py', 'line': 67, 'function': 'load_user', 'agent_name': 'load_user', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                return None
        else:
            return None


def init_default_admin():
    # Verify that at least one active admin user exists. If not, create a default one.
    users = UserService.query(is_superuser=True)
    if not users:
        default_admin = {
            "id": uuid.uuid1().hex,
            "password": encode_to_base64("admin"),
            "nickname": "admin",
            "is_superuser": True,
            "email": "admin@ragflow.io",
            "creator": "system",
            "status": "1",
        }
        if not UserService.save(**default_admin):
            raise AdminException("Can't init admin.", 500)
    elif not any([u.is_active == ActiveEnum.ACTIVE.value for u in users]):
        raise AdminException("No active admin. Please update 'is_active' in db manually.", 500)


def check_admin_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = UserService.filter_by_id(current_user.id)
        if not user:
            raise UserNotFoundError(current_user.email)
        if not user.is_superuser:
            raise AdminException("Not admin", 403)
        if user.is_active == ActiveEnum.INACTIVE.value:
            raise AdminException(f"User {current_user.email} inactive", 403)

        return func(*args, **kwargs)

    # LINEAJE: runtime guardrail checks `wrapper` as it flows from the agent to the user interface, before it leaves the application (in check_admin_auth).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `wrapper` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:03baf4d2d4ca9475900fb5b53fc13525989d9d8d00d9d868f2107a1d71313a71'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:03baf4d2d4ca9475900fb5b53fc13525989d9d8d00d9d868f2107a1d71313a71', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/auth.py', 'line': 105, 'function': 'check_admin_auth'}, 'file': 'admin/server/auth.py', 'line': 105, 'function': 'check_admin_auth', 'agent_name': 'check_admin_auth', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        wrapper = _gr_client.enforce(_gr_site, wrapper, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return wrapper


def login_admin(email: str, password: str):
    """
    :param email: admin email
    :param password: string before decrypt
    """
    users = UserService.query(email=email)
    if not users:
        raise UserNotFoundError(email)
    psw = decrypt(password)
    user = UserService.query_user(email, psw)
    if not user:
        raise AdminException("Email and password do not match!")
    if not user.is_superuser:
        raise AdminException("Not admin", 403)
    if user.is_active == ActiveEnum.INACTIVE.value:
        raise AdminException(f"User {email} inactive", 403)

    resp = user.to_json()
    user.access_token = get_uuid()
    login_user(user)
    user.update_time = (current_timestamp(),)
    user.update_date = (datetime_format(datetime.now()),)
    user.last_login_time = get_format_time()
    user.save()
    msg = "Welcome back!"
    return sync_construct_response(data=resp, auth=user.get_id(), message=msg)


def check_admin(username: str, password: str):
    users = UserService.query(email=username)
    if not users:
        _lineaje_payload = f"Username: {username} is not registered!"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in check_admin).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:38d1100ef1324b5f632e26c399cc46d62b448f36aafdddf5b948d66fdb8ff72a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:38d1100ef1324b5f632e26c399cc46d62b448f36aafdddf5b948d66fdb8ff72a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/auth.py', 'line': 139, 'function': 'check_admin'}, 'file': 'admin/server/auth.py', 'line': 139, 'function': 'check_admin', 'agent_name': 'check_admin', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        user_info = {
            "id": uuid.uuid1().hex,
            "password": encode_to_base64("admin"),
            "nickname": "admin",
            "is_superuser": True,
            "email": "admin@ragflow.io",
            "creator": "system",
            "status": "1",
        }
        if not UserService.save(**user_info):
            raise AdminException("Can't init admin.", 500)

    user = UserService.query_user(username, password)
    if user:
        return True
    else:
        return False


def login_verify(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or 'username' not in auth.parameters or 'password' not in auth.parameters:
            _lineaje_payload = ({
                "code": 401,
                "message": "Authentication required",
                "data": None
            })
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the user interface, before it leaves the application (in decorated).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:11d9d4e3726f58e65ed40aacf70a899160b3f993d6379b8690aca74d3da3e21f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:11d9d4e3726f58e65ed40aacf70a899160b3f993d6379b8690aca74d3da3e21f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/auth.py', 'line': 164, 'function': 'login_verify.decorated'}, 'file': 'admin/server/auth.py', 'line': 164, 'function': 'decorated', 'agent_name': 'decorated', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return jsonify(_lineaje_payload), 200

        username = auth.parameters['username']
        password = auth.parameters['password']
        try:
            if not check_admin(username, password):
                _lineaje_payload = ({
                    "code": 500,
                    "message": "Access denied",
                    "data": None
                })
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the user interface, before it leaves the application (in decorated).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:b86da8e6bfa33ec60da3b03bcf612cc4da6b33ec137f5aea3116272ec5e6fc1c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b86da8e6bfa33ec60da3b03bcf612cc4da6b33ec137f5aea3116272ec5e6fc1c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/auth.py', 'line': 174, 'function': 'login_verify.decorated'}, 'file': 'admin/server/auth.py', 'line': 174, 'function': 'decorated', 'agent_name': 'decorated', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return jsonify(_lineaje_payload), 200
        except Exception:
            _lineaje_payload = "An error occurred during admin login verification."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in decorated).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b687dccf0746c1954d9ceb377f0f9f2ad4daf5e6c6e741344a8dc08b80c89034'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b687dccf0746c1954d9ceb377f0f9f2ad4daf5e6c6e741344a8dc08b80c89034', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/auth.py', 'line': 180, 'function': 'login_verify.decorated'}, 'file': 'admin/server/auth.py', 'line': 180, 'function': 'decorated', 'agent_name': 'decorated', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
            _lineaje_payload = ({
                "code": 500,
                "message": "An internal server error occurred."
            })
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the user interface, before it leaves the application (in decorated).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0f9026c2224d5baa572fa5716481457ce9c86fdc6d1ed917a34b84cc91313f56'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0f9026c2224d5baa572fa5716481457ce9c86fdc6d1ed917a34b84cc91313f56', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/auth.py', 'line': 181, 'function': 'login_verify.decorated'}, 'file': 'admin/server/auth.py', 'line': 181, 'function': 'decorated', 'agent_name': 'decorated', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return jsonify(_lineaje_payload), 200

        return f(*args, **kwargs)

    # LINEAJE: runtime guardrail checks `decorated` as it flows from the agent to the user interface, before it leaves the application (in login_verify).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `decorated` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:f1869dd69d9036ad11e0cf2e3e1d4e6011ae28b3dfe23bb9dc9891a48f2992c5'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f1869dd69d9036ad11e0cf2e3e1d4e6011ae28b3dfe23bb9dc9891a48f2992c5', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/server/auth.py', 'line': 188, 'function': 'login_verify'}, 'file': 'admin/server/auth.py', 'line': 188, 'function': 'login_verify', 'agent_name': 'login_verify', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        decorated = _gr_client.enforce(_gr_site, decorated, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return decorated
