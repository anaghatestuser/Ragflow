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
import json
import logging
import os
import random
import re
import time
from abc import ABC
from copy import deepcopy
from urllib.parse import urljoin

import json_repair
import litellm
import openai
from openai import AsyncOpenAI, OpenAI
from strenum import StrEnum

from common.token_utils import num_tokens_from_string, total_token_count_from_response
from rag.llm import FACTORY_DEFAULT_BASE_URL, LITELLM_PROVIDER_PREFIX, SupportedLiteLLMProvider
from rag.nlp import is_chinese, is_english


# Error message constants
class LLMErrorCode(StrEnum):
    ERROR_RATE_LIMIT = "RATE_LIMIT_EXCEEDED"
    ERROR_AUTHENTICATION = "AUTH_ERROR"
    ERROR_INVALID_REQUEST = "INVALID_REQUEST"
    ERROR_SERVER = "SERVER_ERROR"
    ERROR_TIMEOUT = "TIMEOUT"
    ERROR_CONNECTION = "CONNECTION_ERROR"
    ERROR_MODEL = "MODEL_ERROR"
    ERROR_MAX_ROUNDS = "ERROR_MAX_ROUNDS"
    ERROR_CONTENT_FILTER = "CONTENT_FILTERED"
    ERROR_QUOTA = "QUOTA_EXCEEDED"
    ERROR_MAX_RETRIES = "MAX_RETRIES_EXCEEDED"
    ERROR_GENERIC = "GENERIC_ERROR"


class ReActMode(StrEnum):
    FUNCTION_CALL = "function_call"
    REACT = "react"


ERROR_PREFIX = "**ERROR**"
LENGTH_NOTIFICATION_CN = "······\n由于大模型的上下文窗口大小限制，回答已经被大模型截断。"
LENGTH_NOTIFICATION_EN = "...\nThe answer is truncated by your chosen LLM due to its limitation on context length."


class Base(ABC):
    def __init__(self, key, model_name, base_url, **kwargs):
        timeout = int(os.environ.get("LLM_TIMEOUT_SECONDS", 600))
        self.client = OpenAI(api_key=key, base_url=base_url, timeout=timeout)
        self.async_client = AsyncOpenAI(api_key=key, base_url=base_url, timeout=timeout)
        self.model_name = model_name
        # Configure retry parameters
        self.max_retries = kwargs.get("max_retries", int(os.environ.get("LLM_MAX_RETRIES", 5)))
        self.base_delay = kwargs.get("retry_interval", float(os.environ.get("LLM_BASE_DELAY", 2.0)))
        self.max_rounds = kwargs.get("max_rounds", 5)
        self.is_tools = False
        self.tools = []
        self.toolcall_sessions = {}

    def _get_delay(self):
        return self.base_delay * random.uniform(10, 150)

    def _classify_error(self, error):
        error_str = str(error).lower()

        keywords_mapping = [
            (["quota", "capacity", "credit", "billing", "balance", "欠费"], LLMErrorCode.ERROR_QUOTA),
            (["rate limit", "429", "tpm limit", "too many requests", "requests per minute"], LLMErrorCode.ERROR_RATE_LIMIT),
            (["auth", "key", "apikey", "401", "forbidden", "permission"], LLMErrorCode.ERROR_AUTHENTICATION),
            (["invalid", "bad request", "400", "format", "malformed", "parameter"], LLMErrorCode.ERROR_INVALID_REQUEST),
            (["server", "503", "502", "504", "500", "unavailable"], LLMErrorCode.ERROR_SERVER),
            (["timeout", "timed out"], LLMErrorCode.ERROR_TIMEOUT),
            (["connect", "network", "unreachable", "dns"], LLMErrorCode.ERROR_CONNECTION),
            (["filter", "content", "policy", "blocked", "safety", "inappropriate"], LLMErrorCode.ERROR_CONTENT_FILTER),
            (["model", "not found", "does not exist", "not available"], LLMErrorCode.ERROR_MODEL),
            (["max rounds"], LLMErrorCode.ERROR_MODEL),
        ]
        for words, code in keywords_mapping:
            if re.search("({})".format("|".join(words)), error_str):
                # LINEAJE: runtime guardrail checks `code` as it flows from the agent to the user interface, before it leaves the application (in Base._classify_error).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `code` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:6b3b175252654ef417500e87df3239bca13e4a390b55fc6e7d8fbc79936752be'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6b3b175252654ef417500e87df3239bca13e4a390b55fc6e7d8fbc79936752be', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 98, 'function': 'Base._classify_error'}, 'file': 'rag/llm/chat_model.py', 'line': 98, 'function': '_classify_error', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    code = _gr_client.enforce(_gr_site, code, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return code

        return LLMErrorCode.ERROR_GENERIC

    def _clean_conf(self, gen_conf):
        if "max_tokens" in gen_conf:
            del gen_conf["max_tokens"]

        allowed_conf = {
            "temperature",
            "max_completion_tokens",
            "top_p",
            "stream",
            "stream_options",
            "stop",
            "n",
            "presence_penalty",
            "frequency_penalty",
            "functions",
            "function_call",
            "logit_bias",
            "user",
            "response_format",
            "seed",
            "tools",
            "tool_choice",
            "logprobs",
            "top_logprobs",
            "extra_headers",
        }

        gen_conf = {k: v for k, v in gen_conf.items() if k in allowed_conf}

        model_name_lower = (self.model_name or "").lower()
        # gpt-5 and gpt-5.1 endpoints have inconsistent parameter support, clear custom generation params to prevent unexpected issues
        if "gpt-5" in model_name_lower:
            gen_conf = {}

        # LINEAJE: runtime guardrail checks `gen_conf` as it flows from the agent to the user interface, before it leaves the application (in Base._clean_conf).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `gen_conf` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:bad17b86e0992a1aea2d2320f5108d9f0732b710431a417ddffaa3c072df569a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bad17b86e0992a1aea2d2320f5108d9f0732b710431a417ddffaa3c072df569a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 136, 'function': 'Base._clean_conf'}, 'file': 'rag/llm/chat_model.py', 'line': 136, 'function': '_clean_conf', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            gen_conf = _gr_client.enforce(_gr_site, gen_conf, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return gen_conf

    async def _async_chat_streamly(self, history, gen_conf, **kwargs):
        # LINEAJE: runtime guardrail checks `history` as it flows from the agent to an external endpoint, before it leaves the application (in Base._async_chat_streamly).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `history` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9aaeabce6bbc8afb44afe43a83611ee234258de3e8d4d5777eff4b26b68ce618'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9aaeabce6bbc8afb44afe43a83611ee234258de3e8d4d5777eff4b26b68ce618', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 139, 'function': 'Base._async_chat_streamly'}, 'file': 'rag/llm/chat_model.py', 'line': 139, 'function': '_async_chat_streamly', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            history = _gr_client.enforce(_gr_site, history, content_type='application/json', variable_name='history', source_file=__file__, before_line=139)
        except _gr_client.GuardrailUnavailableError:
            pass
        _lineaje_payload = "[HISTORY STREAMLY]" + json.dumps(history, ensure_ascii=False, indent=4)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base._async_chat_streamly).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:59c2fdf4e659c76e3ac98f2a149119df00d34ee83efa4781647417f3fc0829c9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:59c2fdf4e659c76e3ac98f2a149119df00d34ee83efa4781647417f3fc0829c9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 139, 'function': 'Base._async_chat_streamly'}, 'file': 'rag/llm/chat_model.py', 'line': 139, 'function': '_async_chat_streamly', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        reasoning_start = False

        request_kwargs = {"model": self.model_name, "messages": history, "stream": True, **gen_conf}
        stop = kwargs.get("stop")
        if stop:
            request_kwargs["stop"] = stop

        # LINEAJE: runtime guardrail checks `request_kwargs` as it flows from the agent to the LLM, before it is sent to the model (in Base._async_chat_streamly).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `request_kwargs` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:674c30466f092d04bf4ad112fc263c9f1ac3e102ffefe99574e9384d57c67fb0'
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:674c30466f092d04bf4ad112fc263c9f1ac3e102ffefe99574e9384d57c67fb0', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-5', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@5', 'version': '5'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'Base._async_chat_streamly', 'line': 147}, 'file': 'rag/llm/chat_model.py', 'line': 147, 'function': '_async_chat_streamly', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:34df8f5e64893c7a'}, interaction_id=_lineaje_interaction_id)
        try:
            if not hasattr(_gr_client, 'enforce_request'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_request (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_request")
            request_kwargs = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_request(_gr_site, request_kwargs, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        response = await self.async_client.chat.completions.create(**request_kwargs)
        # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in Base._async_chat_streamly).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:fae0698771fc1e4470672809538caaee348860a8e48d8fa9988bf82f175a4795'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fae0698771fc1e4470672809538caaee348860a8e48d8fa9988bf82f175a4795', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-5', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@5', 'version': '5'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'Base._async_chat_streamly', 'line': 147}, 'file': 'rag/llm/chat_model.py', 'line': 147, 'function': '_async_chat_streamly', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:34df8f5e64893c7a'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            if not hasattr(_gr_client, 'enforce_reply'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
            response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        async for resp in response:
            if not resp.choices:
                continue
            if not resp.choices[0].delta.content:
                resp.choices[0].delta.content = ""
            if kwargs.get("with_reasoning", True) and hasattr(resp.choices[0].delta, "reasoning_content") and resp.choices[0].delta.reasoning_content:
                ans = ""
                if not reasoning_start:
                    reasoning_start = True
                    ans = "<think>"
                ans += resp.choices[0].delta.reasoning_content + "</think>"
            else:
                reasoning_start = False
                ans = resp.choices[0].delta.content
            tol = total_token_count_from_response(resp)
            if not tol:
                tol = num_tokens_from_string(resp.choices[0].delta.content)

            finish_reason = resp.choices[0].finish_reason if hasattr(resp.choices[0], "finish_reason") else ""
            if finish_reason == "length":
                if is_chinese(ans):
                    ans += LENGTH_NOTIFICATION_CN
                else:
                    ans += LENGTH_NOTIFICATION_EN
            yield ans, tol

    async def async_chat_streamly(self, system, history, gen_conf: dict = {}, **kwargs):
        if system and history and history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": system})
        gen_conf = self._clean_conf(gen_conf)
        ans = ""
        total_tokens = 0

        for attempt in range(self.max_retries + 1):
            try:
                async for delta_ans, tol in self._async_chat_streamly(history, gen_conf, **kwargs):
                    ans = delta_ans
                    total_tokens += tol
                    yield ans

                yield total_tokens
                return
            except Exception as e:
                e = await self._exceptions_async(e, attempt)
                if e:
                    yield e
                    yield total_tokens
                    return

    def _length_stop(self, ans):
        if is_chinese([ans]):
            return ans + LENGTH_NOTIFICATION_CN
        return ans + LENGTH_NOTIFICATION_EN

    @property
    def _retryable_errors(self) -> set[str]:
        return {
            LLMErrorCode.ERROR_RATE_LIMIT,
            LLMErrorCode.ERROR_SERVER,
        }

    def _should_retry(self, error_code: str) -> bool:
        return error_code in self._retryable_errors

    def _exceptions(self, e, attempt) -> str | None:
        _lineaje_payload = "OpenAI chat_with_tools"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base._exceptions).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a723700eb895b26b18528c84c11542832c6ddb26f59f78184a5809120ddb6e61'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a723700eb895b26b18528c84c11542832c6ddb26f59f78184a5809120ddb6e61', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 213, 'function': 'Base._exceptions'}, 'file': 'rag/llm/chat_model.py', 'line': 213, 'function': '_exceptions', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.exception(_lineaje_payload)
        # Classify the error
        error_code = self._classify_error(e)
        if attempt == self.max_retries:
            error_code = LLMErrorCode.ERROR_MAX_RETRIES

        if self._should_retry(error_code):
            delay = self._get_delay()
            _lineaje_payload = f"Error: {error_code}. Retrying in {delay:.2f} seconds... (Attempt {attempt + 1}/{self.max_retries})"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base._exceptions).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:a1d626e8939fc3d2e61d1fb919e4757713186dc8321dba91d2ffe430b8da7309'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a1d626e8939fc3d2e61d1fb919e4757713186dc8321dba91d2ffe430b8da7309', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 221, 'function': 'Base._exceptions'}, 'file': 'rag/llm/chat_model.py', 'line': 221, 'function': '_exceptions', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            time.sleep(delay)
            return None

        msg = f"{ERROR_PREFIX}: {error_code} - {str(e)}"
        _lineaje_payload = f"sync base giving up: {msg}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base._exceptions).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:80483618813c7aabd199990a216238c5f8b3ec30629df438b9302ef872b5316b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:80483618813c7aabd199990a216238c5f8b3ec30629df438b9302ef872b5316b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 226, 'function': 'Base._exceptions'}, 'file': 'rag/llm/chat_model.py', 'line': 226, 'function': '_exceptions', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `msg` as it flows from the agent to the user interface, before it leaves the application (in Base._exceptions).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6a6a8f701632012d9f5a64c8df3d7ed4409f03704ee13f4815ca6e4c9f64a7a0'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6a6a8f701632012d9f5a64c8df3d7ed4409f03704ee13f4815ca6e4c9f64a7a0', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 227, 'function': 'Base._exceptions'}, 'file': 'rag/llm/chat_model.py', 'line': 227, 'function': '_exceptions', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            msg = _gr_client.enforce(_gr_site, msg, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return msg

    async def _exceptions_async(self, e, attempt):
        _lineaje_payload = "OpenAI async completion"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base._exceptions_async).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:38f60e014e843dd8f5f2ef5793b17e6a3990581cef1d5bf8685c7e73b51ce47f'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:38f60e014e843dd8f5f2ef5793b17e6a3990581cef1d5bf8685c7e73b51ce47f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 230, 'function': 'Base._exceptions_async'}, 'file': 'rag/llm/chat_model.py', 'line': 230, 'function': '_exceptions_async', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.exception(_lineaje_payload)
        error_code = self._classify_error(e)
        if attempt == self.max_retries:
            error_code = LLMErrorCode.ERROR_MAX_RETRIES

        if self._should_retry(error_code):
            delay = self._get_delay()
            _lineaje_payload = f"Error: {error_code}. Retrying in {delay:.2f} seconds... (Attempt {attempt + 1}/{self.max_retries})"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base._exceptions_async).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:a25e429c807d383e1d914792a30ac71b3a059faccbfd30cce7b0ae08c9e4d301'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a25e429c807d383e1d914792a30ac71b3a059faccbfd30cce7b0ae08c9e4d301', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 237, 'function': 'Base._exceptions_async'}, 'file': 'rag/llm/chat_model.py', 'line': 237, 'function': '_exceptions_async', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            await asyncio.sleep(delay)
            return None

        msg = f"{ERROR_PREFIX}: {error_code} - {str(e)}"
        _lineaje_payload = f"async base giving up: {msg}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base._exceptions_async).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9319481629976b22300b6419ce5cb42f786144c1b2736a70266a28ca844da8d5'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9319481629976b22300b6419ce5cb42f786144c1b2736a70266a28ca844da8d5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 242, 'function': 'Base._exceptions_async'}, 'file': 'rag/llm/chat_model.py', 'line': 242, 'function': '_exceptions_async', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `msg` as it flows from the agent to the user interface, before it leaves the application (in Base._exceptions_async).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9ac8ba177a10b3fe429431cc6a122760506c661833ea39659bc6faf66a7ce858'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9ac8ba177a10b3fe429431cc6a122760506c661833ea39659bc6faf66a7ce858', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 243, 'function': 'Base._exceptions_async'}, 'file': 'rag/llm/chat_model.py', 'line': 243, 'function': '_exceptions_async', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            msg = _gr_client.enforce(_gr_site, msg, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return msg

    def _verbose_tool_use(self, name, args, res):
        _lineaje_payload = {"name": name, "args": args, "result": res}
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to an external endpoint, before it leaves the application (in Base._verbose_tool_use).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `_lineaje_payload` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:73183336b0e5a70afa3ec269c7fbf0ffd4d9ce8a5c0741e78205d4cb4bf1e288'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:73183336b0e5a70afa3ec269c7fbf0ffd4d9ce8a5c0741e78205d4cb4bf1e288', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 246, 'function': 'Base._verbose_tool_use'}, 'file': 'rag/llm/chat_model.py', 'line': 246, 'function': '_verbose_tool_use', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=246)
        except _gr_client.GuardrailUnavailableError:
            pass
        return "<tool_call>" + json.dumps(_lineaje_payload, ensure_ascii=False, indent=2) + "</tool_call>"

    def _append_history(self, hist, tool_call, tool_res):
        hist.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "index": tool_call.index,
                        "id": tool_call.id,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                        "type": "function",
                    },
                ],
            }
        )
        try:
            if isinstance(tool_res, dict):
                # LINEAJE: runtime guardrail checks `tool_res` as it flows from the agent to an external endpoint, before it leaves the application (in Base._append_history).
                #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `tool_res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:b379625df761f31e5c74fff0452bba49c35d86d58a672a308d8975536b7ea6be'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b379625df761f31e5c74fff0452bba49c35d86d58a672a308d8975536b7ea6be', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 267, 'function': 'Base._append_history'}, 'file': 'rag/llm/chat_model.py', 'line': 267, 'function': '_append_history', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    tool_res = _gr_client.enforce(_gr_site, tool_res, content_type='application/json', variable_name='tool_res', source_file=__file__, before_line=267)
                except _gr_client.GuardrailUnavailableError:
                    pass
                tool_res = json.dumps(tool_res, ensure_ascii=False)
        finally:
            hist.append({"role": "tool", "tool_call_id": tool_call.id, "content": str(tool_res)})
        # LINEAJE: runtime guardrail checks `hist` as it flows from the agent to the user interface, before it leaves the application (in Base._append_history).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `hist` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1cfdd1572ecbe24d428c7da0400bb6e5399c84c65177de5f552b2835e23dc2de'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1cfdd1572ecbe24d428c7da0400bb6e5399c84c65177de5f552b2835e23dc2de', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 270, 'function': 'Base._append_history'}, 'file': 'rag/llm/chat_model.py', 'line': 270, 'function': '_append_history', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            hist = _gr_client.enforce(_gr_site, hist, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return hist

    def bind_tools(self, toolcall_session, tools):
        if not (toolcall_session and tools):
            return
        self.is_tools = True
        self.toolcall_session = toolcall_session
        self.tools = tools

    async def async_chat_with_tools(self, system: str, history: list, gen_conf: dict = {}):
        gen_conf = self._clean_conf(gen_conf)
        if system and history and history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": system})

        ans = ""
        tk_count = 0
        hist = deepcopy(history)
        for attempt in range(self.max_retries + 1):
            history = deepcopy(hist)
            try:
                for _ in range(self.max_rounds + 1):
                    _lineaje_payload = f"{self.tools=}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base.async_chat_with_tools).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:9646bd2923b290b5ad44b567849d5fc306e8a09341adc99bf5396be8ac1b5a6c'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9646bd2923b290b5ad44b567849d5fc306e8a09341adc99bf5396be8ac1b5a6c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 291, 'function': 'Base.async_chat_with_tools'}, 'file': 'rag/llm/chat_model.py', 'line': 291, 'function': 'async_chat_with_tools', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)
                    # LINEAJE: runtime guardrail checks `history` as it flows from the agent to the LLM, before it is sent to the model (in Base.async_chat_with_tools).
                    #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `history` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:b1068243910710a55e0e16613cf34058d2f0f81f8a9a78b95652fbf74bc56060'
                    _lineaje_history_evidence = {'history': history, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
                    _gr_client = _lineaje_load_gr_client()
                    _lineaje_interaction_id = _gr_client.new_interaction_id()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b1068243910710a55e0e16613cf34058d2f0f81f8a9a78b95652fbf74bc56060', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-5', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@5', 'version': '5'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'Base.async_chat_with_tools', 'line': 292}, 'file': 'rag/llm/chat_model.py', 'line': 292, 'function': 'async_chat_with_tools', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:4841fccbb4fb0374'}, interaction_id=_lineaje_interaction_id)
                    try:
                        _lineaje_history_evidence = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_history_evidence, content_type='application/json'))
                        history = _lineaje_history_evidence.get('history', history) if isinstance(_lineaje_history_evidence, dict) else history
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        raise
                    response = await self.async_client.chat.completions.create(model=self.model_name, messages=history, tools=self.tools, tool_choice="auto", **gen_conf)
                    # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in Base.async_chat_with_tools).
                    #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:07dc4f0dd16d26dea45decc86535fef844e6255e2adc49659cfd11a486da5538'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:07dc4f0dd16d26dea45decc86535fef844e6255e2adc49659cfd11a486da5538', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-5', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@5', 'version': '5'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'Base.async_chat_with_tools', 'line': 292}, 'file': 'rag/llm/chat_model.py', 'line': 292, 'function': 'async_chat_with_tools', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:4841fccbb4fb0374'}, interaction_id=locals().get('_lineaje_interaction_id'))
                    try:
                        if not hasattr(_gr_client, 'enforce_reply'):
                            __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                            raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                        response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    tk_count += total_token_count_from_response(response)
                    if any([not response.choices, not response.choices[0].message]):
                        raise Exception(f"500 response structure error. Response: {response}")

                    if not hasattr(response.choices[0].message, "tool_calls") or not response.choices[0].message.tool_calls:
                        if hasattr(response.choices[0].message, "reasoning_content") and response.choices[0].message.reasoning_content:
                            ans += "<think>" + response.choices[0].message.reasoning_content + "</think>"

                        ans += response.choices[0].message.content
                        if response.choices[0].finish_reason == "length":
                            ans = self._length_stop(ans)

                        return ans, tk_count

                    for tool_call in response.choices[0].message.tool_calls:
                        _lineaje_payload = f"Response {tool_call=}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base.async_chat_with_tools).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:bec4a5c253a63468c03254276241f38a3af0f353cf41404e84fd110afe80c3ab'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bec4a5c253a63468c03254276241f38a3af0f353cf41404e84fd110afe80c3ab', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 308, 'function': 'Base.async_chat_with_tools'}, 'file': 'rag/llm/chat_model.py', 'line': 308, 'function': 'async_chat_with_tools', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.info(_lineaje_payload)
                        name = tool_call.function.name
                        try:
                            args = json_repair.loads(tool_call.function.arguments)
                            tool_response = await asyncio.to_thread(self.toolcall_session.tool_call, name, args)
                            history = self._append_history(history, tool_call, tool_response)
                            ans += self._verbose_tool_use(name, args, tool_response)
                        except Exception as e:
                            logging.exception(msg=f"Wrong JSON argument format in LLM tool call response: {tool_call}")
                            history.append({"role": "tool", "tool_call_id": tool_call.id, "content": f"Tool call error: \n{tool_call}\nException:\n" + str(e)})
                            ans += self._verbose_tool_use(name, {}, str(e))

                _lineaje_payload = f"Exceed max rounds: {self.max_rounds}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base.async_chat_with_tools).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:d66c2c63a753aae5e920ff26df8d0546ef6781475c1f76e4761fca70c39c404f'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d66c2c63a753aae5e920ff26df8d0546ef6781475c1f76e4761fca70c39c404f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 320, 'function': 'Base.async_chat_with_tools'}, 'file': 'rag/llm/chat_model.py', 'line': 320, 'function': 'async_chat_with_tools', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                history.append({"role": "user", "content": f"Exceed max rounds: {self.max_rounds}"})
                response, token_count = await self._async_chat(history, gen_conf)
                ans += response
                tk_count += token_count
                return ans, tk_count
            except Exception as e:
                e = await self._exceptions_async(e, attempt)
                if e:
                    return e, tk_count

        assert False, "Shouldn't be here."

    async def async_chat_streamly_with_tools(self, system: str, history: list, gen_conf: dict = {}):
        gen_conf = self._clean_conf(gen_conf)
        tools = self.tools
        if system and history and history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": system})

        total_tokens = 0
        hist = deepcopy(history)

        for attempt in range(self.max_retries + 1):
            history = deepcopy(hist)
            try:
                for _ in range(self.max_rounds + 1):
                    reasoning_start = False
                    _lineaje_payload = f"{tools=}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base.async_chat_streamly_with_tools).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:7b5e80c67ccee651d9482573870b2797c73dac77a0440de2fc14c530be0bee1a'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7b5e80c67ccee651d9482573870b2797c73dac77a0440de2fc14c530be0bee1a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 347, 'function': 'Base.async_chat_streamly_with_tools'}, 'file': 'rag/llm/chat_model.py', 'line': 347, 'function': 'async_chat_streamly_with_tools', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)

                    # LINEAJE: runtime guardrail checks `history` as it flows from the agent to the LLM, before it is sent to the model (in Base.async_chat_streamly_with_tools).
                    #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `history` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:2914309b0ea9ea69a127149c6429d6d138257a2e10a3362164e75fcd307187c1'
                    _lineaje_history_evidence = {'history': history, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
                    _gr_client = _lineaje_load_gr_client()
                    _lineaje_interaction_id = _gr_client.new_interaction_id()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2914309b0ea9ea69a127149c6429d6d138257a2e10a3362164e75fcd307187c1', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-5', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@5', 'version': '5'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'Base.async_chat_streamly_with_tools', 'line': 349}, 'file': 'rag/llm/chat_model.py', 'line': 349, 'function': 'async_chat_streamly_with_tools', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:b52aba2448c62065'}, interaction_id=_lineaje_interaction_id)
                    try:
                        _lineaje_history_evidence = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_history_evidence, content_type='application/json'))
                        history = _lineaje_history_evidence.get('history', history) if isinstance(_lineaje_history_evidence, dict) else history
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        raise
                    response = await self.async_client.chat.completions.create(model=self.model_name, messages=history, stream=True, tools=tools, tool_choice="auto", **gen_conf)
                    # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in Base.async_chat_streamly_with_tools).
                    #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:caca05b2a52c36551b637b9f51e33075cd40d68744b90548228f2e8b3192f517'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:caca05b2a52c36551b637b9f51e33075cd40d68744b90548228f2e8b3192f517', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-5', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@5', 'version': '5'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'Base.async_chat_streamly_with_tools', 'line': 349}, 'file': 'rag/llm/chat_model.py', 'line': 349, 'function': 'async_chat_streamly_with_tools', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:b52aba2448c62065'}, interaction_id=locals().get('_lineaje_interaction_id'))
                    try:
                        if not hasattr(_gr_client, 'enforce_reply'):
                            __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                            raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                        response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass

                    final_tool_calls = {}
                    answer = ""

                    async for resp in response:
                        if not hasattr(resp, "choices") or not resp.choices:
                            continue

                        delta = resp.choices[0].delta

                        if hasattr(delta, "tool_calls") and delta.tool_calls:
                            for tool_call in delta.tool_calls:
                                index = tool_call.index
                                if index not in final_tool_calls:
                                    if not tool_call.function.arguments:
                                        tool_call.function.arguments = ""
                                    final_tool_calls[index] = tool_call
                                else:
                                    final_tool_calls[index].function.arguments += tool_call.function.arguments or ""
                            continue

                        if not hasattr(delta, "content") or delta.content is None:
                            delta.content = ""

                        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                            ans = ""
                            if not reasoning_start:
                                reasoning_start = True
                                ans = "<think>"
                            ans += delta.reasoning_content + "</think>"
                            yield ans
                        else:
                            reasoning_start = False
                            answer += delta.content
                            yield delta.content

                        tol = total_token_count_from_response(resp)
                        if not tol:
                            total_tokens += num_tokens_from_string(delta.content)
                        else:
                            total_tokens = tol

                        finish_reason = getattr(resp.choices[0], "finish_reason", "")
                        if finish_reason == "length":
                            yield self._length_stop("")

                    if answer:
                        yield total_tokens
                        return

                    for tool_call in final_tool_calls.values():
                        name = tool_call.function.name
                        try:
                            args = json_repair.loads(tool_call.function.arguments)
                            yield self._verbose_tool_use(name, args, "Begin to call...")
                            tool_response = await asyncio.to_thread(self.toolcall_session.tool_call, name, args)
                            history = self._append_history(history, tool_call, tool_response)
                            yield self._verbose_tool_use(name, args, tool_response)
                        except Exception as e:
                            logging.exception(msg=f"Wrong JSON argument format in LLM tool call response: {tool_call}")
                            history.append({"role": "tool", "tool_call_id": tool_call.id, "content": f"Tool call error: \n{tool_call}\nException:\n" + str(e)})
                            yield self._verbose_tool_use(name, {}, str(e))

                _lineaje_payload = f"Exceed max rounds: {self.max_rounds}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base.async_chat_streamly_with_tools).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a3a79641c5808586a6a191ce4266d0a0c7eba434b8437584dd73b91a37b4dfc8'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a3a79641c5808586a6a191ce4266d0a0c7eba434b8437584dd73b91a37b4dfc8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 413, 'function': 'Base.async_chat_streamly_with_tools'}, 'file': 'rag/llm/chat_model.py', 'line': 413, 'function': 'async_chat_streamly_with_tools', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                history.append({"role": "user", "content": f"Exceed max rounds: {self.max_rounds}"})

                # LINEAJE: runtime guardrail checks `history` as it flows from the agent to the LLM, before it is sent to the model (in Base.async_chat_streamly_with_tools).
                #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `history` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f4c4435136bd0f968d31d7f3cf3d81cc22395ef4cc7d36af09d43f2ade67b1ca'
                _lineaje_history_evidence = {'history': history, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
                _gr_client = _lineaje_load_gr_client()
                _lineaje_interaction_id = _gr_client.new_interaction_id()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f4c4435136bd0f968d31d7f3cf3d81cc22395ef4cc7d36af09d43f2ade67b1ca', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-5', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@5', 'version': '5'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'Base.async_chat_streamly_with_tools', 'line': 416}, 'file': 'rag/llm/chat_model.py', 'line': 416, 'function': 'async_chat_streamly_with_tools', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:8dcf652d6da3f98b'}, interaction_id=_lineaje_interaction_id)
                try:
                    _lineaje_history_evidence = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_history_evidence, content_type='application/json'))
                    history = _lineaje_history_evidence.get('history', history) if isinstance(_lineaje_history_evidence, dict) else history
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    raise
                response = await self.async_client.chat.completions.create(model=self.model_name, messages=history, stream=True, tools=tools, tool_choice="auto", **gen_conf)
                # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in Base.async_chat_streamly_with_tools).
                #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:9af86d7f4fc1fd8513738fe681431e31e0f3b4640bdc024893e89b0dd5aa9f8c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9af86d7f4fc1fd8513738fe681431e31e0f3b4640bdc024893e89b0dd5aa9f8c', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'gpt-5', 'provider': 'openai', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'GPT', 'purl': 'pkg:aimodel/GPT@5', 'version': '5'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'Base.async_chat_streamly_with_tools', 'line': 416}, 'file': 'rag/llm/chat_model.py', 'line': 416, 'function': 'async_chat_streamly_with_tools', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:8dcf652d6da3f98b'}, interaction_id=locals().get('_lineaje_interaction_id'))
                try:
                    if not hasattr(_gr_client, 'enforce_reply'):
                        __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                        raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                    response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass

                async for resp in response:
                    if not hasattr(resp, "choices") or not resp.choices:
                        continue
                    delta = resp.choices[0].delta
                    if not hasattr(delta, "content") or delta.content is None:
                        continue
                    tol = total_token_count_from_response(resp)
                    if not tol:
                        total_tokens += num_tokens_from_string(delta.content)
                    else:
                        total_tokens = tol
                    yield delta.content

                yield total_tokens
                return

            except Exception as e:
                e = await self._exceptions_async(e, attempt)
                if e:
                    _lineaje_payload = f"async_chat_streamly failed: {e}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base.async_chat_streamly_with_tools).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:aacdcf5be10ac96016a32d4c0007c72d877deb418244ff99081aa9896b404a8a'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:aacdcf5be10ac96016a32d4c0007c72d877deb418244ff99081aa9896b404a8a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 437, 'function': 'Base.async_chat_streamly_with_tools'}, 'file': 'rag/llm/chat_model.py', 'line': 437, 'function': 'async_chat_streamly_with_tools', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.error(_lineaje_payload)
                    yield e
                    yield total_tokens
                    return

        assert False, "Shouldn't be here."

    async def _async_chat(self, history, gen_conf, **kwargs):
        # LINEAJE: runtime guardrail checks `history` as it flows from the agent to an external endpoint, before it leaves the application (in Base._async_chat).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `history` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:cc3eff061175b9686bd55f719268d8669e14977b4f5e5ce656ed909a78d1ca88'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cc3eff061175b9686bd55f719268d8669e14977b4f5e5ce656ed909a78d1ca88', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 445, 'function': 'Base._async_chat'}, 'file': 'rag/llm/chat_model.py', 'line': 445, 'function': '_async_chat', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            history = _gr_client.enforce(_gr_site, history, content_type='application/json', variable_name='history', source_file=__file__, before_line=445)
        except _gr_client.GuardrailUnavailableError:
            pass
        _lineaje_payload = "[HISTORY]" + json.dumps(history, ensure_ascii=False, indent=2)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base._async_chat).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:42cb18d49ec987b7ff482b52b809002d4ab87b9d99b2df3f63c0f3a4730509b2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:42cb18d49ec987b7ff482b52b809002d4ab87b9d99b2df3f63c0f3a4730509b2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 445, 'function': 'Base._async_chat'}, 'file': 'rag/llm/chat_model.py', 'line': 445, 'function': '_async_chat', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        if self.model_name.lower().find("qwq") >= 0:
            _lineaje_payload = f"[INFO] {self.model_name} detected as reasoning model, using async_chat_streamly"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Base._async_chat).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:91525152d2c027cda9c5b3c632207338ea25c3be20001c6789146012a59da5a1'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:91525152d2c027cda9c5b3c632207338ea25c3be20001c6789146012a59da5a1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 447, 'function': 'Base._async_chat'}, 'file': 'rag/llm/chat_model.py', 'line': 447, 'function': '_async_chat', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)

            final_ans = ""
            tol_token = 0
            async for delta, tol in self._async_chat_streamly(history, gen_conf, with_reasoning=False, **kwargs):
                if delta.startswith("<think>") or delta.endswith("</think>"):
                    continue
                final_ans += delta
                tol_token = tol

            if len(final_ans.strip()) == 0:
                final_ans = "**ERROR**: Empty response from reasoning model"

            return final_ans.strip(), tol_token

        if self.model_name.lower().find("qwen3") >= 0:
            kwargs["extra_body"] = {"enable_thinking": False}

        # LINEAJE: runtime guardrail checks `history` as it flows from the agent to the LLM, before it is sent to the model (in Base._async_chat).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `history` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d2ec8471abb5cba008b4024ca3ecc523851c8917547ad29e91d4e1d99059dc7c'
        _lineaje_history_evidence = {'history': history, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d2ec8471abb5cba008b4024ca3ecc523851c8917547ad29e91d4e1d99059dc7c', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'qwen3', 'provider': 'alibaba', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Qwen', 'purl': 'pkg:aimodel/Qwen@3', 'version': '3'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'Base._async_chat', 'line': 465}, 'file': 'rag/llm/chat_model.py', 'line': 465, 'function': '_async_chat', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:b9f1394f4040b866'}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje_history_evidence = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_history_evidence, content_type='application/json'))
            history = _lineaje_history_evidence.get('history', history) if isinstance(_lineaje_history_evidence, dict) else history
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        response = await self.async_client.chat.completions.create(model=self.model_name, messages=history, **gen_conf, **kwargs)
        # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in Base._async_chat).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3a6851a4823370ff04dba9ae14c3ebdf13b9c74f347cb66bdd72dd94347d268d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3a6851a4823370ff04dba9ae14c3ebdf13b9c74f347cb66bdd72dd94347d268d', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'qwen3', 'provider': 'alibaba', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Qwen', 'purl': 'pkg:aimodel/Qwen@3', 'version': '3'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'Base._async_chat', 'line': 465}, 'file': 'rag/llm/chat_model.py', 'line': 465, 'function': '_async_chat', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:b9f1394f4040b866'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            if not hasattr(_gr_client, 'enforce_reply'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
            response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass

        if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
            return "", 0
        ans = response.choices[0].message.content.strip()
        # LINEAJE: runtime guardrail checks `ans` as it flows from the LLM to the agent, after the model replies (in Base._async_chat).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `ans` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:37b57d53029a815d4b3b3a5d424a4e2004845a7f37ecc31bec90da398de84933'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:37b57d53029a815d4b3b3a5d424a4e2004845a7f37ecc31bec90da398de84933', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'qwen3', 'version': '', 'provider': 'alibaba'}, 'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}, 'destination': {'entity_type': 'aimodel', 'name': 'Qwen', 'version': '3', 'purl': 'pkg:aimodel/Qwen@3'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 469, 'function': 'Base._async_chat'}, 'file': 'rag/llm/chat_model.py', 'line': 469, 'function': '_async_chat', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            ans = _gr_client.enforce(_gr_site, ans, content_type='application/json', variable_name='ans', source_file=__file__, before_line=469)
        except _gr_client.GuardrailUnavailableError:
            pass
        if response.choices[0].finish_reason == "length":
            ans = self._length_stop(ans)
        return ans, total_token_count_from_response(response)

    async def async_chat(self, system, history, gen_conf={}, **kwargs):
        if system and history and history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": system})
        gen_conf = self._clean_conf(gen_conf)

        for attempt in range(self.max_retries + 1):
            try:
                return await self._async_chat(history, gen_conf, **kwargs)
            except Exception as e:
                e = await self._exceptions_async(e, attempt)
                if e:
                    return e, 0
        assert False, "Shouldn't be here."


class XinferenceChat(Base):
    _FACTORY_NAME = "Xinference"

    def __init__(self, key=None, model_name="", base_url="", **kwargs):
        if not base_url:
            raise ValueError("Local llm url cannot be None")
        base_url = urljoin(base_url, "v1")
        super().__init__(key, model_name, base_url, **kwargs)


class HuggingFaceChat(Base):
    _FACTORY_NAME = "HuggingFace"

    def __init__(self, key=None, model_name="", base_url="", **kwargs):
        if not base_url:
            raise ValueError("Local llm url cannot be None")
        base_url = urljoin(base_url, "v1")
        super().__init__(key, model_name.split("___")[0], base_url, **kwargs)


class ModelScopeChat(Base):
    _FACTORY_NAME = "ModelScope"

    def __init__(self, key=None, model_name="", base_url="", **kwargs):
        if not base_url:
            raise ValueError("Local llm url cannot be None")
        base_url = urljoin(base_url, "v1")
        super().__init__(key, model_name.split("___")[0], base_url, **kwargs)


class BaiChuanChat(Base):
    _FACTORY_NAME = "BaiChuan"

    def __init__(self, key, model_name="Baichuan3-Turbo", base_url="https://api.baichuan-ai.com/v1", **kwargs):
        if not base_url:
            base_url = "https://api.baichuan-ai.com/v1"
        super().__init__(key, model_name, base_url, **kwargs)

    @staticmethod
    def _format_params(params):
        return {
            "temperature": params.get("temperature", 0.3),
            "top_p": params.get("top_p", 0.85),
        }

    def _clean_conf(self, gen_conf):
        return {
            "temperature": gen_conf.get("temperature", 0.3),
            "top_p": gen_conf.get("top_p", 0.85),
        }

    def _chat(self, history, gen_conf={}, **kwargs):
        # LINEAJE: runtime guardrail checks `history` as it flows from the agent to the LLM, before it is sent to the model (in BaiChuanChat._chat).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `history` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:0cb970f2b5abb7b76c6e32a0476dce7e9c1714a4b888d970afd485f002b85f24'
        _lineaje_history_evidence = {'history': history, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0cb970f2b5abb7b76c6e32a0476dce7e9c1714a4b888d970afd485f002b85f24', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'BaiChuanChat._chat', 'line': 541}, 'file': 'rag/llm/chat_model.py', 'line': 541, 'function': '_chat', 'agent_name': 'BaiChuanChat', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:6c84925135b059eb'}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje_history_evidence = _gr_client.enforce(_gr_site, _lineaje_history_evidence, content_type='application/json')
            history = _lineaje_history_evidence.get('history', history) if isinstance(_lineaje_history_evidence, dict) else history
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=history,
            extra_body={"tools": [{"type": "web_search", "web_search": {"enable": True, "search_mode": "performance_first"}}]},
            **gen_conf,
        )
        # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in BaiChuanChat._chat).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5e2641b2d76cb2de9439eb4e47a1d0f695536e0572d231fe612e4fc4dd02f3ee'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5e2641b2d76cb2de9439eb4e47a1d0f695536e0572d231fe612e4fc4dd02f3ee', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'BaiChuanChat._chat', 'line': 541}, 'file': 'rag/llm/chat_model.py', 'line': 541, 'function': '_chat', 'agent_name': 'BaiChuanChat', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:6c84925135b059eb'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            if not hasattr(_gr_client, 'enforce_reply'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
            response = _gr_client.enforce_reply(_gr_site, response, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        ans = response.choices[0].message.content.strip()
        if response.choices[0].finish_reason == "length":
            if is_chinese([ans]):
                ans += LENGTH_NOTIFICATION_CN
            else:
                ans += LENGTH_NOTIFICATION_EN
        return ans, total_token_count_from_response(response)

    def chat_streamly(self, system, history, gen_conf={}, **kwargs):
        if system and history and history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": system})
        if "max_tokens" in gen_conf:
            del gen_conf["max_tokens"]
        ans = ""
        total_tokens = 0
        try:
            # LINEAJE: runtime guardrail checks `history` as it flows from the agent to the LLM, before it is sent to the model (in BaiChuanChat.chat_streamly).
            #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `history` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ac08738b2915c7d45409330efe38dd997eef79353f95599299a759cd3ca33878'
            _lineaje_history_evidence = {'history': history, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _lineaje_interaction_id = _gr_client.new_interaction_id()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ac08738b2915c7d45409330efe38dd997eef79353f95599299a759cd3ca33878', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'BaiChuanChat.chat_streamly', 'line': 563}, 'file': 'rag/llm/chat_model.py', 'line': 563, 'function': 'chat_streamly', 'agent_name': 'BaiChuanChat', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:1f51ce5839fe9caa'}, interaction_id=_lineaje_interaction_id)
            try:
                _lineaje_history_evidence = _gr_client.enforce(_gr_site, _lineaje_history_evidence, content_type='application/json')
                history = _lineaje_history_evidence.get('history', history) if isinstance(_lineaje_history_evidence, dict) else history
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=history,
                extra_body={"tools": [{"type": "web_search", "web_search": {"enable": True, "search_mode": "performance_first"}}]},
                stream=True,
                **self._format_params(gen_conf),
            )
            # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in BaiChuanChat.chat_streamly).
            #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:207e99c01fb1feda9d76c7ad5e0ffd00ff96b59070b8c8755774345bdb314380'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:207e99c01fb1feda9d76c7ad5e0ffd00ff96b59070b8c8755774345bdb314380', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'BaiChuanChat.chat_streamly', 'line': 563}, 'file': 'rag/llm/chat_model.py', 'line': 563, 'function': 'chat_streamly', 'agent_name': 'BaiChuanChat', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:1f51ce5839fe9caa'}, interaction_id=locals().get('_lineaje_interaction_id'))
            try:
                if not hasattr(_gr_client, 'enforce_reply'):
                    __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                    raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                response = _gr_client.enforce_reply(_gr_site, response, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            for resp in response:
                if not resp.choices:
                    continue
                if not resp.choices[0].delta.content:
                    resp.choices[0].delta.content = ""
                ans = resp.choices[0].delta.content
                tol = total_token_count_from_response(resp)
                if not tol:
                    total_tokens += num_tokens_from_string(resp.choices[0].delta.content)
                else:
                    total_tokens = tol
                if resp.choices[0].finish_reason == "length":
                    if is_chinese([ans]):
                        ans += LENGTH_NOTIFICATION_CN
                    else:
                        ans += LENGTH_NOTIFICATION_EN
                yield ans

        except Exception as e:
            yield ans + "\n**ERROR**: " + str(e)

        yield total_tokens


class LocalAIChat(Base):
    _FACTORY_NAME = "LocalAI"

    def __init__(self, key, model_name, base_url=None, **kwargs):
        super().__init__(key, model_name, base_url=base_url, **kwargs)

        if not base_url:
            raise ValueError("Local llm url cannot be None")
        base_url = urljoin(base_url, "v1")
        self.client = OpenAI(api_key="empty", base_url=base_url)
        self.model_name = model_name.split("___")[0]


class LocalLLM(Base):
    def __init__(self, key, model_name, base_url=None, **kwargs):
        super().__init__(key, model_name, base_url=base_url, **kwargs)
        from jina import Client

        self.client = Client(port=12345, protocol="grpc", asyncio=True)

    def _prepare_prompt(self, system, history, gen_conf):
        from rag.svr.jina_server import Prompt

        if system and history and history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": system})
        return Prompt(message=history, gen_conf=gen_conf)

    def _stream_response(self, endpoint, prompt):
        from rag.svr.jina_server import Generation

        answer = ""
        try:
            res = self.client.stream_doc(on=endpoint, inputs=prompt, return_type=Generation)
            loop = asyncio.get_event_loop()
            try:
                while True:
                    answer = loop.run_until_complete(res.__anext__()).text
                    yield answer
            except StopAsyncIteration:
                pass
        except Exception as e:
            yield answer + "\n**ERROR**: " + str(e)
        yield num_tokens_from_string(answer)

    def chat(self, system, history, gen_conf={}, **kwargs):
        if "max_tokens" in gen_conf:
            del gen_conf["max_tokens"]
        prompt = self._prepare_prompt(system, history, gen_conf)
        chat_gen = self._stream_response("/chat", prompt)
        ans = next(chat_gen)
        total_tokens = next(chat_gen)
        return ans, total_tokens

    def chat_streamly(self, system, history, gen_conf={}, **kwargs):
        if "max_tokens" in gen_conf:
            del gen_conf["max_tokens"]
        prompt = self._prepare_prompt(system, history, gen_conf)
        return self._stream_response("/stream", prompt)


class VolcEngineChat(Base):
    _FACTORY_NAME = "VolcEngine"

    def __init__(self, key, model_name, base_url="https://ark.cn-beijing.volces.com/api/v3", **kwargs):
        """
        Since do not want to modify the original database fields, and the VolcEngine authentication method is quite special,
        Assemble ark_api_key, ep_id into api_key, store it as a dictionary type, and parse it for use
        model_name is for display only
        """
        base_url = base_url if base_url else "https://ark.cn-beijing.volces.com/api/v3"
        ark_api_key = json.loads(key).get("ark_api_key", "")
        model_name = json.loads(key).get("ep_id", "") + json.loads(key).get("endpoint_id", "")
        super().__init__(ark_api_key, model_name, base_url, **kwargs)


class MistralChat(Base):
    _FACTORY_NAME = "Mistral"

    def __init__(self, key, model_name, base_url=None, **kwargs):
        super().__init__(key, model_name, base_url=base_url, **kwargs)

        from mistralai.client import MistralClient

        self.client = MistralClient(api_key=key)
        self.model_name = model_name

    def _clean_conf(self, gen_conf):
        for k in list(gen_conf.keys()):
            if k not in ["temperature", "top_p", "max_tokens"]:
                del gen_conf[k]
        # LINEAJE: runtime guardrail checks `gen_conf` as it flows from the agent to the user interface, before it leaves the application (in MistralChat._clean_conf).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `gen_conf` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e9813a96412ade3b855ac65d525c3c99410b43e9a4cf4a8afddec374fb8f445c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e9813a96412ade3b855ac65d525c3c99410b43e9a4cf4a8afddec374fb8f445c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 684, 'function': 'MistralChat._clean_conf'}, 'file': 'rag/llm/chat_model.py', 'line': 684, 'function': '_clean_conf', 'agent_name': 'MistralChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            gen_conf = _gr_client.enforce(_gr_site, gen_conf, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return gen_conf

    def _chat(self, history, gen_conf={}, **kwargs):
        gen_conf = self._clean_conf(gen_conf)
        # LINEAJE: runtime guardrail checks `history` as it flows from the agent to the LLM, before it is sent to the model (in MistralChat._chat).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `history` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d30cf9560e6a5df850241fa8833c6eb1be2ff321a8a8983904cce59e82127764'
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d30cf9560e6a5df850241fa8833c6eb1be2ff321a8a8983904cce59e82127764', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'version': '', 'provider': ''}, 'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'version': '', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 688, 'function': 'MistralChat._chat'}, 'file': 'rag/llm/chat_model.py', 'line': 688, 'function': '_chat', 'agent_name': 'MistralChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True}, interaction_id=_lineaje_interaction_id)
        try:
            history = _gr_client.enforce(_gr_site, history, content_type='application/json', variable_name='history', source_file=__file__, before_line=688)
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        response = self.client.chat(model=self.model_name, messages=history, **gen_conf)
        ans = response.choices[0].message.content
        # LINEAJE: runtime guardrail checks `ans` as it flows from the LLM to the agent, after the model replies (in MistralChat._chat).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `ans` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:adb7fb79c7b6d4cb89c6df7df203e1521349f02ec8c8b4baa1f0fce3dc21b212'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:adb7fb79c7b6d4cb89c6df7df203e1521349f02ec8c8b4baa1f0fce3dc21b212', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'version': '', 'provider': ''}, 'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'version': '', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 689, 'function': 'MistralChat._chat'}, 'file': 'rag/llm/chat_model.py', 'line': 689, 'function': '_chat', 'agent_name': 'MistralChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            ans = _gr_client.enforce(_gr_site, ans, content_type='application/json', variable_name='ans', source_file=__file__, before_line=689)
        except _gr_client.GuardrailUnavailableError:
            pass
        if response.choices[0].finish_reason == "length":
            if is_chinese(ans):
                ans += LENGTH_NOTIFICATION_CN
            else:
                ans += LENGTH_NOTIFICATION_EN
        return ans, total_token_count_from_response(response)

    def chat_streamly(self, system, history, gen_conf={}, **kwargs):
        if system and history and history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": system})
        gen_conf = self._clean_conf(gen_conf)
        ans = ""
        total_tokens = 0
        try:
            response = self.client.chat_stream(model=self.model_name, messages=history, **gen_conf, **kwargs)
            for resp in response:
                if not resp.choices or not resp.choices[0].delta.content:
                    continue
                ans = resp.choices[0].delta.content
                total_tokens += 1
                if resp.choices[0].finish_reason == "length":
                    if is_chinese(ans):
                        ans += LENGTH_NOTIFICATION_CN
                    else:
                        ans += LENGTH_NOTIFICATION_EN
                yield ans

        except openai.APIError as e:
            yield ans + "\n**ERROR**: " + str(e)

        yield total_tokens


class LmStudioChat(Base):
    _FACTORY_NAME = "LM-Studio"

    def __init__(self, key, model_name, base_url, **kwargs):
        if not base_url:
            raise ValueError("Local llm url cannot be None")
        base_url = urljoin(base_url, "v1")
        super().__init__(key, model_name, base_url, **kwargs)
        self.client = OpenAI(api_key="lm-studio", base_url=base_url)
        self.model_name = model_name


class OpenAI_APIChat(Base):
    _FACTORY_NAME = ["VLLM", "OpenAI-API-Compatible"]

    def __init__(self, key, model_name, base_url, **kwargs):
        if not base_url:
            raise ValueError("url cannot be None")
        model_name = model_name.split("___")[0]
        super().__init__(key, model_name, base_url, **kwargs)


class LeptonAIChat(Base):
    _FACTORY_NAME = "LeptonAI"

    def __init__(self, key, model_name, base_url=None, **kwargs):
        if not base_url:
            base_url = urljoin("https://" + model_name + ".lepton.run", "api/v1")
        super().__init__(key, model_name, base_url, **kwargs)


class ReplicateChat(Base):
    _FACTORY_NAME = "Replicate"

    def __init__(self, key, model_name, base_url=None, **kwargs):
        super().__init__(key, model_name, base_url=base_url, **kwargs)

        from replicate.client import Client

        self.model_name = model_name
        self.client = Client(api_token=key)

    def _chat(self, history, gen_conf={}, **kwargs):
        system = history[0]["content"] if history and history[0]["role"] == "system" else ""
        prompt = "\n".join([item["role"] + ":" + item["content"] for item in history[-5:] if item["role"] != "system"])
        response = self.client.run(
            self.model_name,
            input={"system_prompt": system, "prompt": prompt, **gen_conf},
        )
        ans = "".join(response)
        return ans, num_tokens_from_string(ans)

    def chat_streamly(self, system, history, gen_conf={}, **kwargs):
        if "max_tokens" in gen_conf:
            del gen_conf["max_tokens"]
        prompt = "\n".join([item["role"] + ":" + item["content"] for item in history[-5:]])
        ans = ""
        try:
            response = self.client.run(
                self.model_name,
                input={"system_prompt": system, "prompt": prompt, **gen_conf},
            )
            for resp in response:
                ans = resp
                yield ans

        except Exception as e:
            yield ans + "\n**ERROR**: " + str(e)

        yield num_tokens_from_string(ans)


class HunyuanChat(Base):
    _FACTORY_NAME = "Tencent Hunyuan"

    def __init__(self, key, model_name, base_url=None, **kwargs):
        super().__init__(key, model_name, base_url=base_url, **kwargs)

        from tencentcloud.common import credential
        from tencentcloud.hunyuan.v20230901 import hunyuan_client

        key = json.loads(key)
        sid = key.get("hunyuan_sid", "")
        sk = key.get("hunyuan_sk", "")
        cred = credential.Credential(sid, sk)
        self.model_name = model_name
        self.client = hunyuan_client.HunyuanClient(cred, "")

    def _clean_conf(self, gen_conf):
        _gen_conf = {}
        if "temperature" in gen_conf:
            _gen_conf["Temperature"] = gen_conf["temperature"]
        if "top_p" in gen_conf:
            _gen_conf["TopP"] = gen_conf["top_p"]
        # LINEAJE: runtime guardrail checks `_gen_conf` as it flows from the agent to the user interface, before it leaves the application (in HunyuanChat._clean_conf).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `_gen_conf` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:68aae94e9d0150b135d6d466d7f64959b58d393ff8b5798bfdb301151eed27c5'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:68aae94e9d0150b135d6d466d7f64959b58d393ff8b5798bfdb301151eed27c5', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 817, 'function': 'HunyuanChat._clean_conf'}, 'file': 'rag/llm/chat_model.py', 'line': 817, 'function': '_clean_conf', 'agent_name': 'HunyuanChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _gen_conf = _gr_client.enforce(_gr_site, _gen_conf, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return _gen_conf

    def _chat(self, history, gen_conf={}, **kwargs):
        from tencentcloud.hunyuan.v20230901 import models

        hist = [{k.capitalize(): v for k, v in item.items()} for item in history]
        req = models.ChatCompletionsRequest()
        params = {"Model": self.model_name, "Messages": hist, **gen_conf}
        # LINEAJE: runtime guardrail checks `params` as it flows from the agent to an external endpoint, before it leaves the application (in HunyuanChat._chat).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `params` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:847bf3dca2d222ca793781198e57edfd0fc1c30dd930d21f6cd93d881f0de0d2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:847bf3dca2d222ca793781198e57edfd0fc1c30dd930d21f6cd93d881f0de0d2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 825, 'function': 'HunyuanChat._chat'}, 'file': 'rag/llm/chat_model.py', 'line': 825, 'function': '_chat', 'agent_name': 'HunyuanChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            params = _gr_client.enforce(_gr_site, params, content_type='application/json', variable_name='params', source_file=__file__, before_line=825)
        except _gr_client.GuardrailUnavailableError:
            pass
        req.from_json_string(json.dumps(params))
        response = self.client.ChatCompletions(req)
        ans = response.Choices[0].Message.Content
        return ans, response.Usage.TotalTokens

    def chat_streamly(self, system, history, gen_conf={}, **kwargs):
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
            TencentCloudSDKException,
        )
        from tencentcloud.hunyuan.v20230901 import models

        _gen_conf = {}
        _history = [{k.capitalize(): v for k, v in item.items()} for item in history]
        if system and history and history[0].get("role") != "system":
            _history.insert(0, {"Role": "system", "Content": system})
        if "max_tokens" in gen_conf:
            del gen_conf["max_tokens"]
        if "temperature" in gen_conf:
            _gen_conf["Temperature"] = gen_conf["temperature"]
        if "top_p" in gen_conf:
            _gen_conf["TopP"] = gen_conf["top_p"]
        req = models.ChatCompletionsRequest()
        params = {
            "Model": self.model_name,
            "Messages": _history,
            "Stream": True,
            **_gen_conf,
        }
        # LINEAJE: runtime guardrail checks `params` as it flows from the agent to an external endpoint, before it leaves the application (in HunyuanChat.chat_streamly).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `params` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:00d6621a5a9688eb5be4c5a4b96ed80d504571939b060be40b00d5ad03d2a822'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:00d6621a5a9688eb5be4c5a4b96ed80d504571939b060be40b00d5ad03d2a822', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 853, 'function': 'HunyuanChat.chat_streamly'}, 'file': 'rag/llm/chat_model.py', 'line': 853, 'function': 'chat_streamly', 'agent_name': 'HunyuanChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            params = _gr_client.enforce(_gr_site, params, content_type='application/json', variable_name='params', source_file=__file__, before_line=853)
        except _gr_client.GuardrailUnavailableError:
            pass
        req.from_json_string(json.dumps(params))
        ans = ""
        total_tokens = 0
        try:
            response = self.client.ChatCompletions(req)
            for resp in response:
                resp = json.loads(resp["data"])
                if not resp["Choices"] or not resp["Choices"][0]["Delta"]["Content"]:
                    continue
                ans = resp["Choices"][0]["Delta"]["Content"]
                total_tokens += 1

                yield ans

        except TencentCloudSDKException as e:
            yield ans + "\n**ERROR**: " + str(e)

        yield total_tokens


class SparkChat(Base):
    _FACTORY_NAME = "XunFei Spark"

    def __init__(self, key, model_name, base_url="https://spark-api-open.xf-yun.com/v1", **kwargs):
        if not base_url:
            base_url = "https://spark-api-open.xf-yun.com/v1"
        model2version = {
            "Spark-Max": "generalv3.5",
            "Spark-Lite": "general",
            "Spark-Pro": "generalv3",
            "Spark-Pro-128K": "pro-128k",
            "Spark-4.0-Ultra": "4.0Ultra",
        }
        version2model = {v: k for k, v in model2version.items()}
        assert model_name in model2version or model_name in version2model, f"The given model name is not supported yet. Support: {list(model2version.keys())}"
        if model_name in model2version:
            model_version = model2version[model_name]
        else:
            model_version = model_name
        super().__init__(key, model_version, base_url, **kwargs)


class BaiduYiyanChat(Base):
    _FACTORY_NAME = "BaiduYiyan"

    def __init__(self, key, model_name, base_url=None, **kwargs):
        super().__init__(key, model_name, base_url=base_url, **kwargs)

        import qianfan

        key = json.loads(key)
        ak = key.get("yiyan_ak", "")
        sk = key.get("yiyan_sk", "")
        self.client = qianfan.ChatCompletion(ak=ak, sk=sk)
        self.model_name = model_name.lower()

    def _clean_conf(self, gen_conf):
        gen_conf["penalty_score"] = ((gen_conf.get("presence_penalty", 0) + gen_conf.get("frequency_penalty", 0)) / 2) + 1
        if "max_tokens" in gen_conf:
            del gen_conf["max_tokens"]
        # LINEAJE: runtime guardrail checks `gen_conf` as it flows from the agent to the user interface, before it leaves the application (in BaiduYiyanChat._clean_conf).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `gen_conf` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a2d9ae00770a766d7f47bc7e7be67324c4929b3ce07b9d8b620814e189836d3e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a2d9ae00770a766d7f47bc7e7be67324c4929b3ce07b9d8b620814e189836d3e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 913, 'function': 'BaiduYiyanChat._clean_conf'}, 'file': 'rag/llm/chat_model.py', 'line': 913, 'function': '_clean_conf', 'agent_name': 'BaiduYiyanChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            gen_conf = _gr_client.enforce(_gr_site, gen_conf, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return gen_conf

    def _chat(self, history, gen_conf):
        system = history[0]["content"] if history and history[0]["role"] == "system" else ""
        response = self.client.do(model=self.model_name, messages=[h for h in history if h["role"] != "system"], system=system, **gen_conf).body
        ans = response["result"]
        return ans, total_token_count_from_response(response)

    def chat_streamly(self, system, history, gen_conf={}, **kwargs):
        gen_conf["penalty_score"] = ((gen_conf.get("presence_penalty", 0) + gen_conf.get("frequency_penalty", 0)) / 2) + 1
        if "max_tokens" in gen_conf:
            del gen_conf["max_tokens"]
        ans = ""
        total_tokens = 0

        try:
            response = self.client.do(model=self.model_name, messages=history, system=system, stream=True, **gen_conf)
            for resp in response:
                resp = resp.body
                ans = resp["result"]
                total_tokens = total_token_count_from_response(resp)

                yield ans

        except Exception as e:
            return ans + "\n**ERROR**: " + str(e), 0

        yield total_tokens


class GoogleChat(Base):
    _FACTORY_NAME = "Google Cloud"

    def __init__(self, key, model_name, base_url=None, **kwargs):
        super().__init__(key, model_name, base_url=base_url, **kwargs)

        import base64

        from google.oauth2 import service_account

        key = json.loads(key)
        access_token = json.loads(base64.b64decode(key.get("google_service_account_key", "")))
        project_id = key.get("google_project_id", "")
        region = key.get("google_region", "")

        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        self.model_name = model_name

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
            from google import genai

            if access_token:
                credits = service_account.Credentials.from_service_account_info(access_token, scopes=scopes)
                self.client = genai.Client(vertexai=True, project=project_id, location=region, credentials=credits)
            else:
                self.client = genai.Client(vertexai=True, project=project_id, location=region)

    def _clean_conf(self, gen_conf):
        if "claude" in self.model_name:
            if "max_tokens" in gen_conf:
                del gen_conf["max_tokens"]
        else:
            if "max_tokens" in gen_conf:
                gen_conf["max_output_tokens"] = gen_conf["max_tokens"]
                del gen_conf["max_tokens"]
            for k in list(gen_conf.keys()):
                if k not in ["temperature", "top_p", "max_output_tokens"]:
                    del gen_conf[k]
        # LINEAJE: runtime guardrail checks `gen_conf` as it flows from the agent to the user interface, before it leaves the application (in GoogleChat._clean_conf).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `gen_conf` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:69448083f9071318f0ec23c6fc61fd9b9769d0233e142bb9f64d7fc1ad5beb75'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:69448083f9071318f0ec23c6fc61fd9b9769d0233e142bb9f64d7fc1ad5beb75', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 993, 'function': 'GoogleChat._clean_conf'}, 'file': 'rag/llm/chat_model.py', 'line': 993, 'function': '_clean_conf', 'agent_name': 'GoogleChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            gen_conf = _gr_client.enforce(_gr_site, gen_conf, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return gen_conf

    def _chat(self, history, gen_conf={}, **kwargs):
        system = history[0]["content"] if history and history[0]["role"] == "system" else ""

        if "claude" in self.model_name:
            gen_conf = self._clean_conf(gen_conf)
            _lineaje_messages = [h for h in history if h["role"] != "system"]
            # LINEAJE: runtime guardrail checks `_lineaje_messages` as it flows from the agent to the LLM, before it is sent to the model (in GoogleChat._chat).
            #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `_lineaje_messages` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:21d6f76ba8e7009f787bd14cf3af6a8163067e496bb3c62680e8f4fbd6abc7d4'
            _lineaje__lineaje_messages_evidence = {'_lineaje_messages': _lineaje_messages, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
            _gr_client = _lineaje_load_gr_client()
            _lineaje_interaction_id = _gr_client.new_interaction_id()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:21d6f76ba8e7009f787bd14cf3af6a8163067e496bb3c62680e8f4fbd6abc7d4', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'GoogleChat._chat', 'line': 1000}, 'file': 'rag/llm/chat_model.py', 'line': 1000, 'function': '_chat', 'agent_name': 'GoogleChat', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:22aec97d4b6d7504'}, interaction_id=_lineaje_interaction_id)
            try:
                _lineaje__lineaje_messages_evidence = _gr_client.enforce(_gr_site, _lineaje__lineaje_messages_evidence, content_type='application/json')
                _lineaje_messages = _lineaje__lineaje_messages_evidence.get('_lineaje_messages', _lineaje_messages) if isinstance(_lineaje__lineaje_messages_evidence, dict) else _lineaje_messages
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            response = self.client.messages.create(
                model=self.model_name,
                messages=_lineaje_messages,
                system=system,
                stream=False,
                **gen_conf,
            ).json()
            try:
                _lineaje_obs = _lineaje_load_gr_client()
                _lineaje_obs_site = _lineaje_obs.SiteDescriptor(site_id='site:sha256:3c6e07b24a11dd514370409ae88b7eba14c3e2a6dbb879a6acc93118da09f6ca', phase='', boundary={}, fail_mode='ALLOW', source_type='llm', destination_type='agent', project='tree', organization='', components={'file': 'rag/llm/chat_model.py', 'line': 1000, 'function': '_chat', 'agent_name': 'GoogleChat', 'agent_name_source': 'inferred_from_class', 'call_target': 'self.client.messages.create(model=self.model_name, messages=[h for h in history ', 'not_on_graph': True}, observe_only=True, interaction_id=locals().get('_lineaje_interaction_id'))
                _lineaje_obs.enforce(_lineaje_obs_site, {'activity': 'llm_to_agent'}, content_type='application/json')
            except Exception:
                pass
            ans = response["content"][0]["text"]
            if response["stop_reason"] == "max_tokens":
                ans += "...\nFor the content length reason, it stopped, continue?" if is_english([ans]) else "······\n由于长度的原因，回答被截断了，要继续吗？"
            return (
                ans,
                response["usage"]["input_tokens"] + response["usage"]["output_tokens"],
            )

        # Gemini models with google-genai SDK
        # Set default thinking_budget=0 if not specified
        if "thinking_budget" not in gen_conf:
            gen_conf["thinking_budget"] = 0

        thinking_budget = gen_conf.pop("thinking_budget", 0)
        gen_conf = self._clean_conf(gen_conf)

        # Build GenerateContentConfig
        try:
            from google.genai.types import Content, GenerateContentConfig, Part, ThinkingConfig
        except ImportError as e:
            _lineaje_payload = f"[GoogleChat] Failed to import google-genai: {e}. Please install: pip install google-genai>=1.41.0"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleChat._chat).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6858d018bac5277c819c1a5cd4c7fabd97f1ed317146ecab90cc642cee81ab41'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6858d018bac5277c819c1a5cd4c7fabd97f1ed317146ecab90cc642cee81ab41', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1027, 'function': 'GoogleChat._chat'}, 'file': 'rag/llm/chat_model.py', 'line': 1027, 'function': '_chat', 'agent_name': 'GoogleChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            raise

        config_dict = {}
        if system:
            config_dict["system_instruction"] = system
        if "temperature" in gen_conf:
            config_dict["temperature"] = gen_conf["temperature"]
        if "top_p" in gen_conf:
            config_dict["top_p"] = gen_conf["top_p"]
        if "max_output_tokens" in gen_conf:
            config_dict["max_output_tokens"] = gen_conf["max_output_tokens"]

        # Add ThinkingConfig
        config_dict["thinking_config"] = ThinkingConfig(thinking_budget=thinking_budget)

        config = GenerateContentConfig(**config_dict)

        # Convert history to google-genai Content format
        contents = []
        for item in history:
            if item["role"] == "system":
                continue
            # google-genai uses 'model' instead of 'assistant'
            role = "model" if item["role"] == "assistant" else item["role"]
            content = Content(
                role=role,
                parts=[Part(text=item["content"])],
            )
            contents.append(content)

        # LINEAJE: runtime guardrail checks `contents` as it flows from the agent to the LLM, before it is sent to the model (in GoogleChat._chat).
        #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `contents` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:22c0ab5bc304ab845f801d8561c916304ac6adaf10156e8d7b2e40e4f73c25ef'
        _lineaje_contents_evidence = {'contents': contents, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
        _gr_client = _lineaje_load_gr_client()
        _lineaje_interaction_id = _gr_client.new_interaction_id()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:22c0ab5bc304ab845f801d8561c916304ac6adaf10156e8d7b2e40e4f73c25ef', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'GoogleChat._chat', 'line': 1058}, 'file': 'rag/llm/chat_model.py', 'line': 1058, 'function': '_chat', 'agent_name': 'GoogleChat', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:57db6a61299cb0ec'}, interaction_id=_lineaje_interaction_id)
        try:
            _lineaje_contents_evidence = _gr_client.enforce(_gr_site, _lineaje_contents_evidence, content_type='application/json')
            contents = _lineaje_contents_evidence.get('contents', contents) if isinstance(_lineaje_contents_evidence, dict) else contents
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=config,
        )
        # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in GoogleChat._chat).
        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b6324d85809ce11d3b573a57f1de83474c1634a0007d4fa5ef2c667923c36ddd'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b6324d85809ce11d3b573a57f1de83474c1634a0007d4fa5ef2c667923c36ddd', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'GoogleChat._chat', 'line': 1058}, 'file': 'rag/llm/chat_model.py', 'line': 1058, 'function': '_chat', 'agent_name': 'GoogleChat', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:57db6a61299cb0ec'}, interaction_id=locals().get('_lineaje_interaction_id'))
        try:
            if not hasattr(_gr_client, 'enforce_reply'):
                __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
            response = _gr_client.enforce_reply(_gr_site, response, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass

        ans = response.text
        # Get token count from response
        try:
            total_tokens = response.usage_metadata.total_token_count
        except Exception:
            total_tokens = 0

        return ans, total_tokens

    def chat_streamly(self, system, history, gen_conf={}, **kwargs):
        if "claude" in self.model_name:
            if "max_tokens" in gen_conf:
                del gen_conf["max_tokens"]
            ans = ""
            total_tokens = 0
            try:
                # LINEAJE: runtime guardrail checks `history` as it flows from the agent to the LLM, before it is sent to the model (in GoogleChat.chat_streamly).
                #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `history` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:c52ff5642505423d7fa8d84d3157bde3ba342ed7f1b0fcf4b769adea15225e0b'
                _lineaje_history_evidence = {'history': history, 'model': self.model_name, 'model_source': 'call_kwarg', 'project': 'tree'}
                _gr_client = _lineaje_load_gr_client()
                _lineaje_interaction_id = _gr_client.new_interaction_id()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c52ff5642505423d7fa8d84d3157bde3ba342ed7f1b0fcf4b769adea15225e0b', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'GoogleChat.chat_streamly', 'line': 1080}, 'file': 'rag/llm/chat_model.py', 'line': 1080, 'function': 'chat_streamly', 'agent_name': 'GoogleChat', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:ee24d38d827ee914'}, interaction_id=_lineaje_interaction_id)
                try:
                    _lineaje_history_evidence = _gr_client.enforce(_gr_site, _lineaje_history_evidence, content_type='application/json')
                    history = _lineaje_history_evidence.get('history', history) if isinstance(_lineaje_history_evidence, dict) else history
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    raise
                response = self.client.messages.create(
                    model=self.model_name,
                    messages=history,
                    system=system,
                    stream=True,
                    **gen_conf,
                )
                # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in GoogleChat.chat_streamly).
                #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f05aa7c5fa7803c82a2ed25fef1b07680a800dfe2b2ebe2a17772d0dec762b9c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f05aa7c5fa7803c82a2ed25fef1b07680a800dfe2b2ebe2a17772d0dec762b9c', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'GoogleChat.chat_streamly', 'line': 1080}, 'file': 'rag/llm/chat_model.py', 'line': 1080, 'function': 'chat_streamly', 'agent_name': 'GoogleChat', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:ee24d38d827ee914'}, interaction_id=locals().get('_lineaje_interaction_id'))
                try:
                    if not hasattr(_gr_client, 'enforce_reply'):
                        __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                        raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                    response = _gr_client.enforce_reply(_gr_site, response, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                for res in response.iter_lines():
                    res = res.decode("utf-8")
                    if "content_block_delta" in res and "data" in res:
                        text = json.loads(res[6:])["delta"]["text"]
                        ans = text
                        total_tokens += num_tokens_from_string(text)
            except Exception as e:
                yield ans + "\n**ERROR**: " + str(e)

            yield total_tokens
        else:
            # Gemini models with google-genai SDK
            ans = ""
            total_tokens = 0

            # Set default thinking_budget=0 if not specified
            if "thinking_budget" not in gen_conf:
                gen_conf["thinking_budget"] = 0

            thinking_budget = gen_conf.pop("thinking_budget", 0)
            gen_conf = self._clean_conf(gen_conf)

            # Build GenerateContentConfig
            try:
                from google.genai.types import Content, GenerateContentConfig, Part, ThinkingConfig
            except ImportError as e:
                _lineaje_payload = f"[GoogleChat] Failed to import google-genai: {e}. Please install: pip install google-genai>=1.41.0"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GoogleChat.chat_streamly).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a9aacbe3c3e5d7d8730f8a21457cafa97a2065334c52a71740166b10650279dc'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a9aacbe3c3e5d7d8730f8a21457cafa97a2065334c52a71740166b10650279dc', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1113, 'function': 'GoogleChat.chat_streamly'}, 'file': 'rag/llm/chat_model.py', 'line': 1113, 'function': 'chat_streamly', 'agent_name': 'GoogleChat', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                raise

            config_dict = {}
            if system:
                config_dict["system_instruction"] = system
            if "temperature" in gen_conf:
                config_dict["temperature"] = gen_conf["temperature"]
            if "top_p" in gen_conf:
                config_dict["top_p"] = gen_conf["top_p"]
            if "max_output_tokens" in gen_conf:
                config_dict["max_output_tokens"] = gen_conf["max_output_tokens"]

            # Add ThinkingConfig
            config_dict["thinking_config"] = ThinkingConfig(thinking_budget=thinking_budget)

            config = GenerateContentConfig(**config_dict)

            # Convert history to google-genai Content format
            contents = []
            for item in history:
                # google-genai uses 'model' instead of 'assistant'
                role = "model" if item["role"] == "assistant" else item["role"]
                content = Content(
                    role=role,
                    parts=[Part(text=item["content"])],
                )
                contents.append(content)

            try:
                for chunk in self.client.models.generate_content_stream(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                ):
                    text = chunk.text
                    ans = text
                    total_tokens += num_tokens_from_string(text)
                    yield ans

            except Exception as e:
                yield ans + "\n**ERROR**: " + str(e)

            yield total_tokens


class TokenPonyChat(Base):
    _FACTORY_NAME = "TokenPony"

    def __init__(self, key, model_name, base_url="https://ragflow.vip-api.tokenpony.cn/v1", **kwargs):
        if not base_url:
            base_url = "https://ragflow.vip-api.tokenpony.cn/v1"
        super().__init__(key, model_name, base_url, **kwargs)


class LiteLLMBase(ABC):
    _FACTORY_NAME = [
        "Tongyi-Qianwen",
        "Bedrock",
        "Moonshot",
        "xAI",
        "DeepInfra",
        "Groq",
        "Cohere",
        "Gemini",
        "DeepSeek",
        "NVIDIA",
        "TogetherAI",
        "Anthropic",
        "Ollama",
        "LongCat",
        "CometAPI",
        "SILICONFLOW",
        "OpenRouter",
        "StepFun",
        "PPIO",
        "PerfXCloud",
        "Upstage",
        "NovitaAI",
        "01.AI",
        "GiteeAI",
        "302.AI",
        "Jiekou.AI",
        "ZHIPU-AI",
        "MiniMax",
        "DeerAPI",
        "GPUStack",
        "OpenAI",
        "Azure-OpenAI",
    ]

    def __init__(self, key, model_name, base_url=None, **kwargs):
        self.timeout = int(os.environ.get("LLM_TIMEOUT_SECONDS", 600))
        self.provider = kwargs.get("provider", "")
        self.prefix = LITELLM_PROVIDER_PREFIX.get(self.provider, "")
        self.model_name = f"{self.prefix}{model_name}"
        self.api_key = key
        self.base_url = (base_url or FACTORY_DEFAULT_BASE_URL.get(self.provider, "")).rstrip("/")
        # Configure retry parameters
        self.max_retries = kwargs.get("max_retries", int(os.environ.get("LLM_MAX_RETRIES", 5)))
        self.base_delay = kwargs.get("retry_interval", float(os.environ.get("LLM_BASE_DELAY", 2.0)))
        self.max_rounds = kwargs.get("max_rounds", 5)
        self.is_tools = False
        self.tools = []
        self.toolcall_sessions = {}

        # Factory specific fields
        if self.provider == SupportedLiteLLMProvider.OpenRouter:
            self.api_key = json.loads(key).get("api_key", "")
            self.provider_order = json.loads(key).get("provider_order", "")
        elif self.provider == SupportedLiteLLMProvider.Azure_OpenAI:
            self.api_key = json.loads(key).get("api_key", "")
            self.api_version = json.loads(key).get("api_version", "2024-02-01")

    def _get_delay(self):
        return self.base_delay * random.uniform(10, 150)

    def _classify_error(self, error):
        error_str = str(error).lower()

        keywords_mapping = [
            (["quota", "capacity", "credit", "billing", "balance", "欠费"], LLMErrorCode.ERROR_QUOTA),
            (["rate limit", "429", "tpm limit", "too many requests", "requests per minute"], LLMErrorCode.ERROR_RATE_LIMIT),
            (["auth", "key", "apikey", "401", "forbidden", "permission"], LLMErrorCode.ERROR_AUTHENTICATION),
            (["invalid", "bad request", "400", "format", "malformed", "parameter"], LLMErrorCode.ERROR_INVALID_REQUEST),
            (["server", "503", "502", "504", "500", "unavailable"], LLMErrorCode.ERROR_SERVER),
            (["timeout", "timed out"], LLMErrorCode.ERROR_TIMEOUT),
            (["connect", "network", "unreachable", "dns"], LLMErrorCode.ERROR_CONNECTION),
            (["filter", "content", "policy", "blocked", "safety", "inappropriate"], LLMErrorCode.ERROR_CONTENT_FILTER),
            (["model", "not found", "does not exist", "not available"], LLMErrorCode.ERROR_MODEL),
            (["max rounds"], LLMErrorCode.ERROR_MODEL),
        ]
        for words, code in keywords_mapping:
            if re.search("({})".format("|".join(words)), error_str):
                # LINEAJE: runtime guardrail checks `code` as it flows from the agent to the user interface, before it leaves the application (in LiteLLMBase._classify_error).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `code` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:11a84f2d25ed58b36ca88916f41df7af4d69132219ff4d9527538ff8cd664a7e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:11a84f2d25ed58b36ca88916f41df7af4d69132219ff4d9527538ff8cd664a7e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1247, 'function': 'LiteLLMBase._classify_error'}, 'file': 'rag/llm/chat_model.py', 'line': 1247, 'function': '_classify_error', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    code = _gr_client.enforce(_gr_site, code, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return code

        return LLMErrorCode.ERROR_GENERIC

    def _clean_conf(self, gen_conf):
        if "max_tokens" in gen_conf:
            del gen_conf["max_tokens"]
        # LINEAJE: runtime guardrail checks `gen_conf` as it flows from the agent to the user interface, before it leaves the application (in LiteLLMBase._clean_conf).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `gen_conf` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:84eb0d370948bde0f92be0d1f9320031e7e4a3d42564c3bd18815ded22b27e7a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:84eb0d370948bde0f92be0d1f9320031e7e4a3d42564c3bd18815ded22b27e7a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1254, 'function': 'LiteLLMBase._clean_conf'}, 'file': 'rag/llm/chat_model.py', 'line': 1254, 'function': '_clean_conf', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            gen_conf = _gr_client.enforce(_gr_site, gen_conf, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return gen_conf

    async def async_chat(self, system, history, gen_conf, **kwargs):
        hist = list(history) if history else []
        if system:
            if not hist or hist[0].get("role") != "system":
                hist.insert(0, {"role": "system", "content": system})

        # LINEAJE: runtime guardrail checks `hist` as it flows from the agent to an external endpoint, before it leaves the application (in LiteLLMBase.async_chat).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `hist` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:2063c53f41f5939811f7fbf41f158654c3fb8c01bcccf398b9e5ad8b58b8d2e7'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2063c53f41f5939811f7fbf41f158654c3fb8c01bcccf398b9e5ad8b58b8d2e7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1262, 'function': 'LiteLLMBase.async_chat'}, 'file': 'rag/llm/chat_model.py', 'line': 1262, 'function': 'async_chat', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            hist = _gr_client.enforce(_gr_site, hist, content_type='application/json', variable_name='hist', source_file=__file__, before_line=1262)
        except _gr_client.GuardrailUnavailableError:
            pass
        _lineaje_payload = "[HISTORY]" + json.dumps(hist, ensure_ascii=False, indent=2)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LiteLLMBase.async_chat).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c6a2e676f06f9bb4a72e14a5d283814cacacd5101471632c5e061493c5241e3c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c6a2e676f06f9bb4a72e14a5d283814cacacd5101471632c5e061493c5241e3c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1262, 'function': 'LiteLLMBase.async_chat'}, 'file': 'rag/llm/chat_model.py', 'line': 1262, 'function': 'async_chat', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        if self.model_name.lower().find("qwen3") >= 0:
            kwargs["extra_body"] = {"enable_thinking": False}

        completion_args = self._construct_completion_args(history=hist, stream=False, tools=False, **gen_conf)

        for attempt in range(self.max_retries + 1):
            try:
                # LINEAJE: runtime guardrail checks `completion_args` as it flows from the agent to the LLM, before it is sent to the model (in LiteLLMBase.async_chat).
                #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `completion_args` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:4bd9c8d247e2190a499f5201ee9f87a1f9e0098d6b31f310ffeaa7e13c4b686e'
                _gr_client = _lineaje_load_gr_client()
                _lineaje_interaction_id = _gr_client.new_interaction_id()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4bd9c8d247e2190a499f5201ee9f87a1f9e0098d6b31f310ffeaa7e13c4b686e', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'LiteLLMBase.async_chat', 'line': 1270}, 'file': 'rag/llm/chat_model.py', 'line': 1270, 'function': 'async_chat', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:3a2b313db98b40d8'}, interaction_id=_lineaje_interaction_id)
                try:
                    if not hasattr(_gr_client, 'enforce_request'):
                        __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_request (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                        raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_request")
                    completion_args = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_request(_gr_site, completion_args, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    raise
                response = await litellm.acompletion(
                    **completion_args,
                    drop_params=True,
                    timeout=self.timeout,
                )
                # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in LiteLLMBase.async_chat).
                #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:ac73f170066f3fb73222eb424356cc5d956751f42f4658461894150e33104ad4'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ac73f170066f3fb73222eb424356cc5d956751f42f4658461894150e33104ad4', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'LiteLLMBase.async_chat', 'line': 1270}, 'file': 'rag/llm/chat_model.py', 'line': 1270, 'function': 'async_chat', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:3a2b313db98b40d8'}, interaction_id=locals().get('_lineaje_interaction_id'))
                try:
                    if not hasattr(_gr_client, 'enforce_reply'):
                        __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                        raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                    response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass

                if any([not response.choices, not response.choices[0].message, not response.choices[0].message.content]):
                    return "", 0
                ans = response.choices[0].message.content.strip()
                # LINEAJE: runtime guardrail checks `ans` as it flows from the LLM to the agent, after the model replies (in LiteLLMBase.async_chat).
                #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `ans` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:bbf8ef4634e80c74dca632eb9e9ff10cf8216acb71a45af0d5a17c6c2eab5059'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bbf8ef4634e80c74dca632eb9e9ff10cf8216acb71a45af0d5a17c6c2eab5059', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'version': '', 'provider': ''}, 'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'version': '', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1278, 'function': 'LiteLLMBase.async_chat'}, 'file': 'rag/llm/chat_model.py', 'line': 1278, 'function': 'async_chat', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True}, interaction_id=locals().get('_lineaje_interaction_id'))
                try:
                    ans = _gr_client.enforce(_gr_site, ans, content_type='application/json', variable_name='ans', source_file=__file__, before_line=1278)
                except _gr_client.GuardrailUnavailableError:
                    pass
                if response.choices[0].finish_reason == "length":
                    ans = self._length_stop(ans)

                return ans, total_token_count_from_response(response)
            except Exception as e:
                e = await self._exceptions_async(e, attempt)
                if e:
                    return e, 0

        assert False, "Shouldn't be here."

    async def async_chat_streamly(self, system, history, gen_conf, **kwargs):
        if system and history and history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": system})
        # LINEAJE: runtime guardrail checks `history` as it flows from the agent to an external endpoint, before it leaves the application (in LiteLLMBase.async_chat_streamly).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `history` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:662f89d87b4022c771cf441cdd6991f2ad425492201c6ba0b7a75efe7e2ab518'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:662f89d87b4022c771cf441cdd6991f2ad425492201c6ba0b7a75efe7e2ab518', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1293, 'function': 'LiteLLMBase.async_chat_streamly'}, 'file': 'rag/llm/chat_model.py', 'line': 1293, 'function': 'async_chat_streamly', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            history = _gr_client.enforce(_gr_site, history, content_type='application/json', variable_name='history', source_file=__file__, before_line=1293)
        except _gr_client.GuardrailUnavailableError:
            pass
        _lineaje_payload = "[HISTORY STREAMLY]" + json.dumps(history, ensure_ascii=False, indent=4)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LiteLLMBase.async_chat_streamly).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ca92850d04e799f56fb3a8eca3e0f36d10c85d1a037a7a2302aee4bc42ab0136'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ca92850d04e799f56fb3a8eca3e0f36d10c85d1a037a7a2302aee4bc42ab0136', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1293, 'function': 'LiteLLMBase.async_chat_streamly'}, 'file': 'rag/llm/chat_model.py', 'line': 1293, 'function': 'async_chat_streamly', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        gen_conf = self._clean_conf(gen_conf)
        reasoning_start = False
        total_tokens = 0

        completion_args = self._construct_completion_args(history=history, stream=True, tools=False, **gen_conf)
        stop = kwargs.get("stop")
        if stop:
            completion_args["stop"] = stop

        for attempt in range(self.max_retries + 1):
            try:
                # LINEAJE: runtime guardrail checks `completion_args` as it flows from the agent to the LLM, before it is sent to the model (in LiteLLMBase.async_chat_streamly).
                #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `completion_args` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:d76876f068823858f1444d250a16a06efcd7b31e68725602d5d6132ca9cb3f17'
                _gr_client = _lineaje_load_gr_client()
                _lineaje_interaction_id = _gr_client.new_interaction_id()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d76876f068823858f1444d250a16a06efcd7b31e68725602d5d6132ca9cb3f17', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'LiteLLMBase.async_chat_streamly', 'line': 1305}, 'file': 'rag/llm/chat_model.py', 'line': 1305, 'function': 'async_chat_streamly', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:625c7a8e366241c0'}, interaction_id=_lineaje_interaction_id)
                try:
                    if not hasattr(_gr_client, 'enforce_request'):
                        __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_request (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                        raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_request")
                    completion_args = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_request(_gr_site, completion_args, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    raise
                stream = await litellm.acompletion(
                    **completion_args,
                    drop_params=True,
                    timeout=self.timeout,
                )
                # LINEAJE: runtime guardrail checks `stream` as it flows from the LLM to the agent, after the model replies (in LiteLLMBase.async_chat_streamly).
                #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `stream` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:7fddee83b7d712ebd0d32a05bb3968e37c2875bb3e39c88bf6ffd30f1c1f785c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7fddee83b7d712ebd0d32a05bb3968e37c2875bb3e39c88bf6ffd30f1c1f785c', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'LiteLLMBase.async_chat_streamly', 'line': 1305}, 'file': 'rag/llm/chat_model.py', 'line': 1305, 'function': 'async_chat_streamly', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:625c7a8e366241c0'}, interaction_id=locals().get('_lineaje_interaction_id'))
                try:
                    if not hasattr(_gr_client, 'enforce_reply'):
                        __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                        raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                    stream = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, stream, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass

                async for resp in stream:
                    if not hasattr(resp, "choices") or not resp.choices:
                        continue

                    delta = resp.choices[0].delta
                    if not hasattr(delta, "content") or delta.content is None:
                        delta.content = ""

                    if kwargs.get("with_reasoning", True) and hasattr(delta, "reasoning_content") and delta.reasoning_content:
                        ans = ""
                        if not reasoning_start:
                            reasoning_start = True
                            ans = "<think>"
                        ans += delta.reasoning_content + "</think>"
                    else:
                        reasoning_start = False
                        ans = delta.content

                    tol = total_token_count_from_response(resp)
                    if not tol:
                        tol = num_tokens_from_string(delta.content)
                    total_tokens += tol

                    finish_reason = resp.choices[0].finish_reason if hasattr(resp.choices[0], "finish_reason") else ""
                    if finish_reason == "length":
                        if is_chinese(ans):
                            ans += LENGTH_NOTIFICATION_CN
                        else:
                            ans += LENGTH_NOTIFICATION_EN

                    yield ans
                yield total_tokens
                return
            except Exception as e:
                e = await self._exceptions_async(e, attempt)
                if e:
                    yield e
                    yield total_tokens
                    return

    def _length_stop(self, ans):
        if is_chinese([ans]):
            return ans + LENGTH_NOTIFICATION_CN
        return ans + LENGTH_NOTIFICATION_EN

    @property
    def _retryable_errors(self) -> set[str]:
        return {
            LLMErrorCode.ERROR_RATE_LIMIT,
            LLMErrorCode.ERROR_SERVER,
        }

    def _should_retry(self, error_code: str) -> bool:
        return error_code in self._retryable_errors

    async def _exceptions_async(self, e, attempt):
        _lineaje_payload = "LiteLLMBase async completion"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LiteLLMBase._exceptions_async).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:4efbc3c0121c788c572e91409503f4c89da655ad5cd0904068e54a798e27850d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4efbc3c0121c788c572e91409503f4c89da655ad5cd0904068e54a798e27850d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1367, 'function': 'LiteLLMBase._exceptions_async'}, 'file': 'rag/llm/chat_model.py', 'line': 1367, 'function': '_exceptions_async', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.exception(_lineaje_payload)
        error_code = self._classify_error(e)
        if attempt == self.max_retries:
            error_code = LLMErrorCode.ERROR_MAX_RETRIES

        if self._should_retry(error_code):
            delay = self._get_delay()
            _lineaje_payload = f"Error: {error_code}. Retrying in {delay:.2f} seconds... (Attempt {attempt + 1}/{self.max_retries})"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LiteLLMBase._exceptions_async).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ab7d282c250a03e7fe3f3824185eba605d57232bf0354f382640db7dbdc86df1'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ab7d282c250a03e7fe3f3824185eba605d57232bf0354f382640db7dbdc86df1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1374, 'function': 'LiteLLMBase._exceptions_async'}, 'file': 'rag/llm/chat_model.py', 'line': 1374, 'function': '_exceptions_async', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            await asyncio.sleep(delay)
            return None
        msg = f"{ERROR_PREFIX}: {error_code} - {str(e)}"
        _lineaje_payload = f"async_chat_streamly giving up: {msg}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LiteLLMBase._exceptions_async).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1c7a6fcb78620696f6fd6a6b3631cefac20e53b24623f8d9b7c855ec174f5ec1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1c7a6fcb78620696f6fd6a6b3631cefac20e53b24623f8d9b7c855ec174f5ec1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1378, 'function': 'LiteLLMBase._exceptions_async'}, 'file': 'rag/llm/chat_model.py', 'line': 1378, 'function': '_exceptions_async', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `msg` as it flows from the agent to the user interface, before it leaves the application (in LiteLLMBase._exceptions_async).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:020495db79b392ed2669205399e463ba74667948bda7d114b2c5fd129385c4bc'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:020495db79b392ed2669205399e463ba74667948bda7d114b2c5fd129385c4bc', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1379, 'function': 'LiteLLMBase._exceptions_async'}, 'file': 'rag/llm/chat_model.py', 'line': 1379, 'function': '_exceptions_async', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            msg = _gr_client.enforce(_gr_site, msg, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return msg

    def _verbose_tool_use(self, name, args, res):
        _lineaje_payload = {"name": name, "args": args, "result": res}
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to an external endpoint, before it leaves the application (in LiteLLMBase._verbose_tool_use).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `_lineaje_payload` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:12814c42e40c26f55aabefab260b357f10f323a0d7a7b888843576142868b94f'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:12814c42e40c26f55aabefab260b357f10f323a0d7a7b888843576142868b94f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1382, 'function': 'LiteLLMBase._verbose_tool_use'}, 'file': 'rag/llm/chat_model.py', 'line': 1382, 'function': '_verbose_tool_use', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=1382)
        except _gr_client.GuardrailUnavailableError:
            pass
        return "<tool_call>" + json.dumps(_lineaje_payload, ensure_ascii=False, indent=2) + "</tool_call>"

    def _append_history(self, hist, tool_call, tool_res):
        hist.append(
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "index": tool_call.index,
                        "id": tool_call.id,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                        "type": "function",
                    },
                ],
            }
        )
        try:
            if isinstance(tool_res, dict):
                # LINEAJE: runtime guardrail checks `tool_res` as it flows from the agent to an external endpoint, before it leaves the application (in LiteLLMBase._append_history).
                #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `tool_res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:d6aca8288b1d1f2881efb34f49a08d77e78ebf19492d50aa14a80d5843c4b586'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d6aca8288b1d1f2881efb34f49a08d77e78ebf19492d50aa14a80d5843c4b586', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1403, 'function': 'LiteLLMBase._append_history'}, 'file': 'rag/llm/chat_model.py', 'line': 1403, 'function': '_append_history', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    tool_res = _gr_client.enforce(_gr_site, tool_res, content_type='application/json', variable_name='tool_res', source_file=__file__, before_line=1403)
                except _gr_client.GuardrailUnavailableError:
                    pass
                tool_res = json.dumps(tool_res, ensure_ascii=False)
        finally:
            hist.append({"role": "tool", "tool_call_id": tool_call.id, "content": str(tool_res)})
        # LINEAJE: runtime guardrail checks `hist` as it flows from the agent to the user interface, before it leaves the application (in LiteLLMBase._append_history).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `hist` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3ae5249de60907a3c4d7c9567d395ad560939e0afcd3c702347b4c6463ecdaab'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3ae5249de60907a3c4d7c9567d395ad560939e0afcd3c702347b4c6463ecdaab', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1406, 'function': 'LiteLLMBase._append_history'}, 'file': 'rag/llm/chat_model.py', 'line': 1406, 'function': '_append_history', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            hist = _gr_client.enforce(_gr_site, hist, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return hist

    def bind_tools(self, toolcall_session, tools):
        if not (toolcall_session and tools):
            return
        self.is_tools = True
        self.toolcall_session = toolcall_session
        self.tools = tools

    async def async_chat_with_tools(self, system: str, history: list, gen_conf: dict = {}):
        gen_conf = self._clean_conf(gen_conf)
        if system and history and history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": system})

        ans = ""
        tk_count = 0
        hist = deepcopy(history)
        for attempt in range(self.max_retries + 1):
            history = deepcopy(hist)
            try:
                for _ in range(self.max_rounds + 1):
                    _lineaje_payload = f"{self.tools=}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LiteLLMBase.async_chat_with_tools).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:bc10bfe889de3db792d5d22fe90ab178a44e4cea8f7f72a93f03b24665e55ff1'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bc10bfe889de3db792d5d22fe90ab178a44e4cea8f7f72a93f03b24665e55ff1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1427, 'function': 'LiteLLMBase.async_chat_with_tools'}, 'file': 'rag/llm/chat_model.py', 'line': 1427, 'function': 'async_chat_with_tools', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)

                    completion_args = self._construct_completion_args(history=history, stream=False, tools=True, **gen_conf)
                    # LINEAJE: runtime guardrail checks `completion_args` as it flows from the agent to the LLM, before it is sent to the model (in LiteLLMBase.async_chat_with_tools).
                    #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `completion_args` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:5db93f0b62114800de9aa587cb05558dc2a0b47d502b7bf46199f924bb85d1c8'
                    _gr_client = _lineaje_load_gr_client()
                    _lineaje_interaction_id = _gr_client.new_interaction_id()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5db93f0b62114800de9aa587cb05558dc2a0b47d502b7bf46199f924bb85d1c8', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'LiteLLMBase.async_chat_with_tools', 'line': 1430}, 'file': 'rag/llm/chat_model.py', 'line': 1430, 'function': 'async_chat_with_tools', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:bae0034c13fb4d5f'}, interaction_id=_lineaje_interaction_id)
                    try:
                        if not hasattr(_gr_client, 'enforce_request'):
                            __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_request (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                            raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_request")
                        completion_args = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_request(_gr_site, completion_args, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        raise
                    response = await litellm.acompletion(
                        **completion_args,
                        drop_params=True,
                        timeout=self.timeout,
                    )
                    # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in LiteLLMBase.async_chat_with_tools).
                    #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:fc0ef6b480f4659dc44ab56d51d418c6e32221b5cf3ee70a67824bbc8993a40a'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fc0ef6b480f4659dc44ab56d51d418c6e32221b5cf3ee70a67824bbc8993a40a', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'LiteLLMBase.async_chat_with_tools', 'line': 1430}, 'file': 'rag/llm/chat_model.py', 'line': 1430, 'function': 'async_chat_with_tools', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:bae0034c13fb4d5f'}, interaction_id=locals().get('_lineaje_interaction_id'))
                    try:
                        if not hasattr(_gr_client, 'enforce_reply'):
                            __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                            raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                        response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass

                    tk_count += total_token_count_from_response(response)

                    if not hasattr(response, "choices") or not response.choices or not response.choices[0].message:
                        raise Exception(f"500 response structure error. Response: {response}")

                    message = response.choices[0].message
                    # LINEAJE: runtime guardrail checks `message` as it flows from the LLM to the agent, after the model replies (in LiteLLMBase.async_chat_with_tools).
                    #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `message` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:0223ec3ff8f29037fc87111b9b6859340465bf161800e7c76da58ce116a4481d'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0223ec3ff8f29037fc87111b9b6859340465bf161800e7c76da58ce116a4481d', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'version': '', 'provider': ''}, 'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'version': '', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1441, 'function': 'LiteLLMBase.async_chat_with_tools'}, 'file': 'rag/llm/chat_model.py', 'line': 1441, 'function': 'async_chat_with_tools', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True}, interaction_id=locals().get('_lineaje_interaction_id'))
                    try:
                        message = _gr_client.enforce(_gr_site, message, content_type='application/json', variable_name='message', source_file=__file__, before_line=1441)
                    except _gr_client.GuardrailUnavailableError:
                        pass

                    if not hasattr(message, "tool_calls") or not message.tool_calls:
                        if hasattr(message, "reasoning_content") and message.reasoning_content:
                            ans += f"<think>{message.reasoning_content}</think>"
                        ans += message.content or ""
                        if response.choices[0].finish_reason == "length":
                            ans = self._length_stop(ans)
                        return ans, tk_count

                    for tool_call in message.tool_calls:
                        _lineaje_payload = f"Response {tool_call=}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LiteLLMBase.async_chat_with_tools).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:fb5b0ef29a175f88305266b5417eb337da74f65e178046389a8f83155f7ed5a3'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fb5b0ef29a175f88305266b5417eb337da74f65e178046389a8f83155f7ed5a3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1452, 'function': 'LiteLLMBase.async_chat_with_tools'}, 'file': 'rag/llm/chat_model.py', 'line': 1452, 'function': 'async_chat_with_tools', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.info(_lineaje_payload)
                        name = tool_call.function.name
                        try:
                            args = json_repair.loads(tool_call.function.arguments)
                            tool_response = await asyncio.to_thread(self.toolcall_session.tool_call, name, args)
                            history = self._append_history(history, tool_call, tool_response)
                            ans += self._verbose_tool_use(name, args, tool_response)
                        except Exception as e:
                            logging.exception(msg=f"Wrong JSON argument format in LLM tool call response: {tool_call}")
                            history.append({"role": "tool", "tool_call_id": tool_call.id, "content": f"Tool call error: \n{tool_call}\nException:\n" + str(e)})
                            ans += self._verbose_tool_use(name, {}, str(e))

                _lineaje_payload = f"Exceed max rounds: {self.max_rounds}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LiteLLMBase.async_chat_with_tools).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:a0b9865419ba45e61ccb2b34d84dad1808515c83af11bab2a7f0f1716798613c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a0b9865419ba45e61ccb2b34d84dad1808515c83af11bab2a7f0f1716798613c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1464, 'function': 'LiteLLMBase.async_chat_with_tools'}, 'file': 'rag/llm/chat_model.py', 'line': 1464, 'function': 'async_chat_with_tools', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                history.append({"role": "user", "content": f"Exceed max rounds: {self.max_rounds}"})

                response, token_count = await self.async_chat("", history, gen_conf)
                ans += response
                tk_count += token_count
                return ans, tk_count

            except Exception as e:
                e = await self._exceptions_async(e, attempt)
                if e:
                    return e, tk_count

        assert False, "Shouldn't be here."

    async def async_chat_streamly_with_tools(self, system: str, history: list, gen_conf: dict = {}):
        gen_conf = self._clean_conf(gen_conf)
        tools = self.tools
        if system and history and history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": system})

        total_tokens = 0
        hist = deepcopy(history)

        for attempt in range(self.max_retries + 1):
            history = deepcopy(hist)
            try:
                for _ in range(self.max_rounds + 1):
                    reasoning_start = False
                    _lineaje_payload = f"{tools=}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LiteLLMBase.async_chat_streamly_with_tools).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:5b07c3be820db825054a0ad8b70559b7d7de01b76c64741079fec1101863b16c'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5b07c3be820db825054a0ad8b70559b7d7de01b76c64741079fec1101863b16c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1493, 'function': 'LiteLLMBase.async_chat_streamly_with_tools'}, 'file': 'rag/llm/chat_model.py', 'line': 1493, 'function': 'async_chat_streamly_with_tools', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)

                    completion_args = self._construct_completion_args(history=history, stream=True, tools=True, **gen_conf)
                    # LINEAJE: runtime guardrail checks `completion_args` as it flows from the agent to the LLM, before it is sent to the model (in LiteLLMBase.async_chat_streamly_with_tools).
                    #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `completion_args` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:87afd1dd464aff939ee5fa2d79cc94b61ee49383de82313fced5915cb8c7a6d3'
                    _gr_client = _lineaje_load_gr_client()
                    _lineaje_interaction_id = _gr_client.new_interaction_id()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:87afd1dd464aff939ee5fa2d79cc94b61ee49383de82313fced5915cb8c7a6d3', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'LiteLLMBase.async_chat_streamly_with_tools', 'line': 1496}, 'file': 'rag/llm/chat_model.py', 'line': 1496, 'function': 'async_chat_streamly_with_tools', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:133c661fa880aee0'}, interaction_id=_lineaje_interaction_id)
                    try:
                        if not hasattr(_gr_client, 'enforce_request'):
                            __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_request (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                            raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_request")
                        completion_args = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_request(_gr_site, completion_args, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        raise
                    response = await litellm.acompletion(
                        **completion_args,
                        drop_params=True,
                        timeout=self.timeout,
                    )
                    # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in LiteLLMBase.async_chat_streamly_with_tools).
                    #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:2b7876e7fdb437abb3716fcd1f17a29ea5814ab04ffd9cb3856946fc5f01b92a'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2b7876e7fdb437abb3716fcd1f17a29ea5814ab04ffd9cb3856946fc5f01b92a', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'LiteLLMBase.async_chat_streamly_with_tools', 'line': 1496}, 'file': 'rag/llm/chat_model.py', 'line': 1496, 'function': 'async_chat_streamly_with_tools', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:133c661fa880aee0'}, interaction_id=locals().get('_lineaje_interaction_id'))
                    try:
                        if not hasattr(_gr_client, 'enforce_reply'):
                            __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                            raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                        response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
                    except _gr_client.GuardrailUnavailableError:
                        pass

                    final_tool_calls = {}
                    answer = ""

                    async for resp in response:
                        if not hasattr(resp, "choices") or not resp.choices:
                            continue

                        delta = resp.choices[0].delta

                        if hasattr(delta, "tool_calls") and delta.tool_calls:
                            for tool_call in delta.tool_calls:
                                index = tool_call.index
                                if index not in final_tool_calls:
                                    if not tool_call.function.arguments:
                                        tool_call.function.arguments = ""
                                    final_tool_calls[index] = tool_call
                                else:
                                    final_tool_calls[index].function.arguments += tool_call.function.arguments or ""
                            continue

                        if not hasattr(delta, "content") or delta.content is None:
                            delta.content = ""

                        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                            ans = ""
                            if not reasoning_start:
                                reasoning_start = True
                                ans = "<think>"
                            ans += delta.reasoning_content + "</think>"
                            yield ans
                        else:
                            reasoning_start = False
                            answer += delta.content
                            yield delta.content

                        tol = total_token_count_from_response(resp)
                        if not tol:
                            total_tokens += num_tokens_from_string(delta.content)
                        else:
                            total_tokens = tol

                        finish_reason = getattr(resp.choices[0], "finish_reason", "")
                        if finish_reason == "length":
                            yield self._length_stop("")

                    if answer:
                        yield total_tokens
                        return

                    for tool_call in final_tool_calls.values():
                        name = tool_call.function.name
                        try:
                            args = json_repair.loads(tool_call.function.arguments)
                            yield self._verbose_tool_use(name, args, "Begin to call...")
                            tool_response = await asyncio.to_thread(self.toolcall_session.tool_call, name, args)
                            history = self._append_history(history, tool_call, tool_response)
                            yield self._verbose_tool_use(name, args, tool_response)
                        except Exception as e:
                            logging.exception(msg=f"Wrong JSON argument format in LLM tool call response: {tool_call}")
                            history.append({"role": "tool", "tool_call_id": tool_call.id, "content": f"Tool call error: \n{tool_call}\nException:\n" + str(e)})
                            yield self._verbose_tool_use(name, {}, str(e))

                _lineaje_payload = f"Exceed max rounds: {self.max_rounds}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LiteLLMBase.async_chat_streamly_with_tools).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:e7106c54482560dd6c1fe9a38176a0c4ea065a7f97c7e12fb6a56cb148c500e2'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e7106c54482560dd6c1fe9a38176a0c4ea065a7f97c7e12fb6a56cb148c500e2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1564, 'function': 'LiteLLMBase.async_chat_streamly_with_tools'}, 'file': 'rag/llm/chat_model.py', 'line': 1564, 'function': 'async_chat_streamly_with_tools', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                history.append({"role": "user", "content": f"Exceed max rounds: {self.max_rounds}"})

                completion_args = self._construct_completion_args(history=history, stream=True, tools=True, **gen_conf)
                # LINEAJE: runtime guardrail checks `completion_args` as it flows from the agent to the LLM, before it is sent to the model (in LiteLLMBase.async_chat_streamly_with_tools).
                #   Detected: this statement moves data from the agent to the LLM with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates AI_AGENT_ACTIVITY_LOG, AI_APP_SEC_006, AI_APP_SEC_028, AI_APP_SEC_070 (+2 more); sensitive values in `completion_args` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:899d90405f1fba9f35504671d674baa4a99f1762e86f125fd129635e483007a9'
                _gr_client = _lineaje_load_gr_client()
                _lineaje_interaction_id = _gr_client.new_interaction_id()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:899d90405f1fba9f35504671d674baa4a99f1762e86f125fd129635e483007a9', phase='pre_model', boundary={'source': 'agent_message', 'sink': 'model'}, fail_mode='BLOCK', source_type='agent', destination_type='llm', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'LiteLLMBase.async_chat_streamly_with_tools', 'line': 1568}, 'file': 'rag/llm/chat_model.py', 'line': 1568, 'function': 'async_chat_streamly_with_tools', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:21c10ced9e74b3e5'}, interaction_id=_lineaje_interaction_id)
                try:
                    if not hasattr(_gr_client, 'enforce_request'):
                        __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_request (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                        raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_request")
                    completion_args = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_request(_gr_site, completion_args, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    raise
                response = await litellm.acompletion(
                    **completion_args,
                    drop_params=True,
                    timeout=self.timeout,
                )
                # LINEAJE: runtime guardrail checks `response` as it flows from the LLM to the agent, after the model replies (in LiteLLMBase.async_chat_streamly_with_tools).
                #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:1afeb0b8de22fed8afd7d11acdc3b5cd1db0ae4244a81f5e1f32e37340d02fd4'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1afeb0b8de22fed8afd7d11acdc3b5cd1db0ae4244a81f5e1f32e37340d02fd4', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'destination': {'entity_type': 'llm', 'name': 'Baichuan3-Turbo', 'provider': '', 'version': ''}, 'identity': {'app': {'name': 'ragflow', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo', 'version': 'main'}, 'destination': {'entity_type': 'aimodel', 'name': 'Baichuan3-Turbo', 'purl': 'pkg:aimodel/Baichuan3-Turbo@1.0.0', 'version': ''}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'function': 'LiteLLMBase.async_chat_streamly_with_tools', 'line': 1568}, 'file': 'rag/llm/chat_model.py', 'line': 1568, 'function': 'async_chat_streamly_with_tools', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'boundary_id': 'bnd:21c10ced9e74b3e5'}, interaction_id=locals().get('_lineaje_interaction_id'))
                try:
                    if not hasattr(_gr_client, 'enforce_reply'):
                        __import__("logging").getLogger("lineaje.gr_client").error("gr_stub_client.py predates enforce_reply (STUB_API 2): this site is NOT enforced; replace gr_stub_client.py with the current companion")
                        raise _gr_client.GuardrailUnavailableError("stale gr_stub_client.py: no enforce_reply")
                    response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce_reply(_gr_site, response, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass

                async for resp in response:
                    if not hasattr(resp, "choices") or not resp.choices:
                        continue
                    delta = resp.choices[0].delta
                    if not hasattr(delta, "content") or delta.content is None:
                        continue
                    tol = total_token_count_from_response(resp)
                    if not tol:
                        total_tokens += num_tokens_from_string(delta.content)
                    else:
                        total_tokens = tol
                    yield delta.content

                yield total_tokens
                return

            except Exception as e:
                e = await self._exceptions_async(e, attempt)
                if e:
                    yield e
                    yield total_tokens
                    return

        assert False, "Shouldn't be here."

    def _construct_completion_args(self, history, stream: bool, tools: bool, **kwargs):
        completion_args = {
            "model": self.model_name,
            "messages": history,
            "api_key": self.api_key,
            "num_retries": self.max_retries,
            **kwargs,
        }
        if stream:
            completion_args.update(
                {
                    "stream": stream,
                }
            )
        if tools and self.tools:
            completion_args.update(
                {
                    "tools": self.tools,
                    "tool_choice": "auto",
                }
            )
        if self.provider in FACTORY_DEFAULT_BASE_URL:
            completion_args.update({"api_base": self.base_url})
        elif self.provider == SupportedLiteLLMProvider.Bedrock:
            import boto3

            completion_args.pop("api_key", None)
            completion_args.pop("api_base", None)

            bedrock_key = json.loads(self.api_key)
            mode = bedrock_key.get("auth_mode")
            if not mode:
                _lineaje_payload = "Bedrock auth_mode is not provided in the key"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in LiteLLMBase._construct_completion_args).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:9bee9d635baac188bcb6694c5f579a768de8aa53647f8541941804eef75c310e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9bee9d635baac188bcb6694c5f579a768de8aa53647f8541941804eef75c310e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1631, 'function': 'LiteLLMBase._construct_completion_args'}, 'file': 'rag/llm/chat_model.py', 'line': 1631, 'function': '_construct_completion_args', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
                raise ValueError("Bedrock auth_mode must be provided in the key")

            bedrock_region = bedrock_key.get("bedrock_region")
            bedrock_credentials = {"bedrock_region": bedrock_region}

            if mode == "access_key_secret":
                bedrock_credentials["aws_access_key_id"] = bedrock_key.get("bedrock_ak")
                bedrock_credentials["aws_secret_access_key"] = bedrock_key.get("bedrock_sk")
            elif mode == "iam_role":
                aws_role_arn = bedrock_key.get("aws_role_arn")
                sts_client = boto3.client("sts", region_name=bedrock_region)
                resp = sts_client.assume_role(RoleArn=aws_role_arn, RoleSessionName="BedrockSession")
                creds = resp["Credentials"]
                bedrock_credentials["aws_access_key_id"] = creds["AccessKeyId"]
                bedrock_credentials["aws_secret_access_key"] = creds["SecretAccessKey"]
                bedrock_credentials["aws_session_token"] = creds["SessionToken"]

            completion_args.update(
                {
                    "bedrock_credentials": bedrock_credentials,
                }
            )

        elif self.provider == SupportedLiteLLMProvider.OpenRouter:
            if self.provider_order:

                def _to_order_list(x):
                    if x is None:
                        return []
                    if isinstance(x, str):
                        return [s.strip() for s in x.split(",") if s.strip()]
                    if isinstance(x, (list, tuple)):
                        return [str(s).strip() for s in x if str(s).strip()]
                    return []

                extra_body = {}
                provider_cfg = {}
                provider_order = _to_order_list(self.provider_order)
                provider_cfg["order"] = provider_order
                provider_cfg["allow_fallbacks"] = False
                extra_body["provider"] = provider_cfg
                completion_args.update({"extra_body": extra_body})
        elif self.provider == SupportedLiteLLMProvider.GPUStack:
            completion_args.update(
                {
                    "api_base": self.base_url,
                }
            )
        elif self.provider == SupportedLiteLLMProvider.Azure_OpenAI:
            completion_args.pop("api_key", None)
            completion_args.pop("api_base", None)
            completion_args.update(
                {
                    "api_key": self.api_key,
                    "api_base": self.base_url,
                    "api_version": self.api_version,
                }
            )

        # Ollama deployments commonly sit behind a reverse proxy that enforces
        # Bearer auth. Ensure the Authorization header is set when an API key
        # is provided, while respecting any user-supplied headers. #11350
        extra_headers = deepcopy(completion_args.get("extra_headers") or {})
        if self.provider == SupportedLiteLLMProvider.Ollama and self.api_key and "Authorization" not in extra_headers:
            extra_headers["Authorization"] = f"Bearer {self.api_key}"
        if extra_headers:
            completion_args["extra_headers"] = extra_headers
        # LINEAJE: runtime guardrail checks `completion_args` as it flows from the agent to the user interface, before it leaves the application (in LiteLLMBase._construct_completion_args).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `completion_args` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8c37bfb2a9ef8fee95981c728f4f673c769303db3c7de9c467097820564c22bd'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8c37bfb2a9ef8fee95981c728f4f673c769303db3c7de9c467097820564c22bd', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/chat_model.py', 'line': 1699, 'function': 'LiteLLMBase._construct_completion_args'}, 'file': 'rag/llm/chat_model.py', 'line': 1699, 'function': '_construct_completion_args', 'agent_name': 'LiteLLMBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            completion_args = _gr_client.enforce(_gr_site, completion_args, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return completion_args
