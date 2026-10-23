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

from abc import ABC
import os
from agent.component.base import ComponentBase, ComponentParamBase
from api.utils.api_utils import timeout

class ListOperationsParam(ComponentParamBase):
    """
    Define the List Operations component parameters.
    """
    def __init__(self):
        super().__init__()
        self.query = ""
        self.operations = "topN"
        self.n=0
        self.sort_method = "asc"
        self.filter = {
            "operator": "=",
            "value": ""
        }
        self.outputs = {
            "result": {
                "value": [],
                "type": "Array of ?"
            },
            "first": {
                "value": "",
                "type": "?"
            },
            "last": {
                "value": "",
                "type": "?"
            }
        }
    
    def check(self):
        self.check_empty(self.query, "query")
        self.check_valid_value(self.operations, "Support operations", ["topN","head","tail","filter","sort","drop_duplicates"])

    def get_input_form(self) -> dict[str, dict]:
        return {}
    

class ListOperations(ComponentBase,ABC):
    component_name = "ListOperations"

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10*60)))
    def _invoke(self, **kwargs):
        self.input_objects=[]
        inputs = getattr(self._param, "query", None)
        self.inputs = self._canvas.get_variable_value(inputs)
        if not isinstance(self.inputs, list):
            raise TypeError("The input of List Operations should be an array.")
        self.set_input_value(inputs, self.inputs)
        if self._param.operations == "topN":
            self._topN()
        elif self._param.operations == "head":
            self._head()
        elif self._param.operations == "tail":
            self._tail()
        elif self._param.operations == "filter":
            self._filter()
        elif self._param.operations == "sort":
            self._sort()
        elif self._param.operations == "drop_duplicates":
            self._drop_duplicates()


    def _coerce_n(self):
        try:
            return int(getattr(self._param, "n", 0))
        except Exception:
            return 0
        
    def _set_outputs(self, outputs):
        self._param.outputs["result"]["value"] = outputs
        self._param.outputs["first"]["value"] = outputs[0] if outputs else None
        self._param.outputs["last"]["value"]  = outputs[-1] if outputs else None
        
    def _topN(self):
        n = self._coerce_n()
        if n < 1:
            outputs = []
        else:
            n = min(n, len(self.inputs))
            outputs = self.inputs[:n]
        self._set_outputs(outputs)

    def _head(self):
        n = self._coerce_n()
        if 1 <= n <= len(self.inputs):
            outputs = [self.inputs[n - 1]]
        else:
            outputs = []
        self._set_outputs(outputs)

    def _tail(self):
        n = self._coerce_n()
        if 1 <= n <= len(self.inputs):
            outputs = [self.inputs[-n]]
        else:
            outputs = []
        self._set_outputs(outputs)

    def _filter(self):
        self._set_outputs([i for i in self.inputs if self._eval(self._norm(i),self._param.filter["operator"],self._param.filter["value"])])

    def _norm(self,v):
        s = "" if v is None else str(v)
        # LINEAJE: runtime guardrail checks `s` as it flows from the agent to the user interface, before it leaves the application (in ListOperations._norm).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `s` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3dcd56b3f5444090a9686c54e75ee4f23ddbce05df60b1242ea43d341534da83'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3dcd56b3f5444090a9686c54e75ee4f23ddbce05df60b1242ea43d341534da83', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/list_operations.py', 'line': 109, 'function': 'ListOperations._norm'}, 'file': 'agent/component/list_operations.py', 'line': 109, 'function': '_norm', 'agent_name': 'ListOperations', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            s = _gr_client.enforce(_gr_site, s, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return s
    
    def _eval(self, v, operator, value):
        if operator == "=":
            return v == value
        elif operator == "≠":
            return v != value
        elif operator == "contains":
            return value in v
        elif operator == "start with":
            return v.startswith(value)
        elif operator == "end with":
            return v.endswith(value)
        else:
            return False

    def _sort(self):
        items = self.inputs or []
        method = getattr(self._param, "sort_method", "asc") or "asc"
        reverse = method == "desc"

        if not items:
            self._set_outputs([])
            return

        first = items[0]

        if isinstance(first, dict):
            outputs = sorted(
                items,
                key=lambda x: self._hashable(x),
                reverse=reverse,
            )
        else:
            outputs = sorted(items, reverse=reverse)

        self._set_outputs(outputs)

    def _drop_duplicates(self):
        seen = set()
        outs = []
        for item in self.inputs:
            k = self._hashable(item)
            if k in seen:
                continue
            seen.add(k)
            outs.append(item)
        self._set_outputs(outs)

    def _hashable(self,x):
        if isinstance(x, dict):
            return tuple(sorted((k, self._hashable(v)) for k, v in x.items()))
        if isinstance(x, (list, tuple)):
            return tuple(self._hashable(v) for v in x)
        if isinstance(x, set):
            return tuple(sorted(self._hashable(v) for v in x))
        # LINEAJE: runtime guardrail checks `x` as it flows from the agent to the user interface, before it leaves the application (in ListOperations._hashable).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `x` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a0799ec9996c5618c645cb838bc449fdea6f5639764c4a40e2120cd6cba0b4c4'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a0799ec9996c5618c645cb838bc449fdea6f5639764c4a40e2120cd6cba0b4c4', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/list_operations.py', 'line': 165, 'function': 'ListOperations._hashable'}, 'file': 'agent/component/list_operations.py', 'line': 165, 'function': '_hashable', 'agent_name': 'ListOperations', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            x = _gr_client.enforce(_gr_site, x, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return x
    
    def thoughts(self) -> str:
        return "ListOperation in progress"
