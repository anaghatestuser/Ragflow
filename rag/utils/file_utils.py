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

import io
import hashlib
import zipfile
import requests
from requests.exceptions import Timeout, RequestException
from io import BytesIO
from typing import List, Union, Tuple, Optional, Dict
import PyPDF2
from docx import Document
import olefile

def _is_zip(h: bytes) -> bool:
    return h.startswith(b"PK\x03\x04") or h.startswith(b"PK\x05\x06") or h.startswith(b"PK\x07\x08")

def _is_pdf(h: bytes) -> bool:
    return h.startswith(b"%PDF-")

def _is_ole(h: bytes) -> bool:
    return h.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1")

def _sha10(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:10]

def _guess_ext(b: bytes) -> str:
    h = b[:8]
    if _is_zip(h):
        try:
            with zipfile.ZipFile(io.BytesIO(b), "r") as z:
                names = [n.lower() for n in z.namelist()]
                if any(n.startswith("word/") for n in names):
                    return ".docx"
                if any(n.startswith("ppt/") for n in names):
                    return ".pptx"
                if any(n.startswith("xl/") for n in names):
                    return ".xlsx"
        except Exception:
            pass
        return ".zip"
    if _is_pdf(h):
        return ".pdf"
    if _is_ole(h):
        return ".doc"
    return ".bin"

# Try to extract the real embedded payload from OLE's Ole10Native
def _extract_ole10native_payload(data: bytes) -> bytes:
    try:
        pos = 0
        if len(data) < 4:
            # LINEAJE: runtime guardrail checks `data` as it flows from the agent to the user interface, before it leaves the application (in _extract_ole10native_payload).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3571d64815ba54f8f788b81b539625c722d4ed4e5b8b12b491daeb7d5e26e756'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3571d64815ba54f8f788b81b539625c722d4ed4e5b8b12b491daeb7d5e26e756', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/file_utils.py', 'line': 66, 'function': '_extract_ole10native_payload'}, 'file': 'rag/utils/file_utils.py', 'line': 66, 'function': '_extract_ole10native_payload', 'agent_name': '_extract_ole10native_payload', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                data = _gr_client.enforce(_gr_site, data, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return data
        _ = int.from_bytes(data[pos:pos+4], "little")
        pos += 4
        # filename/src/tmp (NUL-terminated ANSI)
        for _ in range(3):
            z = data.index(b"\x00", pos)
            pos = z + 1
        # skip unknown 4 bytes
        pos += 4
        if pos + 4 > len(data):
            # LINEAJE: runtime guardrail checks `data` as it flows from the agent to the user interface, before it leaves the application (in _extract_ole10native_payload).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e3f60d5cd74d9a5b0e7ca7e8bb50d0184508c0431177a8debd6c8c12cd00a823'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e3f60d5cd74d9a5b0e7ca7e8bb50d0184508c0431177a8debd6c8c12cd00a823', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/file_utils.py', 'line': 76, 'function': '_extract_ole10native_payload'}, 'file': 'rag/utils/file_utils.py', 'line': 76, 'function': '_extract_ole10native_payload', 'agent_name': '_extract_ole10native_payload', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                data = _gr_client.enforce(_gr_site, data, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return data
        size = int.from_bytes(data[pos:pos+4], "little")
        pos += 4
        if pos + size <= len(data):
            return data[pos:pos+size]
    except Exception:
        pass
    # LINEAJE: runtime guardrail checks `data` as it flows from the agent to the user interface, before it leaves the application (in _extract_ole10native_payload).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:0d5186268de9d6131f312716e41afa953a32d87e2afa17bd20c7472bf3caaaf4'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0d5186268de9d6131f312716e41afa953a32d87e2afa17bd20c7472bf3caaaf4', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/file_utils.py', 'line': 83, 'function': '_extract_ole10native_payload'}, 'file': 'rag/utils/file_utils.py', 'line': 83, 'function': '_extract_ole10native_payload', 'agent_name': '_extract_ole10native_payload', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        data = _gr_client.enforce(_gr_site, data, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return data

def extract_embed_file(target: Union[bytes, bytearray]) -> List[Tuple[str, bytes]]:
    """
    Only extract the 'first layer' of embedding, returning raw (filename, bytes).
    """
    top = bytes(target)
    head = top[:8]
    out: List[Tuple[str, bytes]] = []
    seen = set()

    def push(b: bytes, name_hint: str = ""):
        h10 = _sha10(b)
        if h10 in seen:
            return
        seen.add(h10)
        ext = _guess_ext(b)
        # If name_hint has an extension use its basename; else fallback to guessed ext
        if "." in name_hint:
            fname = name_hint.split("/")[-1]
        else:
            fname = f"{h10}{ext}"
        out.append((fname, b))

    # OOXML/ZIP container (docx/xlsx/pptx)
    if _is_zip(head):
        try:
            with zipfile.ZipFile(io.BytesIO(top), "r") as z:
                embed_dirs = (
                    "word/embeddings/", "word/objects/", "word/activex/",
                    "xl/embeddings/", "ppt/embeddings/"
                )
                for name in z.namelist():
                    low = name.lower()
                    if any(low.startswith(d) for d in embed_dirs):
                        try:
                            b = z.read(name)
                            push(b, name)
                        except Exception:
                            pass
        except Exception:
            pass
        # LINEAJE: runtime guardrail checks `out` as it flows from the agent to the user interface, before it leaves the application (in push).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `out` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e9db44236f554fcc31f3bbc3bac8dab1371c4469e70d6ab62870d6db27171768'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e9db44236f554fcc31f3bbc3bac8dab1371c4469e70d6ab62870d6db27171768', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/file_utils.py', 'line': 125, 'function': 'extract_embed_file'}, 'file': 'rag/utils/file_utils.py', 'line': 125, 'function': 'push', 'agent_name': 'push', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            out = _gr_client.enforce(_gr_site, out, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return out

    # OLE container (doc/ppt/xls)
    if _is_ole(head):
        try:
            with olefile.OleFileIO(io.BytesIO(top)) as ole:
                for entry in ole.listdir():
                    p = "/".join(entry)
                    try:
                        data = ole.openstream(entry).read()
                    except Exception:
                        continue
                    if not data:
                        continue
                    if "Ole10Native" in p or "ole10native" in p.lower():
                        data = _extract_ole10native_payload(data)
                    push(data, p)
        except Exception:
            pass
        # LINEAJE: runtime guardrail checks `out` as it flows from the agent to the user interface, before it leaves the application (in push).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `out` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8ae2111ae3c409d9152be1b2ee92d76ce657a5db3987c1a679013dd276de312d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8ae2111ae3c409d9152be1b2ee92d76ce657a5db3987c1a679013dd276de312d', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/file_utils.py', 'line': 144, 'function': 'extract_embed_file'}, 'file': 'rag/utils/file_utils.py', 'line': 144, 'function': 'push', 'agent_name': 'push', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            out = _gr_client.enforce(_gr_site, out, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return out

    # LINEAJE: runtime guardrail checks `out` as it flows from the agent to the user interface, before it leaves the application (in extract_embed_file).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `out` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:61e959a2ef1e52c2b7afd4209434baac4a551dff0c30503e17094bb6120ed04b'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:61e959a2ef1e52c2b7afd4209434baac4a551dff0c30503e17094bb6120ed04b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/file_utils.py', 'line': 146, 'function': 'extract_embed_file'}, 'file': 'rag/utils/file_utils.py', 'line': 146, 'function': 'extract_embed_file', 'agent_name': 'extract_embed_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        out = _gr_client.enforce(_gr_site, out, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return out


def extract_links_from_docx(docx_bytes: bytes):
    """
    Extract all hyperlinks from a Word (.docx) document binary stream.

    Args:
        docx_bytes (bytes): Raw bytes of a .docx file.

    Returns:
        set[str]: A set of unique hyperlink URLs.
    """
    links = set()
    with BytesIO(docx_bytes) as bio:
        document = Document(bio)

        # Each relationship may represent a hyperlink, image, footer, etc.
        for rel in document.part.rels.values():
            if rel.reltype == (
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
            ):
                links.add(rel.target_ref)

    # LINEAJE: runtime guardrail checks `links` as it flows from the agent to the user interface, before it leaves the application (in extract_links_from_docx).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `links` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:968b2d4074e25c59b13b34e6d29edbcb3f70d4b4f6ca3c46183963b8c45a6f44'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:968b2d4074e25c59b13b34e6d29edbcb3f70d4b4f6ca3c46183963b8c45a6f44', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/file_utils.py', 'line': 170, 'function': 'extract_links_from_docx'}, 'file': 'rag/utils/file_utils.py', 'line': 170, 'function': 'extract_links_from_docx', 'agent_name': 'extract_links_from_docx', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        links = _gr_client.enforce(_gr_site, links, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return links


def extract_links_from_pdf(pdf_bytes: bytes):
    """
    Extract all clickable hyperlinks from a PDF binary stream.

    Args:
        pdf_bytes (bytes): Raw bytes of a PDF file.

    Returns:
        set[str]: A set of unique hyperlink URLs (unordered).
    """
    links = set()
    with BytesIO(pdf_bytes) as bio:
        pdf = PyPDF2.PdfReader(bio)

        for page in pdf.pages:
            annots = page.get("/Annots")
            if not annots or isinstance(annots, PyPDF2.generic.IndirectObject):
                continue
            for annot in annots:
                obj = annot.get_object()
                a = obj.get("/A")
                if a and a.get("/URI"):
                    links.add(a["/URI"])

    # LINEAJE: runtime guardrail checks `links` as it flows from the agent to the user interface, before it leaves the application (in extract_links_from_pdf).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `links` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e48b7c7d8c386ace904bd7624aae329e7c864cf8901d082165c040786a6a58cc'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e48b7c7d8c386ace904bd7624aae329e7c864cf8901d082165c040786a6a58cc', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/file_utils.py', 'line': 197, 'function': 'extract_links_from_pdf'}, 'file': 'rag/utils/file_utils.py', 'line': 197, 'function': 'extract_links_from_pdf', 'agent_name': 'extract_links_from_pdf', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        links = _gr_client.enforce(_gr_site, links, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return links


_GLOBAL_SESSION: Optional[requests.Session] = None
def _get_session(headers: Optional[Dict[str, str]] = None) -> requests.Session:
    """Get or create a global reusable session."""
    global _GLOBAL_SESSION
    if _GLOBAL_SESSION is None:
        _GLOBAL_SESSION = requests.Session()
        _GLOBAL_SESSION.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0 Safari/537.36"
            )
        })
    if headers:
        _GLOBAL_SESSION.headers.update(headers)
    return _GLOBAL_SESSION


def extract_html(
    url: str,
    timeout: float = 60.0,
    headers: Optional[Dict[str, str]] = None,
    max_retries: int = 2,
) -> Tuple[Optional[bytes], Dict[str, str]]:
    """
    Extract the full HTML page as raw bytes from a given URL.
    Automatically reuses a persistent HTTP session and applies robust timeout & retry logic.

    Args:
        url (str): Target webpage URL.
        timeout (float): Request timeout in seconds (applies to connect + read).
        headers (dict, optional): Extra HTTP headers.
        max_retries (int): Number of retries on timeout or transient errors.

    Returns:
        tuple(bytes|None, dict):
            - html_bytes: Raw HTML content (or None if failed)
            - metadata: HTTP info (status_code, content_type, final_url, error if any)
    """
    session = _get_session(headers=headers)
    metadata = {"final_url": url, "status_code": "", "content_type": "", "error": ""}

    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()

            html_bytes = resp.content
            metadata.update({
                "final_url": resp.url,
                "status_code": str(resp.status_code),
                "content_type": resp.headers.get("Content-Type", ""),
            })
            return html_bytes, metadata

        except Timeout:
            metadata["error"] = f"Timeout after {timeout}s (attempt {attempt}/{max_retries})"
            if attempt >= max_retries:
                continue
        except RequestException as e:
            metadata["error"] = f"Request failed: {e}"
            continue

    return None, metadata