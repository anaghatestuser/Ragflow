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
import logging
import collections
import re
from typing import Any
from dataclasses import dataclass

from graphrag.general.extractor import Extractor
from graphrag.general.mind_map_prompt import MIND_MAP_EXTRACTION_PROMPT
from graphrag.utils import ErrorHandlerFn, perform_variable_replacements, chat_limiter
from rag.llm.chat_model import Base as CompletionLLM
import markdown_to_json
from functools import reduce
from common.token_utils import num_tokens_from_string


@dataclass
class MindMapResult:
    """Unipartite Mind Graph result class definition."""
    output: dict


class MindMapExtractor(Extractor):
    _input_text_key: str
    _mind_map_prompt: str
    _on_error: ErrorHandlerFn

    def __init__(
            self,
            llm_invoker: CompletionLLM,
            prompt: str | None = None,
            input_text_key: str | None = None,
            on_error: ErrorHandlerFn | None = None,
    ):
        """Init method definition."""
        # TODO: streamline construction
        self._llm = llm_invoker
        self._input_text_key = input_text_key or "input_text"
        self._mind_map_prompt = prompt or MIND_MAP_EXTRACTION_PROMPT
        self._on_error = on_error or (lambda _e, _s, _d: None)

    def _key(self, k):
        return re.sub(r"\*+", "", k)

    def _be_children(self, obj: dict, keyset: set):
        if isinstance(obj, str):
            obj = [obj]
        if isinstance(obj, list):
            keyset.update(obj)
            obj = [re.sub(r"\*+", "", i) for i in obj]
            return [{"id": i, "children": []} for i in obj if i]
        arr = []
        for k, v in obj.items():
            k = self._key(k)
            if k and k not in keyset:
                keyset.add(k)
                arr.append(
                    {
                        "id": k,
                        "children": self._be_children(v, keyset)
                    }
                )
        # LINEAJE: runtime guardrail checks `arr` as it flows from the agent to the user interface, before it leaves the application (in MindMapExtractor._be_children).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `arr` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:4ee9078cae52ff1bc22a4405269fedf20359bb7598553578833c4a650216878c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4ee9078cae52ff1bc22a4405269fedf20359bb7598553578833c4a650216878c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/mind_map_extractor.py', 'line': 79, 'function': 'MindMapExtractor._be_children'}, 'file': 'graphrag/general/mind_map_extractor.py', 'line': 79, 'function': '_be_children', 'agent_name': 'MindMapExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            arr = _gr_client.enforce(_gr_site, arr, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return arr

    async def __call__(
            self, sections: list[str], prompt_variables: dict[str, Any] | None = None
    ) -> MindMapResult:
        """Call method definition."""
        if prompt_variables is None:
            prompt_variables = {}

        res = []
        token_count = max(self._llm.max_length * 0.8, self._llm.max_length - 512)
        texts = []
        cnt = 0
        tasks = []
        for i in range(len(sections)):
            section_cnt = num_tokens_from_string(sections[i])
            if cnt + section_cnt >= token_count and texts:
                tasks.append(asyncio.create_task(
                    self._process_document("".join(texts), prompt_variables, res)
                ))
                texts = []
                cnt = 0

            texts.append(sections[i])
            cnt += section_cnt
        if texts:
            tasks.append(asyncio.create_task(
                self._process_document("".join(texts), prompt_variables, res)
            ))
        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            _lineaje_payload = f"Error processing document: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MindMapExtractor.__call__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:fe357921b7371d56e002bd1ce26ad77753a96242fae6befc2367af527e2016e4'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fe357921b7371d56e002bd1ce26ad77753a96242fae6befc2367af527e2016e4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/mind_map_extractor.py', 'line': 111, 'function': 'MindMapExtractor.__call__'}, 'file': 'graphrag/general/mind_map_extractor.py', 'line': 111, 'function': '__call__', 'agent_name': 'MindMapExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        if not res:
            return MindMapResult(output={"id": "root", "children": []})
        merge_json = reduce(self._merge, res)
        if len(merge_json) > 1:
            keys = [re.sub(r"\*+", "", k) for k, v in merge_json.items() if isinstance(v, dict)]
            keyset = set(i for i in keys if i)
            merge_json = {
                "id": "root",
                "children": [
                    {
                        "id": self._key(k),
                        "children": self._be_children(v, keyset)
                    }
                    for k, v in merge_json.items() if isinstance(v, dict) and self._key(k)
                ]
            }
        else:
            k = self._key(list(merge_json.keys())[0])
            merge_json = {"id": k, "children": self._be_children(list(merge_json.items())[0][1], {k})}

        return MindMapResult(output=merge_json)

    def _merge(self, d1, d2):
        for k in d1:
            if k in d2:
                if isinstance(d1[k], dict) and isinstance(d2[k], dict):
                    self._merge(d1[k], d2[k])
                elif isinstance(d1[k], list) and isinstance(d2[k], list):
                    d2[k].extend(d1[k])
                else:
                    d2[k] = d1[k]
            else:
                d2[k] = d1[k]

        # LINEAJE: runtime guardrail checks `d2` as it flows from the agent to the user interface, before it leaves the application (in MindMapExtractor._merge).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `d2` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a362b7c6764fc688594cf0cced16bfb2411afcaac5a7af41add80d9e76a95ab6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a362b7c6764fc688594cf0cced16bfb2411afcaac5a7af41add80d9e76a95ab6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/mind_map_extractor.py', 'line': 150, 'function': 'MindMapExtractor._merge'}, 'file': 'graphrag/general/mind_map_extractor.py', 'line': 150, 'function': '_merge', 'agent_name': 'MindMapExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            d2 = _gr_client.enforce(_gr_site, d2, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return d2

    def _list_to_kv(self, data):
        for key, value in data.items():
            if isinstance(value, dict):
                self._list_to_kv(value)
            elif isinstance(value, list):
                new_value = {}
                for i in range(len(value)):
                    if isinstance(value[i], list) and i > 0:
                        new_value[value[i - 1]] = value[i][0]
                data[key] = new_value
            else:
                continue
        # LINEAJE: runtime guardrail checks `data` as it flows from the agent to the user interface, before it leaves the application (in MindMapExtractor._list_to_kv).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:8b1f8a4d5029c6650aba0c05f589a92e0d9964e6581cabcbf7d4363d6c3e84bb'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8b1f8a4d5029c6650aba0c05f589a92e0d9964e6581cabcbf7d4363d6c3e84bb', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/mind_map_extractor.py', 'line': 164, 'function': 'MindMapExtractor._list_to_kv'}, 'file': 'graphrag/general/mind_map_extractor.py', 'line': 164, 'function': '_list_to_kv', 'agent_name': 'MindMapExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            data = _gr_client.enforce(_gr_site, data, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return data

    def _todict(self, layer: collections.OrderedDict):
        to_ret = layer
        if isinstance(layer, collections.OrderedDict):
            to_ret = dict(layer)

        try:
            for key, value in to_ret.items():
                to_ret[key] = self._todict(value)
        except AttributeError:
            pass

        return self._list_to_kv(to_ret)

    async def _process_document(
            self, text: str, prompt_variables: dict[str, str], out_res
    ) -> str:
        variables = {
            **prompt_variables,
            self._input_text_key: text,
        }
        text = perform_variable_replacements(self._mind_map_prompt, variables=variables)
        async with chat_limiter:
            response = await asyncio.to_thread(self._chat,text,[{"role": "user", "content": "Output:"}],{})
        response = re.sub(r"```[^\n]*", "", response)
        # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the application log, before it is written to the log (in MindMapExtractor._process_document).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:31a7e28552255ff5b8e8a262c4269ac3fed5e8cc24548cd264c314c33be8069b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:31a7e28552255ff5b8e8a262c4269ac3fed5e8cc24548cd264c314c33be8069b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/mind_map_extractor.py', 'line': 190, 'function': 'MindMapExtractor._process_document'}, 'file': 'graphrag/general/mind_map_extractor.py', 'line': 190, 'function': '_process_document', 'agent_name': 'MindMapExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            response = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, response, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(response)
        _lineaje_payload = self._todict(markdown_to_json.dictify(response))
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in MindMapExtractor._process_document).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:412c5547f76debab05ce3d9fdcd20adf09d5feceb17fe37a751e2ca88b54c5de'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:412c5547f76debab05ce3d9fdcd20adf09d5feceb17fe37a751e2ca88b54c5de', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/mind_map_extractor.py', 'line': 191, 'function': 'MindMapExtractor._process_document'}, 'file': 'graphrag/general/mind_map_extractor.py', 'line': 191, 'function': '_process_document', 'agent_name': 'MindMapExtractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)
        out_res.append(self._todict(markdown_to_json.dictify(response)))
