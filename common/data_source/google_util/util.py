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

import json
import logging
import os
import re
import socket
from collections.abc import Callable, Iterator
from enum import Enum
from typing import Any
import unicodedata
from googleapiclient.errors import HttpError  # type: ignore  # type: ignore

from common.data_source.config import DocumentSource
from common.data_source.google_drive.model import GoogleDriveFileType
from common.data_source.google_util.oauth_flow import ensure_oauth_token_dict


# See https://developers.google.com/drive/api/reference/rest/v3/files/list for more
class GoogleFields(str, Enum):
    ID = "id"
    CREATED_TIME = "createdTime"
    MODIFIED_TIME = "modifiedTime"
    NAME = "name"
    SIZE = "size"
    PARENTS = "parents"


NEXT_PAGE_TOKEN_KEY = "nextPageToken"
PAGE_TOKEN_KEY = "pageToken"
ORDER_BY_KEY = "orderBy"


def get_file_owners(file: GoogleDriveFileType, primary_admin_email: str) -> list[str]:
    """
    Get the owners of a file if the attribute is present.
    """
    return [email for owner in file.get("owners", []) if (email := owner.get("emailAddress")) and email.split("@")[-1] == primary_admin_email.split("@")[-1]]


# included for type purposes; caller should not need to address
# Nones unless max_num_pages is specified. Use
# execute_paginated_retrieval_with_max_pages instead if you want
# the early stop + yield None after max_num_pages behavior.
def execute_paginated_retrieval(
    retrieval_function: Callable,
    list_key: str | None = None,
    continue_on_404_or_403: bool = False,
    **kwargs: Any,
) -> Iterator[GoogleDriveFileType]:
    for item in _execute_paginated_retrieval(
        retrieval_function,
        list_key,
        continue_on_404_or_403,
        **kwargs,
    ):
        if not isinstance(item, str):
            yield item


def execute_paginated_retrieval_with_max_pages(
    retrieval_function: Callable,
    max_num_pages: int,
    list_key: str | None = None,
    continue_on_404_or_403: bool = False,
    **kwargs: Any,
) -> Iterator[GoogleDriveFileType | str]:
    yield from _execute_paginated_retrieval(
        retrieval_function,
        list_key,
        continue_on_404_or_403,
        max_num_pages=max_num_pages,
        **kwargs,
    )


def _execute_paginated_retrieval(
    retrieval_function: Callable,
    list_key: str | None = None,
    continue_on_404_or_403: bool = False,
    max_num_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[GoogleDriveFileType | str]:
    """Execute a paginated retrieval from Google Drive API
    Args:
        retrieval_function: The specific list function to call (e.g., service.files().list)
        list_key: If specified, each object returned by the retrieval function
                  will be accessed at the specified key and yielded from.
        continue_on_404_or_403: If True, the retrieval will continue even if the request returns a 404 or 403 error.
        max_num_pages: If specified, the retrieval will stop after the specified number of pages and yield None.
        **kwargs: Arguments to pass to the list function
    """
    if "fields" not in kwargs or "nextPageToken" not in kwargs["fields"]:
        raise ValueError("fields must contain nextPageToken for execute_paginated_retrieval")
    next_page_token = kwargs.get(PAGE_TOKEN_KEY, "")
    num_pages = 0
    while next_page_token is not None:
        if max_num_pages is not None and num_pages >= max_num_pages:
            yield next_page_token
            return
        num_pages += 1
        request_kwargs = kwargs.copy()
        if next_page_token:
            request_kwargs[PAGE_TOKEN_KEY] = next_page_token
        results = _execute_single_retrieval(
            retrieval_function,
            continue_on_404_or_403,
            **request_kwargs,
        )

        next_page_token = results.get(NEXT_PAGE_TOKEN_KEY)
        if list_key:
            for item in results.get(list_key, []):
                yield item
        else:
            yield results


def _execute_single_retrieval(
    retrieval_function: Callable,
    continue_on_404_or_403: bool = False,
    **request_kwargs: Any,
) -> GoogleDriveFileType:
    """Execute a single retrieval from Google Drive API"""
    try:
        results = retrieval_function(**request_kwargs).execute()

    except HttpError as e:
        if e.resp.status >= 500:
            results = retrieval_function()
        elif e.resp.status == 400:
            if "pageToken" in request_kwargs and "Invalid Value" in str(e) and "pageToken" in str(e):
                logging.warning(f"Invalid page token: {request_kwargs['pageToken']}, retrying from start of request")
                request_kwargs.pop("pageToken")
                return _execute_single_retrieval(
                    retrieval_function,
                    continue_on_404_or_403,
                    **request_kwargs,
                )
            _lineaje_payload = f"Error executing request: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _execute_single_retrieval).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:8bf80566c31e950aa4ff864d1e1cdff0876c699b74d8cd416f1fe134b9948f0b'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8bf80566c31e950aa4ff864d1e1cdff0876c699b74d8cd416f1fe134b9948f0b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/util.py', 'line': 138, 'function': '_execute_single_retrieval'}, 'file': 'common/data_source/google_util/util.py', 'line': 138, 'function': '_execute_single_retrieval', 'agent_name': '_execute_single_retrieval', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            raise e
        elif e.resp.status == 404 or e.resp.status == 403:
            if continue_on_404_or_403:
                _lineaje_payload = f"Error executing request: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _execute_single_retrieval).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:efd8aa1afc2751efae1f3fd59fb6255838af025f5a36f2a2bf5c66be1096c452'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:efd8aa1afc2751efae1f3fd59fb6255838af025f5a36f2a2bf5c66be1096c452', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/util.py', 'line': 142, 'function': '_execute_single_retrieval'}, 'file': 'common/data_source/google_util/util.py', 'line': 142, 'function': '_execute_single_retrieval', 'agent_name': '_execute_single_retrieval', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.debug(_lineaje_payload)
                results = {}
            else:
                raise e
        elif e.resp.status == 429:
            results = retrieval_function()
        else:
            _lineaje_payload = "Error executing request:"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _execute_single_retrieval).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:4fdfad59528bf61bcebef5fdffa224408f4c0bfe5468438de969fb4ea4967c1d'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4fdfad59528bf61bcebef5fdffa224408f4c0bfe5468438de969fb4ea4967c1d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/util.py', 'line': 149, 'function': '_execute_single_retrieval'}, 'file': 'common/data_source/google_util/util.py', 'line': 149, 'function': '_execute_single_retrieval', 'agent_name': '_execute_single_retrieval', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
            raise e
    except (TimeoutError, socket.timeout) as error:
        # LINEAJE: runtime guardrail checks `error` as it flows from the agent to the application log, before it is written to the log (in _execute_single_retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3aa76cfe7b4334a1e56e2de2104c7610ecc41ace64b8cd5d20b25ca2f14d5191'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3aa76cfe7b4334a1e56e2de2104c7610ecc41ace64b8cd5d20b25ca2f14d5191', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/util.py', 'line': 152, 'function': '_execute_single_retrieval'}, 'file': 'common/data_source/google_util/util.py', 'line': 152, 'function': '_execute_single_retrieval', 'agent_name': '_execute_single_retrieval', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            error = _gr_client.enforce(_gr_site, error, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning(
            "Timed out executing Google API request; retrying with backoff. Details: %s",
            error,
        )
        results = retrieval_function()
    # LINEAJE: runtime guardrail checks `results` as it flows from the agent to the user interface, before it leaves the application (in _execute_single_retrieval).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `results` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:34355573ab57e8c3c291c884f950a35ed7754ed2ce15c242daa46aa3ad9b7c8e'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:34355573ab57e8c3c291c884f950a35ed7754ed2ce15c242daa46aa3ad9b7c8e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/util.py', 'line': 157, 'function': '_execute_single_retrieval'}, 'file': 'common/data_source/google_util/util.py', 'line': 157, 'function': '_execute_single_retrieval', 'agent_name': '_execute_single_retrieval', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        results = _gr_client.enforce(_gr_site, results, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return results


def get_credentials_from_env(email: str, oauth: bool = False, source="drive") -> dict:
    try:
        if oauth:
            raw_credential_string = os.environ["GOOGLE_OAUTH_CREDENTIALS_JSON_STR"]
        else:
            raw_credential_string = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON_STR"]
    except KeyError:
        raise ValueError("Missing Google Drive credentials in environment variables")

    try:
        credential_dict = json.loads(raw_credential_string)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON in Google Drive credentials")

    if oauth and source == "drive":
        credential_dict = ensure_oauth_token_dict(credential_dict, DocumentSource.GOOGLE_DRIVE)
    else:
        credential_dict = ensure_oauth_token_dict(credential_dict, DocumentSource.GMAIL)

    # LINEAJE: runtime guardrail checks `credential_dict` as it flows from the agent to an external endpoint, before it leaves the application (in get_credentials_from_env).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `credential_dict` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:ea8ae703723f8f471062d7da769db5c3b8a525d4d835f0c3d50fd6ff1eb8566c'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ea8ae703723f8f471062d7da769db5c3b8a525d4d835f0c3d50fd6ff1eb8566c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/util.py', 'line': 179, 'function': 'get_credentials_from_env'}, 'file': 'common/data_source/google_util/util.py', 'line': 179, 'function': 'get_credentials_from_env', 'agent_name': 'get_credentials_from_env', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        credential_dict = _gr_client.enforce(_gr_site, credential_dict, content_type='application/json', variable_name='credential_dict', source_file=__file__, before_line=179)
    except _gr_client.GuardrailUnavailableError:
        pass
    refried_credential_string = json.dumps(credential_dict)

    DB_CREDENTIALS_DICT_TOKEN_KEY = "google_tokens"
    DB_CREDENTIALS_DICT_SERVICE_ACCOUNT_KEY = "google_service_account_key"
    DB_CREDENTIALS_PRIMARY_ADMIN_KEY = "google_primary_admin"
    DB_CREDENTIALS_AUTHENTICATION_METHOD = "authentication_method"

    cred_key = DB_CREDENTIALS_DICT_TOKEN_KEY if oauth else DB_CREDENTIALS_DICT_SERVICE_ACCOUNT_KEY

    return {
        cred_key: refried_credential_string,
        DB_CREDENTIALS_PRIMARY_ADMIN_KEY: email,
        DB_CREDENTIALS_AUTHENTICATION_METHOD: "uploaded",
    }

def sanitize_filename(name: str) -> str:
    """
    Soft sanitize for MinIO/S3:
    - Replace only prohibited characters with a space.
    - Preserve readability (no ugly underscores).
    - Collapse multiple spaces.
    """
    if name is None:
        return "file.txt"

    name = str(name).strip()

    # Characters that MUST NOT appear in S3/MinIO object keys
    # Replace them with a space (not underscore)
    forbidden = r'[\\\?\#\%\*\:\|\<\>"]'
    name = re.sub(forbidden, " ", name)

    # Replace slashes "/" (S3 interprets as folder) with space
    name = name.replace("/", " ")

    # Collapse multiple spaces into one
    name = re.sub(r"\s+", " ", name)

    # Trim both ends
    name = name.strip()

    # Enforce reasonable max length
    if len(name) > 200:
        base, ext = os.path.splitext(name)
        name = base[:180].rstrip() + ext

    # Ensure there is an extension (your original logic)
    if not os.path.splitext(name)[1]:
        name += ".txt"

    # LINEAJE: runtime guardrail checks `name` as it flows from the agent to the user interface, before it leaves the application (in sanitize_filename).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `name` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:876ed2a8b5510a5c42c326a90cadf235338f0601a92fc6a8214e36b48c2f72ff'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:876ed2a8b5510a5c42c326a90cadf235338f0601a92fc6a8214e36b48c2f72ff', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/util.py', 'line': 229, 'function': 'sanitize_filename'}, 'file': 'common/data_source/google_util/util.py', 'line': 229, 'function': 'sanitize_filename', 'agent_name': 'sanitize_filename', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        name = _gr_client.enforce(_gr_site, name, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return name


def clean_string(text: str | None) -> str | None:
    """
    Clean a string to make it safe for insertion into MySQL (utf8mb4).
    - Normalize Unicode
    - Remove control characters / zero-width characters
    - Optionally remove high-plane emoji and symbols
    """
    if text is None:
        return None

    # 0. Ensure the value is a string
    text = str(text)

    # 1. Normalize Unicode (NFC)
    text = unicodedata.normalize("NFC", text)

    # 2. Remove ASCII control characters (except tab, newline, carriage return)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # 3. Remove zero-width characters / BOM
    text = re.sub(r"[\u200b-\u200d\uFEFF]", "", text)

    # 4. Remove high Unicode characters (emoji, special symbols)
    text = re.sub(r"[\U00010000-\U0010FFFF]", "", text)

    # 5. Final fallback: strip any invalid UTF-8 sequences
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        text = text.encode("utf-8", errors="ignore").decode("utf-8")

    # LINEAJE: runtime guardrail checks `text` as it flows from the agent to the user interface, before it leaves the application (in clean_string).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `text` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:f08785d0baadcafa23b02d147a92ff422c4b1cd7c810cf1103eae36891d1c974'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f08785d0baadcafa23b02d147a92ff422c4b1cd7c810cf1103eae36891d1c974', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/util.py', 'line': 263, 'function': 'clean_string'}, 'file': 'common/data_source/google_util/util.py', 'line': 263, 'function': 'clean_string', 'agent_name': 'clean_string', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        text = _gr_client.enforce(_gr_site, text, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return text