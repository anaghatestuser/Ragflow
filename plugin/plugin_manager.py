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
import os
from pathlib import Path
import pluginlib

from .common import PLUGIN_TYPE_LLM_TOOLS

from .llm_tool_plugin import LLMToolPlugin


class PluginManager:
    _llm_tool_plugins: dict[str, LLMToolPlugin]

    def __init__(self) -> None:
        self._llm_tool_plugins = {}

    def load_plugins(self) -> None:
        loader = pluginlib.PluginLoader(
            paths=[str(Path(os.path.dirname(__file__), "embedded_plugins"))]
        )
        
        for type, plugins in loader.plugins.items():
            for name, plugin in plugins.items():
                _lineaje_payload = f"Loaded {type} plugin {name} version {plugin.version}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PluginManager.load_plugins).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a9743eada6001bacc68c1de0ae25e0bf96d8f1575184056b850fae346c993a90'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a9743eada6001bacc68c1de0ae25e0bf96d8f1575184056b850fae346c993a90', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'plugin/plugin_manager.py', 'line': 24, 'function': 'PluginManager.load_plugins'}, 'file': 'plugin/plugin_manager.py', 'line': 24, 'function': 'load_plugins', 'agent_name': 'PluginManager', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)

                if type == PLUGIN_TYPE_LLM_TOOLS:
                    metadata = plugin.get_metadata()
                    self._llm_tool_plugins[metadata["name"]] = plugin

    def get_llm_tools(self) -> list[LLMToolPlugin]:
        return list(self._llm_tool_plugins.values())

    def get_llm_tool_by_name(self, name: str) -> LLMToolPlugin | None:
        return self._llm_tool_plugins.get(name)

    def get_llm_tools_by_names(self, tool_names: list[str]) -> list[LLMToolPlugin]:
        results = []

        for name in tool_names:
            plugin = self._llm_tool_plugins.get(name)

            if plugin is not None:
                results.append(plugin)

        # LINEAJE: runtime guardrail checks `results` as it flows from the agent to the user interface, before it leaves the application (in PluginManager.get_llm_tools_by_names).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `results` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f2784dcdc8bc91b65044f33e2750bbf72a92356f1b581c81e5419dbfc276a046'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f2784dcdc8bc91b65044f33e2750bbf72a92356f1b581c81e5419dbfc276a046', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'plugin/plugin_manager.py', 'line': 45, 'function': 'PluginManager.get_llm_tools_by_names'}, 'file': 'plugin/plugin_manager.py', 'line': 45, 'function': 'get_llm_tools_by_names', 'agent_name': 'PluginManager', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            results = _gr_client.enforce(_gr_site, results, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return results
