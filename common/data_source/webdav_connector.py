"""WebDAV connector"""
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
import os
from datetime import datetime, timezone
from typing import Any, Optional

from webdav4.client import Client as WebDAVClient

from common.data_source.utils import (
    get_file_ext,
)
from common.data_source.config import DocumentSource, INDEX_BATCH_SIZE, BLOB_STORAGE_SIZE_THRESHOLD
from common.data_source.exceptions import (
    ConnectorMissingCredentialError,
    ConnectorValidationError,
    CredentialExpiredError,
    InsufficientPermissionsError
)
from common.data_source.interfaces import LoadConnector, PollConnector
from common.data_source.models import Document, SecondsSinceUnixEpoch, GenerateDocumentsOutput


class WebDAVConnector(LoadConnector, PollConnector):
    """WebDAV connector for syncing files from WebDAV servers"""

    def __init__(
        self,
        base_url: str,
        remote_path: str = "/",
        batch_size: int = INDEX_BATCH_SIZE,
    ) -> None:
        """Initialize WebDAV connector
        
        Args:
            base_url: Base URL of the WebDAV server (e.g., "https://webdav.example.com")
            remote_path: Remote path to sync from (default: "/")
            batch_size: Number of documents per batch
        """
        self.base_url = base_url.rstrip("/")
        if not remote_path:
            remote_path = "/"
        if not remote_path.startswith("/"):
            remote_path = f"/{remote_path}"
        if remote_path.endswith("/") and remote_path != "/":
            remote_path = remote_path.rstrip("/")
        self.remote_path = remote_path
        self.batch_size = batch_size
        self.client: Optional[WebDAVClient] = None
        self._allow_images: bool | None = None
        self.size_threshold: int | None = BLOB_STORAGE_SIZE_THRESHOLD

    def set_allow_images(self, allow_images: bool) -> None:
        """Set whether to process images"""
        _lineaje_payload = f"Setting allow_images to {allow_images}."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector.set_allow_images).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:50082ae4365a9f4bd89860f63cdb847e758021f8d4554540ab4c539e8eaa9998'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:50082ae4365a9f4bd89860f63cdb847e758021f8d4554540ab4c539e8eaa9998', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 54, 'function': 'WebDAVConnector.set_allow_images'}, 'file': 'common/data_source/webdav_connector.py', 'line': 54, 'function': 'set_allow_images', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        self._allow_images = allow_images

    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        """Load credentials and initialize WebDAV client
        
        Args:
            credentials: Dictionary containing 'username' and 'password'
        
        Returns:
            None
        
        Raises:
            ConnectorMissingCredentialError: If required credentials are missing
        """
        _lineaje_payload = f"Loading credentials for WebDAV server {self.base_url}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector.load_credentials).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:57f70abe0936aa3aaa71fb860c11d80f1b7bfdf0c1590bde0acb2d7f066755fb'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:57f70abe0936aa3aaa71fb860c11d80f1b7bfdf0c1590bde0acb2d7f066755fb', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 69, 'function': 'WebDAVConnector.load_credentials'}, 'file': 'common/data_source/webdav_connector.py', 'line': 69, 'function': 'load_credentials', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)

        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            raise ConnectorMissingCredentialError(
                "WebDAV requires 'username' and 'password' credentials"
            )

        try:
            # Initialize WebDAV client
            self.client = WebDAVClient(
                base_url=self.base_url,
                auth=(username, password)
            )
            
            # Test connection
            self.client.exists(self.remote_path)
            
        except Exception as e:
            _lineaje_payload = f"Failed to connect to WebDAV server: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector.load_credentials).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f569d1be81e55494139cb70a7a819bdbd1658acd53c21ee62d54487e591ba0bb'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f569d1be81e55494139cb70a7a819bdbd1658acd53c21ee62d54487e591ba0bb', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 90, 'function': 'WebDAVConnector.load_credentials'}, 'file': 'common/data_source/webdav_connector.py', 'line': 90, 'function': 'load_credentials', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            raise ConnectorMissingCredentialError(
                f"Failed to authenticate with WebDAV server: {e}"
            )

        return None

    def _list_files_recursive(
        self, 
        path: str,
        start: datetime,
        end: datetime,
    ) -> list[tuple[str, dict]]:
        """Recursively list all files in the given path
        
        Args:
            path: Path to list files from
            start: Start datetime for filtering
            end: End datetime for filtering
            
        Returns:
            List of tuples containing (file_path, file_info)
        """
        if self.client is None:
            raise ConnectorMissingCredentialError("WebDAV client not initialized")

        files = []
        
        try:
            _lineaje_payload = f"Listing directory: {path}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._list_files_recursive).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:c8cb55176168cb9871de574e71ce8a760f6b49560820b734da2421d7b9006898'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c8cb55176168cb9871de574e71ce8a760f6b49560820b734da2421d7b9006898', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 119, 'function': 'WebDAVConnector._list_files_recursive'}, 'file': 'common/data_source/webdav_connector.py', 'line': 119, 'function': '_list_files_recursive', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.debug(_lineaje_payload)
            for item in self.client.ls(path, detail=True):
                item_path = item['name']
            
                if item_path == path or item_path == path + '/':
                    continue
                
                _lineaje_payload = f"Found item: {item_path}, type: {item.get('type')}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._list_files_recursive).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f5362c5e81c47d561af0fd0cfce08cb9d44b9646d8d943ecc1db59e7bc39877e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f5362c5e81c47d561af0fd0cfce08cb9d44b9646d8d943ecc1db59e7bc39877e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 126, 'function': 'WebDAVConnector._list_files_recursive'}, 'file': 'common/data_source/webdav_connector.py', 'line': 126, 'function': '_list_files_recursive', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.debug(_lineaje_payload)

                if item.get('type') == 'directory':
                    try:
                        files.extend(self._list_files_recursive(item_path, start, end))
                    except Exception as e:
                        _lineaje_payload = f"Error recursing into directory {item_path}: {e}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._list_files_recursive).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:49027d7976e3154cad459b7b9ab2c75acdc3e393a2fc6f8572c015d0ac911e97'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:49027d7976e3154cad459b7b9ab2c75acdc3e393a2fc6f8572c015d0ac911e97', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 132, 'function': 'WebDAVConnector._list_files_recursive'}, 'file': 'common/data_source/webdav_connector.py', 'line': 132, 'function': '_list_files_recursive', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.error(_lineaje_payload)
                        continue
                else:
                    try:
                        modified_time = item.get('modified')
                        if modified_time:
                            if isinstance(modified_time, datetime):
                                modified = modified_time
                                if modified.tzinfo is None:
                                    modified = modified.replace(tzinfo=timezone.utc)
                            elif isinstance(modified_time, str):
                                try:
                                    modified = datetime.strptime(modified_time, '%a, %d %b %Y %H:%M:%S %Z')
                                    modified = modified.replace(tzinfo=timezone.utc)
                                except (ValueError, TypeError):
                                    try:
                                        modified = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
                                    except (ValueError, TypeError):
                                        _lineaje_payload = f"Could not parse modified time for {item_path}: {modified_time}"
                                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._list_files_recursive).
                                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                                        #   Do not remove without review. site_id='site:sha256:7f5743798f1fe1af6dcc0501246a6f0a339d951f61c1d974d03017a1d881bcd8'
                                        _gr_client = _lineaje_load_gr_client()
                                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7f5743798f1fe1af6dcc0501246a6f0a339d951f61c1d974d03017a1d881bcd8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 150, 'function': 'WebDAVConnector._list_files_recursive'}, 'file': 'common/data_source/webdav_connector.py', 'line': 150, 'function': '_list_files_recursive', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                                        try:
                                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                                        except _gr_client.GuardrailUnavailableError:
                                            pass
                                        except PermissionError:
                                            pass
                                        logging.warning(_lineaje_payload)
                                        modified = datetime.now(timezone.utc)
                            else:
                                modified = datetime.now(timezone.utc)
                        else:
                            modified = datetime.now(timezone.utc)
                        

                        _lineaje_payload = f"File {item_path}: modified={modified}, start={start}, end={end}, include={start < modified <= end}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._list_files_recursive).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:6c33cc4390016fb9aea91a084c9f8d78985655d6ebecf92d45c304ef7fba97a3'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6c33cc4390016fb9aea91a084c9f8d78985655d6ebecf92d45c304ef7fba97a3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 158, 'function': 'WebDAVConnector._list_files_recursive'}, 'file': 'common/data_source/webdav_connector.py', 'line': 158, 'function': '_list_files_recursive', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.debug(_lineaje_payload)
                        if start < modified <= end:
                            files.append((item_path, item))
                        else:
                            _lineaje_payload = f"File {item_path} filtered out by time range"
                            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._list_files_recursive).
                            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                            #   Do not remove without review. site_id='site:sha256:0116db9aff71af646e9f4571e267c45b8bf259d61846bd251728945b2071ea49'
                            _gr_client = _lineaje_load_gr_client()
                            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0116db9aff71af646e9f4571e267c45b8bf259d61846bd251728945b2071ea49', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 162, 'function': 'WebDAVConnector._list_files_recursive'}, 'file': 'common/data_source/webdav_connector.py', 'line': 162, 'function': '_list_files_recursive', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                            try:
                                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                            except _gr_client.GuardrailUnavailableError:
                                pass
                            except PermissionError:
                                pass
                            logging.debug(_lineaje_payload)
                    except Exception as e:
                        _lineaje_payload = f"Error processing file {item_path}: {e}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._list_files_recursive).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:961e28aa509069528a0f8f5282ab8b1bbb46c0165ff8fe6e5a1a4d4d96cead91'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:961e28aa509069528a0f8f5282ab8b1bbb46c0165ff8fe6e5a1a4d4d96cead91', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 164, 'function': 'WebDAVConnector._list_files_recursive'}, 'file': 'common/data_source/webdav_connector.py', 'line': 164, 'function': '_list_files_recursive', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.error(_lineaje_payload)
                        continue
                        
        except Exception as e:
            _lineaje_payload = f"Error listing directory {path}: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._list_files_recursive).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:5038c65a461fc5a80e068f4f09caaca3e42b281592c84518887e303fdeab2050'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5038c65a461fc5a80e068f4f09caaca3e42b281592c84518887e303fdeab2050', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 168, 'function': 'WebDAVConnector._list_files_recursive'}, 'file': 'common/data_source/webdav_connector.py', 'line': 168, 'function': '_list_files_recursive', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            
        # LINEAJE: runtime guardrail checks `files` as it flows from the agent to the user interface, before it leaves the application (in WebDAVConnector._list_files_recursive).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `files` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:35c06f83c15fa280dd51f1f27279d5411add21d72955348b9f57be86ff57a503'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:35c06f83c15fa280dd51f1f27279d5411add21d72955348b9f57be86ff57a503', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 170, 'function': 'WebDAVConnector._list_files_recursive'}, 'file': 'common/data_source/webdav_connector.py', 'line': 170, 'function': '_list_files_recursive', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            files = _gr_client.enforce(_gr_site, files, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return files

    def _yield_webdav_documents(
        self,
        start: datetime,
        end: datetime,
    ) -> GenerateDocumentsOutput:
        """Generate documents from WebDAV server
        
        Args:
            start: Start datetime for filtering
            end: End datetime for filtering
            
        Yields:
            Batches of documents
        """
        if self.client is None:
            raise ConnectorMissingCredentialError("WebDAV client not initialized")

        _lineaje_payload = f"Searching for files in {self.remote_path} between {start} and {end}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._yield_webdav_documents).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:63d061d6ea2df78bc336249c2a6a6b0770b9f36d4a4a759a787334291b9263f9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:63d061d6ea2df78bc336249c2a6a6b0770b9f36d4a4a759a787334291b9263f9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 189, 'function': 'WebDAVConnector._yield_webdav_documents'}, 'file': 'common/data_source/webdav_connector.py', 'line': 189, 'function': '_yield_webdav_documents', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        files = self._list_files_recursive(self.remote_path, start, end)
        _lineaje_payload = f"Found {len(files)} files matching time criteria"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._yield_webdav_documents).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:7d4c12b2b31a3a2dcb501b3ea7508f134f273bf839af69267632cffca17bc5c7'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7d4c12b2b31a3a2dcb501b3ea7508f134f273bf839af69267632cffca17bc5c7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 191, 'function': 'WebDAVConnector._yield_webdav_documents'}, 'file': 'common/data_source/webdav_connector.py', 'line': 191, 'function': '_yield_webdav_documents', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        
        filename_counts: dict[str, int] = {}
        for file_path, _ in files:
            file_name = os.path.basename(file_path)
            filename_counts[file_name] = filename_counts.get(file_name, 0) + 1
        
        batch: list[Document] = []
        for file_path, file_info in files:
            file_name = os.path.basename(file_path)
            
            size_bytes = file_info.get('size', 0)
            if (
                self.size_threshold is not None
                and isinstance(size_bytes, int)
                and size_bytes > self.size_threshold
            ):
                _lineaje_payload = f"{file_name} exceeds size threshold of {self.size_threshold}. Skipping."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._yield_webdav_documents).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:7e7420e77bedaaa8418e3ad84e832f523828c9bfd65e97ccf698798c5aa266e4'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7e7420e77bedaaa8418e3ad84e832f523828c9bfd65e97ccf698798c5aa266e4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 208, 'function': 'WebDAVConnector._yield_webdav_documents'}, 'file': 'common/data_source/webdav_connector.py', 'line': 208, 'function': '_yield_webdav_documents', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(
                    _lineaje_payload
                )
                continue
            
            try:
                _lineaje_payload = f"Downloading file: {file_path}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._yield_webdav_documents).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:683f5d4d28c3db5aef791c31ce11934d50a0b52494514e01fe247f4a55e7a5a7'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:683f5d4d28c3db5aef791c31ce11934d50a0b52494514e01fe247f4a55e7a5a7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 214, 'function': 'WebDAVConnector._yield_webdav_documents'}, 'file': 'common/data_source/webdav_connector.py', 'line': 214, 'function': '_yield_webdav_documents', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.debug(_lineaje_payload)
                from io import BytesIO
                buffer = BytesIO()
                self.client.download_fileobj(file_path, buffer)
                blob = buffer.getvalue()
                
                if blob is None or len(blob) == 0:
                    _lineaje_payload = f"Downloaded content is empty for {file_path}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._yield_webdav_documents).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:f3926e6842e5f56d56ca49f912fafee4b6198e408fa455bb0f59cbf3caa49d03'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f3926e6842e5f56d56ca49f912fafee4b6198e408fa455bb0f59cbf3caa49d03', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 221, 'function': 'WebDAVConnector._yield_webdav_documents'}, 'file': 'common/data_source/webdav_connector.py', 'line': 221, 'function': '_yield_webdav_documents', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.warning(_lineaje_payload)
                    continue

                modified_time = file_info.get('modified')
                if modified_time:
                    if isinstance(modified_time, datetime):
                        modified = modified_time
                        if modified.tzinfo is None:
                            modified = modified.replace(tzinfo=timezone.utc)
                    elif isinstance(modified_time, str):
                        try:
                            modified = datetime.strptime(modified_time, '%a, %d %b %Y %H:%M:%S %Z')
                            modified = modified.replace(tzinfo=timezone.utc)
                        except (ValueError, TypeError):
                            try:
                                modified = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
                            except (ValueError, TypeError):
                                _lineaje_payload = f"Could not parse modified time for {file_path}: {modified_time}"
                                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._yield_webdav_documents).
                                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                                #   Do not remove without review. site_id='site:sha256:ff14db8992a9e7d19e3ee7fbfa0b8a93343d27e1663a28c9dc488aee5d4c3e40'
                                _gr_client = _lineaje_load_gr_client()
                                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ff14db8992a9e7d19e3ee7fbfa0b8a93343d27e1663a28c9dc488aee5d4c3e40', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 238, 'function': 'WebDAVConnector._yield_webdav_documents'}, 'file': 'common/data_source/webdav_connector.py', 'line': 238, 'function': '_yield_webdav_documents', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                                try:
                                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                                except _gr_client.GuardrailUnavailableError:
                                    pass
                                except PermissionError:
                                    pass
                                logging.warning(_lineaje_payload)
                                modified = datetime.now(timezone.utc)
                    else:
                        modified = datetime.now(timezone.utc)
                else:
                    modified = datetime.now(timezone.utc)

                if filename_counts.get(file_name, 0) > 1:
                    relative_path = file_path
                    if file_path.startswith(self.remote_path):
                        relative_path = file_path[len(self.remote_path):]
                    if relative_path.startswith('/'):
                        relative_path = relative_path[1:]
                    semantic_id = relative_path.replace('/', ' / ') if relative_path else file_name
                else:
                    semantic_id = file_name

                batch.append(
                    Document(
                        id=f"webdav:{self.base_url}:{file_path}",
                        blob=blob,
                        source=DocumentSource.WEBDAV,
                        semantic_identifier=semantic_id,
                        extension=get_file_ext(file_name),
                        doc_updated_at=modified,
                        size_bytes=size_bytes if size_bytes else 0
                    )
                )
                
                if len(batch) == self.batch_size:
                    yield batch
                    batch = []

            except Exception as e:
                _lineaje_payload = f"Error downloading file {file_path}: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector._yield_webdav_documents).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:3bc7e2fc93dfcbae5a7fdc8ee585da75a9dcc9d49ee924b3ff296b1ea2b229d1'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3bc7e2fc93dfcbae5a7fdc8ee585da75a9dcc9d49ee924b3ff296b1ea2b229d1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 272, 'function': 'WebDAVConnector._yield_webdav_documents'}, 'file': 'common/data_source/webdav_connector.py', 'line': 272, 'function': '_yield_webdav_documents', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(_lineaje_payload)
        
        if batch:
            yield batch

    def load_from_state(self) -> GenerateDocumentsOutput:
        """Load all documents from WebDAV server
        
        Yields:
            Batches of documents
        """
        _lineaje_payload = f"Loading documents from WebDAV server {self.base_url}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in WebDAVConnector.load_from_state).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f136381d001dd77869a8b4495181886a4aff26d07e82a0f9724c4382d0e39862'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f136381d001dd77869a8b4495181886a4aff26d07e82a0f9724c4382d0e39862', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/webdav_connector.py', 'line': 283, 'function': 'WebDAVConnector.load_from_state'}, 'file': 'common/data_source/webdav_connector.py', 'line': 283, 'function': 'load_from_state', 'agent_name': 'WebDAVConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)
        return self._yield_webdav_documents(
            start=datetime(1970, 1, 1, tzinfo=timezone.utc),
            end=datetime.now(timezone.utc),
        )

    def poll_source(
        self, start: SecondsSinceUnixEpoch, end: SecondsSinceUnixEpoch
    ) -> GenerateDocumentsOutput:
        """Poll WebDAV server for updated documents
        
        Args:
            start: Start timestamp (seconds since Unix epoch)
            end: End timestamp (seconds since Unix epoch)
            
        Yields:
            Batches of documents
        """
        if self.client is None:
            raise ConnectorMissingCredentialError("WebDAV client not initialized")

        start_datetime = datetime.fromtimestamp(start, tz=timezone.utc)
        end_datetime = datetime.fromtimestamp(end, tz=timezone.utc)

        for batch in self._yield_webdav_documents(start_datetime, end_datetime):
            yield batch

    def validate_connector_settings(self) -> None:
        """Validate WebDAV connector settings
        
        Raises:
            ConnectorMissingCredentialError: If credentials are not loaded
            ConnectorValidationError: If settings are invalid
        """
        if self.client is None:
            raise ConnectorMissingCredentialError(
                "WebDAV credentials not loaded."
            )

        if not self.base_url:
            raise ConnectorValidationError(
                "No base URL was provided in connector settings."
            )

        try:
            if not self.client.exists(self.remote_path):
                raise ConnectorValidationError(
                    f"Remote path '{self.remote_path}' does not exist on WebDAV server."
                )

        except Exception as e:
            error_message = str(e)
            
            if "401" in error_message or "unauthorized" in error_message.lower():
                raise CredentialExpiredError(
                    "WebDAV credentials appear invalid or expired."
                )
            
            if "403" in error_message or "forbidden" in error_message.lower():
                raise InsufficientPermissionsError(
                    f"Insufficient permissions to access path '{self.remote_path}' on WebDAV server."
                )
            
            if "404" in error_message or "not found" in error_message.lower():
                raise ConnectorValidationError(
                    f"Remote path '{self.remote_path}' does not exist on WebDAV server."
                )

            raise ConnectorValidationError(
                f"Unexpected WebDAV client error: {e}"
            )


if __name__ == "__main__":
    credentials_dict = {
        "username": os.environ.get("WEBDAV_USERNAME"),
        "password": os.environ.get("WEBDAV_PASSWORD"),
    }

    connector = WebDAVConnector(
        base_url=os.environ.get("WEBDAV_URL") or "https://webdav.example.com",
        remote_path=os.environ.get("WEBDAV_PATH") or "/",
    )

    try:
        connector.load_credentials(credentials_dict)
        connector.validate_connector_settings()
        
        document_batch_generator = connector.load_from_state()
        for document_batch in document_batch_generator:
            print("First batch of documents:")
            for doc in document_batch:
                print(f"Document ID: {doc.id}")
                print(f"Semantic Identifier: {doc.semantic_identifier}")
                print(f"Source: {doc.source}")
                print(f"Updated At: {doc.doc_updated_at}")
                print("---")
            break

    except ConnectorMissingCredentialError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
