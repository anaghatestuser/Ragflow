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
from collections.abc import Callable
from typing import Any

from google.auth.exceptions import RefreshError  # type: ignore
from google.oauth2.credentials import Credentials as OAuthCredentials  # type: ignore  # type: ignore
from google.oauth2.service_account import Credentials as ServiceAccountCredentials  # type: ignore  # type: ignore
from googleapiclient.discovery import (
    Resource,  # type: ignore
    build,  # type: ignore
)


class GoogleDriveService(Resource):
    pass


class GoogleDocsService(Resource):
    pass


class AdminService(Resource):
    pass


class GmailService(Resource):
    pass


class RefreshableDriveObject:
    """
    Running Google Drive service retrieval functions
    involves accessing methods of the service object (i.e. files().list())
    which can raise a RefreshError if the access token is expired.
    This class is a wrapper that propagates the ability to refresh the access token
    and retry the final retrieval function until execute() is called.
    """

    def __init__(
        self,
        call_stack: Callable[[ServiceAccountCredentials | OAuthCredentials], Any],
        creds: ServiceAccountCredentials | OAuthCredentials,
        creds_getter: Callable[..., ServiceAccountCredentials | OAuthCredentials],
    ):
        self.call_stack = call_stack
        self.creds = creds
        self.creds_getter = creds_getter

    def __getattr__(self, name: str) -> Any:
        if name == "execute":
            return self.make_refreshable_execute()
        return RefreshableDriveObject(
            lambda creds: getattr(self.call_stack(creds), name),
            self.creds,
            self.creds_getter,
        )

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return RefreshableDriveObject(
            lambda creds: self.call_stack(creds)(*args, **kwargs),
            self.creds,
            self.creds_getter,
        )

    def make_refreshable_execute(self) -> Callable:
        def execute(*args: Any, **kwargs: Any) -> Any:
            try:
                return self.call_stack(self.creds).execute(*args, **kwargs)
            except RefreshError as e:
                _lineaje_payload = f"RefreshError, going to attempt a creds refresh and retry: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RefreshableDriveObject.execute).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:19b6fbdc0eb66771fb15f69e31df8dee2464aff58f595250c66cdaed7ba3883d'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:19b6fbdc0eb66771fb15f69e31df8dee2464aff58f595250c66cdaed7ba3883d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/resource.py', 'line': 70, 'function': 'RefreshableDriveObject.make_refreshable_execute.execute'}, 'file': 'common/data_source/google_util/resource.py', 'line': 70, 'function': 'execute', 'agent_name': 'RefreshableDriveObject', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                # Refresh the access token
                self.creds = self.creds_getter()
                return self.call_stack(self.creds).execute(*args, **kwargs)

        # LINEAJE: runtime guardrail checks `execute` as it flows from the agent to the user interface, before it leaves the application (in RefreshableDriveObject.make_refreshable_execute).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `execute` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:0b9589107334c096c5e617eb47622c5343d5eb927a7f9fddb09efe37f7166ba3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0b9589107334c096c5e617eb47622c5343d5eb927a7f9fddb09efe37f7166ba3', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/resource.py', 'line': 75, 'function': 'RefreshableDriveObject.make_refreshable_execute'}, 'file': 'common/data_source/google_util/resource.py', 'line': 75, 'function': 'make_refreshable_execute', 'agent_name': 'RefreshableDriveObject', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            execute = _gr_client.enforce(_gr_site, execute, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return execute


def _get_google_service(
    service_name: str,
    service_version: str,
    creds: ServiceAccountCredentials | OAuthCredentials,
    user_email: str | None = None,
) -> GoogleDriveService | GoogleDocsService | AdminService | GmailService:
    service: Resource
    if isinstance(creds, ServiceAccountCredentials):
        # NOTE: https://developers.google.com/identity/protocols/oauth2/service-account#error-codes
        creds = creds.with_subject(user_email)
        service = build(service_name, service_version, credentials=creds)
    elif isinstance(creds, OAuthCredentials):
        service = build(service_name, service_version, credentials=creds)

    return service


def get_google_docs_service(
    creds: ServiceAccountCredentials | OAuthCredentials,
    user_email: str | None = None,
) -> GoogleDocsService:
    return _get_google_service("docs", "v1", creds, user_email)


def get_drive_service(
    creds: ServiceAccountCredentials | OAuthCredentials,
    user_email: str | None = None,
) -> GoogleDriveService:
    return _get_google_service("drive", "v3", creds, user_email)


def get_admin_service(
    creds: ServiceAccountCredentials | OAuthCredentials,
    user_email: str | None = None,
) -> AdminService:
    return _get_google_service("admin", "directory_v1", creds, user_email)


def get_gmail_service(
    creds: ServiceAccountCredentials | OAuthCredentials,
    user_email: str | None = None,
) -> GmailService:
    return _get_google_service("gmail", "v1", creds, user_email)
