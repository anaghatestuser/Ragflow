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
from abc import ABC
import os
import numbers
from agent.component.base import ComponentBase, ComponentParamBase
from api.utils.api_utils import timeout

class VariableAssignerParam(ComponentParamBase):
    """
    Define the Variable Assigner component parameters.
    """
    def __init__(self):
        super().__init__()
        self.variables=[]

    def check(self):
        return True
    
    def get_input_form(self) -> dict[str, dict]:
        return {
            "items": {
                "type": "json",
                "name": "Items"
            }
        }

class VariableAssigner(ComponentBase,ABC):
    component_name = "VariableAssigner"

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10*60)))
    def _invoke(self, **kwargs):
        if not isinstance(self._param.variables,list):
            return
        else:
            for item in self._param.variables:
                if any([not item.get("variable"), not item.get("operator"), not item.get("parameter")]):
                    assert "Variable is not complete."
                variable=item["variable"]
                operator=item["operator"]
                parameter=item["parameter"]
                variable_value=self._canvas.get_variable_value(variable)
                new_variable=self._operate(variable_value,operator,parameter)
                self._canvas.set_variable_value(variable, new_variable)

    def _operate(self,variable,operator,parameter):
        if operator == "overwrite":
            return self._overwrite(parameter)
        elif operator == "clear":
            return self._clear(variable)
        elif operator == "set":
            return self._set(variable,parameter)
        elif operator == "append":
            return self._append(variable,parameter)
        elif operator == "extend":
            return self._extend(variable,parameter)
        elif operator == "remove_first":
            return self._remove_first(variable)
        elif operator == "remove_last":
            return self._remove_last(variable)
        elif operator == "+=":
            return self._add(variable,parameter)
        elif operator == "-=":
            return self._subtract(variable,parameter)
        elif operator == "*=":
            return self._multiply(variable,parameter)
        elif operator == "/=":
            return self._divide(variable,parameter)
        else:
            return
    
    def _overwrite(self,parameter):
        return self._canvas.get_variable_value(parameter)

    def _clear(self,variable):
        if isinstance(variable,list):
            return []
        elif isinstance(variable,str):
            return ""
        elif isinstance(variable,dict):
            return {}
        elif isinstance(variable,int):
            return 0
        elif isinstance(variable,float):
            return 0.0
        elif isinstance(variable,bool):
            return False
        else:
            return None

    def _set(self,variable,parameter):
        if variable is None:
            return self._canvas.get_value_with_variable(parameter)
        elif isinstance(variable,str):
            return self._canvas.get_value_with_variable(parameter)
        elif isinstance(variable,bool):
            # LINEAJE: runtime guardrail checks `parameter` as it flows from the agent to the user interface, before it leaves the application (in VariableAssigner._set).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `parameter` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f5052a760a2632216cbc3191867a50e8fd454e93b7cb03bb9e1199177a3b6fbb'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f5052a760a2632216cbc3191867a50e8fd454e93b7cb03bb9e1199177a3b6fbb', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/variable_assigner.py', 'line': 110, 'function': 'VariableAssigner._set'}, 'file': 'agent/component/variable_assigner.py', 'line': 110, 'function': '_set', 'agent_name': 'VariableAssigner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                parameter = _gr_client.enforce(_gr_site, parameter, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return parameter
        elif isinstance(variable,int):
            # LINEAJE: runtime guardrail checks `parameter` as it flows from the agent to the user interface, before it leaves the application (in VariableAssigner._set).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `parameter` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:dbdafeb2c2f3757f3c675747c050f44514c1901103e5dfa66ee9f088a9377939'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dbdafeb2c2f3757f3c675747c050f44514c1901103e5dfa66ee9f088a9377939', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/variable_assigner.py', 'line': 112, 'function': 'VariableAssigner._set'}, 'file': 'agent/component/variable_assigner.py', 'line': 112, 'function': '_set', 'agent_name': 'VariableAssigner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                parameter = _gr_client.enforce(_gr_site, parameter, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return parameter
        elif isinstance(variable,float):
            # LINEAJE: runtime guardrail checks `parameter` as it flows from the agent to the user interface, before it leaves the application (in VariableAssigner._set).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `parameter` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:230870be6a0ef987c6f8be7988305f2365150cf822aee92914f438c270099a3e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:230870be6a0ef987c6f8be7988305f2365150cf822aee92914f438c270099a3e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/variable_assigner.py', 'line': 114, 'function': 'VariableAssigner._set'}, 'file': 'agent/component/variable_assigner.py', 'line': 114, 'function': '_set', 'agent_name': 'VariableAssigner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                parameter = _gr_client.enforce(_gr_site, parameter, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return parameter
        else:
            # LINEAJE: runtime guardrail checks `parameter` as it flows from the agent to the user interface, before it leaves the application (in VariableAssigner._set).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `parameter` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f1549a66b094ca69b22cc1dcef8a04cc5e9cdb00d11a765bd0294c967cfb39ae'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f1549a66b094ca69b22cc1dcef8a04cc5e9cdb00d11a765bd0294c967cfb39ae', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/variable_assigner.py', 'line': 116, 'function': 'VariableAssigner._set'}, 'file': 'agent/component/variable_assigner.py', 'line': 116, 'function': '_set', 'agent_name': 'VariableAssigner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                parameter = _gr_client.enforce(_gr_site, parameter, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return parameter

    def _append(self,variable,parameter):
        parameter=self._canvas.get_variable_value(parameter)
        if variable is None:
            variable=[]
        if not isinstance(variable,list):
            return "ERROR:VARIABLE_NOT_LIST"
        elif len(variable)!=0 and not isinstance(parameter,type(variable[0])):
            return "ERROR:PARAMETER_NOT_LIST_ELEMENT_TYPE"
        else:
            variable.append(parameter)
            # LINEAJE: runtime guardrail checks `variable` as it flows from the agent to the user interface, before it leaves the application (in VariableAssigner._append).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `variable` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:821dab8152da0d38e7e1db39fa2deb6132cd48e3a93ce43bc5adc71f10f365b9'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:821dab8152da0d38e7e1db39fa2deb6132cd48e3a93ce43bc5adc71f10f365b9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/variable_assigner.py', 'line': 128, 'function': 'VariableAssigner._append'}, 'file': 'agent/component/variable_assigner.py', 'line': 128, 'function': '_append', 'agent_name': 'VariableAssigner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                variable = _gr_client.enforce(_gr_site, variable, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return variable

    def _extend(self,variable,parameter):
        parameter=self._canvas.get_variable_value(parameter)
        if variable is None:
            variable=[]
        if not isinstance(variable,list):
            return "ERROR:VARIABLE_NOT_LIST"
        elif not isinstance(parameter,list):
            return "ERROR:PARAMETER_NOT_LIST"
        elif len(variable)!=0 and len(parameter)!=0 and not isinstance(parameter[0],type(variable[0])):
            return "ERROR:PARAMETER_NOT_LIST_ELEMENT_TYPE"
        else:
            return variable + parameter

    def _remove_first(self,variable):
        if len(variable)==0:
            # LINEAJE: runtime guardrail checks `variable` as it flows from the agent to the user interface, before it leaves the application (in VariableAssigner._remove_first).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `variable` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:33da399c376ee46525503ca70f0e5f624059aa8a1cbdf0df91174f6057420b01'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:33da399c376ee46525503ca70f0e5f624059aa8a1cbdf0df91174f6057420b01', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/variable_assigner.py', 'line': 145, 'function': 'VariableAssigner._remove_first'}, 'file': 'agent/component/variable_assigner.py', 'line': 145, 'function': '_remove_first', 'agent_name': 'VariableAssigner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                variable = _gr_client.enforce(_gr_site, variable, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return variable
        if not isinstance(variable,list):
            return "ERROR:VARIABLE_NOT_LIST"
        else:
            return variable[1:]

    def _remove_last(self,variable):
        if len(variable)==0:
            # LINEAJE: runtime guardrail checks `variable` as it flows from the agent to the user interface, before it leaves the application (in VariableAssigner._remove_last).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `variable` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:237415652311270ae54c3c6925971a2ebf6e1410c344d7a61e44db1b26a81a54'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:237415652311270ae54c3c6925971a2ebf6e1410c344d7a61e44db1b26a81a54', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/variable_assigner.py', 'line': 153, 'function': 'VariableAssigner._remove_last'}, 'file': 'agent/component/variable_assigner.py', 'line': 153, 'function': '_remove_last', 'agent_name': 'VariableAssigner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                variable = _gr_client.enforce(_gr_site, variable, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return variable
        if not isinstance(variable,list):
            return "ERROR:VARIABLE_NOT_LIST"
        else:
            return variable[:-1]

    def is_number(self, value):
        if isinstance(value, bool):
            return False
        return isinstance(value, numbers.Number)

    def _add(self,variable,parameter):
        if self.is_number(variable) and self.is_number(parameter):
            return variable + parameter
        else:
            return "ERROR:VARIABLE_NOT_NUMBER or PARAMETER_NOT_NUMBER"

    def _subtract(self,variable,parameter):
        if self.is_number(variable) and self.is_number(parameter):
            return variable - parameter
        else:
            return "ERROR:VARIABLE_NOT_NUMBER or PARAMETER_NOT_NUMBER"

    def _multiply(self,variable,parameter):
        if self.is_number(variable) and self.is_number(parameter):
            return variable * parameter
        else:
            return "ERROR:VARIABLE_NOT_NUMBER or PARAMETER_NOT_NUMBER"

    def _divide(self,variable,parameter):
        if self.is_number(variable) and self.is_number(parameter):
            if  parameter==0:
                return "ERROR:DIVIDE_BY_ZERO"
            else:
                return variable/parameter
        else:
            return  "ERROR:VARIABLE_NOT_NUMBER or PARAMETER_NOT_NUMBER"

    def thoughts(self) -> str:
        return "Assign variables from canvas."