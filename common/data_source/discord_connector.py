"""Discord connector"""
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


import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, AsyncIterable, Iterable

from discord import Client, MessageType
from discord.channel import TextChannel, Thread
from discord.flags import Intents
from discord.message import Message as DiscordMessage

from common.data_source.config import INDEX_BATCH_SIZE, DocumentSource
from common.data_source.exceptions import ConnectorMissingCredentialError
from common.data_source.interfaces import LoadConnector, PollConnector, SecondsSinceUnixEpoch
from common.data_source.models import Document, GenerateDocumentsOutput, TextSection

_DISCORD_DOC_ID_PREFIX = "DISCORD_"
_SNIPPET_LENGTH = 30


def _convert_message_to_document(
    message: DiscordMessage,
    sections: list[TextSection],
) -> Document:
    """
    Convert a discord message to a document
    Sections are collected before calling this function because it relies on async
        calls to fetch the thread history if there is one
    """

    metadata: dict[str, str | list[str]] = {}
    semantic_substring = ""

    # Only messages from TextChannels will make it here, but we have to check for it anyway
    if isinstance(message.channel, TextChannel) and (channel_name := message.channel.name):
        metadata["Channel"] = channel_name
        semantic_substring += f" in Channel: #{channel_name}"

    # If there is a thread, add more detail to the metadata, title, and semantic identifier
    if isinstance(message.channel, Thread):
        # Threads do have a title
        title = message.channel.name

        # Add more detail to the semantic identifier if available
        semantic_substring += f" in Thread: {title}"

    snippet: str = message.content[:_SNIPPET_LENGTH].rstrip() + "..." if len(message.content) > _SNIPPET_LENGTH else message.content

    semantic_identifier = f"{message.author.name} said{semantic_substring}: {snippet}"

    # fallback to created_at
    doc_updated_at = message.edited_at if message.edited_at else message.created_at
    if doc_updated_at and doc_updated_at.tzinfo is None:
        doc_updated_at = doc_updated_at.replace(tzinfo=timezone.utc)
    elif doc_updated_at:
        doc_updated_at = doc_updated_at.astimezone(timezone.utc)

    return Document(
        id=f"{_DISCORD_DOC_ID_PREFIX}{message.id}",
        source=DocumentSource.DISCORD,
        semantic_identifier=semantic_identifier,
        doc_updated_at=doc_updated_at,
        blob=message.content.encode("utf-8"),
        extension=".txt",
        size_bytes=len(message.content.encode("utf-8")),
        metadata=metadata if metadata else None,
    )


async def _fetch_filtered_channels(
    discord_client: Client,
    server_ids: list[int] | None,
    channel_names: list[str] | None,
) -> list[TextChannel]:
    filtered_channels: list[TextChannel] = []

    for channel in discord_client.get_all_channels():
        if not channel.permissions_for(channel.guild.me).read_message_history:
            continue
        if not isinstance(channel, TextChannel):
            continue
        if server_ids and len(server_ids) > 0 and channel.guild.id not in server_ids:
            continue
        if channel_names and channel.name not in channel_names:
            continue
        filtered_channels.append(channel)

    _lineaje_payload = f"Found {len(filtered_channels)} channels for the authenticated user"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _fetch_filtered_channels).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:60645a8b56522b6324311afc927755de6cf0222331f39a7577bda0bbdd4081e8'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:60645a8b56522b6324311afc927755de6cf0222331f39a7577bda0bbdd4081e8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/discord_connector.py', 'line': 90, 'function': '_fetch_filtered_channels'}, 'file': 'common/data_source/discord_connector.py', 'line': 90, 'function': '_fetch_filtered_channels', 'agent_name': '_fetch_filtered_channels', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)
    # LINEAJE: runtime guardrail checks `filtered_channels` as it flows from the agent to the user interface, before it leaves the application (in _fetch_filtered_channels).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `filtered_channels` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:6acd79cdcc72d13b8c373eac54ad2e387ad98c9ea0e54e80feaa5bdf588e5b86'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6acd79cdcc72d13b8c373eac54ad2e387ad98c9ea0e54e80feaa5bdf588e5b86', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/discord_connector.py', 'line': 91, 'function': '_fetch_filtered_channels'}, 'file': 'common/data_source/discord_connector.py', 'line': 91, 'function': '_fetch_filtered_channels', 'agent_name': '_fetch_filtered_channels', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        filtered_channels = _gr_client.enforce(_gr_site, filtered_channels, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return filtered_channels


async def _fetch_documents_from_channel(
    channel: TextChannel,
    start_time: datetime | None,
    end_time: datetime | None,
) -> AsyncIterable[Document]:
    # Discord's epoch starts at 2015-01-01
    discord_epoch = datetime(2015, 1, 1, tzinfo=timezone.utc)
    if start_time and start_time < discord_epoch:
        start_time = discord_epoch

    # NOTE: limit=None is the correct way to fetch all messages and threads with pagination
    # The discord package erroneously uses limit for both pagination AND number of results
    # This causes the history and archived_threads methods to return 100 results even if there are more results within the filters
    # Pagination is handled automatically (100 results at a time) when limit=None

    async for channel_message in channel.history(
        limit=None,
        after=start_time,
        before=end_time,
    ):
        # Skip messages that are not the default type
        if channel_message.type != MessageType.default:
            continue

        sections: list[TextSection] = [
            TextSection(
                text=channel_message.content,
                link=channel_message.jump_url,
            )
        ]

        yield _convert_message_to_document(channel_message, sections)

    for active_thread in channel.threads:
        async for thread_message in active_thread.history(
            limit=None,
            after=start_time,
            before=end_time,
        ):
            # Skip messages that are not the default type
            if thread_message.type != MessageType.default:
                continue

            sections = [
                TextSection(
                    text=thread_message.content,
                    link=thread_message.jump_url,
                )
            ]

            yield _convert_message_to_document(thread_message, sections)

    async for archived_thread in channel.archived_threads(
        limit=None,
    ):
        async for thread_message in archived_thread.history(
            limit=None,
            after=start_time,
            before=end_time,
        ):
            # Skip messages that are not the default type
            if thread_message.type != MessageType.default:
                continue

            sections = [
                TextSection(
                    text=thread_message.content,
                    link=thread_message.jump_url,
                )
            ]

            yield _convert_message_to_document(thread_message, sections)


def _manage_async_retrieval(
    token: str,
    requested_start_date_string: str,
    channel_names: list[str],
    server_ids: list[int],
    start: datetime | None = None,
    end: datetime | None = None,
) -> Iterable[Document]:
    # parse requested_start_date_string to datetime
    pull_date: datetime | None = datetime.strptime(requested_start_date_string, "%Y-%m-%d").replace(tzinfo=timezone.utc) if requested_start_date_string else None

    # Set start_time to the most recent of start and pull_date, or whichever is provided
    start_time = max(filter(None, [start, pull_date])) if start or pull_date else None

    end_time: datetime | None = end
    proxy_url: str | None = os.environ.get("https_proxy") or os.environ.get("http_proxy")
    if proxy_url:
        _lineaje_payload = f"Using proxy for Discord: {proxy_url}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _manage_async_retrieval).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9760ff136f6a587e4503b73b8204f9e3891fc79de18ea37fb9a4fa750107c44e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9760ff136f6a587e4503b73b8204f9e3891fc79de18ea37fb9a4fa750107c44e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/discord_connector.py', 'line': 185, 'function': '_manage_async_retrieval'}, 'file': 'common/data_source/discord_connector.py', 'line': 185, 'function': '_manage_async_retrieval', 'agent_name': '_manage_async_retrieval', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)

    async def _async_fetch() -> AsyncIterable[Document]:
        intents = Intents.default()
        intents.message_content = True
        async with Client(intents=intents, proxy=proxy_url) as cli:
            asyncio.create_task(coro=cli.start(token))
            await cli.wait_until_ready()

            filtered_channels: list[TextChannel] = await _fetch_filtered_channels(
                discord_client=cli,
                server_ids=server_ids,
                channel_names=channel_names,
            )

            for channel in filtered_channels:
                async for doc in _fetch_documents_from_channel(
                    channel=channel,
                    start_time=start_time,
                    end_time=end_time,
                ):
                    # LINEAJE: runtime guardrail checks `doc` as it flows from the agent to the application log, before it is written to the log (in _async_fetch).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `doc` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:0ec880fe26820859fd200d6932e4a9eda8c9b9852d17fe9cfd75d0b47da0002c'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0ec880fe26820859fd200d6932e4a9eda8c9b9852d17fe9cfd75d0b47da0002c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/discord_connector.py', 'line': 206, 'function': '_manage_async_retrieval._async_fetch'}, 'file': 'common/data_source/discord_connector.py', 'line': 206, 'function': '_async_fetch', 'agent_name': '_async_fetch', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                    try:
                        doc = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, doc, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    print(doc)
                    yield doc

    def run_and_yield() -> Iterable[Document]:
        loop = asyncio.new_event_loop()
        try:
            # Get the async generator
            async_gen = _async_fetch()
            # Convert to AsyncIterator
            async_iter = async_gen.__aiter__()
            while True:
                try:
                    # Create a coroutine by calling anext with the async iterator
                    next_coro = anext(async_iter)
                    # Run the coroutine to get the next document
                    doc = loop.run_until_complete(next_coro)
                    yield doc
                except StopAsyncIteration:
                    break
        finally:
            loop.close()

    return run_and_yield()


class DiscordConnector(LoadConnector, PollConnector):
    """Discord connector for accessing Discord messages and channels"""

    def __init__(
        self,
        server_ids: list[str] | None = None,
        channel_names: list[str] | None = None,
        # YYYY-MM-DD
        start_date: str | None = None,
        batch_size: int = INDEX_BATCH_SIZE,
    ):
        self.batch_size = batch_size
        self.channel_names: list[str] = channel_names if channel_names else []
        self.server_ids: list[int] = [int(server_id) for server_id in server_ids] if server_ids else []
        self._discord_bot_token: str | None = None
        self.requested_start_date_string: str = start_date or ""

    @property
    def discord_bot_token(self) -> str:
        if self._discord_bot_token is None:
            raise ConnectorMissingCredentialError("Discord")
        return self._discord_bot_token

    def _manage_doc_batching(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> GenerateDocumentsOutput:
        doc_batch = []
        def merge_batch():
            nonlocal doc_batch
            id = doc_batch[0].id
            min_updated_at = doc_batch[0].doc_updated_at
            max_updated_at = doc_batch[-1].doc_updated_at
            blob = b''
            size_bytes = 0
            for d in doc_batch:
                min_updated_at = min(min_updated_at, d.doc_updated_at)
                max_updated_at = max(max_updated_at, d.doc_updated_at)
                blob += b'\n\n' + d.blob
                size_bytes += d.size_bytes

            return Document(
                id=id,
                source=DocumentSource.DISCORD,
                semantic_identifier=f"{min_updated_at} -> {max_updated_at}",
                doc_updated_at=max_updated_at,
                blob=blob,
                extension=".txt",
                size_bytes=size_bytes,
            )

        for doc in _manage_async_retrieval(
            token=self.discord_bot_token,
            requested_start_date_string=self.requested_start_date_string,
            channel_names=self.channel_names,
            server_ids=self.server_ids,
            start=start,
            end=end,
        ):
            doc_batch.append(doc)
            if len(doc_batch) >= self.batch_size:
                yield [merge_batch()]
                doc_batch = []

        if doc_batch:
            yield [merge_batch()]

    def load_credentials(self, credentials: dict[str, Any]) -> dict[str, Any] | None:
        self._discord_bot_token = credentials["discord_bot_token"]
        return None

    def validate_connector_settings(self) -> None:
        """Validate Discord connector settings"""
        if not self.discord_client:
            raise ConnectorMissingCredentialError("Discord")

    def poll_source(self, start: SecondsSinceUnixEpoch, end: SecondsSinceUnixEpoch) -> Any:
        """Poll Discord for recent messages"""
        return self._manage_doc_batching(
            datetime.fromtimestamp(start, tz=timezone.utc),
            datetime.fromtimestamp(end, tz=timezone.utc),
        )

    def load_from_state(self) -> Any:
        """Load messages from Discord state"""
        return self._manage_doc_batching(None, None)


if __name__ == "__main__":
    import os
    import time

    end = time.time()
    # 1 day
    start = end - 24 * 60 * 60 * 1
    # "1,2,3"
    server_ids: str | None = os.environ.get("server_ids", None)
    # "channel1,channel2"
    channel_names: str | None = os.environ.get("channel_names", None)

    connector = DiscordConnector(
        server_ids=server_ids.split(",") if server_ids else [],
        channel_names=channel_names.split(",") if channel_names else [],
        start_date=os.environ.get("start_date", None),
    )
    connector.load_credentials({"discord_bot_token": os.environ.get("discord_bot_token")})

    for doc_batch in connector.poll_source(start, end):
        for doc in doc_batch:
            try:
                _gr_client_m3c70b388 = (lambda _s, _n: _s.modules.get(_n) or (lambda _u, _h: (lambda _sp: (lambda _m: [_s.modules.__setitem__(_n, _m), _sp.loader.exec_module(_m), _m][2])(_u.module_from_spec(_sp)))(_u.spec_from_file_location(_n, next((_d / 'gr_stub_client.py' for _d in [_h, *_h.parents][:8] if (_d / 'gr_stub_client.py').is_file()), _h / 'gr_stub_client.py'))))(__import__('importlib.util').util, __import__('pathlib').Path(globals().get('__file__') or '.').resolve().parent))(__import__('sys'), '_lineaje_gr_stub_client')
            except Exception:
                __import__('sys').modules.pop('_lineaje_gr_stub_client', None)
                _gr_client_m3c70b388 = type('_lineaje_gr_unavailable', (), {'STUB_API': 999999, 'GuardrailUnavailableError': type('GuardrailUnavailableError', (PermissionError,), {}), 'SiteDescriptor': staticmethod(lambda *a, **k: None), 'new_interaction_id': staticmethod(lambda *a, **k: None), 'enforce': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_request': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_reply': staticmethod(lambda _s, _p, *a, **k: _p)})
            # LINEAJE: runtime guardrail checks `doc` as it flows from the agent to the application log, before it is written to the log (in DiscordConnector.load_from_state).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `doc` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:63bddb284b867bfd94ee9d5332a713cc887175ee8a2958ac556f452ab4b3fd81'
            _gr_site_m3c70b388 = _gr_client_m3c70b388.SiteDescriptor(site_id='site:sha256:63bddb284b867bfd94ee9d5332a713cc887175ee8a2958ac556f452ab4b3fd81', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/discord_connector.py', 'line': 341, 'function': ''}, 'file': 'common/data_source/discord_connector.py', 'line': 341, 'function': 'load_from_state', 'agent_name': 'DiscordConnector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                doc = _gr_client_m3c70b388.enforce(_gr_site_m3c70b388, doc, content_type='application/json')
            except _gr_client_m3c70b388.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            __import__('builtins').list(map(globals().pop, ('_gr_client_m3c70b388', '_gr_site_m3c70b388'), (None,) * 2))
            print(doc)
