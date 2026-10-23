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
import copy
import re

from deepdoc.parser.figure_parser import vision_figure_parser_pdf_wrapper
from common.constants import ParserType
from rag.nlp import rag_tokenizer, tokenize, tokenize_table, add_positions, bullets_category, title_frequency, tokenize_chunks, attach_media_context
from deepdoc.parser import PdfParser
import numpy as np
from rag.app.naive import by_plaintext, PARSERS
from common.parser_config_utils import normalize_layout_recognizer


class Pdf(PdfParser):
    def __init__(self):
        self.model_speciess = ParserType.PAPER.value
        super().__init__()

    def __call__(self, filename, binary=None, from_page=0,
                 to_page=100000, zoomin=3, callback=None):
        from timeit import default_timer as timer
        start = timer()
        callback(msg="OCR started")
        self.__images__(
            filename if not binary else binary,
            zoomin,
            from_page,
            to_page,
            callback
        )
        callback(msg="OCR finished ({:.2f}s)".format(timer() - start))

        start = timer()
        self._layouts_rec(zoomin)
        callback(0.63, "Layout analysis ({:.2f}s)".format(timer() - start))
        _lineaje_payload = f"layouts cost: {timer() - start}s"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Pdf.__call__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d3e6978c7b6a1d3ecd424795a1d56f368aa4651e339a4039475736e2895199e1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d3e6978c7b6a1d3ecd424795a1d56f368aa4651e339a4039475736e2895199e1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/paper.py', 'line': 52, 'function': 'Pdf.__call__'}, 'file': 'rag/app/paper.py', 'line': 52, 'function': '__call__', 'agent_name': 'Pdf', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)

        start = timer()
        self._table_transformer_job(zoomin)
        callback(0.68, "Table analysis ({:.2f}s)".format(timer() - start))

        start = timer()
        self._text_merge()
        tbls = self._extract_table_figure(True, zoomin, True, True)
        column_width = np.median([b["x1"] - b["x0"] for b in self.boxes])
        self._concat_downward()
        self._filter_forpages()
        callback(0.75, "Text merged ({:.2f}s)".format(timer() - start))

        # clean mess
        if column_width < self.page_images[0].size[0] / zoomin / 2:
            _lineaje_payload = ("two_column................... {} {}".format(column_width,
                  self.page_images[0].size[0] / zoomin / 2))
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Pdf.__call__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:52ce5c793fd85ce9e7d20cf4be00a7fab6f8e8ea02f52145b489bc3b53a21070'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:52ce5c793fd85ce9e7d20cf4be00a7fab6f8e8ea02f52145b489bc3b53a21070', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/paper.py', 'line': 68, 'function': 'Pdf.__call__'}, 'file': 'rag/app/paper.py', 'line': 68, 'function': '__call__', 'agent_name': 'Pdf', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.debug(_lineaje_payload)
            self.boxes = self.sort_X_by_page(self.boxes, column_width / 2)
        for b in self.boxes:
            b["text"] = re.sub(r"([\t 　]|\u3000){2,}", " ", b["text"].strip())

        def _begin(txt):
            return re.match(
                "[0-9. 一、i]*(introduction|abstract|摘要|引言|keywords|key words|关键词|background|背景|目录|前言|contents)",
                txt.lower().strip())

        if from_page > 0:
            return {
                "title": "",
                "authors": "",
                "abstract": "",
                "sections": [(b["text"] + self._line_tag(b, zoomin), b.get("layoutno", "")) for b in self.boxes if
                             re.match(r"(text|title)", b.get("layoutno", "text"))],
                "tables": tbls
            }
        # get title and authors
        title = ""
        authors = []
        i = 0
        while i < min(32, len(self.boxes)-1):
            b = self.boxes[i]
            i += 1
            if b.get("layoutno", "").find("title") >= 0:
                title = b["text"]
                if _begin(title):
                    title = ""
                    break
                for j in range(3):
                    if _begin(self.boxes[i + j]["text"]):
                        break
                    authors.append(self.boxes[i + j]["text"])
                    break
                break
        # get abstract
        abstr = ""
        i = 0
        while i + 1 < min(32, len(self.boxes)):
            b = self.boxes[i]
            i += 1
            txt = b["text"].lower().strip()
            if re.match("(abstract|摘要)", txt):
                if len(txt.split()) > 32 or len(txt) > 64:
                    abstr = txt + self._line_tag(b, zoomin)
                    break
                txt = self.boxes[i]["text"].lower().strip()
                if len(txt.split()) > 32 or len(txt) > 64:
                    abstr = txt + self._line_tag(self.boxes[i], zoomin)
                i += 1
                break
        if not abstr:
            i = 0

        callback(
            0.8, "Page {}~{}: Text merging finished".format(
                from_page, min(
                    to_page, self.total_page)))
        for b in self.boxes:
            _lineaje_payload = "{} {}".format(b["text"], b.get("layoutno"))
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Pdf._begin).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:43acb2756db87f9b0a4a26c8b6affa4f60227df37b97ad3c912e5a3ea8508880'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:43acb2756db87f9b0a4a26c8b6affa4f60227df37b97ad3c912e5a3ea8508880', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/paper.py', 'line': 130, 'function': 'Pdf.__call__'}, 'file': 'rag/app/paper.py', 'line': 130, 'function': '_begin', 'agent_name': 'Pdf', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.debug(_lineaje_payload)
        _lineaje_payload = "{}".format(tbls)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Pdf.__call__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:29b565815d1463e6b0fb1c08c253f96454b9542436caebb2bf48ae0f520e72a5'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:29b565815d1463e6b0fb1c08c253f96454b9542436caebb2bf48ae0f520e72a5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/paper.py', 'line': 131, 'function': 'Pdf.__call__'}, 'file': 'rag/app/paper.py', 'line': 131, 'function': '__call__', 'agent_name': 'Pdf', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)

        return {
            "title": title,
            "authors": " ".join(authors),
            "abstract": abstr,
            "sections": [(b["text"] + self._line_tag(b, zoomin), b.get("layoutno", "")) for b in self.boxes[i:] if
                         re.match(r"(text|title)", b.get("layoutno", "text"))],
            "tables": tbls
        }


def chunk(filename, binary=None, from_page=0, to_page=100000,
          lang="Chinese", callback=None, **kwargs):
    """
        Only pdf is supported.
        The abstract of the paper will be sliced as an entire chunk, and will not be sliced partly.
    """
    parser_config = kwargs.get(
        "parser_config", {
            "chunk_token_num": 512, "delimiter": "\n!?。；！？", "layout_recognize": "DeepDOC"})
    if re.search(r"\.pdf$", filename, re.IGNORECASE):
        layout_recognizer, parser_model_name = normalize_layout_recognizer(
            parser_config.get("layout_recognize", "DeepDOC")
        )

        if isinstance(layout_recognizer, bool):
            layout_recognizer = "DeepDOC" if layout_recognizer else "Plain Text"

        name = layout_recognizer.strip().lower()
        pdf_parser = PARSERS.get(name, by_plaintext)
        callback(0.1, "Start to parse.")

        if name == "deepdoc":
            pdf_parser = Pdf()
            paper = pdf_parser(filename if not binary else binary,
                               from_page=from_page, to_page=to_page, callback=callback)
        else:
            kwargs.pop("parse_method", None)
            kwargs.pop("mineru_llm_name", None)
            sections, tables, pdf_parser = pdf_parser(
                filename=filename,
                binary=binary,
                from_page=from_page,
                to_page=to_page,
                lang=lang,
                callback=callback,
                pdf_cls=Pdf,
                layout_recognizer=layout_recognizer,
                mineru_llm_name=parser_model_name,
                parse_method="paper",
                **kwargs
            )

            paper = {
                "title": filename,
                "authors": " ",
                "abstract": "",
                "sections": sections,
                "tables": tables
            }

        tbls=paper["tables"]
        tbls=vision_figure_parser_pdf_wrapper(tbls=tbls,callback=callback,**kwargs)
        paper["tables"] = tbls
    else:
        raise NotImplementedError("file type not supported yet(pdf supported)")

    doc = {"docnm_kwd": filename, "authors_tks": rag_tokenizer.tokenize(paper["authors"]),
           "title_tks": rag_tokenizer.tokenize(paper["title"] if paper["title"] else filename)}
    doc["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(doc["title_tks"])
    doc["authors_sm_tks"] = rag_tokenizer.fine_grained_tokenize(doc["authors_tks"])
    # is it English
    eng = lang.lower() == "english"  # pdf_parser.is_english
    _lineaje_payload = "It's English.....{}".format(eng)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in chunk).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:d0cdc489b42395918a95ae90fc86175eda5e875ea292aa41869e0dd23c1d659c'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d0cdc489b42395918a95ae90fc86175eda5e875ea292aa41869e0dd23c1d659c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/paper.py', 'line': 205, 'function': 'chunk'}, 'file': 'rag/app/paper.py', 'line': 205, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.debug(_lineaje_payload)

    res = tokenize_table(paper["tables"], doc, eng)

    if paper["abstract"]:
        d = copy.deepcopy(doc)
        txt = pdf_parser.remove_tag(paper["abstract"])
        d["important_kwd"] = ["abstract", "总结", "概括", "summary", "summarize"]
        d["important_tks"] = " ".join(d["important_kwd"])
        d["image"], poss = pdf_parser.crop(
            paper["abstract"], need_position=True)
        add_positions(d, poss)
        tokenize(d, txt, eng)
        res.append(d)

    sorted_sections = paper["sections"]
    # set pivot using the most frequent type of title,
    # then merge between 2 pivot
    bull = bullets_category([txt for txt, _ in sorted_sections])
    most_level, levels = title_frequency(bull, sorted_sections)
    assert len(sorted_sections) == len(levels)
    sec_ids = []
    sid = 0
    for i, lvl in enumerate(levels):
        if lvl <= most_level and i > 0 and lvl != levels[i - 1]:
            sid += 1
        sec_ids.append(sid)
        _lineaje_payload = "{} {} {} {}".format(lvl, sorted_sections[i][0], most_level, sid)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in chunk).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e7791589ce23690102c0f4fd9fcd156bd8e7375b861dffd3268f932715d30e63'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e7791589ce23690102c0f4fd9fcd156bd8e7375b861dffd3268f932715d30e63', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/paper.py', 'line': 232, 'function': 'chunk'}, 'file': 'rag/app/paper.py', 'line': 232, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)

    chunks = []
    last_sid = -2
    for (txt, _), sec_id in zip(sorted_sections, sec_ids):
        if sec_id == last_sid:
            if chunks:
                chunks[-1] += "\n" + txt
                continue
        chunks.append(txt)
        last_sid = sec_id
    res.extend(tokenize_chunks(chunks, doc, eng, pdf_parser))
    table_ctx = max(0, int(parser_config.get("table_context_size", 0) or 0))
    image_ctx = max(0, int(parser_config.get("image_context_size", 0) or 0))
    if table_ctx or image_ctx:
        attach_media_context(res, table_ctx, image_ctx)
    # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in chunk).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:3047269eac8492ae477888dcaf3a801fd17c4a0b432948ac5a5220d6316c85d1'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3047269eac8492ae477888dcaf3a801fd17c4a0b432948ac5a5220d6316c85d1', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/paper.py', 'line': 248, 'function': 'chunk'}, 'file': 'rag/app/paper.py', 'line': 248, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return res


"""
    readed = [0] * len(paper["lines"])
    # find colon firstly
    i = 0
    while i + 1 < len(paper["lines"]):
        txt = pdf_parser.remove_tag(paper["lines"][i][0])
        j = i
        if txt.strip("\n").strip()[-1] not in ":：":
            i += 1
            continue
        i += 1
        while i < len(paper["lines"]) and not paper["lines"][i][0]:
            i += 1
        if i >= len(paper["lines"]): break
        proj = [paper["lines"][i][0].strip()]
        i += 1
        while i < len(paper["lines"]) and paper["lines"][i][0].strip()[0] == proj[-1][0]:
            proj.append(paper["lines"][i])
            i += 1
        for k in range(j, i): readed[k] = True
        txt = txt[::-1]
        if eng:
            r = re.search(r"(.*?) ([\\.;?!]|$)", txt)
            txt = r.group(1)[::-1] if r else txt[::-1]
        else:
            r = re.search(r"(.*?) ([。？；！]|$)", txt)
            txt = r.group(1)[::-1] if r else txt[::-1]
        for p in proj:
            d = copy.deepcopy(doc)
            txt += "\n" + pdf_parser.remove_tag(p)
            d["image"], poss = pdf_parser.crop(p, need_position=True)
            add_positions(d, poss)
            tokenize(d, txt, eng)
            res.append(d)

    i = 0
    chunk = []
    tk_cnt = 0
    def add_chunk():
        nonlocal chunk, res, doc, pdf_parser, tk_cnt
        d = copy.deepcopy(doc)
        ck = "\n".join(chunk)
        tokenize(d, pdf_parser.remove_tag(ck), pdf_parser.is_english)
        d["image"], poss = pdf_parser.crop(ck, need_position=True)
        add_positions(d, poss)
        res.append(d)
        chunk = []
        tk_cnt = 0

    while i < len(paper["lines"]):
        if tk_cnt > 128:
            add_chunk()
        if readed[i]:
            i += 1
            continue
        readed[i] = True
        txt, layouts = paper["lines"][i]
        txt_ = pdf_parser.remove_tag(txt)
        i += 1
        cnt = num_tokens_from_string(txt_)
        if any([
            layouts.find("title") >= 0 and chunk,
            cnt + tk_cnt > 128 and tk_cnt > 32,
        ]):
            add_chunk()
            chunk = [txt]
            tk_cnt = cnt
        else:
            chunk.append(txt)
            tk_cnt += cnt

    if chunk: add_chunk()
    for i, d in enumerate(res):
        print(d)
        # d["image"].save(f"./logs/{i}.jpg")
    return res
"""

if __name__ == "__main__":
    import sys

    def dummy(prog=None, msg=""):
        pass
    chunk(sys.argv[1], callback=dummy)
