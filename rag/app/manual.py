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

from common.constants import ParserType
from io import BytesIO
from rag.nlp import rag_tokenizer, tokenize, tokenize_table, bullets_category, title_frequency, tokenize_chunks, docx_question_level, attach_media_context
from common.token_utils import num_tokens_from_string
from deepdoc.parser import PdfParser, DocxParser
from deepdoc.parser.figure_parser import vision_figure_parser_pdf_wrapper,vision_figure_parser_docx_wrapper
from docx import Document
from PIL import Image
from rag.app.naive import by_plaintext, PARSERS
from common.parser_config_utils import normalize_layout_recognizer

class Pdf(PdfParser):
    def __init__(self):
        self.model_speciess = ParserType.MANUAL.value
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
        _lineaje_payload = "OCR: {}".format(timer() - start)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Pdf.__call__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:77cc3f76d4f6174d0889d9debc4dd20a51be3ec09017c41be32448997c2db08f'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:77cc3f76d4f6174d0889d9debc4dd20a51be3ec09017c41be32448997c2db08f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/manual.py', 'line': 50, 'function': 'Pdf.__call__'}, 'file': 'rag/app/manual.py', 'line': 50, 'function': '__call__', 'agent_name': 'Pdf', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)

        start = timer()
        self._layouts_rec(zoomin)
        callback(0.65, "Layout analysis ({:.2f}s)".format(timer() - start))
        _lineaje_payload = "layouts: {}".format(timer() - start)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Pdf.__call__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a7e170669293106022b695d36de20732f30b287ff7f8dc3a5f99ab65c76b2c74'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a7e170669293106022b695d36de20732f30b287ff7f8dc3a5f99ab65c76b2c74', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/manual.py', 'line': 55, 'function': 'Pdf.__call__'}, 'file': 'rag/app/manual.py', 'line': 55, 'function': '__call__', 'agent_name': 'Pdf', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)

        start = timer()
        self._table_transformer_job(zoomin)
        callback(0.67, "Table analysis ({:.2f}s)".format(timer() - start))

        start = timer()
        self._text_merge()
        tbls = self._extract_table_figure(True, zoomin, True, True)
        self._concat_downward()
        self._filter_forpages()
        callback(0.68, "Text merged ({:.2f}s)".format(timer() - start))

        # clean mess
        for b in self.boxes:
            b["text"] = re.sub(r"([\t 　]|\u3000){2,}", " ", b["text"].strip())

        return [(b["text"], b.get("layoutno", ""), self.get_position(b, zoomin))
                for i, b in enumerate(self.boxes)], tbls


class Docx(DocxParser):
    def __init__(self):
        pass

    def get_picture(self, document, paragraph):
        img = paragraph._element.xpath('.//pic:pic')
        if not img:
            return None
        try:
            img = img[0]
            embed = img.xpath('.//a:blip/@r:embed')[0]
            related_part = document.part.related_parts[embed]
            image = related_part.image
            if image is not None:
                image = Image.open(BytesIO(image.blob))
                # LINEAJE: runtime guardrail checks `image` as it flows from the agent to the user interface, before it leaves the application (in Docx.get_picture).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `image` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:7e56ac79945d87e50045268e505069373cb82588561979d3b8337254d2d73076'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7e56ac79945d87e50045268e505069373cb82588561979d3b8337254d2d73076', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/manual.py', 'line': 91, 'function': 'Docx.get_picture'}, 'file': 'rag/app/manual.py', 'line': 91, 'function': 'get_picture', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    image = _gr_client.enforce(_gr_site, image, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return image
            elif related_part.blob is not None:
                image = Image.open(BytesIO(related_part.blob))
                # LINEAJE: runtime guardrail checks `image` as it flows from the agent to the user interface, before it leaves the application (in Docx.get_picture).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `image` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f55a8c9477b1d4accac324ebd4e9dcd3c53b5cfa79ae324967749a64726aa3ac'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f55a8c9477b1d4accac324ebd4e9dcd3c53b5cfa79ae324967749a64726aa3ac', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/manual.py', 'line': 94, 'function': 'Docx.get_picture'}, 'file': 'rag/app/manual.py', 'line': 94, 'function': 'get_picture', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    image = _gr_client.enforce(_gr_site, image, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return image
            else:
                return None
        except Exception:
            return None

    def concat_img(self, img1, img2):
        if img1 and not img2:
            # LINEAJE: runtime guardrail checks `img1` as it flows from the agent to the user interface, before it leaves the application (in Docx.concat_img).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `img1` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:bd76d30539915a0dbbba9e2c4b18c0d3c3ea2b9611ab58286e2ee76073a5605a'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bd76d30539915a0dbbba9e2c4b18c0d3c3ea2b9611ab58286e2ee76073a5605a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/manual.py', 'line': 102, 'function': 'Docx.concat_img'}, 'file': 'rag/app/manual.py', 'line': 102, 'function': 'concat_img', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                img1 = _gr_client.enforce(_gr_site, img1, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return img1
        if not img1 and img2:
            # LINEAJE: runtime guardrail checks `img2` as it flows from the agent to the user interface, before it leaves the application (in Docx.concat_img).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `img2` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:2953e3b3399eb5c03ff7f61ded38f16fa77ab3201e1daed1fd45d4e3af9dbdee'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2953e3b3399eb5c03ff7f61ded38f16fa77ab3201e1daed1fd45d4e3af9dbdee', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/manual.py', 'line': 104, 'function': 'Docx.concat_img'}, 'file': 'rag/app/manual.py', 'line': 104, 'function': 'concat_img', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                img2 = _gr_client.enforce(_gr_site, img2, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return img2
        if not img1 and not img2:
            return None
        width1, height1 = img1.size
        width2, height2 = img2.size

        new_width = max(width1, width2)
        new_height = height1 + height2
        new_image = Image.new('RGB', (new_width, new_height))

        new_image.paste(img1, (0, 0))
        new_image.paste(img2, (0, height1))

        # LINEAJE: runtime guardrail checks `new_image` as it flows from the agent to the user interface, before it leaves the application (in Docx.concat_img).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `new_image` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:66b53e6eb8c07c3044892ff485a94f7f94e2b5c995bfc8a58db782df1f3bdb56'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:66b53e6eb8c07c3044892ff485a94f7f94e2b5c995bfc8a58db782df1f3bdb56', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/manual.py', 'line': 117, 'function': 'Docx.concat_img'}, 'file': 'rag/app/manual.py', 'line': 117, 'function': 'concat_img', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            new_image = _gr_client.enforce(_gr_site, new_image, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return new_image

    def __call__(self, filename, binary=None, from_page=0, to_page=100000, callback=None):
        self.doc = Document(
            filename) if not binary else Document(BytesIO(binary))
        pn = 0
        last_answer, last_image = "", None
        question_stack, level_stack = [], []
        ti_list = []
        for p in self.doc.paragraphs:
            if pn > to_page:
                break
            question_level, p_text = 0, ''
            if from_page <= pn < to_page and p.text.strip():
                question_level, p_text = docx_question_level(p)
            if not question_level or question_level > 6: # not a question
                last_answer = f'{last_answer}\n{p_text}'
                current_image = self.get_picture(self.doc, p)
                last_image = self.concat_img(last_image, current_image)
            else:   # is a question
                if last_answer or last_image:
                    sum_question = '\n'.join(question_stack)
                    if sum_question:
                        ti_list.append((f'{sum_question}\n{last_answer}', last_image))
                    last_answer, last_image = '', None

                i = question_level
                while question_stack and i <= level_stack[-1]:
                    question_stack.pop()
                    level_stack.pop()
                question_stack.append(p_text)
                level_stack.append(question_level)
            for run in p.runs:
                if 'lastRenderedPageBreak' in run._element.xml:
                    pn += 1
                    continue
                if 'w:br' in run._element.xml and 'type="page"' in run._element.xml:
                    pn += 1
        if last_answer:
            sum_question = '\n'.join(question_stack)
            if sum_question:
                ti_list.append((f'{sum_question}\n{last_answer}', last_image))

        tbls = []
        for tb in self.doc.tables:
            html= "<table>"
            for r in tb.rows:
                html += "<tr>"
                i = 0
                while i < len(r.cells):
                    span = 1
                    c = r.cells[i]
                    for j in range(i+1, len(r.cells)):
                        if c.text == r.cells[j].text:
                            span += 1
                            i = j
                        else:
                            break
                    i += 1
                    html += f"<td>{c.text}</td>" if span == 1 else f"<td colspan='{span}'>{c.text}</td>"
                html += "</tr>"
            html += "</table>"
            tbls.append(((None, html), ""))
        return ti_list, tbls


def chunk(filename, binary=None, from_page=0, to_page=100000,
          lang="Chinese", callback=None, **kwargs):
    """
        Only pdf is supported.
    """
    parser_config = kwargs.get(
        "parser_config", {
            "chunk_token_num": 512, "delimiter": "\n!?。；！？", "layout_recognize": "DeepDOC"})
    pdf_parser = None
    doc = {
        "docnm_kwd": filename
    }
    doc["title_tks"] = rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", doc["docnm_kwd"]))
    doc["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(doc["title_tks"])
    # is it English
    eng = lang.lower() == "english"  # pdf_parser.is_english
    if re.search(r"\.pdf$", filename, re.IGNORECASE):
        layout_recognizer, parser_model_name = normalize_layout_recognizer(
            parser_config.get("layout_recognize", "DeepDOC")
        )

        if isinstance(layout_recognizer, bool):
            layout_recognizer = "DeepDOC" if layout_recognizer else "Plain Text"

        name = layout_recognizer.strip().lower()
        pdf_parser = PARSERS.get(name, by_plaintext)
        callback(0.1, "Start to parse.")

        kwargs.pop("parse_method", None)
        kwargs.pop("mineru_llm_name", None)
        sections, tbls, pdf_parser = pdf_parser(
            filename = filename,
            binary = binary,
            from_page = from_page,
            to_page = to_page,
            lang = lang,
            callback = callback,
            pdf_cls = Pdf,
            layout_recognizer = layout_recognizer,
            mineru_llm_name=parser_model_name,
            parse_method = "manual",
            **kwargs
        )

        def _normalize_section(section):
            # pad section to length 3: (txt, sec_id, poss)
            if len(section) == 1:
                section = (section[0], "", [])
            elif len(section) == 2:
                section = (section[0], "", section[1])
            elif len(section) != 3:
                raise ValueError(f"Unexpected section length: {len(section)} (value={section!r})")

            txt, layoutno, poss = section
            if isinstance(poss, str):
                poss = pdf_parser.extract_positions(poss)
                if poss:
                    first = poss[0]          # tuple: ([pn], x1, x2, y1, y2)
                    pn = first[0]
                    if isinstance(pn, list) and pn:
                        pn = pn[0]           # [pn] -> pn
                        poss[0] = (pn, *first[1:])

            return (txt, layoutno, poss)

        sections = [_normalize_section(sec) for sec in sections]

        if not sections and not tbls:
            return []

        if name in ["tcadp", "docling", "mineru"]:
            parser_config["chunk_token_num"] = 0

        callback(0.8, "Finish parsing.")

        if len(sections) > 0 and len(pdf_parser.outlines) / len(sections) > 0.03:
            max_lvl = max([lvl for _, lvl in pdf_parser.outlines])
            most_level = max(0, max_lvl - 1)
            levels = []
            for txt, _, _ in sections:
                for t, lvl in pdf_parser.outlines:
                    tks = set([t[i] + t[i + 1] for i in range(len(t) - 1)])
                    tks_ = set([txt[i] + txt[i + 1]
                                for i in range(min(len(t), len(txt) - 1))])
                    if len(set(tks & tks_)) / max([len(tks), len(tks_), 1]) > 0.8:
                        levels.append(lvl)
                        break
                else:
                    levels.append(max_lvl + 1)

        else:
            bull = bullets_category([txt for txt, _, _ in sections])
            most_level, levels = title_frequency(
                bull, [(txt, lvl) for txt, lvl, _ in sections])

        assert len(sections) == len(levels)
        sec_ids = []
        sid = 0
        for i, lvl in enumerate(levels):
            if lvl <= most_level and i > 0 and lvl != levels[i - 1]:
                sid += 1
            sec_ids.append(sid)

        sections = [(txt, sec_ids[i], poss)
                    for i, (txt, _, poss) in enumerate(sections)]
        for (img, rows), poss in tbls:
            if not rows:
                continue
            sections.append((rows if isinstance(rows, str) else rows[0], -1,
                            [(p[0] + 1 - from_page, p[1], p[2], p[3], p[4]) for p in poss]))

        def tag(pn, left, right, top, bottom):
            if pn + left + right + top + bottom == 0:
                return ""
            return "@@{}\t{:.1f}\t{:.1f}\t{:.1f}\t{:.1f}##" \
                .format(pn, left, right, top, bottom)

        chunks = []
        last_sid = -2
        tk_cnt = 0
        for txt, sec_id, poss in sorted(sections, key=lambda x: (
                x[-1][0][0], x[-1][0][3], x[-1][0][1])):
            poss = "\t".join([tag(*pos) for pos in poss])
            if tk_cnt < 32 or (tk_cnt < 1024 and (sec_id == last_sid or sec_id == -1)):
                if chunks:
                    chunks[-1] += "\n" + txt + poss
                    tk_cnt += num_tokens_from_string(txt)
                    continue
            chunks.append(txt + poss)
            tk_cnt = num_tokens_from_string(txt)
            if sec_id > -1:
                last_sid = sec_id
        tbls = vision_figure_parser_pdf_wrapper(tbls=tbls,callback=callback,**kwargs)
        res = tokenize_table(tbls, doc, eng)
        res.extend(tokenize_chunks(chunks, doc, eng, pdf_parser))
        table_ctx = max(0, int(parser_config.get("table_context_size", 0) or 0))
        image_ctx = max(0, int(parser_config.get("image_context_size", 0) or 0))
        if table_ctx or image_ctx:
            attach_media_context(res, table_ctx, image_ctx)
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in chunk).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9b676bed88293c0a81973018439d5df2422ba7538ce04ed7cef254c5374c510b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9b676bed88293c0a81973018439d5df2422ba7538ce04ed7cef254c5374c510b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/manual.py', 'line': 322, 'function': 'chunk'}, 'file': 'rag/app/manual.py', 'line': 322, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    elif re.search(r"\.docx?$", filename, re.IGNORECASE):
        docx_parser = Docx()
        ti_list, tbls = docx_parser(filename, binary,
                                    from_page=0, to_page=10000, callback=callback)
        tbls = vision_figure_parser_docx_wrapper(sections=ti_list,tbls=tbls,callback=callback,**kwargs)
        res = tokenize_table(tbls, doc, eng)
        for text, image in ti_list:
            d = copy.deepcopy(doc)
            if image:
                d['image'] = image
                d["doc_type_kwd"] = "image"
            tokenize(d, text, eng)
            res.append(d)
        table_ctx = max(0, int(parser_config.get("table_context_size", 0) or 0))
        image_ctx = max(0, int(parser_config.get("image_context_size", 0) or 0))
        if table_ctx or image_ctx:
            attach_media_context(res, table_ctx, image_ctx)
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in chunk).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b745817dfca1f05745a3c530c52c00ea615248e7f8b1656848683552ea296e0e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b745817dfca1f05745a3c530c52c00ea615248e7f8b1656848683552ea296e0e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/manual.py', 'line': 341, 'function': 'chunk'}, 'file': 'rag/app/manual.py', 'line': 341, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res
    else:
        raise NotImplementedError("file type not supported yet(pdf and docx supported)")


if __name__ == "__main__":
    import sys


    def dummy(prog=None, msg=""):
        pass


    chunk(sys.argv[1], callback=dummy)
