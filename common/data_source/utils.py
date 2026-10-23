"""Utility functions for all connectors"""
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


import base64
import contextvars
import json
import logging
import math
import os
import re
import threading
import time
from collections.abc import Callable, Generator, Iterator, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, as_completed, wait
from datetime import datetime, timedelta, timezone
from functools import lru_cache, wraps
from io import BytesIO
from itertools import islice
from numbers import Integral
from pathlib import Path
from typing import IO, Any, Generic, Iterable, Optional, Protocol, TypeVar, cast
from urllib.parse import parse_qs, quote, urljoin, urlparse

import boto3
import chardet
import requests
from botocore.client import Config
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session
from googleapiclient.errors import HttpError
from mypy_boto3_s3 import S3Client
from retry import retry
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web import SlackResponse

from common.data_source.config import (
    _ITERATION_LIMIT,
    _NOTION_CALL_TIMEOUT,
    _SLACK_LIMIT,
    CONFLUENCE_OAUTH_TOKEN_URL,
    DOWNLOAD_CHUNK_SIZE,
    EXCLUDED_IMAGE_TYPES,
    RATE_LIMIT_MESSAGE_LOWERCASE,
    SIZE_THRESHOLD_BUFFER,
    BlobType,
)
from common.data_source.exceptions import RateLimitTriedTooManyTimesError
from common.data_source.interfaces import CT, CheckpointedConnector, CheckpointOutputWrapper, ConfluenceUser, LoadFunction, OnyxExtensionType, SecondsSinceUnixEpoch, TokenResponse
from common.data_source.models import BasicExpertInfo, Document

_TZ_SUFFIX_PATTERN = re.compile(r"([+-])([\d:]+)$")


def datetime_from_string(datetime_string: str) -> datetime:
    datetime_string = datetime_string.strip()

    match_jira_format = _TZ_SUFFIX_PATTERN.search(datetime_string)
    if match_jira_format:
        sign, tz_field = match_jira_format.groups()
        digits = tz_field.replace(":", "")

        if digits.isdigit() and 1 <= len(digits) <= 4:
            if len(digits) >= 3:
                hours = digits[:-2].rjust(2, "0")
                minutes = digits[-2:]
            else:
                hours = digits.rjust(2, "0")
                minutes = "00"

            normalized = f"{sign}{hours}:{minutes}"
            datetime_string = f"{datetime_string[: match_jira_format.start()]}{normalized}"

    # Handle the case where the datetime string ends with 'Z' (Zulu time)
    if datetime_string.endswith("Z"):
        datetime_string = datetime_string[:-1] + "+00:00"

    # Handle timezone format "+0000" -> "+00:00"
    if datetime_string.endswith("+0000"):
        datetime_string = datetime_string[:-5] + "+00:00"

    datetime_object = datetime.fromisoformat(datetime_string)

    if datetime_object.tzinfo is None:
        # If no timezone info, assume it is UTC
        datetime_object = datetime_object.replace(tzinfo=timezone.utc)
    else:
        # If not in UTC, translate it
        datetime_object = datetime_object.astimezone(timezone.utc)

    # LINEAJE: runtime guardrail checks `datetime_object` as it flows from the agent to the user interface, before it leaves the application (in datetime_from_string).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `datetime_object` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:cf37a2a50115c61f787049cc197d0aa8f3b5d5774d328aee7a6bb346614fd022'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cf37a2a50115c61f787049cc197d0aa8f3b5d5774d328aee7a6bb346614fd022', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 90, 'function': 'datetime_from_string'}, 'file': 'common/data_source/utils.py', 'line': 90, 'function': 'datetime_from_string', 'agent_name': 'datetime_from_string', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        datetime_object = _gr_client.enforce(_gr_site, datetime_object, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return datetime_object


def is_valid_image_type(mime_type: str) -> bool:
    """
    Check if mime_type is a valid image type.

    Args:
        mime_type: The MIME type to check

    Returns:
        True if the MIME type is a valid image type, False otherwise
    """
    return bool(mime_type) and mime_type.startswith("image/") and mime_type not in EXCLUDED_IMAGE_TYPES


"""If you want to allow the external service to tell you when you've hit the rate limit,
use the following instead"""

R = TypeVar("R", bound=Callable[..., requests.Response])


def _handle_http_error(e: requests.HTTPError, attempt: int) -> int:
    MIN_DELAY = 2
    MAX_DELAY = 60
    STARTING_DELAY = 5
    BACKOFF = 2

    # Check if the response or headers are None to avoid potential AttributeError
    if e.response is None or e.response.headers is None:
        _lineaje_payload = "HTTPError with `None` as response or as headers"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _handle_http_error).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:aa92a82dd19ed385191d71f95fe1e9ae1c36b3920cbc32a2a8a4894c0fa1a25d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aa92a82dd19ed385191d71f95fe1e9ae1c36b3920cbc32a2a8a4894c0fa1a25d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 120, 'function': '_handle_http_error'}, 'file': 'common/data_source/utils.py', 'line': 120, 'function': '_handle_http_error', 'agent_name': '_handle_http_error', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning(_lineaje_payload)
        raise e

    # Confluence Server returns 403 when rate limited
    if e.response.status_code == 403:
        FORBIDDEN_MAX_RETRY_ATTEMPTS = 7
        FORBIDDEN_RETRY_DELAY = 10
        if attempt < FORBIDDEN_MAX_RETRY_ATTEMPTS:
            _lineaje_payload = f"403 error. This sometimes happens when we hit Confluence rate limits. Retrying in {FORBIDDEN_RETRY_DELAY} seconds..."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _handle_http_error).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9be37a63521c4655d058aaf2c2f76deddbb33625e7b30ba5c81a91cbe135a5c5'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9be37a63521c4655d058aaf2c2f76deddbb33625e7b30ba5c81a91cbe135a5c5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 128, 'function': '_handle_http_error'}, 'file': 'common/data_source/utils.py', 'line': 128, 'function': '_handle_http_error', 'agent_name': '_handle_http_error', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            # LINEAJE: runtime guardrail checks `FORBIDDEN_RETRY_DELAY` as it flows from the agent to the user interface, before it leaves the application (in _handle_http_error).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `FORBIDDEN_RETRY_DELAY` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1f23ad2303e2fde61ea7ef296e59700f4e2e885667a86880cc07597259797532'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1f23ad2303e2fde61ea7ef296e59700f4e2e885667a86880cc07597259797532', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 129, 'function': '_handle_http_error'}, 'file': 'common/data_source/utils.py', 'line': 129, 'function': '_handle_http_error', 'agent_name': '_handle_http_error', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                FORBIDDEN_RETRY_DELAY = _gr_client.enforce(_gr_site, FORBIDDEN_RETRY_DELAY, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return FORBIDDEN_RETRY_DELAY

        raise e

    if e.response.status_code != 429 and RATE_LIMIT_MESSAGE_LOWERCASE not in e.response.text.lower():
        raise e

    retry_after = None

    retry_after_header = e.response.headers.get("Retry-After")
    if retry_after_header is not None:
        try:
            retry_after = int(retry_after_header)
            if retry_after > MAX_DELAY:
                _lineaje_payload = f"Clamping retry_after from {retry_after} to {MAX_DELAY} seconds..."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _handle_http_error).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:96816082b861ee764bae6683cde6aa7258980e669dde92a7b856fe7319683792'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:96816082b861ee764bae6683cde6aa7258980e669dde92a7b856fe7319683792', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 143, 'function': '_handle_http_error'}, 'file': 'common/data_source/utils.py', 'line': 143, 'function': '_handle_http_error', 'agent_name': '_handle_http_error', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                retry_after = MAX_DELAY
            if retry_after < MIN_DELAY:
                retry_after = MIN_DELAY
        except ValueError:
            pass

    if retry_after is not None:
        _lineaje_payload = f"Rate limiting with retry header. Retrying after {retry_after} seconds..."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _handle_http_error).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1598ecd131d4c1b98e0a434fa091dc80fbe9ac759bad0d54aa2da5297016b63b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1598ecd131d4c1b98e0a434fa091dc80fbe9ac759bad0d54aa2da5297016b63b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 151, 'function': '_handle_http_error'}, 'file': 'common/data_source/utils.py', 'line': 151, 'function': '_handle_http_error', 'agent_name': '_handle_http_error', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning(_lineaje_payload)
        delay = retry_after
    else:
        _lineaje_payload = "Rate limiting without retry header. Retrying with exponential backoff..."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _handle_http_error).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:318a597d81ddf7d51ae97d96e95462cabf8b1f2ec452f03c8e7772083ac7aaf2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:318a597d81ddf7d51ae97d96e95462cabf8b1f2ec452f03c8e7772083ac7aaf2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 154, 'function': '_handle_http_error'}, 'file': 'common/data_source/utils.py', 'line': 154, 'function': '_handle_http_error', 'agent_name': '_handle_http_error', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning(_lineaje_payload)
        delay = min(STARTING_DELAY * (BACKOFF**attempt), MAX_DELAY)

    delay_until = math.ceil(time.monotonic() + delay)
    # LINEAJE: runtime guardrail checks `delay_until` as it flows from the agent to the user interface, before it leaves the application (in _handle_http_error).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `delay_until` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:2d27fe8283c26aaafd405f182f0feee94208ae29a8b4788875746efa973b8865'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2d27fe8283c26aaafd405f182f0feee94208ae29a8b4788875746efa973b8865', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 158, 'function': '_handle_http_error'}, 'file': 'common/data_source/utils.py', 'line': 158, 'function': '_handle_http_error', 'agent_name': '_handle_http_error', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        delay_until = _gr_client.enforce(_gr_site, delay_until, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return delay_until


def update_param_in_path(path: str, param: str, value: str) -> str:
    """Update a parameter in a path. Path should look something like:

    /api/rest/users?start=0&limit=10
    """
    parsed_url = urlparse(path)
    query_params = parse_qs(parsed_url.query)
    query_params[param] = [value]
    return path.split("?")[0] + "?" + "&".join(f"{k}={quote(v[0])}" for k, v in query_params.items())


def build_confluence_document_id(base_url: str, content_url: str, is_cloud: bool) -> str:
    """For confluence, the document id is the page url for a page based document
        or the attachment download url for an attachment based document

    Args:
        base_url (str): The base url of the Confluence instance
        content_url (str): The url of the page or attachment download url

    Returns:
        str: The document id
    """

    # NOTE: urljoin is tricky and will drop the last segment of the base if it doesn't
    # end with "/" because it believes that makes it a file.
    final_url = base_url.rstrip("/") + "/"
    if is_cloud and not final_url.endswith("/wiki/"):
        final_url = urljoin(final_url, "wiki") + "/"
    final_url = urljoin(final_url, content_url.lstrip("/"))
    # LINEAJE: runtime guardrail checks `final_url` as it flows from the agent to the user interface, before it leaves the application (in build_confluence_document_id).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `final_url` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:8ecfb87a52c7ade1d31297eed150509dcd1b0dffbce50fa28fb68aa8e09900d5'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8ecfb87a52c7ade1d31297eed150509dcd1b0dffbce50fa28fb68aa8e09900d5', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 190, 'function': 'build_confluence_document_id'}, 'file': 'common/data_source/utils.py', 'line': 190, 'function': 'build_confluence_document_id', 'agent_name': 'build_confluence_document_id', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        final_url = _gr_client.enforce(_gr_site, final_url, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return final_url


def get_single_param_from_url(url: str, param: str) -> str | None:
    """Get a parameter from a url"""
    parsed_url = urlparse(url)
    return parse_qs(parsed_url.query).get(param, [None])[0]


def get_start_param_from_url(url: str) -> int:
    """Get the start parameter from a url"""
    start_str = get_single_param_from_url(url, "start")
    return int(start_str) if start_str else 0


def wrap_request_to_handle_ratelimiting(request_fn: R, default_wait_time_sec: int = 30, max_waits: int = 30) -> R:
    def wrapped_request(*args: list, **kwargs: dict[str, Any]) -> requests.Response:
        for _ in range(max_waits):
            response = request_fn(*args, **kwargs)
            if response.status_code == 429:
                try:
                    wait_time = int(response.headers.get("Retry-After", default_wait_time_sec))
                except ValueError:
                    wait_time = default_wait_time_sec

                time.sleep(wait_time)
                continue

            # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the user interface, before it leaves the application (in wrapped_request).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b2124232612418131e237e9c23cdb840d83f345aec00e19c93ba11142d601cee'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b2124232612418131e237e9c23cdb840d83f345aec00e19c93ba11142d601cee', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 218, 'function': 'wrap_request_to_handle_ratelimiting.wrapped_request'}, 'file': 'common/data_source/utils.py', 'line': 218, 'function': 'wrapped_request', 'agent_name': 'wrapped_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                response = _gr_client.enforce(_gr_site, response, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return response

        raise RateLimitTriedTooManyTimesError(f"Exceeded '{max_waits}' retries")

    return cast(R, wrapped_request)


_rate_limited_get = wrap_request_to_handle_ratelimiting(requests.get)
_rate_limited_post = wrap_request_to_handle_ratelimiting(requests.post)


class _RateLimitedRequest:
    get = _rate_limited_get
    post = _rate_limited_post


rl_requests = _RateLimitedRequest

# Blob Storage Utilities


def create_s3_client(bucket_type: BlobType, credentials: dict[str, Any], european_residency: bool = False) -> S3Client:
    """Create S3 client for different blob storage types"""
    if bucket_type == BlobType.R2:
        subdomain = "eu." if european_residency else ""
        endpoint_url = f"https://{credentials['account_id']}.{subdomain}r2.cloudflarestorage.com"

        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=credentials["r2_access_key_id"],
            aws_secret_access_key=credentials["r2_secret_access_key"],
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )

    elif bucket_type == BlobType.S3:
        authentication_method = credentials.get("authentication_method", "access_key")

        region_name = credentials.get("region") or None

        if authentication_method == "access_key":
            session = boto3.Session(
                aws_access_key_id=credentials["aws_access_key_id"],
                aws_secret_access_key=credentials["aws_secret_access_key"],
                region_name=region_name,
            )
            return session.client("s3", region_name=region_name)

        elif authentication_method == "iam_role":
            role_arn = credentials["aws_role_arn"]

            def _refresh_credentials() -> dict[str, str]:
                sts_client = boto3.client("sts", region_name=credentials.get("region") or None)
                assumed_role_object = sts_client.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName=f"onyx_blob_storage_{int(datetime.now().timestamp())}",
                )
                creds = assumed_role_object["Credentials"]
                return {
                    "access_key": creds["AccessKeyId"],
                    "secret_key": creds["SecretAccessKey"],
                    "token": creds["SessionToken"],
                    "expiry_time": creds["Expiration"].isoformat(),
                }

            refreshable = RefreshableCredentials.create_from_metadata(
                metadata=_refresh_credentials(),
                refresh_using=_refresh_credentials,
                method="sts-assume-role",
            )
            botocore_session = get_session()
            botocore_session._credentials = refreshable
            session = boto3.Session(botocore_session=botocore_session, region_name=region_name)
            return session.client("s3", region_name=region_name)

        elif authentication_method == "assume_role":
            return boto3.client("s3", region_name=region_name)

        else:
            raise ValueError("Invalid authentication method for S3.")

    elif bucket_type == BlobType.GOOGLE_CLOUD_STORAGE:
        return boto3.client(
            "s3",
            endpoint_url="https://storage.googleapis.com",
            aws_access_key_id=credentials["access_key_id"],
            aws_secret_access_key=credentials["secret_access_key"],
            region_name="auto",
        )

    elif bucket_type == BlobType.OCI_STORAGE:
        return boto3.client(
            "s3",
            endpoint_url=f"https://{credentials['namespace']}.compat.objectstorage.{credentials['region']}.oraclecloud.com",
            aws_access_key_id=credentials["access_key_id"],
            aws_secret_access_key=credentials["secret_access_key"],
            region_name=credentials["region"],
        )
    elif bucket_type == BlobType.S3_COMPATIBLE:
        addressing_style = credentials.get("addressing_style", "virtual")

        return boto3.client(
            "s3",
            endpoint_url=credentials["endpoint_url"],
            aws_access_key_id=credentials["aws_access_key_id"],
            aws_secret_access_key=credentials["aws_secret_access_key"],
            config=Config(s3={'addressing_style': addressing_style}),
        )

    else:
        raise ValueError(f"Unsupported bucket type: {bucket_type}")


def detect_bucket_region(s3_client: S3Client, bucket_name: str) -> str | None:
    """Detect bucket region"""
    try:
        response = s3_client.head_bucket(Bucket=bucket_name)
        bucket_region = response.get("BucketRegion") or response.get("ResponseMetadata", {}).get("HTTPHeaders", {}).get("x-amz-bucket-region")

        if bucket_region:
            _lineaje_payload = f"Detected bucket region: {bucket_region}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in detect_bucket_region).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:bb0c99f6df5a94a4b94e8c7e1dc4dd2eb1e7951c28d0208960d86e3e7c919ce6'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bb0c99f6df5a94a4b94e8c7e1dc4dd2eb1e7951c28d0208960d86e3e7c919ce6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 339, 'function': 'detect_bucket_region'}, 'file': 'common/data_source/utils.py', 'line': 339, 'function': 'detect_bucket_region', 'agent_name': 'detect_bucket_region', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.debug(_lineaje_payload)
        else:
            _lineaje_payload = "Bucket region not found in head_bucket response"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in detect_bucket_region).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:21e26c9b1888ff81c4ab5ac99e90e35e5821a9bacd410638877567955df7c8c6'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:21e26c9b1888ff81c4ab5ac99e90e35e5821a9bacd410638877567955df7c8c6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 341, 'function': 'detect_bucket_region'}, 'file': 'common/data_source/utils.py', 'line': 341, 'function': 'detect_bucket_region', 'agent_name': 'detect_bucket_region', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)

        # LINEAJE: runtime guardrail checks `bucket_region` as it flows from the agent to the user interface, before it leaves the application (in detect_bucket_region).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `bucket_region` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c0c63f04d60f0279b1118063d581b28f127a3b68cc150abd49c62f737d7c5c43'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c0c63f04d60f0279b1118063d581b28f127a3b68cc150abd49c62f737d7c5c43', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 343, 'function': 'detect_bucket_region'}, 'file': 'common/data_source/utils.py', 'line': 343, 'function': 'detect_bucket_region', 'agent_name': 'detect_bucket_region', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            bucket_region = _gr_client.enforce(_gr_site, bucket_region, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return bucket_region
    except Exception as e:
        _lineaje_payload = f"Failed to detect bucket region via head_bucket: {e}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in detect_bucket_region).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e4bf7945b2c49f249b8336da11f88b224ae30026a67db1e906526774bc043cd3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e4bf7945b2c49f249b8336da11f88b224ae30026a67db1e906526774bc043cd3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 345, 'function': 'detect_bucket_region'}, 'file': 'common/data_source/utils.py', 'line': 345, 'function': 'detect_bucket_region', 'agent_name': 'detect_bucket_region', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning(_lineaje_payload)
        return None


def download_object(s3_client: S3Client, bucket_name: str, key: str, size_threshold: int | None = None) -> bytes | None:
    """Download object from blob storage"""
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    body = response["Body"]

    try:
        if size_threshold is None:
            return body.read()

        return read_stream_with_limit(body, key, size_threshold)
    finally:
        body.close()


def read_stream_with_limit(body: Any, key: str, size_threshold: int) -> bytes | None:
    """Read stream with size limit"""
    bytes_read = 0
    chunks: list[bytes] = []
    chunk_size = min(DOWNLOAD_CHUNK_SIZE, size_threshold + SIZE_THRESHOLD_BUFFER)

    for chunk in body.iter_chunks(chunk_size=chunk_size):
        if not chunk:
            continue
        chunks.append(chunk)
        bytes_read += len(chunk)

        if bytes_read > size_threshold + SIZE_THRESHOLD_BUFFER:
            _lineaje_payload = f"{key} exceeds size threshold of {size_threshold}. Skipping."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in read_stream_with_limit).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:8baad060fe32345e16f8f54b8d1397373f892fb2ca13a5f9cbc7ac3690ccaffe'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8baad060fe32345e16f8f54b8d1397373f892fb2ca13a5f9cbc7ac3690ccaffe', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 376, 'function': 'read_stream_with_limit'}, 'file': 'common/data_source/utils.py', 'line': 376, 'function': 'read_stream_with_limit', 'agent_name': 'read_stream_with_limit', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            return None

    return b"".join(chunks)


def _extract_onyx_metadata(line: str) -> dict | None:
    """
    Example: first line has:
        <!-- ONYX_METADATA={"title": "..."} -->
      or
        #ONYX_METADATA={"title":"..."}
    """
    html_comment_pattern = r"<!--\s*ONYX_METADATA=\{(.*?)\}\s*-->"
    hashtag_pattern = r"#ONYX_METADATA=\{(.*?)\}"

    html_comment_match = re.search(html_comment_pattern, line)
    hashtag_match = re.search(hashtag_pattern, line)

    if html_comment_match:
        json_str = html_comment_match.group(1)
    elif hashtag_match:
        json_str = hashtag_match.group(1)
    else:
        return None

    try:
        return json.loads("{" + json_str + "}")
    except json.JSONDecodeError:
        return None


def read_text_file(
    file: IO,
    encoding: str = "utf-8",
    errors: str = "replace",
    ignore_onyx_metadata: bool = True,
) -> tuple[str, dict]:
    """
    For plain text files. Optionally extracts Onyx metadata from the first line.
    """
    metadata = {}
    file_content_raw = ""
    for ind, line in enumerate(file):
        # decode
        try:
            line = line.decode(encoding) if isinstance(line, bytes) else line
        except UnicodeDecodeError:
            line = line.decode(encoding, errors=errors) if isinstance(line, bytes) else line

        # optionally parse metadata in the first line
        if ind == 0 and not ignore_onyx_metadata:
            potential_meta = _extract_onyx_metadata(line)
            if potential_meta is not None:
                metadata = potential_meta
                continue

        file_content_raw += line

    return file_content_raw, metadata


def get_blob_link(bucket_type: BlobType, s3_client: S3Client, bucket_name: str, key: str, bucket_region: str | None = None) -> str:
    """Get object link for different blob storage types"""
    encoded_key = quote(key, safe="/")

    if bucket_type == BlobType.R2:
        account_id = s3_client.meta.endpoint_url.split("//")[1].split(".")[0]
        subdomain = "eu/" if "eu." in s3_client.meta.endpoint_url else "default/"

        return f"https://dash.cloudflare.com/{account_id}/r2/{subdomain}buckets/{bucket_name}/objects/{encoded_key}/details"

    elif bucket_type == BlobType.S3:
        region = bucket_region or s3_client.meta.region_name
        return f"https://s3.console.aws.amazon.com/s3/object/{bucket_name}?region={region}&prefix={encoded_key}"

    elif bucket_type == BlobType.GOOGLE_CLOUD_STORAGE:
        return f"https://console.cloud.google.com/storage/browser/_details/{bucket_name}/{encoded_key}"

    elif bucket_type == BlobType.OCI_STORAGE:
        namespace = s3_client.meta.endpoint_url.split("//")[1].split(".")[0]
        region = s3_client.meta.region_name
        return f"https://objectstorage.{region}.oraclecloud.com/n/{namespace}/b/{bucket_name}/o/{encoded_key}"

    else:
        raise ValueError(f"Unsupported bucket type: {bucket_type}")


def extract_size_bytes(obj: Mapping[str, Any]) -> int | None:
    """Extract size bytes from object metadata"""
    candidate_keys = (
        "Size",
        "size",
        "ContentLength",
        "content_length",
        "Content-Length",
        "contentLength",
        "bytes",
        "Bytes",
    )

    def _normalize(value: Any) -> int | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, Integral):
            return int(value)
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric >= 0 and numeric.is_integer():
            return int(numeric)
        return None

    for key in candidate_keys:
        if key in obj:
            normalized = _normalize(obj.get(key))
            if normalized is not None:
                # LINEAJE: runtime guardrail checks `normalized` as it flows from the agent to the user interface, before it leaves the application (in _RateLimitedRequest._normalize).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `normalized` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:6cf81ff743f716bbbc676609c4d8477400377d9c07dfaf61ced838f2d2de3637'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6cf81ff743f716bbbc676609c4d8477400377d9c07dfaf61ced838f2d2de3637', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 494, 'function': 'extract_size_bytes'}, 'file': 'common/data_source/utils.py', 'line': 494, 'function': '_normalize', 'agent_name': '_RateLimitedRequest', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    normalized = _gr_client.enforce(_gr_site, normalized, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return normalized

    for key, value in obj.items():
        if not isinstance(key, str):
            continue
        lowered_key = key.lower()
        if "size" in lowered_key or "length" in lowered_key:
            normalized = _normalize(value)
            if normalized is not None:
                # LINEAJE: runtime guardrail checks `normalized` as it flows from the agent to the user interface, before it leaves the application (in _RateLimitedRequest._normalize).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `normalized` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:01ba648a8c2cec65f9c961a583dabc26fb5af72a3a420da9e63668117f6d634f'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:01ba648a8c2cec65f9c961a583dabc26fb5af72a3a420da9e63668117f6d634f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 503, 'function': 'extract_size_bytes'}, 'file': 'common/data_source/utils.py', 'line': 503, 'function': '_normalize', 'agent_name': '_RateLimitedRequest', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    normalized = _gr_client.enforce(_gr_site, normalized, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return normalized

    return None


def get_file_ext(file_name: str) -> str:
    """Get file extension"""
    return os.path.splitext(file_name)[1].lower()


def is_accepted_file_ext(file_ext: str, extension_type: OnyxExtensionType) -> bool:
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
    text_extensions = {".txt", ".md", ".mdx", ".conf", ".log", ".json", ".csv", ".tsv", ".xml", ".yml", ".yaml", ".sql"}
    document_extensions = {".pdf", ".docx", ".pptx", ".xlsx", ".eml", ".epub", ".html"}

    if extension_type & OnyxExtensionType.Multimedia and file_ext in image_extensions:
        return True

    if extension_type & OnyxExtensionType.Plain and file_ext in text_extensions:
        return True

    if extension_type & OnyxExtensionType.Document and file_ext in document_extensions:
        return True

    return False


def detect_encoding(file: IO[bytes]) -> str:
    raw_data = file.read(50000)
    file.seek(0)
    encoding = chardet.detect(raw_data)["encoding"] or "utf-8"
    # LINEAJE: runtime guardrail checks `encoding` as it flows from the agent to the user interface, before it leaves the application (in detect_encoding).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `encoding` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:5976ccdf244965190e7a65c74908045c75b439d548ced6da72937535fdd4f046'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5976ccdf244965190e7a65c74908045c75b439d548ced6da72937535fdd4f046', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 534, 'function': 'detect_encoding'}, 'file': 'common/data_source/utils.py', 'line': 534, 'function': 'detect_encoding', 'agent_name': 'detect_encoding', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        encoding = _gr_client.enforce(_gr_site, encoding, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return encoding


def get_markitdown_converter():
    global _MARKITDOWN_CONVERTER
    from markitdown import MarkItDown

    if _MARKITDOWN_CONVERTER is None:
        _MARKITDOWN_CONVERTER = MarkItDown(enable_plugins=False)
    return _MARKITDOWN_CONVERTER


def to_bytesio(stream: IO[bytes]) -> BytesIO:
    if isinstance(stream, BytesIO):
        # LINEAJE: runtime guardrail checks `stream` as it flows from the agent to the user interface, before it leaves the application (in to_bytesio).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `stream` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:943c9961341eef7a794a4b58286e78725bd376e3f7e45d9152857957eecadd17'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:943c9961341eef7a794a4b58286e78725bd376e3f7e45d9152857957eecadd17', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 548, 'function': 'to_bytesio'}, 'file': 'common/data_source/utils.py', 'line': 548, 'function': 'to_bytesio', 'agent_name': 'to_bytesio', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            stream = _gr_client.enforce(_gr_site, stream, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return stream
    data = stream.read()  # consumes the stream!
    return BytesIO(data)


# Slack Utilities


@lru_cache()
def get_base_url(token: str) -> str:
    """Get and cache Slack workspace base URL"""
    client = WebClient(token=token)
    return client.auth_test()["url"]


def get_message_link(event: dict, client: WebClient, channel_id: str) -> str:
    """Get message link"""
    message_ts = event["ts"]
    message_ts_without_dot = message_ts.replace(".", "")
    thread_ts = event.get("thread_ts")
    base_url = get_base_url(client.token)

    link = f"{base_url.rstrip('/')}/archives/{channel_id}/p{message_ts_without_dot}" + (f"?thread_ts={thread_ts}" if thread_ts else "")
    # LINEAJE: runtime guardrail checks `link` as it flows from the agent to the user interface, before it leaves the application (in get_message_link).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `link` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:de4aaf536f5ae704f0b15df7018ada151b0ba7f24f0c381797870f5f10197a95'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:de4aaf536f5ae704f0b15df7018ada151b0ba7f24f0c381797870f5f10197a95', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 571, 'function': 'get_message_link'}, 'file': 'common/data_source/utils.py', 'line': 571, 'function': 'get_message_link', 'agent_name': 'get_message_link', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        link = _gr_client.enforce(_gr_site, link, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return link


def make_slack_api_call(call: Callable[..., SlackResponse], **kwargs: Any) -> SlackResponse:
    """Make Slack API call"""
    return call(**kwargs)


def make_paginated_slack_api_call(call: Callable[..., SlackResponse], **kwargs: Any) -> Generator[dict[str, Any], None, None]:
    """Make paginated Slack API call"""
    return _make_slack_api_call_paginated(call)(**kwargs)


def _make_slack_api_call_paginated(
    call: Callable[..., SlackResponse],
) -> Callable[..., Generator[dict[str, Any], None, None]]:
    """Wrap Slack API call to automatically handle pagination"""

    @wraps(call)
    def paginated_call(**kwargs: Any) -> Generator[dict[str, Any], None, None]:
        cursor: str | None = None
        has_more = True
        while has_more:
            response = call(cursor=cursor, limit=_SLACK_LIMIT, **kwargs)
            yield response.validate()
            cursor = response.get("response_metadata", {}).get("next_cursor", "")
            has_more = bool(cursor)

    # LINEAJE: runtime guardrail checks `paginated_call` as it flows from the agent to the user interface, before it leaves the application (in _make_slack_api_call_paginated).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `paginated_call` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:bfa7276783f51f2a4a97156949c571f532b17ce525496328e2b8dca9be4a9d71'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bfa7276783f51f2a4a97156949c571f532b17ce525496328e2b8dca9be4a9d71', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 599, 'function': '_make_slack_api_call_paginated'}, 'file': 'common/data_source/utils.py', 'line': 599, 'function': '_make_slack_api_call_paginated', 'agent_name': '_make_slack_api_call_paginated', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        paginated_call = _gr_client.enforce(_gr_site, paginated_call, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return paginated_call


def is_atlassian_date_error(e: Exception) -> bool:
    return "field 'updated' is invalid" in str(e)


def expert_info_from_slack_id(
    user_id: str | None,
    client: WebClient,
    user_cache: dict[str, BasicExpertInfo | None],
) -> BasicExpertInfo | None:
    """Get expert information from Slack user ID"""
    if not user_id:
        return None

    if user_id in user_cache:
        return user_cache[user_id]

    response = client.users_info(user=user_id)

    if not response["ok"]:
        user_cache[user_id] = None
        return None

    user: dict = response.data.get("user", {})
    profile = user.get("profile", {})

    expert = BasicExpertInfo(
        display_name=user.get("real_name") or profile.get("display_name"),
        first_name=profile.get("first_name"),
        last_name=profile.get("last_name"),
        email=profile.get("email"),
    )

    user_cache[user_id] = expert

    # LINEAJE: runtime guardrail checks `expert` as it flows from the agent to the user interface, before it leaves the application (in expert_info_from_slack_id).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `expert` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e216a894a8ed04c931585074b77e7b56f698b90943bfba36b31bcadbab213f0a'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e216a894a8ed04c931585074b77e7b56f698b90943bfba36b31bcadbab213f0a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 636, 'function': 'expert_info_from_slack_id'}, 'file': 'common/data_source/utils.py', 'line': 636, 'function': 'expert_info_from_slack_id', 'agent_name': 'expert_info_from_slack_id', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        expert = _gr_client.enforce(_gr_site, expert, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return expert


class SlackTextCleaner:
    """Slack text cleaning utility class"""

    def __init__(self, client: WebClient) -> None:
        self._client = client
        self._id_to_name_map: dict[str, str] = {}

    def _get_slack_name(self, user_id: str) -> str:
        """Get Slack username"""
        if user_id not in self._id_to_name_map:
            try:
                response = self._client.users_info(user=user_id)
                self._id_to_name_map[user_id] = response["user"]["profile"]["display_name"] or response["user"]["profile"]["real_name"]
            except SlackApiError as e:
                _lineaje_payload = f"Error fetching data for user {user_id}: {e.response['error']}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in SlackTextCleaner._get_slack_name).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a197a2880fcea858b596a154a421d959ceb051f787a65cbbeb7da27291fd99ff'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a197a2880fcea858b596a154a421d959ceb051f787a65cbbeb7da27291fd99ff', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 653, 'function': 'SlackTextCleaner._get_slack_name'}, 'file': 'common/data_source/utils.py', 'line': 653, 'function': '_get_slack_name', 'agent_name': 'SlackTextCleaner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(_lineaje_payload)
                raise

        return self._id_to_name_map[user_id]

    def _replace_user_ids_with_names(self, message: str) -> str:
        """Replace user IDs with usernames"""
        user_ids = re.findall("<@(.*?)>", message)

        for user_id in user_ids:
            try:
                if user_id in self._id_to_name_map:
                    user_name = self._id_to_name_map[user_id]
                else:
                    user_name = self._get_slack_name(user_id)

                message = message.replace(f"<@{user_id}>", f"@{user_name}")
            except Exception:
                _lineaje_payload = f"Unable to replace user ID with username for user_id '{user_id}'"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in SlackTextCleaner._replace_user_ids_with_names).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:2169468a9a9466a23039df50942191b4c96669c2e3a42c9f9c53d0d5de797c61'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2169468a9a9466a23039df50942191b4c96669c2e3a42c9f9c53d0d5de797c61', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 671, 'function': 'SlackTextCleaner._replace_user_ids_with_names'}, 'file': 'common/data_source/utils.py', 'line': 671, 'function': '_replace_user_ids_with_names', 'agent_name': 'SlackTextCleaner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(_lineaje_payload)

        # LINEAJE: runtime guardrail checks `message` as it flows from the agent to the user interface, before it leaves the application (in SlackTextCleaner._replace_user_ids_with_names).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `message` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:aab832dbd5432600cfd810c7a8e7672a3d1516db6f43a37450d5a487ddf6972e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aab832dbd5432600cfd810c7a8e7672a3d1516db6f43a37450d5a487ddf6972e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 673, 'function': 'SlackTextCleaner._replace_user_ids_with_names'}, 'file': 'common/data_source/utils.py', 'line': 673, 'function': '_replace_user_ids_with_names', 'agent_name': 'SlackTextCleaner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            message = _gr_client.enforce(_gr_site, message, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return message

    def index_clean(self, message: str) -> str:
        """Index cleaning"""
        message = self._replace_user_ids_with_names(message)
        message = self.replace_tags_basic(message)
        message = self.replace_channels_basic(message)
        message = self.replace_special_mentions(message)
        message = self.replace_special_catchall(message)
        # LINEAJE: runtime guardrail checks `message` as it flows from the agent to the user interface, before it leaves the application (in SlackTextCleaner.index_clean).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `message` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d73ba6730e0c2e83a2a3dbfa1fc78ef570f83fc1ee5b28a3cf5ec39fba0ad130'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d73ba6730e0c2e83a2a3dbfa1fc78ef570f83fc1ee5b28a3cf5ec39fba0ad130', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 682, 'function': 'SlackTextCleaner.index_clean'}, 'file': 'common/data_source/utils.py', 'line': 682, 'function': 'index_clean', 'agent_name': 'SlackTextCleaner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            message = _gr_client.enforce(_gr_site, message, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return message

    @staticmethod
    def replace_tags_basic(message: str) -> str:
        """Basic tag replacement"""
        user_ids = re.findall("<@(.*?)>", message)
        for user_id in user_ids:
            message = message.replace(f"<@{user_id}>", f"@{user_id}")
        # LINEAJE: runtime guardrail checks `message` as it flows from the agent to the user interface, before it leaves the application (in SlackTextCleaner.replace_tags_basic).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `message` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:84e2f44c6ece24a7f47dc7e06e47408aff2306baa681e7ed99c787802e5736a9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:84e2f44c6ece24a7f47dc7e06e47408aff2306baa681e7ed99c787802e5736a9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 690, 'function': 'SlackTextCleaner.replace_tags_basic'}, 'file': 'common/data_source/utils.py', 'line': 690, 'function': 'replace_tags_basic', 'agent_name': 'SlackTextCleaner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            message = _gr_client.enforce(_gr_site, message, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return message

    @staticmethod
    def replace_channels_basic(message: str) -> str:
        """Basic channel replacement"""
        channel_matches = re.findall(r"<#(.*?)\|(.*?)>", message)
        for channel_id, channel_name in channel_matches:
            message = message.replace(f"<#{channel_id}|{channel_name}>", f"#{channel_name}")
        # LINEAJE: runtime guardrail checks `message` as it flows from the agent to the user interface, before it leaves the application (in SlackTextCleaner.replace_channels_basic).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `message` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f7bc761930a285fed1956b16d740308e50b65a30dd07c0384ed56f7f9e668aa7'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f7bc761930a285fed1956b16d740308e50b65a30dd07c0384ed56f7f9e668aa7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 698, 'function': 'SlackTextCleaner.replace_channels_basic'}, 'file': 'common/data_source/utils.py', 'line': 698, 'function': 'replace_channels_basic', 'agent_name': 'SlackTextCleaner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            message = _gr_client.enforce(_gr_site, message, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return message

    @staticmethod
    def replace_special_mentions(message: str) -> str:
        """Special mention replacement"""
        message = message.replace("<!channel>", "@channel")
        message = message.replace("<!here>", "@here")
        message = message.replace("<!everyone>", "@everyone")
        # LINEAJE: runtime guardrail checks `message` as it flows from the agent to the user interface, before it leaves the application (in SlackTextCleaner.replace_special_mentions).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `message` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:2cb607fcbe6e418de529680f9dbc0b1de1574c60064c682034a1248ececfecce'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2cb607fcbe6e418de529680f9dbc0b1de1574c60064c682034a1248ececfecce', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 706, 'function': 'SlackTextCleaner.replace_special_mentions'}, 'file': 'common/data_source/utils.py', 'line': 706, 'function': 'replace_special_mentions', 'agent_name': 'SlackTextCleaner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            message = _gr_client.enforce(_gr_site, message, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return message

    @staticmethod
    def replace_special_catchall(message: str) -> str:
        """Special catchall replacement"""
        pattern = r"<!([^|]+)\|([^>]+)>"
        return re.sub(pattern, r"\2", message)

    @staticmethod
    def add_zero_width_whitespace_after_tag(message: str) -> str:
        """Add zero-width whitespace after tag"""
        return message.replace("@", "@\u200b")


# Gmail Utilities


def is_mail_service_disabled_error(error: HttpError) -> bool:
    """Detect if the Gmail API is telling us the mailbox is not provisioned."""
    if error.resp.status != 400:
        return False

    error_message = str(error)
    return "Mail service not enabled" in error_message or "failedPrecondition" in error_message


def build_time_range_query(
    time_range_start: SecondsSinceUnixEpoch | None = None,
    time_range_end: SecondsSinceUnixEpoch | None = None,
) -> str | None:
    """Build time range query for Gmail API"""
    query = ""
    if time_range_start is not None and time_range_start != 0:
        query += f"after:{int(time_range_start) + 1}"
    if time_range_end is not None and time_range_end != 0:
        query += f" before:{int(time_range_end)}"
    query = query.strip()

    if len(query) == 0:
        return None

    # LINEAJE: runtime guardrail checks `query` as it flows from the agent to the user interface, before it leaves the application (in build_time_range_query).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `query` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:fdf5207afad4426f686517a5cdb79c290499d1f45981a2ba0ab50157ae75e005'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fdf5207afad4426f686517a5cdb79c290499d1f45981a2ba0ab50157ae75e005', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 747, 'function': 'build_time_range_query'}, 'file': 'common/data_source/utils.py', 'line': 747, 'function': 'build_time_range_query', 'agent_name': 'build_time_range_query', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        query = _gr_client.enforce(_gr_site, query, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return query


def clean_email_and_extract_name(email: str) -> tuple[str, str | None]:
    """Extract email address and display name from email string."""
    email = email.strip()
    if "<" in email and ">" in email:
        # Handle format: "Display Name <email@domain.com>"
        display_name = email[: email.find("<")].strip()
        email_address = email[email.find("<") + 1 : email.find(">")].strip()
        return email_address, display_name if display_name else None
    else:
        # Handle plain email address
        return email.strip(), None


def get_message_body(payload: dict[str, Any]) -> str:
    """Extract message body text from Gmail message payload."""
    parts = payload.get("parts", [])
    message_body = ""
    for part in parts:
        mime_type = part.get("mimeType")
        body = part.get("body")
        if mime_type == "text/plain" and body:
            data = body.get("data", "")
            text = base64.urlsafe_b64decode(data).decode()
            message_body += text
    # LINEAJE: runtime guardrail checks `message_body` as it flows from the agent to the user interface, before it leaves the application (in get_message_body).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `message_body` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:814792a380bb73a160f3851dbbd8d2fdcab638fac6ca5b988628b414622fb096'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:814792a380bb73a160f3851dbbd8d2fdcab638fac6ca5b988628b414622fb096', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 774, 'function': 'get_message_body'}, 'file': 'common/data_source/utils.py', 'line': 774, 'function': 'get_message_body', 'agent_name': 'get_message_body', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        message_body = _gr_client.enforce(_gr_site, message_body, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return message_body


def time_str_to_utc(time_str: str):
    """Convert time string to UTC datetime."""
    from datetime import datetime

    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))


def gmail_time_str_to_utc(time_str: str):
    """Convert Gmail RFC 2822 time string to UTC."""
    from email.utils import parsedate_to_datetime
    from datetime import timezone

    dt = parsedate_to_datetime(time_str)
    return dt.astimezone(timezone.utc)


# Notion Utilities
T = TypeVar("T")


def batch_generator(
    items: Iterable[T],
    batch_size: int,
    pre_batch_yield: Callable[[list[T]], None] | None = None,
) -> Generator[list[T], None, None]:
    iterable = iter(items)
    while True:
        batch = list(islice(iterable, batch_size))
        if not batch:
            return

        if pre_batch_yield:
            pre_batch_yield(batch)
        yield batch


@retry(tries=3, delay=1, backoff=2)
def fetch_notion_data(url: str, headers: dict[str, str], method: str = "GET", json_data: Optional[dict] = None) -> dict[str, Any]:
    """Fetch data from Notion API with retry logic."""
    try:
        if method == "GET":
            response = rl_requests.get(url, headers=headers, timeout=_NOTION_CALL_TIMEOUT)
        elif method == "POST":
            response = rl_requests.post(url, headers=headers, json=json_data, timeout=_NOTION_CALL_TIMEOUT)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        _lineaje_payload = f"Error fetching data from Notion API: {e}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in fetch_notion_data).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:fa110234a96bcd05a4011ce9f50e332f92eb9e052a16d456da6057e3f6947a0c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fa110234a96bcd05a4011ce9f50e332f92eb9e052a16d456da6057e3f6947a0c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 827, 'function': 'fetch_notion_data'}, 'file': 'common/data_source/utils.py', 'line': 827, 'function': 'fetch_notion_data', 'agent_name': 'fetch_notion_data', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(_lineaje_payload)
        raise


def properties_to_str(properties: dict[str, Any]) -> str:
    """Convert Notion properties to a string representation."""

    def _recurse_list_properties(inner_list: list[Any]) -> str | None:
        list_properties: list[str | None] = []
        for item in inner_list:
            if item and isinstance(item, dict):
                list_properties.append(_recurse_properties(item))
            elif item and isinstance(item, list):
                list_properties.append(_recurse_list_properties(item))
            else:
                list_properties.append(str(item))
        return ", ".join([list_property for list_property in list_properties if list_property]) or None

    def _recurse_properties(inner_dict: dict[str, Any]) -> str | None:
        sub_inner_dict: dict[str, Any] | list[Any] | str = inner_dict
        while isinstance(sub_inner_dict, dict) and "type" in sub_inner_dict:
            type_name = sub_inner_dict["type"]
            sub_inner_dict = sub_inner_dict[type_name]

            if not sub_inner_dict:
                return None

        if isinstance(sub_inner_dict, list):
            return _recurse_list_properties(sub_inner_dict)
        elif isinstance(sub_inner_dict, str):
            # LINEAJE: runtime guardrail checks `sub_inner_dict` as it flows from the agent to the user interface, before it leaves the application (in SlackTextCleaner._recurse_properties).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `sub_inner_dict` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1c284251f9ee30ea19dd6155af8f5a1ca7358fc02f21e1604b5924f532ecce23'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1c284251f9ee30ea19dd6155af8f5a1ca7358fc02f21e1604b5924f532ecce23', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 857, 'function': 'properties_to_str._recurse_properties'}, 'file': 'common/data_source/utils.py', 'line': 857, 'function': '_recurse_properties', 'agent_name': 'SlackTextCleaner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                sub_inner_dict = _gr_client.enforce(_gr_site, sub_inner_dict, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return sub_inner_dict
        elif isinstance(sub_inner_dict, dict):
            if "name" in sub_inner_dict:
                return sub_inner_dict["name"]
            if "content" in sub_inner_dict:
                return sub_inner_dict["content"]
            start = sub_inner_dict.get("start")
            end = sub_inner_dict.get("end")
            if start is not None:
                if end is not None:
                    return f"{start} - {end}"
                # LINEAJE: runtime guardrail checks `start` as it flows from the agent to the user interface, before it leaves the application (in SlackTextCleaner._recurse_properties).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `start` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:0d3329bceab7cec609a08f6a991b0ca1e99ca447733abbf2b0e718c4afb3d6ca'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0d3329bceab7cec609a08f6a991b0ca1e99ca447733abbf2b0e718c4afb3d6ca', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 868, 'function': 'properties_to_str._recurse_properties'}, 'file': 'common/data_source/utils.py', 'line': 868, 'function': '_recurse_properties', 'agent_name': 'SlackTextCleaner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    start = _gr_client.enforce(_gr_site, start, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return start
            elif end is not None:
                return f"Until {end}"

            if "id" in sub_inner_dict:
                _lineaje_payload = "Skipping Notion object id field property"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in SlackTextCleaner._recurse_properties).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a15eeb37d4eb3a92f540d327c3e0fa88dda009eacbbb0c39a3174837934d4519'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a15eeb37d4eb3a92f540d327c3e0fa88dda009eacbbb0c39a3174837934d4519', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 873, 'function': 'properties_to_str._recurse_properties'}, 'file': 'common/data_source/utils.py', 'line': 873, 'function': '_recurse_properties', 'agent_name': 'SlackTextCleaner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.debug(_lineaje_payload)
                return None

        _lineaje_payload = f"Unreadable property from innermost prop: {sub_inner_dict}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in SlackTextCleaner._recurse_properties).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:69b2c7b8a0432f6b3ba3e151aa0a4eacebc7a69b0fe6247d161eb5dcc7177379'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:69b2c7b8a0432f6b3ba3e151aa0a4eacebc7a69b0fe6247d161eb5dcc7177379', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 876, 'function': 'properties_to_str._recurse_properties'}, 'file': 'common/data_source/utils.py', 'line': 876, 'function': '_recurse_properties', 'agent_name': 'SlackTextCleaner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)
        return None

    result = ""
    for prop_name, prop in properties.items():
        if not prop or not isinstance(prop, dict):
            continue

        try:
            inner_value = _recurse_properties(prop)
        except Exception as e:
            _lineaje_payload = f"Error recursing properties for {prop_name}: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in SlackTextCleaner._recurse_properties).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3fa6c880814418b0b3bdd0c964ee27c8c8bd56b3d8c15324c09e5e30802c1033'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3fa6c880814418b0b3bdd0c964ee27c8c8bd56b3d8c15324c09e5e30802c1033', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 887, 'function': 'properties_to_str'}, 'file': 'common/data_source/utils.py', 'line': 887, 'function': '_recurse_properties', 'agent_name': 'SlackTextCleaner', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            continue

        if inner_value:
            result += f"{prop_name}: {inner_value}\t"

    # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in properties_to_str).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:4a3b499214e7cb9a14d49238e95c260bd2adb0eef33afee442e708d73a6259ad'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4a3b499214e7cb9a14d49238e95c260bd2adb0eef33afee442e708d73a6259ad', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 893, 'function': 'properties_to_str'}, 'file': 'common/data_source/utils.py', 'line': 893, 'function': 'properties_to_str', 'agent_name': 'properties_to_str', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return result


def filter_pages_by_time(pages: list[dict[str, Any]], start: float, end: float, filter_field: str = "last_edited_time") -> list[dict[str, Any]]:
    """Filter pages by time range."""
    from datetime import datetime

    filtered_pages: list[dict[str, Any]] = []
    for page in pages:
        timestamp = page[filter_field].replace(".000Z", "+00:00")
        compare_time = datetime.fromisoformat(timestamp).timestamp()
        if compare_time > start and compare_time <= end:
            filtered_pages.append(page)
    # LINEAJE: runtime guardrail checks `filtered_pages` as it flows from a tool to the user interface, before it leaves the application (in filter_pages_by_time).
    #   Detected: this statement moves data from a tool to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012, AI_DAT_SEC_027; sensitive values in `filtered_pages` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:490924a9b7e8e2c88ebb9e18530ac91aa2218bdff111627ab16e09d7881d2610'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:490924a9b7e8e2c88ebb9e18530ac91aa2218bdff111627ab16e09d7881d2610', phase='data_egress', boundary={'source': 'tool_result', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='tool', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 906, 'function': 'filter_pages_by_time'}, 'file': 'common/data_source/utils.py', 'line': 906, 'function': 'filter_pages_by_time', 'agent_name': 'filter_pages_by_time', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        filtered_pages = _gr_client.enforce(_gr_site, filtered_pages, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return filtered_pages


def _load_all_docs(
    connector: CheckpointedConnector[CT],
    load: LoadFunction,
) -> list[Document]:
    num_iterations = 0

    checkpoint = cast(CT, connector.build_dummy_checkpoint())
    documents: list[Document] = []
    while checkpoint.has_more:
        doc_batch_generator = CheckpointOutputWrapper[CT]()(load(checkpoint))
        for document, failure, next_checkpoint in doc_batch_generator:
            if failure is not None:
                raise RuntimeError(f"Failed to load documents: {failure}")
            if document is not None and isinstance(document, Document):
                documents.append(document)
            if next_checkpoint is not None:
                checkpoint = next_checkpoint

        num_iterations += 1
        if num_iterations > _ITERATION_LIMIT:
            raise RuntimeError("Too many iterations. Infinite loop?")

    # LINEAJE: runtime guardrail checks `documents` as it flows from the agent to the user interface, before it leaves the application (in _load_all_docs).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `documents` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:cd41eb5ba9ae8eb1b230473f832840c32e6209f30a48d26e935d9ef174783745'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cd41eb5ba9ae8eb1b230473f832840c32e6209f30a48d26e935d9ef174783745', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 931, 'function': '_load_all_docs'}, 'file': 'common/data_source/utils.py', 'line': 931, 'function': '_load_all_docs', 'agent_name': '_load_all_docs', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        documents = _gr_client.enforce(_gr_site, documents, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return documents


def load_all_docs_from_checkpoint_connector(
    connector: CheckpointedConnector[CT],
    start: SecondsSinceUnixEpoch,
    end: SecondsSinceUnixEpoch,
) -> list[Document]:
    return _load_all_docs(
        connector=connector,
        load=lambda checkpoint: connector.load_from_checkpoint(start=start, end=end, checkpoint=checkpoint),
    )


_ATLASSIAN_CLOUD_DOMAINS = (".atlassian.net", ".jira.com", ".jira-dev.com")


def is_atlassian_cloud_url(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    host = host.lower()
    return any(host.endswith(domain) for domain in _ATLASSIAN_CLOUD_DOMAINS)


def get_cloudId(base_url: str) -> str:
    tenant_info_url = urljoin(base_url, "/_edge/tenant_info")
    response = requests.get(tenant_info_url, timeout=10)
    # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in get_cloudId).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:a032ccbd81db7a5ecdf99c34321df6a9d0186605ca37282cf334c44dfb77ec5b'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a032ccbd81db7a5ecdf99c34321df6a9d0186605ca37282cf334c44dfb77ec5b', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 959, 'function': 'get_cloudId'}, 'file': 'common/data_source/utils.py', 'line': 959, 'function': 'get_cloudId', 'agent_name': 'get_cloudId', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=959)
    except _gr_client.GuardrailUnavailableError:
        pass
    response.raise_for_status()
    # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the user interface, before it leaves the application (in get_cloudId).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:13e5a018da8706858a6f16a15c338621b67521af44a789dfbc74fe3014f6f31a'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:13e5a018da8706858a6f16a15c338621b67521af44a789dfbc74fe3014f6f31a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 961, 'function': 'get_cloudId'}, 'file': 'common/data_source/utils.py', 'line': 961, 'function': 'get_cloudId', 'agent_name': 'get_cloudId', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        response = _gr_client.enforce(_gr_site, response, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return response.json()["cloudId"]


def scoped_url(url: str, product: str) -> str:
    parsed = urlparse(url)
    base_url = parsed.scheme + "://" + parsed.netloc
    cloud_id = get_cloudId(base_url)
    return f"https://api.atlassian.com/ex/{product}/{cloud_id}{parsed.path}"


def process_confluence_user_profiles_override(
    confluence_user_email_override: list[dict[str, str]],
) -> list[ConfluenceUser]:
    return [
        ConfluenceUser(
            user_id=override["user_id"],
            # username is not returned by the Confluence Server API anyways
            username=override["username"],
            display_name=override["display_name"],
            email=override["email"],
            type=override["type"],
        )
        for override in confluence_user_email_override
        if override is not None
    ]


def confluence_refresh_tokens(client_id: str, client_secret: str, cloud_id: str, refresh_token: str) -> dict[str, Any]:
    # rotate the refresh and access token
    # Note that access tokens are only good for an hour in confluence cloud,
    # so we're going to have problems if the connector runs for longer
    # https://developer.atlassian.com/cloud/confluence/oauth-2-3lo-apps/#use-a-refresh-token-to-get-another-access-token-and-refresh-token-pair
    response = requests.post(
        CONFLUENCE_OAUTH_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        },
    )
    # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in confluence_refresh_tokens).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:c6ce0b7239be5ca227af5375e8c98ad4255f7f5a59ab9100f8c5d421694e9585'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c6ce0b7239be5ca227af5375e8c98ad4255f7f5a59ab9100f8c5d421694e9585', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 993, 'function': 'confluence_refresh_tokens'}, 'file': 'common/data_source/utils.py', 'line': 993, 'function': 'confluence_refresh_tokens', 'agent_name': 'confluence_refresh_tokens', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=993)
    except _gr_client.GuardrailUnavailableError:
        pass

    try:
        token_response = TokenResponse.model_validate_json(response.text)
    except Exception:
        raise RuntimeError("Confluence Cloud token refresh failed.")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=token_response.expires_in)

    new_credentials: dict[str, Any] = {}
    new_credentials["confluence_access_token"] = token_response.access_token
    new_credentials["confluence_refresh_token"] = token_response.refresh_token
    new_credentials["created_at"] = now.isoformat()
    new_credentials["expires_at"] = expires_at.isoformat()
    new_credentials["expires_in"] = token_response.expires_in
    new_credentials["scope"] = token_response.scope
    new_credentials["cloud_id"] = cloud_id
    return new_credentials


class TimeoutThread(threading.Thread, Generic[R]):
    def __init__(self, timeout: float, func: Callable[..., R], *args: Any, **kwargs: Any):
        super().__init__()
        self.timeout = timeout
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.exception: Exception | None = None

    def run(self) -> None:
        try:
            self.result = self.func(*self.args, **self.kwargs)
        except Exception as e:
            self.exception = e

    def end(self) -> None:
        raise TimeoutError(f"Function {self.func.__name__} timed out after {self.timeout} seconds")


def run_with_timeout(timeout: float, func: Callable[..., R], *args: Any, **kwargs: Any) -> R:
    """
    Executes a function with a timeout. If the function doesn't complete within the specified
    timeout, raises TimeoutError.
    """
    context = contextvars.copy_context()
    task = TimeoutThread(timeout, context.run, func, *args, **kwargs)
    task.start()
    task.join(timeout)

    if task.exception is not None:
        raise task.exception
    if task.is_alive():
        task.end()

    return task.result  # type: ignore


def validate_attachment_filetype(
    attachment: dict[str, Any],
) -> bool:
    """
    Validates if the attachment is a supported file type.
    """
    media_type = attachment.get("metadata", {}).get("mediaType", "")
    if media_type.startswith("image/"):
        return is_valid_image_type(media_type)

    # For non-image files, check if we support the extension
    title = attachment.get("title", "")
    extension = Path(title).suffix.lstrip(".").lower() if "." in title else ""

    return is_accepted_file_ext("." + extension, OnyxExtensionType.Plain | OnyxExtensionType.Document)


class CallableProtocol(Protocol):
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


def run_functions_tuples_in_parallel(
    functions_with_args: Sequence[tuple[CallableProtocol, tuple[Any, ...]]],
    allow_failures: bool = False,
    max_workers: int | None = None,
) -> list[Any]:
    """
    Executes multiple functions in parallel and returns a list of the results for each function.
    This function preserves contextvars across threads, which is important for maintaining
    context like tenant IDs in database sessions.

    Args:
        functions_with_args: List of tuples each containing the function callable and a tuple of arguments.
        allow_failures: if set to True, then the function result will just be None
        max_workers: Max number of worker threads

    Returns:
        list: A list of results from each function, in the same order as the input functions.
    """
    workers = min(max_workers, len(functions_with_args)) if max_workers is not None else len(functions_with_args)

    if workers <= 0:
        return []

    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        # The primary reason for propagating contextvars is to allow acquiring a db session
        # that respects tenant id. Context.run is expected to be low-overhead, but if we later
        # find that it is increasing latency we can make using it optional.
        future_to_index = {executor.submit(contextvars.copy_context().run, func, *args): i for i, (func, args) in enumerate(functions_with_args)}

        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                results.append((index, future.result()))
            except Exception as e:
                _lineaje_payload = f"Function at index {index} failed due to {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in run_functions_tuples_in_parallel).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:c57df95c3be13fe0ff9d6d0d2f22394ef4dcf6969ed75f9e3c7a0274ba2301cd'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c57df95c3be13fe0ff9d6d0d2f22394ef4dcf6969ed75f9e3c7a0274ba2301cd', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/utils.py', 'line': 1116, 'function': 'run_functions_tuples_in_parallel'}, 'file': 'common/data_source/utils.py', 'line': 1116, 'function': 'run_functions_tuples_in_parallel', 'agent_name': 'run_functions_tuples_in_parallel', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(_lineaje_payload)
                results.append((index, None))  # type: ignore

                if not allow_failures:
                    raise

    results.sort(key=lambda x: x[0])
    return [result for index, result in results]


def _next_or_none(ind: int, gen: Iterator[R]) -> tuple[int, R | None]:
    return ind, next(gen, None)


def parallel_yield(gens: list[Iterator[R]], max_workers: int = 10) -> Iterator[R]:
    """
    Runs the list of generators with thread-level parallelism, yielding
    results as available. The asynchronous nature of this yielding means
    that stopping the returned iterator early DOES NOT GUARANTEE THAT NO
    FURTHER ITEMS WERE PRODUCED by the input gens. Only use this function
    if you are consuming all elements from the generators OR it is acceptable
    for some extra generator code to run and not have the result(s) yielded.
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index: dict[Future[tuple[int, R | None]], int] = {executor.submit(_next_or_none, ind, gen): ind for ind, gen in enumerate(gens)}

        next_ind = len(gens)
        while future_to_index:
            done, _ = wait(future_to_index, return_when=FIRST_COMPLETED)
            for future in done:
                ind, result = future.result()
                if result is not None:
                    yield result
                    future_to_index[executor.submit(_next_or_none, ind, gens[ind])] = next_ind
                    next_ind += 1
                del future_to_index[future]
