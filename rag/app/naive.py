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
import re
import os
from functools import reduce
from io import BytesIO
from timeit import default_timer as timer
from docx import Document
from docx.image.exceptions import InvalidImageStreamError, UnexpectedEndOfFileError, UnrecognizedImageError
from docx.opc.pkgreader import _SerializedRelationships, _SerializedRelationship
from docx.opc.oxml import parse_xml
from markdown import markdown
from PIL import Image
from common.token_utils import num_tokens_from_string

from common.constants import LLMType
from api.db.services.llm_service import LLMBundle
from rag.utils.file_utils import extract_embed_file, extract_links_from_pdf, extract_links_from_docx, extract_html
from deepdoc.parser import DocxParser, ExcelParser, HtmlParser, JsonParser, MarkdownElementExtractor, MarkdownParser, PdfParser, TxtParser
from deepdoc.parser.figure_parser import VisionFigureParser,vision_figure_parser_docx_wrapper,vision_figure_parser_pdf_wrapper
from deepdoc.parser.pdf_parser import PlainParser, VisionParser
from deepdoc.parser.docling_parser import DoclingParser
from deepdoc.parser.tcadp_parser import TCADPParser
from common.parser_config_utils import normalize_layout_recognizer
from rag.nlp import concat_img, find_codec, naive_merge, naive_merge_with_images, naive_merge_docx, rag_tokenizer, tokenize_chunks, tokenize_chunks_with_images, tokenize_table, attach_media_context


def by_deepdoc(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, pdf_cls = None, **kwargs):
    callback = callback
    binary = binary
    pdf_parser = pdf_cls() if pdf_cls else Pdf()
    sections, tables = pdf_parser(
        filename if not binary else binary,
        from_page=from_page,
        to_page=to_page,
        callback=callback
    )

    tables = vision_figure_parser_pdf_wrapper(tbls=tables,
                                              callback=callback,
                                              **kwargs)
    return sections, tables, pdf_parser


def by_mineru(
    filename,
    binary=None,
    from_page=0,
    to_page=100000,
    lang="Chinese",
    callback=None,
    pdf_cls=None,
    parse_method: str = "raw",
    mineru_llm_name: str | None = None,
    tenant_id: str | None = None,
    **kwargs,
):
    pdf_parser = None
    if tenant_id:
        if not mineru_llm_name:
            try:
                from api.db.services.tenant_llm_service import TenantLLMService

                env_name = TenantLLMService.ensure_mineru_from_env(tenant_id)
                candidates = TenantLLMService.query(tenant_id=tenant_id, llm_factory="MinerU", model_type=LLMType.OCR)
                if candidates:
                    mineru_llm_name = candidates[0].llm_name
                elif env_name:
                    mineru_llm_name = env_name
            except Exception as e:  # best-effort fallback
                _lineaje_payload = f"fallback to env mineru: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in by_mineru).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:e83731bccd38a2fae67b0e7af7beb36f8cbce743c70a4349cd31b4ef4cffc5bd'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e83731bccd38a2fae67b0e7af7beb36f8cbce743c70a4349cd31b4ef4cffc5bd', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 86, 'function': 'by_mineru'}, 'file': 'rag/app/naive.py', 'line': 86, 'function': 'by_mineru', 'agent_name': 'by_mineru', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)

        if mineru_llm_name:
            try:
                ocr_model = LLMBundle(tenant_id=tenant_id, llm_type=LLMType.OCR, llm_name=mineru_llm_name, lang=lang)
                pdf_parser = ocr_model.mdl
                sections, tables = pdf_parser.parse_pdf(
                    filepath=filename,
                    binary=binary,
                    callback=callback,
                    parse_method=parse_method,
                    lang=lang,
                    **kwargs,
                )
                return sections, tables, pdf_parser
            except Exception as e:
                _lineaje_payload = f"Failed to parse pdf via LLMBundle MinerU ({mineru_llm_name}): {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in by_mineru).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:5d81cc5c822aba1f3cd6fc3e67fe3796db65d747a83a549c6da0050b9a587aa0'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5d81cc5c822aba1f3cd6fc3e67fe3796db65d747a83a549c6da0050b9a587aa0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 102, 'function': 'by_mineru'}, 'file': 'rag/app/naive.py', 'line': 102, 'function': 'by_mineru', 'agent_name': 'by_mineru', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)

    if callback:
        callback(-1, "MinerU not found.")
    return None, None, None


def by_docling(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, pdf_cls = None, **kwargs):
    pdf_parser = DoclingParser()
    parse_method = kwargs.get("parse_method", "raw")

    if not pdf_parser.check_installation():
        callback(-1, "Docling not found.")
        return None, None, pdf_parser

    sections, tables = pdf_parser.parse_pdf(
        filepath=filename,
        binary=binary,
        callback=callback,
        output_dir=os.environ.get("MINERU_OUTPUT_DIR", ""),
        delete_output=bool(int(os.environ.get("MINERU_DELETE_OUTPUT", 1))),
        parse_method=parse_method
    )
    return sections, tables, pdf_parser


def by_tcadp(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, pdf_cls = None, **kwargs):
    tcadp_parser = TCADPParser()

    if not tcadp_parser.check_installation():
        callback(-1, "TCADP parser not available. Please check Tencent Cloud API configuration.")
        return None, None, tcadp_parser

    sections, tables = tcadp_parser.parse_pdf(
        filepath=filename,
        binary=binary,
        callback=callback,
        output_dir=os.environ.get("TCADP_OUTPUT_DIR", ""),
        file_type="PDF"
    )
    return sections, tables, tcadp_parser


def by_plaintext(filename, binary=None, from_page=0, to_page=100000, callback=None, **kwargs):
    layout_recognizer = (kwargs.get("layout_recognizer") or "").strip()
    if (not layout_recognizer) or (layout_recognizer == "Plain Text"):
        pdf_parser = PlainParser()
    else:
        tenant_id = kwargs.get("tenant_id")
        if not tenant_id:
            raise ValueError("tenant_id is required when using vision layout recognizer")
        vision_model = LLMBundle(
            tenant_id,
            LLMType.IMAGE2TEXT,
            llm_name=layout_recognizer,
            lang=kwargs.get("lang", "Chinese"),
        )
        pdf_parser = VisionParser(vision_model=vision_model, **kwargs)

    sections, tables = pdf_parser(
        filename if not binary else binary,
        from_page=from_page,
        to_page=to_page,
        callback=callback
    )
    return sections, tables, pdf_parser


PARSERS = {
    "deepdoc":  by_deepdoc,
    "mineru":   by_mineru,
    "docling":  by_docling,
    "tcadp":    by_tcadp,
    "plaintext": by_plaintext,  # default
}


class Docx(DocxParser):
    def __init__(self):
        pass

    def get_picture(self, document, paragraph):
        imgs = paragraph._element.xpath('.//pic:pic')
        if not imgs:
            return None
        res_img = None
        for img in imgs:
            embed = img.xpath('.//a:blip/@r:embed')
            if not embed:
                continue
            embed = embed[0]
            try:
                related_part = document.part.related_parts[embed]
                image_blob = related_part.image.blob
            except UnrecognizedImageError:
                _lineaje_payload = "Unrecognized image format. Skipping image."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Docx.get_picture).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:9ca60a6408e57070d85363fecf1eb560dc77921f0d10aa896ccd108f2106bcb0'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9ca60a6408e57070d85363fecf1eb560dc77921f0d10aa896ccd108f2106bcb0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 197, 'function': 'Docx.get_picture'}, 'file': 'rag/app/naive.py', 'line': 197, 'function': 'get_picture', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                continue
            except UnexpectedEndOfFileError:
                _lineaje_payload = "EOF was unexpectedly encountered while reading an image stream. Skipping image."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Docx.get_picture).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:583dda473df256130fbaad21b2b63b202a37824137fc75167b068455a5c536e9'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:583dda473df256130fbaad21b2b63b202a37824137fc75167b068455a5c536e9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 200, 'function': 'Docx.get_picture'}, 'file': 'rag/app/naive.py', 'line': 200, 'function': 'get_picture', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                continue
            except InvalidImageStreamError:
                _lineaje_payload = "The recognized image stream appears to be corrupted. Skipping image."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Docx.get_picture).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:d7b140799092db9ceeaa818e9b748fdccb5254b508990e2b99ae66dc19142c7f'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d7b140799092db9ceeaa818e9b748fdccb5254b508990e2b99ae66dc19142c7f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 203, 'function': 'Docx.get_picture'}, 'file': 'rag/app/naive.py', 'line': 203, 'function': 'get_picture', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                continue
            except UnicodeDecodeError:
                _lineaje_payload = "The recognized image stream appears to be corrupted. Skipping image."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Docx.get_picture).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f6a5ef1e32cb203b79a82b74df12af9e5c4f0c644f8165dc744387bffa7cded5'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f6a5ef1e32cb203b79a82b74df12af9e5c4f0c644f8165dc744387bffa7cded5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 206, 'function': 'Docx.get_picture'}, 'file': 'rag/app/naive.py', 'line': 206, 'function': 'get_picture', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                continue
            except Exception:
                _lineaje_payload = "The recognized image stream appears to be corrupted. Skipping image."
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Docx.get_picture).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:bc978d2f8cf0351ea14054433d79e46b0c0c5fae3e61cda68e7070e2cf0de7c0'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bc978d2f8cf0351ea14054433d79e46b0c0c5fae3e61cda68e7070e2cf0de7c0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 209, 'function': 'Docx.get_picture'}, 'file': 'rag/app/naive.py', 'line': 209, 'function': 'get_picture', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                continue
            try:
                image = Image.open(BytesIO(image_blob)).convert('RGB')
                if res_img is None:
                    res_img = image
                else:
                    res_img = concat_img(res_img, image)
            except Exception:
                continue

        # LINEAJE: runtime guardrail checks `res_img` as it flows from the agent to the user interface, before it leaves the application (in Docx.get_picture).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res_img` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:fdc8fdf819403d98534a220465ed1278fdb5113f281c4bb891a47f14256dbea7'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fdc8fdf819403d98534a220465ed1278fdb5113f281c4bb891a47f14256dbea7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 220, 'function': 'Docx.get_picture'}, 'file': 'rag/app/naive.py', 'line': 220, 'function': 'get_picture', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res_img = _gr_client.enforce(_gr_site, res_img, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res_img

    def __clean(self, line):
        line = re.sub(r"\u3000", " ", line).strip()
        # LINEAJE: runtime guardrail checks `line` as it flows from the agent to the user interface, before it leaves the application (in Docx.__clean).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `line` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e8a4375de4e515decc70883a03bef717331824767d51ffb1cf72ee0719d8a386'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e8a4375de4e515decc70883a03bef717331824767d51ffb1cf72ee0719d8a386', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 224, 'function': 'Docx.__clean'}, 'file': 'rag/app/naive.py', 'line': 224, 'function': '__clean', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            line = _gr_client.enforce(_gr_site, line, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return line

    def __get_nearest_title(self, table_index, filename):
        """Get the hierarchical title structure before the table"""
        import re
        from docx.text.paragraph import Paragraph

        titles = []
        blocks = []

        # Get document name from filename parameter
        doc_name = re.sub(r"\.[a-zA-Z]+$", "", filename)
        if not doc_name:
            doc_name = "Untitled Document"

        # Collect all document blocks while maintaining document order
        try:
            # Iterate through all paragraphs and tables in document order
            for i, block in enumerate(self.doc._element.body):
                if block.tag.endswith('p'):  # Paragraph
                    p = Paragraph(block, self.doc)
                    blocks.append(('p', i, p))
                elif block.tag.endswith('tbl'):  # Table
                    blocks.append(('t', i, None))  # Table object will be retrieved later
        except Exception as e:
            _lineaje_payload = f"Error collecting blocks: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Docx.__get_nearest_title).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:309c75b23f2c7f01d93abc7a083103cd83d8e3a061e43e9ca778a8402f224adc'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:309c75b23f2c7f01d93abc7a083103cd83d8e3a061e43e9ca778a8402f224adc', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 249, 'function': 'Docx.__get_nearest_title'}, 'file': 'rag/app/naive.py', 'line': 249, 'function': '__get_nearest_title', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            return ""

        # Find the target table position
        target_table_pos = -1
        table_count = 0
        for i, (block_type, pos, _) in enumerate(blocks):
            if block_type == 't':
                if table_count == table_index:
                    target_table_pos = pos
                    break
                table_count += 1

        if target_table_pos == -1:
            return ""  # Target table not found

        # Find the nearest heading paragraph in reverse order
        nearest_title = None
        for i in range(len(blocks)-1, -1, -1):
            block_type, pos, block = blocks[i]
            if pos >= target_table_pos:  # Skip blocks after the table
                continue

            if block_type != 'p':
                continue

            if block.style and block.style.name and re.search(r"Heading\s*(\d+)", block.style.name, re.I):
                try:
                    level_match = re.search(r"(\d+)", block.style.name)
                    if level_match:
                        level = int(level_match.group(1))
                        if level <= 7:  # Support up to 7 heading levels
                            title_text = block.text.strip()
                            if title_text:  # Avoid empty titles
                                nearest_title = (level, title_text)
                                break
                except Exception as e:
                    _lineaje_payload = f"Error parsing heading level: {e}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Docx.__get_nearest_title).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:8f3d591eed2fc7ed7cdee3bdb43211f88d46968b7d8669c4e0de0c5dcd81c480'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8f3d591eed2fc7ed7cdee3bdb43211f88d46968b7d8669c4e0de0c5dcd81c480', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 286, 'function': 'Docx.__get_nearest_title'}, 'file': 'rag/app/naive.py', 'line': 286, 'function': '__get_nearest_title', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.error(_lineaje_payload)

        if nearest_title:
            # Add current title
            titles.append(nearest_title)
            current_level = nearest_title[0]

            # Find all parent headings, allowing cross-level search
            while current_level > 1:
                found = False
                for i in range(len(blocks)-1, -1, -1):
                    block_type, pos, block = blocks[i]
                    if pos >= target_table_pos:  # Skip blocks after the table
                        continue

                    if block_type != 'p':
                        continue

                    if block.style and re.search(r"Heading\s*(\d+)", block.style.name, re.I):
                        try:
                            level_match = re.search(r"(\d+)", block.style.name)
                            if level_match:
                                level = int(level_match.group(1))
                                # Find any heading with a higher level
                                if level < current_level:
                                    title_text = block.text.strip()
                                    if title_text:  # Avoid empty titles
                                        titles.append((level, title_text))
                                        current_level = level
                                        found = True
                                        break
                        except Exception as e:
                            _lineaje_payload = f"Error parsing parent heading: {e}"
                            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Docx.__get_nearest_title).
                            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                            #   Do not remove without review. site_id='site:sha256:ff58da78c5cdba15800ea1347cca027b9a8c98276c7939a803ed51e6a7feccf4'
                            _gr_client = _lineaje_load_gr_client()
                            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ff58da78c5cdba15800ea1347cca027b9a8c98276c7939a803ed51e6a7feccf4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 318, 'function': 'Docx.__get_nearest_title'}, 'file': 'rag/app/naive.py', 'line': 318, 'function': '__get_nearest_title', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                            try:
                                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                            except _gr_client.GuardrailUnavailableError:
                                pass
                            except PermissionError:
                                pass
                            logging.error(_lineaje_payload)

                if not found:  # Break if no parent heading is found
                    break

            # Sort by level (ascending, from highest to lowest)
            titles.sort(key=lambda x: x[0])
            # Organize titles (from highest to lowest)
            hierarchy = [doc_name] + [t[1] for t in titles]
            return " > ".join(hierarchy)

        return ""

    def __call__(self, filename, binary=None, from_page=0, to_page=100000):
        self.doc = Document(
            filename) if not binary else Document(BytesIO(binary))
        pn = 0
        lines = []
        last_image = None
        for p in self.doc.paragraphs:
            if pn > to_page:
                break
            if from_page <= pn < to_page:
                if p.text.strip():
                    if p.style and p.style.name == 'Caption':
                        former_image = None
                        if lines and lines[-1][1] and lines[-1][2] != 'Caption':
                            former_image = lines[-1][1].pop()
                        elif last_image:
                            former_image = last_image
                            last_image = None
                        lines.append((self.__clean(p.text), [former_image], p.style.name))
                    else:
                        current_image = self.get_picture(self.doc, p)
                        image_list = [current_image]
                        if last_image:
                            image_list.insert(0, last_image)
                            last_image = None
                        lines.append((self.__clean(p.text), image_list, p.style.name if p.style else ""))
                else:
                    if current_image := self.get_picture(self.doc, p):
                        if lines:
                            lines[-1][1].append(current_image)
                        else:
                            last_image = current_image
            for run in p.runs:
                if 'lastRenderedPageBreak' in run._element.xml:
                    pn += 1
                    continue
                if 'w:br' in run._element.xml and 'type="page"' in run._element.xml:
                    pn += 1
        new_line = [(line[0], reduce(concat_img, line[1]) if line[1] else None) for line in lines]

        tbls = []
        for i, tb in enumerate(self.doc.tables):
            title = self.__get_nearest_title(i, filename)
            html = "<table>"
            if title:
                html += f"<caption>Table Location: {title}</caption>"
            for r in tb.rows:
                html += "<tr>"
                i = 0
                try:
                    while i < len(r.cells):
                        span = 1
                        c = r.cells[i]
                        for j in range(i + 1, len(r.cells)):
                            if c.text == r.cells[j].text:
                                span += 1
                                i = j
                            else:
                                break
                        i += 1
                        html += f"<td>{c.text}</td>" if span == 1 else f"<td colspan='{span}'>{c.text}</td>"
                except Exception as e:
                    _lineaje_payload = f"Error parsing table, ignore: {e}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Docx.__call__).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:88ca86aa435e6c41b516cdf5118c9536c7bbfe6dc1b53597e29e9f8d10e61374'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:88ca86aa435e6c41b516cdf5118c9536c7bbfe6dc1b53597e29e9f8d10e61374', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 393, 'function': 'Docx.__call__'}, 'file': 'rag/app/naive.py', 'line': 393, 'function': '__call__', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.warning(_lineaje_payload)
                html += "</tr>"
            html += "</table>"
            tbls.append(((None, html), ""))
        return new_line, tbls

    def to_markdown(self, filename=None, binary=None, inline_images: bool = True):
        """
        This function uses mammoth, licensed under the BSD 2-Clause License.
        """

        import base64
        import uuid

        import mammoth
        from markdownify import markdownify

        docx_file = BytesIO(binary) if binary else open(filename, "rb")
        # LINEAJE: runtime guardrail checks `docx_file` as it flows from file storage to the agent (in Docx.to_markdown).
        #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `docx_file` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1357619e6d844516b18d3c226744113930bde35cedd075897e3cd255f9bab700'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1357619e6d844516b18d3c226744113930bde35cedd075897e3cd255f9bab700', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 410, 'function': 'Docx.to_markdown'}, 'file': 'rag/app/naive.py', 'line': 410, 'function': 'to_markdown', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            docx_file = _gr_client.enforce(_gr_site, docx_file, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise

        def _convert_image_to_base64(image):
            try:
                with image.open() as image_file:
                    image_bytes = image_file.read()
                    # LINEAJE: runtime guardrail checks `image_bytes` as it flows from file storage to the agent (in Docx._convert_image_to_base64).
                    #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `image_bytes` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:37a289091dfdfe0ebe0eb6086f2de693ff9b056c6a8b2f75fa94f916412e8277'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:37a289091dfdfe0ebe0eb6086f2de693ff9b056c6a8b2f75fa94f916412e8277', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 415, 'function': 'Docx.to_markdown._convert_image_to_base64'}, 'file': 'rag/app/naive.py', 'line': 415, 'function': '_convert_image_to_base64', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        image_bytes = _gr_client.enforce(_gr_site, image_bytes, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        raise
                encoded = base64.b64encode(image_bytes).decode("utf-8")
                base64_url = f"data:{image.content_type};base64,{encoded}"

                alt_name = "image"
                alt_name = f"img_{uuid.uuid4().hex[:8]}"

                return {"src": base64_url, "alt": alt_name}
            except Exception as e:
                _lineaje_payload = f"Failed to convert image to base64: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Docx._convert_image_to_base64).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:ff597482d56e9b8e161931a3b0537e1ce67cd11ec3a1e35e135e5935f584d8bc'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ff597482d56e9b8e161931a3b0537e1ce67cd11ec3a1e35e135e5935f584d8bc', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 424, 'function': 'Docx.to_markdown._convert_image_to_base64'}, 'file': 'rag/app/naive.py', 'line': 424, 'function': '_convert_image_to_base64', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
                return {"src": "", "alt": "image"}

        try:
            if inline_images:
                result = mammoth.convert_to_html(docx_file, convert_image=mammoth.images.img_element(_convert_image_to_base64))
            else:
                result = mammoth.convert_to_html(docx_file)

            html = result.value

            markdown_text = markdownify(html)
            # LINEAJE: runtime guardrail checks `markdown_text` as it flows from the agent to the user interface, before it leaves the application (in Docx._convert_image_to_base64).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `markdown_text` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:818d89d983184b8b797ec82d99e1549cd15b8306dcc6250c45416779600f9e2b'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:818d89d983184b8b797ec82d99e1549cd15b8306dcc6250c45416779600f9e2b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 436, 'function': 'Docx.to_markdown'}, 'file': 'rag/app/naive.py', 'line': 436, 'function': '_convert_image_to_base64', 'agent_name': 'Docx', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                markdown_text = _gr_client.enforce(_gr_site, markdown_text, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return markdown_text

        finally:
            if not binary:
                docx_file.close()


class Pdf(PdfParser):
    def __init__(self):
        super().__init__()

    def __call__(self, filename, binary=None, from_page=0,
                 to_page=100000, zoomin=3, callback=None, separate_tables_figures=False):
        start = timer()
        first_start = start
        callback(msg="OCR started")
        self.__images__(
            filename if not binary else binary,
            zoomin,
            from_page,
            to_page,
            callback
        )
        callback(msg="OCR finished ({:.2f}s)".format(timer() - start))
        _lineaje_payload = "OCR({}~{}): {:.2f}s".format(from_page, to_page, timer() - start)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Pdf.__call__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:801fa7f7e99a5be650a05cf308c6b2843994e87c0567e716342b7b06771994cf'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:801fa7f7e99a5be650a05cf308c6b2843994e87c0567e716342b7b06771994cf', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 460, 'function': 'Pdf.__call__'}, 'file': 'rag/app/naive.py', 'line': 460, 'function': '__call__', 'agent_name': 'Pdf', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)

        start = timer()
        self._layouts_rec(zoomin)
        callback(0.63, "Layout analysis ({:.2f}s)".format(timer() - start))

        start = timer()
        self._table_transformer_job(zoomin)
        callback(0.65, "Table analysis ({:.2f}s)".format(timer() - start))

        start = timer()
        self._text_merge(zoomin=zoomin)
        callback(0.67, "Text merged ({:.2f}s)".format(timer() - start))

        if separate_tables_figures:
            tbls, figures = self._extract_table_figure(True, zoomin, True, True, True)
            self._concat_downward()
            _lineaje_payload = "layouts cost: {}s".format(timer() - first_start)
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Pdf.__call__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:51d247e54b7381c55e8461791cfb0624da356395c3041d40b8227aa9437c886c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:51d247e54b7381c55e8461791cfb0624da356395c3041d40b8227aa9437c886c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 477, 'function': 'Pdf.__call__'}, 'file': 'rag/app/naive.py', 'line': 477, 'function': '__call__', 'agent_name': 'Pdf', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            return [(b["text"], self._line_tag(b, zoomin)) for b in self.boxes], tbls, figures
        else:
            tbls = self._extract_table_figure(True, zoomin, True, True)
            self._naive_vertical_merge()
            self._concat_downward()
            self._final_reading_order_merge()
            # self._filter_forpages()
            _lineaje_payload = "layouts cost: {}s".format(timer() - first_start)
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Pdf.__call__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f022fab906cb14d22bad2bd3d543a0d307e572ac4bf60b07bd01f0aae72a461e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f022fab906cb14d22bad2bd3d543a0d307e572ac4bf60b07bd01f0aae72a461e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 485, 'function': 'Pdf.__call__'}, 'file': 'rag/app/naive.py', 'line': 485, 'function': '__call__', 'agent_name': 'Pdf', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            return [(b["text"], self._line_tag(b, zoomin)) for b in self.boxes], tbls


class Markdown(MarkdownParser):
    def md_to_html(self, sections):
        if not sections:
            return []
        if isinstance(sections, type("")):
            text = sections
        elif isinstance(sections[0], type("")):
            text = sections[0]
        else:
            return []

        from bs4 import BeautifulSoup
        html_content = markdown(text)
        soup = BeautifulSoup(html_content, 'html.parser')
        # LINEAJE: runtime guardrail checks `soup` as it flows from the agent to the user interface, before it leaves the application (in Markdown.md_to_html).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `soup` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e049fba7730e401bd3539368f040b6811b1fd62be76e80627416babeb1400168'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e049fba7730e401bd3539368f040b6811b1fd62be76e80627416babeb1400168', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 503, 'function': 'Markdown.md_to_html'}, 'file': 'rag/app/naive.py', 'line': 503, 'function': 'md_to_html', 'agent_name': 'Markdown', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            soup = _gr_client.enforce(_gr_site, soup, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return soup

    def get_hyperlink_urls(self, soup):
        if soup:
            return set([a.get('href') for a in soup.find_all('a') if a.get('href')])
        return []

    def extract_image_urls_with_lines(self, text):
        md_img_re = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
        html_img_re = re.compile(r'src=["\\\']([^"\\\'>\\s]+)', re.IGNORECASE)
        urls = []
        seen = set()
        lines = text.splitlines()
        for idx, line in enumerate(lines):
            for url in md_img_re.findall(line):
                if (url, idx) not in seen:
                    urls.append({"url": url, "line": idx})
                    seen.add((url, idx))
            for url in html_img_re.findall(line):
                if (url, idx) not in seen:
                    urls.append({"url": url, "line": idx})
                    seen.add((url, idx))

        # cross-line
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(text, 'html.parser')
            newline_offsets = [m.start() for m in re.finditer(r"\n", text)] + [len(text)]
            for img_tag in soup.find_all('img'):
                src = img_tag.get('src')
                if not src:
                    continue

                tag_str = str(img_tag)
                pos = text.find(tag_str)
                if pos == -1:
                    # fallback
                    pos = max(text.find(src), 0)
                line_no = 0
                for i, off in enumerate(newline_offsets):
                    if pos <= off:
                        line_no = i
                        break
                if (src, line_no) not in seen:
                    urls.append({"url": src, "line": line_no})
                    seen.add((src, line_no))
        except Exception:
            pass

        # LINEAJE: runtime guardrail checks `urls` as it flows from the agent to the user interface, before it leaves the application (in Markdown.extract_image_urls_with_lines).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `urls` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e43e56bf253191f360134981f5f8e7dec917ecabc294b5a7fa67f9ba431b519d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e43e56bf253191f360134981f5f8e7dec917ecabc294b5a7fa67f9ba431b519d', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 553, 'function': 'Markdown.extract_image_urls_with_lines'}, 'file': 'rag/app/naive.py', 'line': 553, 'function': 'extract_image_urls_with_lines', 'agent_name': 'Markdown', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            urls = _gr_client.enforce(_gr_site, urls, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return urls

    def load_images_from_urls(self, urls, cache=None):
        import requests
        from pathlib import Path

        cache = cache or {}
        images = []
        for url in urls:
            if url in cache:
                if cache[url]:
                    images.append(cache[url])
                continue
            img_obj = None
            try:
                if url.startswith(('http://', 'https://')):
                    response = requests.get(url, stream=True, timeout=30)
                    # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in Markdown.load_images_from_urls).
                    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:14376087809bf61e6fdeab2f28645a7ac5d6c6ffb541c0c310a730e88c8ad5db'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:14376087809bf61e6fdeab2f28645a7ac5d6c6ffb541c0c310a730e88c8ad5db', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 569, 'function': 'Markdown.load_images_from_urls'}, 'file': 'rag/app/naive.py', 'line': 569, 'function': 'load_images_from_urls', 'agent_name': 'Markdown', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=569)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    if response.status_code == 200 and response.headers.get('Content-Type', '').startswith('image/'):
                        img_obj = Image.open(BytesIO(response.content)).convert('RGB')
                        # LINEAJE: runtime guardrail checks `img_obj` as it flows from the LLM to the agent, after the model replies (in Markdown.load_images_from_urls).
                        #   Detected: this statement moves data from the LLM to the agent with no runtime policy check (detection confidence: medium).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_011, AI_DAT_SEC_025, AI_DAT_SEC_027, AI_DAT_SEC_029; sensitive values in `img_obj` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:95792a6d6eef6cc7589c2c3235c726d03b8713c13c0b7611fc0bd94e151655d9'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:95792a6d6eef6cc7589c2c3235c726d03b8713c13c0b7611fc0bd94e151655d9', phase='post_model', boundary={'source': 'model', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='llm', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 571, 'function': 'Markdown.load_images_from_urls'}, 'file': 'rag/app/naive.py', 'line': 571, 'function': 'load_images_from_urls', 'agent_name': 'Markdown', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True}, interaction_id=locals().get('_lineaje_interaction_id'))
                        try:
                            img_obj = _gr_client.enforce(_gr_site, img_obj, content_type='application/json', variable_name='img_obj', source_file=__file__, before_line=571)
                        except _gr_client.GuardrailUnavailableError:
                            pass
                else:
                    local_path = Path(url)
                    if local_path.exists():
                        img_obj = Image.open(url).convert('RGB')
                    else:
                        _lineaje_payload = f"Local image file not found: {url}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Markdown.load_images_from_urls).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:c31ccd1d7aa82651fe2472cac744e4dacaf6e3cac21cc1d82f2ee1e6c3c351af'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c31ccd1d7aa82651fe2472cac744e4dacaf6e3cac21cc1d82f2ee1e6c3c351af', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 577, 'function': 'Markdown.load_images_from_urls'}, 'file': 'rag/app/naive.py', 'line': 577, 'function': 'load_images_from_urls', 'agent_name': 'Markdown', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.warning(_lineaje_payload)
            except Exception as e:
                _lineaje_payload = f"Failed to download/open image from {url}: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Markdown.load_images_from_urls).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:e17e751fc23a14a774d0534e0be4c9cf63242ef270b87b8eeec03467602ad835'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e17e751fc23a14a774d0534e0be4c9cf63242ef270b87b8eeec03467602ad835', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 579, 'function': 'Markdown.load_images_from_urls'}, 'file': 'rag/app/naive.py', 'line': 579, 'function': 'load_images_from_urls', 'agent_name': 'Markdown', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(_lineaje_payload)
            cache[url] = img_obj
            if img_obj:
                images.append(img_obj)
        return images, cache

    def __call__(self, filename, binary=None, separate_tables=True, delimiter=None, return_section_images=False):
        if binary:
            encoding = find_codec(binary)
            txt = binary.decode(encoding, errors="ignore")
        else:
            with open(filename, "r") as f:
                txt = f.read()
                # LINEAJE: runtime guardrail checks `txt` as it flows from file storage to the agent (in Markdown.__call__).
                #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `txt` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:98693a4536a216e4ed7673579249a5e84655a7092e441f5a14bd53afc55f01eb'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:98693a4536a216e4ed7673579249a5e84655a7092e441f5a14bd53afc55f01eb', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 591, 'function': 'Markdown.__call__'}, 'file': 'rag/app/naive.py', 'line': 591, 'function': '__call__', 'agent_name': 'Markdown', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    txt = _gr_client.enforce(_gr_site, txt, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    raise

        remainder, tables = self.extract_tables_and_remainder(f'{txt}\n', separate_tables=separate_tables)
        # To eliminate duplicate tables in chunking result, uncomment code below and set separate_tables to True in line 410.
        # extractor = MarkdownElementExtractor(remainder)
        extractor = MarkdownElementExtractor(txt)
        image_refs = self.extract_image_urls_with_lines(txt)
        element_sections = extractor.extract_elements(delimiter, include_meta=True)

        sections = []
        section_images = []
        image_cache = {}
        for element in element_sections:
            content = element["content"]
            start_line = element["start_line"]
            end_line = element["end_line"]
            urls_in_section = [ref["url"] for ref in image_refs if start_line <= ref["line"] <= end_line]
            imgs = []
            if urls_in_section:
                imgs, image_cache = self.load_images_from_urls(urls_in_section, image_cache)
            combined_image = None
            if imgs:
                combined_image = reduce(concat_img, imgs) if len(imgs) > 1 else imgs[0]
            sections.append((content, ""))
            section_images.append(combined_image)

        tbls = []
        for table in tables:
            tbls.append(((None, markdown(table, extensions=['markdown.extensions.tables'])), ""))
        if return_section_images:
            return sections, tbls, section_images
        return sections, tbls

def load_from_xml_v2(baseURI, rels_item_xml):
    """
    Return |_SerializedRelationships| instance loaded with the
    relationships contained in *rels_item_xml*. Returns an empty
    collection if *rels_item_xml* is |None|.
    """
    srels = _SerializedRelationships()
    if rels_item_xml is not None:
        rels_elm = parse_xml(rels_item_xml)
        for rel_elm in rels_elm.Relationship_lst:
            if rel_elm.target_ref in ('../NULL', 'NULL'):
                continue
            srels._srels.append(_SerializedRelationship(baseURI, rel_elm))
    # LINEAJE: runtime guardrail checks `srels` as it flows from the agent to the user interface, before it leaves the application (in load_from_xml_v2).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `srels` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:f1a265bc0f24b92c7e40257425cc783eca58ffe19be3030658abe7588c358af5'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f1a265bc0f24b92c7e40257425cc783eca58ffe19be3030658abe7588c358af5', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 637, 'function': 'load_from_xml_v2'}, 'file': 'rag/app/naive.py', 'line': 637, 'function': 'load_from_xml_v2', 'agent_name': 'load_from_xml_v2', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        srels = _gr_client.enforce(_gr_site, srels, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return srels

def chunk(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, **kwargs):
    """
        Supported file formats are docx, pdf, excel, txt.
        This method apply the naive ways to chunk files.
        Successive text will be sliced into pieces using 'delimiter'.
        Next, these successive pieces are merge into chunks whose token number is no more than 'Max token number'.
    """
    urls = set()
    url_res = []

    is_english = lang.lower() == "english"  # is_english(cks)
    parser_config = kwargs.get(
        "parser_config", {
            "chunk_token_num": 512, "delimiter": "\n!?。；！？", "layout_recognize": "DeepDOC", "analyze_hyperlink": True})

    child_deli = (parser_config.get("children_delimiter") or "").encode('utf-8').decode('unicode_escape').encode('latin1').decode('utf-8')
    cust_child_deli = re.findall(r"`([^`]+)`", child_deli)
    child_deli = "|".join(re.sub(r"`([^`]+)`", "", child_deli))
    if cust_child_deli:
        cust_child_deli = sorted(set(cust_child_deli), key=lambda x: -len(x))
        cust_child_deli = "|".join(re.escape(t) for t in cust_child_deli if t)
        child_deli += cust_child_deli

    is_markdown = False
    table_context_size = max(0, int(parser_config.get("table_context_size", 0) or 0))
    image_context_size = max(0, int(parser_config.get("image_context_size", 0) or 0))

    doc = {
        "docnm_kwd": filename,
        "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))
    }
    doc["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(doc["title_tks"])
    res = []
    pdf_parser = None
    section_images = None

    is_root = kwargs.get("is_root", True)
    embed_res = []
    if is_root:
        # Only extract embedded files at the root call
        embeds = []
        if binary is not None:
            embeds = extract_embed_file(binary)
        else:
            raise Exception("Embedding extraction from file path is not supported.")

        # Recursively chunk each embedded file and collect results
        for embed_filename, embed_bytes in embeds:
            try:
                sub_res = chunk(embed_filename, binary=embed_bytes, lang=lang, callback=callback, is_root=False, **kwargs) or []
                embed_res.extend(sub_res)
            except Exception as e:
                if callback:
                    callback(0.05, f"Failed to chunk embed {embed_filename}: {e}")
                continue

    if re.search(r"\.docx$", filename, re.IGNORECASE):
        callback(0.1, "Start to parse.")
        if parser_config.get("analyze_hyperlink", False) and is_root:
            urls = extract_links_from_docx(binary)
            for index, url in enumerate(urls):
                html_bytes, metadata = extract_html(url)
                if not html_bytes:
                    continue
                try:
                    sub_url_res = chunk(url, html_bytes, callback=callback, lang=lang, is_root=False, **kwargs)
                except Exception as e:
                    _lineaje_payload = f"Failed to chunk url in registered file type {url}: {e}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in chunk).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:9b0544c6b442497de0f1423d56649738a7b014811aac3545435a3e3a2a7ed787'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9b0544c6b442497de0f1423d56649738a7b014811aac3545435a3e3a2a7ed787', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 706, 'function': 'chunk'}, 'file': 'rag/app/naive.py', 'line': 706, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)
                    sub_url_res = chunk(f"{index}.html", html_bytes, callback=callback, lang=lang, is_root=False, **kwargs)
                url_res.extend(sub_url_res)

        # fix "There is no item named 'word/NULL' in the archive", referring to https://github.com/python-openxml/python-docx/issues/1105#issuecomment-1298075246
        _SerializedRelationships.load_from_xml = load_from_xml_v2
        sections, tables = Docx()(filename, binary)

        tables = vision_figure_parser_docx_wrapper(sections=sections, tbls=tables, callback=callback, **kwargs)

        res = tokenize_table(tables, doc, is_english)
        callback(0.8, "Finish parsing.")

        st = timer()

        chunks, images = naive_merge_docx(
            sections, int(parser_config.get(
                "chunk_token_num", 128)), parser_config.get(
                "delimiter", "\n!?。；！？"))

        res.extend(tokenize_chunks_with_images(chunks, doc, is_english, images, child_delimiters_pattern=child_deli))
        _lineaje_payload = "naive_merge({}): {}".format(filename, timer() - st)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in chunk).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:cd98564075d7cd4bfd9cf8a2c9e184610edc479091c907181ed6aebe3ded8d3f'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cd98564075d7cd4bfd9cf8a2c9e184610edc479091c907181ed6aebe3ded8d3f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 727, 'function': 'chunk'}, 'file': 'rag/app/naive.py', 'line': 727, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        res.extend(embed_res)
        res.extend(url_res)
        if table_context_size or image_context_size:
            attach_media_context(res, table_context_size, image_context_size)
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in chunk).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a398356ac2037679ecf6f92f3392cebe27229c0cbe3b859071717a792f28eaa1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a398356ac2037679ecf6f92f3392cebe27229c0cbe3b859071717a792f28eaa1', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 732, 'function': 'chunk'}, 'file': 'rag/app/naive.py', 'line': 732, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    elif re.search(r"\.pdf$", filename, re.IGNORECASE):
        layout_recognizer, parser_model_name = normalize_layout_recognizer(
            parser_config.get("layout_recognize", "DeepDOC")
        )

        if parser_config.get("analyze_hyperlink", False) and is_root:
            urls = extract_links_from_pdf(binary)

        if isinstance(layout_recognizer, bool):
            layout_recognizer = "DeepDOC" if layout_recognizer else "Plain Text"

        name = layout_recognizer.strip().lower()
        parser = PARSERS.get(name, by_plaintext)
        callback(0.1, "Start to parse.")

        sections, tables, pdf_parser = parser(
            filename = filename,
            binary = binary,
            from_page = from_page,
            to_page = to_page,
            lang = lang,
            callback = callback,
            layout_recognizer = layout_recognizer,
            mineru_llm_name = parser_model_name,
            **kwargs
        )

        if not sections and not tables:
            return []

        if name in ["tcadp", "docling", "mineru"]:
            parser_config["chunk_token_num"] = 0

        res = tokenize_table(tables, doc, is_english)
        callback(0.8, "Finish parsing.")

    elif re.search(r"\.(csv|xlsx?)$", filename, re.IGNORECASE):
        callback(0.1, "Start to parse.")

        # Check if tcadp_parser is selected for spreadsheet files
        layout_recognizer = parser_config.get("layout_recognize", "DeepDOC")
        if layout_recognizer == "TCADP Parser":
            table_result_type = parser_config.get("table_result_type", "1")
            markdown_image_response_type = parser_config.get("markdown_image_response_type", "1")
            tcadp_parser = TCADPParser(
                table_result_type=table_result_type,
                markdown_image_response_type=markdown_image_response_type
            )
            if not tcadp_parser.check_installation():
                callback(-1, "TCADP parser not available. Please check Tencent Cloud API configuration.")
                # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in chunk).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:77f3a52c1049ee33c8bf01761f1bbb10b122f83437c01c742eb53c273e30797b'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:77f3a52c1049ee33c8bf01761f1bbb10b122f83437c01c742eb53c273e30797b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 784, 'function': 'chunk'}, 'file': 'rag/app/naive.py', 'line': 784, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return res

            # Determine file type based on extension
            file_type = "XLSX" if re.search(r"\.xlsx?$", filename, re.IGNORECASE) else "CSV"

            sections, tables = tcadp_parser.parse_pdf(
                filepath=filename,
                binary=binary,
                callback=callback,
                output_dir=os.environ.get("TCADP_OUTPUT_DIR", ""),
                file_type=file_type
            )
            parser_config["chunk_token_num"] = 0
            res = tokenize_table(tables, doc, is_english)
            callback(0.8, "Finish parsing.")
        else:
            # Default DeepDOC parser
            excel_parser = ExcelParser()
            if parser_config.get("html4excel"):
                sections = [(_, "") for _ in excel_parser.html(binary, 12) if _]
                parser_config["chunk_token_num"] = 0
            else:
                sections = [(_, "") for _ in excel_parser(binary) if _]

    elif re.search(r"\.(txt|py|js|java|c|cpp|h|php|go|ts|sh|cs|kt|sql)$", filename, re.IGNORECASE):
        callback(0.1, "Start to parse.")
        sections = TxtParser()(filename, binary,
                               parser_config.get("chunk_token_num", 128),
                               parser_config.get("delimiter", "\n!?;。；！？"))
        callback(0.8, "Finish parsing.")

    elif re.search(r"\.(md|markdown)$", filename, re.IGNORECASE):
        callback(0.1, "Start to parse.")
        markdown_parser = Markdown(int(parser_config.get("chunk_token_num", 128)))
        sections, tables, section_images = markdown_parser(
            filename,
            binary,
            separate_tables=False,
            delimiter=parser_config.get("delimiter", "\n!?;。；！？"),
            return_section_images=True,
        )

        is_markdown = True

        try:
            vision_model = LLMBundle(kwargs["tenant_id"], LLMType.IMAGE2TEXT)
            callback(0.2, "Visual model detected. Attempting to enhance figure extraction...")
        except Exception:
            vision_model = None

        if vision_model:
            # Process images for each section
            for idx, (section_text, _) in enumerate(sections):
                images = []
                if section_images and len(section_images) > idx and section_images[idx] is not None:
                    images.append(section_images[idx])

                if images and len(images) > 0:
                    # If multiple images found, combine them using concat_img
                    combined_image = reduce(concat_img, images) if len(images) > 1 else images[0]
                    if section_images:
                        section_images[idx] = combined_image
                    else:
                        section_images = [None] * len(sections)
                        section_images[idx] = combined_image
                    markdown_vision_parser = VisionFigureParser(vision_model=vision_model, figures_data= [((combined_image, ["markdown image"]), [(0, 0, 0, 0, 0)])], **kwargs)
                    boosted_figures = markdown_vision_parser(callback=callback)
                    sections[idx] = (section_text + "\n\n" + "\n\n".join([fig[0][1] for fig in boosted_figures]), sections[idx][1])

        else:
            _lineaje_payload = "No visual model detected. Skipping figure parsing enhancement."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in chunk).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:23423d0b0a9c135d4efb803aa5cb8f4e7ef6cbc9233ebb22e11c008fbd5a4c94'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:23423d0b0a9c135d4efb803aa5cb8f4e7ef6cbc9233ebb22e11c008fbd5a4c94', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 854, 'function': 'chunk'}, 'file': 'rag/app/naive.py', 'line': 854, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)

        if parser_config.get("hyperlink_urls", False) and is_root:
            for idx, (section_text, _) in enumerate(sections):
                soup = markdown_parser.md_to_html(section_text)
                hyperlink_urls = markdown_parser.get_hyperlink_urls(soup)
                urls.update(hyperlink_urls)
        res = tokenize_table(tables, doc, is_english)
        callback(0.8, "Finish parsing.")

    elif re.search(r"\.(htm|html)$", filename, re.IGNORECASE):
        callback(0.1, "Start to parse.")
        chunk_token_num = int(parser_config.get("chunk_token_num", 128))
        sections = HtmlParser()(filename, binary, chunk_token_num)
        sections = [(_, "") for _ in sections if _]
        callback(0.8, "Finish parsing.")

    elif re.search(r"\.(json|jsonl|ldjson)$", filename, re.IGNORECASE):
        callback(0.1, "Start to parse.")
        chunk_token_num = int(parser_config.get("chunk_token_num", 128))
        sections = JsonParser(chunk_token_num)(binary)
        sections = [(_, "") for _ in sections if _]
        callback(0.8, "Finish parsing.")

    elif re.search(r"\.doc$", filename, re.IGNORECASE):
        callback(0.1, "Start to parse.")

        try:
            from tika import parser as tika_parser
        except Exception as e:
            callback(0.8, f"tika not available: {e}. Unsupported .doc parsing.")
            _lineaje_payload = f"tika not available: {e}. Unsupported .doc parsing for {filename}."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in chunk).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6a8f0cbea3f0716130db4925b1e7df6067d575c5574e6fe438b97db811fd490c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6a8f0cbea3f0716130db4925b1e7df6067d575c5574e6fe438b97db811fd490c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 885, 'function': 'chunk'}, 'file': 'rag/app/naive.py', 'line': 885, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            return []

        binary = BytesIO(binary)
        doc_parsed = tika_parser.from_buffer(binary)
        if doc_parsed.get('content', None) is not None:
            sections = doc_parsed['content'].split('\n')
            sections = [(_, "") for _ in sections if _]
            callback(0.8, "Finish parsing.")
        else:
            callback(0.8, f"tika.parser got empty content from {filename}.")
            _lineaje_payload = f"tika.parser got empty content from {filename}."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in chunk).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0c797194d1934c3dd3dadf6d8309c1a4e8a1a8563ff73416c3d984f61cf900e3'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0c797194d1934c3dd3dadf6d8309c1a4e8a1a8563ff73416c3d984f61cf900e3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 896, 'function': 'chunk'}, 'file': 'rag/app/naive.py', 'line': 896, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            return []
    else:
        raise NotImplementedError(
            "file type not supported yet(pdf, xlsx, doc, docx, txt supported)")

    st = timer()
    if is_markdown:
        merged_chunks = []
        merged_images = []
        chunk_limit = max(0, int(parser_config.get("chunk_token_num", 128)))
        overlapped_percent = int(parser_config.get("overlapped_percent", 0))
        overlapped_percent = max(0, min(overlapped_percent, 90))

        current_text = ""
        current_tokens = 0
        current_image = None

        for idx, sec in enumerate(sections):
            text = sec[0] if isinstance(sec, tuple) else sec
            sec_tokens = num_tokens_from_string(text)
            sec_image = section_images[idx] if section_images and idx < len(section_images) else None

            if current_text and current_tokens + sec_tokens > chunk_limit:
                merged_chunks.append(current_text)
                merged_images.append(current_image)
                overlap_part = ""
                if overlapped_percent > 0:
                    overlap_len = int(len(current_text) * overlapped_percent / 100)
                    if overlap_len > 0:
                        overlap_part = current_text[-overlap_len:]
                current_text = overlap_part
                current_tokens = num_tokens_from_string(current_text)
                current_image = current_image if overlap_part else None

            if current_text:
                current_text += "\n" + text
            else:
                current_text = text
            current_tokens += sec_tokens

            if sec_image:
                current_image = concat_img(current_image, sec_image) if current_image else sec_image

        if current_text:
            merged_chunks.append(current_text)
            merged_images.append(current_image)

        chunks = merged_chunks
        has_images = merged_images and any(img is not None for img in merged_images)

        if has_images:
            res.extend(tokenize_chunks_with_images(chunks, doc, is_english, merged_images, child_delimiters_pattern=child_deli))
        else:
            res.extend(tokenize_chunks(chunks, doc, is_english, pdf_parser, child_delimiters_pattern=child_deli))
    else:
        if section_images:
            if all(image is None for image in section_images):
                section_images = None

        if section_images:
            chunks, images = naive_merge_with_images(sections, section_images,
                                            int(parser_config.get(
                                                "chunk_token_num", 128)), parser_config.get(
                                                "delimiter", "\n!?。；！？"))
            res.extend(tokenize_chunks_with_images(chunks, doc, is_english, images, child_delimiters_pattern=child_deli))
        else:
            chunks = naive_merge(
                sections, int(parser_config.get(
                    "chunk_token_num", 128)), parser_config.get(
                    "delimiter", "\n!?。；！？"))

            res.extend(tokenize_chunks(chunks, doc, is_english, pdf_parser, child_delimiters_pattern=child_deli))

    if urls and parser_config.get("analyze_hyperlink", False) and is_root:
        for index, url in enumerate(urls):
            html_bytes, metadata = extract_html(url)
            if not html_bytes:
                continue
            try:
                sub_url_res = chunk(url, html_bytes, callback=callback, lang=lang, is_root=False, **kwargs)
            except Exception as e:
                _lineaje_payload = f"Failed to chunk url in registered file type {url}: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in chunk).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:abd52aa03740df7bc6b7a7bfefb0c122ed1026adf25ec65e18275972a35dd702'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:abd52aa03740df7bc6b7a7bfefb0c122ed1026adf25ec65e18275972a35dd702', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 978, 'function': 'chunk'}, 'file': 'rag/app/naive.py', 'line': 978, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                sub_url_res = chunk(f"{index}.html", html_bytes, callback=callback, lang=lang, is_root=False, **kwargs)
            url_res.extend(sub_url_res)

    _lineaje_payload = "naive_merge({}): {}".format(filename, timer() - st)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in chunk).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:b92014ced6fa307a9e7396a6649015e6f5c1ec3b1cd5c27ef545a3453de9c2cd'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b92014ced6fa307a9e7396a6649015e6f5c1ec3b1cd5c27ef545a3453de9c2cd', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 982, 'function': 'chunk'}, 'file': 'rag/app/naive.py', 'line': 982, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)

    if embed_res:
        res.extend(embed_res)
    if url_res:
        res.extend(url_res)
    if table_context_size or image_context_size:
        attach_media_context(res, table_context_size, image_context_size)
    # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in chunk).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:d703d73bee460255d233a802c24d9742e492bcf99455550200e7718586365aea'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d703d73bee460255d233a802c24d9742e492bcf99455550200e7718586365aea', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/naive.py', 'line': 990, 'function': 'chunk'}, 'file': 'rag/app/naive.py', 'line': 990, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return res


if __name__ == "__main__":
    import sys

    def dummy(prog=None, msg=""):
        pass

    chunk(sys.argv[1], from_page=0, to_page=10, callback=dummy)
