"""
Content processor for converting Firecrawl output to RAGFlow document format.
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


import re
import hashlib
from typing import List, Dict, Any
from dataclasses import dataclass
import logging
from datetime import datetime

from firecrawl_connector import ScrapedContent


@dataclass
class RAGFlowDocument:
    """Represents a document in RAGFlow format."""
    
    id: str
    title: str
    content: str
    source_url: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    content_type: str = "text"
    language: str = "en"
    chunk_size: int = 1000
    chunk_overlap: int = 200


class FirecrawlProcessor:
    """Processes Firecrawl content for RAGFlow integration."""
    
    def __init__(self):
        """Initialize the processor."""
        self.logger = logging.getLogger(__name__)
    
    def generate_document_id(self, url: str, content: str) -> str:
        """Generate a unique document ID."""
        # Create a hash based on URL and content
        content_hash = hashlib.md5(f"{url}:{content[:100]}".encode()).hexdigest()
        return f"firecrawl_{content_hash}"
    
    def clean_content(self, content: str) -> str:
        """Clean and normalize content."""
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove HTML tags if present
        content = re.sub(r'<[^>]+>', '', content)
        
        # Remove special characters that might cause issues
        content = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\"\']', '', content)
        
        return content.strip()
    
    def extract_title(self, content: ScrapedContent) -> str:
        """Extract title from scraped content."""
        if content.title:
            return content.title
        
        if content.metadata and content.metadata.get("title"):
            return content.metadata["title"]
        
        # Extract title from markdown if available
        if content.markdown:
            title_match = re.search(r'^#\s+(.+)$', content.markdown, re.MULTILINE)
            if title_match:
                return title_match.group(1).strip()
        
        # Fallback to URL
        return content.url.split('/')[-1] or content.url
    
    def extract_description(self, content: ScrapedContent) -> str:
        """Extract description from scraped content."""
        if content.description:
            return content.description
        
        if content.metadata and content.metadata.get("description"):
            return content.metadata["description"]
        
        # Extract first paragraph from markdown
        if content.markdown:
            # Remove headers and get first paragraph
            text = re.sub(r'^#+\s+.*$', '', content.markdown, flags=re.MULTILINE)
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            if paragraphs:
                return paragraphs[0][:200] + "..." if len(paragraphs[0]) > 200 else paragraphs[0]
        
        return ""
    
    def extract_language(self, content: ScrapedContent) -> str:
        """Extract language from content metadata."""
        if content.metadata and content.metadata.get("language"):
            return content.metadata["language"]
        
        # Simple language detection based on common words
        if content.markdown:
            text = content.markdown.lower()
            if any(word in text for word in ["the", "and", "or", "but", "in", "on", "at"]):
                return "en"
            elif any(word in text for word in ["le", "la", "les", "de", "du", "des"]):
                return "fr"
            elif any(word in text for word in ["der", "die", "das", "und", "oder"]):
                return "de"
            elif any(word in text for word in ["el", "la", "los", "las", "de", "del"]):
                return "es"
        
        return "en"  # Default to English
    
    def create_metadata(self, content: ScrapedContent) -> Dict[str, Any]:
        """Create comprehensive metadata for RAGFlow document."""
        metadata = {
            "source": "firecrawl",
            "url": content.url,
            "domain": self.extract_domain(content.url),
            "scraped_at": datetime.utcnow().isoformat(),
            "status_code": content.status_code,
            "content_length": len(content.markdown or ""),
            "has_html": bool(content.html),
            "has_markdown": bool(content.markdown)
        }
        
        # Add original metadata if available
        if content.metadata:
            metadata.update({
                "original_title": content.metadata.get("title"),
                "original_description": content.metadata.get("description"),
                "original_language": content.metadata.get("language"),
                "original_keywords": content.metadata.get("keywords"),
                "original_robots": content.metadata.get("robots"),
                "og_title": content.metadata.get("ogTitle"),
                "og_description": content.metadata.get("ogDescription"),
                "og_image": content.metadata.get("ogImage"),
                "og_url": content.metadata.get("ogUrl")
            })
        
        # LINEAJE: runtime guardrail checks `metadata` as it flows from the agent to the user interface, before it leaves the application (in FirecrawlProcessor.create_metadata).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `metadata` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9ca76aa1d122611b6d69e9de6cb5fa2b867131ceada73af7f4b1185b0d24374b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9ca76aa1d122611b6d69e9de6cb5fa2b867131ceada73af7f4b1185b0d24374b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_processor.py', 'line': 142, 'function': 'FirecrawlProcessor.create_metadata'}, 'file': 'intergrations/firecrawl/firecrawl_processor.py', 'line': 142, 'function': 'create_metadata', 'agent_name': 'FirecrawlProcessor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            metadata = _gr_client.enforce(_gr_site, metadata, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return metadata
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except Exception:
            return ""
    
    def process_content(self, content: ScrapedContent) -> RAGFlowDocument:
        """Process scraped content into RAGFlow document format."""
        if content.error:
            raise ValueError(f"Content has error: {content.error}")
        
        # Determine primary content
        primary_content = content.markdown or content.html or ""
        if not primary_content:
            raise ValueError("No content available to process")
        
        # Clean content
        cleaned_content = self.clean_content(primary_content)
        
        # Extract metadata
        title = self.extract_title(content)
        language = self.extract_language(content)
        metadata = self.create_metadata(content)
        
        # Generate document ID
        doc_id = self.generate_document_id(content.url, cleaned_content)
        
        # Create RAGFlow document
        document = RAGFlowDocument(
            id=doc_id,
            title=title,
            content=cleaned_content,
            source_url=content.url,
            metadata=metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            content_type="text",
            language=language
        )
        
        # LINEAJE: runtime guardrail checks `document` as it flows from the agent to the user interface, before it leaves the application (in FirecrawlProcessor.process_content).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `document` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ae11645f879bb1de97c3c40552d8f201ab1ccd7491788d6d307f51c281915a77'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ae11645f879bb1de97c3c40552d8f201ab1ccd7491788d6d307f51c281915a77', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_processor.py', 'line': 186, 'function': 'FirecrawlProcessor.process_content'}, 'file': 'intergrations/firecrawl/firecrawl_processor.py', 'line': 186, 'function': 'process_content', 'agent_name': 'FirecrawlProcessor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            document = _gr_client.enforce(_gr_site, document, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return document
    
    def process_batch(self, contents: List[ScrapedContent]) -> List[RAGFlowDocument]:
        """Process multiple scraped contents into RAGFlow documents."""
        documents = []
        
        for content in contents:
            try:
                document = self.process_content(content)
                documents.append(document)
            except Exception as e:
                _lineaje_payload = f"Failed to process content from {content.url}: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in FirecrawlProcessor.process_batch).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:0086e64bb089df1e6ffba695c5e7100150c71714144c8adc2873fe033e8d7536'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0086e64bb089df1e6ffba695c5e7100150c71714144c8adc2873fe033e8d7536', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_processor.py', 'line': 197, 'function': 'FirecrawlProcessor.process_batch'}, 'file': 'intergrations/firecrawl/firecrawl_processor.py', 'line': 197, 'function': 'process_batch', 'agent_name': 'FirecrawlProcessor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.error(_lineaje_payload)
                continue
        
        # LINEAJE: runtime guardrail checks `documents` as it flows from the agent to the user interface, before it leaves the application (in FirecrawlProcessor.process_batch).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `documents` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a22f8552690e840933c842b6d6e8d9d21410be01303edbd3e0aa4863a0b72ec3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a22f8552690e840933c842b6d6e8d9d21410be01303edbd3e0aa4863a0b72ec3', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_processor.py', 'line': 200, 'function': 'FirecrawlProcessor.process_batch'}, 'file': 'intergrations/firecrawl/firecrawl_processor.py', 'line': 200, 'function': 'process_batch', 'agent_name': 'FirecrawlProcessor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            documents = _gr_client.enforce(_gr_site, documents, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return documents
    
    def chunk_content(self, document: RAGFlowDocument, 
                     chunk_size: int = 1000, 
                     chunk_overlap: int = 200) -> List[Dict[str, Any]]:
        """Chunk document content for RAG processing."""
        content = document.content
        chunks = []
        
        if len(content) <= chunk_size:
            return [{
                "id": f"{document.id}_chunk_0",
                "content": content,
                "metadata": {
                    **document.metadata,
                    "chunk_index": 0,
                    "total_chunks": 1
                }
            }]
        
        # Split content into chunks
        start = 0
        chunk_index = 0
        
        while start < len(content):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(content):
                # Look for sentence endings
                sentence_end = content.rfind('.', start, end)
                if sentence_end > start + chunk_size // 2:
                    end = sentence_end + 1
            
            chunk_content = content[start:end].strip()
            
            if chunk_content:
                chunks.append({
                    "id": f"{document.id}_chunk_{chunk_index}",
                    "content": chunk_content,
                    "metadata": {
                        **document.metadata,
                        "chunk_index": chunk_index,
                        "total_chunks": len(chunks) + 1,  # Will be updated
                        "chunk_start": start,
                        "chunk_end": end
                    }
                })
                chunk_index += 1
            
            # Move start position with overlap
            start = end - chunk_overlap
            if start >= len(content):
                break
        
        # Update total chunks count
        for chunk in chunks:
            chunk["metadata"]["total_chunks"] = len(chunks)
        
        # LINEAJE: runtime guardrail checks `chunks` as it flows from the agent to the user interface, before it leaves the application (in FirecrawlProcessor.chunk_content).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `chunks` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:016dbe41e2935b3cef4bfba7c7bec8f293784252923dba6ab61a9cd2293a4c72'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:016dbe41e2935b3cef4bfba7c7bec8f293784252923dba6ab61a9cd2293a4c72', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/firecrawl/firecrawl_processor.py', 'line': 259, 'function': 'FirecrawlProcessor.chunk_content'}, 'file': 'intergrations/firecrawl/firecrawl_processor.py', 'line': 259, 'function': 'chunk_content', 'agent_name': 'FirecrawlProcessor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            chunks = _gr_client.enforce(_gr_site, chunks, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return chunks
    
    def validate_document(self, document: RAGFlowDocument) -> bool:
        """Validate RAGFlow document."""
        if not document.id:
            return False
        
        if not document.title:
            return False
        
        if not document.content:
            return False
        
        if not document.source_url:
            return False
        
        return True
