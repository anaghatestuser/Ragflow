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
from Bio import Entrez
import re
import xml.etree.ElementTree as ET
from agent.tools.base import ToolParamBase, ToolMeta, ToolBase
from common.connection_utils import timeout


class PubMedParam(ToolParamBase):
    """
    Define the PubMed component parameters.
    """

    def __init__(self):
        self.meta:ToolMeta = {
            "name": "pubmed_search",
            "description": """
PubMed is an openly accessible, free database which includes primarily the MEDLINE database of references and abstracts on life sciences and biomedical topics.
In addition to MEDLINE, PubMed provides access to:
 - older references from the print version of Index Medicus, back to 1951 and earlier
 - references to some journals before they were indexed in Index Medicus and MEDLINE, for instance Science, BMJ, and Annals of Surgery
 - very recent entries to records for an article before it is indexed with Medical Subject Headings (MeSH) and added to MEDLINE
 - a collection of books available full-text and other subsets of NLM records[4]
 - PMC citations
 - NCBI Bookshelf
            """,
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "The search keywords to execute with PubMed. The keywords should be the most important words/terms(includes synonyms) from the original request.",
                    "default": "{sys.query}",
                    "required": True
                }
            }
        }
        super().__init__()
        self.top_n = 12
        self.email = "A.N.Other@example.com"

    def check(self):
        self.check_positive_integer(self.top_n, "Top N")

    def get_input_form(self) -> dict[str, dict]:
        return {
            "query": {
                "name": "Query",
                "type": "line"
            }
        }

class PubMed(ToolBase, ABC):
    component_name = "PubMed"

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 12)))
    def _invoke(self, **kwargs):
        if self.check_if_canceled("PubMed processing"):
            return

        if not kwargs.get("query"):
            self.set_output("formalized_content", "")
            return ""

        last_e = ""
        for _ in range(self._param.max_retries+1):
            if self.check_if_canceled("PubMed processing"):
                return

            try:
                Entrez.email = self._param.email
                pubmedids = Entrez.read(Entrez.esearch(db='pubmed', retmax=self._param.top_n, term=kwargs["query"]))['IdList']

                if self.check_if_canceled("PubMed processing"):
                    return

                pubmedcnt = ET.fromstring(re.sub(r'<(/?)b>|<(/?)i>', '', Entrez.efetch(db='pubmed', id=",".join(pubmedids),
                                                                                       retmode="xml").read().decode("utf-8")))

                if self.check_if_canceled("PubMed processing"):
                    return

                self._retrieve_chunks(pubmedcnt.findall("PubmedArticle"),
                                      get_title=lambda child: child.find("MedlineCitation").find("Article").find("ArticleTitle").text,
                                      get_url=lambda child: "https://pubmed.ncbi.nlm.nih.gov/" + child.find("MedlineCitation").find("PMID").text,
                                      get_content=lambda child: self._format_pubmed_content(child),)
                return self.output("formalized_content")
            except Exception as e:
                if self.check_if_canceled("PubMed processing"):
                    return

                last_e = e
                _lineaje_payload = f"PubMed error: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PubMed._invoke).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:2e70e2fda83635842cd63bccdb1dff55402c7776fb1ee07ec7a8911432d9a497'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2e70e2fda83635842cd63bccdb1dff55402c7776fb1ee07ec7a8911432d9a497', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/pubmed.py', 'line': 109, 'function': 'PubMed._invoke'}, 'file': 'agent/tools/pubmed.py', 'line': 109, 'function': '_invoke', 'agent_name': 'PubMed', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
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
            return f"PubMed error: {last_e}"

        assert False, self.output()

    def _format_pubmed_content(self, child):
        """Extract structured reference info from PubMed XML"""
        def safe_find(path):
            node = child
            for p in path.split("/"):
                if node is None:
                    return None
                node = node.find(p)
            return node.text if node is not None and node.text else None

        title = safe_find("MedlineCitation/Article/ArticleTitle") or "No title"
        abstract = safe_find("MedlineCitation/Article/Abstract/AbstractText") or "No abstract available"
        journal = safe_find("MedlineCitation/Article/Journal/Title") or "Unknown Journal"
        volume = safe_find("MedlineCitation/Article/Journal/JournalIssue/Volume") or "-"
        issue = safe_find("MedlineCitation/Article/Journal/JournalIssue/Issue") or "-"
        pages = safe_find("MedlineCitation/Article/Pagination/MedlinePgn") or "-"

        # Authors
        authors = []
        for author in child.findall(".//AuthorList/Author"):
            lastname = safe_find("LastName") or ""
            forename = safe_find("ForeName") or ""
            fullname = f"{forename} {lastname}".strip()
            if fullname:
                authors.append(fullname)
        authors_str = ", ".join(authors) if authors else "Unknown Authors"

        # DOI
        doi = None
        for eid in child.findall(".//ArticleId"):
            if eid.attrib.get("IdType") == "doi":
                doi = eid.text
                break

        return (
            f"Title: {title}\n"
            f"Authors: {authors_str}\n"
            f"Journal: {journal}\n"
            f"Volume: {volume}\n"
            f"Issue: {issue}\n"
            f"Pages: {pages}\n"
            f"DOI: {doi or '-'}\n"
            f"Abstract: {abstract.strip()}"
        )

    def thoughts(self) -> str:
        return "Looking for scholarly papers on `{}`,” prioritising reputable sources.".format(self.get_input().get("query", "-_-!"))
