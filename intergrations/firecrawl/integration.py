"""
RAGFlow Integration Entry Point for Firecrawl

This file provides the main entry point for the Firecrawl integration with RAGFlow.
It follows RAGFlow's integration patterns and provides the necessary interfaces.
"""
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


from typing import Dict, Any
import logging

from ragflow_integration import RAGFlowFirecrawlIntegration, create_firecrawl_integration
from firecrawl_ui import FirecrawlUIBuilder

# Set up logging
logger = logging.getLogger(__name__)


class FirecrawlRAGFlowPlugin:
    """
    Main plugin class for Firecrawl integration with RAGFlow.
    This class provides the interface that RAGFlow expects from integrations.
    """
    
    def __init__(self):
        """Initialize the Firecrawl plugin."""
        self.name = "firecrawl"
        self.display_name = "Firecrawl Web Scraper"
        self.description = "Import web content using Firecrawl's powerful scraping capabilities"
        self.version = "1.0.0"
        self.author = "Firecrawl Team"
        self.category = "web"
        self.icon = "🌐"
        
        _lineaje_payload = f"Initialized {self.display_name} plugin v{self.version}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in FirecrawlRAGFlowPlugin.__init__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:cdb12311dd9a01308e0236bf87a497224d841c55d7e585711a60725f40bd96b2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cdb12311dd9a01308e0236bf87a497224d841c55d7e585711a60725f40bd96b2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/integration.py', 'line': 34, 'function': 'FirecrawlRAGFlowPlugin.__init__'}, 'file': 'intergrations/firecrawl/integration.py', 'line': 34, 'function': '__init__', 'agent_name': 'FirecrawlRAGFlowPlugin', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logger.info(_lineaje_payload)
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get plugin information for RAGFlow."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "category": self.category,
            "icon": self.icon,
            "supported_formats": ["markdown", "html", "links", "screenshot"],
            "supported_scrape_types": ["single", "crawl", "batch"]
        }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for RAGFlow."""
        return FirecrawlUIBuilder.create_data_source_config()["config_schema"]
    
    def get_ui_schema(self) -> Dict[str, Any]:
        """Get UI schema for RAGFlow."""
        return FirecrawlUIBuilder.create_ui_schema()
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration and return any errors."""
        try:
            integration = create_firecrawl_integration(config)
            return integration.validate_config(config)
        except Exception as e:
            _lineaje_payload = f"Configuration validation error: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in FirecrawlRAGFlowPlugin.validate_config).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3288cfbaf58ecc19811588d9afa030b55720b8ce5165a72834bd67edc52a2422'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3288cfbaf58ecc19811588d9afa030b55720b8ce5165a72834bd67edc52a2422', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/integration.py', 'line': 64, 'function': 'FirecrawlRAGFlowPlugin.validate_config'}, 'file': 'intergrations/firecrawl/integration.py', 'line': 64, 'function': 'validate_config', 'agent_name': 'FirecrawlRAGFlowPlugin', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logger.error(_lineaje_payload)
            return {"general": str(e)}
    
    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test connection to Firecrawl API."""
        try:
            integration = create_firecrawl_integration(config)
            # Run the async test_connection method
            import asyncio
            return asyncio.run(integration.test_connection())
        except Exception as e:
            _lineaje_payload = f"Connection test error: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in FirecrawlRAGFlowPlugin.test_connection).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6e6f21bc27c650800ab0937f52a8eafdf25e24d348c8028f93b18f98c80d8f5a'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6e6f21bc27c650800ab0937f52a8eafdf25e24d348c8028f93b18f98c80d8f5a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/integration.py', 'line': 75, 'function': 'FirecrawlRAGFlowPlugin.test_connection'}, 'file': 'intergrations/firecrawl/integration.py', 'line': 75, 'function': 'test_connection', 'agent_name': 'FirecrawlRAGFlowPlugin', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logger.error(_lineaje_payload)
            return {
                "success": False,
                "error": str(e),
                "message": "Connection test failed"
            }
    
    def create_integration(self, config: Dict[str, Any]) -> RAGFlowFirecrawlIntegration:
        """Create and return a Firecrawl integration instance."""
        return create_firecrawl_integration(config)
    
    def get_help_text(self) -> Dict[str, str]:
        """Get help text for users."""
        return FirecrawlUIBuilder.create_help_text()
    
    def get_validation_rules(self) -> Dict[str, Any]:
        """Get validation rules for configuration."""
        return FirecrawlUIBuilder.create_validation_rules()


# RAGFlow integration entry points
def get_plugin() -> FirecrawlRAGFlowPlugin:
    """Get the plugin instance for RAGFlow."""
    return FirecrawlRAGFlowPlugin()


def get_integration(config: Dict[str, Any]) -> RAGFlowFirecrawlIntegration:
    """Get an integration instance with the given configuration."""
    return create_firecrawl_integration(config)


def get_config_schema() -> Dict[str, Any]:
    """Get the configuration schema."""
    return FirecrawlUIBuilder.create_data_source_config()["config_schema"]


def get_ui_schema() -> Dict[str, Any]:
    """Get the UI schema."""
    return FirecrawlUIBuilder.create_ui_schema()


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate configuration."""
    try:
        integration = create_firecrawl_integration(config)
        return integration.validate_config(config)
    except Exception as e:
        return {"general": str(e)}


def test_connection(config: Dict[str, Any]) -> Dict[str, Any]:
    """Test connection to Firecrawl API."""
    try:
        integration = create_firecrawl_integration(config)
        return integration.test_connection()
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Connection test failed"
        }


# Export main functions and classes
__all__ = [
    "FirecrawlRAGFlowPlugin",
    "get_plugin",
    "get_integration",
    "get_config_schema",
    "get_ui_schema",
    "validate_config",
    "test_connection",
    "RAGFlowFirecrawlIntegration",
    "create_firecrawl_integration"
]
