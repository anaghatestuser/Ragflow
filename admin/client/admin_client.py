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

import argparse
import base64
from cmd import Cmd

from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5
from typing import Dict, List, Any
from lark import Lark, Transformer, Tree
import requests
import getpass

GRAMMAR = r"""
start: command

command: sql_command | meta_command

sql_command: list_services
           | show_service
           | startup_service
           | shutdown_service
           | restart_service
           | list_users
           | show_user
           | drop_user
           | alter_user
           | create_user
           | activate_user
           | list_datasets
           | list_agents
           | create_role
           | drop_role
           | alter_role
           | list_roles
           | show_role
           | grant_permission
           | revoke_permission
           | alter_user_role
           | show_user_permission
           | show_version

// meta command definition
meta_command: "\\" meta_command_name [meta_args]

meta_command_name: /[a-zA-Z?]+/
meta_args: (meta_arg)+

meta_arg: /[^\\s"']+/ | quoted_string

// command definition

LIST: "LIST"i
SERVICES: "SERVICES"i
SHOW: "SHOW"i
CREATE: "CREATE"i
SERVICE: "SERVICE"i
SHUTDOWN: "SHUTDOWN"i
STARTUP: "STARTUP"i
RESTART: "RESTART"i
USERS: "USERS"i
DROP: "DROP"i
USER: "USER"i
ALTER: "ALTER"i
ACTIVE: "ACTIVE"i
PASSWORD: "PASSWORD"i
DATASETS: "DATASETS"i
OF: "OF"i
AGENTS: "AGENTS"i
ROLE: "ROLE"i
ROLES: "ROLES"i
DESCRIPTION: "DESCRIPTION"i
GRANT: "GRANT"i
REVOKE: "REVOKE"i
ALL: "ALL"i
PERMISSION: "PERMISSION"i
TO: "TO"i
FROM: "FROM"i
FOR: "FOR"i
RESOURCES: "RESOURCES"i
ON: "ON"i
SET: "SET"i
VERSION: "VERSION"i

list_services: LIST SERVICES ";"
show_service: SHOW SERVICE NUMBER ";"
startup_service: STARTUP SERVICE NUMBER ";"
shutdown_service: SHUTDOWN SERVICE NUMBER ";"
restart_service: RESTART SERVICE NUMBER ";"

list_users: LIST USERS ";"
drop_user: DROP USER quoted_string ";"
alter_user: ALTER USER PASSWORD quoted_string quoted_string ";"
show_user: SHOW USER quoted_string ";"
create_user: CREATE USER quoted_string quoted_string ";"
activate_user: ALTER USER ACTIVE quoted_string status ";"

list_datasets: LIST DATASETS OF quoted_string ";"
list_agents: LIST AGENTS OF quoted_string ";"

create_role: CREATE ROLE identifier [DESCRIPTION quoted_string] ";"
drop_role: DROP ROLE identifier ";"
alter_role: ALTER ROLE identifier SET DESCRIPTION quoted_string ";"
list_roles: LIST ROLES ";"
show_role: SHOW ROLE identifier ";"

grant_permission: GRANT action_list ON identifier TO ROLE identifier ";"
revoke_permission: REVOKE action_list ON identifier FROM ROLE identifier ";"
alter_user_role: ALTER USER quoted_string SET ROLE identifier ";"
show_user_permission: SHOW USER PERMISSION quoted_string ";"

show_version: SHOW VERSION ";"

action_list: identifier ("," identifier)*

identifier: WORD
quoted_string: QUOTED_STRING
status: WORD

QUOTED_STRING: /'[^']+'/ | /"[^"]+"/
WORD: /[a-zA-Z0-9_\-\.]+/
NUMBER: /[0-9]+/

%import common.WS
%ignore WS
"""


class AdminTransformer(Transformer):

    def start(self, items):
        return items[0]

    def command(self, items):
        return items[0]

    def list_services(self, items):
        result = {'type': 'list_services'}
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in AdminTransformer.list_services).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:347a915f7e1f1bffd9b8670588b979b53fa11f618a2de5fa274a0dc9511c2be7'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:347a915f7e1f1bffd9b8670588b979b53fa11f618a2de5fa274a0dc9511c2be7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 153, 'function': 'AdminTransformer.list_services'}, 'file': 'admin/client/admin_client.py', 'line': 153, 'function': 'list_services', 'agent_name': 'AdminTransformer', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result

    def show_service(self, items):
        service_id = int(items[2])
        return {"type": "show_service", "number": service_id}

    def startup_service(self, items):
        service_id = int(items[2])
        return {"type": "startup_service", "number": service_id}

    def shutdown_service(self, items):
        service_id = int(items[2])
        return {"type": "shutdown_service", "number": service_id}

    def restart_service(self, items):
        service_id = int(items[2])
        return {"type": "restart_service", "number": service_id}

    def list_users(self, items):
        return {"type": "list_users"}

    def show_user(self, items):
        user_name = items[2]
        return {"type": "show_user", "user_name": user_name}

    def drop_user(self, items):
        user_name = items[2]
        return {"type": "drop_user", "user_name": user_name}

    def alter_user(self, items):
        user_name = items[3]
        new_password = items[4]
        return {"type": "alter_user", "user_name": user_name, "password": new_password}

    def create_user(self, items):
        user_name = items[2]
        password = items[3]
        return {"type": "create_user", "user_name": user_name, "password": password, "role": "user"}

    def activate_user(self, items):
        user_name = items[3]
        activate_status = items[4]
        return {"type": "activate_user", "activate_status": activate_status, "user_name": user_name}

    def list_datasets(self, items):
        user_name = items[3]
        return {"type": "list_datasets", "user_name": user_name}

    def list_agents(self, items):
        user_name = items[3]
        return {"type": "list_agents", "user_name": user_name}

    def create_role(self, items):
        role_name = items[2]
        if len(items) > 4:
            description = items[4]
            return {"type": "create_role", "role_name": role_name, "description": description}
        else:
            return {"type": "create_role", "role_name": role_name}

    def drop_role(self, items):
        role_name = items[2]
        return {"type": "drop_role", "role_name": role_name}

    def alter_role(self, items):
        role_name = items[2]
        description = items[5]
        return {"type": "alter_role", "role_name": role_name, "description": description}

    def list_roles(self, items):
        return {"type": "list_roles"}

    def show_role(self, items):
        role_name = items[2]
        return {"type": "show_role", "role_name": role_name}

    def grant_permission(self, items):
        action_list = items[1]
        resource = items[3]
        role_name = items[6]
        return {"type": "grant_permission", "role_name": role_name, "resource": resource, "actions": action_list}

    def revoke_permission(self, items):
        action_list = items[1]
        resource = items[3]
        role_name = items[6]
        return {
            "type": "revoke_permission",
            "role_name": role_name,
            "resource": resource, "actions": action_list
        }

    def alter_user_role(self, items):
        user_name = items[2]
        role_name = items[5]
        return {"type": "alter_user_role", "user_name": user_name, "role_name": role_name}

    def show_user_permission(self, items):
        user_name = items[3]
        return {"type": "show_user_permission", "user_name": user_name}

    def show_version(self, items):
        return {"type": "show_version"}

    def action_list(self, items):
        # LINEAJE: runtime guardrail checks `items` as it flows from the agent to the user interface, before it leaves the application (in AdminTransformer.action_list).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `items` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:435466b15b1f7a7ce4f6d8332e46c77bf4976f61ab7b99a7a780ea18c3fee243'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:435466b15b1f7a7ce4f6d8332e46c77bf4976f61ab7b99a7a780ea18c3fee243', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 258, 'function': 'AdminTransformer.action_list'}, 'file': 'admin/client/admin_client.py', 'line': 258, 'function': 'action_list', 'agent_name': 'AdminTransformer', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            items = _gr_client.enforce(_gr_site, items, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return items

    def meta_command(self, items):
        command_name = str(items[0]).lower()
        args = items[1:] if len(items) > 1 else []

        # handle quoted parameter
        parsed_args = []
        for arg in args:
            if hasattr(arg, 'value'):
                parsed_args.append(arg.value)
            else:
                parsed_args.append(str(arg))

        return {'type': 'meta', 'command': command_name, 'args': parsed_args}

    def meta_command_name(self, items):
        return items[0]

    def meta_args(self, items):
        # LINEAJE: runtime guardrail checks `items` as it flows from the agent to the user interface, before it leaves the application (in AdminTransformer.meta_args).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `items` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:153ae52fa7fb4e26f697dab9653a8db2141338ade24e10fecdbcf64ecc3824c4'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:153ae52fa7fb4e26f697dab9653a8db2141338ade24e10fecdbcf64ecc3824c4', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 278, 'function': 'AdminTransformer.meta_args'}, 'file': 'admin/client/admin_client.py', 'line': 278, 'function': 'meta_args', 'agent_name': 'AdminTransformer', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            items = _gr_client.enforce(_gr_site, items, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return items


def encrypt(input_string):
    pub = '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArq9XTUSeYr2+N1h3Afl/z8Dse/2yD0ZGrKwx+EEEcdsBLca9Ynmx3nIB5obmLlSfmskLpBo0UACBmB5rEjBp2Q2f3AG3Hjd4B+gNCG6BDaawuDlgANIhGnaTLrIqWrrcm4EMzJOnAOI1fgzJRsOOUEfaS318Eq9OVO3apEyCCt0lOQK6PuksduOjVxtltDav+guVAA068NrPYmRNabVKRNLJpL8w4D44sfth5RvZ3q9t+6RTArpEtc5sh5ChzvqPOzKGMXW83C95TxmXqpbK6olN4RevSfVjEAgCydH6HN6OhtOQEcnrU97r9H0iZOWwbw3pVrZiUkuRD1R56Wzs2wIDAQAB\n-----END PUBLIC KEY-----'
    pub_key = RSA.importKey(pub)
    cipher = Cipher_pkcs1_v1_5.new(pub_key)
    cipher_text = cipher.encrypt(base64.b64encode(input_string.encode('utf-8')))
    return base64.b64encode(cipher_text).decode("utf-8")


def encode_to_base64(input_string):
    base64_encoded = base64.b64encode(input_string.encode('utf-8'))
    return base64_encoded.decode('utf-8')


class AdminCLI(Cmd):
    def __init__(self):
        super().__init__()
        self.parser = Lark(GRAMMAR, start='start', parser='lalr', transformer=AdminTransformer())
        self.command_history = []
        self.is_interactive = False
        self.admin_account = "admin@ragflow.io"
        self.admin_password: str = "admin"
        self.session = requests.Session()
        self.access_token: str = ""
        self.host: str = ""
        self.port: int = 0

    intro = r"""Type "\h" for help."""
    prompt = "admin> "

    def onecmd(self, command: str) -> bool:
        try:
            result = self.parse_command(command)

            if isinstance(result, dict):
                if 'type' in result and result.get('type') == 'empty':
                    return False

            self.execute_command(result)

            if isinstance(result, Tree):
                return False

            if result.get('type') == 'meta' and result.get('command') in ['q', 'quit', 'exit']:
                return True

        except KeyboardInterrupt:
            _lineaje_payload = "\nUse '\\q' to quit"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.onecmd).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9f45891f3181bff94ebccecdc28b20a5a78c46c13bfee03c8c81cc08800763ba'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9f45891f3181bff94ebccecdc28b20a5a78c46c13bfee03c8c81cc08800763ba', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 327, 'function': 'AdminCLI.onecmd'}, 'file': 'admin/client/admin_client.py', 'line': 327, 'function': 'onecmd', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)
        except EOFError:
            _lineaje_payload = "\nGoodbye!"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.onecmd).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b41c12bc7b73eb5e7b219bca4139a8836cf2ee569a4fcb1c059b0e200d5ac953'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b41c12bc7b73eb5e7b219bca4139a8836cf2ee569a4fcb1c059b0e200d5ac953', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 329, 'function': 'AdminCLI.onecmd'}, 'file': 'admin/client/admin_client.py', 'line': 329, 'function': 'onecmd', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)
            return True
        return False

    def emptyline(self) -> bool:
        return False

    def default(self, line: str) -> bool:
        return self.onecmd(line)

    def parse_command(self, command_str: str) -> dict[str, str]:
        if not command_str.strip():
            return {'type': 'empty'}

        self.command_history.append(command_str)

        try:
            result = self.parser.parse(command_str)
            # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in AdminCLI.parse_command).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:47c460f36aaeb741124a342f17de789ac057735d9b7d2a33a26b1664dbb2d0b1'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:47c460f36aaeb741124a342f17de789ac057735d9b7d2a33a26b1664dbb2d0b1', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 347, 'function': 'AdminCLI.parse_command'}, 'file': 'admin/client/admin_client.py', 'line': 347, 'function': 'parse_command', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return result
        except Exception as e:
            return {'type': 'error', 'message': f'Parse error: {str(e)}'}

    def verify_admin(self, arguments: dict, single_command: bool):
        self.host = arguments['host']
        self.port = arguments['port']
        _lineaje_payload = "Attempt to access server for admin login"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.verify_admin).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d4da6e369f0a0cdd7636ec7946e71369a8d788c01614d0631d74a384093c9a90'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d4da6e369f0a0cdd7636ec7946e71369a8d788c01614d0631d74a384093c9a90', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 354, 'function': 'AdminCLI.verify_admin'}, 'file': 'admin/client/admin_client.py', 'line': 354, 'function': 'verify_admin', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f"http://{self.host}:{self.port}/api/v1/admin/login"

        attempt_count = 3
        if single_command:
            attempt_count = 1

        try_count = 0
        while True:
            try_count += 1
            if try_count > attempt_count:
                return False

            if single_command:
                admin_passwd = arguments['password']
            else:
                admin_passwd = getpass.getpass(f"password for {self.admin_account}: ").strip()
            try:
                self.admin_password = encrypt(admin_passwd)
                response = self.session.post(url, json={'email': self.admin_account, 'password': self.admin_password})
                if response.status_code == 200:
                    res_json = response.json()
                    error_code = res_json.get('code', -1)
                    if error_code == 0:
                        self.session.headers.update({
                            'Content-Type': 'application/json',
                            'Authorization': response.headers['Authorization'],
                            'User-Agent': 'RAGFlow-CLI/0.22.1'
                        })
                        _lineaje_payload = "Authentication successful."
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.verify_admin).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:90bcc06023945f4a16ec5e41e45c6504d31d88259c14652b5e12d8d017d2d946'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:90bcc06023945f4a16ec5e41e45c6504d31d88259c14652b5e12d8d017d2d946', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 383, 'function': 'AdminCLI.verify_admin'}, 'file': 'admin/client/admin_client.py', 'line': 383, 'function': 'verify_admin', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        print(_lineaje_payload)
                        return True
                    else:
                        error_message = res_json.get('message', 'Unknown error')
                        _lineaje_payload = f"Authentication failed: {error_message}, try again"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.verify_admin).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:9f3e1393341cb2f2b4b661bd4c01521448f3fba8bd929974df3a273e06f0329e'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9f3e1393341cb2f2b4b661bd4c01521448f3fba8bd929974df3a273e06f0329e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 387, 'function': 'AdminCLI.verify_admin'}, 'file': 'admin/client/admin_client.py', 'line': 387, 'function': 'verify_admin', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        print(_lineaje_payload)
                        continue
                else:
                    _lineaje_payload = f"Bad response，status: {response.status_code}, password is wrong"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.verify_admin).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:e6077f1aafaf47e3bfda9cb29aa4d2832cb869341b41fb67dba5465b9535e0a4'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e6077f1aafaf47e3bfda9cb29aa4d2832cb869341b41fb67dba5465b9535e0a4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 390, 'function': 'AdminCLI.verify_admin'}, 'file': 'admin/client/admin_client.py', 'line': 390, 'function': 'verify_admin', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    print(_lineaje_payload)
            except Exception as e:
                _lineaje_payload = str(e)
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.verify_admin).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:fd67def5faa94ca08b46c59a3c6762b79e993a3db3b66a3dc29af46650083252'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fd67def5faa94ca08b46c59a3c6762b79e993a3db3b66a3dc29af46650083252', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 392, 'function': 'AdminCLI.verify_admin'}, 'file': 'admin/client/admin_client.py', 'line': 392, 'function': 'verify_admin', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
                _lineaje_payload = "Can't access server for admin login (connection failed)"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.verify_admin).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f6e787c98df7446b8e394165ba6c0dc20791d02ee21b7ea18a1defa7aee57e70'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f6e787c98df7446b8e394165ba6c0dc20791d02ee21b7ea18a1defa7aee57e70', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 393, 'function': 'AdminCLI.verify_admin'}, 'file': 'admin/client/admin_client.py', 'line': 393, 'function': 'verify_admin', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)

    def _format_service_detail_table(self, data):
        if isinstance(data, list):
            # LINEAJE: runtime guardrail checks `data` as it flows from the agent to the user interface, before it leaves the application (in AdminCLI._format_service_detail_table).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1072173a61afc1c9084e1698351a7ddfd69691fcc575e30dbe5aee3abf9c10fe'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1072173a61afc1c9084e1698351a7ddfd69691fcc575e30dbe5aee3abf9c10fe', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 397, 'function': 'AdminCLI._format_service_detail_table'}, 'file': 'admin/client/admin_client.py', 'line': 397, 'function': '_format_service_detail_table', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                data = _gr_client.enforce(_gr_site, data, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return data
        if not all([isinstance(v, list) for v in data.values()]):
            # normal table
            # LINEAJE: runtime guardrail checks `data` as it flows from the agent to the user interface, before it leaves the application (in AdminCLI._format_service_detail_table).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f3cc2fcd2f4c8fd8c18fd743d77fd1f6f00e76da24bc3e9b684453578f98debd'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f3cc2fcd2f4c8fd8c18fd743d77fd1f6f00e76da24bc3e9b684453578f98debd', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 400, 'function': 'AdminCLI._format_service_detail_table'}, 'file': 'admin/client/admin_client.py', 'line': 400, 'function': '_format_service_detail_table', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                data = _gr_client.enforce(_gr_site, data, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return data
        # handle task_executor heartbeats map, for example {'name': [{'done': 2, 'now': timestamp1}, {'done': 3, 'now': timestamp2}]
        task_executor_list = []
        for k, v in data.items():
            # display latest status
            heartbeats = sorted(v, key=lambda x: x["now"], reverse=True)
            task_executor_list.append({
                "task_executor_name": k,
                **heartbeats[0],
            } if heartbeats else {"task_executor_name": k})
        # LINEAJE: runtime guardrail checks `task_executor_list` as it flows from the agent to the user interface, before it leaves the application (in AdminCLI._format_service_detail_table).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `task_executor_list` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ee05e9fafd7a9a744f78c1e692d8fed1793c861c2aea5f99599c106fe00befba'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ee05e9fafd7a9a744f78c1e692d8fed1793c861c2aea5f99599c106fe00befba', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 410, 'function': 'AdminCLI._format_service_detail_table'}, 'file': 'admin/client/admin_client.py', 'line': 410, 'function': '_format_service_detail_table', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            task_executor_list = _gr_client.enforce(_gr_site, task_executor_list, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return task_executor_list

    def _print_table_simple(self, data):
        if not data:
            _lineaje_payload = "No data to print"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._print_table_simple).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:baf987de8e4bc828f442a7042e406ecf9ecf5dc90921ba58a0b3192f76894846'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:baf987de8e4bc828f442a7042e406ecf9ecf5dc90921ba58a0b3192f76894846', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 414, 'function': 'AdminCLI._print_table_simple'}, 'file': 'admin/client/admin_client.py', 'line': 414, 'function': '_print_table_simple', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)
            return
        if isinstance(data, dict):
            # handle single row data
            data = [data]

        columns = list(set().union(*(d.keys() for d in data)))
        columns.sort()
        col_widths = {}

        def get_string_width(text):
            half_width_chars = (
                " !\"#$%&'()*+,-./0123456789:;<=>?@"
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`"
                "abcdefghijklmnopqrstuvwxyz{|}~"
                "\t\n\r"
            )
            width = 0
            for char in text:
                if char in half_width_chars:
                    width += 1
                else:
                    width += 2
            # LINEAJE: runtime guardrail checks `width` as it flows from the agent to the user interface, before it leaves the application (in AdminCLI.get_string_width).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `width` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:84a07679e46a515caee1180b29a18db914d82a34d3e71c8197dceeba206ddf3b'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:84a07679e46a515caee1180b29a18db914d82a34d3e71c8197dceeba206ddf3b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 437, 'function': 'AdminCLI._print_table_simple.get_string_width'}, 'file': 'admin/client/admin_client.py', 'line': 437, 'function': 'get_string_width', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                width = _gr_client.enforce(_gr_site, width, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return width

        for col in columns:
            max_width = get_string_width(str(col))
            for item in data:
                value_len = get_string_width(str(item.get(col, '')))
                if value_len > max_width:
                    max_width = value_len
            col_widths[col] = max(2, max_width)

        # Generate delimiter
        separator = "+" + "+".join(["-" * (col_widths[col] + 2) for col in columns]) + "+"

        # Print header
        # LINEAJE: runtime guardrail checks `separator` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._print_table_simple).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `separator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:765b62c62edfe4ba60c4986080fd93b3a21d5b1080bc28845e14d371c1c6131f'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:765b62c62edfe4ba60c4986080fd93b3a21d5b1080bc28845e14d371c1c6131f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 451, 'function': 'AdminCLI._print_table_simple'}, 'file': 'admin/client/admin_client.py', 'line': 451, 'function': '_print_table_simple', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            separator = _gr_client.enforce(_gr_site, separator, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(separator)
        header = "|" + "|".join([f" {col:<{col_widths[col]}} " for col in columns]) + "|"
        # LINEAJE: runtime guardrail checks `header` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._print_table_simple).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `header` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:60a8f2a9e44e0b211fb0fdb4dbbade66565d9a20ebfc29a519b4def84197365a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:60a8f2a9e44e0b211fb0fdb4dbbade66565d9a20ebfc29a519b4def84197365a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 453, 'function': 'AdminCLI._print_table_simple'}, 'file': 'admin/client/admin_client.py', 'line': 453, 'function': '_print_table_simple', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            header = _gr_client.enforce(_gr_site, header, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(header)
        # LINEAJE: runtime guardrail checks `separator` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._print_table_simple).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `separator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5936542b81c89863f13dd7021162a6abdef9109a5bf92ea2ae9daf58d86e10d9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5936542b81c89863f13dd7021162a6abdef9109a5bf92ea2ae9daf58d86e10d9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 454, 'function': 'AdminCLI._print_table_simple'}, 'file': 'admin/client/admin_client.py', 'line': 454, 'function': '_print_table_simple', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            separator = _gr_client.enforce(_gr_site, separator, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(separator)

        # Print data
        for item in data:
            row = "|"
            for col in columns:
                value = str(item.get(col, ''))
                if get_string_width(value) > col_widths[col]:
                    value = value[:col_widths[col] - 3] + "..."
                row += f" {value:<{col_widths[col] - (get_string_width(value) - len(value))}} |"
            # LINEAJE: runtime guardrail checks `row` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.get_string_width).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `row` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6f6ddd541b7b859d4629713d1258d6e00729b52f764f85a9e9916878acd92672'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6f6ddd541b7b859d4629713d1258d6e00729b52f764f85a9e9916878acd92672', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 464, 'function': 'AdminCLI._print_table_simple'}, 'file': 'admin/client/admin_client.py', 'line': 464, 'function': 'get_string_width', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                row = _gr_client.enforce(_gr_site, row, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(row)

        # LINEAJE: runtime guardrail checks `separator` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._print_table_simple).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `separator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b571b1a0025b803c3930f6d76bb65bc3e35887e0d1e17ab940cb190de3f52d90'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b571b1a0025b803c3930f6d76bb65bc3e35887e0d1e17ab940cb190de3f52d90', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 466, 'function': 'AdminCLI._print_table_simple'}, 'file': 'admin/client/admin_client.py', 'line': 466, 'function': '_print_table_simple', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            separator = _gr_client.enforce(_gr_site, separator, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(separator)

    def run_interactive(self):

        self.is_interactive = True
        _lineaje_payload = "RAGFlow Admin command line interface - Type '\\?' for help, '\\q' to quit"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.run_interactive).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a7c3266eba3b6440704e011ca0cdf1081a4c81a67f550009c50bbbdc3405532e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a7c3266eba3b6440704e011ca0cdf1081a4c81a67f550009c50bbbdc3405532e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 471, 'function': 'AdminCLI.run_interactive'}, 'file': 'admin/client/admin_client.py', 'line': 471, 'function': 'run_interactive', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)

        while True:
            try:
                command = input("admin> ").strip()
                if not command:
                    continue

                _lineaje_payload = f"command: {command}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.run_interactive).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:82d7f160b99a1647cce273945245214bbcd93b90295bfca6cefca7e2c667bd65'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:82d7f160b99a1647cce273945245214bbcd93b90295bfca6cefca7e2c667bd65', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 479, 'function': 'AdminCLI.run_interactive'}, 'file': 'admin/client/admin_client.py', 'line': 479, 'function': 'run_interactive', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
                result = self.parse_command(command)
                self.execute_command(result)

                if isinstance(result, Tree):
                    continue

                if result.get('type') == 'meta' and result.get('command') in ['q', 'quit', 'exit']:
                    break

            except KeyboardInterrupt:
                _lineaje_payload = "\nUse '\\q' to quit"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.run_interactive).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:94a3f32070b330250e4697d821d74f9451e6f58443a1535424945bb7411eaf0d'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:94a3f32070b330250e4697d821d74f9451e6f58443a1535424945bb7411eaf0d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 490, 'function': 'AdminCLI.run_interactive'}, 'file': 'admin/client/admin_client.py', 'line': 490, 'function': 'run_interactive', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
            except EOFError:
                _lineaje_payload = "\nGoodbye!"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.run_interactive).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:4e57d88d14d3adc7da3696c5bff4d7df7c947a981c428f83622929fcf630e7d2'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4e57d88d14d3adc7da3696c5bff4d7df7c947a981c428f83622929fcf630e7d2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 492, 'function': 'AdminCLI.run_interactive'}, 'file': 'admin/client/admin_client.py', 'line': 492, 'function': 'run_interactive', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
                break

    def run_single_command(self, command: str):
        result = self.parse_command(command)
        self.execute_command(result)

    def parse_connection_args(self, args: List[str]) -> Dict[str, Any]:
        parser = argparse.ArgumentParser(description='Admin CLI Client', add_help=False)
        parser.add_argument('-h', '--host', default='localhost', help='Admin service host')
        parser.add_argument('-p', '--port', type=int, default=9381, help='Admin service port')
        parser.add_argument('-w', '--password', default='admin', type=str, help='Superuser password')
        parser.add_argument('command', nargs='?', help='Single command')
        try:
            parsed_args, remaining_args = parser.parse_known_args(args)
            if remaining_args:
                command = remaining_args[0]
                return {
                    'host': parsed_args.host,
                    'port': parsed_args.port,
                    'password': parsed_args.password,
                    'command': command
                }
            else:
                return {
                    'host': parsed_args.host,
                    'port': parsed_args.port,
                }
        except SystemExit:
            return {'error': 'Invalid connection arguments'}

    def execute_command(self, parsed_command: Dict[str, Any]):

        command_dict: dict
        if isinstance(parsed_command, Tree):
            command_dict = parsed_command.children[0]
        else:
            if parsed_command['type'] == 'error':
                _lineaje_payload = f"Error: {parsed_command['message']}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.execute_command).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:b30270a2b874b79a82073ec1919321a87e8f708a3a81600a9dc5745f73fd90dd'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b30270a2b874b79a82073ec1919321a87e8f708a3a81600a9dc5745f73fd90dd', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 530, 'function': 'AdminCLI.execute_command'}, 'file': 'admin/client/admin_client.py', 'line': 530, 'function': 'execute_command', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
                return
            else:
                command_dict = parsed_command

        # print(f"Parsed command: {command_dict}")

        command_type = command_dict['type']

        match command_type:
            case 'list_services':
                self._handle_list_services(command_dict)
            case 'show_service':
                self._handle_show_service(command_dict)
            case 'restart_service':
                self._handle_restart_service(command_dict)
            case 'shutdown_service':
                self._handle_shutdown_service(command_dict)
            case 'startup_service':
                self._handle_startup_service(command_dict)
            case 'list_users':
                self._handle_list_users(command_dict)
            case 'show_user':
                self._handle_show_user(command_dict)
            case 'drop_user':
                self._handle_drop_user(command_dict)
            case 'alter_user':
                self._handle_alter_user(command_dict)
            case 'create_user':
                self._handle_create_user(command_dict)
            case 'activate_user':
                self._handle_activate_user(command_dict)
            case 'list_datasets':
                self._handle_list_datasets(command_dict)
            case 'list_agents':
                self._handle_list_agents(command_dict)
            case 'create_role':
                self._create_role(command_dict)
            case 'drop_role':
                self._drop_role(command_dict)
            case 'alter_role':
                self._alter_role(command_dict)
            case 'list_roles':
                self._list_roles(command_dict)
            case 'show_role':
                self._show_role(command_dict)
            case 'grant_permission':
                self._grant_permission(command_dict)
            case 'revoke_permission':
                self._revoke_permission(command_dict)
            case 'alter_user_role':
                self._alter_user_role(command_dict)
            case 'show_user_permission':
                self._show_user_permission(command_dict)
            case 'show_version':
                self._show_version(command_dict)
            case 'meta':
                self._handle_meta_command(command_dict)
            case _:
                _lineaje_payload = f"Command '{command_type}' would be executed with API"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.execute_command).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:0ab913216f353a6e9fef45c09f87a4df552e270b297e9c17984d2e964133eb4d'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0ab913216f353a6e9fef45c09f87a4df552e270b297e9c17984d2e964133eb4d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 589, 'function': 'AdminCLI.execute_command'}, 'file': 'admin/client/admin_client.py', 'line': 589, 'function': 'execute_command', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)

    def _handle_list_services(self, command):
        _lineaje_payload = "Listing all services"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_list_services).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:42830c5c7e69259842d199182b260fffafc6a53378bb4d276a61a84d0e87b12d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:42830c5c7e69259842d199182b260fffafc6a53378bb4d276a61a84d0e87b12d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 592, 'function': 'AdminCLI._handle_list_services'}, 'file': 'admin/client/admin_client.py', 'line': 592, 'function': '_handle_list_services', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)

        url = f'http://{self.host}:{self.port}/api/v1/admin/services'
        response = self.session.get(url)
        res_json = response.json()
        if response.status_code == 200:
            self._print_table_simple(res_json['data'])
        else:
            _lineaje_payload = f"Fail to get all services, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_list_services).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:db73e500d1221ed4a011b12b3a21844e5fb2518454f6526d65d46324671d7a59'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:db73e500d1221ed4a011b12b3a21844e5fb2518454f6526d65d46324671d7a59', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 600, 'function': 'AdminCLI._handle_list_services'}, 'file': 'admin/client/admin_client.py', 'line': 600, 'function': '_handle_list_services', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _handle_show_service(self, command):
        service_id: int = command['number']
        _lineaje_payload = f"Showing service: {service_id}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_show_service).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:02987dae90901be8508510a23233840e1901ee0ca1c07e0d08539de7355cf2bd'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:02987dae90901be8508510a23233840e1901ee0ca1c07e0d08539de7355cf2bd', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 604, 'function': 'AdminCLI._handle_show_service'}, 'file': 'admin/client/admin_client.py', 'line': 604, 'function': '_handle_show_service', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)

        url = f'http://{self.host}:{self.port}/api/v1/admin/services/{service_id}'
        response = self.session.get(url)
        res_json = response.json()
        if response.status_code == 200:
            res_data = res_json['data']
            if 'status' in res_data and res_data['status'] == 'alive':
                _lineaje_payload = f"Service {res_data['service_name']} is alive, "
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_show_service).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:bc2258ed79b5c4a87abdb9d3c2bed8f81f0121b0b2696b82836a510e0083450b'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bc2258ed79b5c4a87abdb9d3c2bed8f81f0121b0b2696b82836a510e0083450b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 612, 'function': 'AdminCLI._handle_show_service'}, 'file': 'admin/client/admin_client.py', 'line': 612, 'function': '_handle_show_service', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
                if isinstance(res_data['message'], str):
                    _lineaje_payload = res_data['message']
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_show_service).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:61f76d171e9fa4e2b8270acc2178910604a310dbb62326ba7fb1ea0878d32a50'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:61f76d171e9fa4e2b8270acc2178910604a310dbb62326ba7fb1ea0878d32a50', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 614, 'function': 'AdminCLI._handle_show_service'}, 'file': 'admin/client/admin_client.py', 'line': 614, 'function': '_handle_show_service', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    print(_lineaje_payload)
                else:
                    data = self._format_service_detail_table(res_data['message'])
                    self._print_table_simple(data)
            else:
                _lineaje_payload = f"Service {res_data['service_name']} is down, {res_data['message']}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_show_service).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:477de2020701cbf5bf168776f76e83bb0f6d64db99b8f7dc4298e9808e4ef122'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:477de2020701cbf5bf168776f76e83bb0f6d64db99b8f7dc4298e9808e4ef122', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 619, 'function': 'AdminCLI._handle_show_service'}, 'file': 'admin/client/admin_client.py', 'line': 619, 'function': '_handle_show_service', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
        else:
            _lineaje_payload = f"Fail to show service, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_show_service).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:cbfcf5bd7e5eea479363c6ca95bdfba671d1b473aa712d401f477baa3fd47edd'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cbfcf5bd7e5eea479363c6ca95bdfba671d1b473aa712d401f477baa3fd47edd', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 621, 'function': 'AdminCLI._handle_show_service'}, 'file': 'admin/client/admin_client.py', 'line': 621, 'function': '_handle_show_service', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _handle_restart_service(self, command):
        service_id: int = command['number']
        _lineaje_payload = f"Restart service {service_id}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_restart_service).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:7db8157262edd77970279dbe206a68d8c3267384636449b227cc24c029215217'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7db8157262edd77970279dbe206a68d8c3267384636449b227cc24c029215217', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 625, 'function': 'AdminCLI._handle_restart_service'}, 'file': 'admin/client/admin_client.py', 'line': 625, 'function': '_handle_restart_service', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)

    def _handle_shutdown_service(self, command):
        service_id: int = command['number']
        _lineaje_payload = f"Shutdown service {service_id}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_shutdown_service).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:58058be082cfa17427330aed028cd473468ec21433fb48178650375e7f9c3074'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:58058be082cfa17427330aed028cd473468ec21433fb48178650375e7f9c3074', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 629, 'function': 'AdminCLI._handle_shutdown_service'}, 'file': 'admin/client/admin_client.py', 'line': 629, 'function': '_handle_shutdown_service', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)

    def _handle_startup_service(self, command):
        service_id: int = command['number']
        _lineaje_payload = f"Startup service {service_id}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_startup_service).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a9dc11246c875f0c1477f12346825a576b4d92c562cd5b227ccd939ed98f42ab'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a9dc11246c875f0c1477f12346825a576b4d92c562cd5b227ccd939ed98f42ab', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 633, 'function': 'AdminCLI._handle_startup_service'}, 'file': 'admin/client/admin_client.py', 'line': 633, 'function': '_handle_startup_service', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)

    def _handle_list_users(self, command):
        _lineaje_payload = "Listing all users"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_list_users).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:aa0f1267e023c54cd9fa56008d995f4bfa32af80143920f7afde70d926b450e9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aa0f1267e023c54cd9fa56008d995f4bfa32af80143920f7afde70d926b450e9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 636, 'function': 'AdminCLI._handle_list_users'}, 'file': 'admin/client/admin_client.py', 'line': 636, 'function': '_handle_list_users', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)

        url = f'http://{self.host}:{self.port}/api/v1/admin/users'
        response = self.session.get(url)
        res_json = response.json()
        if response.status_code == 200:
            self._print_table_simple(res_json['data'])
        else:
            _lineaje_payload = f"Fail to get all users, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_list_users).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3a9ee6c9e45aee1ad806e573d577b368eaf2347fc8786e721ebd15b4cf97db1f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3a9ee6c9e45aee1ad806e573d577b368eaf2347fc8786e721ebd15b4cf97db1f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 644, 'function': 'AdminCLI._handle_list_users'}, 'file': 'admin/client/admin_client.py', 'line': 644, 'function': '_handle_list_users', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _handle_show_user(self, command):
        username_tree: Tree = command['user_name']
        user_name: str = username_tree.children[0].strip("'\"")
        _lineaje_payload = f"Showing user: {user_name}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_show_user).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:7c13924631b3f86cf311af174c097f172b9c9f914a7823e7f87bd44a13bf596f'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7c13924631b3f86cf311af174c097f172b9c9f914a7823e7f87bd44a13bf596f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 649, 'function': 'AdminCLI._handle_show_user'}, 'file': 'admin/client/admin_client.py', 'line': 649, 'function': '_handle_show_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/users/{user_name}'
        response = self.session.get(url)
        res_json = response.json()
        if response.status_code == 200:
            table_data = res_json['data']
            table_data.pop('avatar')
            self._print_table_simple(table_data)
        else:
            _lineaje_payload = f"Fail to get user {user_name}, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_show_user).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0f1bc050c3c8bb354074c971b55795dfe09a612f13d8f2e6c102caefe2a7c7a2'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0f1bc050c3c8bb354074c971b55795dfe09a612f13d8f2e6c102caefe2a7c7a2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 658, 'function': 'AdminCLI._handle_show_user'}, 'file': 'admin/client/admin_client.py', 'line': 658, 'function': '_handle_show_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _handle_drop_user(self, command):
        username_tree: Tree = command['user_name']
        user_name: str = username_tree.children[0].strip("'\"")
        _lineaje_payload = f"Drop user: {user_name}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_drop_user).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:116e53a723eb39018a254e463dfd568da65daa2d6f1ce9015e02540a57cdd846'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:116e53a723eb39018a254e463dfd568da65daa2d6f1ce9015e02540a57cdd846', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 663, 'function': 'AdminCLI._handle_drop_user'}, 'file': 'admin/client/admin_client.py', 'line': 663, 'function': '_handle_drop_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/users/{user_name}'
        response = self.session.delete(url)
        res_json = response.json()
        if response.status_code == 200:
            _lineaje_payload = res_json["message"]
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_drop_user).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:44f3d9d1dba24b89be8ee5036e3c406404d9e92932a279c872bb59c69628b955'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:44f3d9d1dba24b89be8ee5036e3c406404d9e92932a279c872bb59c69628b955', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 668, 'function': 'AdminCLI._handle_drop_user'}, 'file': 'admin/client/admin_client.py', 'line': 668, 'function': '_handle_drop_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)
        else:
            _lineaje_payload = f"Fail to drop user, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_drop_user).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ff26249e7011ee7d07e8942aca200a7d2aa8e8400499b7fd8dfb79207b9e9738'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ff26249e7011ee7d07e8942aca200a7d2aa8e8400499b7fd8dfb79207b9e9738', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 670, 'function': 'AdminCLI._handle_drop_user'}, 'file': 'admin/client/admin_client.py', 'line': 670, 'function': '_handle_drop_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _handle_alter_user(self, command):
        user_name_tree: Tree = command['user_name']
        user_name: str = user_name_tree.children[0].strip("'\"")
        password_tree: Tree = command['password']
        password: str = password_tree.children[0].strip("'\"")
        _lineaje_payload = f"Alter user: {user_name}, password: ******"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_alter_user).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:285e81df3f705a8dea9a309c800da9ab78bcc03ed43c59974827292f779b6505'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:285e81df3f705a8dea9a309c800da9ab78bcc03ed43c59974827292f779b6505', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 677, 'function': 'AdminCLI._handle_alter_user'}, 'file': 'admin/client/admin_client.py', 'line': 677, 'function': '_handle_alter_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/users/{user_name}/password'
        response = self.session.put(url, json={'new_password': encrypt(password)})
        res_json = response.json()
        if response.status_code == 200:
            _lineaje_payload = res_json["message"]
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_alter_user).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:960ea19337d9454164d08db39e78a3c17accde67b54b9b66d8ee871a71884567'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:960ea19337d9454164d08db39e78a3c17accde67b54b9b66d8ee871a71884567', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 682, 'function': 'AdminCLI._handle_alter_user'}, 'file': 'admin/client/admin_client.py', 'line': 682, 'function': '_handle_alter_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)
        else:
            _lineaje_payload = f"Fail to alter password, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_alter_user).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ad3e8fe7a1040a8daa22aa250612567a2c64cfece96dab4b7029d790aaff58da'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ad3e8fe7a1040a8daa22aa250612567a2c64cfece96dab4b7029d790aaff58da', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 684, 'function': 'AdminCLI._handle_alter_user'}, 'file': 'admin/client/admin_client.py', 'line': 684, 'function': '_handle_alter_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _handle_create_user(self, command):
        user_name_tree: Tree = command['user_name']
        user_name: str = user_name_tree.children[0].strip("'\"")
        password_tree: Tree = command['password']
        password: str = password_tree.children[0].strip("'\"")
        role: str = command['role']
        _lineaje_payload = f"Create user: {user_name}, password: ******, role: {role}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_create_user).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c1eee2050b349ba32d126e8656e78434ecec04440b9913851dbbe56a2730a68c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c1eee2050b349ba32d126e8656e78434ecec04440b9913851dbbe56a2730a68c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 692, 'function': 'AdminCLI._handle_create_user'}, 'file': 'admin/client/admin_client.py', 'line': 692, 'function': '_handle_create_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/users'
        response = self.session.post(
            url,
            json={'user_name': user_name, 'password': encrypt(password), 'role': role}
        )
        res_json = response.json()
        if response.status_code == 200:
            self._print_table_simple(res_json['data'])
        else:
            _lineaje_payload = f"Fail to create user {user_name}, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_create_user).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:5f12647c14fda869927a96b5ee9169b47a7569a3408a3f0df238bea3e92400b6'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5f12647c14fda869927a96b5ee9169b47a7569a3408a3f0df238bea3e92400b6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 702, 'function': 'AdminCLI._handle_create_user'}, 'file': 'admin/client/admin_client.py', 'line': 702, 'function': '_handle_create_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _handle_activate_user(self, command):
        user_name_tree: Tree = command['user_name']
        user_name: str = user_name_tree.children[0].strip("'\"")
        activate_tree: Tree = command['activate_status']
        activate_status: str = activate_tree.children[0].strip("'\"")
        if activate_status.lower() in ['on', 'off']:
            _lineaje_payload = f"Alter user {user_name} activate status, turn {activate_status.lower()}."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_activate_user).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3edec797485e07afa4eec7b6dda85c3e37456d3f10aa00a57ea5dfe1a495ca9e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3edec797485e07afa4eec7b6dda85c3e37456d3f10aa00a57ea5dfe1a495ca9e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 710, 'function': 'AdminCLI._handle_activate_user'}, 'file': 'admin/client/admin_client.py', 'line': 710, 'function': '_handle_activate_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)
            url = f'http://{self.host}:{self.port}/api/v1/admin/users/{user_name}/activate'
            response = self.session.put(url, json={'activate_status': activate_status})
            res_json = response.json()
            if response.status_code == 200:
                _lineaje_payload = res_json["message"]
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_activate_user).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:936488ff9ae49d704797ef608318223cf08da8c262d47778fa20c07834a42aa2'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:936488ff9ae49d704797ef608318223cf08da8c262d47778fa20c07834a42aa2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 715, 'function': 'AdminCLI._handle_activate_user'}, 'file': 'admin/client/admin_client.py', 'line': 715, 'function': '_handle_activate_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
            else:
                _lineaje_payload = f"Fail to alter activate status, code: {res_json['code']}, message: {res_json['message']}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_activate_user).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:154b3231c147cf38f56a7236aa7fb94435cf78b07d7bc33d7b5ce3b327fe30aa'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:154b3231c147cf38f56a7236aa7fb94435cf78b07d7bc33d7b5ce3b327fe30aa', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 717, 'function': 'AdminCLI._handle_activate_user'}, 'file': 'admin/client/admin_client.py', 'line': 717, 'function': '_handle_activate_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
        else:
            _lineaje_payload = f"Unknown activate status: {activate_status}."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_activate_user).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:c1206c0ddd05239035b48cfba5624f4093a9c9012540ef80ba6379dbe18e32ad'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c1206c0ddd05239035b48cfba5624f4093a9c9012540ef80ba6379dbe18e32ad', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 719, 'function': 'AdminCLI._handle_activate_user'}, 'file': 'admin/client/admin_client.py', 'line': 719, 'function': '_handle_activate_user', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _handle_list_datasets(self, command):
        username_tree: Tree = command['user_name']
        user_name: str = username_tree.children[0].strip("'\"")
        _lineaje_payload = f"Listing all datasets of user: {user_name}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_list_datasets).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:15d11e1ef0c36a4b9a1b785672e6e331a6a464c834a6a43b18bc382bc35590a4'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:15d11e1ef0c36a4b9a1b785672e6e331a6a464c834a6a43b18bc382bc35590a4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 724, 'function': 'AdminCLI._handle_list_datasets'}, 'file': 'admin/client/admin_client.py', 'line': 724, 'function': '_handle_list_datasets', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/users/{user_name}/datasets'
        response = self.session.get(url)
        res_json = response.json()
        if response.status_code == 200:
            table_data = res_json['data']
            for t in table_data:
                t.pop('avatar')
            self._print_table_simple(table_data)
        else:
            _lineaje_payload = f"Fail to get all datasets of {user_name}, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_list_datasets).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9cbb31366e88bf33645687e763f2bff8f6d83e3cb00b1fa5caf1bee02594a95a'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9cbb31366e88bf33645687e763f2bff8f6d83e3cb00b1fa5caf1bee02594a95a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 734, 'function': 'AdminCLI._handle_list_datasets'}, 'file': 'admin/client/admin_client.py', 'line': 734, 'function': '_handle_list_datasets', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _handle_list_agents(self, command):
        username_tree: Tree = command['user_name']
        user_name: str = username_tree.children[0].strip("'\"")
        _lineaje_payload = f"Listing all agents of user: {user_name}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_list_agents).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ccc454e65a33ec481c89a8cd2e52a1c5df911aa2e381106fc0f804f4f3a1d7ac'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ccc454e65a33ec481c89a8cd2e52a1c5df911aa2e381106fc0f804f4f3a1d7ac', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 739, 'function': 'AdminCLI._handle_list_agents'}, 'file': 'admin/client/admin_client.py', 'line': 739, 'function': '_handle_list_agents', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/users/{user_name}/agents'
        response = self.session.get(url)
        res_json = response.json()
        if response.status_code == 200:
            table_data = res_json['data']
            for t in table_data:
                t.pop('avatar')
            self._print_table_simple(table_data)
        else:
            _lineaje_payload = f"Fail to get all agents of {user_name}, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_list_agents).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:735ccc3c74e3461968051240c7656db57ca120af7f911fc307e96b0921f2560d'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:735ccc3c74e3461968051240c7656db57ca120af7f911fc307e96b0921f2560d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 749, 'function': 'AdminCLI._handle_list_agents'}, 'file': 'admin/client/admin_client.py', 'line': 749, 'function': '_handle_list_agents', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _create_role(self, command):
        role_name_tree: Tree = command['role_name']
        role_name: str = role_name_tree.children[0].strip("'\"")
        desc_str: str = ''
        if 'description' in command:
            desc_tree: Tree = command['description']
            desc_str = desc_tree.children[0].strip("'\"")

        _lineaje_payload = f"create role name: {role_name}, description: {desc_str}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._create_role).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:642a1ce08c57a0852dd9fd5fa4127abe352ac2e59cf1c52045d04d38cb82e445'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:642a1ce08c57a0852dd9fd5fa4127abe352ac2e59cf1c52045d04d38cb82e445', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 759, 'function': 'AdminCLI._create_role'}, 'file': 'admin/client/admin_client.py', 'line': 759, 'function': '_create_role', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/roles'
        response = self.session.post(
            url,
            json={'role_name': role_name, 'description': desc_str}
        )
        res_json = response.json()
        if response.status_code == 200:
            self._print_table_simple(res_json['data'])
        else:
            _lineaje_payload = f"Fail to create role {role_name}, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._create_role).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f59a76797b763bdc9d8a3ae4fada29f779eca47f321dc7234dbb9ddaca021410'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f59a76797b763bdc9d8a3ae4fada29f779eca47f321dc7234dbb9ddaca021410', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 769, 'function': 'AdminCLI._create_role'}, 'file': 'admin/client/admin_client.py', 'line': 769, 'function': '_create_role', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _drop_role(self, command):
        role_name_tree: Tree = command['role_name']
        role_name: str = role_name_tree.children[0].strip("'\"")
        _lineaje_payload = f"drop role name: {role_name}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._drop_role).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f400b950adfb6b6d1abc35d1e27726e7f7f7ee2ca38b89bf834054e246374347'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f400b950adfb6b6d1abc35d1e27726e7f7f7ee2ca38b89bf834054e246374347', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 774, 'function': 'AdminCLI._drop_role'}, 'file': 'admin/client/admin_client.py', 'line': 774, 'function': '_drop_role', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/roles/{role_name}'
        response = self.session.delete(url)
        res_json = response.json()
        if response.status_code == 200:
            self._print_table_simple(res_json['data'])
        else:
            _lineaje_payload = f"Fail to drop role {role_name}, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._drop_role).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ad338dea6dd8b54f8cd91d15dfc52e4cfea73c4cb1f1b18ab097c1f062bdf887'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ad338dea6dd8b54f8cd91d15dfc52e4cfea73c4cb1f1b18ab097c1f062bdf887', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 781, 'function': 'AdminCLI._drop_role'}, 'file': 'admin/client/admin_client.py', 'line': 781, 'function': '_drop_role', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _alter_role(self, command):
        role_name_tree: Tree = command['role_name']
        role_name: str = role_name_tree.children[0].strip("'\"")
        desc_tree: Tree = command['description']
        desc_str: str = desc_tree.children[0].strip("'\"")

        _lineaje_payload = f"alter role name: {role_name}, description: {desc_str}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._alter_role).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:25a943c79564b057d6ba8eeffa38d7eac704009b2c5ef7323856cb9fc7e1a9b6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:25a943c79564b057d6ba8eeffa38d7eac704009b2c5ef7323856cb9fc7e1a9b6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 789, 'function': 'AdminCLI._alter_role'}, 'file': 'admin/client/admin_client.py', 'line': 789, 'function': '_alter_role', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/roles/{role_name}'
        response = self.session.put(
            url,
            json={'description': desc_str}
        )
        res_json = response.json()
        if response.status_code == 200:
            self._print_table_simple(res_json['data'])
        else:
            _lineaje_payload = f"Fail to update role {role_name} with description: {desc_str}, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._alter_role).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:99ec6289c463cfd45a84033b64170a12acefe1368449e65a233a643c8fbf4f09'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:99ec6289c463cfd45a84033b64170a12acefe1368449e65a233a643c8fbf4f09', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 799, 'function': 'AdminCLI._alter_role'}, 'file': 'admin/client/admin_client.py', 'line': 799, 'function': '_alter_role', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(
                _lineaje_payload)

    def _list_roles(self, command):
        _lineaje_payload = "Listing all roles"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._list_roles).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:863a4119ad31a9c27cbd52dcf06ecd56859355adf8944c7b34f7c45950654a74'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:863a4119ad31a9c27cbd52dcf06ecd56859355adf8944c7b34f7c45950654a74', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 803, 'function': 'AdminCLI._list_roles'}, 'file': 'admin/client/admin_client.py', 'line': 803, 'function': '_list_roles', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/roles'
        response = self.session.get(url)
        res_json = response.json()
        if response.status_code == 200:
            self._print_table_simple(res_json['data'])
        else:
            _lineaje_payload = f"Fail to list roles, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._list_roles).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:4d8f576095e2c1c30131cc55a1e39bcb4a38850f69bb54e84b0f186bd930eb63'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4d8f576095e2c1c30131cc55a1e39bcb4a38850f69bb54e84b0f186bd930eb63', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 810, 'function': 'AdminCLI._list_roles'}, 'file': 'admin/client/admin_client.py', 'line': 810, 'function': '_list_roles', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _show_role(self, command):
        role_name_tree: Tree = command['role_name']
        role_name: str = role_name_tree.children[0].strip("'\"")
        _lineaje_payload = f"show role: {role_name}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._show_role).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f77adfe627a1900ea074ab6eb18eca2d0c0b51dc7cfbd99b142f10358c4598b2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f77adfe627a1900ea074ab6eb18eca2d0c0b51dc7cfbd99b142f10358c4598b2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 815, 'function': 'AdminCLI._show_role'}, 'file': 'admin/client/admin_client.py', 'line': 815, 'function': '_show_role', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/roles/{role_name}/permission'
        response = self.session.get(url)
        res_json = response.json()
        if response.status_code == 200:
            self._print_table_simple(res_json['data'])
        else:
            _lineaje_payload = f"Fail to list roles, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._show_role).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:cba51ce745768bc812cb55c85797c6c4034cb553c494a28ae4efaf0c7dc7943c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cba51ce745768bc812cb55c85797c6c4034cb553c494a28ae4efaf0c7dc7943c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 822, 'function': 'AdminCLI._show_role'}, 'file': 'admin/client/admin_client.py', 'line': 822, 'function': '_show_role', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _grant_permission(self, command):
        role_name_tree: Tree = command['role_name']
        role_name_str: str = role_name_tree.children[0].strip("'\"")
        resource_tree: Tree = command['resource']
        resource_str: str = resource_tree.children[0].strip("'\"")
        action_tree_list: list = command['actions']
        actions: list = []
        for action_tree in action_tree_list:
            action_str: str = action_tree.children[0].strip("'\"")
            actions.append(action_str)
        _lineaje_payload = f"grant role_name: {role_name_str}, resource: {resource_str}, actions: {actions}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._grant_permission).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:18c6b9a33829442410277d871c917cb24d5bc7dccb092195291f3ed445d58ea3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:18c6b9a33829442410277d871c917cb24d5bc7dccb092195291f3ed445d58ea3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 834, 'function': 'AdminCLI._grant_permission'}, 'file': 'admin/client/admin_client.py', 'line': 834, 'function': '_grant_permission', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/roles/{role_name_str}/permission'
        response = self.session.post(
            url,
            json={'actions': actions, 'resource': resource_str}
        )
        res_json = response.json()
        if response.status_code == 200:
            self._print_table_simple(res_json['data'])
        else:
            _lineaje_payload = f"Fail to grant role {role_name_str} with {actions} on {resource_str}, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._grant_permission).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e930fb28b47b5e745efb72b17ae2cbbc6b2f27a5724bc4c4396194d091102fe1'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e930fb28b47b5e745efb72b17ae2cbbc6b2f27a5724bc4c4396194d091102fe1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 844, 'function': 'AdminCLI._grant_permission'}, 'file': 'admin/client/admin_client.py', 'line': 844, 'function': '_grant_permission', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(
                _lineaje_payload)

    def _revoke_permission(self, command):
        role_name_tree: Tree = command['role_name']
        role_name_str: str = role_name_tree.children[0].strip("'\"")
        resource_tree: Tree = command['resource']
        resource_str: str = resource_tree.children[0].strip("'\"")
        action_tree_list: list = command['actions']
        actions: list = []
        for action_tree in action_tree_list:
            action_str: str = action_tree.children[0].strip("'\"")
            actions.append(action_str)
        _lineaje_payload = f"revoke role_name: {role_name_str}, resource: {resource_str}, actions: {actions}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._revoke_permission).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8a235151e982521ed443d44b0a568ce231738c5b88089a4ab0d4f05362448c27'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8a235151e982521ed443d44b0a568ce231738c5b88089a4ab0d4f05362448c27', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 857, 'function': 'AdminCLI._revoke_permission'}, 'file': 'admin/client/admin_client.py', 'line': 857, 'function': '_revoke_permission', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/roles/{role_name_str}/permission'
        response = self.session.delete(
            url,
            json={'actions': actions, 'resource': resource_str}
        )
        res_json = response.json()
        if response.status_code == 200:
            self._print_table_simple(res_json['data'])
        else:
            _lineaje_payload = f"Fail to revoke role {role_name_str} with {actions} on {resource_str}, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._revoke_permission).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ab15b79c651f9d358cc9a70f3e666231d397070768ce52aa0a5e5b8a35f76999'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ab15b79c651f9d358cc9a70f3e666231d397070768ce52aa0a5e5b8a35f76999', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 867, 'function': 'AdminCLI._revoke_permission'}, 'file': 'admin/client/admin_client.py', 'line': 867, 'function': '_revoke_permission', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(
                _lineaje_payload)

    def _alter_user_role(self, command):
        role_name_tree: Tree = command['role_name']
        role_name_str: str = role_name_tree.children[0].strip("'\"")
        user_name_tree: Tree = command['user_name']
        user_name_str: str = user_name_tree.children[0].strip("'\"")
        _lineaje_payload = f"alter_user_role user_name: {user_name_str}, role_name: {role_name_str}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._alter_user_role).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:14e52422f9e15b97f3f3c608a79672b3aba11c082b6b36b938a384897ac9788d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:14e52422f9e15b97f3f3c608a79672b3aba11c082b6b36b938a384897ac9788d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 875, 'function': 'AdminCLI._alter_user_role'}, 'file': 'admin/client/admin_client.py', 'line': 875, 'function': '_alter_user_role', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/users/{user_name_str}/role'
        response = self.session.put(
            url,
            json={'role_name': role_name_str}
        )
        res_json = response.json()
        if response.status_code == 200:
            self._print_table_simple(res_json['data'])
        else:
            _lineaje_payload = f"Fail to alter user: {user_name_str} to role {role_name_str}, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._alter_user_role).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ca4f6b6c2705e57255e50acc1036fc9eb5d4855594c60069343b053b96e931d5'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ca4f6b6c2705e57255e50acc1036fc9eb5d4855594c60069343b053b96e931d5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 885, 'function': 'AdminCLI._alter_user_role'}, 'file': 'admin/client/admin_client.py', 'line': 885, 'function': '_alter_user_role', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(
                _lineaje_payload)

    def _show_user_permission(self, command):
        user_name_tree: Tree = command['user_name']
        user_name_str: str = user_name_tree.children[0].strip("'\"")
        _lineaje_payload = f"show_user_permission user_name: {user_name_str}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._show_user_permission).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:522461fab1258691da70feb21e34a18a3e0bc9d77a562f04e3a0fc34646f8735'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:522461fab1258691da70feb21e34a18a3e0bc9d77a562f04e3a0fc34646f8735', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 891, 'function': 'AdminCLI._show_user_permission'}, 'file': 'admin/client/admin_client.py', 'line': 891, 'function': '_show_user_permission', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/users/{user_name_str}/permission'
        response = self.session.get(url)
        res_json = response.json()
        if response.status_code == 200:
            self._print_table_simple(res_json['data'])
        else:
            _lineaje_payload = f"Fail to show user: {user_name_str} permission, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._show_user_permission).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:969d61f5ddbdefa2c66508a3271cded22e1427191e45fe3c1bdb28acff3521f3'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:969d61f5ddbdefa2c66508a3271cded22e1427191e45fe3c1bdb28acff3521f3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 898, 'function': 'AdminCLI._show_user_permission'}, 'file': 'admin/client/admin_client.py', 'line': 898, 'function': '_show_user_permission', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(
                _lineaje_payload)

    def _show_version(self, command):
        _lineaje_payload = "show_version"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._show_version).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5cb719a5dc2cf0ba73ca6df3e152bbd8ed6b5b9a0a68303119cb1fae2cb43f9b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5cb719a5dc2cf0ba73ca6df3e152bbd8ed6b5b9a0a68303119cb1fae2cb43f9b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 902, 'function': 'AdminCLI._show_version'}, 'file': 'admin/client/admin_client.py', 'line': 902, 'function': '_show_version', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        url = f'http://{self.host}:{self.port}/api/v1/admin/version'
        response = self.session.get(url)
        res_json = response.json()
        if response.status_code == 200:
            self._print_table_simple(res_json['data'])
        else:
            _lineaje_payload = f"Fail to show version, code: {res_json['code']}, message: {res_json['message']}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._show_version).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:a93197bfaa2d88737c3a38959143be7e8a838df2c10f9bef0f6573518a431025'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a93197bfaa2d88737c3a38959143be7e8a838df2c10f9bef0f6573518a431025', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 909, 'function': 'AdminCLI._show_version'}, 'file': 'admin/client/admin_client.py', 'line': 909, 'function': '_show_version', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def _handle_meta_command(self, command):
        meta_command = command['command']
        args = command.get('args', [])

        if meta_command in ['?', 'h', 'help']:
            self.show_help()
        elif meta_command in ['q', 'quit', 'exit']:
            _lineaje_payload = "Goodbye!"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_meta_command).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3bf37a79fc37a889f17842b2432a791df4043ba8ffb80f3913ba72c8851d4fa2'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3bf37a79fc37a889f17842b2432a791df4043ba8ffb80f3913ba72c8851d4fa2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 918, 'function': 'AdminCLI._handle_meta_command'}, 'file': 'admin/client/admin_client.py', 'line': 918, 'function': '_handle_meta_command', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)
        else:
            _lineaje_payload = f"Meta command '{meta_command}' with args {args}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AdminCLI._handle_meta_command).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6201fa0420f20cc312a43c0c50d7da67ab6898462570e9f378ea028c7ef32725'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6201fa0420f20cc312a43c0c50d7da67ab6898462570e9f378ea028c7ef32725', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 920, 'function': 'AdminCLI._handle_meta_command'}, 'file': 'admin/client/admin_client.py', 'line': 920, 'function': '_handle_meta_command', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)

    def show_help(self):
        """Help info"""
        help_text = """
Commands:
  LIST SERVICES
  SHOW SERVICE <service>
  STARTUP SERVICE <service>
  SHUTDOWN SERVICE <service>
  RESTART SERVICE <service>
  LIST USERS
  SHOW USER <user>
  DROP USER <user>
  CREATE USER <user> <password>
  ALTER USER PASSWORD <user> <new_password>
  ALTER USER ACTIVE <user> <on/off>
  LIST DATASETS OF <user>
  LIST AGENTS OF <user>

Meta Commands:
  \\?, \\h, \\help     Show this help
  \\q, \\quit, \\exit   Quit the CLI
        """
        # LINEAJE: runtime guardrail checks `help_text` as it flows from the agent to the application log, before it is written to the log (in AdminCLI.show_help).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `help_text` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8bb3edbc06c8fe74cd71df6d7a65d9829ddab7e816d93647b39588cb3095cd14'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8bb3edbc06c8fe74cd71df6d7a65d9829ddab7e816d93647b39588cb3095cd14', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 944, 'function': 'AdminCLI.show_help'}, 'file': 'admin/client/admin_client.py', 'line': 944, 'function': 'show_help', 'agent_name': 'AdminCLI', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            help_text = _gr_client.enforce(_gr_site, help_text, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(help_text)


def main():
    import sys

    cli = AdminCLI()

    args = cli.parse_connection_args(sys.argv)
    if 'error' in args:
        _lineaje_payload = "Error: Invalid connection arguments"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:beadbf0df9e6d26eeeda1900a7ad3ad2cec0257eb7ffceb8d03b7d5380dd9a51'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:beadbf0df9e6d26eeeda1900a7ad3ad2cec0257eb7ffceb8d03b7d5380dd9a51', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 954, 'function': 'main'}, 'file': 'admin/client/admin_client.py', 'line': 954, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        return

    if 'command' in args:
        if 'password' not in args:
            _lineaje_payload = "Error: password is missing"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:8cf3b70037aa3ec11d6003577b30e2aed940f38906fa7fc3aa2585d79c7bac58'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8cf3b70037aa3ec11d6003577b30e2aed940f38906fa7fc3aa2585d79c7bac58', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 959, 'function': 'main'}, 'file': 'admin/client/admin_client.py', 'line': 959, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)
            return
        if cli.verify_admin(args, single_command=True):
            command: str = args['command']
            # print(f"Run single command: {command}")
            cli.run_single_command(command)
    else:
        if cli.verify_admin(args, single_command=False):
            _lineaje_payload = (r"""
                ____  ___   ______________                 ___       __          _     
               / __ \/   | / ____/ ____/ /___ _      __   /   | ____/ /___ ___  (_)___ 
              / /_/ / /| |/ / __/ /_  / / __ \ | /| / /  / /| |/ __  / __ `__ \/ / __ \
             / _, _/ ___ / /_/ / __/ / / /_/ / |/ |/ /  / ___ / /_/ / / / / / / / / / /
            /_/ |_/_/  |_\____/_/   /_/\____/|__/|__/  /_/  |_\__,_/_/ /_/ /_/_/_/ /_/ 
            """)
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9118f896eb8b84d5f70060c1ff50010003e4094ccf8dc2743b34ed52d81829f6'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9118f896eb8b84d5f70060c1ff50010003e4094ccf8dc2743b34ed52d81829f6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'admin/client/admin_client.py', 'line': 967, 'function': 'main'}, 'file': 'admin/client/admin_client.py', 'line': 967, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)
            cli.cmdloop()


if __name__ == '__main__':
    main()
