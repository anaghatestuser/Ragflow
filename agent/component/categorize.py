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
import os
import re
from abc import ABC

from common.constants import LLMType
from api.db.services.llm_service import LLMBundle
from agent.component.llm import LLMParam, LLM
from common.connection_utils import timeout
from rag.llm.chat_model import ERROR_PREFIX


class CategorizeParam(LLMParam):

    """
    Define the categorize component parameters.
    """
    def __init__(self):
        super().__init__()
        self.category_description = {}
        self.query = "sys.query"
        self.message_history_window_size = 1
        self.update_prompt()

    def check(self):
        self.check_positive_integer(self.message_history_window_size, "[Categorize] Message window size > 0")
        self.check_empty(self.category_description, "[Categorize] Category examples")
        for k, v in self.category_description.items():
            if not k:
                raise ValueError("[Categorize] Category name can not be empty!")
            if not v.get("to"):
                raise ValueError(f"[Categorize] 'To' of category {k} can not be empty!")

    def get_input_form(self) -> dict[str, dict]:
        return {
            "query": {
                "type": "line",
                "name": "Query"
            }
        }

    def update_prompt(self):
        cate_lines = []
        for c, desc in self.category_description.items():
            for line in desc.get("examples", []):
                if not line:
                    continue
                cate_lines.append("USER: \"" + re.sub(r"\n", "    ", line, flags=re.DOTALL) + "\" → "+c)

        descriptions = []
        for c, desc in self.category_description.items():
            if desc.get("description"):
                descriptions.append(
                    "\n------\nCategory: {}\nDescription: {}".format(c, desc["description"]))

        self.sys_prompt = """
You are an advanced classification system that categorizes user questions into specific types. Analyze the input question and classify it into ONE of the following categories:
{}

Here's description of each category:
 - {}

---- Instructions ----
 - Consider both explicit mentions and implied context
 - Prioritize the most specific applicable category
 - Return only the category name without explanations
 - Use "Other" only when no other category fits

 """.format(
            "\n - ".join(list(self.category_description.keys())),
            "\n".join(descriptions)
        )

        if cate_lines:
            self.sys_prompt += """
---- Examples ----
{}
""".format("\n".join(cate_lines))


class Categorize(LLM, ABC):
    component_name = "Categorize"

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10*60)))
    async def _invoke_async(self, **kwargs):
        if self.check_if_canceled("Categorize processing"):
            return

        msg = self._canvas.get_history(self._param.message_history_window_size)
        if not msg:
            msg = [{"role": "user", "content": ""}]
        if kwargs.get("sys.query"):
            msg[-1]["content"] = kwargs["sys.query"]
            self.set_input_value("sys.query", kwargs["sys.query"])
        else:
            msg[-1]["content"] = self._canvas.get_variable_value(self._param.query)
            self.set_input_value(self._param.query, msg[-1]["content"])
        self._param.update_prompt()
        chat_mdl = LLMBundle(self._canvas.get_tenant_id(), LLMType.CHAT, self._param.llm_id)

        user_prompt = """
---- Real Data ----
{} →
""".format(" | ".join(["{}: \"{}\"".format(c["role"].upper(), re.sub(r"\n", "", c["content"], flags=re.DOTALL)) for c in msg]))

        if self.check_if_canceled("Categorize processing"):
            return

        ans = await chat_mdl.async_chat(self._param.sys_prompt, [{"role": "user", "content": user_prompt}], self._param.gen_conf())
        _lineaje_payload = f"input: {user_prompt}, answer: {str(ans)}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Categorize._invoke_async).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:487810849e2c5605649fa1e722d30027e2a25df41ef2758e14bc62e5469efe53'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:487810849e2c5605649fa1e722d30027e2a25df41ef2758e14bc62e5469efe53', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/categorize.py', 'line': 126, 'function': 'Categorize._invoke_async'}, 'file': 'agent/component/categorize.py', 'line': 126, 'function': '_invoke_async', 'agent_name': 'Categorize', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        if ERROR_PREFIX in ans:
            raise Exception(ans)

        if self.check_if_canceled("Categorize processing"):
            return

        # Count the number of times each category appears in the answer.
        category_counts = {}
        for c in self._param.category_description.keys():
            count = ans.lower().count(c.lower())
            category_counts[c] = count

        cpn_ids = list(self._param.category_description.items())[-1][1]["to"]
        max_category = list(self._param.category_description.keys())[0]
        if any(category_counts.values()):
            max_category = max(category_counts.items(), key=lambda x: x[1])[0]
            cpn_ids = self._param.category_description[max_category]["to"]

        self.set_output("category_name", max_category)
        self.set_output("_next", cpn_ids)

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10*60)))
    def _invoke(self, **kwargs):
        return asyncio.run(self._invoke_async(**kwargs))

    def thoughts(self) -> str:
        return "Which should it falls into {}? ...".format(",".join([f"`{c}`" for c, _ in self._param.category_description.items()]))
