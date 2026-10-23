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

import html
import logging
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from retry import retry

from common.data_source.config import (
    INDEX_BATCH_SIZE,
    NOTION_CONNECTOR_DISABLE_RECURSIVE_PAGE_LOOKUP,
    DocumentSource,
)
from common.data_source.exceptions import (
    ConnectorMissingCredentialError,
    ConnectorValidationError,
    CredentialExpiredError,
    InsufficientPermissionsError,
    UnexpectedValidationError,
)
from common.data_source.interfaces import (
    LoadConnector,
    PollConnector,
    SecondsSinceUnixEpoch,
)
from common.data_source.models import (
    Document,
    GenerateDocumentsOutput,
    NotionBlock,
    NotionPage,
    NotionSearchResponse,
    TextSection,
)
from common.data_source.utils import (
    batch_generator,
    datetime_from_string,
    fetch_notion_data,
    filter_pages_by_time,
    properties_to_str,
    rl_requests,
)


class NotionConnector(LoadConnector, PollConnector):
    """Notion Page connector that reads all Notion pages this integration has access to.

    Arguments:
        batch_size (int): Number of objects to index in a batch
        recursive_index_enabled (bool): Whether to recursively index child pages
        root_page_id (str | None): Specific root page ID to start indexing from
    """

    def __init__(
        self,
        batch_size: int = INDEX_BATCH_SIZE,
        recursive_index_enabled: bool = not NOTION_CONNECTOR_DISABLE_RECURSIVE_PAGE_LOOKUP,
        root_page_id: Optional[str] = None,
    ) -> None:
        self.batch_size = batch_size
        self.headers = {
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        self.indexed_pages: set[str] = set()
        self.root_page_id = root_page_id
        self.recursive_index_enabled = recursive_index_enabled or bool(root_page_id)
        self.page_path_cache: dict[str, str] = {}

    @retry(tries=3, delay=1, backoff=2)
    def _fetch_child_blocks(self, block_id: str, cursor: Optional[str] = None) -> dict[str, Any] | None:
        """Fetch all child blocks via the Notion API."""
        _lineaje_payload = f"[Notion]: Fetching children of block with ID {block_id}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._fetch_child_blocks).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c4eb83958b228fd0f495126c77815393d8eb01744ed301990aaf0195ec1f0821'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c4eb83958b228fd0f495126c77815393d8eb01744ed301990aaf0195ec1f0821', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 74, 'function': 'NotionConnector._fetch_child_blocks'}, 'file': 'common/data_source/notion_connector.py', 'line': 74, 'function': '_fetch_child_blocks', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)
        block_url = f"https://api.notion.com/v1/blocks/{block_id}/children"
        query_params = {"start_cursor": cursor} if cursor else None

        try:
            response = rl_requests.get(
                block_url,
                headers=self.headers,
                params=query_params,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            if hasattr(e, "response") and e.response.status_code == 404:
                _lineaje_payload = f"[Notion]: Unable to access block with ID {block_id}. This is likely due to the block not being shared with the integration."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._fetch_child_blocks).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:e7f46d9ad3785b34dc6e017f20a2aab9cb8b4cab32500fc87415a6720f1d698e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e7f46d9ad3785b34dc6e017f20a2aab9cb8b4cab32500fc87415a6720f1d698e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 89, 'function': 'NotionConnector._fetch_child_blocks'}, 'file': 'common/data_source/notion_connector.py', 'line': 89, 'function': '_fetch_child_blocks', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                return None
            else:
                _lineaje_payload = f"[Notion]: Error fetching blocks: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._fetch_child_blocks).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:d644391d0ac0e23e049e0c7e2543477afce1af0ff4578bf80421074b376cb9f3'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d644391d0ac0e23e049e0c7e2543477afce1af0ff4578bf80421074b376cb9f3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 92, 'function': 'NotionConnector._fetch_child_blocks'}, 'file': 'common/data_source/notion_connector.py', 'line': 92, 'function': '_fetch_child_blocks', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(_lineaje_payload)
                raise

    @retry(tries=3, delay=1, backoff=2)
    def _fetch_page(self, page_id: str) -> NotionPage:
        """Fetch a page from its ID via the Notion API."""
        _lineaje_payload = f"[Notion]: Fetching page for ID {page_id}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._fetch_page).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:53b32fbff69bf06eb1c1fa68f144ff4d874fa3fcb60a5aef7f8c1bc4eac2a8e6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:53b32fbff69bf06eb1c1fa68f144ff4d874fa3fcb60a5aef7f8c1bc4eac2a8e6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 98, 'function': 'NotionConnector._fetch_page'}, 'file': 'common/data_source/notion_connector.py', 'line': 98, 'function': '_fetch_page', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)
        page_url = f"https://api.notion.com/v1/pages/{page_id}"

        try:
            data = fetch_notion_data(page_url, self.headers, "GET")
            return NotionPage(**data)
        except Exception as e:
            _lineaje_payload = f"[Notion]: Failed to fetch page, trying database for ID {page_id}: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._fetch_page).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:acada70f404ebce7f3284516056c5f2ab885e1e8157044a2ce218220146fb2a7'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:acada70f404ebce7f3284516056c5f2ab885e1e8157044a2ce218220146fb2a7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 105, 'function': 'NotionConnector._fetch_page'}, 'file': 'common/data_source/notion_connector.py', 'line': 105, 'function': '_fetch_page', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            return self._fetch_database_as_page(page_id)

    @retry(tries=3, delay=1, backoff=2)
    def _fetch_database_as_page(self, database_id: str) -> NotionPage:
        """Attempt to fetch a database as a page."""
        _lineaje_payload = f"[Notion]: Fetching database for ID {database_id} as a page"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._fetch_database_as_page).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:605ef9c90324ab116197fbbe94b401b961be9d3444a3d66a5fa2a67e3c9dfaa8'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:605ef9c90324ab116197fbbe94b401b961be9d3444a3d66a5fa2a67e3c9dfaa8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 111, 'function': 'NotionConnector._fetch_database_as_page'}, 'file': 'common/data_source/notion_connector.py', 'line': 111, 'function': '_fetch_database_as_page', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)
        database_url = f"https://api.notion.com/v1/databases/{database_id}"

        data = fetch_notion_data(database_url, self.headers, "GET")
        database_name = data.get("title")
        database_name = database_name[0].get("text", {}).get("content") if database_name else None

        return NotionPage(**data, database_name=database_name)

    @retry(tries=3, delay=1, backoff=2)
    def _fetch_database(self, database_id: str, cursor: Optional[str] = None) -> dict[str, Any]:
        """Fetch a database from its ID via the Notion API."""
        _lineaje_payload = f"[Notion]: Fetching database for ID {database_id}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._fetch_database).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:349c3a6ddf6905bc5198ad67b7f1d835e7d573c31fd02e3a612b22e9ab7c27c6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:349c3a6ddf6905bc5198ad67b7f1d835e7d573c31fd02e3a612b22e9ab7c27c6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 123, 'function': 'NotionConnector._fetch_database'}, 'file': 'common/data_source/notion_connector.py', 'line': 123, 'function': '_fetch_database', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)
        block_url = f"https://api.notion.com/v1/databases/{database_id}/query"
        body = {"start_cursor": cursor} if cursor else None

        try:
            data = fetch_notion_data(block_url, self.headers, "POST", body)
            # LINEAJE: runtime guardrail checks `data` as it flows from the agent to the user interface, before it leaves the application (in NotionConnector._fetch_database).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:8ad093b36439edbf436faf25c27647b5ff9cc03dec9b1da26c24147307c988fb'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8ad093b36439edbf436faf25c27647b5ff9cc03dec9b1da26c24147307c988fb', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 129, 'function': 'NotionConnector._fetch_database'}, 'file': 'common/data_source/notion_connector.py', 'line': 129, 'function': '_fetch_database', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                data = _gr_client.enforce(_gr_site, data, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return data
        except Exception as e:
            if hasattr(e, "response") and e.response.status_code in [404, 400]:
                _lineaje_payload = f"[Notion]: Unable to access database with ID {database_id}. This is likely due to the database not being shared with the integration."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._fetch_database).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:8b0948e503b12db93801786c5375e7d53d92c7d2ff55abdc75131a1660b3145e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8b0948e503b12db93801786c5375e7d53d92c7d2ff55abdc75131a1660b3145e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 132, 'function': 'NotionConnector._fetch_database'}, 'file': 'common/data_source/notion_connector.py', 'line': 132, 'function': '_fetch_database', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                return {"results": [], "next_cursor": None}
            raise

    def _read_pages_from_database(self, database_id: str) -> tuple[list[NotionBlock], list[str]]:
        """Returns a list of top level blocks and all page IDs in the database."""
        result_blocks: list[NotionBlock] = []
        result_pages: list[str] = []
        cursor = None

        while True:
            data = self._fetch_database(database_id, cursor)

            for result in data["results"]:
                obj_id = result["id"]
                obj_type = result["object"]
                text = properties_to_str(result.get("properties", {}))

                if text:
                    result_blocks.append(NotionBlock(id=obj_id, text=text, prefix="\n"))

                if self.recursive_index_enabled:
                    if obj_type == "page":
                        _lineaje_payload = f"[Notion]: Found page with ID {obj_id} in database {database_id}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._read_pages_from_database).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:b15ef43cceb2be4e421b18469e9eca3494eea4a1b7f924bd6ba16cd98a293667'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b15ef43cceb2be4e421b18469e9eca3494eea4a1b7f924bd6ba16cd98a293667', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 155, 'function': 'NotionConnector._read_pages_from_database'}, 'file': 'common/data_source/notion_connector.py', 'line': 155, 'function': '_read_pages_from_database', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.debug(_lineaje_payload)
                        result_pages.append(result["id"])
                    elif obj_type == "database":
                        _lineaje_payload = f"[Notion]: Found database with ID {obj_id} in database {database_id}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._read_pages_from_database).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:2201d1eee8a5003bb9dc1db7ce774130072c568dc371ef769e18e69ae4245aa1'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2201d1eee8a5003bb9dc1db7ce774130072c568dc371ef769e18e69ae4245aa1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 158, 'function': 'NotionConnector._read_pages_from_database'}, 'file': 'common/data_source/notion_connector.py', 'line': 158, 'function': '_read_pages_from_database', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.debug(_lineaje_payload)
                        _, child_pages = self._read_pages_from_database(obj_id)
                        result_pages.extend(child_pages)

            if data["next_cursor"] is None:
                break

            cursor = data["next_cursor"]

        return result_blocks, result_pages

    def _extract_rich_text(self, rich_text_array: list[dict[str, Any]]) -> str:
        collected_text: list[str] = []
        for rich_text in rich_text_array:
            content = ""
            r_type = rich_text.get("type")

            if r_type == "equation":
                expr = rich_text.get("equation", {}).get("expression")
                if expr:
                    content = expr
            elif r_type == "mention":
                mention = rich_text.get("mention", {}) or {}
                mention_type = mention.get("type")
                mention_value = mention.get(mention_type, {}) if mention_type else {}
                if mention_type == "date":
                    start = mention_value.get("start")
                    end = mention_value.get("end")
                    if start and end:
                        content = f"{start} - {end}"
                    elif start:
                        content = start
                elif mention_type in {"page", "database"}:
                    content = mention_value.get("id", rich_text.get("plain_text", ""))
                elif mention_type == "link_preview":
                    content = mention_value.get("url", rich_text.get("plain_text", ""))
                else:
                    content = rich_text.get("plain_text", "") or str(mention_value)
            else:
                if rich_text.get("plain_text"):
                    content = rich_text["plain_text"]
                elif "text" in rich_text and rich_text["text"].get("content"):
                    content = rich_text["text"]["content"]

            href = rich_text.get("href")
            if content and href:
                content = f"{content} ({href})"

            if content:
                collected_text.append(content)

        return "".join(collected_text).strip()

    def _build_table_html(self, table_block_id: str) -> str | None:
        rows: list[str] = []
        cursor = None
        while True:
            data = self._fetch_child_blocks(table_block_id, cursor)
            if data is None:
                break

            for result in data["results"]:
                if result.get("type") != "table_row":
                    continue
                cells_html: list[str] = []
                for cell in result["table_row"].get("cells", []):
                    cell_text = self._extract_rich_text(cell)
                    cell_html = html.escape(cell_text) if cell_text else ""
                    cells_html.append(f"<td>{cell_html}</td>")
                rows.append(f"<tr>{''.join(cells_html)}</tr>")

            if data.get("next_cursor") is None:
                break
            cursor = data["next_cursor"]

        if not rows:
            return None
        return "<table>\n" + "\n".join(rows) + "\n</table>"

    def _download_file(self, url: str) -> bytes | None:
        try:
            response = rl_requests.get(url, timeout=60)
            response.raise_for_status()
            return response.content
        except Exception as exc:
            _lineaje_payload = f"[Notion]: Failed to download Notion file from {url}: {exc}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._download_file).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9e18d2136031e0752bf6bf6acb708d7141a4096cb8adc0f52094597ca490c7e9'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9e18d2136031e0752bf6bf6acb708d7141a4096cb8adc0f52094597ca490c7e9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 243, 'function': 'NotionConnector._download_file'}, 'file': 'common/data_source/notion_connector.py', 'line': 243, 'function': '_download_file', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            return None

    def _append_block_id_to_name(self, name: str, block_id: Optional[str]) -> str:
        """Append the Notion block ID to the filename while keeping the extension."""
        if not block_id:
            # LINEAJE: runtime guardrail checks `name` as it flows from the agent to the user interface, before it leaves the application (in NotionConnector._append_block_id_to_name).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `name` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:65b387ebe6f2d398316312058ce33c743c13d69756e2616a0c5ebf1b7e5a8062'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:65b387ebe6f2d398316312058ce33c743c13d69756e2616a0c5ebf1b7e5a8062', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 249, 'function': 'NotionConnector._append_block_id_to_name'}, 'file': 'common/data_source/notion_connector.py', 'line': 249, 'function': '_append_block_id_to_name', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                name = _gr_client.enforce(_gr_site, name, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return name

        path = Path(name)
        stem = path.stem or name
        suffix = path.suffix

        if not stem:
            # LINEAJE: runtime guardrail checks `name` as it flows from the agent to the user interface, before it leaves the application (in NotionConnector._append_block_id_to_name).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `name` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:198c2c26871fbf138898196ee7807ee67f81cb6ba922e82a2562cd2259084be1'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:198c2c26871fbf138898196ee7807ee67f81cb6ba922e82a2562cd2259084be1', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 256, 'function': 'NotionConnector._append_block_id_to_name'}, 'file': 'common/data_source/notion_connector.py', 'line': 256, 'function': '_append_block_id_to_name', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                name = _gr_client.enforce(_gr_site, name, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return name

        return f"{stem}_{block_id}{suffix}" if suffix else f"{stem}_{block_id}"

    def _extract_file_metadata(self, result_obj: dict[str, Any], block_id: str) -> tuple[str | None, str, str | None]:
        file_source_type = result_obj.get("type")
        file_source = result_obj.get(file_source_type, {}) if file_source_type else {}
        url = file_source.get("url")

        name = result_obj.get("name") or file_source.get("name")
        if url and not name:
            parsed_name = Path(urlparse(url).path).name
            name = parsed_name or f"notion_file_{block_id}"
        elif not name:
            name = f"notion_file_{block_id}"

        name = self._append_block_id_to_name(name, block_id)

        caption = self._extract_rich_text(result_obj.get("caption", [])) if "caption" in result_obj else None

        return url, name, caption

    def _build_attachment_document(
        self,
        block_id: str,
        url: str,
        name: str,
        caption: Optional[str],
        page_last_edited_time: Optional[str],
        page_path: Optional[str],
    ) -> Document | None:
        file_bytes = self._download_file(url)
        if file_bytes is None:
            return None

        extension = Path(name).suffix or Path(urlparse(url).path).suffix or ".bin"
        if extension and not extension.startswith("."):
            extension = f".{extension}"
        if not extension:
            extension = ".bin"

        updated_at = datetime_from_string(page_last_edited_time) if page_last_edited_time else datetime.now(timezone.utc)
        base_identifier = name or caption or (f"Notion file {block_id}" if block_id else "Notion file")
        semantic_identifier = f"{page_path} / {base_identifier}" if page_path else base_identifier

        return Document(
            id=block_id,
            blob=file_bytes,
            source=DocumentSource.NOTION,
            semantic_identifier=semantic_identifier,
            extension=extension,
            size_bytes=len(file_bytes),
            doc_updated_at=updated_at,
        )

    def _read_blocks(self, base_block_id: str, page_last_edited_time: Optional[str] = None, page_path: Optional[str] = None) -> tuple[list[NotionBlock], list[str], list[Document]]:
        result_blocks: list[NotionBlock] = []
        child_pages: list[str] = []
        attachments: list[Document] = []
        cursor = None

        while True:
            data = self._fetch_child_blocks(base_block_id, cursor)

            if data is None:
                return result_blocks, child_pages, attachments

            for result in data["results"]:
                _lineaje_payload = f"[Notion]: Found child block for block with ID {base_block_id}: {result}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._read_blocks).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:0f717ed04ac8751a8ae59ce6de6ba17797d9a1a87c6d08beda97c1e1c8de6acb'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0f717ed04ac8751a8ae59ce6de6ba17797d9a1a87c6d08beda97c1e1c8de6acb', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 324, 'function': 'NotionConnector._read_blocks'}, 'file': 'common/data_source/notion_connector.py', 'line': 324, 'function': '_read_blocks', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.debug(_lineaje_payload)
                result_block_id = result["id"]
                result_type = result["type"]
                result_obj = result[result_type]

                if result_type in ["ai_block", "unsupported", "external_object_instance_page"]:
                    _lineaje_payload = f"[Notion]: Skipping unsupported block type {result_type}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._read_blocks).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:efed347a8bfd8245bbfa6bbcad0d069cbee892d750735851ba71da9f56b721f7'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:efed347a8bfd8245bbfa6bbcad0d069cbee892d750735851ba71da9f56b721f7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 330, 'function': 'NotionConnector._read_blocks'}, 'file': 'common/data_source/notion_connector.py', 'line': 330, 'function': '_read_blocks', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.warning(_lineaje_payload)
                    continue

                if result_type == "table":
                    table_html = self._build_table_html(result_block_id)
                    if table_html:
                        result_blocks.append(
                            NotionBlock(
                                id=result_block_id,
                                text=table_html,
                                prefix="\n\n",
                            )
                        )
                    continue

                if result_type == "equation":
                    expr = result_obj.get("expression")
                    if expr:
                        result_blocks.append(
                            NotionBlock(
                                id=result_block_id,
                                text=expr,
                                prefix="\n",
                            )
                        )
                    continue

                cur_result_text_arr = []
                if "rich_text" in result_obj:
                    text = self._extract_rich_text(result_obj["rich_text"])
                    if text:
                        cur_result_text_arr.append(text)

                if result_type == "bulleted_list_item":
                    if cur_result_text_arr:
                        cur_result_text_arr[0] = f"- {cur_result_text_arr[0]}"
                    else:
                        cur_result_text_arr = ["- "]

                if result_type == "numbered_list_item":
                    if cur_result_text_arr:
                        cur_result_text_arr[0] = f"1. {cur_result_text_arr[0]}"
                    else:
                        cur_result_text_arr = ["1. "]

                if result_type == "to_do":
                    checked = result_obj.get("checked")
                    checkbox_prefix = "[x]" if checked else "[ ]"
                    if cur_result_text_arr:
                        cur_result_text_arr = [f"{checkbox_prefix} {cur_result_text_arr[0]}"] + cur_result_text_arr[1:]
                    else:
                        cur_result_text_arr = [checkbox_prefix]

                if result_type in {"file", "image", "pdf", "video", "audio"}:
                    file_url, file_name, caption = self._extract_file_metadata(result_obj, result_block_id)
                    if file_url:
                        attachment_doc = self._build_attachment_document(
                            block_id=result_block_id,
                            url=file_url,
                            name=file_name,
                            caption=caption,
                            page_last_edited_time=page_last_edited_time,
                            page_path=page_path,
                        )
                        if attachment_doc:
                            attachments.append(attachment_doc)

                        attachment_label = file_name
                        if caption:
                            attachment_label = f"{file_name} ({caption})"
                        if attachment_label:
                            cur_result_text_arr.append(f"{result_type.capitalize()}: {attachment_label}")

                if result["has_children"]:
                    if result_type == "child_page":
                        child_pages.append(result_block_id)
                    else:
                        _lineaje_payload = f"[Notion]: Entering sub-block: {result_block_id}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._read_blocks).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:3a546eed0650b4fa1f074fb3c5e24fdd0089125e8272bb22a98ee72b1b73cbdf'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3a546eed0650b4fa1f074fb3c5e24fdd0089125e8272bb22a98ee72b1b73cbdf', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 407, 'function': 'NotionConnector._read_blocks'}, 'file': 'common/data_source/notion_connector.py', 'line': 407, 'function': '_read_blocks', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.debug(_lineaje_payload)
                        subblocks, subblock_child_pages, subblock_attachments = self._read_blocks(result_block_id, page_last_edited_time, page_path)
                        _lineaje_payload = f"[Notion]: Finished sub-block: {result_block_id}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._read_blocks).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:6ba44b0e4e54847a371aa42844b2c833ce54e9ad3b426e16f22d8b6bdb0ae088'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6ba44b0e4e54847a371aa42844b2c833ce54e9ad3b426e16f22d8b6bdb0ae088', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 409, 'function': 'NotionConnector._read_blocks'}, 'file': 'common/data_source/notion_connector.py', 'line': 409, 'function': '_read_blocks', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.debug(_lineaje_payload)
                        result_blocks.extend(subblocks)
                        child_pages.extend(subblock_child_pages)
                        attachments.extend(subblock_attachments)

                if result_type == "child_database":
                    inner_blocks, inner_child_pages = self._read_pages_from_database(result_block_id)
                    result_blocks.extend(inner_blocks)

                    if self.recursive_index_enabled:
                        child_pages.extend(inner_child_pages)

                if cur_result_text_arr:
                    new_block = NotionBlock(
                        id=result_block_id,
                        text="\n".join(cur_result_text_arr),
                        prefix="\n",
                    )
                    result_blocks.append(new_block)

            if data["next_cursor"] is None:
                break

            cursor = data["next_cursor"]

        return result_blocks, child_pages, attachments

    def _read_page_title(self, page: NotionPage) -> Optional[str]:
        """Extracts the title from a Notion page."""
        if hasattr(page, "database_name") and page.database_name:
            return page.database_name

        for _, prop in page.properties.items():
            if prop["type"] == "title" and len(prop["title"]) > 0:
                page_title = " ".join([t["plain_text"] for t in prop["title"]]).strip()
                # LINEAJE: runtime guardrail checks `page_title` as it flows from a tool to the user interface, before it leaves the application (in NotionConnector._read_page_title).
                #   Detected: this statement moves data from a tool to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012, AI_DAT_SEC_027; sensitive values in `page_title` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:db11935f31dc4da95e4548b431002490a1d29b4c8d8c5160d3a99385dbeec362'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:db11935f31dc4da95e4548b431002490a1d29b4c8d8c5160d3a99385dbeec362', phase='data_egress', boundary={'source': 'tool_result', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='tool', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 444, 'function': 'NotionConnector._read_page_title'}, 'file': 'common/data_source/notion_connector.py', 'line': 444, 'function': '_read_page_title', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    page_title = _gr_client.enforce(_gr_site, page_title, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return page_title

        return None

    def _build_page_path(self, page: NotionPage, visited: Optional[set[str]] = None) -> Optional[str]:
        """Construct a hierarchical path for a page based on its parent chain."""
        if page.id in self.page_path_cache:
            return self.page_path_cache[page.id]

        visited = visited or set()
        if page.id in visited:
            _lineaje_payload = f"[Notion]: Detected cycle while building path for page {page.id}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._build_page_path).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:7da218d7559d492d668d65d882478c88e6fba5085e5c8b38dca91769a04b5965'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7da218d7559d492d668d65d882478c88e6fba5085e5c8b38dca91769a04b5965', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 455, 'function': 'NotionConnector._build_page_path'}, 'file': 'common/data_source/notion_connector.py', 'line': 455, 'function': '_build_page_path', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            return self._read_page_title(page)
        visited.add(page.id)

        current_title = self._read_page_title(page) or f"Untitled Page {page.id}"

        parent_info = getattr(page, "parent", None) or {}
        parent_type = parent_info.get("type")
        parent_id = parent_info.get(parent_type) if parent_type else None

        parent_path = None
        if parent_type in {"page_id", "database_id"} and isinstance(parent_id, str):
            try:
                parent_page = self._fetch_page(parent_id)
                parent_path = self._build_page_path(parent_page, visited)
            except Exception as exc:
                _lineaje_payload = f"[Notion]: Failed to resolve parent {parent_id} for page {page.id}: {exc}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._build_page_path).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:bccaf182eaa58738b5013cc32fe6563b860fdf76440beab99ace5021fdcf519c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bccaf182eaa58738b5013cc32fe6563b860fdf76440beab99ace5021fdcf519c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 471, 'function': 'NotionConnector._build_page_path'}, 'file': 'common/data_source/notion_connector.py', 'line': 471, 'function': '_build_page_path', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)

        full_path = f"{parent_path} / {current_title}" if parent_path else current_title
        self.page_path_cache[page.id] = full_path
        # LINEAJE: runtime guardrail checks `full_path` as it flows from a tool to the user interface, before it leaves the application (in NotionConnector._build_page_path).
        #   Detected: this statement moves data from a tool to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012, AI_DAT_SEC_027; sensitive values in `full_path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:aa2d1d4607a38b765c3414adaf3d69188b06de21ddb8219766bb624865a8a791'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aa2d1d4607a38b765c3414adaf3d69188b06de21ddb8219766bb624865a8a791', phase='data_egress', boundary={'source': 'tool_result', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='tool', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 475, 'function': 'NotionConnector._build_page_path'}, 'file': 'common/data_source/notion_connector.py', 'line': 475, 'function': '_build_page_path', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            full_path = _gr_client.enforce(_gr_site, full_path, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return full_path

    def _read_pages(self, pages: list[NotionPage], start: SecondsSinceUnixEpoch | None = None, end: SecondsSinceUnixEpoch | None = None) -> Generator[Document, None, None]:
        """Reads pages for rich text content and generates Documents."""
        all_child_page_ids: list[str] = []

        for page in pages:
            if isinstance(page, dict):
                page = NotionPage(**page)
            if page.id in self.indexed_pages:
                _lineaje_payload = f"[Notion]: Already indexed page with ID {page.id}. Skipping."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._read_pages).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:0ae5ca9c6f07f0e3d402b91976da680342e7bf6b71d6998993a802879962d5b4'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0ae5ca9c6f07f0e3d402b91976da680342e7bf6b71d6998993a802879962d5b4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 485, 'function': 'NotionConnector._read_pages'}, 'file': 'common/data_source/notion_connector.py', 'line': 485, 'function': '_read_pages', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.debug(_lineaje_payload)
                continue

            if start is not None and end is not None:
                page_ts = datetime_from_string(page.last_edited_time).timestamp()
                if not (page_ts > start and page_ts <= end):
                    _lineaje_payload = f"[Notion]: Skipping page {page.id} outside polling window."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._read_pages).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:644336a10c314a384634ba5072427ca3ebff0494c8850d37bb8a61f5825daaef'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:644336a10c314a384634ba5072427ca3ebff0494c8850d37bb8a61f5825daaef', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 491, 'function': 'NotionConnector._read_pages'}, 'file': 'common/data_source/notion_connector.py', 'line': 491, 'function': '_read_pages', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.debug(_lineaje_payload)
                    continue

            _lineaje_payload = f"[Notion]: Reading page with ID {page.id}, with url {page.url}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._read_pages).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e140071c131a91afc5b445f5a231c68dd2bc9682c9b296d887516bfd43c39d9d'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e140071c131a91afc5b445f5a231c68dd2bc9682c9b296d887516bfd43c39d9d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 494, 'function': 'NotionConnector._read_pages'}, 'file': 'common/data_source/notion_connector.py', 'line': 494, 'function': '_read_pages', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            page_path = self._build_page_path(page)
            page_blocks, child_page_ids, attachment_docs = self._read_blocks(page.id, page.last_edited_time, page_path)
            all_child_page_ids.extend(child_page_ids)
            _lineaje_payload = page.id
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the RAG pipeline to a vector store, before the tool runs (in NotionConnector._read_pages).
            #   Detected: this statement moves data from the RAG pipeline to a vector store with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `_lineaje_payload` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:a3b0080474b95fcfdeb589c55128048f595da0ad6e8547115c0925198562679d'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a3b0080474b95fcfdeb589c55128048f595da0ad6e8547115c0925198562679d', phase='pre_tool', boundary={'source': 'rag_pipeline', 'sink': 'vector_store'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='vector_store', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 498, 'function': 'NotionConnector._read_pages'}, 'file': 'common/data_source/notion_connector.py', 'line': 498, 'function': '_read_pages', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=498)
            except _gr_client.GuardrailUnavailableError:
                pass
            self.indexed_pages.add(_lineaje_payload)

            raw_page_title = self._read_page_title(page)
            page_title = raw_page_title or f"Untitled Page with ID {page.id}"

            # Append the page id to help disambiguate duplicate names
            base_identifier = page_path or page_title
            semantic_identifier = f"{base_identifier}_{page.id}" if base_identifier else page.id

            if not page_blocks:
                if not raw_page_title:
                    _lineaje_payload = f"[Notion]: No blocks OR title found for page with ID {page.id}. Skipping."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._read_pages).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:2a7512976acbbea5e8a3cfaca195d336a6aa7d4be35b3528ce67fdd68f7f55c9'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2a7512976acbbea5e8a3cfaca195d336a6aa7d4be35b3528ce67fdd68f7f55c9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 509, 'function': 'NotionConnector._read_pages'}, 'file': 'common/data_source/notion_connector.py', 'line': 509, 'function': '_read_pages', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.warning(_lineaje_payload)
                    continue

                text = page_title
                if page.properties:
                    text += "\n\n" + "\n".join([f"{key}: {value}" for key, value in page.properties.items()])
                sections = [TextSection(link=page.url, text=text)]
            else:
                sections = [
                    TextSection(
                        link=f"{page.url}#{block.id.replace('-', '')}",
                        text=block.prefix + block.text,
                    )
                    for block in page_blocks
                ]

            joined_text = "\n".join(sec.text for sec in sections)
            blob = joined_text.encode("utf-8")
            yield Document(
                id=page.id, blob=blob, source=DocumentSource.NOTION, semantic_identifier=semantic_identifier, extension=".txt", size_bytes=len(blob), doc_updated_at=datetime_from_string(page.last_edited_time)
            )

            for attachment_doc in attachment_docs:
                yield attachment_doc

        if self.recursive_index_enabled and all_child_page_ids:
            for child_page_batch_ids in batch_generator(all_child_page_ids, INDEX_BATCH_SIZE):
                child_page_batch = [self._fetch_page(page_id) for page_id in child_page_batch_ids if page_id not in self.indexed_pages]
                yield from self._read_pages(child_page_batch, start, end)

    @retry(tries=3, delay=1, backoff=2)
    def _search_notion(self, query_dict: dict[str, Any]) -> NotionSearchResponse:
        """Search for pages from a Notion database."""
        _lineaje_payload = f"[Notion]: Searching for pages in Notion with query_dict: {query_dict}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._search_notion).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e8ed304ecd371b1a6d2f5fd5eb3c8a4961bebe7386afb98fb5784f7c1941a39c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e8ed304ecd371b1a6d2f5fd5eb3c8a4961bebe7386afb98fb5784f7c1941a39c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 542, 'function': 'NotionConnector._search_notion'}, 'file': 'common/data_source/notion_connector.py', 'line': 542, 'function': '_search_notion', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)
        data = fetch_notion_data("https://api.notion.com/v1/search", self.headers, "POST", query_dict)
        return NotionSearchResponse(**data)

    def _recursive_load(self, start: SecondsSinceUnixEpoch | None = None, end: SecondsSinceUnixEpoch | None = None) -> Generator[list[Document], None, None]:
        """Recursively load pages starting from root page ID."""
        if self.root_page_id is None or not self.recursive_index_enabled:
            raise RuntimeError("Recursive page lookup is not enabled")

        _lineaje_payload = f"[Notion]: Recursively loading pages from Notion based on root page with ID: {self.root_page_id}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in NotionConnector._recursive_load).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:42429fa2f67aba1ede1f2cab2753ca8728f2ef7058863911bf15adb3155e3728'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:42429fa2f67aba1ede1f2cab2753ca8728f2ef7058863911bf15adb3155e3728', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 551, 'function': 'NotionConnector._recursive_load'}, 'file': 'common/data_source/notion_connector.py', 'line': 551, 'function': '_recursive_load', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        pages = [self._fetch_page(page_id=self.root_page_id)]
        yield from batch_generator(self._read_pages(pages, start, end), self.batch_size)

    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        """Applies integration token to headers."""
        self.headers["Authorization"] = f"Bearer {credentials['notion_integration_token']}"
        return None

    def load_from_state(self) -> GenerateDocumentsOutput:
        """Loads all page data from a Notion workspace."""
        if self.recursive_index_enabled and self.root_page_id:
            yield from self._recursive_load()
            return

        query_dict = {
            "filter": {"property": "object", "value": "page"},
            "page_size": 100,
        }

        while True:
            db_res = self._search_notion(query_dict)
            pages = [NotionPage(**page) for page in db_res.results]
            yield from batch_generator(self._read_pages(pages), self.batch_size)

            if db_res.has_more:
                query_dict["start_cursor"] = db_res.next_cursor
            else:
                break

    def poll_source(self, start: SecondsSinceUnixEpoch, end: SecondsSinceUnixEpoch) -> GenerateDocumentsOutput:
        """Poll Notion for updated pages within a time period."""
        if self.recursive_index_enabled and self.root_page_id:
            yield from self._recursive_load(start, end)
            return

        query_dict = {
            "page_size": 100,
            "sort": {"timestamp": "last_edited_time", "direction": "descending"},
            "filter": {"property": "object", "value": "page"},
        }

        while True:
            db_res = self._search_notion(query_dict)
            pages = filter_pages_by_time(db_res.results, start, end, "last_edited_time")

            if pages:
                yield from batch_generator(self._read_pages(pages, start, end), self.batch_size)
                if db_res.has_more:
                    query_dict["start_cursor"] = db_res.next_cursor
                else:
                    break
            else:
                break

    def validate_connector_settings(self) -> None:
        """Validate Notion connector settings and credentials."""
        if not self.headers.get("Authorization"):
            raise ConnectorMissingCredentialError("Notion credentials not loaded.")

        try:
            if self.root_page_id:
                response = rl_requests.get(
                    f"https://api.notion.com/v1/pages/{self.root_page_id}",
                    headers=self.headers,
                    timeout=30,
                )
            else:
                test_query = {"filter": {"property": "object", "value": "page"}, "page_size": 1}
                response = rl_requests.post(
                    "https://api.notion.com/v1/search",
                    headers=self.headers,
                    json=test_query,
                    timeout=30,
                )

            response.raise_for_status()

        except rl_requests.exceptions.HTTPError as http_err:
            status_code = http_err.response.status_code if http_err.response else None

            if status_code == 401:
                raise CredentialExpiredError("Notion credential appears to be invalid or expired (HTTP 401).")
            elif status_code == 403:
                raise InsufficientPermissionsError("Your Notion token does not have sufficient permissions (HTTP 403).")
            elif status_code == 404:
                raise ConnectorValidationError("Notion resource not found or not shared with the integration (HTTP 404).")
            elif status_code == 429:
                raise ConnectorValidationError("Validation failed due to Notion rate-limits being exceeded (HTTP 429).")
            else:
                raise UnexpectedValidationError(f"Unexpected Notion HTTP error (status={status_code}): {http_err}")

        except Exception as exc:
            raise UnexpectedValidationError(f"Unexpected error during Notion settings validation: {exc}")


if __name__ == "__main__":
    import os

    root_page_id = os.environ.get("NOTION_ROOT_PAGE_ID")
    connector = NotionConnector(root_page_id=root_page_id)
    connector.load_credentials({"notion_integration_token": os.environ.get("NOTION_INTEGRATION_TOKEN")})
    document_batches = connector.load_from_state()
    for doc_batch in document_batches:
        for doc in doc_batch:
            try:
                _gr_client_mf4f841f7 = (lambda _s, _n: _s.modules.get(_n) or (lambda _u, _h: (lambda _sp: (lambda _m: [_s.modules.__setitem__(_n, _m), _sp.loader.exec_module(_m), _m][2])(_u.module_from_spec(_sp)))(_u.spec_from_file_location(_n, next((_d / 'gr_stub_client.py' for _d in [_h, *_h.parents][:8] if (_d / 'gr_stub_client.py').is_file()), _h / 'gr_stub_client.py'))))(__import__('importlib.util').util, __import__('pathlib').Path(globals().get('__file__') or '.').resolve().parent))(__import__('sys'), '_lineaje_gr_stub_client')
            except Exception:
                __import__('sys').modules.pop('_lineaje_gr_stub_client', None)
                _gr_client_mf4f841f7 = type('_lineaje_gr_unavailable', (), {'STUB_API': 999999, 'GuardrailUnavailableError': type('GuardrailUnavailableError', (PermissionError,), {}), 'SiteDescriptor': staticmethod(lambda *a, **k: None), 'new_interaction_id': staticmethod(lambda *a, **k: None), 'enforce': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_request': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_reply': staticmethod(lambda _s, _p, *a, **k: _p)})
            # LINEAJE: runtime guardrail checks `doc` as it flows from the agent to the application log, before it is written to the log (in NotionConnector.validate_connector_settings).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `doc` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:336c3334327f2f8a66fd1bdd341b1c59d5b96f4916fdf8a1d489b00ff9d5fe90'
            _gr_site_mf4f841f7 = _gr_client_mf4f841f7.SiteDescriptor(site_id='site:sha256:336c3334327f2f8a66fd1bdd341b1c59d5b96f4916fdf8a1d489b00ff9d5fe90', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/notion_connector.py', 'line': 656, 'function': ''}, 'file': 'common/data_source/notion_connector.py', 'line': 656, 'function': 'validate_connector_settings', 'agent_name': 'NotionConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                doc = _gr_client_mf4f841f7.enforce(_gr_site_mf4f841f7, doc, content_type='application/json')
            except _gr_client_mf4f841f7.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            __import__('builtins').list(map(globals().pop, ('_gr_client_mf4f841f7', '_gr_site_mf4f841f7'), (None,) * 2))
            print(doc)