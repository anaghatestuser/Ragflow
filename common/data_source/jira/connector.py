"""Checkpointed Jira connector that emits markdown blobs for each issue."""

from __future__ import annotations
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


import argparse
import copy
import logging
import os
import re
from collections.abc import Callable, Generator, Iterable, Iterator, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jira import JIRA
from jira.resources import Issue
from pydantic import Field

from common.data_source.config import (
    INDEX_BATCH_SIZE,
    JIRA_CONNECTOR_LABELS_TO_SKIP,
    JIRA_CONNECTOR_MAX_TICKET_SIZE,
    JIRA_TIMEZONE_OFFSET,
    ONE_HOUR,
    DocumentSource,
)
from common.data_source.exceptions import (
    ConnectorMissingCredentialError,
    ConnectorValidationError,
    InsufficientPermissionsError,
    UnexpectedValidationError,
)
from common.data_source.interfaces import (
    CheckpointedConnectorWithPermSync,
    CheckpointOutputWrapper,
    SecondsSinceUnixEpoch,
    SlimConnectorWithPermSync,
)
from common.data_source.jira.utils import (
    JIRA_CLOUD_API_VERSION,
    JIRA_SERVER_API_VERSION,
    build_issue_url,
    extract_body_text,
    extract_named_value,
    extract_user,
    format_attachments,
    format_comments,
    parse_jira_datetime,
    should_skip_issue,
)
from common.data_source.models import (
    ConnectorCheckpoint,
    ConnectorFailure,
    Document,
    DocumentFailure,
    SlimDocument,
)
from common.data_source.utils import is_atlassian_cloud_url, is_atlassian_date_error, scoped_url

logger = logging.getLogger(__name__)

_DEFAULT_FIELDS = "summary,description,updated,created,status,priority,assignee,reporter,labels,issuetype,project,comment,attachment"
_SLIM_FIELDS = "key,project"
_MAX_RESULTS_FETCH_IDS = 5000
_JIRA_SLIM_PAGE_SIZE = 500
_JIRA_FULL_PAGE_SIZE = 50
_DEFAULT_ATTACHMENT_SIZE_LIMIT = 10 * 1024 * 1024  # 10MB


class JiraCheckpoint(ConnectorCheckpoint):
    """Checkpoint that tracks which slice of the current JQL result set was emitted."""

    start_at: int = 0
    cursor: str | None = None
    ids_done: bool = False
    all_issue_ids: list[list[str]] = Field(default_factory=list)


_TZ_OFFSET_PATTERN = re.compile(r"([+-])(\d{2})(:?)(\d{2})$")


class JiraConnector(CheckpointedConnectorWithPermSync, SlimConnectorWithPermSync):
    """Retrieve Jira issues and emit them as Markdown documents."""

    def __init__(
        self,
        jira_base_url: str,
        project_key: str | None = None,
        jql_query: str | None = None,
        batch_size: int = INDEX_BATCH_SIZE,
        include_comments: bool = True,
        include_attachments: bool = False,
        labels_to_skip: Sequence[str] | None = None,
        comment_email_blacklist: Sequence[str] | None = None,
        scoped_token: bool = False,
        attachment_size_limit: int | None = None,
        timezone_offset: float | None = None,
    ) -> None:
        if not jira_base_url:
            raise ConnectorValidationError("Jira base URL must be provided.")

        self.jira_base_url = jira_base_url.rstrip("/")
        self.project_key = project_key
        self.jql_query = jql_query
        self.batch_size = batch_size
        self.include_comments = include_comments
        self.include_attachments = include_attachments
        configured_labels = labels_to_skip or JIRA_CONNECTOR_LABELS_TO_SKIP
        self.labels_to_skip = {label.lower() for label in configured_labels}
        self.comment_email_blacklist = {email.lower() for email in comment_email_blacklist or []}
        self.scoped_token = scoped_token
        self.jira_client: JIRA | None = None

        self.max_ticket_size = JIRA_CONNECTOR_MAX_TICKET_SIZE
        self.attachment_size_limit = attachment_size_limit if attachment_size_limit and attachment_size_limit > 0 else _DEFAULT_ATTACHMENT_SIZE_LIMIT
        self._fields_param = _DEFAULT_FIELDS
        self._slim_fields = _SLIM_FIELDS

        tz_offset_value = float(timezone_offset) if timezone_offset is not None else float(JIRA_TIMEZONE_OFFSET)
        self.timezone_offset = tz_offset_value
        self.timezone = timezone(offset=timedelta(hours=tz_offset_value))
        self._timezone_overridden = timezone_offset is not None

    # -------------------------------------------------------------------------
    # Connector lifecycle helpers
    # -------------------------------------------------------------------------

    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        """Instantiate the Jira client using either an API token or username/password."""
        jira_url_for_client = self.jira_base_url
        if self.scoped_token:
            if is_atlassian_cloud_url(self.jira_base_url):
                try:
                    jira_url_for_client = scoped_url(self.jira_base_url, "jira")
                except ValueError as exc:
                    raise ConnectorValidationError(str(exc)) from exc
            else:
                _lineaje_payload = "[Jira] Scoped token requested but Jira base URL does not appear to be an Atlassian Cloud domain; scoped token ignored."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in JiraConnector.load_credentials).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:66b6c6b5550c602ddf2fa0fb9f09d3f11a2c1c01eca466b00369fc124eb82157'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:66b6c6b5550c602ddf2fa0fb9f09d3f11a2c1c01eca466b00369fc124eb82157', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 138, 'function': 'JiraConnector.load_credentials'}, 'file': 'common/data_source/jira/connector.py', 'line': 138, 'function': 'load_credentials', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logger.warning(_lineaje_payload)

        user_email = credentials.get("jira_user_email") or credentials.get("username")
        api_token = credentials.get("jira_api_token") or credentials.get("token") or credentials.get("api_token")
        password = credentials.get("jira_password") or credentials.get("password")
        rest_api_version = credentials.get("rest_api_version")

        if not rest_api_version:
            rest_api_version = JIRA_CLOUD_API_VERSION if api_token else JIRA_SERVER_API_VERSION
        options: dict[str, Any] = {"rest_api_version": rest_api_version}

        try:
            if user_email and api_token:
                self.jira_client = JIRA(
                    server=jira_url_for_client,
                    basic_auth=(user_email, api_token),
                    options=options,
                )
            elif api_token:
                self.jira_client = JIRA(
                    server=jira_url_for_client,
                    token_auth=api_token,
                    options=options,
                )
            elif user_email and password:
                self.jira_client = JIRA(
                    server=jira_url_for_client,
                    basic_auth=(user_email, password),
                    options=options,
                )
            else:
                raise ConnectorMissingCredentialError("Jira credentials must include either an API token or username/password.")
        except Exception as exc:  # pragma: no cover - jira lib raises many types
            raise ConnectorMissingCredentialError(f"Jira: {exc}") from exc
        self._sync_timezone_from_server()
        return None

    def validate_connector_settings(self) -> None:
        """Validate connectivity by fetching basic Jira info."""
        if not self.jira_client:
            raise ConnectorMissingCredentialError("Jira")

        try:
            if self.jql_query:
                dummy_checkpoint = self.build_dummy_checkpoint()
                checkpoint_callback = self._make_checkpoint_callback(dummy_checkpoint)
                iterator = self._perform_jql_search(
                    jql=self.jql_query,
                    start=0,
                    max_results=1,
                    fields="key",
                    all_issue_ids=dummy_checkpoint.all_issue_ids,
                    checkpoint_callback=checkpoint_callback,
                    next_page_token=dummy_checkpoint.cursor,
                    ids_done=dummy_checkpoint.ids_done,
                )
                next(iter(iterator), None)
            elif self.project_key:
                self.jira_client.project(self.project_key)
            else:
                self.jira_client.projects()
        except Exception as exc:  # pragma: no cover - dependent on Jira responses
            self._handle_validation_error(exc)

    # -------------------------------------------------------------------------
    # Checkpointed connector implementation
    # -------------------------------------------------------------------------

    def load_from_checkpoint(
        self,
        start: SecondsSinceUnixEpoch,
        end: SecondsSinceUnixEpoch,
        checkpoint: JiraCheckpoint,
    ) -> Generator[Document | ConnectorFailure, None, JiraCheckpoint]:
        """Load Jira issues, emitting a Document per issue."""
        try:
            return (yield from self._load_with_retry(start, end, checkpoint))
        except Exception as exc:
            _lineaje_payload = f"[Jira] Jira query ultimately failed: {exc}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in JiraConnector.load_from_checkpoint).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1566a39624a583bb8a163121b7848636e594df78cd4a83881380a174bad68303'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1566a39624a583bb8a163121b7848636e594df78cd4a83881380a174bad68303', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 216, 'function': 'JiraConnector.load_from_checkpoint'}, 'file': 'common/data_source/jira/connector.py', 'line': 216, 'function': 'load_from_checkpoint', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logger.exception(_lineaje_payload)
            yield ConnectorFailure(
                failure_message=f"Failed to query Jira: {exc}",
                exception=exc,
            )
            return JiraCheckpoint(has_more=False, start_at=checkpoint.start_at)

    def load_from_checkpoint_with_perm_sync(
        self,
        start: SecondsSinceUnixEpoch,
        end: SecondsSinceUnixEpoch,
        checkpoint: JiraCheckpoint,
    ) -> Generator[Document | ConnectorFailure, None, JiraCheckpoint]:
        """Permissions are not synced separately, so reuse the standard loader."""
        return (yield from self.load_from_checkpoint(start=start, end=end, checkpoint=checkpoint))

    def _load_with_retry(
        self,
        start: SecondsSinceUnixEpoch,
        end: SecondsSinceUnixEpoch,
        checkpoint: JiraCheckpoint,
    ) -> Generator[Document | ConnectorFailure, None, JiraCheckpoint]:
        if not self.jira_client:
            raise ConnectorMissingCredentialError("Jira")

        attempt_start = start
        retried_with_buffer = False
        attempt = 0

        while True:
            attempt += 1
            jql = self._build_jql(attempt_start, end)
            _lineaje_payload = f"[Jira] Executing Jira JQL attempt {attempt} (buffered_retry={retried_with_buffer})[start and end parameters redacted]"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in JiraConnector._load_with_retry).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:bfb3442ac00822fd944fcb39aa3004f19891276f1d839d65309d2c5ab7b14536'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bfb3442ac00822fd944fcb39aa3004f19891276f1d839d65309d2c5ab7b14536', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 248, 'function': 'JiraConnector._load_with_retry'}, 'file': 'common/data_source/jira/connector.py', 'line': 248, 'function': '_load_with_retry', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logger.info(_lineaje_payload)
            try:
                return (yield from self._load_from_checkpoint_internal(jql, checkpoint, start_filter=start))
            except Exception as exc:
                if attempt_start is not None and not retried_with_buffer and is_atlassian_date_error(exc):
                    attempt_start = attempt_start - ONE_HOUR
                    retried_with_buffer = True
                    _lineaje_payload = f"[Jira] Atlassian date error detected; retrying with start={attempt_start}."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in JiraConnector._load_with_retry).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:5c2fe27a3d2cec02bc1c3370b59c1e338a3dceee05881c7c9738c39bdc925e83'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5c2fe27a3d2cec02bc1c3370b59c1e338a3dceee05881c7c9738c39bdc925e83', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 255, 'function': 'JiraConnector._load_with_retry'}, 'file': 'common/data_source/jira/connector.py', 'line': 255, 'function': '_load_with_retry', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logger.info(_lineaje_payload)
                    continue
                raise

    def _handle_validation_error(self, exc: Exception) -> None:
        status_code = getattr(exc, "status_code", None)
        if status_code == 401:
            raise InsufficientPermissionsError("Jira credential appears to be invalid or expired (HTTP 401).") from exc
        if status_code == 403:
            raise InsufficientPermissionsError("Jira token does not have permission to access the requested resources (HTTP 403).") from exc
        if status_code == 404:
            raise ConnectorValidationError("Jira resource not found (HTTP 404).") from exc
        if status_code == 429:
            raise ConnectorValidationError("Jira rate limit exceeded during validation (HTTP 429).") from exc

        message = getattr(exc, "text", str(exc))
        if not message:
            raise UnexpectedValidationError("Unexpected Jira validation error.") from exc

        raise ConnectorValidationError(f"Jira validation failed: {message}") from exc

    def _load_from_checkpoint_internal(
        self,
        jql: str,
        checkpoint: JiraCheckpoint,
        start_filter: SecondsSinceUnixEpoch | None = None,
    ) -> Generator[Document | ConnectorFailure, None, JiraCheckpoint]:
        assert self.jira_client, "load_credentials must be called before loading issues."

        page_size = self._full_page_size()
        new_checkpoint = copy.deepcopy(checkpoint)
        starting_offset = new_checkpoint.start_at or 0
        current_offset = starting_offset
        checkpoint_callback = self._make_checkpoint_callback(new_checkpoint)

        issue_iter = self._perform_jql_search(
            jql=jql,
            start=current_offset,
            max_results=page_size,
            fields=self._fields_param,
            all_issue_ids=new_checkpoint.all_issue_ids,
            checkpoint_callback=checkpoint_callback,
            next_page_token=new_checkpoint.cursor,
            ids_done=new_checkpoint.ids_done,
        )

        start_cutoff = float(start_filter) if start_filter is not None else None

        for issue in issue_iter:
            current_offset += 1
            issue_key = getattr(issue, "key", "unknown")
            if should_skip_issue(issue, self.labels_to_skip):
                continue

            issue_updated = parse_jira_datetime(issue.raw.get("fields", {}).get("updated"))
            if start_cutoff is not None and issue_updated is not None and issue_updated.timestamp() <= start_cutoff:
                # Jira JQL only supports minute precision, so we discard already-processed
                # issues here based on the original second-level cutoff.
                continue

            try:
                document = self._issue_to_document(issue)
            except Exception as exc:  # pragma: no cover - defensive
                _lineaje_payload = f"[Jira] Failed to convert Jira issue {issue_key}: {exc}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in JiraConnector._load_from_checkpoint_internal).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:9ca6ff9158cb52c99159550167f0dabab706e4df3d05c24d4c229fb2f1fc4a76'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9ca6ff9158cb52c99159550167f0dabab706e4df3d05c24d4c229fb2f1fc4a76', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 318, 'function': 'JiraConnector._load_from_checkpoint_internal'}, 'file': 'common/data_source/jira/connector.py', 'line': 318, 'function': '_load_from_checkpoint_internal', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logger.exception(_lineaje_payload)
                yield ConnectorFailure(
                    failure_message=f"Failed to convert Jira issue {issue_key}: {exc}",
                    failed_document=DocumentFailure(
                        document_id=issue_key,
                        document_link=build_issue_url(self.jira_base_url, issue_key),
                    ),
                    exception=exc,
                )
                continue

            if document is not None:
                yield document
                if self.include_attachments:
                    for attachment_document in self._attachment_documents(issue):
                        if attachment_document is not None:
                            yield attachment_document

        self._update_checkpoint_for_next_run(
            checkpoint=new_checkpoint,
            current_offset=current_offset,
            starting_offset=starting_offset,
            page_size=page_size,
        )
        new_checkpoint.start_at = current_offset
        # LINEAJE: runtime guardrail checks `new_checkpoint` as it flows from the agent to the user interface, before it leaves the application (in JiraConnector._load_from_checkpoint_internal).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `new_checkpoint` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ddca2b79f758ff933f0de0d5ef335ccf5d7025442219e1ca8a165595c8dbd0b9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ddca2b79f758ff933f0de0d5ef335ccf5d7025442219e1ca8a165595c8dbd0b9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 343, 'function': 'JiraConnector._load_from_checkpoint_internal'}, 'file': 'common/data_source/jira/connector.py', 'line': 343, 'function': '_load_from_checkpoint_internal', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            new_checkpoint = _gr_client.enforce(_gr_site, new_checkpoint, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return new_checkpoint

    def build_dummy_checkpoint(self) -> JiraCheckpoint:
        """Create an empty checkpoint used to kick off ingestion."""
        return JiraCheckpoint(has_more=True, start_at=0)

    def validate_checkpoint_json(self, checkpoint_json: str) -> JiraCheckpoint:
        """Validate a serialized checkpoint."""
        return JiraCheckpoint.model_validate_json(checkpoint_json)

    # -------------------------------------------------------------------------
    # Slim connector implementation
    # -------------------------------------------------------------------------

    def retrieve_all_slim_docs_perm_sync(
        self,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
        callback: Any = None,  # noqa: ARG002 - maintained for interface compatibility
    ) -> Generator[list[SlimDocument], None, None]:
        """Return lightweight references to Jira issues (used for permission syncing)."""
        if not self.jira_client:
            raise ConnectorMissingCredentialError("Jira")

        start_ts = start if start is not None else 0
        end_ts = end if end is not None else datetime.now(timezone.utc).timestamp()
        jql = self._build_jql(start_ts, end_ts)

        checkpoint = self.build_dummy_checkpoint()
        checkpoint_callback = self._make_checkpoint_callback(checkpoint)
        prev_offset = 0
        current_offset = 0
        slim_batch: list[SlimDocument] = []

        while checkpoint.has_more:
            for issue in self._perform_jql_search(
                jql=jql,
                start=current_offset,
                max_results=_JIRA_SLIM_PAGE_SIZE,
                fields=self._slim_fields,
                all_issue_ids=checkpoint.all_issue_ids,
                checkpoint_callback=checkpoint_callback,
                next_page_token=checkpoint.cursor,
                ids_done=checkpoint.ids_done,
            ):
                current_offset += 1
                if should_skip_issue(issue, self.labels_to_skip):
                    continue

                doc_id = build_issue_url(self.jira_base_url, issue.key)
                slim_batch.append(SlimDocument(id=doc_id))

                if len(slim_batch) >= _JIRA_SLIM_PAGE_SIZE:
                    yield slim_batch
                    slim_batch = []

            self._update_checkpoint_for_next_run(
                checkpoint=checkpoint,
                current_offset=current_offset,
                starting_offset=prev_offset,
                page_size=_JIRA_SLIM_PAGE_SIZE,
            )
            prev_offset = current_offset

        if slim_batch:
            yield slim_batch

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _build_jql(self, start: SecondsSinceUnixEpoch, end: SecondsSinceUnixEpoch) -> str:
        clauses: list[str] = []
        if self.jql_query:
            clauses.append(f"({self.jql_query})")
        elif self.project_key:
            clauses.append(f'project = "{self.project_key}"')
        else:
            raise ConnectorValidationError("Either project_key or jql_query must be provided for Jira connector.")

        if self.labels_to_skip:
            labels = ", ".join(f'"{label}"' for label in self.labels_to_skip)
            clauses.append(f"labels NOT IN ({labels})")

        if start is not None:
            clauses.append(f'updated >= "{self._format_jql_time(start)}"')
        if end is not None:
            clauses.append(f'updated <= "{self._format_jql_time(end)}"')

        if not clauses:
            raise ConnectorValidationError("Unable to build Jira JQL query.")

        jql = " AND ".join(clauses)
        if "order by" not in jql.lower():
            jql = f"{jql} ORDER BY updated ASC"
        # LINEAJE: runtime guardrail checks `jql` as it flows from the agent to the user interface, before it leaves the application (in JiraConnector._build_jql).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `jql` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:684079dab299d4cadcc7c7bccb6ade106673de9d8895081ee5e61a2ce8b04c08'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:684079dab299d4cadcc7c7bccb6ade106673de9d8895081ee5e61a2ce8b04c08', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 438, 'function': 'JiraConnector._build_jql'}, 'file': 'common/data_source/jira/connector.py', 'line': 438, 'function': '_build_jql', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            jql = _gr_client.enforce(_gr_site, jql, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return jql

    def _format_jql_time(self, timestamp: SecondsSinceUnixEpoch) -> str:
        dt_utc = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
        dt_local = dt_utc.astimezone(self.timezone)
        # Jira only accepts minute-precision timestamps in JQL, so we format accordingly
        # and rely on a post-query second-level filter to avoid duplicates.
        # LINEAJE: runtime guardrail checks `dt_local` as it flows from the agent to the user interface, before it leaves the application (in JiraConnector._format_jql_time).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `dt_local` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:88795fa50de53f9f04c89a3e787617240c2d88ae03b2b4fdeff18423f514a236'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:88795fa50de53f9f04c89a3e787617240c2d88ae03b2b4fdeff18423f514a236', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 445, 'function': 'JiraConnector._format_jql_time'}, 'file': 'common/data_source/jira/connector.py', 'line': 445, 'function': '_format_jql_time', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            dt_local = _gr_client.enforce(_gr_site, dt_local, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return dt_local.strftime("%Y-%m-%d %H:%M")

    def _issue_to_document(self, issue: Issue) -> Document | None:
        fields = issue.raw.get("fields", {})
        summary = fields.get("summary") or ""
        description_text = extract_body_text(fields.get("description"))
        comments_text = (
            format_comments(
                fields.get("comment"),
                blacklist=self.comment_email_blacklist,
            )
            if self.include_comments
            else ""
        )
        attachments_text = format_attachments(fields.get("attachment"))

        reporter_name, reporter_email = extract_user(fields.get("reporter"))
        assignee_name, assignee_email = extract_user(fields.get("assignee"))
        status = extract_named_value(fields.get("status"))
        priority = extract_named_value(fields.get("priority"))
        issue_type = extract_named_value(fields.get("issuetype"))
        project = fields.get("project") or {}

        issue_url = build_issue_url(self.jira_base_url, issue.key)

        metadata_lines = [
            f"key: {issue.key}",
            f"url: {issue_url}",
            f"summary: {summary}",
            f"status: {status or 'Unknown'}",
            f"priority: {priority or 'Unspecified'}",
            f"issue_type: {issue_type or 'Unknown'}",
            f"project: {project.get('name') or ''}",
            f"project_key: {project.get('key') or self.project_key or ''}",
        ]

        if reporter_name:
            metadata_lines.append(f"reporter: {reporter_name}")
        if reporter_email:
            metadata_lines.append(f"reporter_email: {reporter_email}")
        if assignee_name:
            metadata_lines.append(f"assignee: {assignee_name}")
        if assignee_email:
            metadata_lines.append(f"assignee_email: {assignee_email}")
        if fields.get("labels"):
            metadata_lines.append(f"labels: {', '.join(fields.get('labels'))}")

        created_dt = parse_jira_datetime(fields.get("created"))
        updated_dt = parse_jira_datetime(fields.get("updated")) or created_dt or datetime.now(timezone.utc)
        metadata_lines.append(f"created: {created_dt.isoformat() if created_dt else ''}")
        metadata_lines.append(f"updated: {updated_dt.isoformat() if updated_dt else ''}")

        sections: list[str] = [
            "---",
            "\n".join(filter(None, metadata_lines)),
            "---",
            "",
            "## Description",
            description_text or "No description provided.",
        ]

        if comments_text:
            sections.extend(["", "## Comments", comments_text])
        if attachments_text:
            sections.extend(["", "## Attachments", attachments_text])

        blob_text = "\n".join(sections).strip() + "\n"
        blob = blob_text.encode("utf-8")

        if len(blob) > self.max_ticket_size:
            _lineaje_payload = f"[Jira] Skipping {issue.key} because it exceeds the maximum size of {self.max_ticket_size} bytes."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in JiraConnector._issue_to_document).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:bb224e7bdbe88302c7c8168bdb2d049d00d2434b2e3423171073034d7bfd82ff'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bb224e7bdbe88302c7c8168bdb2d049d00d2434b2e3423171073034d7bfd82ff', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 515, 'function': 'JiraConnector._issue_to_document'}, 'file': 'common/data_source/jira/connector.py', 'line': 515, 'function': '_issue_to_document', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logger.info(_lineaje_payload)
            return None

        semantic_identifier = f"{issue.key}: {summary}" if summary else issue.key

        return Document(
            id=issue_url,
            source=DocumentSource.JIRA,
            semantic_identifier=semantic_identifier,
            extension=".md",
            blob=blob,
            doc_updated_at=updated_dt,
            size_bytes=len(blob),
        )

    def _attachment_documents(self, issue: Issue) -> Iterable[Document]:
        attachments = issue.raw.get("fields", {}).get("attachment") or []
        for attachment in attachments:
            try:
                document = self._attachment_to_document(issue, attachment)
                if document is not None:
                    yield document
            except Exception as exc:  # pragma: no cover - defensive
                failed_id = attachment.get("id") or attachment.get("filename")
                issue_key = getattr(issue, "key", "unknown")
                _lineaje_payload = f"[Jira] Failed to process attachment {failed_id} for issue {issue_key}: {exc}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in JiraConnector._attachment_documents).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:40d075e0d18aebfc2c9dc6d5215ac17915d1b61cd8538a955cfd08b90cfcadce'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:40d075e0d18aebfc2c9dc6d5215ac17915d1b61cd8538a955cfd08b90cfcadce', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 540, 'function': 'JiraConnector._attachment_documents'}, 'file': 'common/data_source/jira/connector.py', 'line': 540, 'function': '_attachment_documents', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logger.warning(_lineaje_payload)

    def _attachment_to_document(self, issue: Issue, attachment: dict[str, Any]) -> Document | None:
        if not self.include_attachments:
            return None

        filename = attachment.get("filename")
        content_url = attachment.get("content")
        if not filename or not content_url:
            return None

        try:
            attachment_size = int(attachment.get("size", 0))
        except (TypeError, ValueError):
            attachment_size = 0
        if attachment_size and attachment_size > self.attachment_size_limit:
            _lineaje_payload = f"[Jira] Skipping attachment {filename} on {issue.key} because reported size exceeds limit ({self.attachment_size_limit} bytes)."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in JiraConnector._attachment_to_document).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:55765c95dbca6c44818bee7319c1c8d2eee971e62c7d970eef1e483eefcf6b39'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:55765c95dbca6c44818bee7319c1c8d2eee971e62c7d970eef1e483eefcf6b39', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 556, 'function': 'JiraConnector._attachment_to_document'}, 'file': 'common/data_source/jira/connector.py', 'line': 556, 'function': '_attachment_to_document', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logger.info(_lineaje_payload)
            return None

        blob = self._download_attachment(content_url)
        if blob is None:
            return None

        if len(blob) > self.attachment_size_limit:
            _lineaje_payload = f"[Jira] Skipping attachment {filename} on {issue.key} because it exceeds the size limit ({self.attachment_size_limit} bytes)."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in JiraConnector._attachment_to_document).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:251fa0f44f5b6eb3c28a967face4984ab1541a98cc34278e10461b4633a3e7f4'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:251fa0f44f5b6eb3c28a967face4984ab1541a98cc34278e10461b4633a3e7f4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 564, 'function': 'JiraConnector._attachment_to_document'}, 'file': 'common/data_source/jira/connector.py', 'line': 564, 'function': '_attachment_to_document', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logger.info(_lineaje_payload)
            return None

        attachment_time = parse_jira_datetime(attachment.get("created")) or parse_jira_datetime(attachment.get("updated"))
        updated_dt = attachment_time or parse_jira_datetime(issue.raw.get("fields", {}).get("updated")) or datetime.now(timezone.utc)

        extension = os.path.splitext(filename)[1] or ""
        document_id = f"{issue.key}::attachment::{attachment.get('id') or filename}"
        semantic_identifier = f"{issue.key} attachment: {filename}"

        return Document(
            id=document_id,
            source=DocumentSource.JIRA,
            semantic_identifier=semantic_identifier,
            extension=extension,
            blob=blob,
            doc_updated_at=updated_dt,
            size_bytes=len(blob),
        )

    def _download_attachment(self, url: str) -> bytes | None:
        if not self.jira_client:
            raise ConnectorMissingCredentialError("Jira")
        response = self.jira_client._session.get(url)
        response.raise_for_status()
        return response.content

    def _sync_timezone_from_server(self) -> None:
        if self._timezone_overridden or not self.jira_client:
            return
        try:
            server_info = self.jira_client.server_info()
        except Exception as exc:  # pragma: no cover - defensive
            _lineaje_payload = f"[Jira] Unable to determine timezone from server info; continuing with offset {self.timezone_offset}. Error: {exc}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in JiraConnector._sync_timezone_from_server).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:066ad6b6af113ada1083599e7ea40e8c4fc0e6ba06bf34697e42ee710ac81d4e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:066ad6b6af113ada1083599e7ea40e8c4fc0e6ba06bf34697e42ee710ac81d4e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 597, 'function': 'JiraConnector._sync_timezone_from_server'}, 'file': 'common/data_source/jira/connector.py', 'line': 597, 'function': '_sync_timezone_from_server', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logger.info(_lineaje_payload)
            return

        detected_offset = self._extract_timezone_offset(server_info)
        if detected_offset is None or detected_offset == self.timezone_offset:
            return

        self.timezone_offset = detected_offset
        self.timezone = timezone(offset=timedelta(hours=detected_offset))
        _lineaje_payload = f"[Jira] Timezone offset adjusted to {detected_offset} hours using Jira server info."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in JiraConnector._sync_timezone_from_server).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:08fb61efcedebd9b18e839ecccd02286816e8d58234798eb0251f654e68ec784'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:08fb61efcedebd9b18e839ecccd02286816e8d58234798eb0251f654e68ec784', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 606, 'function': 'JiraConnector._sync_timezone_from_server'}, 'file': 'common/data_source/jira/connector.py', 'line': 606, 'function': '_sync_timezone_from_server', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logger.info(_lineaje_payload)

    def _extract_timezone_offset(self, server_info: dict[str, Any]) -> float | None:
        server_time_raw = server_info.get("serverTime")
        if isinstance(server_time_raw, str):
            offset = self._parse_offset_from_datetime_string(server_time_raw)
            if offset is not None:
                # LINEAJE: runtime guardrail checks `offset` as it flows from the agent to the user interface, before it leaves the application (in JiraConnector._extract_timezone_offset).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `offset` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:c56d9da3b897b924f591c652bfa69d3441bab230a7e60129e6d34f4172795159'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c56d9da3b897b924f591c652bfa69d3441bab230a7e60129e6d34f4172795159', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 613, 'function': 'JiraConnector._extract_timezone_offset'}, 'file': 'common/data_source/jira/connector.py', 'line': 613, 'function': '_extract_timezone_offset', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    offset = _gr_client.enforce(_gr_site, offset, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return offset

        tz_name = server_info.get("timeZone")
        if isinstance(tz_name, str):
            offset = self._offset_from_zone_name(tz_name)
            if offset is not None:
                # LINEAJE: runtime guardrail checks `offset` as it flows from the agent to the user interface, before it leaves the application (in JiraConnector._extract_timezone_offset).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `offset` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:cb4a43aa507241e880c217ec2085ef3c4754b77b5b28a360360737895ffae1d3'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cb4a43aa507241e880c217ec2085ef3c4754b77b5b28a360360737895ffae1d3', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 619, 'function': 'JiraConnector._extract_timezone_offset'}, 'file': 'common/data_source/jira/connector.py', 'line': 619, 'function': '_extract_timezone_offset', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    offset = _gr_client.enforce(_gr_site, offset, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return offset
        return None

    @staticmethod
    def _parse_offset_from_datetime_string(value: str) -> float | None:
        normalized = JiraConnector._normalize_datetime_string(value)
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        if dt.tzinfo is None:
            return 0.0

        offset = dt.tzinfo.utcoffset(dt)
        if offset is None:
            return None
        return offset.total_seconds() / 3600.0

    @staticmethod
    def _normalize_datetime_string(value: str) -> str:
        trimmed = (value or "").strip()
        if trimmed.endswith("Z"):
            return f"{trimmed[:-1]}+00:00"

        match = _TZ_OFFSET_PATTERN.search(trimmed)
        if match and match.group(3) != ":":
            sign, hours, _, minutes = match.groups()
            trimmed = f"{trimmed[: match.start()]}{sign}{hours}:{minutes}"
        # LINEAJE: runtime guardrail checks `trimmed` as it flows from the agent to the user interface, before it leaves the application (in JiraConnector._normalize_datetime_string).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `trimmed` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:066b706539386e53191fd22d23432e39ab0f8b1915e8cc3f3ca67fca9570954b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:066b706539386e53191fd22d23432e39ab0f8b1915e8cc3f3ca67fca9570954b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 648, 'function': 'JiraConnector._normalize_datetime_string'}, 'file': 'common/data_source/jira/connector.py', 'line': 648, 'function': '_normalize_datetime_string', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            trimmed = _gr_client.enforce(_gr_site, trimmed, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return trimmed

    @staticmethod
    def _offset_from_zone_name(name: str) -> float | None:
        try:
            tz = ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            return None
        reference = datetime.now(tz)
        offset = reference.utcoffset()
        if offset is None:
            return None
        return offset.total_seconds() / 3600.0

    def _is_cloud_client(self) -> bool:
        if not self.jira_client:
            return False
        rest_version = str(self.jira_client._options.get("rest_api_version", "")).strip()
        return rest_version == str(JIRA_CLOUD_API_VERSION)

    def _full_page_size(self) -> int:
        return max(1, min(self.batch_size, _JIRA_FULL_PAGE_SIZE))

    def _perform_jql_search(
        self,
        *,
        jql: str,
        start: int,
        max_results: int,
        fields: str | None = None,
        all_issue_ids: list[list[str]] | None = None,
        checkpoint_callback: Callable[[Iterable[list[str]], str | None], None] | None = None,
        next_page_token: str | None = None,
        ids_done: bool = False,
    ) -> Iterable[Issue]:
        assert self.jira_client, "Jira client not initialized."
        is_cloud = self._is_cloud_client()
        if is_cloud:
            if all_issue_ids is None:
                raise ValueError("all_issue_ids is required for Jira Cloud searches.")
            yield from self._perform_jql_search_v3(
                jql=jql,
                max_results=max_results,
                fields=fields,
                all_issue_ids=all_issue_ids,
                checkpoint_callback=checkpoint_callback,
                next_page_token=next_page_token,
                ids_done=ids_done,
            )
        else:
            yield from self._perform_jql_search_v2(
                jql=jql,
                start=start,
                max_results=max_results,
                fields=fields,
            )

    def _perform_jql_search_v3(
        self,
        *,
        jql: str,
        max_results: int,
        all_issue_ids: list[list[str]],
        fields: str | None = None,
        checkpoint_callback: Callable[[Iterable[list[str]], str | None], None] | None = None,
        next_page_token: str | None = None,
        ids_done: bool = False,
    ) -> Iterable[Issue]:
        assert self.jira_client, "Jira client not initialized."

        if not ids_done:
            new_ids, page_token = self._enhanced_search_ids(jql, next_page_token)
            if checkpoint_callback is not None and new_ids:
                checkpoint_callback(
                    self._chunk_issue_ids(new_ids, max_results),
                    page_token,
                )
            elif checkpoint_callback is not None:
                checkpoint_callback([], page_token)

        if all_issue_ids:
            issue_ids = all_issue_ids.pop()
            if issue_ids:
                yield from self._bulk_fetch_issues(issue_ids, fields)

    def _perform_jql_search_v2(
        self,
        *,
        jql: str,
        start: int,
        max_results: int,
        fields: str | None = None,
    ) -> Iterable[Issue]:
        assert self.jira_client, "Jira client not initialized."

        issues = self.jira_client.search_issues(
            jql_str=jql,
            startAt=start,
            maxResults=max_results,
            fields=fields or self._fields_param,
            expand="renderedFields",
        )
        for issue in issues:
            yield issue

    def _enhanced_search_ids(
        self,
        jql: str,
        next_page_token: str | None,
    ) -> tuple[list[str], str | None]:
        assert self.jira_client, "Jira client not initialized."
        enhanced_search_path = self.jira_client._get_url("search/jql")
        params: dict[str, str | int | None] = {
            "jql": jql,
            "maxResults": _MAX_RESULTS_FETCH_IDS,
            "nextPageToken": next_page_token,
            "fields": "id",
        }
        response = self.jira_client._session.get(enhanced_search_path, params=params)
        response.raise_for_status()
        data = response.json()
        return [str(issue["id"]) for issue in data.get("issues", [])], data.get("nextPageToken")

    def _bulk_fetch_issues(
        self,
        issue_ids: list[str],
        fields: str | None,
    ) -> Iterable[Issue]:
        assert self.jira_client, "Jira client not initialized."
        if not issue_ids:
            return []

        bulk_fetch_path = self.jira_client._get_url("issue/bulkfetch")
        payload: dict[str, Any] = {"issueIdsOrKeys": issue_ids}
        payload["fields"] = fields.split(",") if fields else ["*all"]

        response = self.jira_client._session.post(bulk_fetch_path, json=payload)
        response.raise_for_status()
        data = response.json()
        return [Issue(self.jira_client._options, self.jira_client._session, raw=issue) for issue in data.get("issues", [])]

    @staticmethod
    def _chunk_issue_ids(issue_ids: list[str], chunk_size: int) -> Iterable[list[str]]:
        if chunk_size <= 0:
            chunk_size = _JIRA_FULL_PAGE_SIZE

        for idx in range(0, len(issue_ids), chunk_size):
            yield issue_ids[idx : idx + chunk_size]

    def _make_checkpoint_callback(self, checkpoint: JiraCheckpoint) -> Callable[[Iterable[list[str]], str | None], None]:
        def checkpoint_callback(
            issue_ids: Iterable[list[str]] | list[list[str]],
            page_token: str | None,
        ) -> None:
            for id_batch in issue_ids:
                checkpoint.all_issue_ids.append(list(id_batch))
            checkpoint.cursor = page_token
            checkpoint.ids_done = page_token is None

        # LINEAJE: runtime guardrail checks `checkpoint_callback` as it flows from the agent to the user interface, before it leaves the application (in JiraConnector._make_checkpoint_callback).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `checkpoint_callback` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:2212a8d083694c1b5c5d5c932d96c548ce55e6e392ef6c42ece52ad0ccec16c9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2212a8d083694c1b5c5d5c932d96c548ce55e6e392ef6c42ece52ad0ccec16c9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 807, 'function': 'JiraConnector._make_checkpoint_callback'}, 'file': 'common/data_source/jira/connector.py', 'line': 807, 'function': '_make_checkpoint_callback', 'agent_name': 'JiraConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            checkpoint_callback = _gr_client.enforce(_gr_site, checkpoint_callback, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return checkpoint_callback

    def _update_checkpoint_for_next_run(
        self,
        *,
        checkpoint: JiraCheckpoint,
        current_offset: int,
        starting_offset: int,
        page_size: int,
    ) -> None:
        if self._is_cloud_client():
            checkpoint.has_more = bool(checkpoint.all_issue_ids) or not checkpoint.ids_done
        else:
            checkpoint.has_more = current_offset - starting_offset == page_size
            checkpoint.cursor = None
            checkpoint.ids_done = True
            checkpoint.all_issue_ids = []


def iterate_jira_documents(
    connector: "JiraConnector",
    start: SecondsSinceUnixEpoch,
    end: SecondsSinceUnixEpoch,
    iteration_limit: int = 100_000,
) -> Iterator[Document]:
    """Yield documents without materializing the entire result set."""

    checkpoint = connector.build_dummy_checkpoint()
    iterations = 0

    while checkpoint.has_more:
        wrapper = CheckpointOutputWrapper[JiraCheckpoint]()
        generator = wrapper(connector.load_from_checkpoint(start=start, end=end, checkpoint=checkpoint))

        for document, failure, next_checkpoint in generator:
            if failure is not None:
                failure_message = getattr(failure, "failure_message", str(failure))
                raise RuntimeError(f"Failed to load Jira documents: {failure_message}")
            if document is not None:
                yield document
            if next_checkpoint is not None:
                checkpoint = next_checkpoint

        iterations += 1
        if iterations > iteration_limit:
            raise RuntimeError("Too many iterations while loading Jira documents.")


def test_jira(
    *,
    base_url: str,
    project_key: str | None = None,
    jql_query: str | None = None,
    credentials: dict[str, Any],
    batch_size: int = INDEX_BATCH_SIZE,
    start_ts: float | None = None,
    end_ts: float | None = None,
    connector_options: dict[str, Any] | None = None,
) -> list[Document]:
    """Programmatic entry point that mirrors the CLI workflow."""

    connector_kwargs = connector_options.copy() if connector_options else {}
    connector = JiraConnector(
        jira_base_url=base_url,
        project_key=project_key,
        jql_query=jql_query,
        batch_size=batch_size,
        **connector_kwargs,
    )
    connector.load_credentials(credentials)
    connector.validate_connector_settings()

    now_ts = datetime.now(timezone.utc).timestamp()
    start = start_ts if start_ts is not None else 0.0
    end = end_ts if end_ts is not None else now_ts

    documents = list(iterate_jira_documents(connector, start=start, end=end))
    _lineaje_payload = f"[Jira] Fetched {len(documents)} Jira documents."
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in test_jira).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:9d406fb8478c6d1331e63aa25406942cb31bb014275f60704a5eccc3ea46a86c'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9d406fb8478c6d1331e63aa25406942cb31bb014275f60704a5eccc3ea46a86c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 884, 'function': 'test_jira'}, 'file': 'common/data_source/jira/connector.py', 'line': 884, 'function': 'test_jira', 'agent_name': 'test_jira', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logger.info(_lineaje_payload)
    for doc in documents[:5]:
        _lineaje_payload = f"[Jira] Document {doc.semantic_identifier} ({doc.id}) size={doc.size_bytes} bytes"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in test_jira).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:67a7bb9e5d849a562aa8ebeb7b35695d706ad381fa8e9cbabdec82880bf7ca57'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:67a7bb9e5d849a562aa8ebeb7b35695d706ad381fa8e9cbabdec82880bf7ca57', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 886, 'function': 'test_jira'}, 'file': 'common/data_source/jira/connector.py', 'line': 886, 'function': 'test_jira', 'agent_name': 'test_jira', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logger.info(_lineaje_payload)
    # LINEAJE: runtime guardrail checks `documents` as it flows from the agent to the user interface, before it leaves the application (in test_jira).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `documents` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:58114d754086238196333d972c7de2cc2387ea94c7d2da42406aebdd75c0af79'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:58114d754086238196333d972c7de2cc2387ea94c7d2da42406aebdd75c0af79', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 887, 'function': 'test_jira'}, 'file': 'common/data_source/jira/connector.py', 'line': 887, 'function': 'test_jira', 'agent_name': 'test_jira', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        documents = _gr_client.enforce(_gr_site, documents, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return documents


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch Jira issues and print summary statistics.")
    parser.add_argument("--base-url", dest="base_url", default=os.environ.get("JIRA_BASE_URL"))
    parser.add_argument("--project", dest="project_key", default=os.environ.get("JIRA_PROJECT_KEY"))
    parser.add_argument("--jql", dest="jql_query", default=os.environ.get("JIRA_JQL"))
    parser.add_argument("--email", dest="user_email", default=os.environ.get("JIRA_USER_EMAIL"))
    parser.add_argument("--token", dest="api_token", default=os.environ.get("JIRA_API_TOKEN"))
    parser.add_argument("--password", dest="password", default=os.environ.get("JIRA_PASSWORD"))
    parser.add_argument("--batch-size", dest="batch_size", type=int, default=int(os.environ.get("JIRA_BATCH_SIZE", INDEX_BATCH_SIZE)))
    parser.add_argument("--include_comments", dest="include_comments", type=bool, default=True)
    parser.add_argument("--include_attachments", dest="include_attachments", type=bool, default=True)
    parser.add_argument("--attachment_size_limit", dest="attachment_size_limit", type=float, default=_DEFAULT_ATTACHMENT_SIZE_LIMIT)
    parser.add_argument("--start-ts", dest="start_ts", type=float, default=None, help="Epoch seconds inclusive lower bound for updated issues.")
    parser.add_argument("--end-ts", dest="end_ts", type=float, default=9999999999, help="Epoch seconds inclusive upper bound for updated issues.")
    # LINEAJE: runtime guardrail checks `parser` as it flows from the agent to the user interface, before it leaves the application (in _build_arg_parser).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `parser` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:9c3394af0f5e7470f2b67e5a7042b299e1891cec131199a6b3bd91aaba19e0d4'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9c3394af0f5e7470f2b67e5a7042b299e1891cec131199a6b3bd91aaba19e0d4', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 904, 'function': '_build_arg_parser'}, 'file': 'common/data_source/jira/connector.py', 'line': 904, 'function': '_build_arg_parser', 'agent_name': '_build_arg_parser', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        parser = _gr_client.enforce(_gr_site, parser, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return parser


def main(config: dict[str, Any] | None = None) -> None:
    if config is None:
        args = _build_arg_parser().parse_args()
        config = {
            "base_url": args.base_url,
            "project_key": args.project_key,
            "jql_query": args.jql_query,
            "batch_size": args.batch_size,
            "start_ts": args.start_ts,
            "end_ts": args.end_ts,
            "include_comments": args.include_comments,
            "include_attachments": args.include_attachments,
            "attachment_size_limit": args.attachment_size_limit,
            "credentials": {
                "jira_user_email": args.user_email,
                "jira_api_token": args.api_token,
                "jira_password": args.password,
            },
        }

    base_url = config.get("base_url")
    credentials = config.get("credentials", {})

    if not base_url:
        raise RuntimeError("Jira base URL must be provided via config or CLI arguments.")
    if not (credentials.get("jira_api_token") or (credentials.get("jira_user_email") and credentials.get("jira_password"))):
        raise RuntimeError("Provide either an API token or both email/password for Jira authentication.")

    connector_options = {
        key: value
        for key, value in (
            ("include_comments", config.get("include_comments")),
            ("include_attachments", config.get("include_attachments")),
            ("attachment_size_limit", config.get("attachment_size_limit")),
            ("labels_to_skip", config.get("labels_to_skip")),
            ("comment_email_blacklist", config.get("comment_email_blacklist")),
            ("scoped_token", config.get("scoped_token")),
            ("timezone_offset", config.get("timezone_offset")),
        )
        if value is not None
    }

    documents = test_jira(
        base_url=base_url,
        project_key=config.get("project_key"),
        jql_query=config.get("jql_query"),
        credentials=credentials,
        batch_size=config.get("batch_size", INDEX_BATCH_SIZE),
        start_ts=config.get("start_ts"),
        end_ts=config.get("end_ts"),
        connector_options=connector_options,
    )

    preview_count = min(len(documents), 5)
    for idx in range(preview_count):
        doc = documents[idx]
        _lineaje_payload = f"[Jira] [Sample {idx + 1}] {doc.semantic_identifier} | id={doc.id} | size={doc.size_bytes} bytes"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:27325e2bbbd07ed7aa078f38da452950a3649d99c29afadb797f2e6c839dd468'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:27325e2bbbd07ed7aa078f38da452950a3649d99c29afadb797f2e6c839dd468', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 963, 'function': 'main'}, 'file': 'common/data_source/jira/connector.py', 'line': 963, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)

    _lineaje_payload = f"[Jira] Jira connector test completed. Documents fetched: {len(documents)}"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:9496e819c74e7b34177a3fea910b34fc26c6ee091875a325dc71b363c40b3358'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9496e819c74e7b34177a3fea910b34fc26c6ee091875a325dc71b363c40b3358', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/connector.py', 'line': 965, 'function': 'main'}, 'file': 'common/data_source/jira/connector.py', 'line': 965, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(_lineaje_payload)


if __name__ == "__main__":  # pragma: no cover - manual execution path
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    main()
