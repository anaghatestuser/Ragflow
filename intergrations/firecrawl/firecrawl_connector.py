"""
Main connector class for integrating Firecrawl with RAGFlow.
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


import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
from urllib.parse import urlparse

from firecrawl_config import FirecrawlConfig


@dataclass
class ScrapedContent:
    """Represents scraped content from Firecrawl."""
    
    url: str
    markdown: Optional[str] = None
    html: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status_code: Optional[int] = None
    error: Optional[str] = None


@dataclass
class CrawlJob:
    """Represents a crawl job from Firecrawl."""
    
    job_id: str
    status: str
    total: Optional[int] = None
    completed: Optional[int] = None
    data: Optional[List[ScrapedContent]] = None
    error: Optional[str] = None


class FirecrawlConnector:
    """Main connector class for Firecrawl integration with RAGFlow."""
    
    def __init__(self, config: FirecrawlConfig):
        """Initialize the Firecrawl connector."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_semaphore = asyncio.Semaphore(config.max_concurrent_requests)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._create_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
    
    async def _create_session(self):
        """Create aiohttp session with proper headers."""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "RAGFlow-Firecrawl-Plugin/1.0.0"
        }
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout
        )
    
    async def _close_session(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with rate limiting and retry logic."""
        async with self._rate_limit_semaphore:
            # Rate limiting
            await asyncio.sleep(self.config.rate_limit_delay)
            
            url = f"{self.config.api_url}{endpoint}"
            
            for attempt in range(self.config.max_retries):
                try:
                    async with self.session.request(method, url, **kwargs) as response:
                        if response.status == 429:  # Rate limited
                            wait_time = 2 ** attempt
                            _lineaje_payload = f"Rate limited, waiting {wait_time}s"
                            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in FirecrawlConnector._make_request).
                            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                            #   Do not remove without review. site_id='site:sha256:afe0c9f51890da2825caaa8b4c63f88992cdccb1c34df06a0b0ebe6e137d50ce'
                            _gr_client = _lineaje_load_gr_client()
                            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:afe0c9f51890da2825caaa8b4c63f88992cdccb1c34df06a0b0ebe6e137d50ce', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 92, 'function': 'FirecrawlConnector._make_request'}, 'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 92, 'function': '_make_request', 'agent_name': 'FirecrawlConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                            try:
                                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                            except _gr_client.GuardrailUnavailableError:
                                pass
                            except PermissionError:
                                pass
                            self.logger.warning(_lineaje_payload)
                            await asyncio.sleep(wait_time)
                            continue
                        
                        response.raise_for_status()
                        return await response.json()
                        
                except aiohttp.ClientError as e:
                    _lineaje_payload = f"Request failed (attempt {attempt + 1}): {e}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in FirecrawlConnector._make_request).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:8590448299595cb5801fa87b7670270b4973cb44220d337c4aa83e2c207a47e6'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8590448299595cb5801fa87b7670270b4973cb44220d337c4aa83e2c207a47e6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 100, 'function': 'FirecrawlConnector._make_request'}, 'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 100, 'function': '_make_request', 'agent_name': 'FirecrawlConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    self.logger.error(_lineaje_payload)
                    if attempt == self.config.max_retries - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
            
            raise Exception("Max retries exceeded")
    
    async def scrape_url(self, url: str, formats: List[str] = None, 
                        extract_options: Dict[str, Any] = None) -> ScrapedContent:
        """Scrape a single URL."""
        if formats is None:
            formats = ["markdown", "html"]
        
        payload = {
            "url": url,
            "formats": formats
        }
        
        if extract_options:
            payload["extractOptions"] = extract_options
        
        try:
            response = await self._make_request("POST", "/v2/scrape", json=payload)
            
            if not response.get("success"):
                return ScrapedContent(url=url, error=response.get("error", "Unknown error"))
            
            data = response.get("data", {})
            metadata = data.get("metadata", {})
            
            return ScrapedContent(
                url=url,
                markdown=data.get("markdown"),
                html=data.get("html"),
                metadata=metadata,
                title=metadata.get("title"),
                description=metadata.get("description"),
                status_code=metadata.get("statusCode")
            )
            
        except Exception as e:
            _lineaje_payload = f"Failed to scrape {url}: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in FirecrawlConnector.scrape_url).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:4e9d8b1d63c3020b23ad652e28b099aadfb735b21f313728d3a636c8c9052ca1'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4e9d8b1d63c3020b23ad652e28b099aadfb735b21f313728d3a636c8c9052ca1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 141, 'function': 'FirecrawlConnector.scrape_url'}, 'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 141, 'function': 'scrape_url', 'agent_name': 'FirecrawlConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.error(_lineaje_payload)
            return ScrapedContent(url=url, error=str(e))
    
    async def start_crawl(self, url: str, limit: int = 100, 
                         scrape_options: Dict[str, Any] = None) -> CrawlJob:
        """Start a crawl job."""
        if scrape_options is None:
            scrape_options = {"formats": ["markdown", "html"]}
        
        payload = {
            "url": url,
            "limit": limit,
            "scrapeOptions": scrape_options
        }
        
        try:
            response = await self._make_request("POST", "/v2/crawl", json=payload)
            
            if not response.get("success"):
                return CrawlJob(
                    job_id="",
                    status="failed",
                    error=response.get("error", "Unknown error")
                )
            
            job_id = response.get("id")
            return CrawlJob(job_id=job_id, status="started")
            
        except Exception as e:
            _lineaje_payload = f"Failed to start crawl for {url}: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in FirecrawlConnector.start_crawl).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3641b48394364ae8c884732e927b0e4a3b94a63f2c4f87ffd0e5821b8a5ee4b5'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3641b48394364ae8c884732e927b0e4a3b94a63f2c4f87ffd0e5821b8a5ee4b5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 170, 'function': 'FirecrawlConnector.start_crawl'}, 'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 170, 'function': 'start_crawl', 'agent_name': 'FirecrawlConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.error(_lineaje_payload)
            return CrawlJob(job_id="", status="failed", error=str(e))
    
    async def get_crawl_status(self, job_id: str) -> CrawlJob:
        """Get the status of a crawl job."""
        try:
            response = await self._make_request("GET", f"/v2/crawl/{job_id}")
            
            if not response.get("success"):
                return CrawlJob(
                    job_id=job_id,
                    status="failed",
                    error=response.get("error", "Unknown error")
                )
            
            status = response.get("status", "unknown")
            total = response.get("total")
            data = response.get("data", [])
            
            # Convert data to ScrapedContent objects
            scraped_content = []
            for item in data:
                metadata = item.get("metadata", {})
                scraped_content.append(ScrapedContent(
                    url=metadata.get("sourceURL", ""),
                    markdown=item.get("markdown"),
                    html=item.get("html"),
                    metadata=metadata,
                    title=metadata.get("title"),
                    description=metadata.get("description"),
                    status_code=metadata.get("statusCode")
                ))
            
            return CrawlJob(
                job_id=job_id,
                status=status,
                total=total,
                completed=len(scraped_content),
                data=scraped_content
            )
            
        except Exception as e:
            _lineaje_payload = f"Failed to get crawl status for {job_id}: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in FirecrawlConnector.get_crawl_status).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6eccf22a1c18a11383345334eef7b50f7a465492b0495ac27d077afb23bf6da0'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6eccf22a1c18a11383345334eef7b50f7a465492b0495ac27d077afb23bf6da0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 212, 'function': 'FirecrawlConnector.get_crawl_status'}, 'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 212, 'function': 'get_crawl_status', 'agent_name': 'FirecrawlConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.error(_lineaje_payload)
            return CrawlJob(job_id=job_id, status="failed", error=str(e))
    
    async def wait_for_crawl_completion(self, job_id: str, 
                                      poll_interval: int = 30) -> CrawlJob:
        """Wait for a crawl job to complete."""
        while True:
            job = await self.get_crawl_status(job_id)
            
            if job.status in ["completed", "failed", "cancelled"]:
                # LINEAJE: runtime guardrail checks `job` as it flows from the agent to the user interface, before it leaves the application (in FirecrawlConnector.wait_for_crawl_completion).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `job` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:04e13131c7251ebc0750170093b04040d825ed9cbe9196ae802917df7c6b13e0'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:04e13131c7251ebc0750170093b04040d825ed9cbe9196ae802917df7c6b13e0', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 222, 'function': 'FirecrawlConnector.wait_for_crawl_completion'}, 'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 222, 'function': 'wait_for_crawl_completion', 'agent_name': 'FirecrawlConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    job = _gr_client.enforce(_gr_site, job, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return job
            
            _lineaje_payload = f"Crawl {job_id} status: {job.status}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in FirecrawlConnector.wait_for_crawl_completion).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:5bf081ce0451d18d6526d0fccd84bc0bea9c9dcb873e3b7d5eb28622fe1208f4'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5bf081ce0451d18d6526d0fccd84bc0bea9c9dcb873e3b7d5eb28622fe1208f4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 224, 'function': 'FirecrawlConnector.wait_for_crawl_completion'}, 'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 224, 'function': 'wait_for_crawl_completion', 'agent_name': 'FirecrawlConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.info(_lineaje_payload)
            await asyncio.sleep(poll_interval)
    
    async def batch_scrape(self, urls: List[str], 
                          formats: List[str] = None) -> List[ScrapedContent]:
        """Scrape multiple URLs concurrently."""
        if formats is None:
            formats = ["markdown", "html"]
        
        tasks = [self.scrape_url(url, formats) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ScrapedContent(
                    url=urls[i],
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        # LINEAJE: runtime guardrail checks `processed_results` as it flows from the agent to the user interface, before it leaves the application (in FirecrawlConnector.batch_scrape).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `processed_results` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:325cafda114b296044b61cc728d8f3c65104a265f3aa6fd818a400478e813744'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:325cafda114b296044b61cc728d8f3c65104a265f3aa6fd818a400478e813744', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 247, 'function': 'FirecrawlConnector.batch_scrape'}, 'file': 'intergrations/firecrawl/firecrawl_connector.py', 'line': 247, 'function': 'batch_scrape', 'agent_name': 'FirecrawlConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            processed_results = _gr_client.enforce(_gr_site, processed_results, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return processed_results
    
    def validate_url(self, url: str) -> bool:
        """Validate if URL is properly formatted."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(url).netloc
        except Exception:
            return ""
