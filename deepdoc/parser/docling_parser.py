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
from __future__ import annotations
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


import logging
import re
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from os import PathLike
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

import pdfplumber
from PIL import Image

try:
    from docling.document_converter import DocumentConverter
except Exception:
    DocumentConverter = None  

try:
    from deepdoc.parser.pdf_parser import RAGFlowPdfParser
except Exception:
    class RAGFlowPdfParser:  
        pass


class DoclingContentType(str, Enum):
    IMAGE = "image"
    TABLE = "table"
    TEXT = "text"
    EQUATION = "equation"


@dataclass
class _BBox:
    page_no: int  
    x0: float
    y0: float
    x1: float
    y1: float


class DoclingParser(RAGFlowPdfParser):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.page_images: list[Image.Image] = []
        self.page_from = 0
        self.page_to = 10_000
        self.outlines = []
   
        
    def check_installation(self) -> bool:
        if DocumentConverter is None:
            _lineaje_payload = "[Docling] 'docling' is not importable, please: pip install docling"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in DoclingParser.check_installation).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:4209ce494aa55792380020aea5601f1944acb81ab9d28fa36e769310816540c1'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4209ce494aa55792380020aea5601f1944acb81ab9d28fa36e769310816540c1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/docling_parser.py', 'line': 69, 'function': 'DoclingParser.check_installation'}, 'file': 'deepdoc/parser/docling_parser.py', 'line': 69, 'function': 'check_installation', 'agent_name': 'DoclingParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.warning(_lineaje_payload)
            return False
        try:
            _ = DocumentConverter()
            return True
        except Exception as e:
            _lineaje_payload = f"[Docling] init DocumentConverter failed: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in DoclingParser.check_installation).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1c0177f4291ca33aee51630488749639c66f22b8828b450df5b9166b476a9c21'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1c0177f4291ca33aee51630488749639c66f22b8828b450df5b9166b476a9c21', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/docling_parser.py', 'line': 75, 'function': 'DoclingParser.check_installation'}, 'file': 'deepdoc/parser/docling_parser.py', 'line': 75, 'function': 'check_installation', 'agent_name': 'DoclingParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.error(_lineaje_payload)
            return False

    def __images__(self, fnm, zoomin: int = 1, page_from=0, page_to=600, callback=None):
        self.page_from = page_from
        self.page_to = page_to
        try:
            opener = pdfplumber.open(fnm) if isinstance(fnm, (str, PathLike)) else pdfplumber.open(BytesIO(fnm))
            with opener as pdf:
                pages = pdf.pages[page_from:page_to]
                self.page_images = [p.to_image(resolution=72 * zoomin, antialias=True).original for p in pages]
        except Exception as e:
            self.page_images = []
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in DoclingParser.__images__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:284eacf88d25c089e742a93f73f197a48b44161847602b61659159f7b47f6b07'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:284eacf88d25c089e742a93f73f197a48b44161847602b61659159f7b47f6b07', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/docling_parser.py', 'line': 88, 'function': 'DoclingParser.__images__'}, 'file': 'deepdoc/parser/docling_parser.py', 'line': 88, 'function': '__images__', 'agent_name': 'DoclingParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                e = _gr_client.enforce(_gr_site, e, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.exception(e)

    def _make_line_tag(self,bbox: _BBox) -> str:
        if bbox is None:
            return ""
        x0,x1, top, bott = bbox.x0, bbox.x1, bbox.y0, bbox.y1
        if hasattr(self, "page_images") and self.page_images and len(self.page_images) >= bbox.page_no:
            _, page_height = self.page_images[bbox.page_no-1].size
            top, bott = page_height-top ,page_height-bott
        return "@@{}\t{:.1f}\t{:.1f}\t{:.1f}\t{:.1f}##".format(
            bbox.page_no, x0,x1, top, bott
        )

    @staticmethod
    def extract_positions(txt: str) -> list[tuple[list[int], float, float, float, float]]:
        poss = []
        for tag in re.findall(r"@@[0-9-]+\t[0-9.\t]+##", txt):
            pn, left, right, top, bottom = tag.strip("#").strip("@").split("\t")
            left, right, top, bottom = float(left), float(right), float(top), float(bottom)
            poss.append(([int(p) - 1 for p in pn.split("-")], left, right, top, bottom))
        # LINEAJE: runtime guardrail checks `poss` as it flows from the agent to the user interface, before it leaves the application (in DoclingParser.extract_positions).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `poss` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:bafc42433a3ec7e59648ce9658ede7e4f57f5a5aee55dd22a3d0a70badb6af9f'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bafc42433a3ec7e59648ce9658ede7e4f57f5a5aee55dd22a3d0a70badb6af9f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/docling_parser.py', 'line': 108, 'function': 'DoclingParser.extract_positions'}, 'file': 'deepdoc/parser/docling_parser.py', 'line': 108, 'function': 'extract_positions', 'agent_name': 'DoclingParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            poss = _gr_client.enforce(_gr_site, poss, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return poss

    def crop(self, text: str, ZM: int = 1, need_position: bool = False):
        imgs = []
        poss = self.extract_positions(text)
        if not poss:
            return (None, None) if need_position else None

        GAP = 6
        pos = poss[0]
        poss.insert(0, ([pos[0][0]], pos[1], pos[2], max(0, pos[3] - 120), max(pos[3] - GAP, 0)))
        pos = poss[-1]
        poss.append(([pos[0][-1]], pos[1], pos[2], min(self.page_images[pos[0][-1]].size[1], pos[4] + GAP), min(self.page_images[pos[0][-1]].size[1], pos[4] + 120)))
        positions = []
        for ii, (pns, left, right, top, bottom) in enumerate(poss):
            if bottom <= top:
                bottom = top + 4
            img0 = self.page_images[pns[0]]
            x0, y0, x1, y1 = int(left), int(top), int(right), int(min(bottom, img0.size[1]))
            
            crop0 = img0.crop((x0, y0, x1, y1))
            imgs.append(crop0)
            if 0 < ii < len(poss)-1:
                positions.append((pns[0] + self.page_from, x0, x1, y0, y1))
            remain_bottom = bottom - img0.size[1]
            for pn in pns[1:]:
                if remain_bottom <= 0:
                    break
                page = self.page_images[pn]
                x0, y0, x1, y1 = int(left), 0, int(right), int(min(remain_bottom, page.size[1]))
                cimgp = page.crop((x0, y0, x1, y1))
                imgs.append(cimgp)
                if 0 < ii < len(poss) - 1:
                    positions.append((pn + self.page_from, x0, x1, y0, y1))
                remain_bottom -= page.size[1]

        if not imgs:
            return (None, None) if need_position else None

        height = sum(i.size[1] + GAP for i in imgs)
        width = max(i.size[0] for i in imgs)
        pic = Image.new("RGB", (width, int(height)), (245, 245, 245))
        h = 0
        for ii, img in enumerate(imgs):
            if ii == 0 or ii + 1 == len(imgs):
                img = img.convert("RGBA")
                overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
                overlay.putalpha(128)
                img = Image.alpha_composite(img, overlay).convert("RGB")
            pic.paste(img, (0, int(h)))
            h += img.size[1] + GAP

        return (pic, positions) if need_position else pic

    def _iter_doc_items(self, doc) -> Iterable[tuple[str, Any, Optional[_BBox]]]:
        for t in getattr(doc, "texts", []):
            parent=getattr(t, "parent", "")
            ref=getattr(parent,"cref","")
            label=getattr(t, "label", "")
            if (label in ("section_header","text",) and ref in ("#/body",)) or label in ("list_item",):
                text = getattr(t, "text", "") or ""
                bbox = None
                if getattr(t, "prov", None):
                    pn = getattr(t.prov[0], "page_no", None)
                    bb = getattr(t.prov[0], "bbox", None)
                    bb = [getattr(bb, "l", None),getattr(bb, "t", None),getattr(bb, "r", None),getattr(bb, "b", None)]
                    if pn and bb and len(bb) == 4:
                        bbox = _BBox(page_no=int(pn), x0=bb[0], y0=bb[1], x1=bb[2], y1=bb[3])
                yield (DoclingContentType.TEXT.value, text, bbox)

        for item in getattr(doc, "texts", []):
            if getattr(item, "label", "") in ("FORMULA",):
                text = getattr(item, "text", "") or ""
                bbox = None
                if getattr(item, "prov", None):
                    pn = getattr(item.prov, "page_no", None)
                    bb = getattr(item.prov, "bbox", None)
                    bb = [getattr(bb, "l", None),getattr(bb, "t", None),getattr(bb, "r", None),getattr(bb, "b", None)]
                    if pn and bb and len(bb) == 4:
                        bbox = _BBox(int(pn), bb[0], bb[1], bb[2], bb[3])
                yield (DoclingContentType.EQUATION.value, text, bbox)

    def _transfer_to_sections(self, doc, parse_method: str) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []
        for typ, payload, bbox in self._iter_doc_items(doc):
            if typ == DoclingContentType.TEXT.value:
                section = payload.strip()
                if not section:
                    continue
            elif typ == DoclingContentType.EQUATION.value:
                section = payload.strip()
            else:
                continue
            
            tag = self._make_line_tag(bbox) if isinstance(bbox,_BBox) else ""
            if parse_method == "manual":
                sections.append((section, typ, tag))
            elif parse_method == "paper":
                sections.append((section + tag, typ))
            else:
                sections.append((section, tag))
        # LINEAJE: runtime guardrail checks `sections` as it flows from the agent to the user interface, before it leaves the application (in DoclingParser._transfer_to_sections).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `sections` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1273c1a581d394c58333b2f9e11794d9b2cbf68f9abb9908c6100d72cb929fc7'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1273c1a581d394c58333b2f9e11794d9b2cbf68f9abb9908c6100d72cb929fc7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/docling_parser.py', 'line': 209, 'function': 'DoclingParser._transfer_to_sections'}, 'file': 'deepdoc/parser/docling_parser.py', 'line': 209, 'function': '_transfer_to_sections', 'agent_name': 'DoclingParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            sections = _gr_client.enforce(_gr_site, sections, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return sections

    def cropout_docling_table(self, page_no: int, bbox: tuple[float, float, float, float], zoomin: int = 1):
        if not getattr(self, "page_images", None):
            return None, ""

        idx = (page_no - 1) - getattr(self, "page_from", 0)
        if idx < 0 or idx >= len(self.page_images):
            return None, ""

        page_img = self.page_images[idx]
        W, H = page_img.size
        left, top, right, bott = bbox

        x0 = float(left)
        y0 = float(H-top)
        x1 = float(right)
        y1 = float(H-bott)

        x0, y0 = max(0.0, min(x0, W - 1)), max(0.0, min(y0, H - 1))
        x1, y1 = max(x0 + 1.0, min(x1, W)), max(y0 + 1.0, min(y1, H))

        try:
            crop = page_img.crop((int(x0), int(y0), int(x1), int(y1))).convert("RGB")
        except Exception:
            return None, ""

        pos = (page_no-1 if page_no>0 else 0, x0, x1, y0, y1)
        return crop, [pos]

    def _transfer_to_tables(self, doc):
        tables = []
        for tab in getattr(doc, "tables", []):
            img = None
            positions = ""
            if getattr(tab, "prov", None):
                pn = getattr(tab.prov[0], "page_no", None)
                bb = getattr(tab.prov[0], "bbox", None)
                if pn is not None and bb is not None:
                    left = getattr(bb, "l", None)
                    top = getattr(bb, "t", None)
                    right = getattr(bb, "r", None)
                    bott = getattr(bb, "b", None)
                    if None not in (left, top, right, bott):
                        img, positions = self.cropout_docling_table(int(pn), (float(left), float(top), float(right), float(bott)))
            html = ""
            try:
                html = tab.export_to_html(doc=doc)
            except Exception:
                pass
            tables.append(((img, html), positions if positions else ""))
        for pic in getattr(doc, "pictures", []):
            img = None
            positions = ""
            if getattr(pic, "prov", None):
                pn = getattr(pic.prov[0], "page_no", None)
                bb = getattr(pic.prov[0], "bbox", None)
                if pn is not None and bb is not None:
                    left = getattr(bb, "l", None)
                    top = getattr(bb, "t", None)
                    right = getattr(bb, "r", None)
                    bott = getattr(bb, "b", None)
                    if None not in (left, top, right, bott):
                        img, positions = self.cropout_docling_table(int(pn), (float(left), float(top), float(right), float(bott)))
            captions = ""
            try:
                captions = pic.caption_text(doc=doc)
            except Exception:
                pass
            tables.append(((img, [captions]), positions if positions else ""))
        # LINEAJE: runtime guardrail checks `tables` as it flows from the agent to the user interface, before it leaves the application (in DoclingParser._transfer_to_tables).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `tables` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:19798f2c52e78a1613f7a76cfc42699987f93d545da07d050505e45170b6c969'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:19798f2c52e78a1613f7a76cfc42699987f93d545da07d050505e45170b6c969', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/docling_parser.py', 'line': 279, 'function': 'DoclingParser._transfer_to_tables'}, 'file': 'deepdoc/parser/docling_parser.py', 'line': 279, 'function': '_transfer_to_tables', 'agent_name': 'DoclingParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            tables = _gr_client.enforce(_gr_site, tables, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return tables

    def parse_pdf(
        self,
        filepath: str | PathLike[str],
        binary: BytesIO | bytes | None = None,
        callback: Optional[Callable] = None,
        *,
        output_dir: Optional[str] = None, 
        lang: Optional[str] = None,        
        method: str = "auto",             
        delete_output: bool = True,
        parse_method: str = "raw"     
    ):

        if not self.check_installation():
            raise RuntimeError("Docling not available, please install `docling`")

        if binary is not None:
            tmpdir = Path(output_dir) if output_dir else Path.cwd() / ".docling_tmp"
            tmpdir.mkdir(parents=True, exist_ok=True)
            name = Path(filepath).name or "input.pdf"
            tmp_pdf = tmpdir / name
            with open(tmp_pdf, "wb") as f:
                if isinstance(binary, (bytes, bytearray)):
                    # LINEAJE: runtime guardrail checks `binary` as it flows from the agent to a file, before it is written to disk (in DoclingParser.parse_pdf).
                    #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `binary` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:c36321d3f381726f8dd76157e4e954b40a3b5e3322ded5340f1f109576b74135'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c36321d3f381726f8dd76157e4e954b40a3b5e3322ded5340f1f109576b74135', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/docling_parser.py', 'line': 304, 'function': 'DoclingParser.parse_pdf'}, 'file': 'deepdoc/parser/docling_parser.py', 'line': 304, 'function': 'parse_pdf', 'agent_name': 'DoclingParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        binary = _gr_client.enforce(_gr_site, binary, content_type='application/json', variable_name='binary', source_file=__file__, before_line=304)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    f.write(binary)
                else:
                    _lineaje_payload = binary.getbuffer()
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to a file, before it is written to disk (in DoclingParser.parse_pdf).
                    #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:021af61777e99c79a8d4107cdeaafa3cb62d34e13fd947c907a5f02311b5b34c'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:021af61777e99c79a8d4107cdeaafa3cb62d34e13fd947c907a5f02311b5b34c', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/docling_parser.py', 'line': 306, 'function': 'DoclingParser.parse_pdf'}, 'file': 'deepdoc/parser/docling_parser.py', 'line': 306, 'function': 'parse_pdf', 'agent_name': 'DoclingParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=306)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    f.write(_lineaje_payload)
            src_path = tmp_pdf
        else:
            src_path = Path(filepath)
            if not src_path.exists():
                raise FileNotFoundError(f"PDF not found: {src_path}")

        if callback:
            callback(0.1, f"[Docling] Converting: {src_path}")

        try:
            self.__images__(str(src_path), zoomin=1)
        except Exception as e:
            _lineaje_payload = f"[Docling] render pages failed: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in DoclingParser.parse_pdf).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:dd2bfb15ce8c0b9738b31585373cc626fa4fe72e08c4ed30233c79fcb822b289'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dd2bfb15ce8c0b9738b31585373cc626fa4fe72e08c4ed30233c79fcb822b289', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/docling_parser.py', 'line': 319, 'function': 'DoclingParser.parse_pdf'}, 'file': 'deepdoc/parser/docling_parser.py', 'line': 319, 'function': 'parse_pdf', 'agent_name': 'DoclingParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            self.logger.warning(_lineaje_payload)

        conv = DocumentConverter()  
        conv_res = conv.convert(str(src_path))
        doc = conv_res.document
        if callback:
            callback(0.7, f"[Docling] Parsed doc: {getattr(doc, 'num_pages', 'n/a')} pages")

        sections = self._transfer_to_sections(doc, parse_method=parse_method)
        tables = self._transfer_to_tables(doc)

        if callback:
            callback(0.95, f"[Docling] Sections: {len(sections)}, Tables: {len(tables)}")

        if binary is not None and delete_output:
            try:
                Path(src_path).unlink(missing_ok=True)
            except Exception:
                pass

        if callback:
            callback(1.0, "[Docling] Done.")
        return sections, tables


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = DoclingParser()
    print("Docling available:", parser.check_installation())
    sections, tables = parser.parse_pdf(filepath="test_docling/toc.pdf", binary=None)
    print(len(sections), len(tables))
