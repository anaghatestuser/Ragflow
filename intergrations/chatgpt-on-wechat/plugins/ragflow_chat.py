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

import logging
import requests
from bridge.context import ContextType  # Import Context, ContextType
from bridge.reply import Reply, ReplyType  # Import Reply, ReplyType
from plugins import Plugin, register  # Import Plugin and register
from plugins.event import Event, EventContext, EventAction  # Import event-related classes

@register(name="RAGFlowChat", desc="Use RAGFlow API to chat", version="1.0", author="Your Name")
class RAGFlowChat(Plugin):
    def __init__(self):
        super().__init__()
        # Load plugin configuration
        self.cfg = self.load_config()
        # Bind event handling function
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        # Store conversation_id for each user
        self.conversations = {}
        _lineaje_payload = "[RAGFlowChat] Plugin initialized"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowChat.__init__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:88b13a90845b555b7aba6f007c9e2573dadb8a375b5b95b7c172148141d05e82'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:88b13a90845b555b7aba6f007c9e2573dadb8a375b5b95b7c172148141d05e82', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 34, 'function': 'RAGFlowChat.__init__'}, 'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 34, 'function': '__init__', 'agent_name': 'RAGFlowChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)

    def on_handle_context(self, e_context: EventContext):
        context = e_context['context']
        if context.type != ContextType.TEXT:
            return  # Only process text messages

        user_input = context.content.strip()
        session_id = context['session_id']

        # Call RAGFlow API to get a reply
        reply_text = self.get_ragflow_reply(user_input, session_id)
        if reply_text:
            reply = Reply()
            reply.type = ReplyType.TEXT
            reply.content = reply_text
            e_context['reply'] = reply
            e_context.action = EventAction.BREAK_PASS  # Skip the default processing logic
        else:
            # If no reply is received, pass to the next plugin or default logic
            e_context.action = EventAction.CONTINUE

    def get_ragflow_reply(self, user_input, session_id):
        # Get API_KEY and host address from the configuration
        api_key = self.cfg.get("api_key")
        host_address = self.cfg.get("host_address")
        user_id = session_id  # Use session_id as user_id

        if not api_key or not host_address:
            _lineaje_payload = "[RAGFlowChat] Missing configuration"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowChat.get_ragflow_reply).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d6553f9973e4fc3eede92233201d89d05c51884b47d615f3e47414cbfcea8d66'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d6553f9973e4fc3eede92233201d89d05c51884b47d615f3e47414cbfcea8d66', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 63, 'function': 'RAGFlowChat.get_ragflow_reply'}, 'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 63, 'function': 'get_ragflow_reply', 'agent_name': 'RAGFlowChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            return "The plugin configuration is incomplete. Please check the configuration."

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Step 1: Get or create conversation_id
        conversation_id = self.conversations.get(user_id)
        if not conversation_id:
            # Create a new conversation
            url_new_conversation = f"http://{host_address}/v1/api/new_conversation"
            params_new_conversation = {
                "user_id": user_id
            }
            try:
                response = requests.get(url_new_conversation, headers=headers, params=params_new_conversation)
                # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in RAGFlowChat.get_ragflow_reply).
                #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:ebaae20f32a1f5857dc5674945e5108a9892f5a376afafd9044f7b67499689e6'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ebaae20f32a1f5857dc5674945e5108a9892f5a376afafd9044f7b67499689e6', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 80, 'function': 'RAGFlowChat.get_ragflow_reply'}, 'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 80, 'function': 'get_ragflow_reply', 'agent_name': 'RAGFlowChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=80)
                except _gr_client.GuardrailUnavailableError:
                    pass
                _lineaje_payload = f"[RAGFlowChat] New conversation response: {response.text}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowChat.get_ragflow_reply).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:13b8a4b2155d89b07274dda885e72f3488a65e081a7d26eb309d106671d509db'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:13b8a4b2155d89b07274dda885e72f3488a65e081a7d26eb309d106671d509db', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 81, 'function': 'RAGFlowChat.get_ragflow_reply'}, 'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 81, 'function': 'get_ragflow_reply', 'agent_name': 'RAGFlowChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.debug(_lineaje_payload)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        conversation_id = data["data"]["id"]
                        self.conversations[user_id] = conversation_id
                    else:
                        _lineaje_payload = f"[RAGFlowChat] Failed to create conversation: {data.get('message')}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowChat.get_ragflow_reply).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:7ad8a1127d2e8acc54eefd94fcc209e8e18995303d46ad8c7585d23c81547350'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7ad8a1127d2e8acc54eefd94fcc209e8e18995303d46ad8c7585d23c81547350', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 88, 'function': 'RAGFlowChat.get_ragflow_reply'}, 'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 88, 'function': 'get_ragflow_reply', 'agent_name': 'RAGFlowChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.error(_lineaje_payload)
                        return f"Sorry, unable to create a conversation: {data.get('message')}"
                else:
                    _lineaje_payload = f"[RAGFlowChat] HTTP error when creating conversation: {response.status_code}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowChat.get_ragflow_reply).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:20f2bf87c3615e0f961139985d8036d4adb2e3ba9bbfc12b79c3da0e2fb97526'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:20f2bf87c3615e0f961139985d8036d4adb2e3ba9bbfc12b79c3da0e2fb97526', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 91, 'function': 'RAGFlowChat.get_ragflow_reply'}, 'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 91, 'function': 'get_ragflow_reply', 'agent_name': 'RAGFlowChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.error(_lineaje_payload)
                    return f"Sorry, unable to connect to RAGFlow API (create conversation). HTTP status code: {response.status_code}"
            except Exception as e:
                _lineaje_payload = "[RAGFlowChat] Exception when creating conversation"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowChat.get_ragflow_reply).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:4824dfa5c8eb43d0d89f6cf7f03bf8b879fc0b41e9f7d7246dab831d9a34d1b8'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4824dfa5c8eb43d0d89f6cf7f03bf8b879fc0b41e9f7d7246dab831d9a34d1b8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 94, 'function': 'RAGFlowChat.get_ragflow_reply'}, 'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 94, 'function': 'get_ragflow_reply', 'agent_name': 'RAGFlowChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(_lineaje_payload)
                return f"Sorry, an internal error occurred: {str(e)}"

        # Step 2: Send the message and get a reply
        url_completion = f"http://{host_address}/v1/api/completion"
        payload_completion = {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "role": "user",
                    "content": user_input
                }
            ],
            "quote": False,
            "stream": False
        }

        try:
            response = requests.post(url_completion, headers=headers, json=payload_completion)
            # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in RAGFlowChat.get_ragflow_reply).
            #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:5ed400dfdbd48bee0df2de908dcfc8c2a7d089d37c1aa82203486c80a4def325'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5ed400dfdbd48bee0df2de908dcfc8c2a7d089d37c1aa82203486c80a4def325', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 112, 'function': 'RAGFlowChat.get_ragflow_reply'}, 'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 112, 'function': 'get_ragflow_reply', 'agent_name': 'RAGFlowChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=112)
            except _gr_client.GuardrailUnavailableError:
                pass
            _lineaje_payload = f"[RAGFlowChat] Completion response: {response.text}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowChat.get_ragflow_reply).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:53eb1de26f811a5b218cd98650d1f45f744ba8eb4afe3aa41516f6ea04f72959'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:53eb1de26f811a5b218cd98650d1f45f744ba8eb4afe3aa41516f6ea04f72959', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 113, 'function': 'RAGFlowChat.get_ragflow_reply'}, 'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 113, 'function': 'get_ragflow_reply', 'agent_name': 'RAGFlowChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.debug(_lineaje_payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    answer = data["data"]["answer"]
                    # LINEAJE: runtime guardrail checks `answer` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowChat.get_ragflow_reply).
                    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `answer` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:1653d11a39493aabc5fa438dae0acdf41ed39de24e60963dfa2a85003f6c4a34'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1653d11a39493aabc5fa438dae0acdf41ed39de24e60963dfa2a85003f6c4a34', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 118, 'function': 'RAGFlowChat.get_ragflow_reply'}, 'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 118, 'function': 'get_ragflow_reply', 'agent_name': 'RAGFlowChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        answer = _gr_client.enforce(_gr_site, answer, content_type='text/plain')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    return answer
                else:
                    _lineaje_payload = f"[RAGFlowChat] Failed to get answer: {data.get('message')}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowChat.get_ragflow_reply).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:1b63879df513cf9395ab25ea16d6f3f97fda43ba70e55f3a7bc389868df0e5ce'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1b63879df513cf9395ab25ea16d6f3f97fda43ba70e55f3a7bc389868df0e5ce', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 120, 'function': 'RAGFlowChat.get_ragflow_reply'}, 'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 120, 'function': 'get_ragflow_reply', 'agent_name': 'RAGFlowChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.error(_lineaje_payload)
                    return f"Sorry, unable to get a reply: {data.get('message')}"
            else:
                _lineaje_payload = f"[RAGFlowChat] HTTP error when getting answer: {response.status_code}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowChat.get_ragflow_reply).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a13b4b0eb3fc61b2ea72a9a28be0857202a7d907748bcfa38dc88a957db1f9bd'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a13b4b0eb3fc61b2ea72a9a28be0857202a7d907748bcfa38dc88a957db1f9bd', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 123, 'function': 'RAGFlowChat.get_ragflow_reply'}, 'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 123, 'function': 'get_ragflow_reply', 'agent_name': 'RAGFlowChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                return f"Sorry, unable to connect to RAGFlow API (get reply). HTTP status code: {response.status_code}"
        except Exception as e:
            _lineaje_payload = "[RAGFlowChat] Exception when getting answer"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in RAGFlowChat.get_ragflow_reply).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ba1b066ee5016bc50efbfca9a3d872eab3f835d977980a236580ec73d41d019d'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ba1b066ee5016bc50efbfca9a3d872eab3f835d977980a236580ec73d41d019d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 126, 'function': 'RAGFlowChat.get_ragflow_reply'}, 'file': 'intergrations/chatgpt-on-wechat/plugins/ragflow_chat.py', 'line': 126, 'function': 'get_ragflow_reply', 'agent_name': 'RAGFlowChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
            return f"Sorry, an internal error occurred: {str(e)}"
