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
from abc import ABC
import pandas as pd
import requests
from agent.component.base import ComponentBase, ComponentParamBase


class Jin10Param(ComponentParamBase):
    """
    Define the Jin10 component parameters.
    """

    def __init__(self):
        super().__init__()
        self.type = "flash"
        self.secret_key = "xxx"
        self.flash_type = '1'
        self.calendar_type = 'cj'
        self.calendar_datatype = 'data'
        self.symbols_type = 'GOODS'
        self.symbols_datatype = 'symbols'
        self.contain = ""
        self.filter = ""

    def check(self):
        self.check_valid_value(self.type, "Type", ['flash', 'calendar', 'symbols', 'news'])
        self.check_valid_value(self.flash_type, "Flash Type", ['1', '2', '3', '4', '5'])
        self.check_valid_value(self.calendar_type, "Calendar Type", ['cj', 'qh', 'hk', 'us'])
        self.check_valid_value(self.calendar_datatype, "Calendar DataType", ['data', 'event', 'holiday'])
        self.check_valid_value(self.symbols_type, "Symbols Type", ['GOODS', 'FOREX', 'FUTURE', 'CRYPTO'])
        self.check_valid_value(self.symbols_datatype, 'Symbols DataType', ['symbols', 'quotes'])


class Jin10(ComponentBase, ABC):
    component_name = "Jin10"

    def _run(self, history, **kwargs):
        if self.check_if_canceled("Jin10 processing"):
            return

        ans = self.get_input()
        ans = " - ".join(ans["content"]) if "content" in ans else ""
        if not ans:
            return Jin10.be_output("")

        jin10_res = []
        headers = {'secret-key': self._param.secret_key}
        try:
            if self.check_if_canceled("Jin10 processing"):
                return

            if self._param.type == "flash":
                params = {
                    'category': self._param.flash_type,
                    'contain': self._param.contain,
                    'filter': self._param.filter
                }
                # LINEAJE: runtime guardrail checks `params` as it flows from the agent to an external endpoint, before it leaves the application (in Jin10._run).
                #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `params` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:6a69e2e217cc75d86819d4e3b556a524395bfb5bcb147d129c9c1a0d5f778391'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6a69e2e217cc75d86819d4e3b556a524395bfb5bcb147d129c9c1a0d5f778391', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/jin10.py', 'line': 73, 'function': 'Jin10._run'}, 'file': 'agent/tools/jin10.py', 'line': 73, 'function': '_run', 'agent_name': 'Jin10', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    params = _gr_client.enforce(_gr_site, params, content_type='application/json', variable_name='params', source_file=__file__, before_line=73)
                except _gr_client.GuardrailUnavailableError:
                    pass
                response = requests.get(
                    url='https://open-data-api.jin10.com/data-api/flash?category=' + self._param.flash_type,
                    headers=headers, data=json.dumps(params))
                # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in Jin10._run).
                #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:b79b70322325173ea978261cbac5be75111b21b09b33a572a4a3ebb5d655c96b'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b79b70322325173ea978261cbac5be75111b21b09b33a572a4a3ebb5d655c96b', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/jin10.py', 'line': 73, 'function': 'Jin10._run'}, 'file': 'agent/tools/jin10.py', 'line': 73, 'function': '_run', 'agent_name': 'Jin10', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=73)
                except _gr_client.GuardrailUnavailableError:
                    pass
                response = response.json()
                for i in response['data']:
                    if self.check_if_canceled("Jin10 processing"):
                        return
                    jin10_res.append({"content": i['data']['content']})
            if self._param.type == "calendar":
                params = {
                    'category': self._param.calendar_type
                }
                # LINEAJE: runtime guardrail checks `params` as it flows from the agent to an external endpoint, before it leaves the application (in Jin10._run).
                #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `params` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:8bb7475a72c2cffd9d92a6a9471fe272e208c3722de9c10e9310e0392ee1cc88'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8bb7475a72c2cffd9d92a6a9471fe272e208c3722de9c10e9310e0392ee1cc88', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/jin10.py', 'line': 85, 'function': 'Jin10._run'}, 'file': 'agent/tools/jin10.py', 'line': 85, 'function': '_run', 'agent_name': 'Jin10', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    params = _gr_client.enforce(_gr_site, params, content_type='application/json', variable_name='params', source_file=__file__, before_line=85)
                except _gr_client.GuardrailUnavailableError:
                    pass
                response = requests.get(
                    url='https://open-data-api.jin10.com/data-api/calendar/' + self._param.calendar_datatype + '?category=' + self._param.calendar_type,
                    headers=headers, data=json.dumps(params))
                # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in Jin10._run).
                #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a60ad3193e63549e27f1b481d00333ace1f421199c5bd9eaed65c7cf672d6499'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a60ad3193e63549e27f1b481d00333ace1f421199c5bd9eaed65c7cf672d6499', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/jin10.py', 'line': 85, 'function': 'Jin10._run'}, 'file': 'agent/tools/jin10.py', 'line': 85, 'function': '_run', 'agent_name': 'Jin10', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=85)
                except _gr_client.GuardrailUnavailableError:
                    pass

                response = response.json()
                if self.check_if_canceled("Jin10 processing"):
                    return
                jin10_res.append({"content": pd.DataFrame(response['data']).to_markdown()})
            if self._param.type == "symbols":
                params = {
                    'type': self._param.symbols_type
                }
                if self._param.symbols_datatype == "quotes":
                    params['codes'] = 'BTCUSD'
                # LINEAJE: runtime guardrail checks `params` as it flows from the agent to an external endpoint, before it leaves the application (in Jin10._run).
                #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `params` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:937d4b7e2b13b9540b955b1e0319add14ecb94ecf9beb11fa5f384e4b9a06375'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:937d4b7e2b13b9540b955b1e0319add14ecb94ecf9beb11fa5f384e4b9a06375', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/jin10.py', 'line': 99, 'function': 'Jin10._run'}, 'file': 'agent/tools/jin10.py', 'line': 99, 'function': '_run', 'agent_name': 'Jin10', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    params = _gr_client.enforce(_gr_site, params, content_type='application/json', variable_name='params', source_file=__file__, before_line=99)
                except _gr_client.GuardrailUnavailableError:
                    pass
                response = requests.get(
                    url='https://open-data-api.jin10.com/data-api/' + self._param.symbols_datatype + '?type=' + self._param.symbols_type,
                    headers=headers, data=json.dumps(params))
                # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in Jin10._run).
                #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:5ae56a0d2f713d3e69a298f1e04263530ec6e8a8edf5d2bdbfef0e853342cc0e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5ae56a0d2f713d3e69a298f1e04263530ec6e8a8edf5d2bdbfef0e853342cc0e', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/jin10.py', 'line': 99, 'function': 'Jin10._run'}, 'file': 'agent/tools/jin10.py', 'line': 99, 'function': '_run', 'agent_name': 'Jin10', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=99)
                except _gr_client.GuardrailUnavailableError:
                    pass
                response = response.json()
                if self.check_if_canceled("Jin10 processing"):
                    return
                if self._param.symbols_datatype == "symbols":
                    for i in response['data']:
                        if self.check_if_canceled("Jin10 processing"):
                            return
                        i['Commodity Code'] = i['c']
                        i['Stock Exchange'] = i['e']
                        i['Commodity Name'] = i['n']
                        i['Commodity Type'] = i['t']
                        del i['c'], i['e'], i['n'], i['t']
                if self._param.symbols_datatype == "quotes":
                    for i in response['data']:
                        if self.check_if_canceled("Jin10 processing"):
                            return
                        i['Selling Price'] = i['a']
                        i['Buying Price'] = i['b']
                        i['Commodity Code'] = i['c']
                        i['Stock Exchange'] = i['e']
                        i['Highest Price'] = i['h']
                        i['Yesterday’s Closing Price'] = i['hc']
                        i['Lowest Price'] = i['l']
                        i['Opening Price'] = i['o']
                        i['Latest Price'] = i['p']
                        i['Market Quote Time'] = i['t']
                        del i['a'], i['b'], i['c'], i['e'], i['h'], i['hc'], i['l'], i['o'], i['p'], i['t']
                jin10_res.append({"content": pd.DataFrame(response['data']).to_markdown()})
            if self._param.type == "news":
                params = {
                    'contain': self._param.contain,
                    'filter': self._param.filter
                }
                # LINEAJE: runtime guardrail checks `params` as it flows from the agent to an external endpoint, before it leaves the application (in Jin10._run).
                #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `params` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a187cfe9880566fc95136f1454c35febe4bc3e9b463d9384d5f9d5f7f2e7b7b8'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a187cfe9880566fc95136f1454c35febe4bc3e9b463d9384d5f9d5f7f2e7b7b8', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/jin10.py', 'line': 135, 'function': 'Jin10._run'}, 'file': 'agent/tools/jin10.py', 'line': 135, 'function': '_run', 'agent_name': 'Jin10', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    params = _gr_client.enforce(_gr_site, params, content_type='application/json', variable_name='params', source_file=__file__, before_line=135)
                except _gr_client.GuardrailUnavailableError:
                    pass
                response = requests.get(
                    url='https://open-data-api.jin10.com/data-api/news',
                    headers=headers, data=json.dumps(params))
                # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in Jin10._run).
                #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:c256d72dd16266ce9ffd8827a55027190bcb32b93f460e7210bd3faf202639a1'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c256d72dd16266ce9ffd8827a55027190bcb32b93f460e7210bd3faf202639a1', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/jin10.py', 'line': 135, 'function': 'Jin10._run'}, 'file': 'agent/tools/jin10.py', 'line': 135, 'function': '_run', 'agent_name': 'Jin10', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=135)
                except _gr_client.GuardrailUnavailableError:
                    pass
                response = response.json()
                if self.check_if_canceled("Jin10 processing"):
                    return
                jin10_res.append({"content": pd.DataFrame(response['data']).to_markdown()})
        except Exception as e:
            if self.check_if_canceled("Jin10 processing"):
                return
            return Jin10.be_output("**ERROR**: " + str(e))

        if not jin10_res:
            return Jin10.be_output("")

        return pd.DataFrame(jin10_res)
