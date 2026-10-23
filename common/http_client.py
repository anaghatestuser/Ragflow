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

# Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse, urlunparse

from common import settings
import httpx

logger = logging.getLogger(__name__)

# Default knobs; keep conservative to avoid unexpected behavioural changes.
DEFAULT_TIMEOUT = float(os.environ.get("HTTP_CLIENT_TIMEOUT", "15"))
# Align with requests default: follow redirects with a max of 30 unless overridden.
DEFAULT_FOLLOW_REDIRECTS = bool(
    int(os.environ.get("HTTP_CLIENT_FOLLOW_REDIRECTS", "1"))
)
DEFAULT_MAX_REDIRECTS = int(os.environ.get("HTTP_CLIENT_MAX_REDIRECTS", "30"))
DEFAULT_MAX_RETRIES = int(os.environ.get("HTTP_CLIENT_MAX_RETRIES", "2"))
DEFAULT_BACKOFF_FACTOR = float(os.environ.get("HTTP_CLIENT_BACKOFF_FACTOR", "0.5"))
DEFAULT_PROXY = os.environ.get("HTTP_CLIENT_PROXY")
DEFAULT_USER_AGENT = os.environ.get("HTTP_CLIENT_USER_AGENT", "ragflow-http-client")


def _clean_headers(
    headers: Optional[Dict[str, str]], auth_token: Optional[str] = None
) -> Optional[Dict[str, str]]:
    merged_headers: Dict[str, str] = {}
    if DEFAULT_USER_AGENT:
        merged_headers["User-Agent"] = DEFAULT_USER_AGENT
    if auth_token:
        merged_headers["Authorization"] = auth_token
    if headers is None:
        return merged_headers or None
    merged_headers.update({str(k): str(v) for k, v in headers.items() if v is not None})
    return merged_headers or None


def _get_delay(backoff_factor: float, attempt: int) -> float:
    return backoff_factor * (2**attempt)


# List of sensitive parameters to redact from URLs before logging
_SENSITIVE_QUERY_KEYS = {"client_secret", "secret", "code", "access_token", "refresh_token", "password", "token", "app_secret"}

def _redact_sensitive_url_params(url: str) -> str:
    """
    Return a version of the URL that is safe to log.

    We intentionally drop query parameters and userinfo to avoid leaking
    credentials or tokens via logs. Only scheme, host, port and path
    are preserved.
    """
    try:
        parsed = urlparse(url)
        # Remove any potential userinfo (username:password@)
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        # Reconstruct URL without query, params, fragment, or userinfo.
        safe_url = urlunparse(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                "",  # params
                "",  # query
                "",  # fragment
            )
        )
        # LINEAJE: runtime guardrail checks `safe_url` as it flows from the agent to the user interface, before it leaves the application (in _redact_sensitive_url_params).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `safe_url` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:4abcf66e852e8b607a81d867b42e2d308cc831d98ab4181c07868f61490efbdf'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4abcf66e852e8b607a81d867b42e2d308cc831d98ab4181c07868f61490efbdf', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/http_client.py', 'line': 85, 'function': '_redact_sensitive_url_params'}, 'file': 'common/http_client.py', 'line': 85, 'function': '_redact_sensitive_url_params', 'agent_name': '_redact_sensitive_url_params', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            safe_url = _gr_client.enforce(_gr_site, safe_url, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return safe_url
    except Exception:
        # If parsing fails, fall back to omitting the URL entirely.
        return "<redacted-url>"

def _is_sensitive_url(url: str) -> bool:
    """Return True if URL is one of the configured OAuth endpoints."""
    # Collect known sensitive endpoint URLs from settings
    oauth_urls = set()
    # GitHub OAuth endpoints
    try:
        if settings.GITHUB_OAUTH is not None:
            url_val = settings.GITHUB_OAUTH.get("url")
            if url_val:
                oauth_urls.add(url_val)
    except Exception:
        pass
    # Feishu OAuth endpoints
    try:
        if settings.FEISHU_OAUTH is not None:
            for k in ("app_access_token_url", "user_access_token_url"):
                url_val = settings.FEISHU_OAUTH.get(k)
                if url_val:
                    oauth_urls.add(url_val)
    except Exception:
        pass
    # Defensive normalization: compare only scheme+netloc+path
    url_obj = urlparse(url)
    for sensitive_url in oauth_urls:
        sensitive_obj = urlparse(sensitive_url)
        if (url_obj.scheme, url_obj.netloc, url_obj.path) == (sensitive_obj.scheme, sensitive_obj.netloc, sensitive_obj.path):
            return True
    return False

async def async_request(
    method: str,
    url: str,
    *,
    request_timeout: float | httpx.Timeout | None = None,
    follow_redirects: bool | None = None,
    max_redirects: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None,
    auth_token: Optional[str] = None,
    retries: Optional[int] = None,
    backoff_factor: Optional[float] = None,
    proxy: Any = None,
    **kwargs: Any,
) -> httpx.Response:
    """Lightweight async HTTP wrapper using httpx.AsyncClient with safe defaults."""
    timeout = request_timeout if request_timeout is not None else DEFAULT_TIMEOUT
    follow_redirects = (
        DEFAULT_FOLLOW_REDIRECTS if follow_redirects is None else follow_redirects
    )
    max_redirects = DEFAULT_MAX_REDIRECTS if max_redirects is None else max_redirects
    retries = DEFAULT_MAX_RETRIES if retries is None else max(retries, 0)
    backoff_factor = (
        DEFAULT_BACKOFF_FACTOR if backoff_factor is None else backoff_factor
    )
    headers = _clean_headers(headers, auth_token=auth_token)
    proxy = DEFAULT_PROXY if proxy is None else proxy

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=follow_redirects,
        max_redirects=max_redirects,
        proxy=proxy,
    ) as client:
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                start = time.monotonic()
                response = await client.request(
                    method=method, url=url, headers=headers, **kwargs
                )
                # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in async_request).
                #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: low).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:ab34ef55cf3458fe4c319b0ce7282233c7a537d972df02dc7879d1bbc89b5e03'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ab34ef55cf3458fe4c319b0ce7282233c7a537d972df02dc7879d1bbc89b5e03', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/http_client.py', 'line': 156, 'function': 'async_request'}, 'file': 'common/http_client.py', 'line': 156, 'function': 'async_request', 'agent_name': 'async_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=156))
                except _gr_client.GuardrailUnavailableError:
                    pass
                duration = time.monotonic() - start
                if not _is_sensitive_url(url):
                    log_url = _redact_sensitive_url_params(url)
                    _lineaje_payload = f"async_request {method} {log_url} -> {response.status_code} in {duration:.3f}s"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in async_request).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:256a082290b3adc7cb4c80966e2824362f790edef850833414c173540a0f1fae'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:256a082290b3adc7cb4c80966e2824362f790edef850833414c173540a0f1fae', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/http_client.py', 'line': 162, 'function': 'async_request'}, 'file': 'common/http_client.py', 'line': 162, 'function': 'async_request', 'agent_name': 'async_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logger.debug(_lineaje_payload)
                # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the user interface, before it leaves the application (in async_request).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:db9d4cf481340a9bf43f553ba65e7f2f70ea56fba5d56ceaec64d480536b6823'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:db9d4cf481340a9bf43f553ba65e7f2f70ea56fba5d56ceaec64d480536b6823', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/http_client.py', 'line': 163, 'function': 'async_request'}, 'file': 'common/http_client.py', 'line': 163, 'function': 'async_request', 'agent_name': 'async_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    response = _gr_client.enforce(_gr_site, response, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return response
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt >= retries:
                    if not _is_sensitive_url(url):
                        log_url = _redact_sensitive_url_params(url)
                        _lineaje_payload = f"async_request exhausted retries for {method}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in async_request).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:e5655cf843ed2e18787bf164400d4cd81d34a09aba93af1b148d8580b29df76f'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e5655cf843ed2e18787bf164400d4cd81d34a09aba93af1b148d8580b29df76f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/http_client.py', 'line': 169, 'function': 'async_request'}, 'file': 'common/http_client.py', 'line': 169, 'function': 'async_request', 'agent_name': 'async_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                        try:
                            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logger.warning(_lineaje_payload)
                    raise
                delay = _get_delay(backoff_factor, attempt)
                if not _is_sensitive_url(url):
                    log_url = _redact_sensitive_url_params(url)
                    _lineaje_payload = f"async_request attempt {attempt + 1}/{retries + 1} failed for {method}; retrying in {delay:.2f}s"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in async_request).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:20f45f01753b8f4c1919615cfee6998768597fcce94df029bc1fede6183e8b68'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:20f45f01753b8f4c1919615cfee6998768597fcce94df029bc1fede6183e8b68', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/http_client.py', 'line': 174, 'function': 'async_request'}, 'file': 'common/http_client.py', 'line': 174, 'function': 'async_request', 'agent_name': 'async_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logger.warning(
                        _lineaje_payload
                    )
                    raise
                delay = _get_delay(backoff_factor, attempt)
                # Avoid including the (potentially sensitive) URL in retry logs.
                _lineaje_payload = f"async_request attempt {attempt + 1}/{retries + 1} failed for {method}; retrying in {delay:.2f}s"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in async_request).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:042ad6c64af95eb4d3aff1b50a0c57281e7479c1376d51013ce2fb59f9bebbf7'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:042ad6c64af95eb4d3aff1b50a0c57281e7479c1376d51013ce2fb59f9bebbf7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/http_client.py', 'line': 180, 'function': 'async_request'}, 'file': 'common/http_client.py', 'line': 180, 'function': 'async_request', 'agent_name': 'async_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logger.warning(
                    _lineaje_payload
                )
                await asyncio.sleep(delay)
        raise last_exc  # pragma: no cover


def sync_request(
    method: str,
    url: str,
    *,
    timeout: float | httpx.Timeout | None = None,
    follow_redirects: bool | None = None,
    max_redirects: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None,
    auth_token: Optional[str] = None,
    retries: Optional[int] = None,
    backoff_factor: Optional[float] = None,
    proxy: Any = None,
    **kwargs: Any,
) -> httpx.Response:
    """Synchronous counterpart to async_request, for CLI/tests or sync contexts."""
    timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
    follow_redirects = (
        DEFAULT_FOLLOW_REDIRECTS if follow_redirects is None else follow_redirects
    )
    max_redirects = DEFAULT_MAX_REDIRECTS if max_redirects is None else max_redirects
    retries = DEFAULT_MAX_RETRIES if retries is None else max(retries, 0)
    backoff_factor = (
        DEFAULT_BACKOFF_FACTOR if backoff_factor is None else backoff_factor
    )
    headers = _clean_headers(headers, auth_token=auth_token)
    proxy = DEFAULT_PROXY if proxy is None else proxy

    with httpx.Client(
        timeout=timeout,
        follow_redirects=follow_redirects,
        max_redirects=max_redirects,
        proxy=proxy,
    ) as client:
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                start = time.monotonic()
                response = client.request(
                    method=method, url=url, headers=headers, **kwargs
                )
                duration = time.monotonic() - start
                _lineaje_payload = f"sync_request {method} {url} -> {response.status_code} in {duration:.3f}s"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in sync_request).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:1561186667e2f75d9ec8306eb06588b8d123e69380f4f5115a21c8fc0cb34cae'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1561186667e2f75d9ec8306eb06588b8d123e69380f4f5115a21c8fc0cb34cae', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/http_client.py', 'line': 228, 'function': 'sync_request'}, 'file': 'common/http_client.py', 'line': 228, 'function': 'sync_request', 'agent_name': 'sync_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logger.debug(
                    _lineaje_payload
                )
                # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the user interface, before it leaves the application (in sync_request).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:702d1cc6530b9a3459e28e85d21f340771303d1f8c7fd04ab9f21eba95f375a4'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:702d1cc6530b9a3459e28e85d21f340771303d1f8c7fd04ab9f21eba95f375a4', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/http_client.py', 'line': 231, 'function': 'sync_request'}, 'file': 'common/http_client.py', 'line': 231, 'function': 'sync_request', 'agent_name': 'sync_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    response = _gr_client.enforce(_gr_site, response, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return response
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt >= retries:
                    _lineaje_payload = f"sync_request exhausted retries for {method} {url}: {exc}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in sync_request).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:b563e97f17dfa31c074e289310c806bd82d0e6c8b2ec7dd7c5566e7c522232a0'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b563e97f17dfa31c074e289310c806bd82d0e6c8b2ec7dd7c5566e7c522232a0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/http_client.py', 'line': 235, 'function': 'sync_request'}, 'file': 'common/http_client.py', 'line': 235, 'function': 'sync_request', 'agent_name': 'sync_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logger.warning(
                        _lineaje_payload
                    )
                    raise
                delay = _get_delay(backoff_factor, attempt)
                _lineaje_payload = f"sync_request attempt {attempt + 1}/{retries + 1} failed for {method} {url}: {exc}; retrying in {delay:.2f}s"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in sync_request).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:876289bff323c49da7963b55771510fe08b2429390d090facd7efb748c68dd13'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:876289bff323c49da7963b55771510fe08b2429390d090facd7efb748c68dd13', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/http_client.py', 'line': 240, 'function': 'sync_request'}, 'file': 'common/http_client.py', 'line': 240, 'function': 'sync_request', 'agent_name': 'sync_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logger.warning(
                    _lineaje_payload
                )
                time.sleep(delay)
        raise last_exc  # pragma: no cover


__all__ = [
    "async_request",
    "sync_request",
    "DEFAULT_TIMEOUT",
    "DEFAULT_FOLLOW_REDIRECTS",
    "DEFAULT_MAX_REDIRECTS",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_BACKOFF_FACTOR",
    "DEFAULT_PROXY",
    "DEFAULT_USER_AGENT",
]
