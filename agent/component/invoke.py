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
import json
import logging
import os
import re
import time
from abc import ABC

import requests

from agent.component.base import ComponentBase, ComponentParamBase
from common.connection_utils import timeout
from deepdoc.parser import HtmlParser


class InvokeParam(ComponentParamBase):
    """
    Define the Crawler component parameters.
    """

    def __init__(self):
        super().__init__()
        self.proxy = None
        self.headers = ""
        self.method = "get"
        self.variables = []
        self.url = ""
        self.timeout = 60
        self.clean_html = False
        self.datatype = "json"  # New parameter to determine data posting type

    def check(self):
        self.check_valid_value(self.method.lower(), "Type of content from the crawler", ["get", "post", "put"])
        self.check_empty(self.url, "End point URL")
        self.check_positive_integer(self.timeout, "Timeout time in second")
        self.check_boolean(self.clean_html, "Clean HTML")
        self.check_valid_value(self.datatype.lower(), "Data post type", ["json", "formdata"])  # Check for valid datapost value


class Invoke(ComponentBase, ABC):
    component_name = "Invoke"

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 3)))
    def _invoke(self, **kwargs):
        if self.check_if_canceled("Invoke processing"):
            return

        args = {}
        for para in self._param.variables:
            if para.get("value"):
                args[para["key"]] = para["value"]
            else:
                args[para["key"]] = self._canvas.get_variable_value(para["ref"])

        url = self._param.url.strip()

        def replace_variable(match):
            var_name = match.group(1)
            try:
                value = self._canvas.get_variable_value(var_name)
                return str(value or "")
            except Exception:
                return ""

        # {base_url} or {component_id@variable_name}
        url = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_.@-]*)\}", replace_variable, url)

        if url.find("http") != 0:
            url = "http://" + url

        method = self._param.method.lower()
        headers = {}
        if self._param.headers:
            headers = json.loads(self._param.headers)
        proxies = None
        if re.sub(r"https?:?/?/?", "", self._param.proxy):
            proxies = {"http": self._param.proxy, "https": self._param.proxy}

        last_e = ""
        for _ in range(self._param.max_retries + 1):
            if self.check_if_canceled("Invoke processing"):
                return

            try:
                if method == "get":
                    response = requests.get(url=url, params=args, headers=headers, proxies=proxies, timeout=self._param.timeout)
                    # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in Invoke.replace_variable).
                    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:0004b7fa195271621dd0f2c97c2eea0d3e6214ad9d0f0ad4778954aefab57998'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0004b7fa195271621dd0f2c97c2eea0d3e6214ad9d0f0ad4778954aefab57998', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/invoke.py', 'line': 100, 'function': 'Invoke._invoke'}, 'file': 'agent/component/invoke.py', 'line': 100, 'function': 'replace_variable', 'agent_name': 'Invoke', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=100)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    if self._param.clean_html:
                        sections = HtmlParser()(None, response.content)
                        # LINEAJE: runtime guardrail checks `sections` as it flows from the LLM to the agent, after the model replies (in Invoke.replace_variable).
                        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `sections` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:291c361c8aa5d887b5380e91e9a8dc96083f0aac7846b703f9a24e335b7a7c99'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:291c361c8aa5d887b5380e91e9a8dc96083f0aac7846b703f9a24e335b7a7c99', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/invoke.py', 'line': 102, 'function': 'Invoke._invoke'}, 'file': 'agent/component/invoke.py', 'line': 102, 'function': 'replace_variable', 'agent_name': 'Invoke', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True}, interaction_id=locals().get('_lineaje_interaction_id'))
                        try:
                            sections = _gr_client.enforce(_gr_site, sections, content_type='application/json', variable_name='sections', source_file=__file__, before_line=102)
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        self.set_output("result", "\n".join(sections))
                    else:
                        self.set_output("result", response.text)

                if method == "put":
                    if self._param.datatype.lower() == "json":
                        response = requests.put(url=url, json=args, headers=headers, proxies=proxies, timeout=self._param.timeout)
                        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in Invoke.replace_variable).
                        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:4207e2fc6a53eae5247ea9627d518068201cd51be798da4214cc4a9830ee784c'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4207e2fc6a53eae5247ea9627d518068201cd51be798da4214cc4a9830ee784c', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/invoke.py', 'line': 109, 'function': 'Invoke._invoke'}, 'file': 'agent/component/invoke.py', 'line': 109, 'function': 'replace_variable', 'agent_name': 'Invoke', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=109)
                        except _gr_client.GuardrailUnavailableError:
                            pass
                    else:
                        response = requests.put(url=url, data=args, headers=headers, proxies=proxies, timeout=self._param.timeout)
                        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in Invoke.replace_variable).
                        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:ac9cf307e289e643d6a5aba99c55440646fc7dbee66105c885db08da906575fe'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ac9cf307e289e643d6a5aba99c55440646fc7dbee66105c885db08da906575fe', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/invoke.py', 'line': 111, 'function': 'Invoke._invoke'}, 'file': 'agent/component/invoke.py', 'line': 111, 'function': 'replace_variable', 'agent_name': 'Invoke', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=111)
                        except _gr_client.GuardrailUnavailableError:
                            pass
                    if self._param.clean_html:
                        sections = HtmlParser()(None, response.content)
                        # LINEAJE: runtime guardrail checks `sections` as it flows from the LLM to the agent, after the model replies (in Invoke.replace_variable).
                        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `sections` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:a8d9d3ba701edabcee8dd189d8c6e98f6dd5433fd92731d43f872711cb3bd0fd'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a8d9d3ba701edabcee8dd189d8c6e98f6dd5433fd92731d43f872711cb3bd0fd', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/invoke.py', 'line': 113, 'function': 'Invoke._invoke'}, 'file': 'agent/component/invoke.py', 'line': 113, 'function': 'replace_variable', 'agent_name': 'Invoke', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True}, interaction_id=locals().get('_lineaje_interaction_id'))
                        try:
                            sections = _gr_client.enforce(_gr_site, sections, content_type='application/json', variable_name='sections', source_file=__file__, before_line=113)
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        self.set_output("result", "\n".join(sections))
                    else:
                        self.set_output("result", response.text)

                if method == "post":
                    if self._param.datatype.lower() == "json":
                        response = requests.post(url=url, json=args, headers=headers, proxies=proxies, timeout=self._param.timeout)
                        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in Invoke.replace_variable).
                        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:2c31067b3beb7ea1ef1e51e4fbc684acdd3e5b5bb7318a5873cd6852296bc309'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2c31067b3beb7ea1ef1e51e4fbc684acdd3e5b5bb7318a5873cd6852296bc309', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/invoke.py', 'line': 120, 'function': 'Invoke._invoke'}, 'file': 'agent/component/invoke.py', 'line': 120, 'function': 'replace_variable', 'agent_name': 'Invoke', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=120)
                        except _gr_client.GuardrailUnavailableError:
                            pass
                    else:
                        response = requests.post(url=url, data=args, headers=headers, proxies=proxies, timeout=self._param.timeout)
                        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in Invoke.replace_variable).
                        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:d72604a4b7cef3608c717605e9cdfa5f545fc8d8e12c1c44c9156ee1c2f9b12e'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d72604a4b7cef3608c717605e9cdfa5f545fc8d8e12c1c44c9156ee1c2f9b12e', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/invoke.py', 'line': 122, 'function': 'Invoke._invoke'}, 'file': 'agent/component/invoke.py', 'line': 122, 'function': 'replace_variable', 'agent_name': 'Invoke', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=122)
                        except _gr_client.GuardrailUnavailableError:
                            pass
                    if self._param.clean_html:
                        self.set_output("result", "\n".join(sections))
                    else:
                        self.set_output("result", response.text)

                return self.output("result")
            except Exception as e:
                if self.check_if_canceled("Invoke processing"):
                    return

                last_e = e
                _lineaje_payload = f"Http request error: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Invoke.replace_variable).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:e32f89a92c201db4af1b213fe0b6f1e0ae3035411644f0f700ee6a03ea5f7978'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e32f89a92c201db4af1b213fe0b6f1e0ae3035411644f0f700ee6a03ea5f7978', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/invoke.py', 'line': 134, 'function': 'Invoke._invoke'}, 'file': 'agent/component/invoke.py', 'line': 134, 'function': 'replace_variable', 'agent_name': 'Invoke', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(_lineaje_payload)
                time.sleep(self._param.delay_after_error)

        if last_e:
            self.set_output("_ERROR", str(last_e))
            return f"Http request error: {last_e}"

        assert False, self.output()

    def thoughts(self) -> str:
        return "Waiting for the server respond..."
