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

import _thread as thread
import base64
import hashlib
import hmac
import json
import queue
import re
import ssl
import time
from abc import ABC
from datetime import datetime
from time import mktime
from typing import Annotated, Literal
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time

import httpx
import ormsgpack
import requests
import websocket
from pydantic import BaseModel, conint

from common.token_utils import num_tokens_from_string


class ServeReferenceAudio(BaseModel):
    audio: bytes
    text: str


class ServeTTSRequest(BaseModel):
    text: str
    chunk_length: Annotated[int, conint(ge=100, le=300, strict=True)] = 200
    # Audio format
    format: Literal["wav", "pcm", "mp3"] = "mp3"
    mp3_bitrate: Literal[64, 128, 192] = 128
    # References audios for in-context learning
    references: list[ServeReferenceAudio] = []
    # Reference id
    # For example, if you want use https://fish.audio/m/7f92f8afb8ec43bf81429cc1c9199cb1/
    # Just pass 7f92f8afb8ec43bf81429cc1c9199cb1
    reference_id: str | None = None
    # Normalize text for en & zh, this increase stability for numbers
    normalize: bool = True
    # Balance mode will reduce latency to 300ms, but may decrease stability
    latency: Literal["normal", "balanced"] = "normal"


class Base(ABC):
    def __init__(self, key, model_name, base_url, **kwargs):
        """
        Abstract base class constructor.
        Parameters are not stored; subclasses should handle their own initialization.
        """
        pass

    def tts(self, audio):
        pass

    def normalize_text(self, text):
        return re.sub(r"(\*\*|##\d+\$\$|#)", "", text)


class FishAudioTTS(Base):
    _FACTORY_NAME = "Fish Audio"

    def __init__(self, key, model_name, base_url="https://api.fish.audio/v1/tts"):
        if not base_url:
            base_url = "https://api.fish.audio/v1/tts"
        key = json.loads(key)
        self.headers = {
            "api-key": key.get("fish_audio_ak"),
            "content-type": "application/msgpack",
        }
        self.ref_id = key.get("fish_audio_refid")
        self.base_url = base_url

    def tts(self, text):
        from http import HTTPStatus

        text = self.normalize_text(text)
        request = ServeTTSRequest(text=text, reference_id=self.ref_id)

        with httpx.Client() as client:
            try:
                with client.stream(
                    method="POST",
                    url=self.base_url,
                    content=ormsgpack.packb(request, option=ormsgpack.OPT_SERIALIZE_PYDANTIC),
                    headers=self.headers,
                    timeout=None,
                ) as response:
                    if response.status_code == HTTPStatus.OK:
                        for chunk in response.iter_bytes():
                            yield chunk
                    else:
                        response.raise_for_status()

                yield num_tokens_from_string(text)

            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"**ERROR**: {e}")


class QwenTTS(Base):
    _FACTORY_NAME = "Tongyi-Qianwen"

    def __init__(self, key, model_name, base_url=""):
        import dashscope

        self.model_name = model_name
        dashscope.api_key = key

    def tts(self, text):
        from collections import deque

        from dashscope.api_entities.dashscope_response import SpeechSynthesisResponse
        from dashscope.audio.tts import ResultCallback, SpeechSynthesisResult, SpeechSynthesizer

        class Callback(ResultCallback):
            def __init__(self) -> None:
                self.dque = deque()

            def _run(self):
                while True:
                    if not self.dque:
                        time.sleep(0)
                        continue
                    val = self.dque.popleft()
                    if val:
                        yield val
                    else:
                        break

            def on_open(self):
                pass

            def on_complete(self):
                self.dque.append(None)

            def on_error(self, response: SpeechSynthesisResponse):
                raise RuntimeError(str(response))

            def on_close(self):
                pass

            def on_event(self, result: SpeechSynthesisResult):
                if result.get_audio_frame() is not None:
                    self.dque.append(result.get_audio_frame())

        text = self.normalize_text(text)
        callback = Callback()
        SpeechSynthesizer.call(model=self.model_name, text=text, callback=callback, format="mp3")
        try:
            for data in callback._run():
                yield data
            yield num_tokens_from_string(text)

        except Exception as e:
            raise RuntimeError(f"**ERROR**: {e}")


class OpenAITTS(Base):
    _FACTORY_NAME = "OpenAI"

    def __init__(self, key, model_name="tts-1", base_url="https://api.openai.com/v1"):
        if not base_url:
            base_url = "https://api.openai.com/v1"
        self.api_key = key
        self.model_name = model_name
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def tts(self, text, voice="alloy"):
        text = self.normalize_text(text)
        payload = {"model": self.model_name, "voice": voice, "input": text}

        response = requests.post(f"{self.base_url}/audio/speech", headers=self.headers, json=payload, stream=True)
        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in OpenAITTS.tts).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:43488555787acaca5ec4702b37d2f4364ea881b67eb9b7ddfc1a8c83439b373c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:43488555787acaca5ec4702b37d2f4364ea881b67eb9b7ddfc1a8c83439b373c', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/tts_model.py', 'line': 194, 'function': 'OpenAITTS.tts'}, 'file': 'rag/llm/tts_model.py', 'line': 194, 'function': 'tts', 'agent_name': 'OpenAITTS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=194)
        except _gr_client.GuardrailUnavailableError:
            pass

        if response.status_code != 200:
            raise Exception(f"**Error**: {response.status_code}, {response.text}")
        for chunk in response.iter_content():
            if chunk:
                yield chunk


class SparkTTS(Base):
    _FACTORY_NAME = "XunFei Spark"
    STATUS_FIRST_FRAME = 0
    STATUS_CONTINUE_FRAME = 1
    STATUS_LAST_FRAME = 2

    def __init__(self, key, model_name, base_url=""):
        key = json.loads(key)
        self.APPID = key.get("spark_app_id", "xxxxxxx")
        self.APISecret = key.get("spark_api_secret", "xxxxxxx")
        self.APIKey = key.get("spark_api_key", "xxxxxx")
        self.model_name = model_name
        self.CommonArgs = {"app_id": self.APPID}
        self.audio_queue = queue.Queue()

    # 用来存储音频数据

    # 生成url
    def create_url(self):
        url = "wss://tts-api.xfyun.cn/v2/tts"
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        signature_sha = hmac.new(self.APISecret.encode("utf-8"), signature_origin.encode("utf-8"), digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding="utf-8")
        authorization_origin = 'api_key="%s", algorithm="%s", headers="%s", signature="%s"' % (self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(encoding="utf-8")
        v = {"authorization": authorization, "date": date, "host": "ws-api.xfyun.cn"}
        url = url + "?" + urlencode(v)
        # LINEAJE: runtime guardrail checks `url` as it flows from the agent to the user interface, before it leaves the application (in SparkTTS.create_url).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `url` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b6f9619e79b669aefde4feb92291c6913db5a082fc5ae22172e3754e42b88a6b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b6f9619e79b669aefde4feb92291c6913db5a082fc5ae22172e3754e42b88a6b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/tts_model.py', 'line': 234, 'function': 'SparkTTS.create_url'}, 'file': 'rag/llm/tts_model.py', 'line': 234, 'function': 'create_url', 'agent_name': 'SparkTTS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            url = _gr_client.enforce(_gr_site, url, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return url

    def tts(self, text):
        BusinessArgs = {"aue": "lame", "sfl": 1, "auf": "audio/L16;rate=16000", "vcn": self.model_name, "tte": "utf8"}
        Data = {"status": 2, "text": base64.b64encode(text.encode("utf-8")).decode("utf-8")}
        CommonArgs = {"app_id": self.APPID}
        audio_queue = self.audio_queue
        model_name = self.model_name

        class Callback:
            def __init__(self):
                self.audio_queue = audio_queue

            def on_message(self, ws, message):
                message = json.loads(message)
                code = message["code"]
                sid = message["sid"]
                audio = message["data"]["audio"]
                audio = base64.b64decode(audio)
                status = message["data"]["status"]
                if status == 2:
                    ws.close()
                if code != 0:
                    errMsg = message["message"]
                    raise Exception(f"sid:{sid} call error:{errMsg} code:{code}")
                else:
                    self.audio_queue.put(audio)

            def on_error(self, ws, error):
                raise Exception(error)

            def on_close(self, ws, close_status_code, close_msg):
                self.audio_queue.put(None)  # 放入 None 作为结束标志

            def on_open(self, ws):
                def run(*args):
                    d = {"common": CommonArgs, "business": BusinessArgs, "data": Data}
                    # LINEAJE: runtime guardrail checks `d` as it flows from the agent to an external endpoint, before it leaves the application (in Callback.run).
                    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `d` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:2375d7a13d69cefe534e42af26d226654c699181a17bff0fc8022a4cc43102a7'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2375d7a13d69cefe534e42af26d226654c699181a17bff0fc8022a4cc43102a7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/tts_model.py', 'line': 271, 'function': 'SparkTTS.tts.Callback.on_open.run'}, 'file': 'rag/llm/tts_model.py', 'line': 271, 'function': 'run', 'agent_name': 'Callback', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        d = _gr_client.enforce(_gr_site, d, content_type='application/json', variable_name='d', source_file=__file__, before_line=271)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    ws.send(json.dumps(d))

                thread.start_new_thread(run, ())

        wsUrl = self.create_url()
        websocket.enableTrace(False)
        a = Callback()
        ws = websocket.WebSocketApp(wsUrl, on_open=a.on_open, on_error=a.on_error, on_close=a.on_close, on_message=a.on_message)
        status_code = 0
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        while True:
            audio_chunk = self.audio_queue.get()
            if audio_chunk is None:
                if status_code == 0:
                    raise Exception(f"Fail to access model({model_name}) using the provided credentials. **ERROR**: Invalid APPID, API Secret, or API Key.")
                else:
                    break
            status_code = 1
            yield audio_chunk


class XinferenceTTS(Base):
    _FACTORY_NAME = "Xinference"

    def __init__(self, key, model_name, **kwargs):
        self.base_url = kwargs.get("base_url", None)
        self.model_name = model_name
        self.headers = {"accept": "application/json", "Content-Type": "application/json"}

    def tts(self, text, voice="中文女", stream=True):
        payload = {"model": self.model_name, "input": text, "voice": voice}

        response = requests.post(f"{self.base_url}/v1/audio/speech", headers=self.headers, json=payload, stream=stream)
        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in XinferenceTTS.tts).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:bac9b2a4f5fa2ee4dc44f574d568d3ddef82f3a7fb41cd9d8a76c6b9f3599414'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bac9b2a4f5fa2ee4dc44f574d568d3ddef82f3a7fb41cd9d8a76c6b9f3599414', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/tts_model.py', 'line': 303, 'function': 'XinferenceTTS.tts'}, 'file': 'rag/llm/tts_model.py', 'line': 303, 'function': 'tts', 'agent_name': 'XinferenceTTS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=303)
        except _gr_client.GuardrailUnavailableError:
            pass

        if response.status_code != 200:
            raise Exception(f"**Error**: {response.status_code}, {response.text}")

        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                yield chunk


class OllamaTTS(Base):
    def __init__(self, key, model_name="ollama-tts", base_url="https://api.ollama.ai/v1"):
        if not base_url:
            base_url = "https://api.ollama.ai/v1"
        self.model_name = model_name
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        if key and key != "x":
            self.headers["Authorization"] = f"Bearer {key}"

    def tts(self, text, voice="standard-voice"):
        payload = {"model": self.model_name, "voice": voice, "input": text}

        response = requests.post(f"{self.base_url}/audio/tts", headers=self.headers, json=payload, stream=True)
        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in OllamaTTS.tts).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8e175843a0832ee2fa73120c1b7e1d054213ac4008724afe71c6fa52b05528a1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8e175843a0832ee2fa73120c1b7e1d054213ac4008724afe71c6fa52b05528a1', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/tts_model.py', 'line': 326, 'function': 'OllamaTTS.tts'}, 'file': 'rag/llm/tts_model.py', 'line': 326, 'function': 'tts', 'agent_name': 'OllamaTTS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=326)
        except _gr_client.GuardrailUnavailableError:
            pass

        if response.status_code != 200:
            raise Exception(f"**Error**: {response.status_code}, {response.text}")

        for chunk in response.iter_content():
            if chunk:
                yield chunk


class GPUStackTTS(Base):
    _FACTORY_NAME = "GPUStack"

    def __init__(self, key, model_name, **kwargs):
        self.base_url = kwargs.get("base_url", None)
        self.api_key = key
        self.model_name = model_name
        self.headers = {"accept": "application/json", "Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

    def tts(self, text, voice="Chinese Female", stream=True):
        payload = {"model": self.model_name, "input": text, "voice": voice}

        response = requests.post(f"{self.base_url}/v1/audio/speech", headers=self.headers, json=payload, stream=stream)
        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in GPUStackTTS.tts).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6977ee77b1988d70d2755e06638c4c17acc4cb2eee511db4d0fc6456c91573ca'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6977ee77b1988d70d2755e06638c4c17acc4cb2eee511db4d0fc6456c91573ca', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/tts_model.py', 'line': 348, 'function': 'GPUStackTTS.tts'}, 'file': 'rag/llm/tts_model.py', 'line': 348, 'function': 'tts', 'agent_name': 'GPUStackTTS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=348)
        except _gr_client.GuardrailUnavailableError:
            pass

        if response.status_code != 200:
            raise Exception(f"**Error**: {response.status_code}, {response.text}")

        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                yield chunk


class SILICONFLOWTTS(Base):
    _FACTORY_NAME = "SILICONFLOW"

    def __init__(self, key, model_name="FunAudioLLM/CosyVoice2-0.5B", base_url="https://api.siliconflow.cn/v1"):
        if not base_url:
            base_url = "https://api.siliconflow.cn/v1"
        self.api_key = key
        self.model_name = model_name
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def tts(self, text, voice="anna"):
        text = self.normalize_text(text)
        payload = {
            "model": self.model_name,
            "input": text,
            "voice": f"{self.model_name}:{voice}",
            "response_format": "mp3",
            "sample_rate": 123,
            "stream": True,
            "speed": 1,
            "gain": 0,
        }

        response = requests.post(f"{self.base_url}/audio/speech", headers=self.headers, json=payload)
        # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in SILICONFLOWTTS.tts).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:95f5c3c8416296161fbe2895214d7e4aa70655230d1980c73878b760259119b9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:95f5c3c8416296161fbe2895214d7e4aa70655230d1980c73878b760259119b9', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/llm/tts_model.py', 'line': 382, 'function': 'SILICONFLOWTTS.tts'}, 'file': 'rag/llm/tts_model.py', 'line': 382, 'function': 'tts', 'agent_name': 'SILICONFLOWTTS', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=382)
        except _gr_client.GuardrailUnavailableError:
            pass

        if response.status_code != 200:
            raise Exception(f"**Error**: {response.status_code}, {response.text}")
        for chunk in response.iter_content():
            if chunk:
                yield chunk

class DeepInfraTTS(OpenAITTS):
    _FACTORY_NAME = "DeepInfra"

    def __init__(self, key, model_name, base_url="https://api.deepinfra.com/v1/openai", **kwargs):
        if not base_url:
            base_url = "https://api.deepinfra.com/v1/openai"
        super().__init__(key, model_name, base_url, **kwargs)
        
class CometAPITTS(OpenAITTS):
    _FACTORY_NAME = "CometAPI"

    def __init__(self, key, model_name, base_url="https://api.cometapi.com/v1", **kwargs):
        if not base_url:
            base_url = "https://api.cometapi.com/v1"
        super().__init__(key, model_name, base_url, **kwargs)
        
class DeerAPITTS(OpenAITTS):
    _FACTORY_NAME = "DeerAPI"

    def __init__(self, key, model_name, base_url="https://api.deerapi.com/v1", **kwargs):
        if not base_url:
            base_url = "https://api.deerapi.com/v1"
        super().__init__(key, model_name, base_url, **kwargs)
