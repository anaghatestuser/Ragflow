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

#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import asyncio
import logging
import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from string import Template
from typing import Any, Literal, Protocol

from typing_extensions import override

from common.constants import MCPServerType
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

MCPTaskType = Literal["list_tools", "tool_call"]
MCPTask = tuple[MCPTaskType, dict[str, Any], asyncio.Queue[Any]]


class ToolCallSession(Protocol):
    def tool_call(self, name: str, arguments: dict[str, Any]) -> str: ...


class MCPToolCallSession(ToolCallSession):
    _ALL_INSTANCES: weakref.WeakSet["MCPToolCallSession"] = weakref.WeakSet()

    def __init__(self, mcp_server: Any, server_variables: dict[str, Any] | None = None) -> None:
        self.__class__._ALL_INSTANCES.add(self)

        self._mcp_server = mcp_server
        self._server_variables = server_variables or {}
        self._queue = asyncio.Queue()
        self._close = False

        self._event_loop = asyncio.new_event_loop()
        self._thread_pool = ThreadPoolExecutor(max_workers=1)
        self._thread_pool.submit(self._event_loop.run_forever)

        asyncio.run_coroutine_threadsafe(self._mcp_server_loop(), self._event_loop)

    async def _mcp_server_loop(self) -> None:
        url = self._mcp_server.url.strip()
        raw_headers: dict[str, str] = self._mcp_server.headers or {}
        headers: dict[str, str] = {}

        for h, v in raw_headers.items():
            nh = Template(h).safe_substitute(self._server_variables)
            nv = Template(v).safe_substitute(self._server_variables)
            if nh.strip() and nv.strip().strip("Bearer"):
                headers[nh] = nv

        if self._mcp_server.server_type == MCPServerType.SSE:
            # SSE transport
            try:
                async with sse_client(url, headers) as stream:
                    async with ClientSession(*stream) as client_session:
                        try:
                            await asyncio.wait_for(client_session.initialize(), timeout=5)
                            _lineaje_payload = "client_session initialized successfully"
                            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession._mcp_server_loop).
                            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                            #   Do not remove without review. site_id='site:sha256:5b456895572d8e83dbdd19fb3005538227bb786039be7c18d7583c43380d77a4'
                            _gr_client = _lineaje_load_gr_client()
                            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5b456895572d8e83dbdd19fb3005538227bb786039be7c18d7583c43380d77a4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 77, 'function': 'MCPToolCallSession._mcp_server_loop'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 77, 'function': '_mcp_server_loop', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                            try:
                                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                            except _gr_client.GuardrailUnavailableError:
                                pass
                            except PermissionError:
                                pass
                            logging.info(_lineaje_payload)
                            await self._process_mcp_tasks(client_session)
                        except asyncio.TimeoutError:
                            msg = f"Timeout initializing client_session for server {self._mcp_server.id}"
                            # LINEAJE: runtime guardrail checks `msg` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession._mcp_server_loop).
                            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                            #   Do not remove without review. site_id='site:sha256:1428d9371fdf175bc8f92be55cda1c9adec988bb72b863d04f77e0b30a5ae8dd'
                            _gr_client = _lineaje_load_gr_client()
                            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1428d9371fdf175bc8f92be55cda1c9adec988bb72b863d04f77e0b30a5ae8dd', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 81, 'function': 'MCPToolCallSession._mcp_server_loop'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 81, 'function': '_mcp_server_loop', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                            try:
                                msg = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, msg, content_type='application/json'))
                            except _gr_client.GuardrailUnavailableError:
                                pass
                            except PermissionError:
                                pass
                            logging.error(msg)
                            await self._process_mcp_tasks(None, msg)
                        except asyncio.CancelledError:
                            _lineaje_payload = f"SSE transport MCP session cancelled for server {self._mcp_server.id}"
                            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession._mcp_server_loop).
                            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                            #   Do not remove without review. site_id='site:sha256:74ffef109406ae670c182e9763450aeb5a0235c80f3036778f66f76e82ac3af5'
                            _gr_client = _lineaje_load_gr_client()
                            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:74ffef109406ae670c182e9763450aeb5a0235c80f3036778f66f76e82ac3af5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 84, 'function': 'MCPToolCallSession._mcp_server_loop'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 84, 'function': '_mcp_server_loop', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                            try:
                                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                            except _gr_client.GuardrailUnavailableError:
                                pass
                            except PermissionError:
                                pass
                            logging.warning(_lineaje_payload)
                            return
            except Exception:
                msg = "Connection failed (possibly due to auth error). Please check authentication settings first"
                await self._process_mcp_tasks(None, msg)

        elif self._mcp_server.server_type == MCPServerType.STREAMABLE_HTTP:
            # Streamable HTTP transport
            try:
                async with streamablehttp_client(url, headers) as (read_stream, write_stream, _):
                    async with ClientSession(read_stream, write_stream) as client_session:
                        try:
                            await asyncio.wait_for(client_session.initialize(), timeout=5)
                            _lineaje_payload = "client_session initialized successfully"
                            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession._mcp_server_loop).
                            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                            #   Do not remove without review. site_id='site:sha256:9a0ec68cad5587ccd3263194da1a7b198b7b01d5055a796dd8fdb6162f9485a6'
                            _gr_client = _lineaje_load_gr_client()
                            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9a0ec68cad5587ccd3263194da1a7b198b7b01d5055a796dd8fdb6162f9485a6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 97, 'function': 'MCPToolCallSession._mcp_server_loop'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 97, 'function': '_mcp_server_loop', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                            try:
                                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                            except _gr_client.GuardrailUnavailableError:
                                pass
                            except PermissionError:
                                pass
                            logging.info(_lineaje_payload)
                            await self._process_mcp_tasks(client_session)
                        except asyncio.TimeoutError:
                            msg = f"Timeout initializing client_session for server {self._mcp_server.id}"
                            # LINEAJE: runtime guardrail checks `msg` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession._mcp_server_loop).
                            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                            #   Do not remove without review. site_id='site:sha256:a1902738d69336b579eb3e81eb7b2ce44b86baf0a3ddf331ef630bac7cce4e8e'
                            _gr_client = _lineaje_load_gr_client()
                            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a1902738d69336b579eb3e81eb7b2ce44b86baf0a3ddf331ef630bac7cce4e8e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 101, 'function': 'MCPToolCallSession._mcp_server_loop'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 101, 'function': '_mcp_server_loop', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                            try:
                                msg = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, msg, content_type='application/json'))
                            except _gr_client.GuardrailUnavailableError:
                                pass
                            except PermissionError:
                                pass
                            logging.error(msg)
                            await self._process_mcp_tasks(None, msg)
                        except asyncio.CancelledError:
                            _lineaje_payload = f"STREAMABLE_HTTP MCP session cancelled for server {self._mcp_server.id}"
                            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession._mcp_server_loop).
                            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                            #   Do not remove without review. site_id='site:sha256:aedc28c19231effbb869a046ce0b1b5f0266b82cf3fbfe559a40d415a11d6d40'
                            _gr_client = _lineaje_load_gr_client()
                            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aedc28c19231effbb869a046ce0b1b5f0266b82cf3fbfe559a40d415a11d6d40', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 104, 'function': 'MCPToolCallSession._mcp_server_loop'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 104, 'function': '_mcp_server_loop', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                            try:
                                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                            except _gr_client.GuardrailUnavailableError:
                                pass
                            except PermissionError:
                                pass
                            logging.warning(_lineaje_payload)
                            return
            except Exception as e:
                # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession._mcp_server_loop).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f86ff0cb056130354bc2ead176f5159637efe72af5b0fa7b06751b9ec91f0d32'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f86ff0cb056130354bc2ead176f5159637efe72af5b0fa7b06751b9ec91f0d32', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 107, 'function': 'MCPToolCallSession._mcp_server_loop'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 107, 'function': '_mcp_server_loop', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    e = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, e, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(e)
                msg = "Connection failed (possibly due to auth error). Please check authentication settings first"
                await self._process_mcp_tasks(None, msg)

        else:
            await self._process_mcp_tasks(None,
                                          f"Unsupported MCP server type: {self._mcp_server.server_type}, id: {self._mcp_server.id}")

    async def _process_mcp_tasks(self, client_session: ClientSession | None, error_message: str | None = None) -> None:
        while not self._close:
            try:
                mcp_task, arguments, result_queue = await asyncio.wait_for(self._queue.get(), timeout=1)
                # LINEAJE: runtime guardrail checks `result_queue` as it flows from an external API to the agent, after the tool returns (in MCPToolCallSession._process_mcp_tasks).
                #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `result_queue` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f84078c334c3459f4bfd1d6037cedf0f9f1a5f4d0a98197283936b7594c3d9be'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f84078c334c3459f4bfd1d6037cedf0f9f1a5f4d0a98197283936b7594c3d9be', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 118, 'function': 'MCPToolCallSession._process_mcp_tasks'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 118, 'function': '_process_mcp_tasks', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    result_queue = _gr_client.enforce(_gr_site, result_queue, content_type='application/json', variable_name='result_queue', source_file=__file__, before_line=118)
                except _gr_client.GuardrailUnavailableError:
                    pass
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            _lineaje_payload = f"Got MCP task {mcp_task} arguments {arguments}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession._process_mcp_tasks).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d600921f483565a6b6da2d215e4baff27b55aa385c52e108c0e6f3268c63ec06'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d600921f483565a6b6da2d215e4baff27b55aa385c52e108c0e6f3268c63ec06', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 124, 'function': 'MCPToolCallSession._process_mcp_tasks'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 124, 'function': '_process_mcp_tasks', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.debug(_lineaje_payload)

            r: Any = None

            if not client_session or error_message:
                r = ValueError(error_message)
                try:
                    await result_queue.put(r)
                except asyncio.CancelledError:
                    break
                continue

            try:
                if mcp_task == "list_tools":
                    r = await client_session.list_tools()
                elif mcp_task == "tool_call":
                    try:
                        _lineaje_obs = _lineaje_load_gr_client()
                        _lineaje_obs_site = _lineaje_obs.SiteDescriptor(site_id='site:sha256:a89ddb1a905c330b6d2a15e85f99b7afa49a7fd67b0f088a125af06b2fdb547b', phase='', boundary={}, fail_mode='ALLOW', source_type='agent', destination_type='tool', project='tree', organization='', components={'file': 'common/mcp_tool_call_conn.py', 'line': 140, 'function': '_process_mcp_tasks', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'call_target': 'client_session.call_tool', 'tool_protocol': 'mcp', 'tool_protocol_source': 'scan: call_tool on a client session', 'not_on_graph': True}, observe_only=True)
                        await __import__('asyncio').to_thread(lambda: _lineaje_obs.enforce(_lineaje_obs_site, {'activity': 'mcp_call'}, content_type='application/json'))
                    except Exception:
                        pass
                    r = await client_session.call_tool(**arguments)
                else:
                    r = ValueError(f"Unknown MCP task {mcp_task}")
            except Exception as e:
                r = e
            except asyncio.CancelledError:
                break

            try:
                await result_queue.put(r)
            except asyncio.CancelledError:
                break

    async def _call_mcp_server(self, task_type: MCPTaskType, request_timeout: float | int = 8, **kwargs) -> Any:
        if self._close:
            raise ValueError("Session is closed")

        results = asyncio.Queue()
        await self._queue.put((task_type, kwargs, results))

        try:
            result: CallToolResult | Exception = await asyncio.wait_for(results.get(), timeout=request_timeout)
            if isinstance(result, Exception):
                raise result
            # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in MCPToolCallSession._call_mcp_server).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:7c21d3ab71a099a5123e1bef9b1fc527bfd3b65661eb4dcc96c3f141d7224501'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7c21d3ab71a099a5123e1bef9b1fc527bfd3b65661eb4dcc96c3f141d7224501', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 164, 'function': 'MCPToolCallSession._call_mcp_server'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 164, 'function': '_call_mcp_server', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return result
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError(f"MCP task '{task_type}' timeout after {request_timeout}s")
        except Exception:
            raise

    async def _call_mcp_tool(self, name: str, arguments: dict[str, Any], request_timeout: float | int = 10) -> str:
        result: CallToolResult = await self._call_mcp_server("tool_call", name=name, arguments=arguments,
                                                             request_timeout=request_timeout)

        if result.isError:
            return f"MCP server error: {result.content}"

        # For now, we only support text content
        if isinstance(result.content[0], TextContent):
            return result.content[0].text
        else:
            return f"Unsupported content type {type(result.content)}"

    async def _get_tools_from_mcp_server(self, request_timeout: float | int = 8) -> list[Tool]:
        try:
            result: ListToolsResult = await self._call_mcp_server("list_tools", request_timeout=request_timeout)
            return result.tools
        except Exception:
            raise

    def get_tools(self, timeout: float | int = 10) -> list[Tool]:
        if self._close:
            raise ValueError("Session is closed")

        future = asyncio.run_coroutine_threadsafe(self._get_tools_from_mcp_server(request_timeout=timeout), self._event_loop)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            msg = f"Timeout when fetching tools from MCP server: {self._mcp_server.id} (timeout={timeout})"
            # LINEAJE: runtime guardrail checks `msg` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession.get_tools).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6a026e6c4beaa5dcfebe3ba66825cbcc476c4968a7e2e0d1855e9a330311184c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6a026e6c4beaa5dcfebe3ba66825cbcc476c4968a7e2e0d1855e9a330311184c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 199, 'function': 'MCPToolCallSession.get_tools'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 199, 'function': 'get_tools', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                msg = _gr_client.enforce(_gr_site, msg, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(msg)
            raise RuntimeError(msg)
        except Exception:
            _lineaje_payload = f"Error fetching tools from MCP server: {self._mcp_server.id}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession.get_tools).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b22ac04f0a159edf1f11dd3b257c74296b749160df00f61362b5adeb82bd849b'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b22ac04f0a159edf1f11dd3b257c74296b749160df00f61362b5adeb82bd849b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 202, 'function': 'MCPToolCallSession.get_tools'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 202, 'function': 'get_tools', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
            raise

    @override
    def tool_call(self, name: str, arguments: dict[str, Any], timeout: float | int = 10) -> str:
        if self._close:
            return "Error: Session is closed"

        future = asyncio.run_coroutine_threadsafe(self._call_mcp_tool(name, arguments), self._event_loop)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            _lineaje_payload = f"Timeout calling tool '{name}' on MCP server: {self._mcp_server.id} (timeout={timeout})"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession.tool_call).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:40aed3d1c1dca722a9ceafefa6404174078843bf7506f2333970353239967f1f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:40aed3d1c1dca722a9ceafefa6404174078843bf7506f2333970353239967f1f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 214, 'function': 'MCPToolCallSession.tool_call'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 214, 'function': 'tool_call', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            return f"Timeout calling tool '{name}' (timeout={timeout})."
        except Exception as e:
            _lineaje_payload = f"Error calling tool '{name}' on MCP server: {self._mcp_server.id}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession.tool_call).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3a63f50f067ad2fc82973023abd44ee0e6cc91c37cefa194b9626f49085ec057'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3a63f50f067ad2fc82973023abd44ee0e6cc91c37cefa194b9626f49085ec057', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 217, 'function': 'MCPToolCallSession.tool_call'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 217, 'function': 'tool_call', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
            return f"Error calling tool '{name}': {e}."

    async def close(self) -> None:
        if self._close:
            return

        self._close = True

        while not self._queue.empty():
            try:
                _, _, result_queue = self._queue.get_nowait()
                try:
                    await result_queue.put(asyncio.CancelledError("Session is closing"))
                except Exception:
                    pass
            except asyncio.QueueEmpty:
                break
            except Exception:
                break

        try:
            self._event_loop.call_soon_threadsafe(self._event_loop.stop)
        except Exception:
            pass

        try:
            self._thread_pool.shutdown(wait=True)
        except Exception:
            pass

        self.__class__._ALL_INSTANCES.discard(self)

    def close_sync(self, timeout: float | int = 5) -> None:
        if not self._event_loop.is_running():
            _lineaje_payload = f"Event loop already stopped for {self._mcp_server.id}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession.close_sync).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:485b20b80e40c18d621cb3b401b65fc2487db30309133a2689f941cfd5d4682c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:485b20b80e40c18d621cb3b401b65fc2487db30309133a2689f941cfd5d4682c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 252, 'function': 'MCPToolCallSession.close_sync'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 252, 'function': 'close_sync', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            return

        try:
            future = asyncio.run_coroutine_threadsafe(self.close(), self._event_loop)
            try:
                future.result(timeout=timeout)
            except FuturesTimeoutError:
                _lineaje_payload = f"Timeout while closing session for server {self._mcp_server.id} (timeout={timeout})"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession.close_sync).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:8752affda5aa73d6919339067d59d1363de81082d5fbb73fa5f2a400571c2f14'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8752affda5aa73d6919339067d59d1363de81082d5fbb73fa5f2a400571c2f14', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 260, 'function': 'MCPToolCallSession.close_sync'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 260, 'function': 'close_sync', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
            except Exception:
                _lineaje_payload = f"Unexpected error during close_sync for {self._mcp_server.id}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession.close_sync).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:dd59ee616a838b3fccc9b01d2104af7485311d8c96471c1ec1f94853d7d27425'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dd59ee616a838b3fccc9b01d2104af7485311d8c96471c1ec1f94853d7d27425', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 262, 'function': 'MCPToolCallSession.close_sync'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 262, 'function': 'close_sync', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(_lineaje_payload)
        except Exception:
            _lineaje_payload = f"Exception while scheduling close for server {self._mcp_server.id}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession.close_sync).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:48607238db753b0b62a2b5b98167d83a3070ac6f3a3f14d26bd2b5fa6a38aeeb'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:48607238db753b0b62a2b5b98167d83a3070ac6f3a3f14d26bd2b5fa6a38aeeb', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 264, 'function': 'MCPToolCallSession.close_sync'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 264, 'function': 'close_sync', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)


def close_multiple_mcp_toolcall_sessions(sessions: list[MCPToolCallSession]) -> None:
    _lineaje_payload = f"Want to clean up {len(sessions)} MCP sessions"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in close_multiple_mcp_toolcall_sessions).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:45e870be73c98ce1be29362e6d70e7cbca4eb087773c37a99610a657924c1e0f'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:45e870be73c98ce1be29362e6d70e7cbca4eb087773c37a99610a657924c1e0f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 268, 'function': 'close_multiple_mcp_toolcall_sessions'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 268, 'function': 'close_multiple_mcp_toolcall_sessions', 'agent_name': 'close_multiple_mcp_toolcall_sessions', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)

    async def _gather_and_stop() -> None:
        try:
            await asyncio.gather(*[s.close() for s in sessions if s is not None], return_exceptions=True)
        except Exception:
            _lineaje_payload = "Exception during MCP session cleanup"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession._gather_and_stop).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:7b259f129a5634473d2fa9623f479d62b445d9ef4e19817ea99eb6dd02c44354'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7b259f129a5634473d2fa9623f479d62b445d9ef4e19817ea99eb6dd02c44354', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 274, 'function': 'close_multiple_mcp_toolcall_sessions._gather_and_stop'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 274, 'function': '_gather_and_stop', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
        finally:
            try:
                loop.call_soon_threadsafe(loop.stop)
            except Exception:
                pass

    try:
        loop = asyncio.new_event_loop()
        thread = threading.Thread(target=loop.run_forever, daemon=True)
        thread.start()

        asyncio.run_coroutine_threadsafe(_gather_and_stop(), loop).result()
        thread.join()
    except Exception:
        _lineaje_payload = "Exception during MCP session cleanup thread management"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MCPToolCallSession._gather_and_stop).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d4a4c724df05fdfe006b5d2aaa28feb5751b29d8ced0aa704364716e7001a877'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d4a4c724df05fdfe006b5d2aaa28feb5751b29d8ced0aa704364716e7001a877', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 289, 'function': 'close_multiple_mcp_toolcall_sessions'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 289, 'function': '_gather_and_stop', 'agent_name': 'MCPToolCallSession', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.exception(_lineaje_payload)

    _lineaje_payload = f"{len(sessions)} MCP sessions has been cleaned up. {len(list(MCPToolCallSession._ALL_INSTANCES))} in global context."
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in close_multiple_mcp_toolcall_sessions).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:62d0ce1e521e969fd57b594cc576700891f525f72d47b768d044b0afff0155c0'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:62d0ce1e521e969fd57b594cc576700891f525f72d47b768d044b0afff0155c0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 291, 'function': 'close_multiple_mcp_toolcall_sessions'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 291, 'function': 'close_multiple_mcp_toolcall_sessions', 'agent_name': 'close_multiple_mcp_toolcall_sessions', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(
        _lineaje_payload)


def shutdown_all_mcp_sessions():
    """Gracefully shutdown all active MCPToolCallSession instances."""
    sessions = list(MCPToolCallSession._ALL_INSTANCES)
    if not sessions:
        _lineaje_payload = "No MCPToolCallSession instances to close."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in shutdown_all_mcp_sessions).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8f9d9e0a6d9c61ddcaaa59f717916b2ef7997691d6a075051c1aef45330c4903'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8f9d9e0a6d9c61ddcaaa59f717916b2ef7997691d6a075051c1aef45330c4903', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 299, 'function': 'shutdown_all_mcp_sessions'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 299, 'function': 'shutdown_all_mcp_sessions', 'agent_name': 'shutdown_all_mcp_sessions', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        return

    _lineaje_payload = f"Shutting down {len(sessions)} MCPToolCallSession instances..."
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in shutdown_all_mcp_sessions).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:485aafc8004437db90e70e6529f7f021abcd1d0422f28e41145c368d112696a1'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:485aafc8004437db90e70e6529f7f021abcd1d0422f28e41145c368d112696a1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 302, 'function': 'shutdown_all_mcp_sessions'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 302, 'function': 'shutdown_all_mcp_sessions', 'agent_name': 'shutdown_all_mcp_sessions', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)
    close_multiple_mcp_toolcall_sessions(sessions)
    _lineaje_payload = "All MCPToolCallSession instances have been closed."
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in shutdown_all_mcp_sessions).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:c7cf0213d05f8278e3b034e0cb3659b28d7f393e0a47842052d0f988024f0b59'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c7cf0213d05f8278e3b034e0cb3659b28d7f393e0a47842052d0f988024f0b59', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/mcp_tool_call_conn.py', 'line': 304, 'function': 'shutdown_all_mcp_sessions'}, 'file': 'common/mcp_tool_call_conn.py', 'line': 304, 'function': 'shutdown_all_mcp_sessions', 'agent_name': 'shutdown_all_mcp_sessions', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)


def mcp_tool_metadata_to_openai_tool(mcp_tool: Tool | dict) -> dict[str, Any]:
    if isinstance(mcp_tool, dict):
        return {
            "type": "function",
            "function": {
                "name": mcp_tool["name"],
                "description": mcp_tool["description"],
                "parameters": mcp_tool["inputSchema"],
            },
        }

    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description,
            "parameters": mcp_tool.inputSchema,
        },
    }
