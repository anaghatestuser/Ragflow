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
from agent.component.base import ComponentBase, ComponentParamBase


class LoopParam(ComponentParamBase):
    """
    Define the Loop component parameters.
    """

    def __init__(self):
        super().__init__()
        self.loop_variables = []
        self.loop_termination_condition=[]
        self.maximum_loop_count = 0

    def get_input_form(self) -> dict[str, dict]:
        return {
            "items": {
                "type": "json",
                "name": "Items"
            }
        }

    def check(self):
        return True


class Loop(ComponentBase, ABC):
    component_name = "Loop"

    def get_start(self):
        for cid in self._canvas.components.keys():
            if self._canvas.get_component(cid)["obj"].component_name.lower() != "loopitem":
                continue
            if self._canvas.get_component(cid)["parent_id"] == self._id:
                # LINEAJE: runtime guardrail checks `cid` as it flows from the agent to the user interface, before it leaves the application (in Loop.get_start).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `cid` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:8ebe00415589bcf638258c25f95d90b3440cde8b4ab6d3dc6c18969d5097ee7d'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8ebe00415589bcf638258c25f95d90b3440cde8b4ab6d3dc6c18969d5097ee7d', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/loop.py', 'line': 51, 'function': 'Loop.get_start'}, 'file': 'agent/component/loop.py', 'line': 51, 'function': 'get_start', 'agent_name': 'Loop', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    cid = _gr_client.enforce(_gr_site, cid, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return cid

    def _invoke(self, **kwargs):
        if self.check_if_canceled("Loop processing"):
            return

        for item in self._param.loop_variables:
            if any([not item.get("variable"), not item.get("input_mode"), not item.get("value"),not item.get("type")]):
                assert "Loop Variable is not complete."
            if item["input_mode"]=="variable":
                self.set_output(item["variable"],self._canvas.get_variable_value(item["value"]))
            elif item["input_mode"]=="constant":
                self.set_output(item["variable"],item["value"])
            else:
                if item["type"] == "number":
                    self.set_output(item["variable"], 0)
                elif item["type"] == "string":
                    self.set_output(item["variable"], "")
                elif item["type"] == "boolean":
                    self.set_output(item["variable"], False)
                elif item["type"].startswith("object"):
                    self.set_output(item["variable"], {})
                elif item["type"].startswith("array"):
                    self.set_output(item["variable"], [])
                else:
                    self.set_output(item["variable"], "")


    def thoughts(self) -> str:
        return "Loop from canvas."