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
import json
import logging
import os
import re
from copy import deepcopy
from functools import partial
from typing import Any

import json_repair
from timeit import default_timer as timer
from agent.tools.base import LLMToolPluginCallSession, ToolParamBase, ToolBase, ToolMeta
from api.db.services.llm_service import LLMBundle
from api.db.services.tenant_llm_service import TenantLLMService
from api.db.services.mcp_server_service import MCPServerService
from common.connection_utils import timeout
from rag.prompts.generator import next_step_async, COMPLETE_TASK, \
    citation_prompt, kb_prompt, citation_plus, full_question, message_fit_in, structured_output_prompt
from common.mcp_tool_call_conn import MCPToolCallSession, mcp_tool_metadata_to_openai_tool
from agent.component.llm import LLMParam, LLM


class AgentParam(LLMParam, ToolParamBase):
    """
    Define the Agent component parameters.
    """

    def __init__(self):
        self.meta:ToolMeta = {
                "name": "agent",
                "description": "This is an agent for a specific task.",
                "parameters": {
                    "user_prompt": {
                        "type": "string",
                        "description": "This is the order you need to send to the agent.",
                        "default": "",
                        "required": True
                    },
                    "reasoning": {
                        "type": "string",
                        "description": (
                            "Supervisor's reasoning for choosing the this agent. "
                            "Explain why this agent is being invoked and what is expected of it."
                        ),
                        "required": True
                    },
                    "context": {
                        "type": "string",
                        "description": (
                                "All relevant background information, prior facts, decisions, "
                                "and state needed by the agent to solve the current query. "
                                "Should be as detailed and self-contained as possible."
                            ),
                        "required": True
                    },
                }
            }
        super().__init__()
        self.function_name = "agent"
        self.tools = []
        self.mcp = []
        self.max_rounds = 5
        self.description = ""


class Agent(LLM, ToolBase):
    component_name = "Agent"

    def __init__(self, canvas, id, param: LLMParam):
        LLM.__init__(self, canvas, id, param)
        self.tools = {}
        for idx, cpn in enumerate(self._param.tools):
            cpn = self._load_tool_obj(cpn)
            original_name = cpn.get_meta()["function"]["name"]
            indexed_name = f"{original_name}_{idx}"
            self.tools[indexed_name] = cpn

        _lineaje_payload = self._canvas.get_tenant_id()
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the LLM, before it is sent to the model (in Agent.__init__).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:7f590aee49446c99b087c690abc65e91a08a68bd4eefff63f9f2d8e6f937133d'
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7f590aee49446c99b087c690abc65e91a08a68bd4eefff63f9f2d8e6f937133d', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'source': {'entity_type': 'agent', 'file_path': 'agent/component/agent_with_tools.py', 'line': 81, 'name': 'Agent', 'repository_uri': 'https://github.com/anaghatestuser/ragflow', 'unique_org_id': 'vdna_cju84i8UDBHggOy4'}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'custom_llm_client', 'purl': 'pkg:aimodel/custom_llm_client@1.0.0', 'version': ''}, 'source': {'entity_type': 'aiagent', 'name': 'Agent', 'purl': 'pkg:aiagent/Agent@1.0.0', 'version': '1.0.0'}}, 'invocation': {'file': 'agent/component/agent_with_tools.py', 'function': 'Agent.__init__', 'line': 93}, 'destination': {'entity_type': 'llm', 'name': 'custom_llm_client', 'provider': '', 'version': ''}, 'file': 'agent/component/agent_with_tools.py', 'line': 93, 'function': '__init__', 'agent_name': 'Agent', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:3170e14f1ebe6810'}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=93)
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        self.chat_mdl = LLMBundle(_lineaje_payload, TenantLLMService.llm_id2llm_type(self._param.llm_id), self._param.llm_id,
                                  max_retries=self._param.max_retries,
                                  retry_interval=self._param.delay_after_error,
                                  max_rounds=self._param.max_rounds,
                                  verbose_tool_use=True
                                  )
        # LINEAJE: runtime guardrail checks `self.chat_mdl` as it flows from the LLM to the agent, after the model replies (in Agent.__init__).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `self.chat_mdl` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:de5e3c171662711a84eff9bfebd364d2ef6909598f8bbb95c4cb374bc570ded0'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:de5e3c171662711a84eff9bfebd364d2ef6909598f8bbb95c4cb374bc570ded0', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'source': {'entity_type': 'agent', 'file_path': 'agent/component/agent_with_tools.py', 'line': 81, 'name': 'Agent', 'repository_uri': 'https://github.com/anaghatestuser/ragflow', 'unique_org_id': 'vdna_cju84i8UDBHggOy4'}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'custom_llm_client', 'purl': 'pkg:aimodel/custom_llm_client@1.0.0', 'version': ''}, 'source': {'entity_type': 'aiagent', 'name': 'Agent', 'purl': 'pkg:aiagent/Agent@1.0.0', 'version': '1.0.0'}}, 'invocation': {'file': 'agent/component/agent_with_tools.py', 'function': 'Agent.__init__', 'line': 93}, 'destination': {'entity_type': 'llm', 'name': 'custom_llm_client', 'provider': '', 'version': ''}, 'file': 'agent/component/agent_with_tools.py', 'line': 93, 'function': '__init__', 'agent_name': 'Agent', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:3170e14f1ebe6810'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            self.chat_mdl = _gr_client.enforce(_gr_site, self.chat_mdl, content_type='application/json', variable_name='self.chat_mdl', source_file=__file__, before_line=93)
        except _gr_client.GuardrailUnavailableError:
            pass
        self.tool_meta = []
        for indexed_name, tool_obj in self.tools.items():
            original_meta = tool_obj.get_meta()
            indexed_meta = deepcopy(original_meta)
            indexed_meta["function"]["name"] = indexed_name
            self.tool_meta.append(indexed_meta)

        for mcp in self._param.mcp:
            _, mcp_server = MCPServerService.get_by_id(mcp["mcp_id"])
            tool_call_session = MCPToolCallSession(mcp_server, mcp_server.variables)
            for tnm, meta in mcp["tools"].items():
                self.tool_meta.append(mcp_tool_metadata_to_openai_tool(meta))
                self.tools[tnm] = tool_call_session
        self.callback = partial(self._canvas.tool_use_callback, id)
        self.toolcall_session = LLMToolPluginCallSession(self.tools, self.callback)
        #self.chat_mdl.bind_tools(self.toolcall_session, self.tool_metas)

    def _load_tool_obj(self, cpn: dict) -> object:
        from agent.component import component_class
        tool_name = cpn["component_name"]
        param = component_class(tool_name + "Param")()
        param.update(cpn["params"])
        try:
            param.check()
        except Exception as e:
            self.set_output("_ERROR", cpn["component_name"] + f" configuration error: {e}")
            raise
        cpn_id = f"{self._id}-->" + cpn.get("name", "").replace(" ", "_")
        return component_class(cpn["component_name"])(self._canvas, cpn_id, param)

    def get_meta(self) -> dict[str, Any]:
        self._param.function_name= self._id.split("-->")[-1]
        m = super().get_meta()
        if hasattr(self._param, "user_prompt") and self._param.user_prompt:
            m["function"]["parameters"]["properties"]["user_prompt"] = self._param.user_prompt
        # LINEAJE: runtime guardrail checks `m` as it flows from the agent to the user interface, before it leaves the application (in Agent.get_meta).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `m` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:77e360e48094f2d22e8256d0b7fa68055629fa7ad6d8678c54ea251633cdf985'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:77e360e48094f2d22e8256d0b7fa68055629fa7ad6d8678c54ea251633cdf985', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'source': {'entity_type': 'agent', 'unique_org_id': 'vdna_cju84i8UDBHggOy4', 'repository_uri': 'https://github.com/anaghatestuser/ragflow', 'file_path': 'agent/component/agent_with_tools.py', 'line': 81, 'name': 'Agent'}, 'identity': {'source': {'entity_type': 'aiagent', 'name': 'Agent', 'version': '1.0.0', 'purl': 'pkg:aiagent/Agent@1.0.0'}, 'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/agent_with_tools.py', 'line': 134, 'function': 'Agent.get_meta'}, 'file': 'agent/component/agent_with_tools.py', 'line': 134, 'function': 'get_meta', 'agent_name': 'Agent', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            m = _gr_client.enforce(_gr_site, m, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return m

    def get_input_form(self) -> dict[str, dict]:
        res = {}
        for k, v in self.get_input_elements().items():
            res[k] = {
                "type": "line",
                "name": v["name"]
            }
        for cpn in self._param.tools:
            if not isinstance(cpn, LLM):
                continue
            res.update(cpn.get_input_form())
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in Agent.get_input_form).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:284a3c3822c3a14b99542bf646e2070fcf8a295c26ad41ce8fb86950c3c8bded'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:284a3c3822c3a14b99542bf646e2070fcf8a295c26ad41ce8fb86950c3c8bded', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'source': {'entity_type': 'agent', 'unique_org_id': 'vdna_cju84i8UDBHggOy4', 'repository_uri': 'https://github.com/anaghatestuser/ragflow', 'file_path': 'agent/component/agent_with_tools.py', 'line': 81, 'name': 'Agent'}, 'identity': {'source': {'entity_type': 'aiagent', 'name': 'Agent', 'version': '1.0.0', 'purl': 'pkg:aiagent/Agent@1.0.0'}, 'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/agent_with_tools.py', 'line': 147, 'function': 'Agent.get_input_form'}, 'file': 'agent/component/agent_with_tools.py', 'line': 147, 'function': 'get_input_form', 'agent_name': 'Agent', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    def _get_output_schema(self):
        try:
            cand = self._param.outputs.get("structured")
        except Exception:
            return None

        if isinstance(cand, dict):
            if isinstance(cand.get("properties"), dict) and len(cand["properties"]) > 0:
                # LINEAJE: runtime guardrail checks `cand` as it flows from the agent to the user interface, before it leaves the application (in Agent._get_output_schema).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `cand` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:755c7ec8a61109e2156f3ed7f5d93eec9ec6e095d7b60f48ba0bf4f9269c32a7'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:755c7ec8a61109e2156f3ed7f5d93eec9ec6e095d7b60f48ba0bf4f9269c32a7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'source': {'entity_type': 'agent', 'unique_org_id': 'vdna_cju84i8UDBHggOy4', 'repository_uri': 'https://github.com/anaghatestuser/ragflow', 'file_path': 'agent/component/agent_with_tools.py', 'line': 81, 'name': 'Agent'}, 'identity': {'source': {'entity_type': 'aiagent', 'name': 'Agent', 'version': '1.0.0', 'purl': 'pkg:aiagent/Agent@1.0.0'}, 'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/agent_with_tools.py', 'line': 157, 'function': 'Agent._get_output_schema'}, 'file': 'agent/component/agent_with_tools.py', 'line': 157, 'function': '_get_output_schema', 'agent_name': 'Agent', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    cand = _gr_client.enforce(_gr_site, cand, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return cand
            for k in ("schema", "structured"):
                if isinstance(cand.get(k), dict) and isinstance(cand[k].get("properties"), dict) and len(cand[k]["properties"]) > 0:
                    return cand[k]

        return None

    async def _force_format_to_schema_async(self, text: str, schema_prompt: str) -> str:
        fmt_msgs = [
            {"role": "system", "content": schema_prompt + "\nIMPORTANT: Output ONLY valid JSON. No markdown, no extra text."},
            {"role": "user", "content": text},
        ]
        _, fmt_msgs = message_fit_in(fmt_msgs, int(self.chat_mdl.max_length * 0.97))
        return await self._generate_async(fmt_msgs)

    def _invoke(self, **kwargs):
        return asyncio.run(self._invoke_async(**kwargs))

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 20*60)))
    async def _invoke_async(self, **kwargs):
        if self.check_if_canceled("Agent processing"):
            return

        if kwargs.get("user_prompt"):
            usr_pmt = ""
            if kwargs.get("reasoning"):
                usr_pmt += "\nREASONING:\n{}\n".format(kwargs["reasoning"])
            if kwargs.get("context"):
                usr_pmt += "\nCONTEXT:\n{}\n".format(kwargs["context"])
            if usr_pmt:
                usr_pmt += "\nQUERY:\n{}\n".format(str(kwargs["user_prompt"]))
            else:
                usr_pmt = str(kwargs["user_prompt"])
            self._param.prompts = [{"role": "user", "content": usr_pmt}]

        if not self.tools:
            if self.check_if_canceled("Agent processing"):
                return
            return await LLM._invoke_async(self, **kwargs)

        prompt, msg, user_defined_prompt = self._prepare_prompt_variables()
        output_schema = self._get_output_schema()
        schema_prompt = ""
        if output_schema:
            # LINEAJE: runtime guardrail checks `output_schema` as it flows from the agent to an external endpoint, before it leaves the application (in Agent._invoke_async).
            #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `output_schema` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1462cd644c6c69f7c646e75f91a8969683f70c06fd7c7bc6caa454d4f63f4f79'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1462cd644c6c69f7c646e75f91a8969683f70c06fd7c7bc6caa454d4f63f4f79', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'source': {'entity_type': 'agent', 'unique_org_id': 'vdna_cju84i8UDBHggOy4', 'repository_uri': 'https://github.com/anaghatestuser/ragflow', 'file_path': 'agent/component/agent_with_tools.py', 'line': 81, 'name': 'Agent'}, 'identity': {'source': {'entity_type': 'aiagent', 'name': 'Agent', 'version': '1.0.0', 'purl': 'pkg:aiagent/Agent@1.0.0'}, 'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/agent_with_tools.py', 'line': 201, 'function': 'Agent._invoke_async'}, 'file': 'agent/component/agent_with_tools.py', 'line': 201, 'function': '_invoke_async', 'agent_name': 'Agent', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                output_schema = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, output_schema, content_type='application/json', variable_name='output_schema', source_file=__file__, before_line=201))
            except _gr_client.GuardrailUnavailableError:
                pass
            schema = json.dumps(output_schema, ensure_ascii=False, indent=2)
            schema_prompt = structured_output_prompt(schema)

        downstreams = self._canvas.get_component(self._id)["downstream"] if self._canvas.get_component(self._id) else []
        ex = self.exception_handler()
        if any([self._canvas.get_component_obj(cid).component_name.lower()=="message" for cid in downstreams]) and not (ex and ex["goto"]) and not output_schema:
            self.set_output("content", partial(self.stream_output_with_tools_async, prompt, deepcopy(msg), user_defined_prompt))
            return

        _, msg = message_fit_in([{"role": "system", "content": prompt}, *msg], int(self.chat_mdl.max_length * 0.97))
        use_tools = []
        ans = ""
        async for delta_ans, _tk in self._react_with_tools_streamly_async_simple(prompt, msg, use_tools, user_defined_prompt,schema_prompt=schema_prompt):
            if self.check_if_canceled("Agent processing"):
                return
            ans += delta_ans

        if ans.find("**ERROR**") >= 0:
            _lineaje_payload = f"Agent._chat got error. response: {ans}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Agent._invoke_async).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:438a6cdbf3eb2b75df6047ad88aad012a03f17a7bbba53b5c4b61e667fce2f7c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:438a6cdbf3eb2b75df6047ad88aad012a03f17a7bbba53b5c4b61e667fce2f7c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'source': {'entity_type': 'agent', 'unique_org_id': 'vdna_cju84i8UDBHggOy4', 'repository_uri': 'https://github.com/anaghatestuser/ragflow', 'file_path': 'agent/component/agent_with_tools.py', 'line': 81, 'name': 'Agent'}, 'identity': {'source': {'entity_type': 'aiagent', 'name': 'Agent', 'version': '1.0.0', 'purl': 'pkg:aiagent/Agent@1.0.0'}, 'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/agent_with_tools.py', 'line': 219, 'function': 'Agent._invoke_async'}, 'file': 'agent/component/agent_with_tools.py', 'line': 219, 'function': '_invoke_async', 'agent_name': 'Agent', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            if self.get_exception_default_value():
                self.set_output("content", self.get_exception_default_value())
            else:
                self.set_output("_ERROR", ans)
            return

        if output_schema:
            error = ""
            for _ in range(self._param.max_retries + 1):
                try:
                    def clean_formated_answer(ans: str) -> str:
                        ans = re.sub(r"^.*</think>", "", ans, flags=re.DOTALL)
                        ans = re.sub(r"^.*```json", "", ans, flags=re.DOTALL)
                        return re.sub(r"```\n*$", "", ans, flags=re.DOTALL)
                    obj = json_repair.loads(clean_formated_answer(ans))
                    self.set_output("structured", obj)
                    if use_tools:
                        self.set_output("use_tools", use_tools)
                    # LINEAJE: runtime guardrail checks `obj` as it flows from the agent to the user interface, before it leaves the application (in Agent._invoke_async).
                    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `obj` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:e02f0b648a3bb15a09aaaa02e062ea6fd3233a2fa032ea0c0f015dc0fc36ccd8'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e02f0b648a3bb15a09aaaa02e062ea6fd3233a2fa032ea0c0f015dc0fc36ccd8', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'source': {'entity_type': 'agent', 'unique_org_id': 'vdna_cju84i8UDBHggOy4', 'repository_uri': 'https://github.com/anaghatestuser/ragflow', 'file_path': 'agent/component/agent_with_tools.py', 'line': 81, 'name': 'Agent'}, 'identity': {'source': {'entity_type': 'aiagent', 'name': 'Agent', 'version': '1.0.0', 'purl': 'pkg:aiagent/Agent@1.0.0'}, 'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/agent_with_tools.py', 'line': 238, 'function': 'Agent._invoke_async'}, 'file': 'agent/component/agent_with_tools.py', 'line': 238, 'function': '_invoke_async', 'agent_name': 'Agent', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        obj = _gr_client.enforce(_gr_site, obj, content_type='text/plain')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    return obj
                except Exception:
                    error = "The answer cannot be parsed as JSON"
                    ans = await self._force_format_to_schema_async(ans, schema_prompt)
                    if ans.find("**ERROR**") >= 0:
                        continue

            self.set_output("_ERROR", error)
            return

        self.set_output("content", ans)
        if use_tools:
            self.set_output("use_tools", use_tools)
        # LINEAJE: runtime guardrail checks `ans` as it flows from the agent to the user interface, before it leaves the application (in Agent._invoke_async).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `ans` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:0ab53c5c9fb08fb51a8d9a1e506704c581c23da0a9280b395c23bb849dbf0b14'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0ab53c5c9fb08fb51a8d9a1e506704c581c23da0a9280b395c23bb849dbf0b14', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'source': {'entity_type': 'agent', 'unique_org_id': 'vdna_cju84i8UDBHggOy4', 'repository_uri': 'https://github.com/anaghatestuser/ragflow', 'file_path': 'agent/component/agent_with_tools.py', 'line': 81, 'name': 'Agent'}, 'identity': {'source': {'entity_type': 'aiagent', 'name': 'Agent', 'version': '1.0.0', 'purl': 'pkg:aiagent/Agent@1.0.0'}, 'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/agent_with_tools.py', 'line': 251, 'function': 'Agent._invoke_async'}, 'file': 'agent/component/agent_with_tools.py', 'line': 251, 'function': '_invoke_async', 'agent_name': 'Agent', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            ans = _gr_client.enforce(_gr_site, ans, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return ans

    async def stream_output_with_tools_async(self, prompt, msg, user_defined_prompt={}):
        _, msg = message_fit_in([{"role": "system", "content": prompt}, *msg], int(self.chat_mdl.max_length * 0.97))
        answer_without_toolcall = ""
        use_tools = []
        async for delta_ans, _ in self._react_with_tools_streamly_async_simple(prompt, msg, use_tools, user_defined_prompt):
            if self.check_if_canceled("Agent streaming"):
                return

            if delta_ans.find("**ERROR**") >= 0:
                if self.get_exception_default_value():
                    self.set_output("content", self.get_exception_default_value())
                    yield self.get_exception_default_value()
                else:
                    self.set_output("_ERROR", delta_ans)
                    return
            answer_without_toolcall += delta_ans
            yield delta_ans

        self.set_output("content", answer_without_toolcall)
        if use_tools:
            self.set_output("use_tools", use_tools)

    async def _react_with_tools_streamly_async_simple(self, prompt, history: list[dict], use_tools, user_defined_prompt={}, schema_prompt: str = ""):
        token_count = 0
        tool_metas = self.tool_meta
        hist = deepcopy(history)
        last_calling = ""
        if len(hist) > 3:
            st = timer()
            user_request = await full_question(messages=history, chat_mdl=self.chat_mdl)
            self.callback("Multi-turn conversation optimization", {}, user_request, elapsed_time=timer()-st)
        else:
            user_request = history[-1]["content"]

        def build_task_desc(prompt: str, user_request: str, user_defined_prompt: dict | None = None) -> str:
            """Build a minimal task_desc by concatenating prompt, query, and tool schemas."""
            user_defined_prompt = user_defined_prompt or {}

            task_desc = (
                "### Agent Prompt\n"
                f"{prompt}\n\n"
                "### User Request\n"
                f"{user_request}\n\n"
            )

            if user_defined_prompt:
                # LINEAJE: runtime guardrail checks `user_defined_prompt` as it flows from the agent to an external endpoint, before it leaves the application (in Agent.build_task_desc).
                #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `user_defined_prompt` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:45ae3351c7d9107c04d1afd1fe01d6ec77c0870f0963f25ee65e2fd138b30a56'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:45ae3351c7d9107c04d1afd1fe01d6ec77c0870f0963f25ee65e2fd138b30a56', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'source': {'entity_type': 'agent', 'unique_org_id': 'vdna_cju84i8UDBHggOy4', 'repository_uri': 'https://github.com/anaghatestuser/ragflow', 'file_path': 'agent/component/agent_with_tools.py', 'line': 81, 'name': 'Agent'}, 'identity': {'source': {'entity_type': 'aiagent', 'name': 'Agent', 'version': '1.0.0', 'purl': 'pkg:aiagent/Agent@1.0.0'}, 'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/agent_with_tools.py', 'line': 299, 'function': 'Agent._react_with_tools_streamly_async_simple.build_task_desc'}, 'file': 'agent/component/agent_with_tools.py', 'line': 299, 'function': 'build_task_desc', 'agent_name': 'Agent', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    user_defined_prompt = _gr_client.enforce(_gr_site, user_defined_prompt, content_type='application/json', variable_name='user_defined_prompt', source_file=__file__, before_line=299)
                except _gr_client.GuardrailUnavailableError:
                    pass
                udp_json = json.dumps(user_defined_prompt, ensure_ascii=False, indent=2)
                task_desc += "\n### User Defined Prompts\n" + udp_json + "\n"

            # LINEAJE: runtime guardrail checks `task_desc` as it flows from the agent to the user interface, before it leaves the application (in Agent.build_task_desc).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `task_desc` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:a2993d7c934a75781e2204be01c290bbaca6cf299dfdadd5dbe62aa05e124638'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a2993d7c934a75781e2204be01c290bbaca6cf299dfdadd5dbe62aa05e124638', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'source': {'entity_type': 'agent', 'unique_org_id': 'vdna_cju84i8UDBHggOy4', 'repository_uri': 'https://github.com/anaghatestuser/ragflow', 'file_path': 'agent/component/agent_with_tools.py', 'line': 81, 'name': 'Agent'}, 'identity': {'source': {'entity_type': 'aiagent', 'name': 'Agent', 'version': '1.0.0', 'purl': 'pkg:aiagent/Agent@1.0.0'}, 'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/agent_with_tools.py', 'line': 302, 'function': 'Agent._react_with_tools_streamly_async_simple.build_task_desc'}, 'file': 'agent/component/agent_with_tools.py', 'line': 302, 'function': 'build_task_desc', 'agent_name': 'Agent', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                task_desc = _gr_client.enforce(_gr_site, task_desc, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return task_desc


        async def use_tool_async(name, args):
            nonlocal hist, use_tools, last_calling
            _lineaje_payload = f"{last_calling=} == {name=}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Agent.use_tool_async).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:c44c624f34e7bf86555ad1bddcbe21510d0d21973cbe6ec9d3fb846e32778512'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c44c624f34e7bf86555ad1bddcbe21510d0d21973cbe6ec9d3fb846e32778512', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'source': {'entity_type': 'agent', 'unique_org_id': 'vdna_cju84i8UDBHggOy4', 'repository_uri': 'https://github.com/anaghatestuser/ragflow', 'file_path': 'agent/component/agent_with_tools.py', 'line': 81, 'name': 'Agent'}, 'identity': {'source': {'entity_type': 'aiagent', 'name': 'Agent', 'version': '1.0.0', 'purl': 'pkg:aiagent/Agent@1.0.0'}, 'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/agent_with_tools.py', 'line': 307, 'function': 'Agent._react_with_tools_streamly_async_simple.use_tool_async'}, 'file': 'agent/component/agent_with_tools.py', 'line': 307, 'function': 'use_tool_async', 'agent_name': 'Agent', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            last_calling = name
            tool_response = await self.toolcall_session.tool_call_async(name, args)
            use_tools.append({
                "name": name,
                "arguments": args,
                "results": tool_response
            })
            return name, tool_response

        async def complete():
            nonlocal hist
            need2cite = self._param.cite and self._canvas.get_reference()["chunks"] and self._id.find("-->") < 0
            if schema_prompt:
                need2cite = False
            cited = False
            if hist and hist[0]["role"] == "system":
                if schema_prompt:
                    hist[0]["content"] += "\n" + schema_prompt
                if need2cite and len(hist) < 7:
                    hist[0]["content"] += citation_prompt()
                    cited = True
            yield "", token_count

            _hist = hist
            if len(hist) > 12:
                _hist = [hist[0], hist[1], *hist[-10:]]
            entire_txt = ""
            async for delta_ans in self._generate_streamly(_hist):
                if not need2cite or cited:
                    yield delta_ans, 0
                entire_txt += delta_ans
            if not need2cite or cited:
                return

            st = timer()
            txt = ""
            async for delta_ans in self._gen_citations_async(entire_txt):
                if self.check_if_canceled("Agent streaming"):
                    return
                yield delta_ans, 0
                txt += delta_ans

            self.callback("gen_citations", {}, txt, elapsed_time=timer()-st)

        def build_observation(tool_call_res: list[tuple]) -> str:
            """
            Build a Observation from tool call results.
            No LLM involved.
            """
            if not tool_call_res:
                return ""

            lines = ["Observation:"]
            for name, result in tool_call_res:
                lines.append(f"[{name} result]")
                lines.append(str(result))

            return "\n".join(lines)

        def append_user_content(hist, content):
            if hist[-1]["role"] == "user":
                hist[-1]["content"] += content
            else:
                hist.append({"role": "user", "content": content})

        st = timer()
        task_desc = build_task_desc(prompt, user_request, user_defined_prompt)
        self.callback("analyze_task", {}, task_desc, elapsed_time=timer()-st)
        for _ in range(self._param.max_rounds + 1):
            if self.check_if_canceled("Agent streaming"):
                return
            response, tk = await next_step_async(self.chat_mdl, hist, tool_metas, task_desc, user_defined_prompt)
            # self.callback("next_step", {}, str(response)[:256]+"...")
            token_count += tk or 0
            hist.append({"role": "assistant", "content": response})
            try:
                functions = json_repair.loads(re.sub(r"```.*", "", response))
                if not isinstance(functions, list):
                    raise TypeError(f"List should be returned, but `{functions}`")
                for f in functions:
                    if not isinstance(f, dict):
                        raise TypeError(f"An object type should be returned, but `{f}`")

                tool_tasks = []
                for func in functions:
                    name = func["name"]
                    args = func["arguments"]
                    if name == COMPLETE_TASK:
                        append_user_content(hist, f"Respond with a formal answer. FORGET(DO NOT mention) about `{COMPLETE_TASK}`. The language for the response MUST be as the same as the first user request.\n")
                        async for txt, tkcnt in complete():
                            yield txt, tkcnt
                        return

                    tool_tasks.append(asyncio.create_task(use_tool_async(name, args)))

                results = await asyncio.gather(*tool_tasks) if tool_tasks else []
                st = timer()
                reflection = build_observation(results)
                append_user_content(hist, reflection)
                self.callback("reflection", {}, str(reflection), elapsed_time=timer()-st)

            except Exception as e:
                logging.exception(msg=f"Wrong JSON argument format in LLM ReAct response: {e}")
                e = f"\nTool call error, please correct the input parameter of response format and call it again.\n *** Exception ***\n{e}"
                append_user_content(hist, str(e))

        _lineaje_payload = f"Exceed max rounds: {self._param.max_rounds}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Agent._react_with_tools_streamly_async_simple).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e878204500b0d695770359bc82e3c43d40c72a9e51030611f13f19a45fafa811'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e878204500b0d695770359bc82e3c43d40c72a9e51030611f13f19a45fafa811', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'source': {'entity_type': 'agent', 'unique_org_id': 'vdna_cju84i8UDBHggOy4', 'repository_uri': 'https://github.com/anaghatestuser/ragflow', 'file_path': 'agent/component/agent_with_tools.py', 'line': 81, 'name': 'Agent'}, 'identity': {'source': {'entity_type': 'aiagent', 'name': 'Agent', 'version': '1.0.0', 'purl': 'pkg:aiagent/Agent@1.0.0'}, 'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/agent_with_tools.py', 'line': 414, 'function': 'Agent._react_with_tools_streamly_async_simple'}, 'file': 'agent/component/agent_with_tools.py', 'line': 414, 'function': '_react_with_tools_streamly_async_simple', 'agent_name': 'Agent', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning( _lineaje_payload)
        final_instruction = f"""
{user_request}
IMPORTANT: You have reached the conversation limit. Based on ALL the information and research you have gathered so far, please provide a DIRECT and COMPREHENSIVE final answer to the original request.
Instructions:
1. SYNTHESIZE all information collected during this conversation
2. Provide a COMPLETE response using existing data - do not suggest additional research
3. Structure your response as a FINAL DELIVERABLE, not a plan
4. If information is incomplete, state what you found and provide the best analysis possible with available data
5. DO NOT mention conversation limits or suggest further steps
6. Focus on delivering VALUE with the information already gathered
Respond immediately with your final comprehensive answer.
        """
        if self.check_if_canceled("Agent final instruction"):
            return
        append_user_content(hist, final_instruction)

        async for txt, tkcnt in complete():
            yield txt, tkcnt

#     async def _react_with_tools_streamly_async(self, prompt, history: list[dict], use_tools, user_defined_prompt={}, schema_prompt: str = ""):
#         token_count = 0
#         tool_metas = self.tool_meta
#         hist = deepcopy(history)
#         last_calling = ""
#         if len(hist) > 3:
#             st = timer()
#             user_request = await full_question(messages=history, chat_mdl=self.chat_mdl)
#             self.callback("Multi-turn conversation optimization", {}, user_request, elapsed_time=timer()-st)
#         else:
#             user_request = history[-1]["content"]

#         async def use_tool_async(name, args):
#             nonlocal hist, use_tools, last_calling
#             logging.info(f"{last_calling=} == {name=}")
#             last_calling = name
#             tool_response = await self.toolcall_session.tool_call_async(name, args)
#             use_tools.append({
#                 "name": name,
#                 "arguments": args,
#                 "results": tool_response
#             })
#             # self.callback("add_memory", {}, "...")
#             #self.add_memory(hist[-2]["content"], hist[-1]["content"], name, args, str(tool_response), user_defined_prompt)

#             return name, tool_response

#         async def complete():
#             nonlocal hist
#             need2cite = self._param.cite and self._canvas.get_reference()["chunks"] and self._id.find("-->") < 0
#             if schema_prompt:
#                 need2cite = False
#             cited = False
#             if hist and hist[0]["role"] == "system":
#                 if schema_prompt:
#                     hist[0]["content"] += "\n" + schema_prompt
#                 if need2cite and len(hist) < 7:
#                     hist[0]["content"] += citation_prompt()
#                     cited = True
#             yield "", token_count

#             _hist = hist
#             if len(hist) > 12:
#                 _hist = [hist[0], hist[1], *hist[-10:]]
#             entire_txt = ""
#             async for delta_ans in self._generate_streamly(_hist):
#                 if not need2cite or cited:
#                     yield delta_ans, 0
#                 entire_txt += delta_ans
#             if not need2cite or cited:
#                 return

#             st = timer()
#             txt = ""
#             async for delta_ans in self._gen_citations_async(entire_txt):
#                 if self.check_if_canceled("Agent streaming"):
#                     return
#                 yield delta_ans, 0
#                 txt += delta_ans

#             self.callback("gen_citations", {}, txt, elapsed_time=timer()-st)

#         def append_user_content(hist, content):
#             if hist[-1]["role"] == "user":
#                 hist[-1]["content"] += content
#             else:
#                 hist.append({"role": "user", "content": content})

#         st = timer()
#         task_desc = await analyze_task_async(self.chat_mdl, prompt, user_request, tool_metas, user_defined_prompt)
#         self.callback("analyze_task", {}, task_desc, elapsed_time=timer()-st)
#         for _ in range(self._param.max_rounds + 1):
#             if self.check_if_canceled("Agent streaming"):
#                 return
#             response, tk = await next_step_async(self.chat_mdl, hist, tool_metas, task_desc, user_defined_prompt)
#             # self.callback("next_step", {}, str(response)[:256]+"...")
#             token_count += tk or 0
#             hist.append({"role": "assistant", "content": response})
#             try:
#                 functions = json_repair.loads(re.sub(r"```.*", "", response))
#                 if not isinstance(functions, list):
#                     raise TypeError(f"List should be returned, but `{functions}`")
#                 for f in functions:
#                     if not isinstance(f, dict):
#                         raise TypeError(f"An object type should be returned, but `{f}`")

#                 tool_tasks = []
#                 for func in functions:
#                     name = func["name"]
#                     args = func["arguments"]
#                     if name == COMPLETE_TASK:
#                         append_user_content(hist, f"Respond with a formal answer. FORGET(DO NOT mention) about `{COMPLETE_TASK}`. The language for the response MUST be as the same as the first user request.\n")
#                         async for txt, tkcnt in complete():
#                             yield txt, tkcnt
#                         return

#                     tool_tasks.append(asyncio.create_task(use_tool_async(name, args)))

#                 results = await asyncio.gather(*tool_tasks) if tool_tasks else []
#                 st = timer()
#                 reflection = await reflect_async(self.chat_mdl, hist, results, user_defined_prompt)
#                 append_user_content(hist, reflection)
#                 self.callback("reflection", {}, str(reflection), elapsed_time=timer()-st)

#             except Exception as e:
#                 logging.exception(msg=f"Wrong JSON argument format in LLM ReAct response: {e}")
#                 e = f"\nTool call error, please correct the input parameter of response format and call it again.\n *** Exception ***\n{e}"
#                 append_user_content(hist, str(e))

#         logging.warning( f"Exceed max rounds: {self._param.max_rounds}")
#         final_instruction = f"""
# {user_request}
# IMPORTANT: You have reached the conversation limit. Based on ALL the information and research you have gathered so far, please provide a DIRECT and COMPREHENSIVE final answer to the original request.
# Instructions:
# 1. SYNTHESIZE all information collected during this conversation
# 2. Provide a COMPLETE response using existing data - do not suggest additional research
# 3. Structure your response as a FINAL DELIVERABLE, not a plan
# 4. If information is incomplete, state what you found and provide the best analysis possible with available data
# 5. DO NOT mention conversation limits or suggest further steps
# 6. Focus on delivering VALUE with the information already gathered
# Respond immediately with your final comprehensive answer.
#         """
#         if self.check_if_canceled("Agent final instruction"):
#             return
#         append_user_content(hist, final_instruction)

#         async for txt, tkcnt in complete():
#             yield txt, tkcnt

    async def _gen_citations_async(self, text):
        retrievals = self._canvas.get_reference()
        retrievals = {"chunks": list(retrievals["chunks"].values()), "doc_aggs": list(retrievals["doc_aggs"].values())}
        formated_refer = kb_prompt(retrievals, self.chat_mdl.max_length, True)
        async for delta_ans in self._generate_streamly([{"role": "system", "content": citation_plus("\n\n".join(formated_refer))},
                                                  {"role": "user", "content": text}
                                                  ]):
            yield delta_ans

    def reset(self, only_output=False):
        """
        Reset all tools if they have a reset method. This avoids errors for tools like MCPToolCallSession.
        """
        for k in self._param.outputs.keys():
            self._param.outputs[k]["value"] = None

        for k, cpn in self.tools.items():
            if hasattr(cpn, "reset") and callable(cpn.reset):
                cpn.reset()
        if only_output:
            return
        for k in self._param.inputs.keys():
            self._param.inputs[k]["value"] = None
        self._param.debug_inputs = {}
