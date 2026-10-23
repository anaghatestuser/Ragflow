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
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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
import logging
import os
import time
from functools import partial
from typing import Any
from agent.component.base import ComponentBase, ComponentParamBase
from common.connection_utils import timeout


class ProcessParamBase(ComponentParamBase):
    def __init__(self):
        super().__init__()
        self.timeout = 100000000
        self.persist_logs = True


class ProcessBase(ComponentBase):
    def __init__(self, pipeline, id, param: ProcessParamBase):
        super().__init__(pipeline, id, param)
        if hasattr(self._canvas, "callback"):
            self.callback = partial(self._canvas.callback, id)
        else:
            self.callback = partial(lambda *args, **kwargs: None, id)

    async def invoke(self, **kwargs) -> dict[str, Any]:
        self.set_output("_created_time", time.perf_counter())
        for k, v in kwargs.items():
            self.set_output(k, v)
        try:
            await asyncio.wait_for(
                self._invoke(**kwargs),
                timeout=self._param.timeout
            )
            self.callback(1, "Done")
        except Exception as e:
            if self.get_exception_default_value():
                self.set_exception_default_value()
            else:
                self.set_output("_ERROR", str(e))
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in ProcessBase.invoke).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e89298b47fedc05d457fb8d517a60bb416d8a45492baa3cb2b7ef2f61929ae66'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e89298b47fedc05d457fb8d517a60bb416d8a45492baa3cb2b7ef2f61929ae66', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/base.py', 'line': 56, 'function': 'ProcessBase.invoke'}, 'file': 'rag/flow/base.py', 'line': 56, 'function': 'invoke', 'agent_name': 'ProcessBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                e = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, e, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)
            self.callback(-1, str(e))
        self.set_output("_elapsed_time", time.perf_counter() - self.output("_created_time"))
        return self.output()

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10 * 60)))
    async def _invoke(self, **kwargs):
        raise NotImplementedError()
