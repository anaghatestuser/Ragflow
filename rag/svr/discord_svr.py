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
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
import logging
import discord
import requests
import base64
import asyncio

URL = '{YOUR_IP_ADDRESS:PORT}/v1/api/completion_aibotk' # Default: https://demo.ragflow.io/v1/api/completion_aibotk

JSON_DATA = {
    "conversation_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxx", # Get conversation id from /api/new_conversation
    "Authorization": "ragflow-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx", # RAGFlow Assistant Chat Bot API Key
    "word": "" # User question, don't need to initialize
}

DISCORD_BOT_KEY = "xxxxxxxxxxxxxxxxxxxxxxxxxx" #Get DISCORD_BOT_KEY from Discord Application


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    _lineaje_payload = f'We have logged in as {client.user}'
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in on_ready).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:b56c6b0eb60d892af3119214f7c0eb0f183da26f20ef5006c291cd358282270b'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b56c6b0eb60d892af3119214f7c0eb0f183da26f20ef5006c291cd358282270b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/discord_svr.py', 'line': 40, 'function': 'on_ready'}, 'file': 'rag/svr/discord_svr.py', 'line': 40, 'function': 'on_ready', 'agent_name': 'on_ready', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if client.user.mentioned_in(message):

        if len(message.content.split('> ')) == 1:
            await message.channel.send("Hi~ How can I help you? ")
        else:
            JSON_DATA['word']=message.content.split('> ')[1]
            response = requests.post(URL, json=JSON_DATA)
            # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in on_message).
            #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e8d30e515df2cfbd63ec462217041c3ba2cd7d6afbc39971af9d53ac588f4c6c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e8d30e515df2cfbd63ec462217041c3ba2cd7d6afbc39971af9d53ac588f4c6c', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/discord_svr.py', 'line': 54, 'function': 'on_message'}, 'file': 'rag/svr/discord_svr.py', 'line': 54, 'function': 'on_message', 'agent_name': 'on_message', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=54))
            except _gr_client.GuardrailUnavailableError:
                pass
            response_data = response.json().get('data', [])
            image_bool = False

            for i in response_data:
                if i['type'] == 1:
                    res = i['content']
                if i['type'] == 3:
                    image_bool = True
                    image_data = base64.b64decode(i['url'])
                    with open('tmp_image.png','wb') as file:
                        # LINEAJE: runtime guardrail checks `image_data` as it flows from the agent to a file, before it is written to disk (in on_message).
                        #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `image_data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:ea29f77b893a1d18025993f9e8b76e8c5ab5819d70a8725fff21543515fcade1'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ea29f77b893a1d18025993f9e8b76e8c5ab5819d70a8725fff21543515fcade1', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/svr/discord_svr.py', 'line': 65, 'function': 'on_message'}, 'file': 'rag/svr/discord_svr.py', 'line': 65, 'function': 'on_message', 'agent_name': 'on_message', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                        try:
                            image_data = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, image_data, content_type='application/json', variable_name='image_data', source_file=__file__, before_line=65))
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        file.write(image_data)
                    image= discord.File('tmp_image.png')

            await message.channel.send(f"{message.author.mention}{res}")

            if image_bool:
                await message.channel.send(file=image)


loop = asyncio.get_event_loop()

try:
    loop.run_until_complete(client.start(DISCORD_BOT_KEY))
except KeyboardInterrupt:
    loop.run_until_complete(client.close())
finally:
    loop.close()
