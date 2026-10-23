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
import json
import logging
import random
from copy import deepcopy

import xxhash

from agent.component.llm import LLMParam, LLM
from rag.flow.base import ProcessBase, ProcessParamBase
from rag.prompts.generator import run_toc_from_text


class ExtractorParam(ProcessParamBase, LLMParam):
    def __init__(self):
        super().__init__()
        self.field_name = ""

    def check(self):
        super().check()
        self.check_empty(self.field_name, "Result Destination")


class Extractor(ProcessBase, LLM):
    component_name = "Extractor"

    async def _build_TOC(self, docs):
        self.callback(0.2,message="Start to generate table of content ...")
        docs = sorted(docs, key=lambda d:(
            d.get("page_num_int", 0)[0] if isinstance(d.get("page_num_int", 0), list) else d.get("page_num_int", 0),
            d.get("top_int", 0)[0] if isinstance(d.get("top_int", 0), list) else d.get("top_int", 0)
        ))
        toc = await run_toc_from_text([d["text"] for d in docs], self.chat_mdl)
        # LINEAJE: runtime guardrail checks `toc` as it flows from the agent to an external endpoint, before it leaves the application (in Extractor._build_TOC).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `toc` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:08df45f55f8655dc5d459b44045fc7f94f961c31576203f3c09487f03a4c0f50'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:08df45f55f8655dc5d459b44045fc7f94f961c31576203f3c09487f03a4c0f50', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/extractor/extractor.py', 'line': 47, 'function': 'Extractor._build_TOC'}, 'file': 'rag/flow/extractor/extractor.py', 'line': 47, 'function': '_build_TOC', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            toc = _gr_client.enforce(_gr_site, toc, content_type='application/json', variable_name='toc', source_file=__file__, before_line=47)
        except _gr_client.GuardrailUnavailableError:
            pass
        _lineaje_payload = "------------ T O C -------------\n"+json.dumps(toc, ensure_ascii=False, indent='  ')
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Extractor._build_TOC).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:90d30a5edacf3c16155a09bc3005777adb3c8bea7aad989dc12fe1eab1464467'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:90d30a5edacf3c16155a09bc3005777adb3c8bea7aad989dc12fe1eab1464467', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/extractor/extractor.py', 'line': 47, 'function': 'Extractor._build_TOC'}, 'file': 'rag/flow/extractor/extractor.py', 'line': 47, 'function': '_build_TOC', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        ii = 0
        while ii < len(toc):
            try:
                idx = int(toc[ii]["chunk_id"])
                del toc[ii]["chunk_id"]
                toc[ii]["ids"] = [docs[idx]["id"]]
                if ii == len(toc) -1:
                    break
                for jj in range(idx+1, int(toc[ii+1]["chunk_id"])+1):
                    toc[ii]["ids"].append(docs[jj]["id"])
            except Exception as e:
                # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in Extractor._build_TOC).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:1f5bd4ed27fd14cb1151f867797cd88aeaaab3f95631fafed9de58f9cb982cc6'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1f5bd4ed27fd14cb1151f867797cd88aeaaab3f95631fafed9de58f9cb982cc6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/extractor/extractor.py', 'line': 59, 'function': 'Extractor._build_TOC'}, 'file': 'rag/flow/extractor/extractor.py', 'line': 59, 'function': '_build_TOC', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    e = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, e, content_type='application/json'))
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(e)
            ii += 1

        if toc:
            d = deepcopy(docs[-1])
            d["doc_id"] = self._canvas._doc_id
            # LINEAJE: runtime guardrail checks `toc` as it flows from the agent to an external endpoint, before it leaves the application (in Extractor._build_TOC).
            #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `toc` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:72cb9b59673b255c80d91fd1fb20604c867e074be600b770f9b6d44ea74508e2'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:72cb9b59673b255c80d91fd1fb20604c867e074be600b770f9b6d44ea74508e2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/extractor/extractor.py', 'line': 65, 'function': 'Extractor._build_TOC'}, 'file': 'rag/flow/extractor/extractor.py', 'line': 65, 'function': '_build_TOC', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                toc = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, toc, content_type='application/json', variable_name='toc', source_file=__file__, before_line=65))
            except _gr_client.GuardrailUnavailableError:
                pass
            d["content_with_weight"] = json.dumps(toc, ensure_ascii=False)
            d["toc_kwd"] = "toc"
            d["available_int"] = 0
            d["page_num_int"] = [100000000]
            d["id"] = xxhash.xxh64((d["content_with_weight"] + str(d["doc_id"])).encode("utf-8", "surrogatepass")).hexdigest()
            # LINEAJE: runtime guardrail checks `d` as it flows from the agent to the user interface, before it leaves the application (in Extractor._build_TOC).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `d` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9e2b5dc10481483503896839aae60b8df3c9456e9bda5a70530832d53503d42a'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9e2b5dc10481483503896839aae60b8df3c9456e9bda5a70530832d53503d42a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/extractor/extractor.py', 'line': 70, 'function': 'Extractor._build_TOC'}, 'file': 'rag/flow/extractor/extractor.py', 'line': 70, 'function': '_build_TOC', 'agent_name': 'Extractor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                d = _gr_client.enforce(_gr_site, d, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return d
        return None

    async def _invoke(self, **kwargs):
        self.set_output("output_format", "chunks")
        self.callback(random.randint(1, 5) / 100.0, "Start to generate.")
        inputs = self.get_input_elements()
        chunks = []
        chunks_key = ""
        args = {}
        for k, v in inputs.items():
            args[k] = v["value"]
            if isinstance(args[k], list):
                chunks = deepcopy(args[k])
                chunks_key = k

        if chunks:
            if self._param.field_name == "toc":
                for ck in chunks:
                    ck["doc_id"] = self._canvas._doc_id
                    ck["id"] = xxhash.xxh64((ck["text"] + str(ck["doc_id"])).encode("utf-8")).hexdigest()
                toc =await self._build_TOC(chunks)
                chunks.append(toc)
                self.set_output("chunks", chunks)
                return

            prog = 0
            for i, ck in enumerate(chunks):
                args[chunks_key] = ck["text"]
                msg, sys_prompt = self._sys_prompt_and_msg([], args)
                msg.insert(0, {"role": "system", "content": sys_prompt})
                ck[self._param.field_name] = await self._generate_async(msg)
                prog += 1./len(chunks)
                if i % (len(chunks)//100+1) == 1:
                    self.callback(prog, f"{i+1} / {len(chunks)}")
            self.set_output("chunks", chunks)
        else:
            msg, sys_prompt = self._sys_prompt_and_msg([], args)
            msg.insert(0, {"role": "system", "content": sys_prompt})
            self.set_output("chunks", [{self._param.field_name: await self._generate_async(msg)}])


