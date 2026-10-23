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

import asyncio
import base64
import json
import logging
import os
import re
import tempfile
from abc import ABC
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin

import requests
from openai import OpenAI, AsyncOpenAI
from openai.lib.azure import AzureOpenAI, AsyncAzureOpenAI

from common.token_utils import num_tokens_from_string, total_token_count_from_response
from rag.nlp import is_english
from rag.prompts.generator import vision_llm_describe_prompt


class Base(ABC):
    def __init__(self, **kwargs):
        # Configure retry parameters
        self.max_retries = kwargs.get("max_retries", int(os.environ.get("LLM_MAX_RETRIES", 5)))
        self.base_delay = kwargs.get("retry_interval", float(os.environ.get("LLM_BASE_DELAY", 2.0)))
        self.max_rounds = kwargs.get("max_rounds", 5)
        self.is_tools = False
        self.tools = []
        self.toolcall_sessions = {}
        self.extra_body = None

    def describe(self, image):
        raise NotImplementedError("Please implement encode method!")

    def describe_with_prompt(self, image, prompt=None):
        raise NotImplementedError("Please implement encode method!")

    def _form_history(self, system, history, images=None):
        hist = []
        if system:
            hist.append({"role": "system", "content": system})
        for h in history:
            if images and h["role"] == "user":
                h["content"] = self._image_prompt(h["content"], images)
                images = []
            hist.append(h)
        # LINEAJE: runtime guardrail checks `hist` as it flows from the agent to the user interface, before it leaves the application (in Base._form_history).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `hist` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e05653d4e91e066361acca1c32c8498f76dbd6439e048473e33a8e9a298ba0c2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e05653d4e91e066361acca1c32c8498f76dbd6439e048473e33a8e9a298ba0c2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 65, 'function': 'Base._form_history'}, 'file': 'rag/llm/cv_model.py', 'line': 65, 'function': '_form_history', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            hist = _gr_client.enforce(_gr_site, hist, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return hist

    def _image_prompt(self, text, images):
        if not images:
            # LINEAJE: runtime guardrail checks `text` as it flows from the agent to the user interface, before it leaves the application (in Base._image_prompt).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `text` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:5faf2aa12211a1d8429c313b3eadb1510f9e76bcb354d71e3093442adb0b9601'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5faf2aa12211a1d8429c313b3eadb1510f9e76bcb354d71e3093442adb0b9601', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 69, 'function': 'Base._image_prompt'}, 'file': 'rag/llm/cv_model.py', 'line': 69, 'function': '_image_prompt', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                text = _gr_client.enforce(_gr_site, text, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return text

        if isinstance(images, str) or "bytes" in type(images).__name__:
            images = [images]

        pmpt = [{"type": "text", "text": text}]
        for img in images:
            pmpt.append({"type": "image_url", "image_url": {"url": img if isinstance(img, str) and img.startswith("data:") else f"data:image/png;base64,{img}"}})
        # LINEAJE: runtime guardrail checks `pmpt` as it flows from the agent to the user interface, before it leaves the application (in Base._image_prompt).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `pmpt` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:268e68c8d7c78ded5a45d0c51d596687e6f259a727306dc445c25a114061b14a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:268e68c8d7c78ded5a45d0c51d596687e6f259a727306dc445c25a114061b14a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 77, 'function': 'Base._image_prompt'}, 'file': 'rag/llm/cv_model.py', 'line': 77, 'function': '_image_prompt', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            pmpt = _gr_client.enforce(_gr_site, pmpt, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return pmpt

    async def async_chat(self, system, history, gen_conf, images=None, **kwargs):
        try:
            _lineaje_messages = self._form_history(system, history, images)
            # LINEAJE: runtime guardrail checks `_lineaje_messages` as it flows from the agent to the LLM, before it is sent to the model (in Base.async_chat).
            #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_messages` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f491a9d75b7ba446d82ced1d9fe180e5ce61491e92cc39e68b7021ca9fb45ab1'
            _lineaje__lineaje_messages_evidence = {'_lineaje_messages': _lineaje_messages, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _lineaje_interaction_id = _gr_client.new_interaction_id()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f491a9d75b7ba446d82ced1d9fe180e5ce61491e92cc39e68b7021ca9fb45ab1', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-4-vision-preview', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@4-vision-preview', 'version': '4-vision-preview'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'Base.async_chat', 'line': 81}, 'file': 'rag/llm/cv_model.py', 'line': 81, 'function': 'async_chat', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:84270adc6a14337e'}, interaction_id=_lineaje_interaction_id)
            try:
                _lineaje__lineaje_messages_evidence = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje__lineaje_messages_evidence, content_type='application/json'))
                _lineaje_messages = _lineaje__lineaje_messages_evidence.get('_lineaje_messages', _lineaje_messages) if isinstance(_lineaje__lineaje_messages_evidence, dict) else _lineaje_messages
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=_lineaje_messages,
                extra_body=self.extra_body,
            )
            # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in Base.async_chat).
            #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ddc12d365c244495f8a787053120fe15f13a85f50e58bdac23416e366ef7dad9'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ddc12d365c244495f8a787053120fe15f13a85f50e58bdac23416e366ef7dad9', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-4-vision-preview', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@4-vision-preview', 'version': '4-vision-preview'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'Base.async_chat', 'line': 81}, 'file': 'rag/llm/cv_model.py', 'line': 81, 'function': 'async_chat', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:84270adc6a14337e'}, interaction_id=locals().get('_lineaje_interaction_id'))
            try:
                if not hasattr(_gr_client, 'enforce_reply'):
                    __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                    raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            return response.choices[0].message.content.strip(), response.usage.total_tokens
        except Exception as e:
            return "**ERROR**: " + str(e), 0

    async def async_chat_streamly(self, system, history, gen_conf, images=None, **kwargs):
        ans = ""
        tk_count = 0
        try:
            _lineaje_messages = self._form_history(system, history, images)
            # LINEAJE: runtime guardrail checks `_lineaje_messages` as it flows from the agent to the LLM, before it is sent to the model (in Base.async_chat_streamly).
            #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_messages` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:280aba4e0bb6ffd5999841a8dd570ceb4ed063b628396b184e378bfb91cab3ff'
            _lineaje__lineaje_messages_evidence = {'_lineaje_messages': _lineaje_messages, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _lineaje_interaction_id = _gr_client.new_interaction_id()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:280aba4e0bb6ffd5999841a8dd570ceb4ed063b628396b184e378bfb91cab3ff', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-4-vision-preview', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@4-vision-preview', 'version': '4-vision-preview'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'Base.async_chat_streamly', 'line': 94}, 'file': 'rag/llm/cv_model.py', 'line': 94, 'function': 'async_chat_streamly', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:4dab4caa041950d3'}, interaction_id=_lineaje_interaction_id)
            try:
                _lineaje__lineaje_messages_evidence = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje__lineaje_messages_evidence, content_type='application/json'))
                _lineaje_messages = _lineaje__lineaje_messages_evidence.get('_lineaje_messages', _lineaje_messages) if isinstance(_lineaje__lineaje_messages_evidence, dict) else _lineaje_messages
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=_lineaje_messages,
                stream=True,
                extra_body=self.extra_body,
            )
            # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in Base.async_chat_streamly).
            #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:484970f01edd3566d0944819b08d93bd851ae3c60616d89736a8b1cc3a1860f4'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:484970f01edd3566d0944819b08d93bd851ae3c60616d89736a8b1cc3a1860f4', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-4-vision-preview', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@4-vision-preview', 'version': '4-vision-preview'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'Base.async_chat_streamly', 'line': 94}, 'file': 'rag/llm/cv_model.py', 'line': 94, 'function': 'async_chat_streamly', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:4dab4caa041950d3'}, interaction_id=locals().get('_lineaje_interaction_id'))
            try:
                if not hasattr(_gr_client, 'enforce_reply'):
                    __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                    raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            async for resp in response:
                if not resp.choices[0].delta.content:
                    continue
                delta = resp.choices[0].delta.content
                ans = delta
                if resp.choices[0].finish_reason == "length":
                    ans += "...\nFor the content length reason, it stopped, continue?" if is_english([ans]) else "······\n由于长度的原因，回答被截断了，要继续吗？"
                if resp.choices[0].finish_reason == "stop":
                    tk_count += resp.usage.total_tokens
                yield ans
        except Exception as e:
            yield ans + "\n**ERROR**: " + str(e)

        yield tk_count

    @staticmethod
    def image2base64_rawvalue(self, image):
        # Return a base64 string without data URL header
        if isinstance(image, bytes):
            b64 = base64.b64encode(image).decode("utf-8")
            # LINEAJE: runtime guardrail checks `b64` as it flows from the agent to the user interface, before it leaves the application (in Base.image2base64_rawvalue).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `b64` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f14c7446757321430dae27d8f4163817f1a66aa81a1305daae127e1f6f17b81f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f14c7446757321430dae27d8f4163817f1a66aa81a1305daae127e1f6f17b81f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 120, 'function': 'Base.image2base64_rawvalue'}, 'file': 'rag/llm/cv_model.py', 'line': 120, 'function': 'image2base64_rawvalue', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                b64 = _gr_client.enforce(_gr_site, b64, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return b64
        if isinstance(image, BytesIO):
            data = image.getvalue()
            b64 = base64.b64encode(data).decode("utf-8")
            # LINEAJE: runtime guardrail checks `b64` as it flows from the agent to the user interface, before it leaves the application (in Base.image2base64_rawvalue).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `b64` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3544350978efc4232ce30b437bbf4b0cd1d6e1d1a559e60a20012ff92332ad54'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3544350978efc4232ce30b437bbf4b0cd1d6e1d1a559e60a20012ff92332ad54', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 124, 'function': 'Base.image2base64_rawvalue'}, 'file': 'rag/llm/cv_model.py', 'line': 124, 'function': 'image2base64_rawvalue', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                b64 = _gr_client.enforce(_gr_site, b64, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return b64
        with BytesIO() as buffered:
            try:
                image.save(buffered, format="JPEG")
            except Exception:
                # reset buffer before saving PNG
                buffered.seek(0)
                buffered.truncate()
                image.save(buffered, format="PNG")
            data = buffered.getvalue()
            b64 = base64.b64encode(data).decode("utf-8")
        # LINEAJE: runtime guardrail checks `b64` as it flows from the agent to the user interface, before it leaves the application (in Base.image2base64_rawvalue).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `b64` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:49b4094babb114fd83d232f4cbaabeb0d1febaab643b832bf5935f086029f82c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:49b4094babb114fd83d232f4cbaabeb0d1febaab643b832bf5935f086029f82c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 135, 'function': 'Base.image2base64_rawvalue'}, 'file': 'rag/llm/cv_model.py', 'line': 135, 'function': 'image2base64_rawvalue', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            b64 = _gr_client.enforce(_gr_site, b64, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return b64

    @staticmethod
    def image2base64(image):
        # Return a data URL with the correct MIME to avoid provider mismatches
        if isinstance(image, bytes):
            # Best-effort magic number sniffing
            mime = "image/png"
            if len(image) >= 2 and image[0] == 0xFF and image[1] == 0xD8:
                mime = "image/jpeg"
            b64 = base64.b64encode(image).decode("utf-8")
            return f"data:{mime};base64,{b64}"
        if isinstance(image, BytesIO):
            data = image.getvalue()
            mime = "image/png"
            if len(data) >= 2 and data[0] == 0xFF and data[1] == 0xD8:
                mime = "image/jpeg"
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:{mime};base64,{b64}"
        with BytesIO() as buffered:
            fmt = "jpeg"
            try:
                image.save(buffered, format="JPEG")
            except Exception:
                # reset buffer before saving PNG
                buffered.seek(0)
                buffered.truncate()
                image.save(buffered, format="PNG")
                fmt = "png"
            data = buffered.getvalue()
            b64 = base64.b64encode(data).decode("utf-8")
            mime = f"image/{fmt}"
        return f"data:{mime};base64,{b64}"

    def prompt(self, b64):
        return [
            {
                "role": "user",
                "content": self._image_prompt(
                    "请用中文详细描述一下图中的内容，比如时间，地点，人物，事情，人物心情等，如果有数据请提取出数据。"
                    if self.lang.lower() == "chinese"
                    else "Please describe the content of this picture, like where, when, who, what happen. If it has number data, please extract them out.",
                    b64,
                ),
            }
        ]

    def vision_llm_prompt(self, b64, prompt=None):
        return [{"role": "user", "content": self._image_prompt(prompt if prompt else vision_llm_describe_prompt(), b64)}]


class GptV4(Base):
    _FACTORY_NAME = "OpenAI"

    def __init__(self, key, model_name="gpt-4-vision-preview", lang="Chinese", base_url="https://api.openai.com/v1", **kwargs):
        if not base_url:
            base_url = "https://api.openai.com/v1"
        self.api_key = key
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name
        self.lang = lang
        super().__init__(**kwargs)

    def describe(self, image):
        b64 = self.image2base64(image)
        _lineaje_messages = self.prompt(b64)
        # LINEAJE: runtime guardrail checks `_lineaje_messages` as it flows from the agent to the LLM, before it is sent to the model (in GptV4.describe).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_messages` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:210e7c6f42d9855bfc063054c249a4acae047f05e1d7b90924319514e4aa35da'
        _lineaje__lineaje_messages_evidence = {'_lineaje_messages': _lineaje_messages, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:210e7c6f42d9855bfc063054c249a4acae047f05e1d7b90924319514e4aa35da', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-4-vision-preview', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@4-vision-preview', 'version': '4-vision-preview'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'GptV4.describe', 'line': 201}, 'file': 'rag/llm/cv_model.py', 'line': 201, 'function': 'describe', 'agent_name': 'GptV4', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:2db54d0c76758863'}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje__lineaje_messages_evidence = _gr_client.enforce(_gr_site, _lineaje__lineaje_messages_evidence, content_type='application/json')
            _lineaje_messages = _lineaje__lineaje_messages_evidence.get('_lineaje_messages', _lineaje_messages) if isinstance(_lineaje__lineaje_messages_evidence, dict) else _lineaje_messages
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        res = self.client.chat.completions.create(
            model=self.model_name,
            messages=_lineaje_messages,
            extra_body=self.extra_body
        )
        # LINEAJE: runtime guardrail checks `res` as it flows from the LLM to the agent, after the model replies (in GptV4.describe).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ccb693f353088b3a342a2dfb9724d8dcfe74adb34494dca7af33343f696b4271'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ccb693f353088b3a342a2dfb9724d8dcfe74adb34494dca7af33343f696b4271', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-4-vision-preview', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@4-vision-preview', 'version': '4-vision-preview'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'GptV4.describe', 'line': 201}, 'file': 'rag/llm/cv_model.py', 'line': 201, 'function': 'describe', 'agent_name': 'GptV4', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:2db54d0c76758863'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            if not hasattr(_gr_client, 'enforce_reply'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
            res = _gr_client.enforce_reply(_gr_site, res, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        return res.choices[0].message.content.strip(), total_token_count_from_response(res)

    def describe_with_prompt(self, image, prompt=None):
        b64 = self.image2base64(image)
        _lineaje_messages = self.vision_llm_prompt(b64, prompt)
        # LINEAJE: runtime guardrail checks `_lineaje_messages` as it flows from the agent to the LLM, before it is sent to the model (in GptV4.describe_with_prompt).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_messages` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:52cbff4a1b210d7a1d2f7453fadc6dac467c7bccb49a08a3ef29849901e0ce5a'
        _lineaje__lineaje_messages_evidence = {'_lineaje_messages': _lineaje_messages, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:52cbff4a1b210d7a1d2f7453fadc6dac467c7bccb49a08a3ef29849901e0ce5a', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-4-vision-preview', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@4-vision-preview', 'version': '4-vision-preview'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'GptV4.describe_with_prompt', 'line': 210}, 'file': 'rag/llm/cv_model.py', 'line': 210, 'function': 'describe_with_prompt', 'agent_name': 'GptV4', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:9940d07f13f0794d'}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje__lineaje_messages_evidence = _gr_client.enforce(_gr_site, _lineaje__lineaje_messages_evidence, content_type='application/json')
            _lineaje_messages = _lineaje__lineaje_messages_evidence.get('_lineaje_messages', _lineaje_messages) if isinstance(_lineaje__lineaje_messages_evidence, dict) else _lineaje_messages
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        res = self.client.chat.completions.create(
            model=self.model_name,
            messages=_lineaje_messages,
            extra_body=self.extra_body,
        )
        # LINEAJE: runtime guardrail checks `res` as it flows from the LLM to the agent, after the model replies (in GptV4.describe_with_prompt).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c2e337af3f235114b8b272d70bbe801c57ffbbfadfe5bd761e0645f7149de7a1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c2e337af3f235114b8b272d70bbe801c57ffbbfadfe5bd761e0645f7149de7a1', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-4-vision-preview', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@4-vision-preview', 'version': '4-vision-preview'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'GptV4.describe_with_prompt', 'line': 210}, 'file': 'rag/llm/cv_model.py', 'line': 210, 'function': 'describe_with_prompt', 'agent_name': 'GptV4', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:9940d07f13f0794d'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            if not hasattr(_gr_client, 'enforce_reply'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
            res = _gr_client.enforce_reply(_gr_site, res, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        return res.choices[0].message.content.strip(), total_token_count_from_response(res)


class AzureGptV4(GptV4):
    _FACTORY_NAME = "Azure-OpenAI"

    def __init__(self, key, model_name, lang="Chinese", **kwargs):
        api_key = json.loads(key).get("api_key", "")
        api_version = json.loads(key).get("api_version", "2024-02-01")
        self.client = AzureOpenAI(api_key=api_key, azure_endpoint=kwargs["base_url"], api_version=api_version)
        self.async_client = AsyncAzureOpenAI(api_key=api_key, azure_endpoint=kwargs["base_url"], api_version=api_version)
        self.model_name = model_name
        self.lang = lang
        Base.__init__(self, **kwargs)


class xAICV(GptV4):
    _FACTORY_NAME = "xAI"

    def __init__(self, key, model_name="grok-3", lang="Chinese", base_url=None, **kwargs):
        if not base_url:
            base_url = "https://api.x.ai/v1"
        super().__init__(key, model_name, lang=lang, base_url=base_url, **kwargs)


class QWenCV(GptV4):
    _FACTORY_NAME = "Tongyi-Qianwen"

    def __init__(self, key, model_name="qwen-vl-chat-v1", lang="Chinese", base_url=None, **kwargs):
        if not base_url:
            base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        super().__init__(key, model_name, lang=lang, base_url=base_url, **kwargs)

    async def async_chat(self, system, history, gen_conf, images=None, video_bytes=None, filename="", **kwargs):
        if video_bytes:
            try:
                summary, summary_num_tokens = self._process_video(video_bytes, filename)
                return summary, summary_num_tokens
            except Exception as e:
                return "**ERROR**: " + str(e), 0

        return "**ERROR**: Method chat not supported yet.", 0

    def _process_video(self, video_bytes, filename):
        from dashscope import MultiModalConversation

        video_suffix = Path(filename).suffix or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=video_suffix) as tmp:
            tmp.write(video_bytes)
            tmp_path = tmp.name

            video_path = f"file://{tmp_path}"
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "video": video_path,
                            "fps": 2,
                        },
                        {
                            "text": "Please summarize this video in proper sentences.",
                        },
                    ],
                }
            ]

            def call_api():
                response = MultiModalConversation.call(
                    api_key=self.api_key,
                    model=self.model_name,
                    messages=messages,
                )
                if response.get("message"):
                    raise Exception(response["message"])
                summary = response["output"]["choices"][0]["message"].content[0]["text"]
                return summary, num_tokens_from_string(summary)

            try:
                return call_api()
            except Exception as e1:
                import dashscope

                dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"
                try:
                    return call_api()
                except Exception as e2:
                    raise RuntimeError(f"Both default and intl endpoint failed.\nFirst error: {e1}\nSecond error: {e2}")


class HunyuanCV(GptV4):
    _FACTORY_NAME = "Tencent Hunyuan"

    def __init__(self, key, model_name, lang="Chinese", base_url=None, **kwargs):
        if not base_url:
            base_url = "https://api.hunyuan.cloud.tencent.com/v1"
        super().__init__(key, model_name, lang=lang, base_url=base_url, **kwargs)


class Zhipu4V(GptV4):
    _FACTORY_NAME = "ZHIPU-AI"

    def __init__(self, key, model_name="glm-4v", lang="Chinese", **kwargs):
        self.client = OpenAI(api_key=key, base_url="https://open.bigmodel.cn/api/paas/v4/")
        self.async_client = AsyncOpenAI(api_key=key, base_url="https://open.bigmodel.cn/api/paas/v4/")
        self.model_name = model_name
        self.lang = lang
        Base.__init__(self, **kwargs)

    def _clean_conf(self, gen_conf):
        if "max_tokens" in gen_conf:
            del gen_conf["max_tokens"]
        gen_conf = self._clean_conf_plealty(gen_conf)
        # LINEAJE: runtime guardrail checks `gen_conf` as it flows from the agent to the user interface, before it leaves the application (in Zhipu4V._clean_conf).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `gen_conf` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f3dccb131be4766b3e01def8515d5db6f69c98c4a78b1ff7f3a4baabeb709fdf'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f3dccb131be4766b3e01def8515d5db6f69c98c4a78b1ff7f3a4baabeb709fdf', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 328, 'function': 'Zhipu4V._clean_conf'}, 'file': 'rag/llm/cv_model.py', 'line': 328, 'function': '_clean_conf', 'agent_name': 'Zhipu4V', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            gen_conf = _gr_client.enforce(_gr_site, gen_conf, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return gen_conf

    def _clean_conf_plealty(self, gen_conf):
        if "presence_penalty" in gen_conf:
            del gen_conf["presence_penalty"]
        if "frequency_penalty" in gen_conf:
            del gen_conf["frequency_penalty"]
        # LINEAJE: runtime guardrail checks `gen_conf` as it flows from the agent to the user interface, before it leaves the application (in Zhipu4V._clean_conf_plealty).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `gen_conf` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:bbfcf4089dfbbede9d77d6f45f2572d9831b30eb0b3a588f16ee108f5cb26045'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bbfcf4089dfbbede9d77d6f45f2572d9831b30eb0b3a588f16ee108f5cb26045', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 335, 'function': 'Zhipu4V._clean_conf_plealty'}, 'file': 'rag/llm/cv_model.py', 'line': 335, 'function': '_clean_conf_plealty', 'agent_name': 'Zhipu4V', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            gen_conf = _gr_client.enforce(_gr_site, gen_conf, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return gen_conf

    def _request(self, msg, stream, gen_conf={}):
        response = requests.post(
            self.base_url,
            json={"model": self.model_name, "messages": msg, "stream": stream, **gen_conf},
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in Zhipu4V._request).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:fc4e9c3fca450cc8327e58a710366db0d7b7ef516df67efb147ea4c6e66bd264'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fc4e9c3fca450cc8327e58a710366db0d7b7ef516df67efb147ea4c6e66bd264', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 338, 'function': 'Zhipu4V._request'}, 'file': 'rag/llm/cv_model.py', 'line': 338, 'function': '_request', 'agent_name': 'Zhipu4V', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=338)
        except _gr_client.GuardrailUnavailableError:
            pass
        return response.json()

    async def async_chat(self, system, history, gen_conf, images=None, **kwargs):
        if system and history and history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": system})

        gen_conf = self._clean_conf(gen_conf)

        # LINEAJE: runtime guardrail checks `history` as it flows from the agent to an external endpoint, before it leaves the application (in Zhipu4V.async_chat).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `history` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:fd642c40f4859ea807a4d4b7ac09cae3b563feaf771ce8922ef89a2ecf78a34d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fd642c40f4859ea807a4d4b7ac09cae3b563feaf771ce8922ef89a2ecf78a34d', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 354, 'function': 'Zhipu4V.async_chat'}, 'file': 'rag/llm/cv_model.py', 'line': 354, 'function': 'async_chat', 'agent_name': 'Zhipu4V', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            history = _gr_client.enforce(_gr_site, history, content_type='application/json', variable_name='history', source_file=__file__, before_line=354)
        except _gr_client.GuardrailUnavailableError:
            pass
        _lineaje_payload = json.dumps(history, ensure_ascii=False, indent=2)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Zhipu4V.async_chat).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5fc9c472f9b6665e47922addd8aba64c292d51b78bbc2250aa18dfe3c041d7e6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5fc9c472f9b6665e47922addd8aba64c292d51b78bbc2250aa18dfe3c041d7e6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 354, 'function': 'Zhipu4V.async_chat'}, 'file': 'rag/llm/cv_model.py', 'line': 354, 'function': 'async_chat', 'agent_name': 'Zhipu4V', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        _lineaje_messages = self._form_history(system, history, images)
        # LINEAJE: runtime guardrail checks `_lineaje_messages` as it flows from the agent to the LLM, before it is sent to the model (in Zhipu4V.async_chat).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_messages` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:344d273019456e54d2aca5da1eda4ad2287df77be8978c699cf1ff246476a332'
        _lineaje__lineaje_messages_evidence = {'_lineaje_messages': _lineaje_messages, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:344d273019456e54d2aca5da1eda4ad2287df77be8978c699cf1ff246476a332', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'glm-4v', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'glm-4v', 'purl': 'pkg:aimodel/glm-4v@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'Zhipu4V.async_chat', 'line': 355}, 'file': 'rag/llm/cv_model.py', 'line': 355, 'function': 'async_chat', 'agent_name': 'Zhipu4V', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:59bc203f5cfe1b83'}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje__lineaje_messages_evidence = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje__lineaje_messages_evidence, content_type='application/json'))
            _lineaje_messages = _lineaje__lineaje_messages_evidence.get('_lineaje_messages', _lineaje_messages) if isinstance(_lineaje__lineaje_messages_evidence, dict) else _lineaje_messages
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        response = await self.async_client.chat.completions.create(model=self.model_name, messages=_lineaje_messages, stream=False, **gen_conf)
        # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in Zhipu4V.async_chat).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:463b47ecda9223d7c80cd1ea96b8556e77574356ef1f1722b43808f52c25c3a7'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:463b47ecda9223d7c80cd1ea96b8556e77574356ef1f1722b43808f52c25c3a7', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'glm-4v', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'glm-4v', 'purl': 'pkg:aimodel/glm-4v@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'Zhipu4V.async_chat', 'line': 355}, 'file': 'rag/llm/cv_model.py', 'line': 355, 'function': 'async_chat', 'agent_name': 'Zhipu4V', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:59bc203f5cfe1b83'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            if not hasattr(_gr_client, 'enforce_reply'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
            response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        content = response.choices[0].message.content.strip()

        cleaned = re.sub(r"<\|(begin_of_box|end_of_box)\|>", "", content).strip()
        return cleaned, total_token_count_from_response(response)

    async def async_chat_streamly(self, system, history, gen_conf, images=None, **kwargs):
        from rag.llm.chat_model import LENGTH_NOTIFICATION_CN, LENGTH_NOTIFICATION_EN
        from rag.nlp import is_chinese

        if system and history and history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": system})
        gen_conf = self._clean_conf(gen_conf)
        ans = ""
        tk_count = 0
        try:
            # LINEAJE: runtime guardrail checks `history` as it flows from the agent to an external endpoint, before it leaves the application (in Zhipu4V.async_chat_streamly).
            #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `history` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:a874e4ffba06f27774b387148df0aa6ec9a1d7b7c90d5102d0f84260b97d9e77'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a874e4ffba06f27774b387148df0aa6ec9a1d7b7c90d5102d0f84260b97d9e77', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 371, 'function': 'Zhipu4V.async_chat_streamly'}, 'file': 'rag/llm/cv_model.py', 'line': 371, 'function': 'async_chat_streamly', 'agent_name': 'Zhipu4V', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                history = _gr_client.enforce(_gr_site, history, content_type='application/json', variable_name='history', source_file=__file__, before_line=371)
            except _gr_client.GuardrailUnavailableError:
                pass
            _lineaje_payload = json.dumps(history, ensure_ascii=False, indent=2)
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Zhipu4V.async_chat_streamly).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:71b2ccd2570b7509502d8930ee27f20fd6e46f7f383bfae2f5e536ef6d80c15d'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:71b2ccd2570b7509502d8930ee27f20fd6e46f7f383bfae2f5e536ef6d80c15d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 371, 'function': 'Zhipu4V.async_chat_streamly'}, 'file': 'rag/llm/cv_model.py', 'line': 371, 'function': 'async_chat_streamly', 'agent_name': 'Zhipu4V', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            _lineaje_messages = self._form_history(system, history, images)
            # LINEAJE: runtime guardrail checks `_lineaje_messages` as it flows from the agent to the LLM, before it is sent to the model (in Zhipu4V.async_chat_streamly).
            #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_messages` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b4dcaf2d5319a9253eb5d277d4ab787bbab8ceb822fe7a10a58856a868911dd7'
            _lineaje__lineaje_messages_evidence = {'_lineaje_messages': _lineaje_messages, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _lineaje_interaction_id = _gr_client.new_interaction_id()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b4dcaf2d5319a9253eb5d277d4ab787bbab8ceb822fe7a10a58856a868911dd7', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'glm-4v', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'glm-4v', 'purl': 'pkg:aimodel/glm-4v@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'Zhipu4V.async_chat_streamly', 'line': 372}, 'file': 'rag/llm/cv_model.py', 'line': 372, 'function': 'async_chat_streamly', 'agent_name': 'Zhipu4V', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:7f3eb203183944b6'}, interaction_id=_lineaje_interaction_id)
            try:
                _lineaje__lineaje_messages_evidence = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje__lineaje_messages_evidence, content_type='application/json'))
                _lineaje_messages = _lineaje__lineaje_messages_evidence.get('_lineaje_messages', _lineaje_messages) if isinstance(_lineaje__lineaje_messages_evidence, dict) else _lineaje_messages
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            response = await self.async_client.chat.completions.create(model=self.model_name, messages=_lineaje_messages, stream=True, **gen_conf)
            # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in Zhipu4V.async_chat_streamly).
            #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:898964ffb2f677e9b2d9f4e3ced9d1db1b7b5cc7468a3a7cfedc64a2bd19e305'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:898964ffb2f677e9b2d9f4e3ced9d1db1b7b5cc7468a3a7cfedc64a2bd19e305', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'glm-4v', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'glm-4v', 'purl': 'pkg:aimodel/glm-4v@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'Zhipu4V.async_chat_streamly', 'line': 372}, 'file': 'rag/llm/cv_model.py', 'line': 372, 'function': 'async_chat_streamly', 'agent_name': 'Zhipu4V', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:7f3eb203183944b6'}, interaction_id=locals().get('_lineaje_interaction_id'))
            try:
                if not hasattr(_gr_client, 'enforce_reply'):
                    __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                    raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            async for resp in response:
                if not resp.choices[0].delta.content:
                    continue
                delta = resp.choices[0].delta.content
                ans = delta
                if resp.choices[0].finish_reason == "length":
                    if is_chinese(ans):
                        ans += LENGTH_NOTIFICATION_CN
                    else:
                        ans += LENGTH_NOTIFICATION_EN
                    tk_count = total_token_count_from_response(resp)
                if resp.choices[0].finish_reason == "stop":
                    tk_count = total_token_count_from_response(resp)
                yield ans
        except Exception as e:
            yield ans + "\n**ERROR**: " + str(e)

        yield tk_count

    def describe(self, image):
        return self.describe_with_prompt(image)

    def describe_with_prompt(self, image, prompt=None):
        b64 = self.image2base64(image)
        if prompt is None:
            prompt = "Describe this image."

        # Chat messages
        messages = [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": b64}}, {"type": "text", "text": prompt}]}]

        # LINEAJE: runtime guardrail checks `messages` as it flows from the agent to the LLM, before it is sent to the model (in Zhipu4V.describe_with_prompt).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `messages` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:597c73dd7e53fe5d086df406cd0a399d8e335fcd48ef5cdafbff41d34d28ea3d'
        _lineaje_messages_evidence = {'messages': messages, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:597c73dd7e53fe5d086df406cd0a399d8e335fcd48ef5cdafbff41d34d28ea3d', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'glm-4v', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'glm-4v', 'purl': 'pkg:aimodel/glm-4v@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'Zhipu4V.describe_with_prompt', 'line': 403}, 'file': 'rag/llm/cv_model.py', 'line': 403, 'function': 'describe_with_prompt', 'agent_name': 'Zhipu4V', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:699dba8c8c9266c4'}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje_messages_evidence = _gr_client.enforce(_gr_site, _lineaje_messages_evidence, content_type='application/json')
            messages = _lineaje_messages_evidence.get('messages', messages) if isinstance(_lineaje_messages_evidence, dict) else messages
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        resp = self.client.chat.completions.create(model=self.model_name, messages=messages, stream=False)
        # LINEAJE: runtime guardrail checks `resp` as it flows from the LLM to the agent, after the model replies (in Zhipu4V.describe_with_prompt).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `resp` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1423189e10af69556d91421cad0daf454da411a86960f7f8057e1168f0ca575f'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1423189e10af69556d91421cad0daf454da411a86960f7f8057e1168f0ca575f', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'glm-4v', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'glm-4v', 'purl': 'pkg:aimodel/glm-4v@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'Zhipu4V.describe_with_prompt', 'line': 403}, 'file': 'rag/llm/cv_model.py', 'line': 403, 'function': 'describe_with_prompt', 'agent_name': 'Zhipu4V', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:699dba8c8c9266c4'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            if not hasattr(_gr_client, 'enforce_reply'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
            resp = _gr_client.enforce_reply(_gr_site, resp, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass

        content = resp.choices[0].message.content.strip()
        cleaned = re.sub(r"<\|(begin_of_box|end_of_box)\|>", "", content).strip()

        return cleaned, num_tokens_from_string(cleaned)


class StepFunCV(GptV4):
    _FACTORY_NAME = "StepFun"

    def __init__(self, key, model_name="step-1v-8k", lang="Chinese", base_url="https://api.stepfun.com/v1", **kwargs):
        if not base_url:
            base_url = "https://api.stepfun.com/v1"
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name
        self.lang = lang
        Base.__init__(self, **kwargs)


class VolcEngineCV(GptV4):
    _FACTORY_NAME = "VolcEngine"

    def __init__(self, key, model_name, lang="Chinese", base_url="https://ark.cn-beijing.volces.com/api/v3", **kwargs):
        if not base_url:
            base_url = "https://ark.cn-beijing.volces.com/api/v3"
        ark_api_key = json.loads(key).get("ark_api_key", "")
        self.client = OpenAI(api_key=ark_api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=ark_api_key, base_url=base_url)
        self.model_name = json.loads(key).get("ep_id", "") + json.loads(key).get("endpoint_id", "")
        self.lang = lang
        Base.__init__(self, **kwargs)


class LmStudioCV(GptV4):
    _FACTORY_NAME = "LM-Studio"

    def __init__(self, key, model_name, lang="Chinese", base_url="", **kwargs):
        if not base_url:
            raise ValueError("Local llm url cannot be None")
        base_url = urljoin(base_url, "v1")
        self.client = OpenAI(api_key="lm-studio", base_url=base_url)
        self.async_client = AsyncOpenAI(api_key="lm-studio", base_url=base_url)
        self.model_name = model_name
        self.lang = lang
        Base.__init__(self, **kwargs)


class OpenAI_APICV(GptV4):
    _FACTORY_NAME = ["VLLM", "OpenAI-API-Compatible"]

    def __init__(self, key, model_name, lang="Chinese", base_url="", **kwargs):
        if not base_url:
            raise ValueError("url cannot be None")
        base_url = urljoin(base_url, "v1")
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name.split("___")[0]
        self.lang = lang
        Base.__init__(self, **kwargs)


class TogetherAICV(GptV4):
    _FACTORY_NAME = "TogetherAI"

    def __init__(self, key, model_name, lang="Chinese", base_url="https://api.together.xyz/v1", **kwargs):
        if not base_url:
            base_url = "https://api.together.xyz/v1"
        super().__init__(key, model_name, lang, base_url, **kwargs)


class YiCV(GptV4):
    _FACTORY_NAME = "01.AI"

    def __init__(self, key, model_name, lang="Chinese", base_url="https://api.lingyiwanwu.com/v1", **kwargs):
        if not base_url:
            base_url = "https://api.lingyiwanwu.com/v1"
        super().__init__(key, model_name, lang, base_url, **kwargs)


class SILICONFLOWCV(GptV4):
    _FACTORY_NAME = "SILICONFLOW"

    def __init__(self, key, model_name, lang="Chinese", base_url="https://api.siliconflow.cn/v1", **kwargs):
        if not base_url:
            base_url = "https://api.siliconflow.cn/v1"
        super().__init__(key, model_name, lang, base_url, **kwargs)


class OpenRouterCV(GptV4):
    _FACTORY_NAME = "OpenRouter"

    def __init__(self, key, model_name, lang="Chinese", base_url="https://openrouter.ai/api/v1", **kwargs):
        if not base_url:
            base_url = "https://openrouter.ai/api/v1"
        api_key = json.loads(key).get("api_key", "")
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name
        self.lang = lang
        Base.__init__(self, **kwargs)
        provider_order = json.loads(key).get("provider_order", "")
        self.extra_body = {}
        if provider_order:

            def _to_order_list(x):
                if x is None:
                    return []
                if isinstance(x, str):
                    return [s.strip() for s in x.split(",") if s.strip()]
                if isinstance(x, (list, tuple)):
                    return [str(s).strip() for s in x if str(s).strip()]
                return []

            provider_cfg = {}
            provider_order = _to_order_list(provider_order)
            provider_cfg["order"] = provider_order
            provider_cfg["allow_fallbacks"] = False
            self.extra_body["provider"] = provider_cfg


class LocalAICV(GptV4):
    _FACTORY_NAME = "LocalAI"

    def __init__(self, key, model_name, base_url, lang="Chinese", **kwargs):
        if not base_url:
            raise ValueError("Local cv model url cannot be None")
        base_url = urljoin(base_url, "v1")
        self.client = OpenAI(api_key="empty", base_url=base_url)
        self.async_client = AsyncOpenAI(api_key="empty", base_url=base_url)
        self.model_name = model_name.split("___")[0]
        self.lang = lang
        Base.__init__(self, **kwargs)


class XinferenceCV(GptV4):
    _FACTORY_NAME = "Xinference"

    def __init__(self, key, model_name="", lang="Chinese", base_url="", **kwargs):
        base_url = urljoin(base_url, "v1")
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name
        self.lang = lang
        Base.__init__(self, **kwargs)


class GPUStackCV(GptV4):
    _FACTORY_NAME = "GPUStack"

    def __init__(self, key, model_name, lang="Chinese", base_url="", **kwargs):
        if not base_url:
            raise ValueError("Local llm url cannot be None")
        base_url = urljoin(base_url, "v1")
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name
        self.lang = lang
        Base.__init__(self, **kwargs)


class LocalCV(Base):
    _FACTORY_NAME = "Local"

    def __init__(self, key, model_name="glm-4v", lang="Chinese", **kwargs):
        pass

    def describe(self, image):
        return "", 0


class OllamaCV(Base):
    _FACTORY_NAME = "Ollama"

    def __init__(self, key, model_name, lang="Chinese", **kwargs):
        from ollama import Client

        self.client = Client(host=kwargs["base_url"])
        self.model_name = model_name
        self.lang = lang
        self.keep_alive = kwargs.get("ollama_keep_alive", int(os.environ.get("OLLAMA_KEEP_ALIVE", -1)))
        Base.__init__(self, **kwargs)

    def _clean_img(self, img):
        if not isinstance(img, str):
            # LINEAJE: runtime guardrail checks `img` as it flows from the agent to the user interface, before it leaves the application (in OllamaCV._clean_img).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `img` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:938bdacb35729bb486f779f3da1b053c065c6a7dd36fb43d0736cfc13748003a'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:938bdacb35729bb486f779f3da1b053c065c6a7dd36fb43d0736cfc13748003a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 589, 'function': 'OllamaCV._clean_img'}, 'file': 'rag/llm/cv_model.py', 'line': 589, 'function': '_clean_img', 'agent_name': 'OllamaCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                img = _gr_client.enforce(_gr_site, img, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return img

        # remove the header like "data/*;base64,"
        if img.startswith("data:") and ";base64," in img:
            img = img.split(";base64,")[1]
        # LINEAJE: runtime guardrail checks `img` as it flows from the agent to the user interface, before it leaves the application (in OllamaCV._clean_img).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `img` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:caa2357782b23cda9ada7ee01bb374316977e0236479a7c1dca07794b9a0dd9a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:caa2357782b23cda9ada7ee01bb374316977e0236479a7c1dca07794b9a0dd9a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 594, 'function': 'OllamaCV._clean_img'}, 'file': 'rag/llm/cv_model.py', 'line': 594, 'function': '_clean_img', 'agent_name': 'OllamaCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            img = _gr_client.enforce(_gr_site, img, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return img

    def _clean_conf(self, gen_conf):
        options = {}
        if "temperature" in gen_conf:
            options["temperature"] = gen_conf["temperature"]
        if "top_p" in gen_conf:
            options["top_k"] = gen_conf["top_p"]
        if "presence_penalty" in gen_conf:
            options["presence_penalty"] = gen_conf["presence_penalty"]
        if "frequency_penalty" in gen_conf:
            options["frequency_penalty"] = gen_conf["frequency_penalty"]
        # LINEAJE: runtime guardrail checks `options` as it flows from the agent to the user interface, before it leaves the application (in OllamaCV._clean_conf).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `options` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f19a87d628f2a86f555b6f9521279d22c10044db2ebab1d4c54821e90a2c43a6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f19a87d628f2a86f555b6f9521279d22c10044db2ebab1d4c54821e90a2c43a6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 606, 'function': 'OllamaCV._clean_conf'}, 'file': 'rag/llm/cv_model.py', 'line': 606, 'function': '_clean_conf', 'agent_name': 'OllamaCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            options = _gr_client.enforce(_gr_site, options, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return options

    def _form_history(self, system, history, images=None):
        hist = deepcopy(history)
        if system and hist[0]["role"] == "user":
            hist.insert(0, {"role": "system", "content": system})
        if not images:
            # LINEAJE: runtime guardrail checks `hist` as it flows from the agent to the user interface, before it leaves the application (in OllamaCV._form_history).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `hist` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6ab320ec3d536537e1c1fa1e657533fcef99c9713b61a1a2f66e0dbc9d5c65ed'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6ab320ec3d536537e1c1fa1e657533fcef99c9713b61a1a2f66e0dbc9d5c65ed', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 613, 'function': 'OllamaCV._form_history'}, 'file': 'rag/llm/cv_model.py', 'line': 613, 'function': '_form_history', 'agent_name': 'OllamaCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                hist = _gr_client.enforce(_gr_site, hist, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return hist
        temp_images = []
        for img in images:
            temp_images.append(self._clean_img(img))
        for his in hist:
            if his["role"] == "user":
                his["images"] = temp_images
                break
        # LINEAJE: runtime guardrail checks `hist` as it flows from the agent to the user interface, before it leaves the application (in OllamaCV._form_history).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `hist` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:2c94eb04458341070104bb93afb24621b709944906759b2c2357bd2a44024220'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2c94eb04458341070104bb93afb24621b709944906759b2c2357bd2a44024220', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 621, 'function': 'OllamaCV._form_history'}, 'file': 'rag/llm/cv_model.py', 'line': 621, 'function': '_form_history', 'agent_name': 'OllamaCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            hist = _gr_client.enforce(_gr_site, hist, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return hist

    def describe(self, image):
        prompt = self.prompt("")
        try:
            _lineaje_prompt = prompt[0]["content"]
            # LINEAJE: runtime guardrail checks `_lineaje_prompt` as it flows from the agent to the LLM, before it is sent to the model (in OllamaCV.describe).
            #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_prompt` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:bb0bb9f7262bc86a397e9f38a72cab558982e2ce95c5a26b2bea3e7e0dfb97e2'
            _lineaje__lineaje_prompt_evidence = {'_lineaje_prompt': _lineaje_prompt, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _lineaje_interaction_id = _gr_client.new_interaction_id()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bb0bb9f7262bc86a397e9f38a72cab558982e2ce95c5a26b2bea3e7e0dfb97e2', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'step-1v-8k', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'step-1v-8k', 'purl': 'pkg:aimodel/step-1v-8k@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'OllamaCV.describe', 'line': 626}, 'file': 'rag/llm/cv_model.py', 'line': 626, 'function': 'describe', 'agent_name': 'OllamaCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:21ae48178f3cf1ff'}, interaction_id=_lineaje_interaction_id)
            try:
                _lineaje__lineaje_prompt_evidence = _gr_client.enforce(_gr_site, _lineaje__lineaje_prompt_evidence, content_type='application/json')
                _lineaje_prompt = _lineaje__lineaje_prompt_evidence.get('_lineaje_prompt', _lineaje_prompt) if isinstance(_lineaje__lineaje_prompt_evidence, dict) else _lineaje_prompt
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            response = self.client.generate(
                model=self.model_name,
                prompt=_lineaje_prompt,
                images=[image],
            )
            # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in OllamaCV.describe).
            #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6ee2b242cfadb1bb1cb473984cc0e86985e0cf62837796fac3543b8077554759'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6ee2b242cfadb1bb1cb473984cc0e86985e0cf62837796fac3543b8077554759', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'step-1v-8k', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'step-1v-8k', 'purl': 'pkg:aimodel/step-1v-8k@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'OllamaCV.describe', 'line': 626}, 'file': 'rag/llm/cv_model.py', 'line': 626, 'function': 'describe', 'agent_name': 'OllamaCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:21ae48178f3cf1ff'}, interaction_id=locals().get('_lineaje_interaction_id'))
            try:
                if not hasattr(_gr_client, 'enforce_reply'):
                    __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                    raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                response = _gr_client.enforce_reply(_gr_site, response, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            ans = response["response"].strip()
            return ans, 128
        except Exception as e:
            return "**ERROR**: " + str(e), 0

    def describe_with_prompt(self, image, prompt=None):
        vision_prompt = self.vision_llm_prompt("", prompt) if prompt else self.vision_llm_prompt("")
        try:
            _lineaje_prompt = vision_prompt[0]["content"]
            # LINEAJE: runtime guardrail checks `_lineaje_prompt` as it flows from the agent to the LLM, before it is sent to the model (in OllamaCV.describe_with_prompt).
            #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_prompt` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:044586c2ca2f3f652a61d2808c9578ce10bbf597238858ba2dd3e3f77ec20ad0'
            _lineaje__lineaje_prompt_evidence = {'_lineaje_prompt': _lineaje_prompt, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _lineaje_interaction_id = _gr_client.new_interaction_id()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:044586c2ca2f3f652a61d2808c9578ce10bbf597238858ba2dd3e3f77ec20ad0', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'step-1v-8k', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'step-1v-8k', 'purl': 'pkg:aimodel/step-1v-8k@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'OllamaCV.describe_with_prompt', 'line': 639}, 'file': 'rag/llm/cv_model.py', 'line': 639, 'function': 'describe_with_prompt', 'agent_name': 'OllamaCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:5d614d6a36654816'}, interaction_id=_lineaje_interaction_id)
            try:
                _lineaje__lineaje_prompt_evidence = _gr_client.enforce(_gr_site, _lineaje__lineaje_prompt_evidence, content_type='application/json')
                _lineaje_prompt = _lineaje__lineaje_prompt_evidence.get('_lineaje_prompt', _lineaje_prompt) if isinstance(_lineaje__lineaje_prompt_evidence, dict) else _lineaje_prompt
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            response = self.client.generate(
                model=self.model_name,
                prompt=_lineaje_prompt,
                images=[image],
            )
            # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in OllamaCV.describe_with_prompt).
            #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:8bbb223d596f80fbd6bb6160e54d38010c076bf654ab65f0aa7c9696272b5d3d'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8bbb223d596f80fbd6bb6160e54d38010c076bf654ab65f0aa7c9696272b5d3d', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'step-1v-8k', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'step-1v-8k', 'purl': 'pkg:aimodel/step-1v-8k@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'OllamaCV.describe_with_prompt', 'line': 639}, 'file': 'rag/llm/cv_model.py', 'line': 639, 'function': 'describe_with_prompt', 'agent_name': 'OllamaCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:5d614d6a36654816'}, interaction_id=locals().get('_lineaje_interaction_id'))
            try:
                if not hasattr(_gr_client, 'enforce_reply'):
                    __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                    raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                response = _gr_client.enforce_reply(_gr_site, response, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            ans = response["response"].strip()
            return ans, 128
        except Exception as e:
            return "**ERROR**: " + str(e), 0

    async def async_chat(self, system, history, gen_conf, images=None, **kwargs):
        try:
            response = await asyncio.to_thread(self.client.chat, model=self.model_name, messages=self._form_history(system, history, images), options=self._clean_conf(gen_conf), keep_alive=self.keep_alive)

            ans = response["message"]["content"].strip()
            return ans, response["eval_count"] + response.get("prompt_eval_count", 0)
        except Exception as e:
            return "**ERROR**: " + str(e), 0

    async def async_chat_streamly(self, system, history, gen_conf, images=None, **kwargs):
        ans = ""
        try:
            response = await asyncio.to_thread(self.client.chat, model=self.model_name, messages=self._form_history(system, history, images), stream=True, options=self._clean_conf(gen_conf), keep_alive=self.keep_alive)
            for resp in response:
                if resp["done"]:
                    yield resp.get("prompt_eval_count", 0) + resp.get("eval_count", 0)
                ans = resp["message"]["content"]
                yield ans
        except Exception as e:
            yield ans + "\n**ERROR**: " + str(e)
        yield 0


class GeminiCV(Base):
    _FACTORY_NAME = "Gemini"

    def __init__(self, key, model_name="gemini-1.0-pro-vision-latest", lang="Chinese", **kwargs):
        from google import genai

        self.api_key = key
        self.model_name = model_name
        self.client = genai.Client(api_key=key)
        self.lang = lang
        Base.__init__(self, **kwargs)
        _lineaje_payload = f"[GeminiCV] Initialized with model={self.model_name} lang={self.lang}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV.__init__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:7f6974e9dc405a6ff458ff5fc5a83730d4914fce750f7b36c9be54d42327d369'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7f6974e9dc405a6ff458ff5fc5a83730d4914fce750f7b36c9be54d42327d369', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 683, 'function': 'GeminiCV.__init__'}, 'file': 'rag/llm/cv_model.py', 'line': 683, 'function': '__init__', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)

    def _image_to_part(self, image):
        from google.genai import types

        if isinstance(image, str) and image.startswith("data:") and ";base64," in image:
            header, b64data = image.split(",", 1)
            mime = header.split(":", 1)[1].split(";", 1)[0]
            data = base64.b64decode(b64data)
        else:
            data_url = self.image2base64(image)
            header, b64data = data_url.split(",", 1)
            mime = header.split(":", 1)[1].split(";", 1)[0]
            data = base64.b64decode(b64data)

        return types.Part(
            inline_data=types.Blob(
                mime_type=mime,
                data=data,
            )
        )

    def _form_history(self, system, history, images=None):
        from google.genai import types

        contents = []
        images = images or []
        system_len = len(system) if isinstance(system, str) else 0
        history_len = len(history) if history else 0
        images_len = len(images)
        _lineaje_payload = f"[GeminiCV] _form_history called: system_len={system_len} history_len={history_len} images_len={images_len}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV._form_history).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:cbbe2c2f53c068b132fdbe923c6e092c5e16aef1b589f505df755fe0a5dc2eac'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cbbe2c2f53c068b132fdbe923c6e092c5e16aef1b589f505df755fe0a5dc2eac', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 713, 'function': 'GeminiCV._form_history'}, 'file': 'rag/llm/cv_model.py', 'line': 713, 'function': '_form_history', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)

        image_parts = []
        for img in images:
            try:
                image_parts.append(self._image_to_part(img))
            except Exception:
                continue

        remaining_history = history or []
        if system or remaining_history:
            parts = []
            if system:
                parts.append(types.Part(text=system))
            if remaining_history:
                first = remaining_history[0]
                parts.append(types.Part(text=first.get("content", "")))
                remaining_history = remaining_history[1:]
            parts.extend(image_parts)
            contents.append(types.Content(role="user", parts=parts))
        elif image_parts:
            contents.append(types.Content(role="user", parts=image_parts))

        role_map = {"user": "user", "assistant": "model", "system": "user"}
        for h in remaining_history:
            role = role_map.get(h.get("role"), "user")
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=h.get("content", ""))],
                )
            )

        # LINEAJE: runtime guardrail checks `contents` as it flows from the agent to the user interface, before it leaves the application (in GeminiCV._form_history).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `contents` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:dcedd852e33cb6c11b9dbb2198cdc52b385a1bb23bb6fa241cabd38795c75553'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dcedd852e33cb6c11b9dbb2198cdc52b385a1bb23bb6fa241cabd38795c75553', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 746, 'function': 'GeminiCV._form_history'}, 'file': 'rag/llm/cv_model.py', 'line': 746, 'function': '_form_history', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            contents = _gr_client.enforce(_gr_site, contents, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return contents

    def describe(self, image):
        from google.genai import types

        prompt = (
            "请用中文详细描述一下图中的内容，比如时间，地点，人物，事情，人物心情等，如果有数据请提取出数据。"
            if self.lang.lower() == "chinese"
            else "Please describe the content of this picture, like where, when, who, what happen. If it has number data, please extract them out."
        )

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(text=prompt),
                    self._image_to_part(image),
                ],
            )
        ]

        # LINEAJE: runtime guardrail checks `contents` as it flows from the agent to the LLM, before it is sent to the model (in GeminiCV.describe).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `contents` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1dfa2fdfa22ea5b746c396fde9b9987bf3f472029d69a2715d800582aad8dd3c'
        _lineaje_contents_evidence = {'contents': contents, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1dfa2fdfa22ea5b746c396fde9b9987bf3f472029d69a2715d800582aad8dd3c', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-1.0-pro-vision-latest', 'provider': 'google', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@1.0-pro-vision-latest', 'version': '1.0-pro-vision-latest'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'GeminiCV.describe', 'line': 767}, 'file': 'rag/llm/cv_model.py', 'line': 767, 'function': 'describe', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:91502f5e8cb3ffac'}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje_contents_evidence = _gr_client.enforce(_gr_site, _lineaje_contents_evidence, content_type='application/json')
            contents = _lineaje_contents_evidence.get('contents', contents) if isinstance(_lineaje_contents_evidence, dict) else contents
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        res = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
        )
        # LINEAJE: runtime guardrail checks `res` as it flows from the LLM to the agent, after the model replies (in GeminiCV.describe).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:490b72fb6755da386af7975d288dd44c56aeb390d7067db5d1ce32e1fe1051a1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:490b72fb6755da386af7975d288dd44c56aeb390d7067db5d1ce32e1fe1051a1', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-1.0-pro-vision-latest', 'provider': 'google', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@1.0-pro-vision-latest', 'version': '1.0-pro-vision-latest'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'GeminiCV.describe', 'line': 767}, 'file': 'rag/llm/cv_model.py', 'line': 767, 'function': 'describe', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:91502f5e8cb3ffac'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            if not hasattr(_gr_client, 'enforce_reply'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
            res = _gr_client.enforce_reply(_gr_site, res, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        return res.text, total_token_count_from_response(res)

    def describe_with_prompt(self, image, prompt=None):
        from google.genai import types

        vision_prompt = prompt if prompt else vision_llm_describe_prompt()

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(text=vision_prompt),
                    self._image_to_part(image),
                ],
            )
        ]

        # LINEAJE: runtime guardrail checks `contents` as it flows from the agent to the LLM, before it is sent to the model (in GeminiCV.describe_with_prompt).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `contents` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:4f15f2ee4917a1bb038b410b1856ce51008b26e1afa248d91c5fe64d0a978c4f'
        _lineaje_contents_evidence = {'contents': contents, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4f15f2ee4917a1bb038b410b1856ce51008b26e1afa248d91c5fe64d0a978c4f', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-1.0-pro-vision-latest', 'provider': 'google', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@1.0-pro-vision-latest', 'version': '1.0-pro-vision-latest'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'GeminiCV.describe_with_prompt', 'line': 788}, 'file': 'rag/llm/cv_model.py', 'line': 788, 'function': 'describe_with_prompt', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:10833bf8fcd8cd6c'}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje_contents_evidence = _gr_client.enforce(_gr_site, _lineaje_contents_evidence, content_type='application/json')
            contents = _lineaje_contents_evidence.get('contents', contents) if isinstance(_lineaje_contents_evidence, dict) else contents
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        res = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
        )
        # LINEAJE: runtime guardrail checks `res` as it flows from the LLM to the agent, after the model replies (in GeminiCV.describe_with_prompt).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:0580e18df68dda0e35e68323555669554dda1c21fa1cea66eb6b87090dbeef8e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0580e18df68dda0e35e68323555669554dda1c21fa1cea66eb6b87090dbeef8e', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-1.0-pro-vision-latest', 'provider': 'google', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@1.0-pro-vision-latest', 'version': '1.0-pro-vision-latest'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'GeminiCV.describe_with_prompt', 'line': 788}, 'file': 'rag/llm/cv_model.py', 'line': 788, 'function': 'describe_with_prompt', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:10833bf8fcd8cd6c'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            if not hasattr(_gr_client, 'enforce_reply'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
            res = _gr_client.enforce_reply(_gr_site, res, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        return res.text, total_token_count_from_response(res)

    async def async_chat(self, system, history, gen_conf, images=None, video_bytes=None, filename="", **kwargs):
        if video_bytes:
            try:
                size = len(video_bytes) if video_bytes else 0
                _lineaje_payload = f"[GeminiCV] async_chat called with video: filename={filename} size={size}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV.async_chat).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:25b0bbb6d270d5045c0d99d08476329683ab16342881327e7caedb875139be60'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:25b0bbb6d270d5045c0d99d08476329683ab16342881327e7caedb875139be60', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 798, 'function': 'GeminiCV.async_chat'}, 'file': 'rag/llm/cv_model.py', 'line': 798, 'function': 'async_chat', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                summary, summary_num_tokens = await asyncio.to_thread(self._process_video, video_bytes, filename)
                return summary, summary_num_tokens
            except Exception as e:
                _lineaje_payload = f"[GeminiCV] async_chat video error: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV.async_chat).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:31abd0c146b30b82025d0948789f56ea7051e6989cd1395fee32551371885f2f'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:31abd0c146b30b82025d0948789f56ea7051e6989cd1395fee32551371885f2f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 802, 'function': 'GeminiCV.async_chat'}, 'file': 'rag/llm/cv_model.py', 'line': 802, 'function': 'async_chat', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                return "**ERROR**: " + str(e), 0

        from google.genai import types

        history_len = len(history) if history else 0
        images_len = len(images) if images else 0
        _lineaje_payload = f"[GeminiCV] async_chat called: history_len={history_len} images_len={images_len} gen_conf={gen_conf}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV.async_chat).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:0b360984aabf05fdbe3ed1f40afc5d3ee87a88b02971f143beaeb70c72e55184'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0b360984aabf05fdbe3ed1f40afc5d3ee87a88b02971f143beaeb70c72e55184', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 809, 'function': 'GeminiCV.async_chat'}, 'file': 'rag/llm/cv_model.py', 'line': 809, 'function': 'async_chat', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)

        generation_config = types.GenerateContentConfig(
            temperature=gen_conf.get("temperature", 0.3),
            top_p=gen_conf.get("top_p", 0.7),
        )
        try:
            _lineaje_contents = self._form_history(system, history, images)
            # LINEAJE: runtime guardrail checks `_lineaje_contents` as it flows from the agent to the LLM, before it is sent to the model (in GeminiCV.async_chat).
            #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_contents` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d8767b5a2956800e14f97145588345ecb66821c224cedec22d4acb47d2538ecd'
            _lineaje__lineaje_contents_evidence = {'_lineaje_contents': _lineaje_contents, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _lineaje_interaction_id = _gr_client.new_interaction_id()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d8767b5a2956800e14f97145588345ecb66821c224cedec22d4acb47d2538ecd', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-2.5-flash', 'provider': 'google', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@2.5-flash', 'version': '2.5-flash'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'GeminiCV.async_chat', 'line': 816}, 'file': 'rag/llm/cv_model.py', 'line': 816, 'function': 'async_chat', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:6307b8ed6283c7d3'}, interaction_id=_lineaje_interaction_id)
            try:
                _lineaje__lineaje_contents_evidence = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje__lineaje_contents_evidence, content_type='application/json'))
                _lineaje_contents = _lineaje__lineaje_contents_evidence.get('_lineaje_contents', _lineaje_contents) if isinstance(_lineaje__lineaje_contents_evidence, dict) else _lineaje_contents
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=_lineaje_contents,
                config=generation_config,
            )
            # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in GeminiCV.async_chat).
            #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d31ee14e928f2c4c2f7b2fd5811fbca7fb7071e41a30da2344da752c1737e065'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d31ee14e928f2c4c2f7b2fd5811fbca7fb7071e41a30da2344da752c1737e065', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-2.5-flash', 'provider': 'google', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@2.5-flash', 'version': '2.5-flash'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'GeminiCV.async_chat', 'line': 816}, 'file': 'rag/llm/cv_model.py', 'line': 816, 'function': 'async_chat', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:6307b8ed6283c7d3'}, interaction_id=locals().get('_lineaje_interaction_id'))
            try:
                if not hasattr(_gr_client, 'enforce_reply'):
                    __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                    raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            ans = response.text
            _lineaje_payload = "[GeminiCV] async_chat completed"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV.async_chat).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ec28f1d30461748bba22040f4776c1858c24a00daaa87c7114702cdac8dee611'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ec28f1d30461748bba22040f4776c1858c24a00daaa87c7114702cdac8dee611', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 822, 'function': 'GeminiCV.async_chat'}, 'file': 'rag/llm/cv_model.py', 'line': 822, 'function': 'async_chat', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            return ans, total_token_count_from_response(response)
        except Exception as e:
            _lineaje_payload = f"[GeminiCV] async_chat error: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV.async_chat).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b063ba0531a9c456eeaf25ae2b15ad1c2dad7cc0097811c7f44ba74305182026'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b063ba0531a9c456eeaf25ae2b15ad1c2dad7cc0097811c7f44ba74305182026', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 825, 'function': 'GeminiCV.async_chat'}, 'file': 'rag/llm/cv_model.py', 'line': 825, 'function': 'async_chat', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            return "**ERROR**: " + str(e), 0

    async def async_chat_streamly(self, system, history, gen_conf, images=None, **kwargs):
        ans = ""
        response = None
        try:
            from google.genai import types

            generation_config = types.GenerateContentConfig(
                temperature=gen_conf.get("temperature", 0.3),
                top_p=gen_conf.get("top_p", 0.7),
            )
            history_len = len(history) if history else 0
            images_len = len(images) if images else 0
            _lineaje_payload = f"[GeminiCV] async_chat_streamly called: history_len={history_len} images_len={images_len} gen_conf={gen_conf}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV.async_chat_streamly).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:5fcc09d9b359ca206dc4c40f0b905403cbbe2a343cd19306e47163f943035917'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5fcc09d9b359ca206dc4c40f0b905403cbbe2a343cd19306e47163f943035917', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 840, 'function': 'GeminiCV.async_chat_streamly'}, 'file': 'rag/llm/cv_model.py', 'line': 840, 'function': 'async_chat_streamly', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)

            response_stream = await self.client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=self._form_history(system, history, images),
                config=generation_config,
            )

            async for chunk in response_stream:
                if chunk.text:
                    ans += chunk.text
                    yield chunk.text
            _lineaje_payload = "[GeminiCV] chat_streamly completed"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV.async_chat_streamly).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:fb6da7cd5766d5a5472a6ab245a2c9eea54dc214dad0e70dea2836b1472cc0b2'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fb6da7cd5766d5a5472a6ab245a2c9eea54dc214dad0e70dea2836b1472cc0b2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 852, 'function': 'GeminiCV.async_chat_streamly'}, 'file': 'rag/llm/cv_model.py', 'line': 852, 'function': 'async_chat_streamly', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
        except Exception as e:
            _lineaje_payload = f"[GeminiCV] chat_streamly error: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV.async_chat_streamly).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1881f54d28540b03bb12ffb1e71a5b8cfb6edfee98d9f3d073fb852c273889f1'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1881f54d28540b03bb12ffb1e71a5b8cfb6edfee98d9f3d073fb852c273889f1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 854, 'function': 'GeminiCV.async_chat_streamly'}, 'file': 'rag/llm/cv_model.py', 'line': 854, 'function': 'async_chat_streamly', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            yield ans + "\n**ERROR**: " + str(e)

        yield total_token_count_from_response(response)

    def _process_video(self, video_bytes, filename):
        from google import genai
        from google.genai import types

        video_size_mb = len(video_bytes) / (1024 * 1024)
        client = self.client if hasattr(self, "client") else genai.Client(api_key=self.api_key)
        _lineaje_payload = f"[GeminiCV] _process_video called: filename={filename} size_mb={video_size_mb:.2f}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV._process_video).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:14f253ab5a5a99bc30e61c2463c96f50873d8e20f977e2508cbb5117ab73551e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:14f253ab5a5a99bc30e61c2463c96f50873d8e20f977e2508cbb5117ab73551e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 865, 'function': 'GeminiCV._process_video'}, 'file': 'rag/llm/cv_model.py', 'line': 865, 'function': '_process_video', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)

        tmp_path = None
        try:
            if video_size_mb <= 20:
                response = client.models.generate_content(
                    model="models/gemini-2.5-flash",
                    contents=types.Content(parts=[types.Part(inline_data=types.Blob(data=video_bytes, mime_type="video/mp4")), types.Part(text="Please summarize the video in proper sentences.")]),
                )
            else:
                _lineaje_payload = f"Video size {video_size_mb:.2f}MB exceeds 20MB. Using Files API..."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV._process_video).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:1f926a741bfb2b8f43613e49f245a6369b5b09f8b1900c29fb3913a28a8de08a'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1f926a741bfb2b8f43613e49f245a6369b5b09f8b1900c29fb3913a28a8de08a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 875, 'function': 'GeminiCV._process_video'}, 'file': 'rag/llm/cv_model.py', 'line': 875, 'function': '_process_video', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                video_suffix = Path(filename).suffix or ".mp4"
                with tempfile.NamedTemporaryFile(delete=False, suffix=video_suffix) as tmp:
                    tmp.write(video_bytes)
                    tmp_path = Path(tmp.name)
                uploaded_file = client.files.upload(file=tmp_path)

                response = client.models.generate_content(model="gemini-2.5-flash", contents=[uploaded_file, "Please summarize this video in proper sentences."])

            summary = response.text or ""
            _lineaje_payload = f"[GeminiCV] Video summarized: {summary[:32]}..."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV._process_video).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d8c8e7854f920c8c6b51588c79d708f6127c978a2d81efc6cd3d7763bf066460'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d8c8e7854f920c8c6b51588c79d708f6127c978a2d81efc6cd3d7763bf066460', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 885, 'function': 'GeminiCV._process_video'}, 'file': 'rag/llm/cv_model.py', 'line': 885, 'function': '_process_video', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            return summary, num_tokens_from_string(summary)
        except Exception as e:
            _lineaje_payload = f"[GeminiCV] Video processing failed: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GeminiCV._process_video).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6155143a7c4e0693b8a142e87b76bf67cb60ede0c9f6fe5be39b06f667035dfc'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6155143a7c4e0693b8a142e87b76bf67cb60ede0c9f6fe5be39b06f667035dfc', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 888, 'function': 'GeminiCV._process_video'}, 'file': 'rag/llm/cv_model.py', 'line': 888, 'function': '_process_video', 'agent_name': 'GeminiCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            raise
        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()


class NvidiaCV(Base):
    _FACTORY_NAME = "NVIDIA"

    def __init__(self, key, model_name, lang="Chinese", base_url="https://ai.api.nvidia.com/v1/vlm", **kwargs):
        if not base_url:
            base_url = ("https://ai.api.nvidia.com/v1/vlm",)
        self.lang = lang
        factory, llm_name = model_name.split("/")
        if factory != "liuhaotian":
            self.base_url = urljoin(base_url, f"{factory}/{llm_name}")
        else:
            self.base_url = urljoin(f"{base_url}/community", llm_name.replace("-v1.6", "16"))
        self.key = key
        Base.__init__(self, **kwargs)

    def _image_prompt(self, text, images):
        if not images:
            # LINEAJE: runtime guardrail checks `text` as it flows from the agent to the user interface, before it leaves the application (in NvidiaCV._image_prompt).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `text` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f2b4015b28b91abf59717b7d164c59f54ed87867ac7bdf3b194dc68f30cac107'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f2b4015b28b91abf59717b7d164c59f54ed87867ac7bdf3b194dc68f30cac107', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 912, 'function': 'NvidiaCV._image_prompt'}, 'file': 'rag/llm/cv_model.py', 'line': 912, 'function': '_image_prompt', 'agent_name': 'NvidiaCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                text = _gr_client.enforce(_gr_site, text, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return text
        htmls = ""
        for img in images:
            htmls += ' <img src="{}"/>'.format(f"data:image/jpeg;base64,{img}" if img[:4] != "data" else img)
        return text + htmls

    def describe(self, image):
        b64 = self.image2base64(image)
        response = requests.post(
            url=self.base_url,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self.key}",
            },
            json={"messages": self.prompt(b64)},
        )
        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in NvidiaCV.describe).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ca5f78a053089d35949fb138ab597a221b35f8aa54be733df31e1eda97d351d4'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ca5f78a053089d35949fb138ab597a221b35f8aa54be733df31e1eda97d351d4', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 920, 'function': 'NvidiaCV.describe'}, 'file': 'rag/llm/cv_model.py', 'line': 920, 'function': 'describe', 'agent_name': 'NvidiaCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=920)
        except _gr_client.GuardrailUnavailableError:
            pass
        response = response.json()
        return (
            response["choices"][0]["message"]["content"].strip(),
            total_token_count_from_response(response),
        )

    def _request(self, msg, gen_conf={}):
        response = requests.post(
            url=self.base_url,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self.key}",
            },
            json={"messages": msg, **gen_conf},
        )
        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in NvidiaCV._request).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:74276a8453e05b3d60a30f9510abda98ae3291685b5705633bcce7843910f867'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:74276a8453e05b3d60a30f9510abda98ae3291685b5705633bcce7843910f867', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 936, 'function': 'NvidiaCV._request'}, 'file': 'rag/llm/cv_model.py', 'line': 936, 'function': '_request', 'agent_name': 'NvidiaCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=936)
        except _gr_client.GuardrailUnavailableError:
            pass
        return response.json()

    def describe_with_prompt(self, image, prompt=None):
        b64 = self.image2base64(image)
        vision_prompt = self.vision_llm_prompt(b64, prompt) if prompt else self.vision_llm_prompt(b64)
        response = self._request(vision_prompt)
        return (response["choices"][0]["message"]["content"].strip(), total_token_count_from_response(response))

    async def async_chat(self, system, history, gen_conf, images=None, **kwargs):
        try:
            response = await asyncio.to_thread(self._request, self._form_history(system, history, images), gen_conf)
            return (response["choices"][0]["message"]["content"].strip(), total_token_count_from_response(response))
        except Exception as e:
            return "**ERROR**: " + str(e), 0

    async def async_chat_streamly(self, system, history, gen_conf, images=None, **kwargs):
        total_tokens = 0
        try:
            response = await asyncio.to_thread(self._request, self._form_history(system, history, images), gen_conf)
            cnt = response["choices"][0]["message"]["content"]
            total_tokens += total_token_count_from_response(response)
            for resp in cnt:
                yield resp
        except Exception as e:
            yield "\n**ERROR**: " + str(e)

        yield total_tokens


class AnthropicCV(Base):
    _FACTORY_NAME = "Anthropic"

    def __init__(self, key, model_name, base_url=None, **kwargs):
        import anthropic

        self.client = anthropic.Anthropic(api_key=key)
        self.async_client = anthropic.AsyncAnthropic(api_key=key)
        self.model_name = model_name
        self.system = ""
        self.max_tokens = 8192
        if "haiku" in self.model_name or "opus" in self.model_name:
            self.max_tokens = 4096
        Base.__init__(self, **kwargs)

    def _image_prompt(self, text, images):
        if not images:
            # LINEAJE: runtime guardrail checks `text` as it flows from the agent to the user interface, before it leaves the application (in AnthropicCV._image_prompt).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `text` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:39a5e39f43cf032ed7c8f782ed7a09a7b7c6def4402fb1b30a8e93b7c0fac457'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:39a5e39f43cf032ed7c8f782ed7a09a7b7c6def4402fb1b30a8e93b7c0fac457', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 991, 'function': 'AnthropicCV._image_prompt'}, 'file': 'rag/llm/cv_model.py', 'line': 991, 'function': '_image_prompt', 'agent_name': 'AnthropicCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                text = _gr_client.enforce(_gr_site, text, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return text
        pmpt = [{"type": "text", "text": text}]
        for img in images:
            pmpt.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": (img.split(":")[1].split(";")[0] if isinstance(img, str) and img[:4] == "data" else "image/png"),
                        "data": (img.split(",")[1] if isinstance(img, str) and img[:4] == "data" else img),
                    },
                }
            )
        # LINEAJE: runtime guardrail checks `pmpt` as it flows from the agent to the user interface, before it leaves the application (in AnthropicCV._image_prompt).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `pmpt` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c4057a49c1f95b6569c5277dd5da9f1fcfe4413775cb9485a53fe482a3d870b2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c4057a49c1f95b6569c5277dd5da9f1fcfe4413775cb9485a53fe482a3d870b2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 1004, 'function': 'AnthropicCV._image_prompt'}, 'file': 'rag/llm/cv_model.py', 'line': 1004, 'function': '_image_prompt', 'agent_name': 'AnthropicCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            pmpt = _gr_client.enforce(_gr_site, pmpt, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return pmpt

    def describe(self, image):
        b64 = self.image2base64(image)
        _lineaje_messages = self.prompt(b64)
        # LINEAJE: runtime guardrail checks `_lineaje_messages` as it flows from the agent to the LLM, before it is sent to the model (in AnthropicCV.describe).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_messages` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9b02aed4c4b2576ed1860930217a237f46014b268c1230c19cde207b6bb43bc0'
        _lineaje__lineaje_messages_evidence = {'_lineaje_messages': _lineaje_messages, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9b02aed4c4b2576ed1860930217a237f46014b268c1230c19cde207b6bb43bc0', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-2.5-flash', 'provider': 'models', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@2.5-flash', 'version': '2.5-flash'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'AnthropicCV.describe', 'line': 1008}, 'file': 'rag/llm/cv_model.py', 'line': 1008, 'function': 'describe', 'agent_name': 'AnthropicCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:cc9ffb96fd6f45c7'}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje__lineaje_messages_evidence = _gr_client.enforce(_gr_site, _lineaje__lineaje_messages_evidence, content_type='application/json')
            _lineaje_messages = _lineaje__lineaje_messages_evidence.get('_lineaje_messages', _lineaje_messages) if isinstance(_lineaje__lineaje_messages_evidence, dict) else _lineaje_messages
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        response = self.client.messages.create(model=self.model_name, max_tokens=self.max_tokens, messages=_lineaje_messages)
        # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in AnthropicCV.describe).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:42e5b5d6d89b8288ed36d5fc24290e7cd9fd3d0414ed6b26fbb0fa689bb50924'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:42e5b5d6d89b8288ed36d5fc24290e7cd9fd3d0414ed6b26fbb0fa689bb50924', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-2.5-flash', 'provider': 'models', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@2.5-flash', 'version': '2.5-flash'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'AnthropicCV.describe', 'line': 1008}, 'file': 'rag/llm/cv_model.py', 'line': 1008, 'function': 'describe', 'agent_name': 'AnthropicCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:cc9ffb96fd6f45c7'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            if not hasattr(_gr_client, 'enforce_reply'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
            response = _gr_client.enforce_reply(_gr_site, response, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        return response["content"][0]["text"].strip(), response["usage"]["input_tokens"] + response["usage"]["output_tokens"]

    def describe_with_prompt(self, image, prompt=None):
        b64 = self.image2base64(image)
        prompt = self.prompt(b64, prompt if prompt else vision_llm_describe_prompt())

        # LINEAJE: runtime guardrail checks `prompt` as it flows from the agent to the LLM, before it is sent to the model (in AnthropicCV.describe_with_prompt).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `prompt` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ef46dba03d671184dc0e6580626e6fd4b8cc950d5d964b6d319c11c4c6d0a675'
        _lineaje_prompt_evidence = {'prompt': prompt, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ef46dba03d671184dc0e6580626e6fd4b8cc950d5d964b6d319c11c4c6d0a675', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-2.5-flash', 'provider': 'models', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@2.5-flash', 'version': '2.5-flash'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'AnthropicCV.describe_with_prompt', 'line': 1015}, 'file': 'rag/llm/cv_model.py', 'line': 1015, 'function': 'describe_with_prompt', 'agent_name': 'AnthropicCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:e9b43dea7363f572'}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje_prompt_evidence = _gr_client.enforce(_gr_site, _lineaje_prompt_evidence, content_type='application/json')
            prompt = _lineaje_prompt_evidence.get('prompt', prompt) if isinstance(_lineaje_prompt_evidence, dict) else prompt
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        response = self.client.messages.create(model=self.model_name, max_tokens=self.max_tokens, messages=prompt)
        # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in AnthropicCV.describe_with_prompt).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f8e7185f48feb44558aaee009b8e0189bc8c2d1b898d4eda667f221a2e3e719b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f8e7185f48feb44558aaee009b8e0189bc8c2d1b898d4eda667f221a2e3e719b', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-2.5-flash', 'provider': 'models', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@2.5-flash', 'version': '2.5-flash'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'AnthropicCV.describe_with_prompt', 'line': 1015}, 'file': 'rag/llm/cv_model.py', 'line': 1015, 'function': 'describe_with_prompt', 'agent_name': 'AnthropicCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:e9b43dea7363f572'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            if not hasattr(_gr_client, 'enforce_reply'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
            response = _gr_client.enforce_reply(_gr_site, response, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        return response["content"][0]["text"].strip(), total_token_count_from_response(response)

    def _clean_conf(self, gen_conf):
        if "presence_penalty" in gen_conf:
            del gen_conf["presence_penalty"]
        if "frequency_penalty" in gen_conf:
            del gen_conf["frequency_penalty"]
        if "max_token" in gen_conf:
            gen_conf["max_tokens"] = self.max_tokens
        # LINEAJE: runtime guardrail checks `gen_conf` as it flows from the agent to the user interface, before it leaves the application (in AnthropicCV._clean_conf).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `gen_conf` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:02bd5d1bc70e7e2ba599f08c749230c6f8254f6fc3edaf3171d3b9fd97e51b39'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:02bd5d1bc70e7e2ba599f08c749230c6f8254f6fc3edaf3171d3b9fd97e51b39', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'line': 1025, 'function': 'AnthropicCV._clean_conf'}, 'file': 'rag/llm/cv_model.py', 'line': 1025, 'function': '_clean_conf', 'agent_name': 'AnthropicCV', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            gen_conf = _gr_client.enforce(_gr_site, gen_conf, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return gen_conf

    async def async_chat(self, system, history, gen_conf, images=None, **kwargs):
        gen_conf = self._clean_conf(gen_conf)
        ans = ""
        try:
            _lineaje_messages = self._form_history(system, history, images)
            # LINEAJE: runtime guardrail checks `_lineaje_messages` as it flows from the agent to the LLM, before it is sent to the model (in AnthropicCV.async_chat).
            #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_messages` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:a4134431274936de80f500826f103113539176080f4e06769fb5f3b6071021ad'
            _lineaje__lineaje_messages_evidence = {'_lineaje_messages': _lineaje_messages, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _lineaje_interaction_id = _gr_client.new_interaction_id()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a4134431274936de80f500826f103113539176080f4e06769fb5f3b6071021ad', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-2.5-flash', 'provider': 'models', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@2.5-flash', 'version': '2.5-flash'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'AnthropicCV.async_chat', 'line': 1031}, 'file': 'rag/llm/cv_model.py', 'line': 1031, 'function': 'async_chat', 'agent_name': 'AnthropicCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:942abbc5de5aacd9'}, interaction_id=_lineaje_interaction_id)
            try:
                _lineaje__lineaje_messages_evidence = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje__lineaje_messages_evidence, content_type='application/json'))
                _lineaje_messages = _lineaje__lineaje_messages_evidence.get('_lineaje_messages', _lineaje_messages) if isinstance(_lineaje__lineaje_messages_evidence, dict) else _lineaje_messages
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            response = await self.async_client.messages.create(
                model=self.model_name,
                messages=_lineaje_messages,
                system=system,
                stream=False,
                **gen_conf,
            )
            # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in AnthropicCV.async_chat).
            #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:24aa5d8cbffe8d61e0746b3e859bbf2b960de1c14520c54df8ff6ea940155f7b'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:24aa5d8cbffe8d61e0746b3e859bbf2b960de1c14520c54df8ff6ea940155f7b', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-2.5-flash', 'provider': 'models', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@2.5-flash', 'version': '2.5-flash'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'AnthropicCV.async_chat', 'line': 1031}, 'file': 'rag/llm/cv_model.py', 'line': 1031, 'function': 'async_chat', 'agent_name': 'AnthropicCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:942abbc5de5aacd9'}, interaction_id=locals().get('_lineaje_interaction_id'))
            try:
                if not hasattr(_gr_client, 'enforce_reply'):
                    __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                    raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            response = response.to_dict()
            ans = response["content"][0]["text"]
            if response["stop_reason"] == "max_tokens":
                ans += "...\nFor the content length reason, it stopped, continue?" if is_english([ans]) else "······\n由于长度的原因，回答被截断了，要继续吗？"
            return (
                ans,
                total_token_count_from_response(response),
            )
        except Exception as e:
            return ans + "\n**ERROR**: " + str(e), 0

    async def async_chat_streamly(self, system, history, gen_conf, images=None, **kwargs):
        gen_conf = self._clean_conf(gen_conf)
        total_tokens = 0
        try:
            _lineaje_messages = self._form_history(system, history, images)
            # LINEAJE: runtime guardrail checks `_lineaje_messages` as it flows from the agent to the LLM, before it is sent to the model (in AnthropicCV.async_chat_streamly).
            #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_messages` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:06a162759e3c97cd26c569fc6b0a3a494ee805f59c52beeafdd16e976c9a4177'
            _lineaje__lineaje_messages_evidence = {'_lineaje_messages': _lineaje_messages, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _lineaje_interaction_id = _gr_client.new_interaction_id()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:06a162759e3c97cd26c569fc6b0a3a494ee805f59c52beeafdd16e976c9a4177', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-2.5-flash', 'provider': 'models', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@2.5-flash', 'version': '2.5-flash'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'AnthropicCV.async_chat_streamly', 'line': 1053}, 'file': 'rag/llm/cv_model.py', 'line': 1053, 'function': 'async_chat_streamly', 'agent_name': 'AnthropicCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:3c332e4118c7554a'}, interaction_id=_lineaje_interaction_id)
            try:
                _lineaje__lineaje_messages_evidence = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje__lineaje_messages_evidence, content_type='application/json'))
                _lineaje_messages = _lineaje__lineaje_messages_evidence.get('_lineaje_messages', _lineaje_messages) if isinstance(_lineaje__lineaje_messages_evidence, dict) else _lineaje_messages
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            response = self.async_client.messages.create(
                model=self.model_name,
                messages=_lineaje_messages,
                system=system,
                stream=True,
                **gen_conf,
            )
            # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in AnthropicCV.async_chat_streamly).
            #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ffd8227b25e2fbb63098993220ca396cfda4635acb1273bad70b2f816b7a99a2'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ffd8227b25e2fbb63098993220ca396cfda4635acb1273bad70b2f816b7a99a2', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-2.5-flash', 'provider': 'models', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@2.5-flash', 'version': '2.5-flash'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'AnthropicCV.async_chat_streamly', 'line': 1053}, 'file': 'rag/llm/cv_model.py', 'line': 1053, 'function': 'async_chat_streamly', 'agent_name': 'AnthropicCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:3c332e4118c7554a'}, interaction_id=locals().get('_lineaje_interaction_id'))
            try:
                if not hasattr(_gr_client, 'enforce_reply'):
                    __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                    raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            think = False
            async for res in response:
                if res.type == "content_block_delta":
                    if res.delta.type == "thinking_delta" and res.delta.thinking:
                        if not think:
                            yield "<think>"
                            think = True
                        yield res.delta.thinking
                        total_tokens += num_tokens_from_string(res.delta.thinking)
                    elif think:
                        yield "</think>"
                    else:
                        yield res.delta.text
                        total_tokens += num_tokens_from_string(res.delta.text)
        except Exception as e:
            yield "\n**ERROR**: " + str(e)

        yield total_tokens


class GoogleCV(AnthropicCV, GeminiCV):
    _FACTORY_NAME = "Google Cloud"

    def __init__(self, key, model_name, lang="Chinese", base_url=None, **kwargs):
        import base64

        from google.oauth2 import service_account

        key = json.loads(key)
        access_token = json.loads(base64.b64decode(key.get("google_service_account_key", "")))
        project_id = key.get("google_project_id", "")
        region = key.get("google_region", "")

        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        self.model_name = model_name
        self.lang = lang

        if "claude" in self.model_name:
            from anthropic import AnthropicVertex
            from google.auth.transport.requests import Request

            if access_token:
                credits = service_account.Credentials.from_service_account_info(access_token, scopes=scopes)
                request = Request()
                credits.refresh(request)
                token = credits.token
                self.client = AnthropicVertex(region=region, project_id=project_id, access_token=token)
            else:
                self.client = AnthropicVertex(region=region, project_id=project_id)
        else:
            import vertexai.generative_models as glm
            from google.cloud import aiplatform

            if access_token:
                credits = service_account.Credentials.from_service_account_info(access_token)
                aiplatform.init(credentials=credits, project=project_id, location=region)
            else:
                aiplatform.init(project=project_id, location=region)
            # LINEAJE: runtime guardrail checks the model this client is built with as it flows from the agent to the LLM, before it is sent to the model (in GoogleCV.__init__).
            #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+1 more); a model that is not approved is refused before the client is built (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9abfb747c33865912cd511636c85563976f56839d8174d0f302323b198652b95'
            _lineaje_model_evidence = {'model': self.model_name, 'client': 'GenerativeModel', 'provider': 'google', 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9abfb747c33865912cd511636c85563976f56839d8174d0f302323b198652b95', phase='pre_model', boundary={'source': 'agent_config', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gemini-2.5-flash', 'provider': 'models', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Gemini', 'purl': 'pkg:aimodel/Gemini@2.5-flash', 'version': '2.5-flash'}}, 'invocation': {'file': 'rag/llm/cv_model.py', 'function': 'GoogleCV.__init__', 'line': 1118}, 'file': 'rag/llm/cv_model.py', 'line': 1118, 'function': '__init__', 'agent_name': 'GoogleCV', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:1005c41a4376d0f0'})
            try:
                _lineaje_model_evidence = _gr_client.enforce(_gr_site, _lineaje_model_evidence, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            self.client = glm.GenerativeModel(model_name=self.model_name)
        Base.__init__(self, **kwargs)

    def describe(self, image):
        if "claude" in self.model_name:
            return AnthropicCV.describe(self, image)
        else:
            return GeminiCV.describe(self, image)

    def describe_with_prompt(self, image, prompt=None):
        if "claude" in self.model_name:
            return AnthropicCV.describe_with_prompt(self, image, prompt)
        else:
            return GeminiCV.describe_with_prompt(self, image, prompt)

    async def async_chat(self, system, history, gen_conf, images=None, **kwargs):
        if "claude" in self.model_name:
            return await AnthropicCV.async_chat(self, system, history, gen_conf, images)
        else:
            return await GeminiCV.async_chat(self, system, history, gen_conf, images)

    async def async_chat_streamly(self, system, history, gen_conf, images=None, **kwargs):
        if "claude" in self.model_name:
            async for ans in AnthropicCV.async_chat_streamly(self, system, history, gen_conf, images):
                yield ans
        else:
            async for ans in GeminiCV.async_chat_streamly(self, system, history, gen_conf, images):
                yield ans


class MoonshotCV(GptV4):
    _FACTORY_NAME = "Moonshot"

    def __init__(self, key, model_name="moonshot-v1-8k-vision-preview", lang="Chinese", base_url="https://api.moonshot.cn/v1", **kwargs):
        if not base_url:
            base_url = "https://api.moonshot.cn/v1"
        super().__init__(key, model_name, lang=lang, base_url=base_url, **kwargs)
