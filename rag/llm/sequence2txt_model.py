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
import base64
import io
import json
import os
import re
from abc import ABC
import tempfile

import requests
from openai import OpenAI
from openai.lib.azure import AzureOpenAI

from common.token_utils import num_tokens_from_string


class Base(ABC):
    def __init__(self, key, model_name, **kwargs):
        """
        Abstract base class constructor.
        Parameters are not stored; initialization is left to subclasses.
        """
        pass

    def transcription(self, audio_path, **kwargs):
        audio_file = open(audio_path, "rb")
        # LINEAJE: runtime guardrail checks `audio_file` as it flows from file storage to the agent (in Base.transcription).
        #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `audio_file` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1a15b052d071571a257e2c48285ad22687e98d40e693604bda8088502c44b1cf'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1a15b052d071571a257e2c48285ad22687e98d40e693604bda8088502c44b1cf', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/sequence2txt_model.py', 'line': 40, 'function': 'Base.transcription'}, 'file': 'rag/llm/sequence2txt_model.py', 'line': 40, 'function': 'transcription', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            audio_file = _gr_client.enforce(_gr_site, audio_file, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        try:
            _lineaje_obs = _lineaje_load_gr_client()
            _lineaje_obs_site = _lineaje_obs.SiteDescriptor(site_id='site:sha256:fc533453567de047496b3191b7b8c2a6aa60eea3e7f4e19870f2ee0d34b4af82', phase='', boundary={}, fail_mode='ALLOW', source_type='agent', destination_type='llm', project='tree', organization='', components={'file': 'rag/llm/sequence2txt_model.py', 'line': 41, 'function': 'transcription', 'agent_name': 'Base', 'agent_name_source': 'inferred_from_class', 'call_target': 'self.client.audio.transcriptions.create', 'not_on_graph': True}, observe_only=True)
            _lineaje_obs.enforce(_lineaje_obs_site, {'activity': 'agent_to_llm'}, content_type='application/json')
        except Exception:
            pass
        transcription = self.client.audio.transcriptions.create(model=self.model_name, file=audio_file)
        return transcription.text.strip(), num_tokens_from_string(transcription.text.strip())

    def audio2base64(self, audio):
        if isinstance(audio, bytes):
            return base64.b64encode(audio).decode("utf-8")
        if isinstance(audio, io.BytesIO):
            return base64.b64encode(audio.getvalue()).decode("utf-8")
        raise TypeError("The input audio file should be in binary format.")


class GPTSeq2txt(Base):
    _FACTORY_NAME = "OpenAI"

    def __init__(self, key, model_name="whisper-1", base_url="https://api.openai.com/v1", **kwargs):
        if not base_url:
            base_url = "https://api.openai.com/v1"
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name


class QWenSeq2txt(Base):
    _FACTORY_NAME = "Tongyi-Qianwen"

    def __init__(self, key, model_name="qwen-audio-asr", **kwargs):
        import dashscope

        dashscope.api_key = key
        self.model_name = model_name

    def transcription(self, audio_path):
        import dashscope

        if audio_path.startswith("http"):
            audio_input = audio_path
        else:
            audio_input = f"file://{audio_path}"

        messages = [
            {
                "role": "system",
                "content": [{"text": ""}]
            },
            {
                "role": "user",
                "content": [{"audio": audio_input}]
            }
        ]

        resp = dashscope.MultiModalConversation.call(
            model=self.model_name,
            messages=messages,
            result_format="message",
            asr_options={
                "enable_lid": True,
                "enable_itn": False
            }
        )

        try:
            text = resp["output"]["choices"][0]["message"].content[0]["text"]
        except Exception as e:
            text = "**ERROR**: " + str(e)
        return text, num_tokens_from_string(text)

    def stream_transcription(self, audio_path):
        import dashscope

        if audio_path.startswith("http"):
            audio_input = audio_path
        else:
            audio_input = f"file://{audio_path}"

        messages = [
            {
                "role": "system",
                "content": [{"text": ""}]
            },
            {
                "role": "user",
                "content": [{"audio": audio_input}]
            }
        ]

        stream = dashscope.MultiModalConversation.call(
            model=self.model_name,
            messages=messages,
            result_format="message",
            stream=True,
            asr_options={
                "enable_lid": True,
                "enable_itn": False
            }
        )

        full = ""
        for chunk in stream:
            try:
                piece = chunk["output"]["choices"][0]["message"].content[0]["text"]
                full = piece
                yield {"event": "delta", "text": piece}
            except Exception as e:
                yield {"event": "error", "text": str(e)}

        yield {"event": "final", "text": full}

class AzureSeq2txt(Base):
    _FACTORY_NAME = "Azure-OpenAI"

    def __init__(self, key, model_name, lang="Chinese", **kwargs):
        self.client = AzureOpenAI(api_key=key, azure_endpoint=kwargs["base_url"], api_version="2024-02-01")
        self.model_name = model_name
        self.lang = lang


class XinferenceSeq2txt(Base):
    _FACTORY_NAME = "Xinference"

    def __init__(self, key, model_name="whisper-small", **kwargs):
        self.base_url = kwargs.get("base_url", None)
        self.model_name = model_name
        self.key = key

    def transcription(self, audio, language="zh", prompt=None, response_format="json", temperature=0.7):
        if isinstance(audio, str):
            audio_file = open(audio, "rb")
            # LINEAJE: runtime guardrail checks `audio_file` as it flows from file storage to the agent (in XinferenceSeq2txt.transcription).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `audio_file` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e4e7cec7a774bef2ce282b0f947a41333c95b15796da105bc341d4715fbf7a29'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e4e7cec7a774bef2ce282b0f947a41333c95b15796da105bc341d4715fbf7a29', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/sequence2txt_model.py', 'line': 166, 'function': 'XinferenceSeq2txt.transcription'}, 'file': 'rag/llm/sequence2txt_model.py', 'line': 166, 'function': 'transcription', 'agent_name': 'XinferenceSeq2txt', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                audio_file = _gr_client.enforce(_gr_site, audio_file, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            audio_data = audio_file.read()
            # LINEAJE: runtime guardrail checks `audio_data` as it flows from file storage to the agent (in XinferenceSeq2txt.transcription).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `audio_data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:a7a1102e573238f03af3d3616d77d3e5bc35d3de928d494311320a37deceb884'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a7a1102e573238f03af3d3616d77d3e5bc35d3de928d494311320a37deceb884', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/sequence2txt_model.py', 'line': 167, 'function': 'XinferenceSeq2txt.transcription'}, 'file': 'rag/llm/sequence2txt_model.py', 'line': 167, 'function': 'transcription', 'agent_name': 'XinferenceSeq2txt', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                audio_data = _gr_client.enforce(_gr_site, audio_data, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            audio_file_name = audio.split("/")[-1]
        else:
            audio_data = audio
            audio_file_name = "audio.wav"

        payload = {"model": self.model_name, "language": language, "prompt": prompt, "response_format": response_format, "temperature": temperature}

        files = {"file": (audio_file_name, audio_data, "audio/wav")}

        try:
            response = requests.post(f"{self.base_url}/v1/audio/transcriptions", files=files, data=payload)
            # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in XinferenceSeq2txt.transcription).
            #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:591a08d82b66cc0453308f11a7dfc9c2c768271f1993c006d4bc08f74186db85'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:591a08d82b66cc0453308f11a7dfc9c2c768271f1993c006d4bc08f74186db85', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/sequence2txt_model.py', 'line': 178, 'function': 'XinferenceSeq2txt.transcription'}, 'file': 'rag/llm/sequence2txt_model.py', 'line': 178, 'function': 'transcription', 'agent_name': 'XinferenceSeq2txt', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=178)
            except _gr_client.GuardrailUnavailableError:
                pass
            response.raise_for_status()
            result = response.json()

            if "text" in result:
                transcription_text = result["text"].strip()
                return transcription_text, num_tokens_from_string(transcription_text)
            else:
                return "**ERROR**: Failed to retrieve transcription.", 0

        except requests.exceptions.RequestException as e:
            return f"**ERROR**: {str(e)}", 0


class TencentCloudSeq2txt(Base):
    _FACTORY_NAME = "Tencent Cloud"

    def __init__(self, key, model_name="16k_zh", base_url="https://asr.tencentcloudapi.com"):
        from tencentcloud.asr.v20190614 import asr_client
        from tencentcloud.common import credential

        key = json.loads(key)
        sid = key.get("tencent_cloud_sid", "")
        sk = key.get("tencent_cloud_sk", "")
        cred = credential.Credential(sid, sk)
        self.client = asr_client.AsrClient(cred, "")
        self.model_name = model_name

    def transcription(self, audio, max_retries=60, retry_interval=5):
        import time

        from tencentcloud.asr.v20190614 import models
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
            TencentCloudSDKException,
        )

        b64 = self.audio2base64(audio)
        try:
            # dispatch disk
            req = models.CreateRecTaskRequest()
            params = {
                "EngineModelType": self.model_name,
                "ChannelNum": 1,
                "ResTextFormat": 0,
                "SourceType": 1,
                "Data": b64,
            }
            # LINEAJE: runtime guardrail checks `params` as it flows from the agent to an external endpoint, before it leaves the application (in TencentCloudSeq2txt.transcription).
            #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `params` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:35fbc8034f75dde7cef631efa9efa12328fb5e205930eb3cf2277d1d54c370d6'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:35fbc8034f75dde7cef631efa9efa12328fb5e205930eb3cf2277d1d54c370d6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/sequence2txt_model.py', 'line': 225, 'function': 'TencentCloudSeq2txt.transcription'}, 'file': 'rag/llm/sequence2txt_model.py', 'line': 225, 'function': 'transcription', 'agent_name': 'TencentCloudSeq2txt', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                params = _gr_client.enforce(_gr_site, params, content_type='application/json', variable_name='params', source_file=__file__, before_line=225)
            except _gr_client.GuardrailUnavailableError:
                pass
            req.from_json_string(json.dumps(params))
            resp = self.client.CreateRecTask(req)

            # loop query
            req = models.DescribeTaskStatusRequest()
            params = {"TaskId": resp.Data.TaskId}
            # LINEAJE: runtime guardrail checks `params` as it flows from the agent to an external endpoint, before it leaves the application (in TencentCloudSeq2txt.transcription).
            #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `params` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:4169d5c35c26c94646149164d3720e5a6d2cfeb43dc9b8cad78b4fdad9af230b'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4169d5c35c26c94646149164d3720e5a6d2cfeb43dc9b8cad78b4fdad9af230b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/sequence2txt_model.py', 'line': 231, 'function': 'TencentCloudSeq2txt.transcription'}, 'file': 'rag/llm/sequence2txt_model.py', 'line': 231, 'function': 'transcription', 'agent_name': 'TencentCloudSeq2txt', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                params = _gr_client.enforce(_gr_site, params, content_type='application/json', variable_name='params', source_file=__file__, before_line=231)
            except _gr_client.GuardrailUnavailableError:
                pass
            req.from_json_string(json.dumps(params))
            retries = 0
            while retries < max_retries:
                resp = self.client.DescribeTaskStatus(req)
                if resp.Data.StatusStr == "success":
                    text = re.sub(r"\[\d+:\d+\.\d+,\d+:\d+\.\d+\]\s*", "", resp.Data.Result).strip()
                    return text, num_tokens_from_string(text)
                elif resp.Data.StatusStr == "failed":
                    return (
                        "**ERROR**: Failed to retrieve speech recognition results.",
                        0,
                    )
                else:
                    time.sleep(retry_interval)
                    retries += 1
            return "**ERROR**: Max retries exceeded. Task may still be processing.", 0

        except TencentCloudSDKException as e:
            return "**ERROR**: " + str(e), 0
        except Exception as e:
            return "**ERROR**: " + str(e), 0


class GPUStackSeq2txt(Base):
    _FACTORY_NAME = "GPUStack"

    def __init__(self, key, model_name, base_url):
        if not base_url:
            raise ValueError("url cannot be None")
        if base_url.split("/")[-1] != "v1":
            base_url = os.path.join(base_url, "v1")
        self.base_url = base_url
        self.model_name = model_name
        self.key = key


class GiteeSeq2txt(Base):
    _FACTORY_NAME = "GiteeAI"

    def __init__(self, key, model_name="whisper-1", base_url="https://ai.gitee.com/v1/", **kwargs):
        if not base_url:
            base_url = "https://ai.gitee.com/v1/"
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name


class DeepInfraSeq2txt(Base):
    _FACTORY_NAME = "DeepInfra"

    def __init__(self, key, model_name, base_url="https://api.deepinfra.com/v1/openai", **kwargs):
        if not base_url:
            base_url = "https://api.deepinfra.com/v1/openai"

        self.client = OpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name


class CometAPISeq2txt(Base):
    _FACTORY_NAME = "CometAPI"

    def __init__(self, key, model_name="whisper-1", base_url="https://api.cometapi.com/v1", **kwargs):
        if not base_url:
            base_url = "https://api.cometapi.com/v1"
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name


class DeerAPISeq2txt(Base):
    _FACTORY_NAME = "DeerAPI"

    def __init__(self, key, model_name="whisper-1", base_url="https://api.deerapi.com/v1", **kwargs):
        if not base_url:
            base_url = "https://api.deerapi.com/v1"
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name


class ZhipuSeq2txt(Base):
    _FACTORY_NAME = "ZHIPU-AI"

    def __init__(self, key, model_name="glm-asr", base_url="https://open.bigmodel.cn/api/paas/v4", **kwargs):
        if not base_url:
            base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.base_url = base_url
        self.api_key = key
        self.model_name = model_name
        self.gen_conf = kwargs.get("gen_conf", {})
        self.stream = kwargs.get("stream", False)

    def _convert_to_wav(self, input_path):
        ext = os.path.splitext(input_path)[1].lower()
        if ext in [".wav", ".mp3"]:
            # LINEAJE: runtime guardrail checks `input_path` as it flows from the agent to the user interface, before it leaves the application (in ZhipuSeq2txt._convert_to_wav).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `input_path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:99ebee2d3a840d0a0250fad68efb99c190eee4ea31d1ee7f9d92880ae0b2856e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:99ebee2d3a840d0a0250fad68efb99c190eee4ea31d1ee7f9d92880ae0b2856e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/sequence2txt_model.py', 'line': 323, 'function': 'ZhipuSeq2txt._convert_to_wav'}, 'file': 'rag/llm/sequence2txt_model.py', 'line': 323, 'function': '_convert_to_wav', 'agent_name': 'ZhipuSeq2txt', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                input_path = _gr_client.enforce(_gr_site, input_path, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return input_path
        fd, out_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            import ffmpeg
            import imageio_ffmpeg as ffmpeg_exe
            ffmpeg_path = ffmpeg_exe.get_ffmpeg_exe()
            (
                ffmpeg
                .input(input_path)
                .output(out_path, ar=16000, ac=1)
                .overwrite_output()
                .run(cmd=ffmpeg_path,quiet=True)
            )
            # LINEAJE: runtime guardrail checks `out_path` as it flows from the agent to the user interface, before it leaves the application (in ZhipuSeq2txt._convert_to_wav).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `out_path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f83fb278916c9df6c16e5ea5b3c5fdf8e1778c773e829acd4d3cc4f7cf4daa06'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f83fb278916c9df6c16e5ea5b3c5fdf8e1778c773e829acd4d3cc4f7cf4daa06', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/sequence2txt_model.py', 'line': 337, 'function': 'ZhipuSeq2txt._convert_to_wav'}, 'file': 'rag/llm/sequence2txt_model.py', 'line': 337, 'function': '_convert_to_wav', 'agent_name': 'ZhipuSeq2txt', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                out_path = _gr_client.enforce(_gr_site, out_path, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return out_path
        except Exception as e:
            raise RuntimeError(f"audio convert failed: {e}")

    def transcription(self, audio_path):
        payload = {
            "model": self.model_name,
            "temperature": str(self.gen_conf.get("temperature", 0.75)) or "0.75",
            "stream": self.stream,
        }

        headers = {"Authorization": f"Bearer {self.api_key}"}
        converted = self._convert_to_wav(audio_path)

        with open(converted, "rb") as audio_file:
            # LINEAJE: runtime guardrail checks `audio_file` as it flows from file storage to the agent (in ZhipuSeq2txt.transcription).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `audio_file` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:384610e25343b573f5916bfbd02e0d48269bda91608297323bcd27ad96cb56d1'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:384610e25343b573f5916bfbd02e0d48269bda91608297323bcd27ad96cb56d1', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/sequence2txt_model.py', 'line': 352, 'function': 'ZhipuSeq2txt.transcription'}, 'file': 'rag/llm/sequence2txt_model.py', 'line': 352, 'function': 'transcription', 'agent_name': 'ZhipuSeq2txt', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                audio_file = _gr_client.enforce(_gr_site, audio_file, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            files = {"file": audio_file}

            try:
                response = requests.post(
                    url=f"{self.base_url}/audio/transcriptions",
                    data=payload,
                    files=files,
                    headers=headers,
                )
                # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in ZhipuSeq2txt.transcription).
                #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:2b6f7b58684d9d7278a0a7c780bbd8a1bcb9a6df3b892470124eb94d4d99213e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2b6f7b58684d9d7278a0a7c780bbd8a1bcb9a6df3b892470124eb94d4d99213e', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/sequence2txt_model.py', 'line': 355, 'function': 'ZhipuSeq2txt.transcription'}, 'file': 'rag/llm/sequence2txt_model.py', 'line': 355, 'function': 'transcription', 'agent_name': 'ZhipuSeq2txt', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=355)
                except _gr_client.GuardrailUnavailableError:
                    pass
                body = response.json()
                if response.status_code == 200:
                    full_content = body["text"]
                    return full_content, num_tokens_from_string(full_content)
                else:
                    error = body["error"]
                    return f"**ERROR**: code: {error['code']}, message: {error['message']}", 0
            except Exception as e:
                return "**ERROR**: " + str(e), 0
