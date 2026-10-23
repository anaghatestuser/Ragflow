"""
Configuration management for Firecrawl integration with RAGFlow.
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


import os
from typing import Dict, Any
from dataclasses import dataclass
import json


@dataclass
class FirecrawlConfig:
    """Configuration class for Firecrawl integration."""
    
    api_key: str
    api_url: str = "https://api.firecrawl.dev"
    max_retries: int = 3
    timeout: int = 30
    rate_limit_delay: float = 1.0
    max_concurrent_requests: int = 5
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.api_key:
            raise ValueError("Firecrawl API key is required")
        
        if not self.api_key.startswith("fc-"):
            raise ValueError("Invalid Firecrawl API key format. Must start with 'fc-'")
        
        if self.max_retries < 1 or self.max_retries > 10:
            raise ValueError("Max retries must be between 1 and 10")
        
        if self.timeout < 5 or self.timeout > 300:
            raise ValueError("Timeout must be between 5 and 300 seconds")
        
        if self.rate_limit_delay < 0.1 or self.rate_limit_delay > 10.0:
            raise ValueError("Rate limit delay must be between 0.1 and 10.0 seconds")
    
    @classmethod
    def from_env(cls) -> "FirecrawlConfig":
        """Create configuration from environment variables."""
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY environment variable not set")
        
        return cls(
            api_key=api_key,
            api_url=os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev"),
            max_retries=int(os.getenv("FIRECRAWL_MAX_RETRIES", "3")),
            timeout=int(os.getenv("FIRECRAWL_TIMEOUT", "30")),
            rate_limit_delay=float(os.getenv("FIRECRAWL_RATE_LIMIT_DELAY", "1.0")),
            max_concurrent_requests=int(os.getenv("FIRECRAWL_MAX_CONCURRENT", "5"))
        )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "FirecrawlConfig":
        """Create configuration from dictionary."""
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "api_key": self.api_key,
            "api_url": self.api_url,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "rate_limit_delay": self.rate_limit_delay,
            "max_concurrent_requests": self.max_concurrent_requests
        }
    
    def to_json(self) -> str:
        """Convert configuration to JSON string."""
        _lineaje_payload = self.to_dict()
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to an external endpoint, before it leaves the application (in FirecrawlConfig.to_json).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `_lineaje_payload` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:bccd322af515787607c28afa538f6064741e7e502a89ca3b1f066134356c4da6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bccd322af515787607c28afa538f6064741e7e502a89ca3b1f066134356c4da6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_config.py', 'line': 73, 'function': 'FirecrawlConfig.to_json'}, 'file': 'intergrations/firecrawl/firecrawl_config.py', 'line': 73, 'function': 'to_json', 'agent_name': 'FirecrawlConfig', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=73)
        except _gr_client.GuardrailUnavailableError:
            pass
        return json.dumps(_lineaje_payload, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "FirecrawlConfig":
        """Create configuration from JSON string."""
        config_dict = json.loads(json_str)
        return cls.from_dict(config_dict)
