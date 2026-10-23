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
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from enum import Enum

from googleapiclient.discovery import Resource  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

from common.data_source.google_drive.constant import DRIVE_FOLDER_TYPE, DRIVE_SHORTCUT_TYPE
from common.data_source.google_drive.model import DriveRetrievalStage, GoogleDriveFileType, RetrievedDriveFile
from common.data_source.google_util.resource import GoogleDriveService
from common.data_source.google_util.util import ORDER_BY_KEY, PAGE_TOKEN_KEY, GoogleFields, execute_paginated_retrieval, execute_paginated_retrieval_with_max_pages
from common.data_source.models import SecondsSinceUnixEpoch

PERMISSION_FULL_DESCRIPTION = "permissions(id, emailAddress, type, domain, permissionDetails)"

FILE_FIELDS = "nextPageToken, files(mimeType, id, name, modifiedTime, webViewLink, shortcutDetails, owners(emailAddress), size)"
FILE_FIELDS_WITH_PERMISSIONS = f"nextPageToken, files(mimeType, id, name, {PERMISSION_FULL_DESCRIPTION}, permissionIds, modifiedTime, webViewLink, shortcutDetails, owners(emailAddress), size)"
SLIM_FILE_FIELDS = f"nextPageToken, files(mimeType, driveId, id, name, {PERMISSION_FULL_DESCRIPTION}, permissionIds, webViewLink, owners(emailAddress), modifiedTime)"

FOLDER_FIELDS = "nextPageToken, files(id, name, permissions, modifiedTime, webViewLink, shortcutDetails)"


class DriveFileFieldType(Enum):
    """Enum to specify which fields to retrieve from Google Drive files"""

    SLIM = "slim"  # Minimal fields for basic file info
    STANDARD = "standard"  # Standard fields including content metadata
    WITH_PERMISSIONS = "with_permissions"  # Full fields including permissions


def generate_time_range_filter(
    start: SecondsSinceUnixEpoch | None = None,
    end: SecondsSinceUnixEpoch | None = None,
) -> str:
    time_range_filter = ""
    if start is not None:
        time_start = datetime.fromtimestamp(start, tz=timezone.utc).isoformat()
        time_range_filter += f" and {GoogleFields.MODIFIED_TIME.value} > '{time_start}'"
    if end is not None:
        time_stop = datetime.fromtimestamp(end, tz=timezone.utc).isoformat()
        time_range_filter += f" and {GoogleFields.MODIFIED_TIME.value} <= '{time_stop}'"
    # LINEAJE: runtime guardrail checks `time_range_filter` as it flows from the agent to the user interface, before it leaves the application (in generate_time_range_filter).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `time_range_filter` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:8197ea9ed598be69eb04126a964360ae2d6b44204c1ad772181bd6329839e889'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8197ea9ed598be69eb04126a964360ae2d6b44204c1ad772181bd6329839e889', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 43, 'function': 'generate_time_range_filter'}, 'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 43, 'function': 'generate_time_range_filter', 'agent_name': 'generate_time_range_filter', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        time_range_filter = _gr_client.enforce(_gr_site, time_range_filter, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return time_range_filter


def _get_folders_in_parent(
    service: Resource,
    parent_id: str | None = None,
) -> Iterator[GoogleDriveFileType]:
    # Follow shortcuts to folders
    query = f"(mimeType = '{DRIVE_FOLDER_TYPE}' or mimeType = '{DRIVE_SHORTCUT_TYPE}')"
    query += " and trashed = false"

    if parent_id:
        query += f" and '{parent_id}' in parents"

    for file in execute_paginated_retrieval(
        retrieval_function=service.files().list,
        list_key="files",
        continue_on_404_or_403=True,
        corpora="allDrives",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        fields=FOLDER_FIELDS,
        q=query,
    ):
        yield file


def _get_fields_for_file_type(field_type: DriveFileFieldType) -> str:
    """Get the appropriate fields string based on the field type enum"""
    if field_type == DriveFileFieldType.SLIM:
        return SLIM_FILE_FIELDS
    elif field_type == DriveFileFieldType.WITH_PERMISSIONS:
        return FILE_FIELDS_WITH_PERMISSIONS
    else:  # DriveFileFieldType.STANDARD
        return FILE_FIELDS


def _get_files_in_parent(
    service: Resource,
    parent_id: str,
    field_type: DriveFileFieldType,
    start: SecondsSinceUnixEpoch | None = None,
    end: SecondsSinceUnixEpoch | None = None,
) -> Iterator[GoogleDriveFileType]:
    query = f"mimeType != '{DRIVE_FOLDER_TYPE}' and '{parent_id}' in parents"
    query += " and trashed = false"
    query += generate_time_range_filter(start, end)

    kwargs = {ORDER_BY_KEY: GoogleFields.MODIFIED_TIME.value}

    for file in execute_paginated_retrieval(
        retrieval_function=service.files().list,
        list_key="files",
        continue_on_404_or_403=True,
        corpora="allDrives",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        fields=_get_fields_for_file_type(field_type),
        q=query,
        **kwargs,
    ):
        yield file


def crawl_folders_for_files(
    service: Resource,
    parent_id: str,
    field_type: DriveFileFieldType,
    user_email: str,
    traversed_parent_ids: set[str],
    update_traversed_ids_func: Callable[[str], None],
    start: SecondsSinceUnixEpoch | None = None,
    end: SecondsSinceUnixEpoch | None = None,
) -> Iterator[RetrievedDriveFile]:
    """
    This function starts crawling from any folder. It is slower though.
    """
    _lineaje_payload = "Entered crawl_folders_for_files with parent_id: " + parent_id
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in crawl_folders_for_files).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:8d76ef7e06742c9e944072544c61529b3a248d27ea5322d4400746ee7a6785fc'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8d76ef7e06742c9e944072544c61529b3a248d27ea5322d4400746ee7a6785fc', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 120, 'function': 'crawl_folders_for_files'}, 'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 120, 'function': 'crawl_folders_for_files', 'agent_name': 'crawl_folders_for_files', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)
    if parent_id not in traversed_parent_ids:
        _lineaje_payload = "Parent id not in traversed parent ids, getting files"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in crawl_folders_for_files).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:0a6ea80b32419eeb1df9634f9f2bfdf7296343feb27c2a30d3c1f084f2c5f7f2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0a6ea80b32419eeb1df9634f9f2bfdf7296343feb27c2a30d3c1f084f2c5f7f2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 122, 'function': 'crawl_folders_for_files'}, 'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 122, 'function': 'crawl_folders_for_files', 'agent_name': 'crawl_folders_for_files', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        found_files = False
        file = {}
        try:
            for file in _get_files_in_parent(
                service=service,
                parent_id=parent_id,
                field_type=field_type,
                start=start,
                end=end,
            ):
                _lineaje_payload = f"Found file: {file['name']}, user email: {user_email}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in crawl_folders_for_files).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:6065282b96025ac44df83fecd4a8693fd240a415392aae66fca21cf40364cb2f'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6065282b96025ac44df83fecd4a8693fd240a415392aae66fca21cf40364cb2f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 133, 'function': 'crawl_folders_for_files'}, 'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 133, 'function': 'crawl_folders_for_files', 'agent_name': 'crawl_folders_for_files', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                found_files = True
                yield RetrievedDriveFile(
                    drive_file=file,
                    user_email=user_email,
                    parent_id=parent_id,
                    completion_stage=DriveRetrievalStage.FOLDER_FILES,
                )
            # Only mark a folder as done if it was fully traversed without errors
            # This usually indicates that the owner of the folder was impersonated.
            # In cases where this never happens, most likely the folder owner is
            # not part of the Google Workspace in question (or for oauth, the authenticated
            # user doesn't own the folder)
            if found_files:
                update_traversed_ids_func(parent_id)
        except Exception as e:
            if isinstance(e, HttpError) and e.status_code == 403:
                # don't yield an error here because this is expected behavior
                # when a user doesn't have access to a folder
                _lineaje_payload = f"Error getting files in parent {parent_id}: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in crawl_folders_for_files).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a88f843066b9bef6616cdfca8cbf5c388f78687b49b7797faec1b3c4f152575e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a88f843066b9bef6616cdfca8cbf5c388f78687b49b7797faec1b3c4f152575e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 152, 'function': 'crawl_folders_for_files'}, 'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 152, 'function': 'crawl_folders_for_files', 'agent_name': 'crawl_folders_for_files', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.debug(_lineaje_payload)
            else:
                _lineaje_payload = f"Error getting files in parent {parent_id}: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in crawl_folders_for_files).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:0f1bb28ef4195ecbc1ace58dce600ba6b2a6b33714ef32df4d93d0441261afdd'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0f1bb28ef4195ecbc1ace58dce600ba6b2a6b33714ef32df4d93d0441261afdd', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 154, 'function': 'crawl_folders_for_files'}, 'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 154, 'function': 'crawl_folders_for_files', 'agent_name': 'crawl_folders_for_files', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                yield RetrievedDriveFile(
                    drive_file=file,
                    user_email=user_email,
                    parent_id=parent_id,
                    completion_stage=DriveRetrievalStage.FOLDER_FILES,
                    error=e,
                )
    else:
        _lineaje_payload = f"Skipping subfolder files since already traversed: {parent_id}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in crawl_folders_for_files).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:235bf7dfdc095874ba1603d7c2dec49259b11ca0118010e25afdf922ee02f142'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:235bf7dfdc095874ba1603d7c2dec49259b11ca0118010e25afdf922ee02f142', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 163, 'function': 'crawl_folders_for_files'}, 'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 163, 'function': 'crawl_folders_for_files', 'agent_name': 'crawl_folders_for_files', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)

    for subfolder in _get_folders_in_parent(
        service=service,
        parent_id=parent_id,
    ):
        _lineaje_payload = "Fetching all files in subfolder: " + subfolder["name"]
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in crawl_folders_for_files).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a3ead58a148a9ef32678d90b2110de143c6ee498487545bd321550440ab21790'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a3ead58a148a9ef32678d90b2110de143c6ee498487545bd321550440ab21790', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 169, 'function': 'crawl_folders_for_files'}, 'file': 'common/data_source/google_drive/file_retrieval.py', 'line': 169, 'function': 'crawl_folders_for_files', 'agent_name': 'crawl_folders_for_files', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        yield from crawl_folders_for_files(
            service=service,
            parent_id=subfolder["id"],
            field_type=field_type,
            user_email=user_email,
            traversed_parent_ids=traversed_parent_ids,
            update_traversed_ids_func=update_traversed_ids_func,
            start=start,
            end=end,
        )


def get_files_in_shared_drive(
    service: Resource,
    drive_id: str,
    field_type: DriveFileFieldType,
    max_num_pages: int,
    update_traversed_ids_func: Callable[[str], None] = lambda _: None,
    cache_folders: bool = True,
    start: SecondsSinceUnixEpoch | None = None,
    end: SecondsSinceUnixEpoch | None = None,
    page_token: str | None = None,
) -> Iterator[GoogleDriveFileType | str]:
    kwargs = {ORDER_BY_KEY: GoogleFields.MODIFIED_TIME.value}
    if page_token:
        logging.info(f"Using page token: {page_token}")
        kwargs[PAGE_TOKEN_KEY] = page_token

    if cache_folders:
        # If we know we are going to folder crawl later, we can cache the folders here
        # Get all folders being queried and add them to the traversed set
        folder_query = f"mimeType = '{DRIVE_FOLDER_TYPE}'"
        folder_query += " and trashed = false"
        for folder in execute_paginated_retrieval(
            retrieval_function=service.files().list,
            list_key="files",
            continue_on_404_or_403=True,
            corpora="drive",
            driveId=drive_id,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            fields="nextPageToken, files(id)",
            q=folder_query,
        ):
            update_traversed_ids_func(folder["id"])

    # Get all files in the shared drive
    file_query = f"mimeType != '{DRIVE_FOLDER_TYPE}'"
    file_query += " and trashed = false"
    file_query += generate_time_range_filter(start, end)

    for file in execute_paginated_retrieval_with_max_pages(
        retrieval_function=service.files().list,
        max_num_pages=max_num_pages,
        list_key="files",
        continue_on_404_or_403=True,
        corpora="drive",
        driveId=drive_id,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
        fields=_get_fields_for_file_type(field_type),
        q=file_query,
        **kwargs,
    ):
        # If we found any files, mark this drive as traversed. When a user has access to a drive,
        # they have access to all the files in the drive. Also, not a huge deal if we re-traverse
        # empty drives.
        # NOTE: ^^ the above is not actually true due to folder restrictions:
        # https://support.google.com/a/users/answer/12380484?hl=en
        # So we may have to change this logic for people who use folder restrictions.
        update_traversed_ids_func(drive_id)
        yield file


def get_all_files_in_my_drive_and_shared(
    service: GoogleDriveService,
    update_traversed_ids_func: Callable,
    field_type: DriveFileFieldType,
    include_shared_with_me: bool,
    max_num_pages: int,
    start: SecondsSinceUnixEpoch | None = None,
    end: SecondsSinceUnixEpoch | None = None,
    cache_folders: bool = True,
    page_token: str | None = None,
) -> Iterator[GoogleDriveFileType | str]:
    kwargs = {ORDER_BY_KEY: GoogleFields.MODIFIED_TIME.value}
    if page_token:
        logging.info(f"Using page token: {page_token}")
        kwargs[PAGE_TOKEN_KEY] = page_token

    if cache_folders:
        # If we know we are going to folder crawl later, we can cache the folders here
        # Get all folders being queried and add them to the traversed set
        folder_query = f"mimeType = '{DRIVE_FOLDER_TYPE}'"
        folder_query += " and trashed = false"
        if not include_shared_with_me:
            folder_query += " and 'me' in owners"
        found_folders = False
        for folder in execute_paginated_retrieval(
            retrieval_function=service.files().list,
            list_key="files",
            corpora="user",
            fields=_get_fields_for_file_type(field_type),
            q=folder_query,
        ):
            update_traversed_ids_func(folder[GoogleFields.ID])
            found_folders = True
        if found_folders:
            update_traversed_ids_func(get_root_folder_id(service))

    # Then get the files
    file_query = f"mimeType != '{DRIVE_FOLDER_TYPE}'"
    file_query += " and trashed = false"
    if not include_shared_with_me:
        file_query += " and 'me' in owners"
    file_query += generate_time_range_filter(start, end)
    yield from execute_paginated_retrieval_with_max_pages(
        retrieval_function=service.files().list,
        max_num_pages=max_num_pages,
        list_key="files",
        continue_on_404_or_403=False,
        corpora="user",
        fields=_get_fields_for_file_type(field_type),
        q=file_query,
        **kwargs,
    )


def get_all_files_for_oauth(
    service: GoogleDriveService,
    include_files_shared_with_me: bool,
    include_my_drives: bool,
    # One of the above 2 should be true
    include_shared_drives: bool,
    field_type: DriveFileFieldType,
    max_num_pages: int,
    start: SecondsSinceUnixEpoch | None = None,
    end: SecondsSinceUnixEpoch | None = None,
    page_token: str | None = None,
) -> Iterator[GoogleDriveFileType | str]:
    kwargs = {ORDER_BY_KEY: GoogleFields.MODIFIED_TIME.value}
    if page_token:
        logging.info(f"Using page token: {page_token}")
        kwargs[PAGE_TOKEN_KEY] = page_token

    should_get_all = include_shared_drives and include_my_drives and include_files_shared_with_me
    corpora = "allDrives" if should_get_all else "user"

    file_query = f"mimeType != '{DRIVE_FOLDER_TYPE}'"
    file_query += " and trashed = false"
    file_query += generate_time_range_filter(start, end)

    if not should_get_all:
        if include_files_shared_with_me and not include_my_drives:
            file_query += " and not 'me' in owners"
        if not include_files_shared_with_me and include_my_drives:
            file_query += " and 'me' in owners"

    yield from execute_paginated_retrieval_with_max_pages(
        max_num_pages=max_num_pages,
        retrieval_function=service.files().list,
        list_key="files",
        continue_on_404_or_403=False,
        corpora=corpora,
        includeItemsFromAllDrives=should_get_all,
        supportsAllDrives=should_get_all,
        fields=_get_fields_for_file_type(field_type),
        q=file_query,
        **kwargs,
    )


# Just in case we need to get the root folder id
def get_root_folder_id(service: Resource) -> str:
    # we don't paginate here because there is only one root folder per user
    # https://developers.google.com/drive/api/guides/v2-to-v3-reference
    return service.files().get(fileId="root", fields=GoogleFields.ID.value).execute()[GoogleFields.ID.value]
