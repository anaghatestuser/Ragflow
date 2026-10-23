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
from typing import Any
from google.oauth2.credentials import Credentials as OAuthCredentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.errors import HttpError

from common.data_source.config import INDEX_BATCH_SIZE, SLIM_BATCH_SIZE, DocumentSource
from common.data_source.google_util.auth import get_google_creds
from common.data_source.google_util.constant import DB_CREDENTIALS_PRIMARY_ADMIN_KEY, MISSING_SCOPES_ERROR_STR, SCOPE_INSTRUCTIONS, USER_FIELDS
from common.data_source.google_util.resource import get_admin_service, get_gmail_service
from common.data_source.google_util.util import _execute_single_retrieval, execute_paginated_retrieval, sanitize_filename, clean_string
from common.data_source.interfaces import LoadConnector, PollConnector, SecondsSinceUnixEpoch, SlimConnectorWithPermSync
from common.data_source.models import BasicExpertInfo, Document, ExternalAccess, GenerateDocumentsOutput, GenerateSlimDocumentOutput, SlimDocument, TextSection
from common.data_source.utils import build_time_range_query, clean_email_and_extract_name, get_message_body, is_mail_service_disabled_error, gmail_time_str_to_utc

# Constants for Gmail API fields
THREAD_LIST_FIELDS = "nextPageToken, threads(id)"
PARTS_FIELDS = "parts(body(data), mimeType)"
PAYLOAD_FIELDS = f"payload(headers, {PARTS_FIELDS})"
MESSAGES_FIELDS = f"messages(id, {PAYLOAD_FIELDS})"
THREADS_FIELDS = f"threads(id, {MESSAGES_FIELDS})"
THREAD_FIELDS = f"id, {MESSAGES_FIELDS}"

EMAIL_FIELDS = ["cc", "bcc", "from", "to"]


def _get_owners_from_emails(emails: dict[str, str | None]) -> list[BasicExpertInfo]:
    """Convert email dictionary to list of BasicExpertInfo objects."""
    owners = []
    for email, names in emails.items():
        if names:
            name_parts = names.split(" ")
            first_name = " ".join(name_parts[:-1])
            last_name = name_parts[-1]
        else:
            first_name = None
            last_name = None
        owners.append(BasicExpertInfo(email=email, first_name=first_name, last_name=last_name))
    # LINEAJE: runtime guardrail checks `owners` as it flows from the agent to the user interface, before it leaves the application (in _get_owners_from_emails).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `owners` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:2c2146248cde366d7433ece282d3fa64c17587ce33b6f689288f0e4e14ef8f53'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2c2146248cde366d7433ece282d3fa64c17587ce33b6f689288f0e4e14ef8f53', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/gmail_connector.py', 'line': 39, 'function': '_get_owners_from_emails'}, 'file': 'common/data_source/gmail_connector.py', 'line': 39, 'function': '_get_owners_from_emails', 'agent_name': '_get_owners_from_emails', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        owners = _gr_client.enforce(_gr_site, owners, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return owners


def message_to_section(message: dict[str, Any]) -> tuple[TextSection, dict[str, str]]:
    """Convert Gmail message to text section and metadata."""
    link = f"https://mail.google.com/mail/u/0/#inbox/{message['id']}"

    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    metadata: dict[str, Any] = {}

    for header in headers:
        name = header.get("name", "").lower()
        value = header.get("value", "")
        if name in EMAIL_FIELDS:
            metadata[name] = value
        if name == "subject":
            metadata["subject"] = value
        if name == "date":
            metadata["updated_at"] = value

    if labels := message.get("labelIds"):
        metadata["labels"] = labels

    message_data = ""
    for name, value in metadata.items():
        if name != "updated_at":
            message_data += f"{name}: {value}\n"

    message_body_text: str = get_message_body(payload)
    return TextSection(link=link, text=message_body_text + message_data), metadata


def thread_to_document(full_thread: dict[str, Any], email_used_to_fetch_thread: str) -> Document | None:
    """Convert Gmail thread to Document object."""
    all_messages = full_thread.get("messages", [])
    if not all_messages:
        return None

    sections = []
    semantic_identifier = ""
    updated_at = None
    from_emails: dict[str, str | None] = {}
    other_emails: dict[str, str | None] = {}

    for message in all_messages:
        section, message_metadata = message_to_section(message)
        sections.append(section)

        for name, value in message_metadata.items():
            if name in EMAIL_FIELDS:
                email, display_name = clean_email_and_extract_name(value)
                if name == "from":
                    from_emails[email] = display_name if not from_emails.get(email) else None
                else:
                    other_emails[email] = display_name if not other_emails.get(email) else None

        if not semantic_identifier:
            semantic_identifier = message_metadata.get("subject", "")
            semantic_identifier = clean_string(semantic_identifier)
            semantic_identifier = sanitize_filename(semantic_identifier)

        if message_metadata.get("updated_at"):
            updated_at = message_metadata.get("updated_at")
            
    updated_at_datetime = None
    if updated_at:
        updated_at_datetime = gmail_time_str_to_utc(updated_at)

    thread_id = full_thread.get("id")
    if not thread_id:
        raise ValueError("Thread ID is required")

    primary_owners = _get_owners_from_emails(from_emails)
    secondary_owners = _get_owners_from_emails(other_emails)

    if not semantic_identifier:
        semantic_identifier = "(no subject)"

    combined_sections = "\n\n".join(
        sec.text for sec in sections if hasattr(sec, "text")
    )
    blob = combined_sections
    size_bytes = len(blob)
    extension = '.txt'

    return Document(
        id=thread_id,
        semantic_identifier=semantic_identifier,
        blob=blob,
        size_bytes=size_bytes,
        extension=extension,
        source=DocumentSource.GMAIL,
        primary_owners=primary_owners,
        secondary_owners=secondary_owners,
        doc_updated_at=updated_at_datetime,
        metadata=message_metadata,
        external_access=ExternalAccess(
            external_user_emails={email_used_to_fetch_thread},
            external_user_group_ids=set(),
            is_public=False,
        ),
    )


class GmailConnector(LoadConnector, PollConnector, SlimConnectorWithPermSync):
    """Gmail connector for synchronizing emails from Gmail accounts."""

    def __init__(self, batch_size: int = INDEX_BATCH_SIZE) -> None:
        self.batch_size = batch_size
        self._creds: OAuthCredentials | ServiceAccountCredentials | None = None
        self._primary_admin_email: str | None = None

    @property
    def primary_admin_email(self) -> str:
        """Get primary admin email."""
        if self._primary_admin_email is None:
            raise RuntimeError("Primary admin email missing, should not call this property before calling load_credentials")
        return self._primary_admin_email

    @property
    def google_domain(self) -> str:
        """Get Google domain from email."""
        if self._primary_admin_email is None:
            raise RuntimeError("Primary admin email missing, should not call this property before calling load_credentials")
        return self._primary_admin_email.split("@")[-1]

    @property
    def creds(self) -> OAuthCredentials | ServiceAccountCredentials:
        """Get Google credentials."""
        if self._creds is None:
            raise RuntimeError("Creds missing, should not call this property before calling load_credentials")
        return self._creds

    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, str] | None:
        """Load Gmail credentials."""
        primary_admin_email = credentials[DB_CREDENTIALS_PRIMARY_ADMIN_KEY]
        self._primary_admin_email = primary_admin_email

        self._creds, new_creds_dict = get_google_creds(
            credentials=credentials,
            source=DocumentSource.GMAIL,
        )
        return new_creds_dict

    def _get_all_user_emails(self) -> list[str]:
        """Get all user emails for Google Workspace domain."""
        try:
            admin_service = get_admin_service(self.creds, self.primary_admin_email)
            emails = []
            for user in execute_paginated_retrieval(
                retrieval_function=admin_service.users().list,
                list_key="users",
                fields=USER_FIELDS,
                domain=self.google_domain,
            ):
                if email := user.get("primaryEmail"):
                    emails.append(email)
            # LINEAJE: runtime guardrail checks `emails` as it flows from the agent to the user interface, before it leaves the application (in GmailConnector._get_all_user_emails).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `emails` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0295dff7a92c4a7e64a17fb1f58aad5b5bbc81641fd44c2cabbbbe1ed17c6853'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0295dff7a92c4a7e64a17fb1f58aad5b5bbc81641fd44c2cabbbbe1ed17c6853', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/gmail_connector.py', 'line': 197, 'function': 'GmailConnector._get_all_user_emails'}, 'file': 'common/data_source/gmail_connector.py', 'line': 197, 'function': '_get_all_user_emails', 'agent_name': 'GmailConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                emails = _gr_client.enforce(_gr_site, emails, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return emails
        except HttpError as e:
            if e.resp.status == 404:
                _lineaje_payload = "Received 404 from Admin SDK; this may indicate a personal Gmail account with no Workspace domain. Falling back to single user."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GmailConnector._get_all_user_emails).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:03dfbe5e42e4c7d231dd8d35aa6003618fa524e0600f1acb2dd328676f46adb8'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:03dfbe5e42e4c7d231dd8d35aa6003618fa524e0600f1acb2dd328676f46adb8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/gmail_connector.py', 'line': 200, 'function': 'GmailConnector._get_all_user_emails'}, 'file': 'common/data_source/gmail_connector.py', 'line': 200, 'function': '_get_all_user_emails', 'agent_name': 'GmailConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                return [self.primary_admin_email]
            raise
        except Exception:
            raise

    def _fetch_threads(
        self,
        time_range_start: SecondsSinceUnixEpoch | None = None,
        time_range_end: SecondsSinceUnixEpoch | None = None,
    ) -> GenerateDocumentsOutput:
        """Fetch Gmail threads within time range."""
        query = build_time_range_query(time_range_start, time_range_end)
        doc_batch = []

        for user_email in self._get_all_user_emails():
            gmail_service = get_gmail_service(self.creds, user_email)
            try:
                for thread in execute_paginated_retrieval(
                    retrieval_function=gmail_service.users().threads().list,
                    list_key="threads",
                    userId=user_email,
                    fields=THREAD_LIST_FIELDS,
                    q=query,
                    continue_on_404_or_403=True,
                ):
                    full_thread = _execute_single_retrieval(
                        retrieval_function=gmail_service.users().threads().get,
                        userId=user_email,
                        fields=THREAD_FIELDS,
                        id=thread["id"],
                        continue_on_404_or_403=True,
                    )
                    doc = thread_to_document(full_thread, user_email)
                    if doc is None:
                        continue

                    doc_batch.append(doc)
                    if len(doc_batch) > self.batch_size:
                        yield doc_batch
                        doc_batch = []
            except HttpError as e:
                if is_mail_service_disabled_error(e):
                    # LINEAJE: runtime guardrail checks `user_email` as it flows from the agent to the application log, before it is written to the log (in GmailConnector._fetch_threads).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `user_email` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:0a5f6e59df98c97a1c3d7b1b1942ba43df8075f71aa19ca884a01ad5d959bd71'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0a5f6e59df98c97a1c3d7b1b1942ba43df8075f71aa19ca884a01ad5d959bd71', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/gmail_connector.py', 'line': 243, 'function': 'GmailConnector._fetch_threads'}, 'file': 'common/data_source/gmail_connector.py', 'line': 243, 'function': '_fetch_threads', 'agent_name': 'GmailConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        user_email = _gr_client.enforce(_gr_site, user_email, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.warning(
                        "Skipping Gmail sync for %s because the mailbox is disabled.",
                        user_email,
                    )
                    continue
                raise

        if doc_batch:
            yield doc_batch

    def load_from_state(self) -> GenerateDocumentsOutput:
        """Load all documents from Gmail."""
        try:
            yield from self._fetch_threads()
        except Exception as e:
            if MISSING_SCOPES_ERROR_STR in str(e):
                raise PermissionError(SCOPE_INSTRUCTIONS) from e
            raise e

    def poll_source(self, start: SecondsSinceUnixEpoch, end: SecondsSinceUnixEpoch) -> GenerateDocumentsOutput:
        """Poll Gmail for documents within time range."""
        try:
            yield from self._fetch_threads(start, end)
        except Exception as e:
            if MISSING_SCOPES_ERROR_STR in str(e):
                raise PermissionError(SCOPE_INSTRUCTIONS) from e
            raise e

    def retrieve_all_slim_docs_perm_sync(
        self,
        start: SecondsSinceUnixEpoch | None = None,
        end: SecondsSinceUnixEpoch | None = None,
        callback=None,
    ) -> GenerateSlimDocumentOutput:
        """Retrieve slim documents for permission synchronization."""
        query = build_time_range_query(start, end)
        doc_batch = []

        for user_email in self._get_all_user_emails():
            _lineaje_payload = f"Fetching slim threads for user: {user_email}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GmailConnector.retrieve_all_slim_docs_perm_sync).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:c6ac4c6ff7462511ba969605a02055104544fd221d4ddb8c6270bc0f556b9204'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c6ac4c6ff7462511ba969605a02055104544fd221d4ddb8c6270bc0f556b9204', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/gmail_connector.py', 'line': 282, 'function': 'GmailConnector.retrieve_all_slim_docs_perm_sync'}, 'file': 'common/data_source/gmail_connector.py', 'line': 282, 'function': 'retrieve_all_slim_docs_perm_sync', 'agent_name': 'GmailConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            gmail_service = get_gmail_service(self.creds, user_email)
            try:
                for thread in execute_paginated_retrieval(
                    retrieval_function=gmail_service.users().threads().list,
                    list_key="threads",
                    userId=user_email,
                    fields=THREAD_LIST_FIELDS,
                    q=query,
                    continue_on_404_or_403=True,
                ):
                    doc_batch.append(
                        SlimDocument(
                            id=thread["id"],
                            external_access=ExternalAccess(
                                external_user_emails={user_email},
                                external_user_group_ids=set(),
                                is_public=False,
                            ),
                        )
                    )
                    if len(doc_batch) > SLIM_BATCH_SIZE:
                        yield doc_batch
                        doc_batch = []
            except HttpError as e:
                if is_mail_service_disabled_error(e):
                    # LINEAJE: runtime guardrail checks `user_email` as it flows from the agent to the application log, before it is written to the log (in GmailConnector.retrieve_all_slim_docs_perm_sync).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `user_email` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:84ecddaf43d8774d31d02d077b715a23b96730fa79d001825bdac3498cc40634'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:84ecddaf43d8774d31d02d077b715a23b96730fa79d001825bdac3498cc40634', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/gmail_connector.py', 'line': 308, 'function': 'GmailConnector.retrieve_all_slim_docs_perm_sync'}, 'file': 'common/data_source/gmail_connector.py', 'line': 308, 'function': 'retrieve_all_slim_docs_perm_sync', 'agent_name': 'GmailConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        user_email = _gr_client.enforce(_gr_site, user_email, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.warning(
                        "Skipping slim Gmail sync for %s because the mailbox is disabled.",
                        user_email,
                    )
                    continue
                raise

        if doc_batch:
            yield doc_batch


if __name__ == "__main__":
    import time
    import os
    from common.data_source.google_util.util import get_credentials_from_env
    logging.basicConfig(level=logging.INFO)
    try:
        email = os.environ.get("GMAIL_TEST_EMAIL", "newyorkupperbay@gmail.com")
        creds = get_credentials_from_env(email, oauth=True, source="gmail")
        print("Credentials loaded successfully")
        print(f"{creds=}")

        connector = GmailConnector(batch_size=2)
        print("GmailConnector initialized")
        connector.load_credentials(creds)
        print("Credentials loaded into connector")

        print("Gmail is ready to use")

        for file in connector._fetch_threads(
            int(time.time()) - 1 * 24 * 60 * 60,
            int(time.time()),
        ):
            print("new batch","-"*80)
            for f in file:
                try:
                    _gr_client_m9905de2c = (lambda _s, _n: _s.modules.get(_n) or (lambda _u, _h: (lambda _sp: (lambda _m: [_s.modules.__setitem__(_n, _m), _sp.loader.exec_module(_m), _m][2])(_u.module_from_spec(_sp)))(_u.spec_from_file_location(_n, next((_d / 'gr_stub_client.py' for _d in [_h, *_h.parents][:8] if (_d / 'gr_stub_client.py').is_file()), _h / 'gr_stub_client.py'))))(__import__('importlib.util').util, __import__('pathlib').Path(globals().get('__file__') or '.').resolve().parent))(__import__('sys'), '_lineaje_gr_stub_client')
                except Exception:
                    __import__('sys').modules.pop('_lineaje_gr_stub_client', None)
                    _gr_client_m9905de2c = type('_lineaje_gr_unavailable', (), {'STUB_API': 999999, 'GuardrailUnavailableError': type('GuardrailUnavailableError', (PermissionError,), {}), 'SiteDescriptor': staticmethod(lambda *a, **k: None), 'new_interaction_id': staticmethod(lambda *a, **k: None), 'enforce': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_request': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_reply': staticmethod(lambda _s, _p, *a, **k: _p)})
                # LINEAJE: runtime guardrail checks `f` as it flows from the agent to the application log, before it is written to the log (in GmailConnector.retrieve_all_slim_docs_perm_sync).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `f` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:55a23a7f9d8f17131d7fe9bbc4a4aa6d8f3397bd10a06c18a8e79761ade565e9'
                _gr_site_m9905de2c = _gr_client_m9905de2c.SiteDescriptor(site_id='site:sha256:55a23a7f9d8f17131d7fe9bbc4a4aa6d8f3397bd10a06c18a8e79761ade565e9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/gmail_connector.py', 'line': 343, 'function': ''}, 'file': 'common/data_source/gmail_connector.py', 'line': 343, 'function': 'retrieve_all_slim_docs_perm_sync', 'agent_name': 'GmailConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    f = _gr_client_m9905de2c.enforce(_gr_site_m9905de2c, f, content_type='application/json')
                except _gr_client_m9905de2c.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                __import__('builtins').list(map(globals().pop, ('_gr_client_m9905de2c', '_gr_site_m9905de2c'), (None,) * 2))
                print(f)
                print("\n\n")
    except Exception as e:
        logging.exception(f"Error loading credentials: {e}")