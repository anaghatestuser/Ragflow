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

from typing import Any
import os

from common.connection_utils import timeout
from agent.component.base import ComponentBase, ComponentParamBase


class VariableAggregatorParam(ComponentParamBase):
    """
    Parameters for VariableAggregator

    - groups: list of dicts {"group_name": str, "variables": [variable selectors]}
    """

    def __init__(self):
        super().__init__()
        # each group expects: {"group_name": str, "variables": List[str]}
        self.groups = []

    def check(self):
        self.check_empty(self.groups, "[VariableAggregator] groups")
        for g in self.groups:
            if not g.get("group_name"):
                raise ValueError("[VariableAggregator] group_name can not be empty!")
            if not g.get("variables"):
                raise ValueError(
                    f"[VariableAggregator] variables of group `{g.get('group_name')}` can not be empty"
                )
            if not isinstance(g.get("variables"), list):
                raise ValueError(
                    f"[VariableAggregator] variables of group `{g.get('group_name')}` should be a list of strings"
                )

    def get_input_form(self) -> dict[str, dict]:
        return {
            "variables": {
                "name": "Variables",
                "type": "list",
            }
        }


class VariableAggregator(ComponentBase):
    component_name = "VariableAggregator"

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 3)))
    def _invoke(self, **kwargs):
        # Group mode: for each group, pick the first available variable
        for group in self._param.groups:
            gname = group.get("group_name")

            # record candidate selectors within this group
            self.set_input_value(f"{gname}.variables", list(group.get("variables", [])))
            for selector in group.get("variables", []):
                val = self._canvas.get_variable_value(selector['value'])
                if val:
                    self.set_output(gname, val)
                    break
            
    @staticmethod
    def _to_object(value: Any) -> Any:
        # Try to convert value to serializable object if it has to_object()
        try:
            return value.to_object()  # type: ignore[attr-defined]
        except Exception:
            # LINEAJE: runtime guardrail checks `value` as it flows from the agent to the user interface, before it leaves the application (in VariableAggregator._to_object).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `value` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:78ef39728f1bad936a3ef5791576c9088f6e034cd007ad9c0691c38e7d050ced'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:78ef39728f1bad936a3ef5791576c9088f6e034cd007ad9c0691c38e7d050ced', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/varaiable_aggregator.py', 'line': 81, 'function': 'VariableAggregator._to_object'}, 'file': 'agent/component/varaiable_aggregator.py', 'line': 81, 'function': '_to_object', 'agent_name': 'VariableAggregator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                value = _gr_client.enforce(_gr_site, value, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return value

    def thoughts(self) -> str:
        return "Aggregating variables from canvas and grouping as configured."
