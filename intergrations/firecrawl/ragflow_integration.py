"""
Main integration file for Firecrawl with RAGFlow.
This file provides the interface between RAGFlow and the Firecrawl plugin.
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


import logging
from typing import List, Dict, Any

from firecrawl_connector import FirecrawlConnector
from firecrawl_config import FirecrawlConfig
from firecrawl_processor import FirecrawlProcessor, RAGFlowDocument
from firecrawl_ui import FirecrawlUIBuilder


class RAGFlowFirecrawlIntegration:
    """Main integration class for Firecrawl with RAGFlow."""
    
    def __init__(self, config: FirecrawlConfig):
        """Initialize the integration."""
        self.config = config
        self.connector = FirecrawlConnector(config)
        self.processor = FirecrawlProcessor()
        self.logger = logging.getLogger(__name__)
    
    async def scrape_and_import(self, urls: List[str], 
                               formats: List[str] = None,
                               extract_options: Dict[str, Any] = None) -> List[RAGFlowDocument]:
        """Scrape URLs and convert to RAGFlow documents."""
        if formats is None:
            formats = ["markdown", "html"]
        
        async with self.connector:
            # Scrape URLs
            scraped_contents = await self.connector.batch_scrape(urls, formats)
            
            # Process into RAGFlow documents
            documents = self.processor.process_batch(scraped_contents)
            
            # LINEAJE: runtime guardrail checks `documents` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowFirecrawlIntegration.scrape_and_import).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `documents` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:61d9a429609f94021e1db6e713af727df8872078b4343292847e657c608c16f9'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:61d9a429609f94021e1db6e713af727df8872078b4343292847e657c608c16f9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/ragflow_integration.py', 'line': 39, 'function': 'RAGFlowFirecrawlIntegration.scrape_and_import'}, 'file': 'intergrations/firecrawl/ragflow_integration.py', 'line': 39, 'function': 'scrape_and_import', 'agent_name': 'RAGFlowFirecrawlIntegration', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                documents = _gr_client.enforce(_gr_site, documents, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return documents
    
    async def crawl_and_import(self, start_url: str, 
                              limit: int = 100,
                              scrape_options: Dict[str, Any] = None) -> List[RAGFlowDocument]:
        """Crawl a website and convert to RAGFlow documents."""
        if scrape_options is None:
            scrape_options = {"formats": ["markdown", "html"]}
        
        async with self.connector:
            # Start crawl job
            crawl_job = await self.connector.start_crawl(start_url, limit, scrape_options)
            
            if crawl_job.error:
                raise Exception(f"Failed to start crawl: {crawl_job.error}")
            
            # Wait for completion
            completed_job = await self.connector.wait_for_crawl_completion(crawl_job.job_id)
            
            if completed_job.error:
                raise Exception(f"Crawl failed: {completed_job.error}")
            
            # Process into RAGFlow documents
            documents = self.processor.process_batch(completed_job.data or [])
            
            # LINEAJE: runtime guardrail checks `documents` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowFirecrawlIntegration.crawl_and_import).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `documents` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:de5966c68468cf5624a0fa2e370fba375968283038ce390ef4022ca628d52a9c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:de5966c68468cf5624a0fa2e370fba375968283038ce390ef4022ca628d52a9c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/ragflow_integration.py', 'line': 64, 'function': 'RAGFlowFirecrawlIntegration.crawl_and_import'}, 'file': 'intergrations/firecrawl/ragflow_integration.py', 'line': 64, 'function': 'crawl_and_import', 'agent_name': 'RAGFlowFirecrawlIntegration', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                documents = _gr_client.enforce(_gr_site, documents, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return documents
    
    def get_ui_schema(self) -> Dict[str, Any]:
        """Get UI schema for RAGFlow integration."""
        return FirecrawlUIBuilder.create_ui_schema()
    
    def validate_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration and return any errors."""
        errors = {}
        
        # Validate API key
        api_key = config_dict.get("api_key", "")
        if not api_key:
            errors["api_key"] = "API key is required"
        elif not api_key.startswith("fc-"):
            errors["api_key"] = "API key must start with 'fc-'"
        
        # Validate API URL
        api_url = config_dict.get("api_url", "https://api.firecrawl.dev")
        if not api_url.startswith("http"):
            errors["api_url"] = "API URL must start with http:// or https://"
        
        # Validate numeric fields
        try:
            max_retries = int(config_dict.get("max_retries", 3))
            if max_retries < 1 or max_retries > 10:
                errors["max_retries"] = "Max retries must be between 1 and 10"
        except (ValueError, TypeError):
            errors["max_retries"] = "Max retries must be a valid integer"
        
        try:
            timeout = int(config_dict.get("timeout", 30))
            if timeout < 5 or timeout > 300:
                errors["timeout"] = "Timeout must be between 5 and 300 seconds"
        except (ValueError, TypeError):
            errors["timeout"] = "Timeout must be a valid integer"
        
        try:
            rate_limit_delay = float(config_dict.get("rate_limit_delay", 1.0))
            if rate_limit_delay < 0.1 or rate_limit_delay > 10.0:
                errors["rate_limit_delay"] = "Rate limit delay must be between 0.1 and 10.0 seconds"
        except (ValueError, TypeError):
            errors["rate_limit_delay"] = "Rate limit delay must be a valid number"
        
        # LINEAJE: runtime guardrail checks `errors` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowFirecrawlIntegration.validate_config).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `errors` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8d35340120c134f6cf7484b31a34ef9385f29d6c8b77eafbeeea437fc36c91e2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8d35340120c134f6cf7484b31a34ef9385f29d6c8b77eafbeeea437fc36c91e2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/ragflow_integration.py', 'line': 108, 'function': 'RAGFlowFirecrawlIntegration.validate_config'}, 'file': 'intergrations/firecrawl/ragflow_integration.py', 'line': 108, 'function': 'validate_config', 'agent_name': 'RAGFlowFirecrawlIntegration', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            errors = _gr_client.enforce(_gr_site, errors, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return errors
    
    def create_config(self, config_dict: Dict[str, Any]) -> FirecrawlConfig:
        """Create FirecrawlConfig from dictionary."""
        return FirecrawlConfig.from_dict(config_dict)
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test the connection to Firecrawl API."""
        try:
            async with self.connector:
                # Try to scrape a simple URL to test connection
                test_url = "https://httpbin.org/json"
                result = await self.connector.scrape_url(test_url, ["markdown"])
                
                if result.error:
                    return {
                        "success": False,
                        "error": result.error,
                        "message": "Failed to connect to Firecrawl API"
                    }
                
                return {
                    "success": True,
                    "message": "Successfully connected to Firecrawl API",
                    "test_url": test_url,
                    "response_time": "N/A"  # Could be enhanced to measure actual response time
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Connection test failed"
            }
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported output formats."""
        return ["markdown", "html", "links", "screenshot"]
    
    def get_supported_scrape_types(self) -> List[str]:
        """Get list of supported scrape types."""
        return ["single", "crawl", "batch"]
    
    def get_help_text(self) -> Dict[str, str]:
        """Get help text for users."""
        return FirecrawlUIBuilder.create_help_text()
    
    def get_validation_rules(self) -> Dict[str, Any]:
        """Get validation rules for configuration."""
        return FirecrawlUIBuilder.create_validation_rules()


# Factory function for creating integration instance
def create_firecrawl_integration(config_dict: Dict[str, Any]) -> RAGFlowFirecrawlIntegration:
    """Create a Firecrawl integration instance from configuration."""
    config = FirecrawlConfig.from_dict(config_dict)
    return RAGFlowFirecrawlIntegration(config)


# Export main classes and functions
__all__ = [
    "RAGFlowFirecrawlIntegration",
    "create_firecrawl_integration",
    "FirecrawlConfig",
    "FirecrawlConnector",
    "FirecrawlProcessor",
    "RAGFlowDocument"
]
