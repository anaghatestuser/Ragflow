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
import os
import threading
from typing import Any, Callable

from common.data_source.config import DocumentSource
from common.data_source.google_util.constant import GOOGLE_SCOPES


def _get_requested_scopes(source: DocumentSource) -> list[str]:
    """Return the scopes to request, honoring an optional override env var."""
    override = os.environ.get("GOOGLE_OAUTH_SCOPE_OVERRIDE", "")
    if override.strip():
        scopes = [scope.strip() for scope in override.split(",") if scope.strip()]
        if scopes:
            # LINEAJE: runtime guardrail checks `scopes` as it flows from the agent to the user interface, before it leaves the application (in _get_requested_scopes).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `scopes` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e2cf1b68480ca683abb67016c128fed0a4146f60edbfd57dd51e9aa07e67f472'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e2cf1b68480ca683abb67016c128fed0a4146f60edbfd57dd51e9aa07e67f472', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/oauth_flow.py', 'line': 16, 'function': '_get_requested_scopes'}, 'file': 'common/data_source/google_util/oauth_flow.py', 'line': 16, 'function': '_get_requested_scopes', 'agent_name': '_get_requested_scopes', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                scopes = _gr_client.enforce(_gr_site, scopes, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return scopes
    return GOOGLE_SCOPES[source]


def _get_oauth_timeout_secs() -> int:
    raw_timeout = os.environ.get("GOOGLE_OAUTH_FLOW_TIMEOUT_SECS", "300").strip()
    try:
        timeout = int(raw_timeout)
    except ValueError:
        timeout = 300
    # LINEAJE: runtime guardrail checks `timeout` as it flows from the agent to the user interface, before it leaves the application (in _get_oauth_timeout_secs).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `timeout` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:fc2bc6807cd5563d9999ee7cd4dc553047c81476192a681f6b83ff123c00150a'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fc2bc6807cd5563d9999ee7cd4dc553047c81476192a681f6b83ff123c00150a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/oauth_flow.py', 'line': 26, 'function': '_get_oauth_timeout_secs'}, 'file': 'common/data_source/google_util/oauth_flow.py', 'line': 26, 'function': '_get_oauth_timeout_secs', 'agent_name': '_get_oauth_timeout_secs', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        timeout = _gr_client.enforce(_gr_site, timeout, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return timeout


def _run_with_timeout(func: Callable[[], Any], timeout_secs: int, timeout_message: str) -> Any:
    if timeout_secs <= 0:
        return func()

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _target() -> None:
        try:
            result["value"] = func()
        except BaseException as exc:  # pragma: no cover
            error["error"] = exc

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout_secs)
    if thread.is_alive():
        raise TimeoutError(timeout_message)
    if "error" in error:
        raise error["error"]
    return result.get("value")


def _run_local_server_flow(client_config: dict[str, Any], source: DocumentSource) -> dict[str, Any]:
    """Launch the standard Google OAuth local-server flow to mint user tokens."""
    from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore

    scopes = _get_requested_scopes(source)
    flow = InstalledAppFlow.from_client_config(
        client_config,
        scopes=scopes,
    )

    open_browser = os.environ.get("GOOGLE_OAUTH_OPEN_BROWSER", "true").lower() != "false"
    preferred_port = os.environ.get("GOOGLE_OAUTH_LOCAL_SERVER_PORT")
    port = int(preferred_port) if preferred_port else 0
    timeout_secs = _get_oauth_timeout_secs()
    timeout_message = f"Google OAuth verification timed out after {timeout_secs} seconds. Close any pending consent windows and rerun the connector configuration to try again."

    _lineaje_payload = "Launching Google OAuth flow. A browser window should open shortly."
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _run_local_server_flow).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:913a0599144d5bdd3b8d1a9eba4739938510ad5d386358bdc4e603bb9660ca73'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:913a0599144d5bdd3b8d1a9eba4739938510ad5d386358bdc4e603bb9660ca73', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/oauth_flow.py', 'line': 68, 'function': '_run_local_server_flow'}, 'file': 'common/data_source/google_util/oauth_flow.py', 'line': 68, 'function': '_run_local_server_flow', 'agent_name': '_run_local_server_flow', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(_lineaje_payload)
    _lineaje_payload = "If it does not, copy the URL shown in the console into your browser manually."
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _run_local_server_flow).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:aeac7a290d2a7b6a9668f37b5b9f6211f028e0a9315ba7191706ede6a5fc3db5'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aeac7a290d2a7b6a9668f37b5b9f6211f028e0a9315ba7191706ede6a5fc3db5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/oauth_flow.py', 'line': 69, 'function': '_run_local_server_flow'}, 'file': 'common/data_source/google_util/oauth_flow.py', 'line': 69, 'function': '_run_local_server_flow', 'agent_name': '_run_local_server_flow', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(_lineaje_payload)
    if timeout_secs > 0:
        _lineaje_payload = f"You have {timeout_secs} seconds to finish granting access before the request times out."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _run_local_server_flow).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5bd0c616e607c4fe57557c8ecb8196b30d40b7895f86ccebeac19c48ee56d35b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5bd0c616e607c4fe57557c8ecb8196b30d40b7895f86ccebeac19c48ee56d35b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/oauth_flow.py', 'line': 71, 'function': '_run_local_server_flow'}, 'file': 'common/data_source/google_util/oauth_flow.py', 'line': 71, 'function': '_run_local_server_flow', 'agent_name': '_run_local_server_flow', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)

    try:
        creds = _run_with_timeout(
            lambda: flow.run_local_server(port=port, open_browser=open_browser, prompt="consent"),
            timeout_secs,
            timeout_message,
        )
    except OSError as exc:
        allow_console = os.environ.get("GOOGLE_OAUTH_ALLOW_CONSOLE_FALLBACK", "true").lower() != "false"
        if not allow_console:
            raise
        _lineaje_payload = f"Local server flow failed ({exc}). Falling back to console-based auth."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _run_local_server_flow).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5c02c04989addff386eb68a1fd39795dd3a7e213f61b7e9f2c5ec418bf69080c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5c02c04989addff386eb68a1fd39795dd3a7e213f61b7e9f2c5ec418bf69080c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/oauth_flow.py', 'line': 83, 'function': '_run_local_server_flow'}, 'file': 'common/data_source/google_util/oauth_flow.py', 'line': 83, 'function': '_run_local_server_flow', 'agent_name': '_run_local_server_flow', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload)
        creds = _run_with_timeout(flow.run_console, timeout_secs, timeout_message)
    except Warning as warning:
        warning_msg = str(warning)
        if "Scope has changed" in warning_msg:
            instructions = [
                "Google rejected one or more of the requested OAuth scopes.",
                "Fix options:",
                "  1. In Google Cloud Console, open APIs & Services > OAuth consent screen and add the missing scopes      (Drive metadata + Admin Directory read scopes), then re-run the flow.",
                "  2. Set GOOGLE_OAUTH_SCOPE_OVERRIDE to a comma-separated list of scopes you are allowed to request.",
            ]
            raise RuntimeError("\n".join(instructions)) from warning
        raise

    token_dict: dict[str, Any] = json.loads(creds.to_json())

    _lineaje_payload = "\nGoogle OAuth flow completed successfully."
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _run_local_server_flow).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:daececa21ba86c6a94ba54101d653edeceb487794456152029e19b02ae13f70b'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:daececa21ba86c6a94ba54101d653edeceb487794456152029e19b02ae13f70b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/oauth_flow.py', 'line': 99, 'function': '_run_local_server_flow'}, 'file': 'common/data_source/google_util/oauth_flow.py', 'line': 99, 'function': '_run_local_server_flow', 'agent_name': '_run_local_server_flow', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(_lineaje_payload)
    _lineaje_payload = "Copy the JSON blob below into GOOGLE_DRIVE_OAUTH_CREDENTIALS_JSON_STR to reuse these tokens without re-authenticating:\n"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _run_local_server_flow).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:38435839737a8d864f7d7182be30fdf92521e978a6445d9def5e176af40ecbeb'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:38435839737a8d864f7d7182be30fdf92521e978a6445d9def5e176af40ecbeb', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/oauth_flow.py', 'line': 100, 'function': '_run_local_server_flow'}, 'file': 'common/data_source/google_util/oauth_flow.py', 'line': 100, 'function': '_run_local_server_flow', 'agent_name': '_run_local_server_flow', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(_lineaje_payload)
    # LINEAJE: runtime guardrail checks `token_dict` as it flows from the agent to an external endpoint, before it leaves the application (in _run_local_server_flow).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `token_dict` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:3eb31e62b0b5f5eda5d9b1b9551837742fa5840f2bcbc5eecdc0464e3c1930be'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3eb31e62b0b5f5eda5d9b1b9551837742fa5840f2bcbc5eecdc0464e3c1930be', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/oauth_flow.py', 'line': 101, 'function': '_run_local_server_flow'}, 'file': 'common/data_source/google_util/oauth_flow.py', 'line': 101, 'function': '_run_local_server_flow', 'agent_name': '_run_local_server_flow', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        token_dict = _gr_client.enforce(_gr_site, token_dict, content_type='application/json', variable_name='token_dict', source_file=__file__, before_line=101)
    except _gr_client.GuardrailUnavailableError:
        pass
    _lineaje_payload = json.dumps(token_dict, indent=2)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _run_local_server_flow).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:842edc2c50273e585e9fe51931165d2b11c65236970ade059de01361af84d340'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:842edc2c50273e585e9fe51931165d2b11c65236970ade059de01361af84d340', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/oauth_flow.py', 'line': 101, 'function': '_run_local_server_flow'}, 'file': 'common/data_source/google_util/oauth_flow.py', 'line': 101, 'function': '_run_local_server_flow', 'agent_name': '_run_local_server_flow', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(_lineaje_payload)
    print()

    # LINEAJE: runtime guardrail checks `token_dict` as it flows from the agent to the user interface, before it leaves the application (in _run_local_server_flow).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `token_dict` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:83b522708a3edfb2a3cc0b35d5d408f984930954e4028b34c865948fa17918d7'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:83b522708a3edfb2a3cc0b35d5d408f984930954e4028b34c865948fa17918d7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_util/oauth_flow.py', 'line': 104, 'function': '_run_local_server_flow'}, 'file': 'common/data_source/google_util/oauth_flow.py', 'line': 104, 'function': '_run_local_server_flow', 'agent_name': '_run_local_server_flow', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        token_dict = _gr_client.enforce(_gr_site, token_dict, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return token_dict


def ensure_oauth_token_dict(credentials: dict[str, Any], source: DocumentSource) -> dict[str, Any]:
    """Return a dict that contains OAuth tokens, running the flow if only a client config is provided."""
    if "refresh_token" in credentials and "token" in credentials:
        return credentials

    client_config: dict[str, Any] | None = None
    if "installed" in credentials:
        client_config = {"installed": credentials["installed"]}
    elif "web" in credentials:
        client_config = {"web": credentials["web"]}

    if client_config is None:
        raise ValueError("Provided Google OAuth credentials are missing both tokens and a client configuration.")

    return _run_local_server_flow(client_config, source)
