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
from typing import Any

from google.auth.transport.requests import Request  # type: ignore
from google.oauth2.credentials import Credentials as OAuthCredentials  # type: ignore  # type: ignore
from google.oauth2.service_account import Credentials as ServiceAccountCredentials  # type: ignore  # type: ignore

from common.data_source.config import OAUTH_GOOGLE_DRIVE_CLIENT_ID, OAUTH_GOOGLE_DRIVE_CLIENT_SECRET, DocumentSource
from common.data_source.google_util.constant import (
    DB_CREDENTIALS_AUTHENTICATION_METHOD,
    DB_CREDENTIALS_DICT_SERVICE_ACCOUNT_KEY,
    DB_CREDENTIALS_DICT_TOKEN_KEY,
    DB_CREDENTIALS_PRIMARY_ADMIN_KEY,
    GOOGLE_SCOPES,
    GoogleOAuthAuthenticationMethod,
)
from common.data_source.google_util.oauth_flow import ensure_oauth_token_dict


def sanitize_oauth_credentials(oauth_creds: OAuthCredentials) -> str:
    """we really don't want to be persisting the client id and secret anywhere but the
    environment.

    Returns a string of serialized json.
    """

    # strip the client id and secret
    oauth_creds_json_str = oauth_creds.to_json()
    oauth_creds_sanitized_json: dict[str, Any] = json.loads(oauth_creds_json_str)
    oauth_creds_sanitized_json.pop("client_id", None)
    oauth_creds_sanitized_json.pop("client_secret", None)
    # LINEAJE: runtime guardrail checks `oauth_creds_sanitized_json` as it flows from the agent to an external endpoint, before it leaves the application (in sanitize_oauth_credentials).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `oauth_creds_sanitized_json` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:0657d7cb982735a996441c55d7868c47eb2e76d18714741ca7be89a338e88135'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0657d7cb982735a996441c55d7868c47eb2e76d18714741ca7be89a338e88135', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/auth.py', 'line': 33, 'function': 'sanitize_oauth_credentials'}, 'file': 'common/data_source/google_util/auth.py', 'line': 33, 'function': 'sanitize_oauth_credentials', 'agent_name': 'sanitize_oauth_credentials', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        oauth_creds_sanitized_json = _gr_client.enforce(_gr_site, oauth_creds_sanitized_json, content_type='application/json', variable_name='oauth_creds_sanitized_json', source_file=__file__, before_line=33)
    except _gr_client.GuardrailUnavailableError:
        pass
    oauth_creds_sanitized_json_str = json.dumps(oauth_creds_sanitized_json)
    # LINEAJE: runtime guardrail checks `oauth_creds_sanitized_json_str` as it flows from the agent to the user interface, before it leaves the application (in sanitize_oauth_credentials).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `oauth_creds_sanitized_json_str` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:75e2c502d757cb00957837915b7b50c8013ecc8b6fe769ba50a4b08c147022ba'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:75e2c502d757cb00957837915b7b50c8013ecc8b6fe769ba50a4b08c147022ba', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/auth.py', 'line': 34, 'function': 'sanitize_oauth_credentials'}, 'file': 'common/data_source/google_util/auth.py', 'line': 34, 'function': 'sanitize_oauth_credentials', 'agent_name': 'sanitize_oauth_credentials', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        oauth_creds_sanitized_json_str = _gr_client.enforce(_gr_site, oauth_creds_sanitized_json_str, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return oauth_creds_sanitized_json_str


def get_google_creds(
    credentials: dict[str, str],
    source: DocumentSource,
) -> tuple[ServiceAccountCredentials | OAuthCredentials, dict[str, str] | None]:
    """Checks for two different types of credentials.
    (1) A credential which holds a token acquired via a user going through
    the Google OAuth flow.
    (2) A credential which holds a service account key JSON file, which
    can then be used to impersonate any user in the workspace.

    Return a tuple where:
        The first element is the requested credentials
        The second element is a new credentials dict that the caller should write back
        to the db. This happens if token rotation occurs while loading credentials.
    """
    oauth_creds = None
    service_creds = None
    new_creds_dict = None
    if DB_CREDENTIALS_DICT_TOKEN_KEY in credentials:
        # OAUTH
        authentication_method: str = credentials.get(
            DB_CREDENTIALS_AUTHENTICATION_METHOD,
            GoogleOAuthAuthenticationMethod.UPLOADED,
        )

        credentials_dict_str = credentials[DB_CREDENTIALS_DICT_TOKEN_KEY]
        credentials_dict = json.loads(credentials_dict_str)

        regenerated_from_client_secret = False
        if "client_id" not in credentials_dict or "client_secret" not in credentials_dict or "refresh_token" not in credentials_dict:
            try:
                credentials_dict = ensure_oauth_token_dict(credentials_dict, source)
            except Exception as exc:
                raise PermissionError(
                    "Google Drive OAuth credentials are incomplete. Please finish the OAuth flow to generate access tokens."
                ) from exc
            credentials_dict_str = json.dumps(credentials_dict)
            regenerated_from_client_secret = True

        # only send what get_google_oauth_creds needs
        authorized_user_info = {}

        # oauth_interactive is sanitized and needs credentials from the environment
        if authentication_method == GoogleOAuthAuthenticationMethod.OAUTH_INTERACTIVE:
            authorized_user_info["client_id"] = OAUTH_GOOGLE_DRIVE_CLIENT_ID
            authorized_user_info["client_secret"] = OAUTH_GOOGLE_DRIVE_CLIENT_SECRET
        else:
            authorized_user_info["client_id"] = credentials_dict["client_id"]
            authorized_user_info["client_secret"] = credentials_dict["client_secret"]

        authorized_user_info["refresh_token"] = credentials_dict["refresh_token"]

        authorized_user_info["token"] = credentials_dict["token"]
        authorized_user_info["expiry"] = credentials_dict["expiry"]

        # LINEAJE: runtime guardrail checks `authorized_user_info` as it flows from the agent to an external endpoint, before it leaves the application (in get_google_creds).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `authorized_user_info` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e5d066f6bb486d17ad1d4ea734434a7681f7a2d76bbc001a7d17a754484f18b3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e5d066f6bb486d17ad1d4ea734434a7681f7a2d76bbc001a7d17a754484f18b3', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/auth.py', 'line': 92, 'function': 'get_google_creds'}, 'file': 'common/data_source/google_util/auth.py', 'line': 92, 'function': 'get_google_creds', 'agent_name': 'get_google_creds', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            authorized_user_info = _gr_client.enforce(_gr_site, authorized_user_info, content_type='application/json', variable_name='authorized_user_info', source_file=__file__, before_line=92)
        except _gr_client.GuardrailUnavailableError:
            pass
        token_json_str = json.dumps(authorized_user_info)
        oauth_creds = get_google_oauth_creds(token_json_str=token_json_str, source=source)

        # tell caller to update token stored in DB if the refresh token changed
        if oauth_creds:
            should_persist = regenerated_from_client_secret or oauth_creds.refresh_token != authorized_user_info["refresh_token"]
            if should_persist:
                # if oauth_interactive, sanitize the credentials so they don't get stored in the db
                if authentication_method == GoogleOAuthAuthenticationMethod.OAUTH_INTERACTIVE:
                    oauth_creds_json_str = sanitize_oauth_credentials(oauth_creds)
                else:
                    oauth_creds_json_str = oauth_creds.to_json()

                new_creds_dict = {
                    DB_CREDENTIALS_DICT_TOKEN_KEY: oauth_creds_json_str,
                    DB_CREDENTIALS_PRIMARY_ADMIN_KEY: credentials[DB_CREDENTIALS_PRIMARY_ADMIN_KEY],
                    DB_CREDENTIALS_AUTHENTICATION_METHOD: authentication_method,
                }
    elif DB_CREDENTIALS_DICT_SERVICE_ACCOUNT_KEY in credentials:
        # SERVICE ACCOUNT
        service_account_key_json_str = credentials[DB_CREDENTIALS_DICT_SERVICE_ACCOUNT_KEY]
        service_account_key = json.loads(service_account_key_json_str)

        service_creds = ServiceAccountCredentials.from_service_account_info(service_account_key, scopes=GOOGLE_SCOPES[source])

        if not service_creds.valid or not service_creds.expired:
            service_creds.refresh(Request())

        if not service_creds.valid:
            raise PermissionError(f"Unable to access {source} - service account credentials are invalid.")

    creds: ServiceAccountCredentials | OAuthCredentials | None = oauth_creds or service_creds
    if creds is None:
        raise PermissionError(f"Unable to access {source} - unknown credential structure.")

    return creds, new_creds_dict


def get_google_oauth_creds(token_json_str: str, source: DocumentSource) -> OAuthCredentials | None:
    """creds_json only needs to contain client_id, client_secret and refresh_token to
    refresh the creds.

    expiry and token are optional ... however, if passing in expiry, token
    should also be passed in or else we may not return any creds.
    (probably a sign we should refactor the function)
    """

    creds_json = json.loads(token_json_str)
    creds = OAuthCredentials.from_authorized_user_info(
        info=creds_json,
        scopes=GOOGLE_SCOPES[source],
    )
    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            if creds.valid:
                _lineaje_payload = "Refreshed Google Drive tokens."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in get_google_oauth_creds).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:72f26f6a106f4650297baced798aed9ca0a82cc53c19562d58f296dc61024408'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:72f26f6a106f4650297baced798aed9ca0a82cc53c19562d58f296dc61024408', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/auth.py', 'line': 151, 'function': 'get_google_oauth_creds'}, 'file': 'common/data_source/google_util/auth.py', 'line': 151, 'function': 'get_google_oauth_creds', 'agent_name': 'get_google_oauth_creds', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                return creds
        except Exception:
            _lineaje_payload = "Failed to refresh google drive access token"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in get_google_oauth_creds).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:a484af9cfd68790674c5fa9b2f8198feba93b4c76daf0ef34e9760b24c82bf8f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a484af9cfd68790674c5fa9b2f8198feba93b4c76daf0ef34e9760b24c82bf8f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/auth.py', 'line': 154, 'function': 'get_google_oauth_creds'}, 'file': 'common/data_source/google_util/auth.py', 'line': 154, 'function': 'get_google_oauth_creds', 'agent_name': 'get_google_oauth_creds', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
            return None

    return None
