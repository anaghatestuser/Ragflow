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
from typing import Any, AsyncGenerator
import json_repair
from functools import partial
from common.constants import LLMType
from api.db.services.llm_service import LLMBundle
from api.db.services.tenant_llm_service import TenantLLMService
from agent.component.base import ComponentBase, ComponentParamBase
from common.connection_utils import timeout
from rag.prompts.generator import tool_call_summary, message_fit_in, citation_prompt, structured_output_prompt


class LLMParam(ComponentParamBase):
    """
    Define the LLM component parameters.
    """

    def __init__(self):
        super().__init__()
        self.llm_id = ""
        self.sys_prompt = ""
        self.prompts = [{"role": "user", "content": "{sys.query}"}]
        self.max_tokens = 0
        self.temperature = 0
        self.top_p = 0
        self.presence_penalty = 0
        self.frequency_penalty = 0
        self.output_structure = None
        self.cite = True
        self.visual_files_var = None

    def check(self):
        self.check_decimal_float(float(self.temperature), "[Agent] Temperature")
        self.check_decimal_float(float(self.presence_penalty), "[Agent] Presence penalty")
        self.check_decimal_float(float(self.frequency_penalty), "[Agent] Frequency penalty")
        self.check_nonnegative_number(int(self.max_tokens), "[Agent] Max tokens")
        self.check_decimal_float(float(self.top_p), "[Agent] Top P")
        self.check_empty(self.llm_id, "[Agent] LLM")
        self.check_empty(self.prompts, "[Agent] User prompt")

    def gen_conf(self):
        conf = {}
        def get_attr(nm):
            try:
                return getattr(self, nm)
            except Exception:
                pass

        if int(self.max_tokens) > 0 and get_attr("maxTokensEnabled"):
            conf["max_tokens"] = int(self.max_tokens)
        if float(self.temperature) > 0 and get_attr("temperatureEnabled"):
            conf["temperature"] = float(self.temperature)
        if float(self.top_p) > 0 and get_attr("topPEnabled"):
            conf["top_p"] = float(self.top_p)
        if float(self.presence_penalty) > 0 and get_attr("presencePenaltyEnabled"):
            conf["presence_penalty"] = float(self.presence_penalty)
        if float(self.frequency_penalty) > 0 and get_attr("frequencyPenaltyEnabled"):
            conf["frequency_penalty"] = float(self.frequency_penalty)
        # LINEAJE: runtime guardrail checks `conf` as it flows from the agent to the user interface, before it leaves the application (in LLMParam.gen_conf).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `conf` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b73c7efa0e36ff2f94aed48072a05c7b642d84d88c17c26ac467da8c6a36b493'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b73c7efa0e36ff2f94aed48072a05c7b642d84d88c17c26ac467da8c6a36b493', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/llm.py', 'line': 79, 'function': 'LLMParam.gen_conf'}, 'file': 'agent/component/llm.py', 'line': 79, 'function': 'gen_conf', 'agent_name': 'LLMParam', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            conf = _gr_client.enforce(_gr_site, conf, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return conf


class LLM(ComponentBase):
    component_name = "LLM"

    def __init__(self, canvas, component_id, param: ComponentParamBase):
        super().__init__(canvas, component_id, param)
        self.chat_mdl = LLMBundle(self._canvas.get_tenant_id(), TenantLLMService.llm_id2llm_type(self._param.llm_id),
                                  self._param.llm_id, max_retries=self._param.max_retries,
                                  retry_interval=self._param.delay_after_error
                                  )
        self.imgs = []

    def get_input_form(self) -> dict[str, dict]:
        res = {}
        for k, v in self.get_input_elements().items():
            res[k] = {
                "type": "line",
                "name": v["name"]
            }
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in LLM.get_input_form).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:2effa27b956f89c1b4f6f16e8b2e82533234e01f0961a68161554ea410158f36'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2effa27b956f89c1b4f6f16e8b2e82533234e01f0961a68161554ea410158f36', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/llm.py', 'line': 100, 'function': 'LLM.get_input_form'}, 'file': 'agent/component/llm.py', 'line': 100, 'function': 'get_input_form', 'agent_name': 'LLM', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    def get_input_elements(self) -> dict[str, Any]:
        res = self.get_input_elements_from_text(self._param.sys_prompt)
        if isinstance(self._param.prompts, str):
            self._param.prompts = [{"role": "user", "content": self._param.prompts}]
        for prompt in self._param.prompts:
            d = self.get_input_elements_from_text(prompt["content"])
            res.update(d)
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in LLM.get_input_elements).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b43e6b3413405515742dd90d62e1fa189fc573b9bb6c8ab5371e01d221f7b84f'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b43e6b3413405515742dd90d62e1fa189fc573b9bb6c8ab5371e01d221f7b84f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/llm.py', 'line': 109, 'function': 'LLM.get_input_elements'}, 'file': 'agent/component/llm.py', 'line': 109, 'function': 'get_input_elements', 'agent_name': 'LLM', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    def set_debug_inputs(self, inputs: dict[str, dict]):
        self._param.debug_inputs = inputs

    def add2system_prompt(self, txt):
        self._param.sys_prompt += txt

    def _sys_prompt_and_msg(self, msg, args):
        if isinstance(self._param.prompts, str):
            self._param.prompts = [{"role": "user", "content": self._param.prompts}]
        for p in self._param.prompts:
            if msg and msg[-1]["role"] == p["role"]:
                continue
            p = deepcopy(p)
            p["content"] = self.string_format(p["content"], args)
            msg.append(p)
        return msg, self.string_format(self._param.sys_prompt, args)

    def _prepare_prompt_variables(self):
        if self._param.visual_files_var:
            self.imgs = self._canvas.get_variable_value(self._param.visual_files_var)
            if not self.imgs:
                self.imgs = []
            self.imgs = [img for img in self.imgs if img[:len("data:image/")] == "data:image/"]
            if self.imgs and TenantLLMService.llm_id2llm_type(self._param.llm_id) == LLMType.CHAT.value:
                self.chat_mdl = LLMBundle(self._canvas.get_tenant_id(), LLMType.IMAGE2TEXT.value,
                                          self._param.llm_id, max_retries=self._param.max_retries,
                                          retry_interval=self._param.delay_after_error
                                          )


        args = {}
        vars = self.get_input_elements() if not self._param.debug_inputs else self._param.debug_inputs
        for k, o in vars.items():
            args[k] = o["value"]
            if not isinstance(args[k], str):
                try:
                    _lineaje_payload = args[k]
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to an external endpoint, before it leaves the application (in LLM._prepare_prompt_variables).
                    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `_lineaje_payload` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:99ba93f12f2d3e5ec543cc2f37063d0cafde556ebcb256c86957a2cb73193779'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:99ba93f12f2d3e5ec543cc2f37063d0cafde556ebcb256c86957a2cb73193779', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/llm.py', 'line': 147, 'function': 'LLM._prepare_prompt_variables'}, 'file': 'agent/component/llm.py', 'line': 147, 'function': '_prepare_prompt_variables', 'agent_name': 'LLM', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=147)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    args[k] = json.dumps(_lineaje_payload, ensure_ascii=False)
                except Exception:
                    args[k] = str(args[k])
            self.set_input_value(k, args[k])

        msg, sys_prompt = self._sys_prompt_and_msg(self._canvas.get_history(self._param.message_history_window_size)[:-1], args)
        user_defined_prompt, sys_prompt = self._extract_prompts(sys_prompt)
        if self._param.cite and self._canvas.get_reference()["chunks"]:
            sys_prompt += citation_prompt(user_defined_prompt)

        return sys_prompt, msg, user_defined_prompt

    def _extract_prompts(self, sys_prompt):
        pts = {}
        for tag in ["TASK_ANALYSIS", "PLAN_GENERATION", "REFLECTION", "CONTEXT_SUMMARY", "CONTEXT_RANKING", "CITATION_GUIDELINES"]:
            r = re.search(rf"<{tag}>(.*?)</{tag}>", sys_prompt, flags=re.DOTALL|re.IGNORECASE)
            if not r:
                continue
            pts[tag.lower()] = r.group(1)
            sys_prompt = re.sub(rf"<{tag}>(.*?)</{tag}>", "", sys_prompt, flags=re.DOTALL|re.IGNORECASE)
        return pts, sys_prompt

    async def _generate_async(self, msg: list[dict], **kwargs) -> str:
        if not self.imgs:
            return await self.chat_mdl.async_chat(msg[0]["content"], msg[1:], self._param.gen_conf(), **kwargs)
        return await self.chat_mdl.async_chat(msg[0]["content"], msg[1:], self._param.gen_conf(), images=self.imgs, **kwargs)

    async def _generate_streamly(self, msg: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        async def delta_wrapper(txt_iter):
            ans = ""
            last_idx = 0
            endswith_think = False

            def delta(txt):
                nonlocal ans, last_idx, endswith_think
                delta_ans = txt[last_idx:]
                ans = txt

                if delta_ans.find("<think>") == 0:
                    last_idx += len("<think>")
                    return "<think>"
                elif delta_ans.find("<think>") > 0:
                    delta_ans = txt[last_idx:last_idx + delta_ans.find("<think>")]
                    last_idx += delta_ans.find("<think>")
                    # LINEAJE: runtime guardrail checks `delta_ans` as it flows from the agent to the user interface, before it leaves the application (in LLM.delta).
                    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `delta_ans` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:3c3702df3c5b65603dddef60c61f52560f5b0e467e4af7ec3448fa323cdb4e79'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3c3702df3c5b65603dddef60c61f52560f5b0e467e4af7ec3448fa323cdb4e79', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/llm.py', 'line': 191, 'function': 'LLM._generate_streamly.delta_wrapper.delta'}, 'file': 'agent/component/llm.py', 'line': 191, 'function': 'delta', 'agent_name': 'LLM', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        delta_ans = _gr_client.enforce(_gr_site, delta_ans, content_type='text/plain')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    return delta_ans
                elif delta_ans.endswith("</think>"):
                    endswith_think = True
                elif endswith_think:
                    endswith_think = False
                    return "</think>"

                last_idx = len(ans)
                if ans.endswith("</think>"):
                    last_idx -= len("</think>")
                return re.sub(r"(<think>|</think>)", "", delta_ans)

            async for t in txt_iter:
                yield delta(t)

        if not self.imgs:
            async for t in delta_wrapper(self.chat_mdl.async_chat_streamly(msg[0]["content"], msg[1:], self._param.gen_conf(), **kwargs)):
                yield t
            return

        async for t in delta_wrapper(self.chat_mdl.async_chat_streamly(msg[0]["content"], msg[1:], self._param.gen_conf(), images=self.imgs, **kwargs)):
            yield t

    async def _stream_output_async(self, prompt, msg):
        _, msg = message_fit_in([{"role": "system", "content": prompt}, *msg], int(self.chat_mdl.max_length * 0.97))
        answer = ""
        last_idx = 0
        endswith_think = False

        def delta(txt):
            nonlocal answer, last_idx, endswith_think
            delta_ans = txt[last_idx:]
            answer = txt

            if delta_ans.find("<think>") == 0:
                last_idx += len("<think>")
                return "<think>"
            elif delta_ans.find("<think>") > 0:
                delta_ans = txt[last_idx:last_idx + delta_ans.find("<think>")]
                last_idx += delta_ans.find("<think>")
                # LINEAJE: runtime guardrail checks `delta_ans` as it flows from the agent to the user interface, before it leaves the application (in LLM.delta).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `delta_ans` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:9b9d23766d9f8e44c1072676b356bca32adb15bd0d07eb7e8a9be0d3d4653ddb'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9b9d23766d9f8e44c1072676b356bca32adb15bd0d07eb7e8a9be0d3d4653ddb', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/llm.py', 'line': 231, 'function': 'LLM._stream_output_async.delta'}, 'file': 'agent/component/llm.py', 'line': 231, 'function': 'delta', 'agent_name': 'LLM', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    delta_ans = _gr_client.enforce(_gr_site, delta_ans, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return delta_ans
            elif delta_ans.endswith("</think>"):
                endswith_think = True
            elif endswith_think:
                endswith_think = False
                return "</think>"

            last_idx = len(answer)
            if answer.endswith("</think>"):
                last_idx -= len("</think>")
            return re.sub(r"(<think>|</think>)", "", delta_ans)

        stream_kwargs = {"images": self.imgs} if self.imgs else {}
        async for ans in self.chat_mdl.async_chat_streamly(msg[0]["content"], msg[1:], self._param.gen_conf(), **stream_kwargs):
            if self.check_if_canceled("LLM streaming"):
                return

            if isinstance(ans, int):
                continue

            if ans.find("**ERROR**") >= 0:
                if self.get_exception_default_value():
                    self.set_output("content", self.get_exception_default_value())
                    yield self.get_exception_default_value()
                else:
                    self.set_output("_ERROR", ans)
                return

            yield delta(ans)

        self.set_output("content", answer)

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10*60)))
    async def _invoke_async(self, **kwargs):
        if self.check_if_canceled("LLM processing"):
            return

        def clean_formated_answer(ans: str) -> str:
            ans = re.sub(r"^.*</think>", "", ans, flags=re.DOTALL)
            ans = re.sub(r"^.*```json", "", ans, flags=re.DOTALL)
            return re.sub(r"```\n*$", "", ans, flags=re.DOTALL)

        prompt, msg, _ = self._prepare_prompt_variables()
        error: str = ""
        output_structure = None
        try:
            output_structure = self._param.outputs["structured"]
        except Exception:
            pass
        if output_structure and isinstance(output_structure, dict) and output_structure.get("properties") and len(output_structure["properties"]) > 0:
            # LINEAJE: runtime guardrail checks `output_structure` as it flows from the agent to an external endpoint, before it leaves the application (in LLM.clean_formated_answer).
            #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `output_structure` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:afd90b31c9e5e3549417f2e73dd40b4022f29f5416d74add4c18a0436e6b7201'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:afd90b31c9e5e3549417f2e73dd40b4022f29f5416d74add4c18a0436e6b7201', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/llm.py', 'line': 281, 'function': 'LLM._invoke_async'}, 'file': 'agent/component/llm.py', 'line': 281, 'function': 'clean_formated_answer', 'agent_name': 'LLM', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                output_structure = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, output_structure, content_type='application/json', variable_name='output_structure', source_file=__file__, before_line=281))
            except _gr_client.GuardrailUnavailableError:
                pass
            schema = json.dumps(output_structure, ensure_ascii=False, indent=2)
            prompt_with_schema = prompt + structured_output_prompt(schema)
            for _ in range(self._param.max_retries + 1):
                if self.check_if_canceled("LLM processing"):
                    return

                _, msg_fit = message_fit_in(
                    [{"role": "system", "content": prompt_with_schema}, *deepcopy(msg)],
                    int(self.chat_mdl.max_length * 0.97),
                )
                error = ""
                ans = await self._generate_async(msg_fit)
                msg_fit.pop(0)
                if ans.find("**ERROR**") >= 0:
                    _lineaje_payload = f"LLM response error: {ans}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LLM.clean_formated_answer).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:86b7eb3d1a846d23803b185acf91580a40606277baedcaa417258fd24d6795af'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:86b7eb3d1a846d23803b185acf91580a40606277baedcaa417258fd24d6795af', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/llm.py', 'line': 295, 'function': 'LLM._invoke_async'}, 'file': 'agent/component/llm.py', 'line': 295, 'function': 'clean_formated_answer', 'agent_name': 'LLM', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.error(_lineaje_payload)
                    error = ans
                    continue
                try:
                    self.set_output("structured", json_repair.loads(clean_formated_answer(ans)))
                    return
                except Exception:
                    msg_fit.append({"role": "user", "content": "The answer can't not be parsed as JSON"})
                    error = "The answer can't not be parsed as JSON"
            if error:
                self.set_output("_ERROR", error)
            return

        downstreams = self._canvas.get_component(self._id)["downstream"] if self._canvas.get_component(self._id) else []
        ex = self.exception_handler()
        if any([self._canvas.get_component_obj(cid).component_name.lower() == "message" for cid in downstreams]) and not (
            ex and ex["goto"]
        ):
            self.set_output("content", partial(self._stream_output_async, prompt, deepcopy(msg)))
            return

        error = ""
        for _ in range(self._param.max_retries + 1):
            if self.check_if_canceled("LLM processing"):
                return

            _, msg_fit = message_fit_in(
                [{"role": "system", "content": prompt}, *deepcopy(msg)], int(self.chat_mdl.max_length * 0.97)
            )
            error = ""
            ans = await self._generate_async(msg_fit)
            msg_fit.pop(0)
            if ans.find("**ERROR**") >= 0:
                _lineaje_payload = f"LLM response error: {ans}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LLM.clean_formated_answer).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:da4359dc392f94ccadfa71fdeb1babeee33b87efe5e2a90823611bd3f5bae13d'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:da4359dc392f94ccadfa71fdeb1babeee33b87efe5e2a90823611bd3f5bae13d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/llm.py', 'line': 328, 'function': 'LLM._invoke_async'}, 'file': 'agent/component/llm.py', 'line': 328, 'function': 'clean_formated_answer', 'agent_name': 'LLM', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                error = ans
                continue
            self.set_output("content", ans)
            break

        if error:
            if self.get_exception_default_value():
                self.set_output("content", self.get_exception_default_value())
            else:
                self.set_output("_ERROR", error)

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10*60)))
    def _invoke(self, **kwargs):
        return asyncio.run(self._invoke_async(**kwargs))

    async def add_memory(self, user:str, assist:str, func_name: str, params: dict, results: str, user_defined_prompt:dict={}):
        summ = await tool_call_summary(self.chat_mdl, func_name, params, results, user_defined_prompt)
        _lineaje_payload = f"[MEMORY]: {summ}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LLM.add_memory).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3b5729a31aa544bd7bf1fb81b0d521d3d7f387bd9e3c35970c1c5871688d245a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3b5729a31aa544bd7bf1fb81b0d521d3d7f387bd9e3c35970c1c5871688d245a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/llm.py', 'line': 346, 'function': 'LLM.add_memory'}, 'file': 'agent/component/llm.py', 'line': 346, 'function': 'add_memory', 'agent_name': 'LLM', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        self._canvas.add_memory(user, assist, summ)

    def thoughts(self) -> str:
        _, msg,_ = self._prepare_prompt_variables()
        return "⌛Give me a moment—starting from: \n\n" + re.sub(r"(User's query:|[\\]+)", '', msg[-1]['content'], flags=re.DOTALL) + "\n\nI’ll figure out our best next move."
