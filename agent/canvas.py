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
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
import asyncio
import base64
import inspect
import binascii
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from functools import partial
from typing import Any, Union, Tuple

from agent.component import component_class
from agent.component.base import ComponentBase
from api.db.services.file_service import FileService
from api.db.services.llm_service import LLMBundle
from api.db.services.task_service import has_canceled
from common.constants import LLMType
from common.misc_utils import get_uuid, hash_str2int
from common.exceptions import TaskCanceledException
from rag.prompts.generator import chunks_format
from rag.utils.redis_conn import REDIS_CONN

class Graph:
    """
        dsl = {
            "components": {
                "begin": {
                    "obj":{
                        "component_name": "Begin",
                        "params": {},
                    },
                    "downstream": ["answer_0"],
                    "upstream": [],
                },
                "retrieval_0": {
                    "obj": {
                        "component_name": "Retrieval",
                        "params": {}
                    },
                    "downstream": ["generate_0"],
                    "upstream": ["answer_0"],
                },
                "generate_0": {
                    "obj": {
                        "component_name": "Generate",
                        "params": {}
                    },
                    "downstream": ["answer_0"],
                    "upstream": ["retrieval_0"],
                }
            },
            "history": [],
            "path": ["begin"],
            "retrieval": {"chunks": [], "doc_aggs": []},
            "globals": {
                "sys.query": "",
                "sys.user_id": tenant_id,
                "sys.conversation_turns": 0,
                "sys.files": []
            }
        }
        """

    def __init__(self, dsl: str, tenant_id=None, task_id=None):
        self.path = []
        self.components = {}
        self.error = ""
        self.dsl = json.loads(dsl)
        self._tenant_id = tenant_id
        self.task_id = task_id if task_id else get_uuid()
        self._thread_pool = ThreadPoolExecutor(max_workers=5)
        self.load()

    def load(self):
        self.components = self.dsl["components"]
        cpn_nms = set([])
        for k, cpn in self.components.items():
            cpn_nms.add(cpn["obj"]["component_name"])
            param = component_class(cpn["obj"]["component_name"] + "Param")()
            param.update(cpn["obj"]["params"])
            try:
                param.check()
            except Exception as e:
                raise ValueError(self.get_component_name(k) + f": {e}")

            cpn["obj"] = component_class(cpn["obj"]["component_name"])(self, k, param)

        self.path = self.dsl["path"]

    def __str__(self):
        self.dsl["path"] = self.path
        self.dsl["task_id"] = self.task_id
        dsl = {
            "components": {}
        }
        for k in self.dsl.keys():
            if k in ["components"]:
                continue
            dsl[k] = deepcopy(self.dsl[k])

        for k, cpn in self.components.items():
            if k not in dsl["components"]:
                dsl["components"][k] = {}
            for c in cpn.keys():
                if c == "obj":
                    dsl["components"][k][c] = json.loads(str(cpn["obj"]))
                    continue
                dsl["components"][k][c] = deepcopy(cpn[c])
        # LINEAJE: runtime guardrail checks `dsl` as it flows from the agent to an external endpoint, before it leaves the application (in Graph.__str__).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `dsl` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:2d12b1aeb54e2748ed43adda385d6de9a1827653be5f62b591843820bbb2fe8b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2d12b1aeb54e2748ed43adda385d6de9a1827653be5f62b591843820bbb2fe8b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 126, 'function': 'Graph.__str__'}, 'file': 'agent/canvas.py', 'line': 126, 'function': '__str__', 'agent_name': 'Graph', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            dsl = _gr_client.enforce(_gr_site, dsl, content_type='application/json', variable_name='dsl', source_file=__file__, before_line=126)
        except _gr_client.GuardrailUnavailableError:
            pass
        return json.dumps(dsl, ensure_ascii=False)

    def reset(self):
        self.path = []
        for k, cpn in self.components.items():
            self.components[k]["obj"].reset()
        try:
            REDIS_CONN.delete(f"{self.task_id}-logs")
            REDIS_CONN.delete(f"{self.task_id}-cancel")
        except Exception as e:
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in Graph.reset).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f7ad8dae67022a6c77dd7d3a0dd2d088a37c2a8c75528e98ba6ceb16f1f4a67f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f7ad8dae67022a6c77dd7d3a0dd2d088a37c2a8c75528e98ba6ceb16f1f4a67f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 136, 'function': 'Graph.reset'}, 'file': 'agent/canvas.py', 'line': 136, 'function': 'reset', 'agent_name': 'Graph', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                e = _gr_client.enforce(_gr_site, e, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)

    def get_component_name(self, cid):
        for n in self.dsl.get("graph", {}).get("nodes", []):
            if cid == n["id"]:
                return n["data"]["name"]
        return ""

    def run(self, **kwargs):
        raise NotImplementedError()

    def get_component(self, cpn_id) -> Union[None, dict[str, Any]]:
        return self.components.get(cpn_id)

    def get_component_obj(self, cpn_id) -> ComponentBase:
        return self.components.get(cpn_id)["obj"]

    def get_component_type(self, cpn_id) -> str:
        return self.components.get(cpn_id)["obj"].component_name

    def get_component_input_form(self, cpn_id) -> dict:
        return self.components.get(cpn_id)["obj"].get_input_form()

    def get_tenant_id(self):
        return self._tenant_id

    def get_value_with_variable(self,value: str) -> Any:
        pat = re.compile(r"\{* *\{([a-zA-Z:0-9]+@[A-Za-z0-9_.-]+|sys\.[A-Za-z0-9_.]+|env\.[A-Za-z0-9_.]+)\} *\}*")
        out_parts = []
        last = 0

        for m in pat.finditer(value):
            out_parts.append(value[last:m.start()])
            key = m.group(1)
            v = self.get_variable_value(key)
            if v is None:
                rep = ""
            elif isinstance(v, partial):
                buf = []
                for chunk in v():
                    buf.append(chunk)
                rep = "".join(buf)
            elif isinstance(v, str):
                rep = v
            else:
                # LINEAJE: runtime guardrail checks `v` as it flows from the agent to an external endpoint, before it leaves the application (in Graph.get_value_with_variable).
                #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `v` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:b20d82e9352ca373f546c4370557bc3c13f35468889fe6b929a5b02c558a6d91'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b20d82e9352ca373f546c4370557bc3c13f35468889fe6b929a5b02c558a6d91', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 181, 'function': 'Graph.get_value_with_variable'}, 'file': 'agent/canvas.py', 'line': 181, 'function': 'get_value_with_variable', 'agent_name': 'Graph', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    v = _gr_client.enforce(_gr_site, v, content_type='application/json', variable_name='v', source_file=__file__, before_line=181)
                except _gr_client.GuardrailUnavailableError:
                    pass
                rep = json.dumps(v, ensure_ascii=False)

            out_parts.append(rep)
            last = m.end()

        out_parts.append(value[last:])
        return("".join(out_parts))

    def get_variable_value(self, exp: str) -> Any:
        exp = exp.strip("{").strip("}").strip(" ").strip("{").strip("}")
        if exp.find("@") < 0:
            return self.globals[exp]
        cpn_id, var_nm = exp.split("@")
        cpn = self.get_component(cpn_id)
        if not cpn:
            raise Exception(f"Can't find variable: '{cpn_id}@{var_nm}'")
        parts = var_nm.split(".", 1)
        root_key = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        root_val = cpn["obj"].output(root_key)

        if not rest:
            # LINEAJE: runtime guardrail checks `root_val` as it flows from the agent to the user interface, before it leaves the application (in Graph.get_variable_value).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `root_val` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9b128d6698ecdd3e4ae694f0bf5be0c138f15de0fb404bbfdbb3c064c11e5842'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9b128d6698ecdd3e4ae694f0bf5be0c138f15de0fb404bbfdbb3c064c11e5842', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 203, 'function': 'Graph.get_variable_value'}, 'file': 'agent/canvas.py', 'line': 203, 'function': 'get_variable_value', 'agent_name': 'Graph', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                root_val = _gr_client.enforce(_gr_site, root_val, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return root_val
        return self.get_variable_param_value(root_val,rest)

    def get_variable_param_value(self, obj: Any, path: str) -> Any:
        cur = obj
        if not path:
            # LINEAJE: runtime guardrail checks `cur` as it flows from the agent to the user interface, before it leaves the application (in Graph.get_variable_param_value).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `cur` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:39cc19674c3bf61b1686c14e1dbd5746caecb301a518c7ae25e13ff19a955588'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:39cc19674c3bf61b1686c14e1dbd5746caecb301a518c7ae25e13ff19a955588', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 209, 'function': 'Graph.get_variable_param_value'}, 'file': 'agent/canvas.py', 'line': 209, 'function': 'get_variable_param_value', 'agent_name': 'Graph', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                cur = _gr_client.enforce(_gr_site, cur, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return cur
        for key in path.split('.'):
            if cur is None:
                return None

            if isinstance(cur, str):
                try:
                    cur = json.loads(cur)
                except Exception:
                    return None

            if isinstance(cur, dict):
                cur = cur.get(key)
                continue

            if isinstance(cur, (list, tuple)):
                try:
                    idx = int(key)
                    cur = cur[idx]
                except Exception:
                    return None
                continue

            cur = getattr(cur, key, None)
        # LINEAJE: runtime guardrail checks `cur` as it flows from the agent to the user interface, before it leaves the application (in Graph.get_variable_param_value).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `cur` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:0ffde5f6504dc27fc2ebc62d98bed5dbc3d58340f64a41555ec5affe5a36dd4b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0ffde5f6504dc27fc2ebc62d98bed5dbc3d58340f64a41555ec5affe5a36dd4b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 233, 'function': 'Graph.get_variable_param_value'}, 'file': 'agent/canvas.py', 'line': 233, 'function': 'get_variable_param_value', 'agent_name': 'Graph', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            cur = _gr_client.enforce(_gr_site, cur, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return cur

    def set_variable_value(self, exp: str,value):
        exp = exp.strip("{").strip("}").strip(" ").strip("{").strip("}")
        if exp.find("@") < 0:
            self.globals[exp] = value
            return
        cpn_id, var_nm = exp.split("@")
        cpn = self.get_component(cpn_id)
        if not cpn:
            raise Exception(f"Can't find variable: '{cpn_id}@{var_nm}'")
        parts = var_nm.split(".", 1)
        root_key = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        if not rest:
            cpn["obj"].set_output(root_key, value)
            return
        root_val = cpn["obj"].output(root_key)
        if not root_val:
            root_val = {}
        cpn["obj"].set_output(root_key, self.set_variable_param_value(root_val,rest,value))

    def set_variable_param_value(self, obj: Any, path: str, value) -> Any:
        cur = obj
        keys = path.split('.')
        if not path:
            # LINEAJE: runtime guardrail checks `value` as it flows from the agent to the user interface, before it leaves the application (in Graph.set_variable_param_value).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `value` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:79ea3cc4dee256774bd40dec5acf1aec851c1080af0c5228ff816fbabc0fc588'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:79ea3cc4dee256774bd40dec5acf1aec851c1080af0c5228ff816fbabc0fc588', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 259, 'function': 'Graph.set_variable_param_value'}, 'file': 'agent/canvas.py', 'line': 259, 'function': 'set_variable_param_value', 'agent_name': 'Graph', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                value = _gr_client.enforce(_gr_site, value, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return value
        for key in keys:
            if key not in cur or not isinstance(cur[key], dict):
                cur[key] = {}
            cur = cur[key]
        cur[keys[-1]] = value
        # LINEAJE: runtime guardrail checks `obj` as it flows from the agent to the user interface, before it leaves the application (in Graph.set_variable_param_value).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `obj` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ebba10cddf9a6f8189585a13595d1d0affa3345cdab0410c61bbad0f605962e6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ebba10cddf9a6f8189585a13595d1d0affa3345cdab0410c61bbad0f605962e6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 265, 'function': 'Graph.set_variable_param_value'}, 'file': 'agent/canvas.py', 'line': 265, 'function': 'set_variable_param_value', 'agent_name': 'Graph', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            obj = _gr_client.enforce(_gr_site, obj, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return obj

    def is_canceled(self) -> bool:
        return has_canceled(self.task_id)

    def cancel_task(self) -> bool:
        try:
            REDIS_CONN.set(f"{self.task_id}-cancel", "x")
        except Exception as e:
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in Graph.cancel_task).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9d205b1e23443a7da1973eeed9f0af306a6896d35526b32d0ea22185dc266f54'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9d205b1e23443a7da1973eeed9f0af306a6896d35526b32d0ea22185dc266f54', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 274, 'function': 'Graph.cancel_task'}, 'file': 'agent/canvas.py', 'line': 274, 'function': 'cancel_task', 'agent_name': 'Graph', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                e = _gr_client.enforce(_gr_site, e, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)
            return False
        return True


class Canvas(Graph):

    def __init__(self, dsl: str, tenant_id=None, task_id=None):
        self.globals = {
            "sys.query": "",
            "sys.user_id": tenant_id,
            "sys.conversation_turns": 0,
            "sys.files": []
        }
        self.variables = {}
        super().__init__(dsl, tenant_id, task_id)

    def load(self):
        super().load()
        self.history = self.dsl["history"]
        if "globals" in self.dsl:
            self.globals = self.dsl["globals"]
        else:
            self.globals = {
            "sys.query": "",
            "sys.user_id": "",
            "sys.conversation_turns": 0,
            "sys.files": []
        }
        if "variables" in self.dsl:
            self.variables = self.dsl["variables"]
        else:
            self.variables = {}

        self.retrieval = self.dsl["retrieval"]
        self.memory = self.dsl.get("memory", [])

    def __str__(self):
        self.dsl["history"] = self.history
        self.dsl["retrieval"] = self.retrieval
        self.dsl["memory"] = self.memory
        return super().__str__()

    def reset(self, mem=False):
        super().reset()
        if not mem:
            self.history = []
            self.retrieval = []
            self.memory = []
        _lineaje_payload = self.variables
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Canvas.reset).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:eac373ae33fc13e460b82c9728bdb4a3fefd2bcb2d47ccbb357a042b1bb00248'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:eac373ae33fc13e460b82c9728bdb4a3fefd2bcb2d47ccbb357a042b1bb00248', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 323, 'function': 'Canvas.reset'}, 'file': 'agent/canvas.py', 'line': 323, 'function': 'reset', 'agent_name': 'Canvas', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        for k in self.globals.keys():
            if k.startswith("sys."):
                if isinstance(self.globals[k], str):
                    self.globals[k] = ""
                elif isinstance(self.globals[k], int):
                    self.globals[k] = 0
                elif isinstance(self.globals[k], float):
                    self.globals[k] = 0
                elif isinstance(self.globals[k], list):
                    self.globals[k] = []
                elif isinstance(self.globals[k], dict):
                    self.globals[k] = {}
                else:
                    self.globals[k] = None
            if k.startswith("env."):
                key = k[4:]
                if key in self.variables:
                    variable = self.variables[key]
                    if variable["value"]:
                        self.globals[k] = variable["value"]
                    else:
                        if variable["type"] == "string":
                            self.globals[k] = ""
                        elif variable["type"] == "number":
                            self.globals[k] = 0
                        elif variable["type"] == "boolean":
                            self.globals[k] = False
                        elif variable["type"] == "object":
                            self.globals[k] = {}
                        elif variable["type"].startswith("array"):
                            self.globals[k] = []
                        else:
                            self.globals[k] = ""
                else:
                    self.globals[k] = ""

    async def run(self, **kwargs):
        st = time.perf_counter()
        self._loop = asyncio.get_running_loop()
        self.message_id = get_uuid()
        created_at = int(time.time())
        self.add_user_input(kwargs.get("query"))
        for k, cpn in self.components.items():
            self.components[k]["obj"].reset(True)

        if kwargs.get("webhook_payload"):
            for k, cpn in self.components.items():
                if self.components[k]["obj"].component_name.lower() == "begin"  and self.components[k]["obj"]._param.mode == "Webhook":
                    payload = kwargs.get("webhook_payload", {})
                    if "input" in payload:
                        self.components[k]["obj"].set_input_value("request", payload["input"])
                    for kk, vv in payload.items():
                        if kk == "input":
                            continue
                        self.components[k]["obj"].set_output(kk, vv)

        for k in kwargs.keys():
            if k in ["query", "user_id", "files"] and kwargs[k]:
                if k == "files":
                    self.globals[f"sys.{k}"] = await self.get_files_async(kwargs[k])
                else:
                    self.globals[f"sys.{k}"] = kwargs[k]
        if not self.globals["sys.conversation_turns"] :
            self.globals["sys.conversation_turns"] = 0
        self.globals["sys.conversation_turns"] += 1

        def decorate(event, dt):
            nonlocal created_at
            return {
                "event": event,
                #"conversation_id": "f3cc152b-24b0-4258-a1a1-7d5e9fc8a115",
                "message_id": self.message_id,
                "created_at": created_at,
                "task_id": self.task_id,
                "data": dt
            }

        if not self.path or self.path[-1].lower().find("userfillup") < 0:
            self.path.append("begin")
            self.retrieval.append({"chunks": [], "doc_aggs": []})

        if self.is_canceled():
            msg = f"Task {self.task_id} has been canceled before starting."
            # LINEAJE: runtime guardrail checks `msg` as it flows from the agent to the application log, before it is written to the log (in Canvas.decorate).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:438264d3792a77c07f926c92afa5fccaee9a299b309a6197ec5eb72659548959'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:438264d3792a77c07f926c92afa5fccaee9a299b309a6197ec5eb72659548959', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 407, 'function': 'Canvas.run'}, 'file': 'agent/canvas.py', 'line': 407, 'function': 'decorate', 'agent_name': 'Canvas', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                msg = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, msg, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(msg)
            raise TaskCanceledException(msg)

        yield decorate("workflow_started", {"inputs": kwargs.get("inputs")})
        self.retrieval.append({"chunks": {}, "doc_aggs": {}})

        async def _run_batch(f, t):
            if self.is_canceled():
                msg = f"Task {self.task_id} has been canceled during batch execution."
                # LINEAJE: runtime guardrail checks `msg` as it flows from the agent to the application log, before it is written to the log (in Canvas._run_batch).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:4be9e09a6baaf02296150866f83e7d6881b597f2a0748458dbf1bf6f68f40e1c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4be9e09a6baaf02296150866f83e7d6881b597f2a0748458dbf1bf6f68f40e1c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 416, 'function': 'Canvas.run._run_batch'}, 'file': 'agent/canvas.py', 'line': 416, 'function': '_run_batch', 'agent_name': 'Canvas', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    msg = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, msg, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(msg)
                raise TaskCanceledException(msg)

            loop = asyncio.get_running_loop()
            tasks = []

            def _run_async_in_thread(coro_func, **call_kwargs):
                return asyncio.run(coro_func(**call_kwargs))

            i = f
            while i < t:
                cpn = self.get_component_obj(self.path[i])
                task_fn = None
                call_kwargs = None

                if cpn.component_name.lower() in ["begin", "userfillup"]:
                    call_kwargs = {"inputs": kwargs.get("inputs", {})}
                    task_fn = cpn.invoke
                    i += 1
                else:
                    for _, ele in cpn.get_input_elements().items():
                        if isinstance(ele, dict) and ele.get("_cpn_id") and ele.get("_cpn_id") not in self.path[:i] and self.path[0].lower().find("userfillup") < 0:
                            self.path.pop(i)
                            t -= 1
                            break
                    else:
                        call_kwargs = cpn.get_input()
                        task_fn = cpn.invoke
                        i += 1

                if task_fn is None:
                    continue

                invoke_async = getattr(cpn, "invoke_async", None)
                if invoke_async and asyncio.iscoroutinefunction(invoke_async):
                    tasks.append(loop.run_in_executor(self._thread_pool, partial(_run_async_in_thread, invoke_async, **(call_kwargs or {}))))
                else:
                    tasks.append(loop.run_in_executor(self._thread_pool, partial(task_fn, **(call_kwargs or {}))))

            if tasks:
                await asyncio.gather(*tasks)

        def _node_finished(cpn_obj):
            return decorate("node_finished",{
                           "inputs": cpn_obj.get_input_values(),
                           "outputs": cpn_obj.output(),
                           "component_id": cpn_obj._id,
                           "component_name": self.get_component_name(cpn_obj._id),
                           "component_type": self.get_component_type(cpn_obj._id),
                           "error": cpn_obj.error(),
                           "elapsed_time": time.perf_counter() - cpn_obj.output("_created_time"),
                           "created_at": cpn_obj.output("_created_time"),
                       })

        self.error = ""
        idx = len(self.path) - 1
        partials = []
        tts_mdl = None
        while idx < len(self.path):
            to = len(self.path)
            for i in range(idx, to):
                yield decorate("node_started", {
                    "inputs": None, "created_at": int(time.time()),
                    "component_id": self.path[i],
                    "component_name": self.get_component_name(self.path[i]),
                    "component_type": self.get_component_type(self.path[i]),
                    "thoughts": self.get_component_thoughts(self.path[i])
                })
            await _run_batch(idx, to)
            to = len(self.path)
            # post-processing of components invocation
            for i in range(idx, to):
                cpn = self.get_component(self.path[i])
                cpn_obj = self.get_component_obj(self.path[i])
                if cpn_obj.component_name.lower() == "message":
                    if cpn_obj.get_param("auto_play"):
                        tts_mdl = LLMBundle(self._tenant_id, LLMType.TTS)
                    if isinstance(cpn_obj.output("content"), partial):
                        _m = ""
                        buff_m = ""
                        stream = cpn_obj.output("content")()
                        async def _process_stream(m):
                            nonlocal buff_m, _m, tts_mdl
                            if not m:
                                return
                            if m == "<think>":
                                return decorate("message", {"content": "", "start_to_think": True})

                            elif m == "</think>":
                                return decorate("message", {"content": "", "end_to_think": True})

                            buff_m += m
                            _m += m

                            if len(buff_m) > 16:
                                ev = decorate(
                                    "message",
                                    {
                                        "content": m,
                                        "audio_binary": self.tts(tts_mdl, buff_m)
                                    }
                                )
                                buff_m = ""
                                # LINEAJE: runtime guardrail checks `ev` as it flows from the agent to the user interface, before it leaves the application (in Canvas._process_stream).
                                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `ev` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                                #   Do not remove without review. site_id='site:sha256:4a8beca25e629b92130bd78972e9e37a7154cf95a488e98a1a785deaec292322'
                                _gr_client = _lineaje_load_gr_client()
                                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4a8beca25e629b92130bd78972e9e37a7154cf95a488e98a1a785deaec292322', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 519, 'function': 'Canvas.run'}, 'file': 'agent/canvas.py', 'line': 519, 'function': '_process_stream', 'agent_name': 'Canvas', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                                try:
                                    ev = _gr_client.enforce(_gr_site, ev, content_type='text/plain')
                                except _gr_client.GuardrailUnavailableError:
                                    pass
                                except PermissionError:
                                    pass
                                return ev

                            return decorate("message", {"content": m})

                        if inspect.isasyncgen(stream):
                            async for m in stream:
                                ev= await _process_stream(m)
                                if ev:
                                    yield ev
                        else:
                            for m in stream:
                                ev= await _process_stream(m)
                                if ev:
                                    yield ev
                        if buff_m:
                            yield decorate("message", {"content": "", "audio_binary": self.tts(tts_mdl, buff_m)})
                            buff_m = ""
                        cpn_obj.set_output("content", _m)
                        cite = re.search(r"\[ID:[ 0-9]+\]", _m)
                    else:
                        yield decorate("message", {"content": cpn_obj.output("content")})
                        cite = re.search(r"\[ID:[ 0-9]+\]",  cpn_obj.output("content"))

                    message_end = {}
                    if cpn_obj.get_param("status"):
                        message_end["status"] = cpn_obj.get_param("status")
                    if isinstance(cpn_obj.output("attachment"), dict):
                        message_end["attachment"] = cpn_obj.output("attachment")
                    if cite:
                        message_end["reference"] = self.get_reference()
                    yield decorate("message_end", message_end)

                    while partials:
                        _cpn_obj = self.get_component_obj(partials[0])
                        if isinstance(_cpn_obj.output("content"), partial):
                            break
                        yield _node_finished(_cpn_obj)
                        partials.pop(0)

                other_branch = False
                if cpn_obj.error():
                    ex = cpn_obj.exception_handler()
                    if ex and ex["goto"]:
                        self.path.extend(ex["goto"])
                        other_branch = True
                    elif ex and ex["default_value"]:
                        yield decorate("message", {"content": ex["default_value"]})
                        yield decorate("message_end", {})
                    else:
                        self.error = cpn_obj.error()

                if cpn_obj.component_name.lower() not in ("iteration","loop"):
                    if isinstance(cpn_obj.output("content"), partial):
                        if self.error:
                            cpn_obj.set_output("content", None)
                            yield _node_finished(cpn_obj)
                        else:
                            partials.append(self.path[i])
                    else:
                        yield _node_finished(cpn_obj)

                def _append_path(cpn_id):
                    nonlocal other_branch
                    if other_branch:
                        return
                    if self.path[-1] == cpn_id:
                        return
                    self.path.append(cpn_id)

                def _extend_path(cpn_ids):
                    nonlocal other_branch
                    if other_branch:
                        return
                    for cpn_id in cpn_ids:
                        _append_path(cpn_id)

                if cpn_obj.component_name.lower() in ("iterationitem","loopitem") and cpn_obj.end():
                    iter = cpn_obj.get_parent()
                    yield _node_finished(iter)
                    _extend_path(self.get_component(cpn["parent_id"])["downstream"])
                elif cpn_obj.component_name.lower() in ["categorize", "switch"]:
                    _extend_path(cpn_obj.output("_next"))
                elif cpn_obj.component_name.lower() in ("iteration", "loop"):
                    _append_path(cpn_obj.get_start())
                elif cpn_obj.component_name.lower() == "exitloop" and cpn_obj.get_parent().component_name.lower() == "loop":
                    _extend_path(self.get_component(cpn["parent_id"])["downstream"])
                elif not cpn["downstream"] and cpn_obj.get_parent():
                    _append_path(cpn_obj.get_parent().get_start())
                else:
                    _extend_path(cpn["downstream"])

            if self.error:
                _lineaje_payload = f"Runtime Error: {self.error}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Canvas._node_finished).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:57a44ba2cb127a6ea5faec724fe7bfd2ee51fd3d350fb55fac2e7b92f1a9831b'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:57a44ba2cb127a6ea5faec724fe7bfd2ee51fd3d350fb55fac2e7b92f1a9831b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 611, 'function': 'Canvas.run'}, 'file': 'agent/canvas.py', 'line': 611, 'function': '_node_finished', 'agent_name': 'Canvas', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                break
            idx = to

            if any([self.get_component_obj(c).component_name.lower() == "userfillup" for c in self.path[idx:]]):
                path = [c for c in self.path[idx:] if self.get_component(c)["obj"].component_name.lower() == "userfillup"]
                path.extend([c for c in self.path[idx:] if self.get_component(c)["obj"].component_name.lower() != "userfillup"])
                another_inputs = {}
                tips = ""
                for c in path:
                    o = self.get_component_obj(c)
                    if o.component_name.lower() == "userfillup":
                        o.invoke()
                        another_inputs.update(o.get_input_elements())
                        if o.get_param("enable_tips"):
                            tips = o.output("tips")
                self.path = path
                yield decorate("user_inputs", {"inputs": another_inputs, "tips": tips})
                return
        self.path = self.path[:idx]
        if not self.error:
            yield decorate("workflow_finished",
                       {
                           "inputs": kwargs.get("inputs"),
                           "outputs": self.get_component_obj(self.path[-1]).output(),
                           "elapsed_time": time.perf_counter() - st,
                           "created_at": st,
                       })
            self.history.append(("assistant", self.get_component_obj(self.path[-1]).output()))
        elif "Task has been canceled" in self.error:
            yield decorate("workflow_finished",
                       {
                           "inputs": kwargs.get("inputs"),
                           "outputs": "Task has been canceled",
                           "elapsed_time": time.perf_counter() - st,
                           "created_at": st,
                       })

    def is_reff(self, exp: str) -> bool:
        exp = exp.strip("{").strip("}")
        if exp.find("@") < 0:
            return exp in self.globals
        arr = exp.split("@")
        if len(arr) != 2:
            return False
        if self.get_component(arr[0]) is None:
            return False
        return True


    def tts(self,tts_mdl, text):
        def clean_tts_text(text: str) -> str:
            if not text:
                return ""

            text = text.encode("utf-8", "ignore").decode("utf-8", "ignore")

            text = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", text)

            emoji_pattern = re.compile(
                "[\U0001F600-\U0001F64F"
                "\U0001F300-\U0001F5FF"
                "\U0001F680-\U0001F6FF"
                "\U0001F1E0-\U0001F1FF"
                "\U00002700-\U000027BF"
                "\U0001F900-\U0001F9FF"
                "\U0001FA70-\U0001FAFF"
                "\U0001FAD0-\U0001FAFF]+",
                flags=re.UNICODE
            )
            text = emoji_pattern.sub("", text)

            text = re.sub(r"\s+", " ", text).strip()

            MAX_LEN = 500
            if len(text) > MAX_LEN:
                text = text[:MAX_LEN]

            # LINEAJE: runtime guardrail checks `text` as it flows from the agent to the user interface, before it leaves the application (in Canvas.clean_tts_text).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `text` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:690671276a292370bc946969f8f6570fa3b9c7b466a0da9927bb7c27897eaeef'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:690671276a292370bc946969f8f6570fa3b9c7b466a0da9927bb7c27897eaeef', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 689, 'function': 'Canvas.tts.clean_tts_text'}, 'file': 'agent/canvas.py', 'line': 689, 'function': 'clean_tts_text', 'agent_name': 'Canvas', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                text = _gr_client.enforce(_gr_site, text, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return text
        if not tts_mdl or not text:
            return None
        text = clean_tts_text(text)
        if not text:
            return None
        bin = b""
        try:
            for chunk in tts_mdl.tts(text):
                bin += chunk
        except Exception as e:
            _lineaje_payload = f"TTS failed: {e}, text={text!r}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Canvas.clean_tts_text).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:8821b3cbf419ea6683708b60f51f6e8fb74d4d63611c32de1363564226bda0b8'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8821b3cbf419ea6683708b60f51f6e8fb74d4d63611c32de1363564226bda0b8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 700, 'function': 'Canvas.tts'}, 'file': 'agent/canvas.py', 'line': 700, 'function': 'clean_tts_text', 'agent_name': 'Canvas', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            return None
        return binascii.hexlify(bin).decode("utf-8")

    def get_history(self, window_size):
        convs = []
        if window_size <= 0:
            # LINEAJE: runtime guardrail checks `convs` as it flows from the agent to the user interface, before it leaves the application (in Canvas.get_history).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `convs` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f285f0712277919c91c7c3c2c896ac0ad4029568811d48995ce941df10b1e009'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f285f0712277919c91c7c3c2c896ac0ad4029568811d48995ce941df10b1e009', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 707, 'function': 'Canvas.get_history'}, 'file': 'agent/canvas.py', 'line': 707, 'function': 'get_history', 'agent_name': 'Canvas', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                convs = _gr_client.enforce(_gr_site, convs, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return convs
        for role, obj in self.history[window_size * -2:]:
            if isinstance(obj, dict):
                convs.append({"role": role, "content": obj.get("content", "")})
            else:
                convs.append({"role": role, "content": str(obj)})
        # LINEAJE: runtime guardrail checks `convs` as it flows from the agent to the user interface, before it leaves the application (in Canvas.get_history).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `convs` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:dcdadaef24fbffe975353256f14934131c8c4363880fa593bc342c39176b9920'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dcdadaef24fbffe975353256f14934131c8c4363880fa593bc342c39176b9920', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 713, 'function': 'Canvas.get_history'}, 'file': 'agent/canvas.py', 'line': 713, 'function': 'get_history', 'agent_name': 'Canvas', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            convs = _gr_client.enforce(_gr_site, convs, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return convs

    def add_user_input(self, question):
        self.history.append(("user", question))

    def get_prologue(self):
        return self.components["begin"]["obj"]._param.prologue

    def get_mode(self):
        return self.components["begin"]["obj"]._param.mode

    def set_global_param(self, **kwargs):
        self.globals.update(kwargs)

    def get_preset_param(self):
        return self.components["begin"]["obj"]._param.inputs

    def get_component_input_elements(self, cpnnm):
        return self.components[cpnnm]["obj"].get_input_elements()

    async def get_files_async(self, files: Union[None, list[dict]]) -> list[str]:
        if not files:
            return  []
        def image_to_base64(file):
            return "data:{};base64,{}".format(file["mime_type"],
                                        base64.b64encode(FileService.get_blob(file["created_by"], file["id"])).decode("utf-8"))
        loop = asyncio.get_running_loop()
        tasks = []
        for file in files:
            if file["mime_type"].find("image") >=0:
                tasks.append(loop.run_in_executor(self._thread_pool, image_to_base64, file))
                continue
            tasks.append(loop.run_in_executor(self._thread_pool, FileService.parse, file["name"], FileService.get_blob(file["created_by"], file["id"]), True, file["created_by"]))
        return await asyncio.gather(*tasks)

    def get_files(self, files: Union[None, list[dict]]) -> list[str]:
        """
        Synchronous wrapper for get_files_async, used by sync component invoke paths.
        """
        loop = getattr(self, "_loop", None)
        if loop and loop.is_running():
            return asyncio.run_coroutine_threadsafe(self.get_files_async(files), loop).result()

        return asyncio.run(self.get_files_async(files))

    def tool_use_callback(self, agent_id: str, func_name: str, params: dict, result: Any, elapsed_time=None):
        agent_ids = agent_id.split("-->")
        agent_name = self.get_component_name(agent_ids[0])
        path = agent_name if len(agent_ids) < 2 else agent_name+"-->"+"-->".join(agent_ids[1:])
        try:
            bin = REDIS_CONN.get(f"{self.task_id}-{self.message_id}-logs")
            if bin:
                obj = json.loads(bin.encode("utf-8"))
                if obj[-1]["component_id"] == agent_ids[0]:
                    obj[-1]["trace"].append({"path": path, "tool_name": func_name, "arguments": params, "result": result, "elapsed_time": elapsed_time})
                else:
                    obj.append({
                    "component_id": agent_ids[0],
                    "trace": [{"path": path, "tool_name": func_name, "arguments": params, "result": result, "elapsed_time": elapsed_time}]
                })
            else:
                obj = [{
                    "component_id": agent_ids[0],
                    "trace": [{"path": path, "tool_name": func_name, "arguments": params, "result": result, "elapsed_time": elapsed_time}]
                }]
            REDIS_CONN.set_obj(f"{self.task_id}-{self.message_id}-logs", obj, 60*10)
        except Exception as e:
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in Canvas.tool_use_callback).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f5589dfb4481381c630bf6a217f99bcfecb0e90d67440e936a796b4738a12fa9'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f5589dfb4481381c630bf6a217f99bcfecb0e90d67440e936a796b4738a12fa9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/canvas.py', 'line': 780, 'function': 'Canvas.tool_use_callback'}, 'file': 'agent/canvas.py', 'line': 780, 'function': 'tool_use_callback', 'agent_name': 'Canvas', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                e = _gr_client.enforce(_gr_site, e, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)

    def add_reference(self, chunks: list[object], doc_infos: list[object]):
        if not self.retrieval:
            self.retrieval = [{"chunks": {}, "doc_aggs": {}}]

        r = self.retrieval[-1]
        for ck in chunks_format({"chunks": chunks}):
            cid = hash_str2int(ck["id"], 500)
            # cid = uuid.uuid5(uuid.NAMESPACE_DNS, ck["id"])
            if cid not in r:
                r["chunks"][cid] = ck

        for doc in doc_infos:
            if doc["doc_name"] not in r:
                r["doc_aggs"][doc["doc_name"]] = doc

    def get_reference(self):
        if not self.retrieval:
            return {"chunks": {}, "doc_aggs": {}}
        return self.retrieval[-1]

    def add_memory(self, user:str, assist:str, summ: str):
        self.memory.append((user, assist, summ))

    def get_memory(self) -> list[Tuple]:
        return self.memory

    def get_component_thoughts(self, cpn_id) -> str:
        return self.components.get(cpn_id)["obj"].thoughts()
