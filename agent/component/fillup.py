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
import re
from functools import partial

from agent.component.base import ComponentParamBase, ComponentBase
from api.db.services.file_service import FileService


class UserFillUpParam(ComponentParamBase):

    def __init__(self):
        super().__init__()
        self.enable_tips = True
        self.tips = "Please fill up the form"

    def check(self) -> bool:
        return True


class UserFillUp(ComponentBase):
    component_name = "UserFillUp"

    def _invoke(self, **kwargs):
        if self.check_if_canceled("UserFillUp processing"):
            return

        if self._param.enable_tips:
            content = self._param.tips
            for k, v in self.get_input_elements_from_text(self._param.tips).items():
                v = v["value"]
                ans = ""
                if isinstance(v, partial):
                    for t in v():
                        ans += t
                elif isinstance(v, list):
                    ans = ",".join([str(vv) for vv in v])
                elif not isinstance(v, str):
                    try:
                        # LINEAJE: runtime guardrail checks `v` as it flows from the agent to an external endpoint, before it leaves the application (in UserFillUp._invoke).
                        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `v` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:17d5cbbbe4a2024f53e3cab5012ce3c95ebf6ea9b6edcbbe3794f7c9da95a960'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:17d5cbbbe4a2024f53e3cab5012ce3c95ebf6ea9b6edcbbe3794f7c9da95a960', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/fillup.py', 'line': 54, 'function': 'UserFillUp._invoke'}, 'file': 'agent/component/fillup.py', 'line': 54, 'function': '_invoke', 'agent_name': 'UserFillUp', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            v = _gr_client.enforce(_gr_site, v, content_type='application/json', variable_name='v', source_file=__file__, before_line=54)
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        ans = json.dumps(v, ensure_ascii=False)
                    except Exception:
                        pass
                else:
                    ans = v
                if not ans:
                    ans = ""
                content = re.sub(r"\{%s\}"%k, ans, content)

            self.set_output("tips", content)
        for k, v in kwargs.get("inputs", {}).items():
            if self.check_if_canceled("UserFillUp processing"):
                return
            if isinstance(v, dict) and v.get("type", "").lower().find("file") >=0:
                if v.get("optional") and v.get("value", None) is None:
                    v = None
                else:
                    v = FileService.get_files([v["value"]])
            else:
                v = v.get("value")
            self.set_output(k, v)

    def thoughts(self) -> str:
        return "Waiting for your input..."
