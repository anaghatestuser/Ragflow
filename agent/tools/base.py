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
import logging
import re
import time
from copy import deepcopy
import asyncio
from functools import partial
from typing import TypedDict, List, Any
from agent.component.base import ComponentParamBase, ComponentBase
from common.misc_utils import hash_str2int
from rag.prompts.generator import kb_prompt
from common.mcp_tool_call_conn import MCPToolCallSession, ToolCallSession
from timeit import default_timer as timer


class ToolParameter(TypedDict):
    type: str
    description: str
    displayDescription: str
    enum: List[str]
    required: bool


class ToolMeta(TypedDict):
    name: str
    displayName: str
    description: str
    displayDescription: str
    parameters: dict[str, ToolParameter]


class LLMToolPluginCallSession(ToolCallSession):
    def __init__(self, tools_map: dict[str, object], callback: partial):
        self.tools_map = tools_map
        self.callback = callback

    def tool_call(self, name: str, arguments: dict[str, Any]) -> Any:
        return asyncio.run(self.tool_call_async(name, arguments))

    async def tool_call_async(self, name: str, arguments: dict[str, Any]) -> Any:
        assert name in self.tools_map, f"LLM tool {name} does not exist"
        st = timer()
        tool_obj = self.tools_map[name]
        if isinstance(tool_obj, MCPToolCallSession):
            resp = await asyncio.to_thread(tool_obj.tool_call, name, arguments, 60)
        else:
            if hasattr(tool_obj, "invoke_async") and asyncio.iscoroutinefunction(tool_obj.invoke_async):
                resp = await tool_obj.invoke_async(**arguments)
            else:
                resp = await asyncio.to_thread(tool_obj.invoke, **arguments)

        self.callback(name, arguments, resp, elapsed_time=timer()-st)
        # LINEAJE: runtime guardrail checks `resp` as it flows from the agent to the user interface, before it leaves the application (in LLMToolPluginCallSession.tool_call_async).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `resp` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:665f0477d544aab147eeec1712909a07ae0dd11b34a31221bcad2ab2e9f79c6e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:665f0477d544aab147eeec1712909a07ae0dd11b34a31221bcad2ab2e9f79c6e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/base.py', 'line': 67, 'function': 'LLMToolPluginCallSession.tool_call_async'}, 'file': 'agent/tools/base.py', 'line': 67, 'function': 'tool_call_async', 'agent_name': 'LLMToolPluginCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            resp = _gr_client.enforce(_gr_site, resp, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return resp

    def get_tool_obj(self, name):
        return self.tools_map[name]


class ToolParamBase(ComponentParamBase):
    def __init__(self):
        #self.meta:ToolMeta = None
        super().__init__()
        self._init_inputs()
        self._init_attr_by_meta()

    def _init_inputs(self):
        self.inputs = {}
        for k,p in self.meta["parameters"].items():
            self.inputs[k] = deepcopy(p)

    def _init_attr_by_meta(self):
        for k,p in self.meta["parameters"].items():
            if not hasattr(self, k):
                setattr(self, k, p.get("default"))

    def get_meta(self):
        params = {}
        for k, p in self.meta["parameters"].items():
            params[k] = {
                "type": p["type"],
                "description": p["description"]
            }
            if "enum" in p:
                params[k]["enum"] = p["enum"]

        desc = self.meta["description"]
        if hasattr(self, "description"):
            desc = self.description

        function_name = self.meta["name"]
        if hasattr(self, "function_name"):
            function_name = self.function_name

        return {
            "type": "function",
            "function": {
                "name": function_name,
                "description": desc,
                "parameters": {
                    "type": "object",
                    "properties": params,
                    "required": [k for k, p in self.meta["parameters"].items() if p["required"]]
                }
            }
        }


class ToolBase(ComponentBase):
    def __init__(self, canvas, id, param: ComponentParamBase):
        from agent.canvas import Canvas  # Local import to avoid cyclic dependency
        assert isinstance(canvas, Canvas), "canvas must be an instance of Canvas"
        self._canvas = canvas
        self._id = id
        self._param = param
        self._param.check()

    def get_meta(self) -> dict[str, Any]:
        return self._param.get_meta()

    def invoke(self, **kwargs):
        if self.check_if_canceled("Tool processing"):
            return

        self.set_output("_created_time", time.perf_counter())
        try:
            res = self._invoke(**kwargs)
        except Exception as e:
            self._param.outputs["_ERROR"] = {"value": str(e)}
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in ToolBase.invoke).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:521abc0b1f238b06902f3152f9eda8252cfa9af08a28a66cc97e63c74a5ce4c5'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:521abc0b1f238b06902f3152f9eda8252cfa9af08a28a66cc97e63c74a5ce4c5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/base.py', 'line': 143, 'function': 'ToolBase.invoke'}, 'file': 'agent/tools/base.py', 'line': 143, 'function': 'invoke', 'agent_name': 'ToolBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                e = _gr_client.enforce(_gr_site, e, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)
            res = str(e)
        self._param.debug_inputs = []

        self.set_output("_elapsed_time", time.perf_counter() - self.output("_created_time"))
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in ToolBase.invoke).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:11cb055b70b04b0e3d79d500f890a39cc00213438059a25a304131a421ea3981'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:11cb055b70b04b0e3d79d500f890a39cc00213438059a25a304131a421ea3981', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/base.py', 'line': 148, 'function': 'ToolBase.invoke'}, 'file': 'agent/tools/base.py', 'line': 148, 'function': 'invoke', 'agent_name': 'ToolBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    async def invoke_async(self, **kwargs):
        """
        Async wrapper for tool invocation.
        If `_invoke` is a coroutine, await it directly; otherwise run in a thread to avoid blocking.
        Mirrors the exception handling of `invoke`.
        """
        if self.check_if_canceled("Tool processing"):
            return

        self.set_output("_created_time", time.perf_counter())
        try:
            fn_async = getattr(self, "_invoke_async", None)
            if fn_async and asyncio.iscoroutinefunction(fn_async):
                res = await fn_async(**kwargs)
            elif asyncio.iscoroutinefunction(self._invoke):
                res = await self._invoke(**kwargs)
            else:
                res = await asyncio.to_thread(self._invoke, **kwargs)
        except Exception as e:
            self._param.outputs["_ERROR"] = {"value": str(e)}
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in ToolBase.invoke_async).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:913ced5f00280d73f4ccf72b1f01bd088764b97b97ae53a249a20398c50212c9'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:913ced5f00280d73f4ccf72b1f01bd088764b97b97ae53a249a20398c50212c9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/base.py', 'line': 170, 'function': 'ToolBase.invoke_async'}, 'file': 'agent/tools/base.py', 'line': 170, 'function': 'invoke_async', 'agent_name': 'ToolBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                e = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, e, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)
            res = str(e)
        self._param.debug_inputs = []

        self.set_output("_elapsed_time", time.perf_counter() - self.output("_created_time"))
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in ToolBase.invoke_async).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6254bad1f81a0bf61c34e969a3d03383e26544cc56175eaa27dfab29ea9f11b0'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6254bad1f81a0bf61c34e969a3d03383e26544cc56175eaa27dfab29ea9f11b0', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/base.py', 'line': 175, 'function': 'ToolBase.invoke_async'}, 'file': 'agent/tools/base.py', 'line': 175, 'function': 'invoke_async', 'agent_name': 'ToolBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    def _retrieve_chunks(self, res_list: list, get_title, get_url, get_content, get_score=None):
        chunks = []
        aggs = []
        for r in res_list:
            content = get_content(r)
            if not content:
                continue
            content = re.sub(r"!?\[[a-z]+\]\(data:image/png;base64,[ 0-9A-Za-z/_=+-]+\)", "", content)
            content = content[:10000]
            if not content:
                continue
            id = str(hash_str2int(content))
            title = get_title(r)
            url = get_url(r)
            score = get_score(r) if get_score else 1
            chunks.append({
                "chunk_id": id,
                "content": content,
                "doc_id": id,
                "docnm_kwd": title,
                "similarity": score,
                "url": url
            })
            aggs.append({
                "doc_name": title,
                "doc_id": id,
                "count": 1,
                "url": url
            })
        self._canvas.add_reference(chunks, aggs)
        self.set_output("formalized_content", "\n".join(kb_prompt({"chunks": chunks, "doc_aggs": aggs}, 200000, True)))

    def thoughts(self) -> str:
        return self._canvas.get_component_name(self._id) + " is running..."
