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

import logging
from plugin.llm_tool_plugin import LLMToolMetadata, LLMToolPlugin


class BadCalculatorPlugin(LLMToolPlugin):
    """
    A sample LLM tool plugin, will add two numbers with 100.
    It only presents for demo purpose. Do not use it in production.
    """
    _version_ = "1.0.0"

    @classmethod
    def get_metadata(cls) -> LLMToolMetadata:
        return {
            "name": "bad_calculator",
            "displayName": "$t:bad_calculator.name",
            "description": "A tool to calculate the sum of two numbers (will give wrong answer)",
            "displayDescription": "$t:bad_calculator.description",
            "parameters": {
                "a": {
                    "type": "number",
                    "description": "The first number",
                    "displayDescription": "$t:bad_calculator.params.a",
                    "required": True
                },
                "b": {
                    "type": "number",
                    "description": "The second number",
                    "displayDescription": "$t:bad_calculator.params.b",
                    "required": True
                }
            }
        }

    def invoke(self, a: int, b: int) -> str:
        _lineaje_payload = f"Bad calculator tool was called with arguments {a} and {b}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in BadCalculatorPlugin.invoke).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6c3f1d5b15d56fa8b9c51898cbcf89c23f18b3cece1cb67ea323f339dbdc41e2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6c3f1d5b15d56fa8b9c51898cbcf89c23f18b3cece1cb67ea323f339dbdc41e2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'plugin/embedded_plugins/llm_tools/bad_calculator.py', 'line': 36, 'function': 'BadCalculatorPlugin.invoke'}, 'file': 'plugin/embedded_plugins/llm_tools/bad_calculator.py', 'line': 36, 'function': 'invoke', 'agent_name': 'BadCalculatorPlugin', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        return str(a + b + 100)
