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
import os
import time
from abc import ABC
from duckduckgo_search import DDGS
from agent.tools.base import ToolMeta, ToolParamBase, ToolBase
from common.connection_utils import timeout


class DuckDuckGoParam(ToolParamBase):
    """
    Define the DuckDuckGo component parameters.
    """

    def __init__(self):
        self.meta:ToolMeta = {
            "name": "duckduckgo_search",
            "description": "DuckDuckGo is a search engine focused on privacy. It offers search capabilities for web pages, images, and provides translation services. DuckDuckGo also features a private AI chat interface, providing users with an AI assistant that prioritizes data protection.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "The search keywords to execute with DuckDuckGo. The keywords should be the most important words/terms(includes synonyms) from the original request.",
                    "default": "{sys.query}",
                    "required": True
                },
                "channel": {
                    "type": "string",
                    "description": "default:general. The category of the search. `news` is useful for retrieving real-time updates, particularly about politics, sports, and major current events covered by mainstream media sources. `general` is for broader, more general-purpose searches that may include a wide range of sources.",
                    "enum": ["general", "news"],
                    "default": "general",
                    "required": False,
                },
            }
        }
        super().__init__()
        self.top_n = 10
        self.channel = "text"

    def check(self):
        self.check_positive_integer(self.top_n, "Top N")
        self.check_valid_value(self.channel, "Web Search or News", ["text", "news"])

    def get_input_form(self) -> dict[str, dict]:
        return {
            "query": {
                "name": "Query",
                "type": "line"
            },
            "channel": {
                "name": "Channel",
                "type": "options",
                "value": "general",
                "options": ["general", "news"]
            }
        }


class DuckDuckGo(ToolBase, ABC):
    component_name = "DuckDuckGo"

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 12)))
    def _invoke(self, **kwargs):
        if self.check_if_canceled("DuckDuckGo processing"):
            return

        if not kwargs.get("query"):
            self.set_output("formalized_content", "")
            return ""

        last_e = ""
        for _ in range(self._param.max_retries+1):
            if self.check_if_canceled("DuckDuckGo processing"):
                return

            try:
                if kwargs.get("topic", "general") == "general":
                    with DDGS() as ddgs:
                        if self.check_if_canceled("DuckDuckGo processing"):
                            return

                        # {'title': '', 'href': '', 'body': ''}
                        duck_res = ddgs.text(kwargs["query"], max_results=self._param.top_n)

                        if self.check_if_canceled("DuckDuckGo processing"):
                            return

                        self._retrieve_chunks(duck_res,
                                              get_title=lambda r: r["title"],
                                              get_url=lambda r: r.get("href", r.get("url")),
                                              get_content=lambda r: r["body"])
                        self.set_output("json", duck_res)
                        return self.output("formalized_content")
                else:
                    with DDGS() as ddgs:
                        if self.check_if_canceled("DuckDuckGo processing"):
                            return

                        # {'date': '', 'title': '', 'body': '', 'url': '', 'image': '', 'source': ''}
                        duck_res = ddgs.news(kwargs["query"], max_results=self._param.top_n)

                        if self.check_if_canceled("DuckDuckGo processing"):
                            return

                        self._retrieve_chunks(duck_res,
                                              get_title=lambda r: r["title"],
                                              get_url=lambda r: r.get("href", r.get("url")),
                                              get_content=lambda r: r["body"])
                        self.set_output("json", duck_res)
                        return self.output("formalized_content")
            except Exception as e:
                if self.check_if_canceled("DuckDuckGo processing"):
                    return

                last_e = e
                _lineaje_payload = f"DuckDuckGo error: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in DuckDuckGo._invoke).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:9c382bea05e7c082cec4ee06eeae0c6161aeafa336e58cdc5488e37e88ef769c'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9c382bea05e7c082cec4ee06eeae0c6161aeafa336e58cdc5488e37e88ef769c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/duckduckgo.py', 'line': 130, 'function': 'DuckDuckGo._invoke'}, 'file': 'agent/tools/duckduckgo.py', 'line': 130, 'function': '_invoke', 'agent_name': 'DuckDuckGo', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.exception(_lineaje_payload)
                time.sleep(self._param.delay_after_error)

        if last_e:
            self.set_output("_ERROR", str(last_e))
            return f"DuckDuckGo error: {last_e}"

        assert False, self.output()

    def thoughts(self) -> str:
        return """
Keywords: {}
Looking for the most relevant articles.
                """.format(self.get_input().get("query", "-_-!"))
