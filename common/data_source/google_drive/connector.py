"""Google Drive connector"""
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


import copy
import logging
import os
import sys
import threading
from collections.abc import Callable, Generator, Iterator
from enum import Enum
from functools import partial
from typing import Any, Protocol, cast
from urllib.parse import urlparse

from google.auth.exceptions import RefreshError  # type: ignore  # type: ignore
from google.oauth2.credentials import Credentials as OAuthCredentials  # type: ignore  # type: ignore  # type: ignore
from google.oauth2.service_account import Credentials as ServiceAccountCredentials  # type: ignore  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore  # type: ignore
from typing_extensions import override

from common.data_source.config import GOOGLE_DRIVE_CONNECTOR_SIZE_THRESHOLD, INDEX_BATCH_SIZE, SLIM_BATCH_SIZE, DocumentSource
from common.data_source.exceptions import ConnectorMissingCredentialError, ConnectorValidationError, CredentialExpiredError, InsufficientPermissionsError
from common.data_source.google_drive.doc_conversion import PermissionSyncContext, build_slim_document, convert_drive_item_to_document, onyx_document_id_from_drive_file
from common.data_source.google_drive.file_retrieval import (
    DriveFileFieldType,
    crawl_folders_for_files,
    get_all_files_for_oauth,
    get_all_files_in_my_drive_and_shared,
    get_files_in_shared_drive,
    get_root_folder_id,
)
from common.data_source.google_drive.model import DriveRetrievalStage, GoogleDriveCheckpoint, GoogleDriveFileType, RetrievedDriveFile, StageCompletion
from common.data_source.google_util.auth import get_google_creds
from common.data_source.google_util.constant import DB_CREDENTIALS_PRIMARY_ADMIN_KEY, MISSING_SCOPES_ERROR_STR, USER_FIELDS
from common.data_source.google_util.resource import GoogleDriveService, get_admin_service, get_drive_service
from common.data_source.google_util.util import GoogleFields, execute_paginated_retrieval, get_file_owners
from common.data_source.google_util.util_threadpool_concurrency import ThreadSafeDict
from common.data_source.interfaces import (
    CheckpointedConnectorWithPermSync,
    IndexingHeartbeatInterface,
    SlimConnectorWithPermSync,
)
from common.data_source.models import CheckpointOutput, ConnectorFailure, Document, EntityFailure, GenerateSlimDocumentOutput, SecondsSinceUnixEpoch
from common.data_source.utils import datetime_from_string, parallel_yield, run_functions_tuples_in_parallel

MAX_DRIVE_WORKERS = int(os.environ.get("MAX_DRIVE_WORKERS", 4))
SHARED_DRIVE_PAGES_PER_CHECKPOINT = 2
MY_DRIVE_PAGES_PER_CHECKPOINT = 2
OAUTH_PAGES_PER_CHECKPOINT = 2
FOLDERS_PER_CHECKPOINT = 1


def _extract_str_list_from_comma_str(string: str | None) -> list[str]:
    if not string:
        return []
    return [s.strip() for s in string.split(",") if s.strip()]


def _extract_ids_from_urls(urls: list[str]) -> list[str]:
    return [urlparse(url).path.strip("/").split("/")[-1] for url in urls]


def _clean_requested_drive_ids(
    requested_drive_ids: set[str],
    requested_folder_ids: set[str],
    all_drive_ids_available: set[str],
) -> tuple[list[str], list[str]]:
    invalid_requested_drive_ids = requested_drive_ids - all_drive_ids_available
    filtered_folder_ids = requested_folder_ids - all_drive_ids_available
    if invalid_requested_drive_ids:
        _lineaje_payload = f"Some shared drive IDs were not found. IDs: {invalid_requested_drive_ids}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _clean_requested_drive_ids).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b07aaa8f1ae5be7a6e2df7b0991bc0137250915c05f7d1ebbb6cec633fc50ece'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b07aaa8f1ae5be7a6e2df7b0991bc0137250915c05f7d1ebbb6cec633fc50ece', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 70, 'function': '_clean_requested_drive_ids'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 70, 'function': '_clean_requested_drive_ids', 'agent_name': '_clean_requested_drive_ids', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning(_lineaje_payload)
        _lineaje_payload = "Checking for folder access instead..."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _clean_requested_drive_ids).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:4d71bcb8cb7d5a880511ce0df44b1da484770110f14c8bfcb962c47f4295517b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4d71bcb8cb7d5a880511ce0df44b1da484770110f14c8bfcb962c47f4295517b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 71, 'function': '_clean_requested_drive_ids'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 71, 'function': '_clean_requested_drive_ids', 'agent_name': '_clean_requested_drive_ids', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning(_lineaje_payload)
        filtered_folder_ids.update(invalid_requested_drive_ids)

    valid_requested_drive_ids = requested_drive_ids - invalid_requested_drive_ids
    return sorted(valid_requested_drive_ids), sorted(filtered_folder_ids)


def add_retrieval_info(
    drive_files: Iterator[GoogleDriveFileType | str],
    user_email: str,
    completion_stage: DriveRetrievalStage,
    parent_id: str | None = None,
) -> Iterator[RetrievedDriveFile | str]:
    for file in drive_files:
        if isinstance(file, str):
            yield file
            continue
        yield RetrievedDriveFile(
            drive_file=file,
            user_email=user_email,
            parent_id=parent_id,
            completion_stage=completion_stage,
        )


class CredentialedRetrievalMethod(Protocol):
    def __call__(
        self,
        field_type: DriveFileFieldType,
        checkpoint: GoogleDriveCheckpoint,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
    ) -> Iterator[RetrievedDriveFile]: ...


class DriveIdStatus(str, Enum):
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class GoogleDriveConnector(SlimConnectorWithPermSync, CheckpointedConnectorWithPermSync):
    def __init__(
        self,
        include_shared_drives: bool = False,
        include_my_drives: bool = False,
        include_files_shared_with_me: bool = False,
        shared_drive_urls: str | None = None,
        my_drive_emails: str | None = None,
        shared_folder_urls: str | None = None,
        specific_user_emails: str | None = None,
        batch_size: int = INDEX_BATCH_SIZE,
    ) -> None:
        if not any(
            (
                include_shared_drives,
                include_my_drives,
                include_files_shared_with_me,
                shared_folder_urls,
                my_drive_emails,
                shared_drive_urls,
            )
        ):
            raise ConnectorValidationError(
                "Nothing to index. Please specify at least one of the following: include_shared_drives, include_my_drives, include_files_shared_with_me, shared_folder_urls, or my_drive_emails"
            )

        specific_requests_made = False
        if bool(shared_drive_urls) or bool(my_drive_emails) or bool(shared_folder_urls):
            specific_requests_made = True
        self.specific_requests_made = specific_requests_made

        # NOTE: potentially modified in load_credentials if using service account
        self.include_files_shared_with_me = False if specific_requests_made else include_files_shared_with_me
        self.include_my_drives = False if specific_requests_made else include_my_drives
        self.include_shared_drives = False if specific_requests_made else include_shared_drives

        shared_drive_url_list = _extract_str_list_from_comma_str(shared_drive_urls)
        self._requested_shared_drive_ids = set(_extract_ids_from_urls(shared_drive_url_list))

        self._requested_my_drive_emails = set(_extract_str_list_from_comma_str(my_drive_emails))

        shared_folder_url_list = _extract_str_list_from_comma_str(shared_folder_urls)
        self._requested_folder_ids = set(_extract_ids_from_urls(shared_folder_url_list))
        self._specific_user_emails = _extract_str_list_from_comma_str(specific_user_emails)

        self._primary_admin_email: str | None = None

        self._creds: OAuthCredentials | ServiceAccountCredentials | None = None
        self._creds_dict: dict[str, Any] | None = None

        # ids of folders and shared drives that have been traversed
        self._retrieved_folder_and_drive_ids: set[str] = set()

        self.allow_images = False

        self.size_threshold = GOOGLE_DRIVE_CONNECTOR_SIZE_THRESHOLD

        self.logger = logging.getLogger(self.__class__.__name__)

    def set_allow_images(self, value: bool) -> None:
        self.allow_images = value

    @property
    def primary_admin_email(self) -> str:
        if self._primary_admin_email is None:
            raise RuntimeError("Primary admin email missing, should not call this property before calling load_credentials")
        return self._primary_admin_email

    @property
    def google_domain(self) -> str:
        if self._primary_admin_email is None:
            raise RuntimeError("Primary admin email missing, should not call this property before calling load_credentials")
        return self._primary_admin_email.split("@")[-1]

    @property
    def creds(self) -> OAuthCredentials | ServiceAccountCredentials:
        if self._creds is None:
            raise RuntimeError("Creds missing, should not call this property before calling load_credentials")
        return self._creds

    # TODO: ensure returned new_creds_dict is actually persisted when this is called?
    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        try:
            self._primary_admin_email = credentials[DB_CREDENTIALS_PRIMARY_ADMIN_KEY]
        except KeyError:
            raise ValueError("Credentials json missing primary admin key")

        self._creds, new_creds_dict = get_google_creds(
            credentials=credentials,
            source=DocumentSource.GOOGLE_DRIVE,
        )

        # Service account connectors don't have a specific setting determining whether
        # to include "shared with me" for each user, so we default to true unless the connector
        # is in specific folders/drives mode. Note that shared files are only picked up during
        # the My Drive stage, so this does nothing if the connector is set to only index shared drives.
        if isinstance(self._creds, ServiceAccountCredentials) and not self.specific_requests_made:
            self.include_files_shared_with_me = True

        self._creds_dict = new_creds_dict

        return new_creds_dict

    def _update_traversed_parent_ids(self, folder_id: str) -> None:
        self._retrieved_folder_and_drive_ids.add(folder_id)

    def _get_all_user_emails(self) -> list[str]:
        if self._specific_user_emails:
            return self._specific_user_emails

        # Start with primary admin email
        user_emails = [self.primary_admin_email]

        # Only fetch additional users if using service account
        if isinstance(self.creds, OAuthCredentials):
            # LINEAJE: runtime guardrail checks `user_emails` as it flows from the agent to the user interface, before it leaves the application (in GoogleDriveConnector._get_all_user_emails).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `user_emails` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:c6cd6134c8b7a69361659673e3accc881d9632ad4e23aef581580e0e97e18bd4'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c6cd6134c8b7a69361659673e3accc881d9632ad4e23aef581580e0e97e18bd4', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 227, 'function': 'GoogleDriveConnector._get_all_user_emails'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 227, 'function': '_get_all_user_emails', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                user_emails = _gr_client.enforce(_gr_site, user_emails, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return user_emails

        admin_service = get_admin_service(
            creds=self.creds,
            user_email=self.primary_admin_email,
        )

        # Get admins first since they're more likely to have access to most files
        for is_admin in [True, False]:
            query = "isAdmin=true" if is_admin else "isAdmin=false"
            for user in execute_paginated_retrieval(
                retrieval_function=admin_service.users().list,
                list_key="users",
                fields=USER_FIELDS,
                domain=self.google_domain,
                query=query,
            ):
                if email := user.get("primaryEmail"):
                    if email not in user_emails:
                        user_emails.append(email)
        # LINEAJE: runtime guardrail checks `user_emails` as it flows from the agent to the user interface, before it leaves the application (in GoogleDriveConnector._get_all_user_emails).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `user_emails` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8b50db1f913399892c06b5cc9bd48e8f95096b4cb397cac31a6a9d6359765c94'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8b50db1f913399892c06b5cc9bd48e8f95096b4cb397cac31a6a9d6359765c94', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 247, 'function': 'GoogleDriveConnector._get_all_user_emails'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 247, 'function': '_get_all_user_emails', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            user_emails = _gr_client.enforce(_gr_site, user_emails, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return user_emails

    def get_all_drive_ids(self) -> set[str]:
        return self._get_all_drives_for_user(self.primary_admin_email)

    def _get_all_drives_for_user(self, user_email: str) -> set[str]:
        drive_service = get_drive_service(self.creds, user_email)
        is_service_account = isinstance(self.creds, ServiceAccountCredentials)
        _lineaje_payload = f"Getting all drives for user {user_email} with service account: {is_service_account}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._get_all_drives_for_user).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6236802238be95f1aee22920c1bed98ef33fe2666a0ed8b745e1cb07b83746c8'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6236802238be95f1aee22920c1bed98ef33fe2666a0ed8b745e1cb07b83746c8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 255, 'function': 'GoogleDriveConnector._get_all_drives_for_user'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 255, 'function': '_get_all_drives_for_user', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)
        all_drive_ids: set[str] = set()
        for drive in execute_paginated_retrieval(
            retrieval_function=drive_service.drives().list,
            list_key="drives",
            useDomainAdminAccess=is_service_account,
            fields="drives(id),nextPageToken",
        ):
            all_drive_ids.add(drive["id"])

        if not all_drive_ids:
            _lineaje_payload = "No drives found even though indexing shared drives was requested."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._get_all_drives_for_user).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:5b681ba1458f61ab494d8bcd492dcdb71a2bc3fabe0b513deef2a5b9ec94aa58'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5b681ba1458f61ab494d8bcd492dcdb71a2bc3fabe0b513deef2a5b9ec94aa58', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 266, 'function': 'GoogleDriveConnector._get_all_drives_for_user'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 266, 'function': '_get_all_drives_for_user', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.warning(_lineaje_payload)

        # LINEAJE: runtime guardrail checks `all_drive_ids` as it flows from the agent to the user interface, before it leaves the application (in GoogleDriveConnector._get_all_drives_for_user).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `all_drive_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:81c318f5727859b21ac5b59b316971b4d199fb7bd98c05ace95bbf0608aace35'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:81c318f5727859b21ac5b59b316971b4d199fb7bd98c05ace95bbf0608aace35', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 268, 'function': 'GoogleDriveConnector._get_all_drives_for_user'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 268, 'function': '_get_all_drives_for_user', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            all_drive_ids = _gr_client.enforce(_gr_site, all_drive_ids, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return all_drive_ids

    def make_drive_id_getter(self, drive_ids: list[str], checkpoint: GoogleDriveCheckpoint) -> Callable[[str], str | None]:
        status_lock = threading.Lock()

        in_progress_drive_ids = {
            completion.current_folder_or_drive_id: user_email
            for user_email, completion in checkpoint.completion_map.items()
            if completion.stage == DriveRetrievalStage.SHARED_DRIVE_FILES and completion.current_folder_or_drive_id is not None
        }
        drive_id_status: dict[str, DriveIdStatus] = {}
        for drive_id in drive_ids:
            if drive_id in self._retrieved_folder_and_drive_ids:
                drive_id_status[drive_id] = DriveIdStatus.FINISHED
            elif drive_id in in_progress_drive_ids:
                drive_id_status[drive_id] = DriveIdStatus.IN_PROGRESS
            else:
                drive_id_status[drive_id] = DriveIdStatus.AVAILABLE

        def get_available_drive_id(thread_id: str) -> str | None:
            completion = checkpoint.completion_map[thread_id]
            with status_lock:
                future_work = None
                for drive_id, status in drive_id_status.items():
                    if drive_id in self._retrieved_folder_and_drive_ids:
                        drive_id_status[drive_id] = DriveIdStatus.FINISHED
                        continue
                    if drive_id in completion.processed_drive_ids:
                        continue

                    if status == DriveIdStatus.AVAILABLE:
                        # add to processed drive ids so if this user fails to retrieve once
                        # they won't try again on the next checkpoint run
                        completion.processed_drive_ids.add(drive_id)
                        # LINEAJE: runtime guardrail checks `drive_id` as it flows from the agent to the user interface, before it leaves the application (in GoogleDriveConnector.get_available_drive_id).
                        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `drive_id` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:e512e3a951b09567105d0efa856f5efd205f00ba98760650ad0d82daee51253e'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e512e3a951b09567105d0efa856f5efd205f00ba98760650ad0d82daee51253e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 302, 'function': 'GoogleDriveConnector.make_drive_id_getter.get_available_drive_id'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 302, 'function': 'get_available_drive_id', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            drive_id = _gr_client.enforce(_gr_site, drive_id, content_type='text/plain')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        return drive_id
                    elif status == DriveIdStatus.IN_PROGRESS:
                        _lineaje_payload = f"Drive id in progress: {drive_id}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector.get_available_drive_id).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:129be55b62305435bb18b6d39b5ba280c9ff33e22f2e6a8e9bb602e2583840fe'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:129be55b62305435bb18b6d39b5ba280c9ff33e22f2e6a8e9bb602e2583840fe', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 304, 'function': 'GoogleDriveConnector.make_drive_id_getter.get_available_drive_id'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 304, 'function': 'get_available_drive_id', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        self.logger.debug(_lineaje_payload)
                        future_work = drive_id

                if future_work:
                    # in this case, all drive ids are either finished or in progress.
                    # This thread will pick up one of the in progress ones in case it fails.
                    # This is a much simpler approach than waiting for a failure picking it up,
                    # at the cost of some repeated work until all shared drives are retrieved.
                    # we avoid apocalyptic cases like all threads focusing on one huge drive
                    # because the drive id is added to _retrieved_folder_and_drive_ids after any thread
                    # manages to retrieve any file from it (unfortunately, this is also the reason we currently
                    # sometimes fail to retrieve restricted access folders/files)
                    completion.processed_drive_ids.add(future_work)
                    # LINEAJE: runtime guardrail checks `future_work` as it flows from the agent to the user interface, before it leaves the application (in GoogleDriveConnector.get_available_drive_id).
                    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `future_work` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:7128a4582630fc05ef58e50e20dbd5db812dc42d9967d11fe8856a8739a37061'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7128a4582630fc05ef58e50e20dbd5db812dc42d9967d11fe8856a8739a37061', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 317, 'function': 'GoogleDriveConnector.make_drive_id_getter.get_available_drive_id'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 317, 'function': 'get_available_drive_id', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        future_work = _gr_client.enforce(_gr_site, future_work, content_type='text/plain')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    return future_work
            return None  # no work available, return None

        # LINEAJE: runtime guardrail checks `get_available_drive_id` as it flows from the agent to the user interface, before it leaves the application (in GoogleDriveConnector.make_drive_id_getter).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `get_available_drive_id` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a2d43bb354b4ffbf988605df9aa9fcda9f31b6135e7e108b4eba694f20d05d36'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a2d43bb354b4ffbf988605df9aa9fcda9f31b6135e7e108b4eba694f20d05d36', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 320, 'function': 'GoogleDriveConnector.make_drive_id_getter'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 320, 'function': 'make_drive_id_getter', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            get_available_drive_id = _gr_client.enforce(_gr_site, get_available_drive_id, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return get_available_drive_id

    def _impersonate_user_for_retrieval(
        self,
        user_email: str,
        field_type: DriveFileFieldType,
        checkpoint: GoogleDriveCheckpoint,
        get_new_drive_id: Callable[[str], str | None],
        sorted_filtered_folder_ids: list[str],
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
    ) -> Iterator[RetrievedDriveFile]:
        _lineaje_payload = f"Impersonating user {user_email}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._impersonate_user_for_retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ad70ff0deb2b093c6eec8f420fec80ad7852425ff1e1be94e73f910c59571551'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ad70ff0deb2b093c6eec8f420fec80ad7852425ff1e1be94e73f910c59571551', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 332, 'function': 'GoogleDriveConnector._impersonate_user_for_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 332, 'function': '_impersonate_user_for_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)
        curr_stage = checkpoint.completion_map[user_email]
        resuming = True
        if curr_stage.stage == DriveRetrievalStage.START:
            _lineaje_payload = f"Setting stage to {DriveRetrievalStage.MY_DRIVE_FILES.value}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._impersonate_user_for_retrieval).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:62a244750e97de8c8509795ef6824ea0c4aeecbbac51d2ebc6061dd380ded3cf'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:62a244750e97de8c8509795ef6824ea0c4aeecbbac51d2ebc6061dd380ded3cf', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 336, 'function': 'GoogleDriveConnector._impersonate_user_for_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 336, 'function': '_impersonate_user_for_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.info(_lineaje_payload)
            curr_stage.stage = DriveRetrievalStage.MY_DRIVE_FILES
            resuming = False
        drive_service = get_drive_service(self.creds, user_email)

        # validate that the user has access to the drive APIs by performing a simple
        # request and checking for a 401
        try:
            _lineaje_payload = f"Getting root folder id for user {user_email}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._impersonate_user_for_retrieval).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9afa52e1369524e0386624d083860e3c8027022957cba72cb7d1bbfde5681dde'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9afa52e1369524e0386624d083860e3c8027022957cba72cb7d1bbfde5681dde', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 344, 'function': 'GoogleDriveConnector._impersonate_user_for_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 344, 'function': '_impersonate_user_for_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.debug(_lineaje_payload)
            get_root_folder_id(drive_service)
        except HttpError as e:
            if e.status_code == 401:
                # fail gracefully, let the other impersonations continue
                # one user without access shouldn't block the entire connector
                _lineaje_payload = f"User '{user_email}' does not have access to the drive APIs."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._impersonate_user_for_retrieval).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:55e28d4c2930cbc32a5fbf14cfe76ba1ad175eb4f614b1fc01a96f445c67dd5e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:55e28d4c2930cbc32a5fbf14cfe76ba1ad175eb4f614b1fc01a96f445c67dd5e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 350, 'function': 'GoogleDriveConnector._impersonate_user_for_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 350, 'function': '_impersonate_user_for_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.warning(_lineaje_payload)
                # mark this user as done so we don't try to retrieve anything for them
                # again
                curr_stage.stage = DriveRetrievalStage.DONE
                return
            raise
        except RefreshError as e:
            _lineaje_payload = f"User '{user_email}' could not refresh their token. Error: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._impersonate_user_for_retrieval).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:643924ff7f57e3f41e6969d0d2bc03c8446d86f1f44722d223d2711059cfa07f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:643924ff7f57e3f41e6969d0d2bc03c8446d86f1f44722d223d2711059cfa07f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 357, 'function': 'GoogleDriveConnector._impersonate_user_for_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 357, 'function': '_impersonate_user_for_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.warning(_lineaje_payload)
            # mark this user as done so we don't try to retrieve anything for them
            # again
            yield RetrievedDriveFile(
                completion_stage=DriveRetrievalStage.DONE,
                drive_file={},
                user_email=user_email,
                error=e,
            )
            curr_stage.stage = DriveRetrievalStage.DONE
            return
        # if we are including my drives, try to get the current user's my
        # drive if any of the following are true:
        # - include_my_drives is true
        # - the current user's email is in the requested emails
        if curr_stage.stage == DriveRetrievalStage.MY_DRIVE_FILES:
            if self.include_my_drives or user_email in self._requested_my_drive_emails:
                self.logger.info(
                    f"Getting all files in my drive as '{user_email}. Resuming: {resuming}. Stage completed until: {curr_stage.completed_until}. Next page token: {curr_stage.next_page_token}"
                )

                for file_or_token in add_retrieval_info(
                    get_all_files_in_my_drive_and_shared(
                        service=drive_service,
                        update_traversed_ids_func=self._update_traversed_parent_ids,
                        field_type=field_type,
                        include_shared_with_me=self.include_files_shared_with_me,
                        max_num_pages=MY_DRIVE_PAGES_PER_CHECKPOINT,
                        start=curr_stage.completed_until if resuming else start,
                        end=end,
                        cache_folders=not bool(curr_stage.completed_until),
                        page_token=curr_stage.next_page_token,
                    ),
                    user_email,
                    DriveRetrievalStage.MY_DRIVE_FILES,
                ):
                    if isinstance(file_or_token, str):
                        _lineaje_payload = f"Done with max num pages for user {user_email}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._impersonate_user_for_retrieval).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:078c9fd63f895a46f57df528d3ec5cc3095311955dcc871dcdb17a6486e6de7a'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:078c9fd63f895a46f57df528d3ec5cc3095311955dcc871dcdb17a6486e6de7a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 394, 'function': 'GoogleDriveConnector._impersonate_user_for_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 394, 'function': '_impersonate_user_for_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        self.logger.debug(_lineaje_payload)
                        checkpoint.completion_map[user_email].next_page_token = file_or_token
                        return  # done with the max num pages, return checkpoint
                    yield file_or_token

            checkpoint.completion_map[user_email].next_page_token = None
            curr_stage.stage = DriveRetrievalStage.SHARED_DRIVE_FILES
            curr_stage.current_folder_or_drive_id = None
            return  # resume from next stage on the next run

        if curr_stage.stage == DriveRetrievalStage.SHARED_DRIVE_FILES:

            def _yield_from_drive(drive_id: str, drive_start: SecondsSinceUnixEpoch | None) -> Iterator[RetrievedDriveFile | str]:
                yield from add_retrieval_info(
                    get_files_in_shared_drive(
                        service=drive_service,
                        drive_id=drive_id,
                        field_type=field_type,
                        max_num_pages=SHARED_DRIVE_PAGES_PER_CHECKPOINT,
                        update_traversed_ids_func=self._update_traversed_parent_ids,
                        cache_folders=not bool(drive_start),  # only cache folders for 0 or None
                        start=drive_start,
                        end=end,
                        page_token=curr_stage.next_page_token,
                    ),
                    user_email,
                    DriveRetrievalStage.SHARED_DRIVE_FILES,
                    parent_id=drive_id,
                )

            # resume from a checkpoint
            if resuming and (drive_id := curr_stage.current_folder_or_drive_id):
                resume_start = curr_stage.completed_until
                for file_or_token in _yield_from_drive(drive_id, resume_start):
                    if isinstance(file_or_token, str):
                        checkpoint.completion_map[user_email].next_page_token = file_or_token
                        return  # done with the max num pages, return checkpoint
                    yield file_or_token

            drive_id = get_new_drive_id(user_email)
            if drive_id:
                _lineaje_payload = f"Getting files in shared drive '{drive_id}' as '{user_email}. Resuming: {resuming}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._yield_from_drive).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:75780adb242862df88618cf19bf055dfa9215e59edd13c4c524e935be1b56525'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:75780adb242862df88618cf19bf055dfa9215e59edd13c4c524e935be1b56525', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 435, 'function': 'GoogleDriveConnector._impersonate_user_for_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 435, 'function': '_yield_from_drive', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.info(_lineaje_payload)
                curr_stage.completed_until = 0
                curr_stage.current_folder_or_drive_id = drive_id
                for file_or_token in _yield_from_drive(drive_id, start):
                    if isinstance(file_or_token, str):
                        checkpoint.completion_map[user_email].next_page_token = file_or_token
                        return  # done with the max num pages, return checkpoint
                    yield file_or_token
                curr_stage.current_folder_or_drive_id = None
                return  # get a new drive id on the next run

            checkpoint.completion_map[user_email].next_page_token = None
            curr_stage.stage = DriveRetrievalStage.FOLDER_FILES
            curr_stage.current_folder_or_drive_id = None
            return  # resume from next stage on the next run

        # In the folder files section of service account retrieval we take extra care
        # to not retrieve duplicate docs. In particular, we only add a folder to
        # retrieved_folder_and_drive_ids when all users are finished retrieving files
        # from that folder, and maintain a set of all file ids that have been retrieved
        # for each folder. This might get rather large; in practice we assume that the
        # specific folders users choose to index don't have too many files.
        if curr_stage.stage == DriveRetrievalStage.FOLDER_FILES:

            def _yield_from_folder_crawl(folder_id: str, folder_start: SecondsSinceUnixEpoch | None) -> Iterator[RetrievedDriveFile]:
                for retrieved_file in crawl_folders_for_files(
                    service=drive_service,
                    parent_id=folder_id,
                    field_type=field_type,
                    user_email=user_email,
                    traversed_parent_ids=self._retrieved_folder_and_drive_ids,
                    update_traversed_ids_func=self._update_traversed_parent_ids,
                    start=folder_start,
                    end=end,
                ):
                    yield retrieved_file

            # resume from a checkpoint
            last_processed_folder = None
            if resuming:
                folder_id = curr_stage.current_folder_or_drive_id
                if folder_id is None:
                    _lineaje_payload = f"folder id not set in checkpoint for user {user_email}. This happens occasionally when the connector is interrupted and resumed."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._yield_from_folder_crawl).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:1927f0e56e9ae6e0fcaba4030331512017cb0e7de81da311a8ff7832a430cb42'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1927f0e56e9ae6e0fcaba4030331512017cb0e7de81da311a8ff7832a430cb42', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 477, 'function': 'GoogleDriveConnector._impersonate_user_for_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 477, 'function': '_yield_from_folder_crawl', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    self.logger.warning(_lineaje_payload)
                else:
                    resume_start = curr_stage.completed_until
                    yield from _yield_from_folder_crawl(folder_id, resume_start)
                last_processed_folder = folder_id

            skipping_seen_folders = last_processed_folder is not None
            # NOTE: this assumes a small number of folders to crawl. If someone
            # really wants to specify a large number of folders, we should use
            # binary search to find the first unseen folder.
            num_completed_folders = 0
            for folder_id in sorted_filtered_folder_ids:
                if skipping_seen_folders:
                    skipping_seen_folders = folder_id != last_processed_folder
                    continue

                if folder_id in self._retrieved_folder_and_drive_ids:
                    continue

                curr_stage.completed_until = 0
                curr_stage.current_folder_or_drive_id = folder_id

                if num_completed_folders >= FOLDERS_PER_CHECKPOINT:
                    return  # resume from this folder on the next run

                _lineaje_payload = f"Getting files in folder '{folder_id}' as '{user_email}'"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._yield_from_folder_crawl).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f45366cb6f6016e129935ce5d96b926e9fcdc02e9c15c3ab17d819fa9782fb03'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f45366cb6f6016e129935ce5d96b926e9fcdc02e9c15c3ab17d819fa9782fb03', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 502, 'function': 'GoogleDriveConnector._impersonate_user_for_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 502, 'function': '_yield_from_folder_crawl', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.info(_lineaje_payload)
                yield from _yield_from_folder_crawl(folder_id, start)
                num_completed_folders += 1

        curr_stage.stage = DriveRetrievalStage.DONE

    def _manage_service_account_retrieval(
        self,
        field_type: DriveFileFieldType,
        checkpoint: GoogleDriveCheckpoint,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
    ) -> Iterator[RetrievedDriveFile]:
        """
        The current implementation of the service account retrieval does some
        initial setup work using the primary admin email, then runs MAX_DRIVE_WORKERS
        concurrent threads, each of which impersonates a different user and retrieves
        files for that user. Technically, the actual work each thread does is "yield the
        next file retrieved by the user", at which point it returns to the thread pool;
        see parallel_yield for more details.
        """
        if checkpoint.completion_stage == DriveRetrievalStage.START:
            checkpoint.completion_stage = DriveRetrievalStage.USER_EMAILS

        if checkpoint.completion_stage == DriveRetrievalStage.USER_EMAILS:
            all_org_emails: list[str] = self._get_all_user_emails()
            checkpoint.user_emails = all_org_emails
            checkpoint.completion_stage = DriveRetrievalStage.DRIVE_IDS
        else:
            if checkpoint.user_emails is None:
                raise ValueError("user emails not set")
            all_org_emails = checkpoint.user_emails

        sorted_drive_ids, sorted_folder_ids = self._determine_retrieval_ids(checkpoint, DriveRetrievalStage.MY_DRIVE_FILES)

        # Setup initial completion map on first connector run
        for email in all_org_emails:
            # don't overwrite existing completion map on resuming runs
            if email in checkpoint.completion_map:
                continue
            checkpoint.completion_map[email] = StageCompletion(
                stage=DriveRetrievalStage.START,
                completed_until=0,
                processed_drive_ids=set(),
            )

        # we've found all users and drives, now time to actually start
        # fetching stuff
        _lineaje_payload = f"Found {len(all_org_emails)} users to impersonate"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._manage_service_account_retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1570223a1d7298652c834147029751c7e43c703cf397819b2b484cbb854fc40e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1570223a1d7298652c834147029751c7e43c703cf397819b2b484cbb854fc40e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 550, 'function': 'GoogleDriveConnector._manage_service_account_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 550, 'function': '_manage_service_account_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)
        _lineaje_payload = f"Users: {all_org_emails}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._manage_service_account_retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:78b58fed3f942089353614dedb1388306a732acd2d1aa0ca4899af93fe0a1275'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:78b58fed3f942089353614dedb1388306a732acd2d1aa0ca4899af93fe0a1275', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 551, 'function': 'GoogleDriveConnector._manage_service_account_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 551, 'function': '_manage_service_account_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.debug(_lineaje_payload)
        _lineaje_payload = f"Found {len(sorted_drive_ids)} drives to retrieve"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._manage_service_account_retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:4ac872cbe09c6b04b1eb5ee5169efd300349013bf4697e700af4938e937e2bfb'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4ac872cbe09c6b04b1eb5ee5169efd300349013bf4697e700af4938e937e2bfb', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 552, 'function': 'GoogleDriveConnector._manage_service_account_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 552, 'function': '_manage_service_account_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)
        _lineaje_payload = f"Drives: {sorted_drive_ids}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._manage_service_account_retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:4c4381bf1af8bf56fea3425986d18e478fa4ca581f1ddbc27df708293271b391'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4c4381bf1af8bf56fea3425986d18e478fa4ca581f1ddbc27df708293271b391', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 553, 'function': 'GoogleDriveConnector._manage_service_account_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 553, 'function': '_manage_service_account_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.debug(_lineaje_payload)
        _lineaje_payload = f"Found {len(sorted_folder_ids)} folders to retrieve"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._manage_service_account_retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:0e1571496a8576f55bb21f8df6f41c95bccf78bfa5feb90a3398af68b39c109e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0e1571496a8576f55bb21f8df6f41c95bccf78bfa5feb90a3398af68b39c109e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 554, 'function': 'GoogleDriveConnector._manage_service_account_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 554, 'function': '_manage_service_account_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)
        _lineaje_payload = f"Folders: {sorted_folder_ids}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._manage_service_account_retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:2e90961d13ad594b1cdf3648ff915b815d7d9307534daee6f0dbe497c2de31eb'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2e90961d13ad594b1cdf3648ff915b815d7d9307534daee6f0dbe497c2de31eb', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 555, 'function': 'GoogleDriveConnector._manage_service_account_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 555, 'function': '_manage_service_account_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.debug(_lineaje_payload)

        drive_id_getter = self.make_drive_id_getter(sorted_drive_ids, checkpoint)

        # only process emails that we haven't already completed retrieval for
        non_completed_org_emails = [user_email for user_email, stage_completion in checkpoint.completion_map.items() if stage_completion.stage != DriveRetrievalStage.DONE]

        _lineaje_payload = f"Non-completed users remaining: {len(non_completed_org_emails)}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._manage_service_account_retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5caf6e1b311af3c562694ea1a3b6850669fcd83c0625159749274c6929b2a8cc'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5caf6e1b311af3c562694ea1a3b6850669fcd83c0625159749274c6929b2a8cc', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 562, 'function': 'GoogleDriveConnector._manage_service_account_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 562, 'function': '_manage_service_account_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.debug(_lineaje_payload)

        # don't process too many emails before returning a checkpoint. This is
        # to resolve the case where there are a ton of emails that don't have access
        # to the drive APIs. Without this, we could loop through these emails for
        # more than 3 hours, causing a timeout and stalling progress.
        email_batch_takes_us_to_completion = True
        MAX_EMAILS_TO_PROCESS_BEFORE_CHECKPOINTING = MAX_DRIVE_WORKERS
        if len(non_completed_org_emails) > MAX_EMAILS_TO_PROCESS_BEFORE_CHECKPOINTING:
            non_completed_org_emails = non_completed_org_emails[:MAX_EMAILS_TO_PROCESS_BEFORE_CHECKPOINTING]
            email_batch_takes_us_to_completion = False

        user_retrieval_gens = [
            self._impersonate_user_for_retrieval(
                email,
                field_type,
                checkpoint,
                drive_id_getter,
                sorted_folder_ids,
                start,
                end,
            )
            for email in non_completed_org_emails
        ]
        yield from parallel_yield(user_retrieval_gens, max_workers=MAX_DRIVE_WORKERS)

        # if there are more emails to process, don't mark as complete
        if not email_batch_takes_us_to_completion:
            return

        remaining_folders = (set(sorted_drive_ids) | set(sorted_folder_ids)) - self._retrieved_folder_and_drive_ids
        if remaining_folders:
            _lineaje_payload = f"Some folders/drives were not retrieved. IDs: {remaining_folders}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._manage_service_account_retrieval).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0f4d49ad05a1872453ac6c0d127b3194bac3f6a149b97f56305407453b40e007'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0f4d49ad05a1872453ac6c0d127b3194bac3f6a149b97f56305407453b40e007', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 594, 'function': 'GoogleDriveConnector._manage_service_account_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 594, 'function': '_manage_service_account_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.warning(_lineaje_payload)
        if any(checkpoint.completion_map[user_email].stage != DriveRetrievalStage.DONE for user_email in all_org_emails):
            _lineaje_payload = "some users did not complete retrieval, returning checkpoint for another run"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._manage_service_account_retrieval).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:aa803060ba162135b28f1af5d220692f3d81ac109b7057e928343f27b24c1ed6'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aa803060ba162135b28f1af5d220692f3d81ac109b7057e928343f27b24c1ed6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 596, 'function': 'GoogleDriveConnector._manage_service_account_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 596, 'function': '_manage_service_account_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.info(_lineaje_payload)
            return
        checkpoint.completion_stage = DriveRetrievalStage.DONE

    def _determine_retrieval_ids(
        self,
        checkpoint: GoogleDriveCheckpoint,
        next_stage: DriveRetrievalStage,
    ) -> tuple[list[str], list[str]]:
        all_drive_ids = self.get_all_drive_ids()
        sorted_drive_ids: list[str] = []
        sorted_folder_ids: list[str] = []
        if checkpoint.completion_stage == DriveRetrievalStage.DRIVE_IDS:
            if self._requested_shared_drive_ids or self._requested_folder_ids:
                (
                    sorted_drive_ids,
                    sorted_folder_ids,
                ) = _clean_requested_drive_ids(
                    requested_drive_ids=self._requested_shared_drive_ids,
                    requested_folder_ids=self._requested_folder_ids,
                    all_drive_ids_available=all_drive_ids,
                )
            elif self.include_shared_drives:
                sorted_drive_ids = sorted(all_drive_ids)

            checkpoint.drive_ids_to_retrieve = sorted_drive_ids
            checkpoint.folder_ids_to_retrieve = sorted_folder_ids
            checkpoint.completion_stage = next_stage
        else:
            if checkpoint.drive_ids_to_retrieve is None:
                raise ValueError("drive ids to retrieve not set in checkpoint")
            if checkpoint.folder_ids_to_retrieve is None:
                raise ValueError("folder ids to retrieve not set in checkpoint")
            # When loading from a checkpoint, load the previously cached drive and folder ids
            sorted_drive_ids = checkpoint.drive_ids_to_retrieve
            sorted_folder_ids = checkpoint.folder_ids_to_retrieve

        # LINEAJE: runtime guardrail checks `sorted_drive_ids` as it flows from the agent to the user interface, before it leaves the application (in GoogleDriveConnector._determine_retrieval_ids).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `sorted_drive_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5eba540e6892c89762524a4d79a64818783dd6796b137cae3eb492bc6b6f2011'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5eba540e6892c89762524a4d79a64818783dd6796b137cae3eb492bc6b6f2011', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 633, 'function': 'GoogleDriveConnector._determine_retrieval_ids'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 633, 'function': '_determine_retrieval_ids', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            sorted_drive_ids = _gr_client.enforce(_gr_site, sorted_drive_ids, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return sorted_drive_ids, sorted_folder_ids

    def _oauth_retrieval_drives(
        self,
        field_type: DriveFileFieldType,
        drive_service: GoogleDriveService,
        drive_ids_to_retrieve: list[str],
        checkpoint: GoogleDriveCheckpoint,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
    ) -> Iterator[RetrievedDriveFile | str]:
        def _yield_from_drive(drive_id: str, drive_start: SecondsSinceUnixEpoch | None) -> Iterator[RetrievedDriveFile | str]:
            yield from add_retrieval_info(
                get_files_in_shared_drive(
                    service=drive_service,
                    drive_id=drive_id,
                    field_type=field_type,
                    max_num_pages=SHARED_DRIVE_PAGES_PER_CHECKPOINT,
                    cache_folders=not bool(drive_start),  # only cache folders for 0 or None
                    update_traversed_ids_func=self._update_traversed_parent_ids,
                    start=drive_start,
                    end=end,
                    page_token=checkpoint.completion_map[self.primary_admin_email].next_page_token,
                ),
                self.primary_admin_email,
                DriveRetrievalStage.SHARED_DRIVE_FILES,
                parent_id=drive_id,
            )

        # If we are resuming from a checkpoint, we need to finish retrieving the files from the last drive we retrieved
        if checkpoint.completion_map[self.primary_admin_email].stage == DriveRetrievalStage.SHARED_DRIVE_FILES:
            drive_id = checkpoint.completion_map[self.primary_admin_email].current_folder_or_drive_id
            if drive_id is None:
                raise ValueError("drive id not set in checkpoint")
            resume_start = checkpoint.completion_map[self.primary_admin_email].completed_until
            for file_or_token in _yield_from_drive(drive_id, resume_start):
                if isinstance(file_or_token, str):
                    checkpoint.completion_map[self.primary_admin_email].next_page_token = file_or_token
                    return  # done with the max num pages, return checkpoint
                yield file_or_token
            checkpoint.completion_map[self.primary_admin_email].next_page_token = None

        for drive_id in drive_ids_to_retrieve:
            if drive_id in self._retrieved_folder_and_drive_ids:
                _lineaje_payload = f"Skipping drive '{drive_id}' as it has already been retrieved"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._yield_from_drive).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:e6775f69acb9dbcb0777b569f3db5e148135c7e609078f0338c938b5c05f95c2'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e6775f69acb9dbcb0777b569f3db5e148135c7e609078f0338c938b5c05f95c2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 677, 'function': 'GoogleDriveConnector._oauth_retrieval_drives'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 677, 'function': '_yield_from_drive', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.info(_lineaje_payload)
                continue
            _lineaje_payload = f"Getting files in shared drive '{drive_id}' as '{self.primary_admin_email}'"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._yield_from_drive).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6125e0ffdfe799c98cf4beb0d29b9bac983ebc3d9626ac42130b58c27cfb97f3'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6125e0ffdfe799c98cf4beb0d29b9bac983ebc3d9626ac42130b58c27cfb97f3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 679, 'function': 'GoogleDriveConnector._oauth_retrieval_drives'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 679, 'function': '_yield_from_drive', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.info(_lineaje_payload)
            for file_or_token in _yield_from_drive(drive_id, start):
                if isinstance(file_or_token, str):
                    checkpoint.completion_map[self.primary_admin_email].next_page_token = file_or_token
                    return  # done with the max num pages, return checkpoint
                yield file_or_token
            checkpoint.completion_map[self.primary_admin_email].next_page_token = None

    def _oauth_retrieval_folders(
        self,
        field_type: DriveFileFieldType,
        drive_service: GoogleDriveService,
        drive_ids_to_retrieve: set[str],
        folder_ids_to_retrieve: set[str],
        checkpoint: GoogleDriveCheckpoint,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
    ) -> Iterator[RetrievedDriveFile]:
        """
        If there are any remaining folder ids to retrieve found earlier in the
        retrieval process, we recursively descend the file tree and retrieve all
        files in the folder(s).
        """
        # Even if no folders were requested, we still check if any drives were requested
        # that could be folders.
        remaining_folders = folder_ids_to_retrieve - self._retrieved_folder_and_drive_ids

        def _yield_from_folder_crawl(folder_id: str, folder_start: SecondsSinceUnixEpoch | None) -> Iterator[RetrievedDriveFile]:
            yield from crawl_folders_for_files(
                service=drive_service,
                parent_id=folder_id,
                field_type=field_type,
                user_email=self.primary_admin_email,
                traversed_parent_ids=self._retrieved_folder_and_drive_ids,
                update_traversed_ids_func=self._update_traversed_parent_ids,
                start=folder_start,
                end=end,
            )

        # resume from a checkpoint
        # TODO: actually checkpoint folder retrieval. Since we moved towards returning from
        # generator functions to indicate when a checkpoint should be returned, this code
        # shouldn't be used currently. Unfortunately folder crawling is quite difficult to checkpoint
        # effectively (likely need separate folder crawling and file retrieval stages),
        # so we'll revisit this later.
        if checkpoint.completion_map[self.primary_admin_email].stage == DriveRetrievalStage.FOLDER_FILES and (
            folder_id := checkpoint.completion_map[self.primary_admin_email].current_folder_or_drive_id
        ):
            resume_start = checkpoint.completion_map[self.primary_admin_email].completed_until
            yield from _yield_from_folder_crawl(folder_id, resume_start)

        # the times stored in the completion_map aren't used due to the crawling behavior
        # instead, the traversed_parent_ids are used to determine what we have left to retrieve
        for folder_id in remaining_folders:
            _lineaje_payload = f"Getting files in folder '{folder_id}' as '{self.primary_admin_email}'"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._yield_from_folder_crawl).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:651d3cd7400b59fa06c832b1f0a12253f5d5417e08b20925f0ba657a1a7ec98e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:651d3cd7400b59fa06c832b1f0a12253f5d5417e08b20925f0ba657a1a7ec98e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 733, 'function': 'GoogleDriveConnector._oauth_retrieval_folders'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 733, 'function': '_yield_from_folder_crawl', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.info(_lineaje_payload)
            yield from _yield_from_folder_crawl(folder_id, start)

        remaining_folders = (drive_ids_to_retrieve | folder_ids_to_retrieve) - self._retrieved_folder_and_drive_ids
        if remaining_folders:
            _lineaje_payload = f"Some folders/drives were not retrieved. IDs: {remaining_folders}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._yield_from_folder_crawl).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:57ab5c9638c0868506894cc94bfe5e822a656bcbdba4fb2fd5915b26115b3df7'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:57ab5c9638c0868506894cc94bfe5e822a656bcbdba4fb2fd5915b26115b3df7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 738, 'function': 'GoogleDriveConnector._oauth_retrieval_folders'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 738, 'function': '_yield_from_folder_crawl', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.warning(_lineaje_payload)

    def _load_from_checkpoint(
        self,
        start: SecondsSinceUnixEpoch,
        end: SecondsSinceUnixEpoch,
        checkpoint: GoogleDriveCheckpoint,
        include_permissions: bool,
    ) -> CheckpointOutput:
        """
        Entrypoint for the connector; first run is with an empty checkpoint.
        """
        if self._creds is None or self._primary_admin_email is None:
            raise RuntimeError("Credentials missing, should not call this method before calling load_credentials")

        _lineaje_payload = f"Loading from checkpoint with completion stage: {checkpoint.completion_stage},num retrieved ids: {len(checkpoint.all_retrieved_file_ids)}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._load_from_checkpoint).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8c25c92b719b9dc4145fb6c82f0736687f24684dcbe65e170007f7b9a86a6327'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8c25c92b719b9dc4145fb6c82f0736687f24684dcbe65e170007f7b9a86a6327', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 753, 'function': 'GoogleDriveConnector._load_from_checkpoint'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 753, 'function': '_load_from_checkpoint', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)
        checkpoint = copy.deepcopy(checkpoint)
        self._retrieved_folder_and_drive_ids = checkpoint.retrieved_folder_and_drive_ids
        try:
            yield from self._extract_docs_from_google_drive(checkpoint, start, end, include_permissions)
        except Exception as e:
            if MISSING_SCOPES_ERROR_STR in str(e):
                raise PermissionError() from e
            raise e
        checkpoint.retrieved_folder_and_drive_ids = self._retrieved_folder_and_drive_ids

        _lineaje_payload = f"num drive files retrieved: {len(checkpoint.all_retrieved_file_ids)}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._load_from_checkpoint).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1a87fa0c567259b5d07626e40d8324ca6c6b05ea0d0b8d9b25de9d88210c8b7a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1a87fa0c567259b5d07626e40d8324ca6c6b05ea0d0b8d9b25de9d88210c8b7a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 764, 'function': 'GoogleDriveConnector._load_from_checkpoint'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 764, 'function': '_load_from_checkpoint', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(_lineaje_payload)
        if checkpoint.completion_stage == DriveRetrievalStage.DONE:
            checkpoint.has_more = False
        # LINEAJE: runtime guardrail checks `checkpoint` as it flows from the agent to the user interface, before it leaves the application (in GoogleDriveConnector._load_from_checkpoint).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `checkpoint` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f84cdef93cc0b7c8b2050e4f6a428cb3a7a13406328e5066c6808b8320f00ba5'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f84cdef93cc0b7c8b2050e4f6a428cb3a7a13406328e5066c6808b8320f00ba5', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 767, 'function': 'GoogleDriveConnector._load_from_checkpoint'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 767, 'function': '_load_from_checkpoint', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            checkpoint = _gr_client.enforce(_gr_site, checkpoint, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return checkpoint

    def _checkpointed_retrieval(
        self,
        retrieval_method: CredentialedRetrievalMethod,
        field_type: DriveFileFieldType,
        checkpoint: GoogleDriveCheckpoint,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
    ) -> Iterator[RetrievedDriveFile]:
        drive_files = retrieval_method(
            field_type=field_type,
            checkpoint=checkpoint,
            start=start,
            end=end,
        )

        for file in drive_files:
            document_id = onyx_document_id_from_drive_file(file.drive_file)
            _lineaje_payload = f"Updating checkpoint for file: {file.drive_file.get('name')}. Seen: {document_id in checkpoint.all_retrieved_file_ids}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._checkpointed_retrieval).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:8b74952ab9bdf22b2cf7c58a43f6315cc193a1c53b0579aed07339f23904086a'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8b74952ab9bdf22b2cf7c58a43f6315cc193a1c53b0579aed07339f23904086a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 786, 'function': 'GoogleDriveConnector._checkpointed_retrieval'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 786, 'function': '_checkpointed_retrieval', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.debug(_lineaje_payload)
            checkpoint.completion_map[file.user_email].update(
                stage=file.completion_stage,
                completed_until=datetime_from_string(file.drive_file[GoogleFields.MODIFIED_TIME.value]).timestamp(),
                current_folder_or_drive_id=file.parent_id,
            )
            if document_id not in checkpoint.all_retrieved_file_ids:
                checkpoint.all_retrieved_file_ids.add(document_id)
                yield file

    def _oauth_retrieval_all_files(
        self,
        field_type: DriveFileFieldType,
        drive_service: GoogleDriveService,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
        page_token: str | None = None,
    ) -> Iterator[RetrievedDriveFile | str]:
        if not self.include_files_shared_with_me and not self.include_my_drives:
            return

        _lineaje_payload = (f"Getting shared files/my drive files for OAuth "
            f"with include_files_shared_with_me={self.include_files_shared_with_me}, "
            f"include_my_drives={self.include_my_drives}, "
            f"include_shared_drives={self.include_shared_drives}."
            f"Using '{self.primary_admin_email}' as the account.")
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._oauth_retrieval_all_files).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:85ced5c39993282c389ce6a693161f1cf76a5e3f9333e0306088aa5d07fb4f73'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:85ced5c39993282c389ce6a693161f1cf76a5e3f9333e0306088aa5d07fb4f73', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 807, 'function': 'GoogleDriveConnector._oauth_retrieval_all_files'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 807, 'function': '_oauth_retrieval_all_files', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        self.logger.info(
            _lineaje_payload
        )
        yield from add_retrieval_info(
            get_all_files_for_oauth(
                service=drive_service,
                include_files_shared_with_me=self.include_files_shared_with_me,
                include_my_drives=self.include_my_drives,
                include_shared_drives=self.include_shared_drives,
                field_type=field_type,
                max_num_pages=OAUTH_PAGES_PER_CHECKPOINT,
                start=start,
                end=end,
                page_token=page_token,
            ),
            self.primary_admin_email,
            DriveRetrievalStage.OAUTH_FILES,
        )

    def _manage_oauth_retrieval(
        self,
        field_type: DriveFileFieldType,
        checkpoint: GoogleDriveCheckpoint,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
    ) -> Iterator[RetrievedDriveFile]:
        if checkpoint.completion_stage == DriveRetrievalStage.START:
            checkpoint.completion_stage = DriveRetrievalStage.OAUTH_FILES
            checkpoint.completion_map[self.primary_admin_email] = StageCompletion(
                stage=DriveRetrievalStage.START,
                completed_until=0,
                current_folder_or_drive_id=None,
            )

        drive_service = get_drive_service(self.creds, self.primary_admin_email)

        if checkpoint.completion_stage == DriveRetrievalStage.OAUTH_FILES:
            completion = checkpoint.completion_map[self.primary_admin_email]
            all_files_start = start
            # if resuming from a checkpoint
            if completion.stage == DriveRetrievalStage.OAUTH_FILES:
                all_files_start = completion.completed_until

            for file_or_token in self._oauth_retrieval_all_files(
                field_type=field_type,
                drive_service=drive_service,
                start=all_files_start,
                end=end,
                page_token=checkpoint.completion_map[self.primary_admin_email].next_page_token,
            ):
                if isinstance(file_or_token, str):
                    checkpoint.completion_map[self.primary_admin_email].next_page_token = file_or_token
                    return  # done with the max num pages, return checkpoint
                yield file_or_token
            checkpoint.completion_stage = DriveRetrievalStage.DRIVE_IDS
            checkpoint.completion_map[self.primary_admin_email].next_page_token = None
            return  # create a new checkpoint

        all_requested = self.include_files_shared_with_me and self.include_my_drives and self.include_shared_drives
        if all_requested:
            # If all 3 are true, we already yielded from get_all_files_for_oauth
            checkpoint.completion_stage = DriveRetrievalStage.DONE
            return

        sorted_drive_ids, sorted_folder_ids = self._determine_retrieval_ids(checkpoint, DriveRetrievalStage.SHARED_DRIVE_FILES)

        if checkpoint.completion_stage == DriveRetrievalStage.SHARED_DRIVE_FILES:
            for file_or_token in self._oauth_retrieval_drives(
                field_type=field_type,
                drive_service=drive_service,
                drive_ids_to_retrieve=sorted_drive_ids,
                checkpoint=checkpoint,
                start=start,
                end=end,
            ):
                if isinstance(file_or_token, str):
                    checkpoint.completion_map[self.primary_admin_email].next_page_token = file_or_token
                    return  # done with the max num pages, return checkpoint
                yield file_or_token
            checkpoint.completion_stage = DriveRetrievalStage.FOLDER_FILES
            checkpoint.completion_map[self.primary_admin_email].next_page_token = None
            return  # create a new checkpoint

        if checkpoint.completion_stage == DriveRetrievalStage.FOLDER_FILES:
            yield from self._oauth_retrieval_folders(
                field_type=field_type,
                drive_service=drive_service,
                drive_ids_to_retrieve=set(sorted_drive_ids),
                folder_ids_to_retrieve=set(sorted_folder_ids),
                checkpoint=checkpoint,
                start=start,
                end=end,
            )

        checkpoint.completion_stage = DriveRetrievalStage.DONE

    def _fetch_drive_items(
        self,
        field_type: DriveFileFieldType,
        checkpoint: GoogleDriveCheckpoint,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
    ) -> Iterator[RetrievedDriveFile]:
        retrieval_method = self._manage_service_account_retrieval if isinstance(self.creds, ServiceAccountCredentials) else self._manage_oauth_retrieval

        return self._checkpointed_retrieval(
            retrieval_method=retrieval_method,
            field_type=field_type,
            checkpoint=checkpoint,
            start=start,
            end=end,
        )

    def _extract_docs_from_google_drive(
        self,
        checkpoint: GoogleDriveCheckpoint,
        start: SecondsSinceUnixEpoch | None,
        end: SecondsSinceUnixEpoch | None,
        include_permissions: bool,
    ) -> Iterator[Document | ConnectorFailure]:
        """
        Retrieves and converts Google Drive files to documents.
        """
        field_type = DriveFileFieldType.WITH_PERMISSIONS if include_permissions else DriveFileFieldType.STANDARD

        try:
            # Prepare a partial function with the credentials and admin email
            convert_func = partial(
                convert_drive_item_to_document,
                self.creds,
                self.allow_images,
                self.size_threshold,
                (
                    PermissionSyncContext(
                        primary_admin_email=self.primary_admin_email,
                        google_domain=self.google_domain,
                    )
                    if include_permissions
                    else None
                ),
            )
            # Fetch files in batches
            batches_complete = 0
            files_batch: list[RetrievedDriveFile] = []

            def _yield_batch(
                files_batch: list[RetrievedDriveFile],
            ) -> Iterator[Document | ConnectorFailure]:
                nonlocal batches_complete
                # Process the batch using run_functions_tuples_in_parallel
                func_with_args = [
                    (
                        convert_func,
                        (
                            [file.user_email, self.primary_admin_email] + get_file_owners(file.drive_file, self.primary_admin_email),
                            file.drive_file,
                        ),
                    )
                    for file in files_batch
                ]
                results = cast(
                    list[Document | ConnectorFailure | None],
                    run_functions_tuples_in_parallel(func_with_args, max_workers=8),
                )
                _lineaje_payload = f"finished processing batch {batches_complete} with {len(results)} results"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._yield_batch).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:e881dc04ec7236b06ddf1981a136423fbe58fdb8c3661c74a4c3f5154a6c86d0'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e881dc04ec7236b06ddf1981a136423fbe58fdb8c3661c74a4c3f5154a6c86d0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 975, 'function': 'GoogleDriveConnector._extract_docs_from_google_drive'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 975, 'function': '_yield_batch', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.debug(_lineaje_payload)

                docs_and_failures = [result for result in results if result is not None]
                _lineaje_payload = f"batch {batches_complete} has {len(docs_and_failures)} docs or failures"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._yield_batch).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:22540c498d2ef1e797b24277042d38aa49c80058ec68d8bb3fe3d47f50ab8aa4'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:22540c498d2ef1e797b24277042d38aa49c80058ec68d8bb3fe3d47f50ab8aa4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 978, 'function': 'GoogleDriveConnector._extract_docs_from_google_drive'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 978, 'function': '_yield_batch', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.debug(_lineaje_payload)

                if docs_and_failures:
                    yield from docs_and_failures
                    batches_complete += 1
                _lineaje_payload = f"finished yielding batch {batches_complete}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._yield_batch).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:1f9cbf6296a7166c879bd927f5c61744892decca266420d71bf6f41af79f775d'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1f9cbf6296a7166c879bd927f5c61744892decca266420d71bf6f41af79f775d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 983, 'function': 'GoogleDriveConnector._extract_docs_from_google_drive'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 983, 'function': '_yield_batch', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.debug(_lineaje_payload)

            for retrieved_file in self._fetch_drive_items(
                field_type=field_type,
                checkpoint=checkpoint,
                start=start,
                end=end,
            ):
                if retrieved_file.error is None:
                    files_batch.append(retrieved_file)
                    continue

                # handle retrieval errors
                failure_stage = retrieved_file.completion_stage.value
                failure_message = f"retrieval failure during stage: {failure_stage},"
                failure_message += f"user: {retrieved_file.user_email},"
                failure_message += f"parent drive/folder: {retrieved_file.parent_id},"
                failure_message += f"error: {retrieved_file.error}"
                # LINEAJE: runtime guardrail checks `failure_message` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._yield_batch).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `failure_message` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:67c3ab173813528228f91cdb752e32a2e7e2a12d1a701b969ff9b6c0df5ce4f5'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:67c3ab173813528228f91cdb752e32a2e7e2a12d1a701b969ff9b6c0df5ce4f5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 1001, 'function': 'GoogleDriveConnector._extract_docs_from_google_drive'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 1001, 'function': '_yield_batch', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    failure_message = _gr_client.enforce(_gr_site, failure_message, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                self.logger.error(failure_message)
                yield ConnectorFailure(
                    failed_entity=EntityFailure(
                        entity_id=failure_stage,
                    ),
                    failure_message=failure_message,
                    exception=retrieved_file.error,
                )

            yield from _yield_batch(files_batch)
            checkpoint.retrieved_folder_and_drive_ids = self._retrieved_folder_and_drive_ids

        except Exception as e:
            _lineaje_payload = f"Error extracting documents from Google Drive: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector._extract_docs_from_google_drive).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:27e9a0cd32416000db27dd43d990c86f012f6035380e3295d01d3c1e5a57b1ee'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:27e9a0cd32416000db27dd43d990c86f012f6035380e3295d01d3c1e5a57b1ee', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 1014, 'function': 'GoogleDriveConnector._extract_docs_from_google_drive'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 1014, 'function': '_extract_docs_from_google_drive', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.exception(_lineaje_payload)
            raise e

    @override
    def load_from_checkpoint(
        self,
        start: SecondsSinceUnixEpoch,
        end: SecondsSinceUnixEpoch,
        checkpoint: GoogleDriveCheckpoint,
    ) -> CheckpointOutput:
        return self._load_from_checkpoint(start, end, checkpoint, include_permissions=False)

    @override
    def load_from_checkpoint_with_perm_sync(
        self,
        start: SecondsSinceUnixEpoch,
        end: SecondsSinceUnixEpoch,
        checkpoint: GoogleDriveCheckpoint,
    ) -> CheckpointOutput:
        return self._load_from_checkpoint(start, end, checkpoint, include_permissions=True)

    def _extract_slim_docs_from_google_drive(
        self,
        checkpoint: GoogleDriveCheckpoint,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
        callback: IndexingHeartbeatInterface | None = None,
    ) -> GenerateSlimDocumentOutput:
        slim_batch = []
        for file in self._fetch_drive_items(
            field_type=DriveFileFieldType.SLIM,
            checkpoint=checkpoint,
            start=start,
            end=end,
        ):
            if file.error is not None:
                raise file.error
            if doc := build_slim_document(
                self.creds,
                file.drive_file,
                # for now, always fetch permissions for slim runs
                # TODO: move everything to load_from_checkpoint
                # and only fetch permissions if needed
                PermissionSyncContext(
                    primary_admin_email=self.primary_admin_email,
                    google_domain=self.google_domain,
                ),
            ):
                slim_batch.append(doc)
            if len(slim_batch) >= SLIM_BATCH_SIZE:
                yield slim_batch
                slim_batch = []
                if callback:
                    if callback.should_stop():
                        raise RuntimeError("_extract_slim_docs_from_google_drive: Stop signal detected")
                    callback.progress("_extract_slim_docs_from_google_drive", 1)
        yield slim_batch

    def retrieve_all_slim_docs_perm_sync(
        self,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
        callback: IndexingHeartbeatInterface | None = None,
    ) -> GenerateSlimDocumentOutput:
        try:
            checkpoint = self.build_dummy_checkpoint()
            while checkpoint.completion_stage != DriveRetrievalStage.DONE:
                yield from self._extract_slim_docs_from_google_drive(
                    checkpoint=checkpoint,
                    start=start,
                    end=end,
                )
            _lineaje_payload = "Drive perm sync: Slim doc retrieval complete"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleDriveConnector.retrieve_all_slim_docs_perm_sync).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:7a113ac07e852b55ef3b498df7d49e09d17ef78e03ddc80c5d367cb6bf6c3bce'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7a113ac07e852b55ef3b498df7d49e09d17ef78e03ddc80c5d367cb6bf6c3bce', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/connector.py', 'line': 1086, 'function': 'GoogleDriveConnector.retrieve_all_slim_docs_perm_sync'}, 'file': 'common/data_source/google_drive/connector.py', 'line': 1086, 'function': 'retrieve_all_slim_docs_perm_sync', 'agent_name': 'GoogleDriveConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.info(_lineaje_payload)

        except Exception as e:
            if MISSING_SCOPES_ERROR_STR in str(e):
                raise PermissionError() from e
            raise e

    def validate_connector_settings(self) -> None:
        if self._creds is None:
            raise ConnectorMissingCredentialError("Google Drive credentials not loaded.")

        if self._primary_admin_email is None:
            raise ConnectorValidationError("Primary admin email not found in credentials. Ensure DB_CREDENTIALS_PRIMARY_ADMIN_KEY is set.")

        try:
            drive_service = get_drive_service(self._creds, self._primary_admin_email)
            drive_service.files().list(pageSize=1, fields="files(id)").execute()

            if isinstance(self._creds, ServiceAccountCredentials):
                # default is ~17mins of retries, don't do that here since this is called from
                # the UI
                get_root_folder_id(drive_service)

        except HttpError as e:
            status_code = e.resp.status if e.resp else None
            if status_code == 401:
                raise CredentialExpiredError("Invalid or expired Google Drive credentials (401).")
            elif status_code == 403:
                raise InsufficientPermissionsError("Google Drive app lacks required permissions (403). Please ensure the necessary scopes are granted and Drive apps are enabled.")
            else:
                raise ConnectorValidationError(f"Unexpected Google Drive error (status={status_code}): {e}")

        except Exception as e:
            # Check for scope-related hints from the error message
            if MISSING_SCOPES_ERROR_STR in str(e):
                raise InsufficientPermissionsError("Google Drive credentials are missing required scopes.")
            raise ConnectorValidationError(f"Unexpected error during Google Drive validation: {e}")

    @override
    def build_dummy_checkpoint(self) -> GoogleDriveCheckpoint:
        return GoogleDriveCheckpoint(
            retrieved_folder_and_drive_ids=set(),
            completion_stage=DriveRetrievalStage.START,
            completion_map=ThreadSafeDict(),
            all_retrieved_file_ids=set(),
            has_more=True,
        )

    @override
    def validate_checkpoint_json(self, checkpoint_json: str) -> GoogleDriveCheckpoint:
        return GoogleDriveCheckpoint.model_validate_json(checkpoint_json)


class CheckpointOutputWrapper:
    """
    Wraps a CheckpointOutput generator to give things back in a more digestible format.
    The connector format is easier for the connector implementor (e.g. it enforces exactly
    one new checkpoint is returned AND that the checkpoint is at the end), thus the different
    formats.
    """

    def __init__(self) -> None:
        self.next_checkpoint: GoogleDriveCheckpoint | None = None

    def __call__(
        self,
        checkpoint_connector_generator: CheckpointOutput,
    ) -> Generator[
        tuple[Document | None, ConnectorFailure | None, GoogleDriveCheckpoint | None],
        None,
        None,
    ]:
        # grabs the final return value and stores it in the `next_checkpoint` variable
        def _inner_wrapper(
            checkpoint_connector_generator: CheckpointOutput,
        ) -> CheckpointOutput:
            self.next_checkpoint = yield from checkpoint_connector_generator
            return self.next_checkpoint  # not used

        for document_or_failure in _inner_wrapper(checkpoint_connector_generator):
            if isinstance(document_or_failure, Document):
                yield document_or_failure, None, None
            elif isinstance(document_or_failure, ConnectorFailure):
                yield None, document_or_failure, None
            else:
                raise ValueError(f"Invalid document_or_failure type: {type(document_or_failure)}")

        if self.next_checkpoint is None:
            raise RuntimeError("Checkpoint is None. This should never happen - the connector should always return a checkpoint.")

        yield None, None, self.next_checkpoint


def yield_all_docs_from_checkpoint_connector(
    connector: GoogleDriveConnector,
    start: SecondsSinceUnixEpoch,
    end: SecondsSinceUnixEpoch,
) -> Iterator[Document | ConnectorFailure]:
    num_iterations = 0

    checkpoint = connector.build_dummy_checkpoint()
    while checkpoint.has_more:
        doc_batch_generator = CheckpointOutputWrapper()(connector.load_from_checkpoint(start, end, checkpoint))
        for document, failure, next_checkpoint in doc_batch_generator:
            if failure is not None:
                yield failure
            if document is not None:
                yield document
            if next_checkpoint is not None:
                checkpoint = next_checkpoint

        num_iterations += 1
        if num_iterations > 100_000:
            raise RuntimeError("Too many iterations. Infinite loop?")


if __name__ == "__main__":
    import time
    from common.data_source.google_util.util import get_credentials_from_env
    logging.basicConfig(level=logging.DEBUG)

    try:
        # Get credentials from environment
        email = os.environ.get("GOOGLE_DRIVE_PRIMARY_ADMIN_EMAIL", "yongtengrey@gmail.com")
        creds = get_credentials_from_env(email, oauth=True)
        print("Credentials loaded successfully")
        print(f"{creds=}")
        # sys.exit(0)
        connector = GoogleDriveConnector(
            include_shared_drives=False,
            shared_drive_urls=None,
            include_my_drives=True,
            my_drive_emails="yongtengrey@gmail.com",
            shared_folder_urls="https://drive.google.com/drive/folders/1fAKwbmf3U2oM139ZmnOzgIZHGkEwnpfy",
            include_files_shared_with_me=False,
            specific_user_emails=None,
        )
        print("GoogleDriveConnector initialized successfully")
        connector.load_credentials(creds)
        print("Credentials loaded into connector successfully")

        print("Google Drive connector is ready to use!")
        max_fsize = 0
        biggest_fsize = 0
        num_errors = 0
        docs_processed = 0
        start_time = time.time()
        with open("stats.txt", "w") as f:
            for num, doc_or_failure in enumerate(yield_all_docs_from_checkpoint_connector(connector, 0, time.time())):
                if num % 200 == 0:
                    f.write(f"Processed {num} files\n")
                    f.write(f"Max file size: {max_fsize / 1000_000:.2f} MB\n")
                    f.write(f"Time so far: {time.time() - start_time:.2f} seconds\n")
                    f.write(f"Docs per minute: {num / (time.time() - start_time) * 60:.2f}\n")
                    biggest_fsize = max(biggest_fsize, max_fsize)
                if isinstance(doc_or_failure, Document):
                    docs_processed += 1
                    max_fsize = max(max_fsize, doc_or_failure.size_bytes)
                    print(f"{doc_or_failure=}")
                elif isinstance(doc_or_failure, ConnectorFailure):
                    num_errors += 1
            print(f"Num errors: {num_errors}")
            print(f"Biggest file size: {biggest_fsize / 1000_000:.2f} MB")
            print(f"Time taken: {time.time() - start_time:.2f} seconds")
            print(f"Total documents produced: {docs_processed}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
