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

import json
import os
import re
import base64
from datetime import datetime
from abc import ABC
from io import BytesIO
from typing import Optional
from functools import partial
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, TableStyle, LongTable
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from agent.component.base import ComponentParamBase
from api.utils.api_utils import timeout
from .message import Message


class PDFGeneratorParam(ComponentParamBase):
    """
    Define the PDF Generator component parameters.
    """

    def __init__(self):
        super().__init__()
        # Output format
        self.output_format = "pdf"  # pdf, docx, txt
        
        # Content inputs
        self.content = ""
        self.title = ""
        self.subtitle = ""
        self.header_text = ""
        self.footer_text = ""
        
        # Images
        self.logo_image = ""  # base64 or file path
        self.logo_position = "left"  # left, center, right
        self.logo_width = 2.0  # inches
        self.logo_height = 1.0  # inches
        
        # Styling
        self.font_family = "Helvetica"  # Helvetica, Times-Roman, Courier
        self.font_size = 12
        self.title_font_size = 24
        self.heading1_font_size = 18
        self.heading2_font_size = 16
        self.heading3_font_size = 14
        self.text_color = "#000000"
        self.title_color = "#000000"
        
        # Page settings
        self.page_size = "A4"
        self.orientation = "portrait"  # portrait, landscape
        self.margin_top = 1.0  # inches
        self.margin_bottom = 1.0
        self.margin_left = 1.0
        self.margin_right = 1.0
        self.line_spacing = 1.2
        
        # Output settings
        self.filename = ""
        self.output_directory = "/tmp/pdf_outputs"
        self.add_page_numbers = True
        self.add_timestamp = True
        
        # Advanced features
        self.watermark_text = ""
        self.enable_toc = False
        
        self.outputs = {
            "file_path": {"value": "", "type": "string"},
            "pdf_base64": {"value": "", "type": "string"},
            "download": {"value": "", "type": "string"},
            "success": {"value": False, "type": "boolean"}
        }

    def check(self):
        self.check_empty(self.content, "[PDFGenerator] Content")
        self.check_valid_value(self.output_format, "[PDFGenerator] Output format", ["pdf", "docx", "txt"])
        self.check_valid_value(self.logo_position, "[PDFGenerator] Logo position", ["left", "center", "right"])
        self.check_valid_value(self.font_family, "[PDFGenerator] Font family", 
                             ["Helvetica", "Times-Roman", "Courier", "Helvetica-Bold", "Times-Bold"])
        self.check_valid_value(self.page_size, "[PDFGenerator] Page size", ["A4", "Letter"])
        self.check_valid_value(self.orientation, "[PDFGenerator] Orientation", ["portrait", "landscape"])
        self.check_positive_number(self.font_size, "[PDFGenerator] Font size")
        self.check_positive_number(self.margin_top, "[PDFGenerator] Margin top")


class PDFGenerator(Message, ABC):
    component_name = "PDFGenerator"
    
    # Track if Unicode fonts have been registered
    _unicode_fonts_registered = False
    _unicode_font_name = None
    _unicode_font_bold_name = None

    @classmethod
    def _reset_font_cache(cls):
        """Reset font registration cache - useful for testing"""
        cls._unicode_fonts_registered = False
        cls._unicode_font_name = None
        cls._unicode_font_bold_name = None

    @classmethod
    def _register_unicode_fonts(cls):
        """Register Unicode-compatible fonts for multi-language support.
        
        Uses CID fonts (STSong-Light) for reliable CJK rendering as TTF fonts
        have issues with glyph mapping in some ReportLab versions.
        """
        # If already registered successfully, return True
        if cls._unicode_fonts_registered and cls._unicode_font_name is not None:
            return True
        
        # Reset and try again if previous registration failed
        cls._unicode_fonts_registered = True
        cls._unicode_font_name = None
        cls._unicode_font_bold_name = None
        
        # Use CID fonts for reliable CJK support
        # These are built into ReportLab and work reliably across all platforms
        cid_fonts = [
            'STSong-Light',      # Simplified Chinese
            'HeiseiMin-W3',      # Japanese
            'HYSMyeongJo-Medium', # Korean
        ]
        
        for cid_font in cid_fonts:
            try:
                pdfmetrics.registerFont(UnicodeCIDFont(cid_font))
                cls._unicode_font_name = cid_font
                cls._unicode_font_bold_name = cid_font  # CID fonts don't have bold variants
                _lineaje_payload = f"Registered CID font: {cid_font}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._register_unicode_fonts).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:44524a896c725d85c2a74b4d06a835a5d258c88bd5c100a22302fff1beb81be1'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:44524a896c725d85c2a74b4d06a835a5d258c88bd5c100a22302fff1beb81be1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 140, 'function': 'PDFGenerator._register_unicode_fonts'}, 'file': 'agent/component/docs_generator.py', 'line': 140, 'function': '_register_unicode_fonts', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
                break
            except Exception as e:
                _lineaje_payload = f"Failed to register CID font {cid_font}: {e}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._register_unicode_fonts).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:ca916c2845ff10cea416dbd1318b3cb502ec69bf595d67c9e7ba97ac347bf686'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ca916c2845ff10cea416dbd1318b3cb502ec69bf595d67c9e7ba97ac347bf686', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 143, 'function': 'PDFGenerator._register_unicode_fonts'}, 'file': 'agent/component/docs_generator.py', 'line': 143, 'function': '_register_unicode_fonts', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
                continue
        
        # If CID fonts fail, try TTF fonts as fallback
        if not cls._unicode_font_name:
            font_paths = [
                '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('UnicodeFont', font_path))
                        cls._unicode_font_name = 'UnicodeFont'
                        cls._unicode_font_bold_name = 'UnicodeFont'
                        _lineaje_payload = f"Registered TTF font from: {font_path}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._register_unicode_fonts).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:f95f6e5cba6a7206e56ff1be946e34ce8c3cf54f5eab34e4ead20542f7b3cbd0'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f95f6e5cba6a7206e56ff1be946e34ce8c3cf54f5eab34e4ead20542f7b3cbd0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 159, 'function': 'PDFGenerator._register_unicode_fonts'}, 'file': 'agent/component/docs_generator.py', 'line': 159, 'function': '_register_unicode_fonts', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        print(_lineaje_payload)
                        
                        # Register font family
                        from reportlab.pdfbase.pdfmetrics import registerFontFamily
                        registerFontFamily('UnicodeFont', normal='UnicodeFont', bold='UnicodeFont')
                        break
                    except Exception as e:
                        _lineaje_payload = f"Failed to register TTF font {font_path}: {e}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._register_unicode_fonts).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:f638064a1626196401265d6f9059d33ed46a6738a112fbf7f8c7f2e6ee489f56'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f638064a1626196401265d6f9059d33ed46a6738a112fbf7f8c7f2e6ee489f56', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 166, 'function': 'PDFGenerator._register_unicode_fonts'}, 'file': 'agent/component/docs_generator.py', 'line': 166, 'function': '_register_unicode_fonts', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        print(_lineaje_payload)
                        continue
        
        return cls._unicode_font_name is not None

    @staticmethod
    def _needs_unicode_font(text: str) -> bool:
        """Check if text contains CJK or other complex scripts that need special fonts.
        
        Standard PDF fonts (Helvetica, Times, Courier) support:
        - Basic Latin, Extended Latin, Cyrillic, Greek
        
        CID fonts are needed for:
        - CJK (Chinese, Japanese, Korean)
        - Arabic, Hebrew (RTL scripts)
        - Thai, Hindi, and other Indic scripts
        """
        if not text:
            return False
        
        for char in text:
            code = ord(char)
            
            # CJK Unified Ideographs and related ranges
            if 0x4E00 <= code <= 0x9FFF:  # CJK Unified Ideographs
                return True
            if 0x3400 <= code <= 0x4DBF:  # CJK Extension A
                return True
            if 0x3000 <= code <= 0x303F:  # CJK Symbols and Punctuation
                return True
            if 0x3040 <= code <= 0x309F:  # Hiragana
                return True
            if 0x30A0 <= code <= 0x30FF:  # Katakana
                return True
            if 0xAC00 <= code <= 0xD7AF:  # Hangul Syllables
                return True
            if 0x1100 <= code <= 0x11FF:  # Hangul Jamo
                return True
            
            # Arabic and Hebrew (RTL scripts)
            if 0x0600 <= code <= 0x06FF:  # Arabic
                return True
            if 0x0590 <= code <= 0x05FF:  # Hebrew
                return True
            
            # Indic scripts
            if 0x0900 <= code <= 0x097F:  # Devanagari (Hindi)
                return True
            if 0x0E00 <= code <= 0x0E7F:  # Thai
                return True
        
        return False

    def _get_font_for_content(self, content: str) -> tuple:
        """Get appropriate font based on content, returns (regular_font, bold_font)"""
        if self._needs_unicode_font(content):
            if self._register_unicode_fonts() and self._unicode_font_name:
                return (self._unicode_font_name, self._unicode_font_bold_name or self._unicode_font_name)
            else:
                _lineaje_payload = "Warning: Content contains non-Latin characters but no Unicode font available"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._get_font_for_content).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:186d94191951eba04e30f437224405d63969cfed4cf6cdcd5858e9b3518e0ca9'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:186d94191951eba04e30f437224405d63969cfed4cf6cdcd5858e9b3518e0ca9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 225, 'function': 'PDFGenerator._get_font_for_content'}, 'file': 'agent/component/docs_generator.py', 'line': 225, 'function': '_get_font_for_content', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
        
        # Fall back to configured font
        return (self._param.font_family, self._get_bold_font_name())

    def _get_active_font(self) -> str:
        """Get the currently active font (Unicode or configured)"""
        return getattr(self, '_active_font', self._param.font_family)

    def _get_active_bold_font(self) -> str:
        """Get the currently active bold font (Unicode or configured)"""
        return getattr(self, '_active_bold_font', self._get_bold_font_name())

    def _get_bold_font_name(self) -> str:
        """Get the correct bold variant of the current font family"""
        font_map = {
            'Helvetica': 'Helvetica-Bold',
            'Times-Roman': 'Times-Bold',
            'Courier': 'Courier-Bold',
        }
        font_family = getattr(self._param, 'font_family', 'Helvetica')
        if 'Bold' in font_family:
            # LINEAJE: runtime guardrail checks `font_family` as it flows from the agent to the user interface, before it leaves the application (in PDFGenerator._get_bold_font_name).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `font_family` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:446db8023e577683412fcda7150ac5d555b9115ff5d6b1ca4d4c547a5783be8f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:446db8023e577683412fcda7150ac5d555b9115ff5d6b1ca4d4c547a5783be8f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 247, 'function': 'PDFGenerator._get_bold_font_name'}, 'file': 'agent/component/docs_generator.py', 'line': 247, 'function': '_get_bold_font_name', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                font_family = _gr_client.enforce(_gr_site, font_family, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return font_family
        return font_map.get(font_family, 'Helvetica-Bold')

    def get_input_form(self) -> dict[str, dict]:
        return {
            "content": {
                "name": "Content",
                "type": "text"
            },
            "title": {
                "name": "Title",
                "type": "line"
            },
            "subtitle": {
                "name": "Subtitle",
                "type": "line"
            }
        }

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10*60)))
    def _invoke(self, **kwargs):
        import traceback
        
        try:
            # Get content from parameters (which may contain variable references)
            content = self._param.content or ""
            title = self._param.title or ""
            subtitle = self._param.subtitle or ""
            
            # Log PDF generation start
            _lineaje_payload = f"Starting PDF generation for title: {title}, content length: {len(content)} chars"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._invoke).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:838abb1ff672b35e6bcbb5cbba904fa019bc25a65338fe7aca7ca101aa638a77'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:838abb1ff672b35e6bcbb5cbba904fa019bc25a65338fe7aca7ca101aa638a77', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 277, 'function': 'PDFGenerator._invoke'}, 'file': 'agent/component/docs_generator.py', 'line': 277, 'function': '_invoke', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)
            
            # Resolve variable references in content using canvas
            if content and self._canvas.is_reff(content):
                # Extract the variable reference and get its value
                import re
                matches = re.findall(self.variable_ref_patt, content, flags=re.DOTALL)
                for match in matches:
                    try:
                        var_value = self._canvas.get_variable_value(match)
                        if var_value:
                            # Handle partial (streaming) content
                            if isinstance(var_value, partial):
                                resolved_content = ""
                                for chunk in var_value():
                                    resolved_content += chunk
                                content = content.replace("{" + match + "}", resolved_content)
                            else:
                                content = content.replace("{" + match + "}", str(var_value))
                    except Exception as e:
                        _lineaje_payload = f"Error resolving variable {match}: {str(e)}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._invoke).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:4dcaea28f5154581d622251c13c5ef9b09f2f2393a2daba51614f9f48488ab72'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4dcaea28f5154581d622251c13c5ef9b09f2f2393a2daba51614f9f48488ab72', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 297, 'function': 'PDFGenerator._invoke'}, 'file': 'agent/component/docs_generator.py', 'line': 297, 'function': '_invoke', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        print(_lineaje_payload)
                        content = content.replace("{" + match + "}", f"[ERROR: {str(e)}]")
            
            # Also process with get_kwargs for any remaining variables
            if content:
                try:
                    content, _ = self.get_kwargs(content, kwargs)
                except Exception as e:
                    _lineaje_payload = f"Error processing content with get_kwargs: {str(e)}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._invoke).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:a7e06d025a4a398a0688f7de76d069e015b95db51b8959e77a241012d9855658'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a7e06d025a4a398a0688f7de76d069e015b95db51b8959e77a241012d9855658', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 305, 'function': 'PDFGenerator._invoke'}, 'file': 'agent/component/docs_generator.py', 'line': 305, 'function': '_invoke', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    print(_lineaje_payload)
            
            # Process template variables in title
            if title and self._canvas.is_reff(title):
                try:
                    matches = re.findall(self.variable_ref_patt, title, flags=re.DOTALL)
                    for match in matches:
                        var_value = self._canvas.get_variable_value(match)
                        if var_value:
                            title = title.replace("{" + match + "}", str(var_value))
                except Exception as e:
                    _lineaje_payload = f"Error processing title variables: {str(e)}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._invoke).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:f77e22274dd2882073b3c06863b56edf75bf489d4f1145f3e007b4ea1132a904'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f77e22274dd2882073b3c06863b56edf75bf489d4f1145f3e007b4ea1132a904', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 316, 'function': 'PDFGenerator._invoke'}, 'file': 'agent/component/docs_generator.py', 'line': 316, 'function': '_invoke', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    print(_lineaje_payload)
            
            if title:
                try:
                    title, _ = self.get_kwargs(title, kwargs)
                except Exception:
                    pass
            
            # Process template variables in subtitle
            if subtitle and self._canvas.is_reff(subtitle):
                try:
                    matches = re.findall(self.variable_ref_patt, subtitle, flags=re.DOTALL)
                    for match in matches:
                        var_value = self._canvas.get_variable_value(match)
                        if var_value:
                            subtitle = subtitle.replace("{" + match + "}", str(var_value))
                except Exception as e:
                    _lineaje_payload = f"Error processing subtitle variables: {str(e)}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._invoke).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:46c485f4a3a8b6897ad0b99b06b9822a57b14cd4a0f5fd0cf066e77c3cce8425'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:46c485f4a3a8b6897ad0b99b06b9822a57b14cd4a0f5fd0cf066e77c3cce8425', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 333, 'function': 'PDFGenerator._invoke'}, 'file': 'agent/component/docs_generator.py', 'line': 333, 'function': '_invoke', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    print(_lineaje_payload)
            
            if subtitle:
                try:
                    subtitle, _ = self.get_kwargs(subtitle, kwargs)
                except Exception:
                    pass
            
            # If content is still empty, check if it was passed directly
            if not content:
                content = kwargs.get("content", "")
            
            # Generate document based on format
            try:
                output_format = self._param.output_format or "pdf"
                
                if output_format == "pdf":
                    file_path, doc_base64 = self._generate_pdf(content, title, subtitle)
                    mime_type = "application/pdf"
                elif output_format == "docx":
                    file_path, doc_base64 = self._generate_docx(content, title, subtitle)
                    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif output_format == "txt":
                    file_path, doc_base64 = self._generate_txt(content, title, subtitle)
                    mime_type = "text/plain"
                else:
                    raise Exception(f"Unsupported output format: {output_format}")
                
                filename = os.path.basename(file_path)
                
                # Verify the file was created and has content
                if not os.path.exists(file_path):
                    raise Exception(f"Document file was not created: {file_path}")
                
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    raise Exception(f"Document file is empty: {file_path}")
                
                _lineaje_payload = f"Successfully generated {output_format.upper()}: {file_path} (Size: {file_size} bytes)"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._invoke).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:2285b97eccfca147679cc127dc7d205255f59b2d5042f5d98ee09b3b24a89c24'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2285b97eccfca147679cc127dc7d205255f59b2d5042f5d98ee09b3b24a89c24', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 371, 'function': 'PDFGenerator._invoke'}, 'file': 'agent/component/docs_generator.py', 'line': 371, 'function': '_invoke', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
                
                # Set outputs
                self.set_output("file_path", file_path)
                self.set_output("pdf_base64", doc_base64)  # Keep same output name for compatibility
                self.set_output("success", True)
                
                # Create download info object
                download_info = {
                    "filename": filename,
                    "path": file_path,
                    "base64": doc_base64,
                    "mime_type": mime_type,
                    "size": file_size
                }
                # Output download info as JSON string so it can be used in Message block
                # LINEAJE: runtime guardrail checks `download_info` as it flows from the agent to an external endpoint, before it leaves the application (in PDFGenerator._invoke).
                #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `download_info` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:d0ad8da3ac8793eabbc75b39d50c595240e7518dc2d5cebdc0f58a6d4fb9e45e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d0ad8da3ac8793eabbc75b39d50c595240e7518dc2d5cebdc0f58a6d4fb9e45e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 387, 'function': 'PDFGenerator._invoke'}, 'file': 'agent/component/docs_generator.py', 'line': 387, 'function': '_invoke', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    download_info = _gr_client.enforce(_gr_site, download_info, content_type='application/json', variable_name='download_info', source_file=__file__, before_line=387)
                except _gr_client.GuardrailUnavailableError:
                    pass
                download_json = json.dumps(download_info)
                self.set_output("download", download_json)
                
                # LINEAJE: runtime guardrail checks `download_info` as it flows from the agent to the user interface, before it leaves the application (in PDFGenerator._invoke).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `download_info` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:785010462b0796015d071a0bcec34e20ce8557c435fb89c48900cd97ec87f052'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:785010462b0796015d071a0bcec34e20ce8557c435fb89c48900cd97ec87f052', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 390, 'function': 'PDFGenerator._invoke'}, 'file': 'agent/component/docs_generator.py', 'line': 390, 'function': '_invoke', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    download_info = _gr_client.enforce(_gr_site, download_info, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return download_info
                
            except Exception as e:
                error_msg = f"Error in _generate_pdf: {str(e)}\n{traceback.format_exc()}"
                # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._invoke).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:579e7d3ac3fbf1631e168d1afda8b2f8d091e31f690c15a61ea777943239abb6'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:579e7d3ac3fbf1631e168d1afda8b2f8d091e31f690c15a61ea777943239abb6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 394, 'function': 'PDFGenerator._invoke'}, 'file': 'agent/component/docs_generator.py', 'line': 394, 'function': '_invoke', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(error_msg)
                self.set_output("success", False)
                self.set_output("_ERROR", f"PDF generation failed: {str(e)}")
                raise
                
        except Exception as e:
            error_msg = f"Error in PDFGenerator._invoke: {str(e)}\n{traceback.format_exc()}"
            # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._invoke).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:6588132ac3664aa147e4a8057cd9ee4ca85d7e2783a5d001f7dcbdba1714d524'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6588132ac3664aa147e4a8057cd9ee4ca85d7e2783a5d001f7dcbdba1714d524', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 401, 'function': 'PDFGenerator._invoke'}, 'file': 'agent/component/docs_generator.py', 'line': 401, 'function': '_invoke', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(error_msg)
            self.set_output("success", False)
            self.set_output("_ERROR", f"PDF generation failed: {str(e)}")
            raise

    def _generate_pdf(self, content: str, title: str = "", subtitle: str = "") -> tuple[str, str]:
        """Generate PDF from markdown-style content with improved error handling and concurrency support"""
        import uuid
        import traceback
        
        # Create output directory if it doesn't exist
        os.makedirs(self._param.output_directory, exist_ok=True)
        
        # Initialize variables that need cleanup
        buffer = None
        temp_file_path = None
        file_path = None
        
        try:
            # Generate a unique filename to prevent conflicts
            if self._param.filename:
                base_name = os.path.splitext(self._param.filename)[0]
                filename = f"{base_name}_{uuid.uuid4().hex[:8]}.pdf"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"document_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"
            
            file_path = os.path.join(self._param.output_directory, filename)
            temp_file_path = f"{file_path}.tmp"
            
            # Setup page size
            page_size = A4
            if self._param.orientation == "landscape":
                page_size = (A4[1], A4[0])
            
            # Create PDF buffer and document
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=page_size,
                topMargin=self._param.margin_top * inch,
                bottomMargin=self._param.margin_bottom * inch,
                leftMargin=self._param.margin_left * inch,
                rightMargin=self._param.margin_right * inch
            )
            
            # Build story (content elements)
            story = []
            # Combine all text content for Unicode font detection
            all_text = f"{title} {subtitle} {content}"
            
            # IMPORTANT: Register Unicode fonts BEFORE creating any styles or Paragraphs
            # This ensures the font family is available for ReportLab's HTML parser
            if self._needs_unicode_font(all_text):
                self._register_unicode_fonts()
            
            styles = self._create_styles(all_text)
            
            # Add logo if provided
            if self._param.logo_image:
                logo = self._add_logo()
                if logo:
                    story.append(logo)
                    story.append(Spacer(1, 0.3 * inch))
            
            # Add title
            if title:
                title_para = Paragraph(self._escape_html(title), styles['PDFTitle'])
                story.append(title_para)
                story.append(Spacer(1, 0.2 * inch))
            
            # Add subtitle
            if subtitle:
                subtitle_para = Paragraph(self._escape_html(subtitle), styles['PDFSubtitle'])
                story.append(subtitle_para)
                story.append(Spacer(1, 0.3 * inch))
            
            # Add timestamp if enabled
            if self._param.add_timestamp:
                timestamp_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                timestamp_para = Paragraph(timestamp_text, styles['Italic'])
                story.append(timestamp_para)
                story.append(Spacer(1, 0.2 * inch))
            
            # Parse and add content
            content_elements = self._parse_markdown_content(content, styles)
            story.extend(content_elements)
            
            # Build PDF
            doc.build(story, onFirstPage=self._add_page_decorations, onLaterPages=self._add_page_decorations)
            
            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            
            # Write to temporary file first
            with open(temp_file_path, 'wb') as f:
                # LINEAJE: runtime guardrail checks `pdf_bytes` as it flows from the agent to a file, before it is written to disk (in PDFGenerator._generate_pdf).
                #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `pdf_bytes` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:0b8bcdd03474aefc9917504902c7377c1b6c0cc3a53f78503a18775ccce3c1f8'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0b8bcdd03474aefc9917504902c7377c1b6c0cc3a53f78503a18775ccce3c1f8', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 497, 'function': 'PDFGenerator._generate_pdf'}, 'file': 'agent/component/docs_generator.py', 'line': 497, 'function': '_generate_pdf', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    pdf_bytes = _gr_client.enforce(_gr_site, pdf_bytes, content_type='application/json', variable_name='pdf_bytes', source_file=__file__, before_line=497)
                except _gr_client.GuardrailUnavailableError:
                    pass
                f.write(pdf_bytes)
            
            # Atomic rename to final filename (works across different filesystems)
            if os.path.exists(file_path):
                # LINEAJE: runtime guardrail checks `file_path` as it flows from the agent to system, at a security decision (in PDFGenerator._generate_pdf).
                #   Detected: this statement moves data from the agent to system with no runtime policy check (detection confidence: medium).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_029; sensitive values in `file_path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:00616123bce61b180223501f51932cb2ce5edd9c6f3781940c1dd381448e0203'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:00616123bce61b180223501f51932cb2ce5edd9c6f3781940c1dd381448e0203', phase='security_decision', boundary={'source': 'agent_message', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='agent', destination_type='system', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 501, 'function': 'PDFGenerator._generate_pdf'}, 'file': 'agent/component/docs_generator.py', 'line': 501, 'function': '_generate_pdf', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    file_path = _gr_client.enforce(_gr_site, file_path, content_type='application/json', variable_name='file_path', source_file=__file__, before_line=501)
                except _gr_client.GuardrailUnavailableError:
                    pass
                os.remove(file_path)
            os.rename(temp_file_path, file_path)
            
            # Verify the file was created and has content
            if not os.path.exists(file_path):
                raise Exception(f"Failed to create output file: {file_path}")
                
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise Exception(f"Generated PDF is empty: {file_path}")
            
            # Convert to base64
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            
            return file_path, pdf_base64
            
        except Exception as e:
            # Clean up any temporary files on error
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    # LINEAJE: runtime guardrail checks `temp_file_path` as it flows from the agent to system, at a security decision (in PDFGenerator._generate_pdf).
                    #   Detected: this statement moves data from the agent to system with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_029; sensitive values in `temp_file_path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:e6b1e0880733044e48eb376a3c2c29acb24f3ff1167785fa33db4f5bbfe8f698'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e6b1e0880733044e48eb376a3c2c29acb24f3ff1167785fa33db4f5bbfe8f698', phase='security_decision', boundary={'source': 'agent_message', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='agent', destination_type='system', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 521, 'function': 'PDFGenerator._generate_pdf'}, 'file': 'agent/component/docs_generator.py', 'line': 521, 'function': '_generate_pdf', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        temp_file_path = _gr_client.enforce(_gr_site, temp_file_path, content_type='application/json', variable_name='temp_file_path', source_file=__file__, before_line=521)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    os.remove(temp_file_path)
                except Exception as cleanup_error:
                    _lineaje_payload = f"Error cleaning up temporary file: {cleanup_error}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._generate_pdf).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:ff4f73c835a7d23d270d68d3616ec5bdfade50b47da68fc898dc9e14c9c32d5b'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ff4f73c835a7d23d270d68d3616ec5bdfade50b47da68fc898dc9e14c9c32d5b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 523, 'function': 'PDFGenerator._generate_pdf'}, 'file': 'agent/component/docs_generator.py', 'line': 523, 'function': '_generate_pdf', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    print(_lineaje_payload)
                    
            error_msg = f"Error generating PDF: {str(e)}\n{traceback.format_exc()}"
            # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._generate_pdf).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b123896126e07a3fba28f2de81384b2520e9a5881800944375c23232c8971442'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b123896126e07a3fba28f2de81384b2520e9a5881800944375c23232c8971442', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 526, 'function': 'PDFGenerator._generate_pdf'}, 'file': 'agent/component/docs_generator.py', 'line': 526, 'function': '_generate_pdf', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(error_msg)
            raise Exception(f"PDF generation failed: {str(e)}")
            
        finally:
            # Ensure buffer is always closed
            if buffer is not None:
                try:
                    buffer.close()
                except Exception as close_error:
                    _lineaje_payload = f"Error closing buffer: {close_error}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._generate_pdf).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:48e9f0169f611fb5064b3f64b89293b9a8198025867a58da741bb48ba92014b1'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:48e9f0169f611fb5064b3f64b89293b9a8198025867a58da741bb48ba92014b1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 535, 'function': 'PDFGenerator._generate_pdf'}, 'file': 'agent/component/docs_generator.py', 'line': 535, 'function': '_generate_pdf', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    print(_lineaje_payload)

    def _create_styles(self, content: str = ""):
        """Create custom paragraph styles with Unicode font support if needed"""
        # Check if content contains CJK characters that need special fonts
        needs_cjk = self._needs_unicode_font(content)
        
        if needs_cjk:
            # Use CID fonts for CJK content
            if self._register_unicode_fonts() and self._unicode_font_name:
                regular_font = self._unicode_font_name
                bold_font = self._unicode_font_bold_name or self._unicode_font_name
                _lineaje_payload = f"Using CID font for CJK content: {regular_font}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._create_styles).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:3360c1229dc7e1234fa1a24ed2fdb72a6e2a5245e7939b98b91dbc5f620e9d02'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3360c1229dc7e1234fa1a24ed2fdb72a6e2a5245e7939b98b91dbc5f620e9d02', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 547, 'function': 'PDFGenerator._create_styles'}, 'file': 'agent/component/docs_generator.py', 'line': 547, 'function': '_create_styles', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
            else:
                # Fall back to configured font if CID fonts unavailable
                regular_font = self._param.font_family
                bold_font = self._get_bold_font_name()
                _lineaje_payload = f"Warning: CJK content detected but no CID font available, using {regular_font}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._create_styles).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f3f603745f6de6a541749304ce44af1840011ed1027bdb3b298d2f5de21074bc'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f3f603745f6de6a541749304ce44af1840011ed1027bdb3b298d2f5de21074bc', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 552, 'function': 'PDFGenerator._create_styles'}, 'file': 'agent/component/docs_generator.py', 'line': 552, 'function': '_create_styles', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
        else:
            # Use user-selected font for Latin-only content
            regular_font = self._param.font_family
            bold_font = self._get_bold_font_name()
            _lineaje_payload = f"Using configured font: {regular_font}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._create_styles).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:38da544606c68d949685a9da6135658275b12684b3bee801531107da983a2390'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:38da544606c68d949685a9da6135658275b12684b3bee801531107da983a2390', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 557, 'function': 'PDFGenerator._create_styles'}, 'file': 'agent/component/docs_generator.py', 'line': 557, 'function': '_create_styles', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)
        
        # Store active fonts as instance variables for use in other methods
        self._active_font = regular_font
        self._active_bold_font = bold_font
        
        # Get fresh style sheet
        styles = getSampleStyleSheet()
        
        # Helper function to get the correct bold font name
        def get_bold_font(font_family):
            """Get the correct bold variant of a font family"""
            # If using Unicode font, return the Unicode bold
            if font_family in ('UnicodeFont', self._unicode_font_name):
                return bold_font
            font_map = {
                'Helvetica': 'Helvetica-Bold',
                'Times-Roman': 'Times-Bold',
                'Courier': 'Courier-Bold',
            }
            if 'Bold' in font_family:
                # LINEAJE: runtime guardrail checks `font_family` as it flows from the agent to the user interface, before it leaves the application (in PDFGenerator.get_bold_font).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `font_family` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:e258cc9dfc12fa8472229bcdb27023b0453e88c7a83ffdc9cac976286271bb4a'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e258cc9dfc12fa8472229bcdb27023b0453e88c7a83ffdc9cac976286271bb4a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 578, 'function': 'PDFGenerator._create_styles.get_bold_font'}, 'file': 'agent/component/docs_generator.py', 'line': 578, 'function': 'get_bold_font', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    font_family = _gr_client.enforce(_gr_site, font_family, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return font_family
            return font_map.get(font_family, 'Helvetica-Bold')
        
        # Use detected font instead of configured font for non-Latin content
        active_font = regular_font
        active_bold_font = bold_font
        
        # Helper function to add or update style
        def add_or_update_style(name, **kwargs):
            if name in styles:
                # Update existing style
                style = styles[name]
                for key, value in kwargs.items():
                    setattr(style, key, value)
            else:
                # Add new style
                styles.add(ParagraphStyle(name=name, **kwargs))
        
        # IMPORTANT: Update base styles to use Unicode font for non-Latin content
        # This ensures ALL text uses the correct font, not just our custom styles
        add_or_update_style('Normal', fontName=active_font)
        add_or_update_style('BodyText', fontName=active_font)
        add_or_update_style('Bullet', fontName=active_font)
        add_or_update_style('Heading1', fontName=active_bold_font)
        add_or_update_style('Heading2', fontName=active_bold_font)
        add_or_update_style('Heading3', fontName=active_bold_font)
        add_or_update_style('Title', fontName=active_bold_font)
        
        # Title style
        add_or_update_style(
            'PDFTitle',
            parent=styles['Heading1'],
            fontSize=self._param.title_font_size,
            textColor=colors.HexColor(self._param.title_color),
            fontName=active_bold_font,
            alignment=TA_CENTER,
            spaceAfter=12
        )
        
        # Subtitle style
        add_or_update_style(
            'PDFSubtitle',
            parent=styles['Heading2'],
            fontSize=self._param.heading2_font_size,
            textColor=colors.HexColor(self._param.text_color),
            fontName=active_font,
            alignment=TA_CENTER,
            spaceAfter=12
        )
        
        # Custom heading styles
        add_or_update_style(
            'CustomHeading1',
            parent=styles['Heading1'],
            fontSize=self._param.heading1_font_size,
            fontName=active_bold_font,
            textColor=colors.HexColor(self._param.text_color),
            spaceAfter=12,
            spaceBefore=12
        )
        
        add_or_update_style(
            'CustomHeading2',
            parent=styles['Heading2'],
            fontSize=self._param.heading2_font_size,
            fontName=active_bold_font,
            textColor=colors.HexColor(self._param.text_color),
            spaceAfter=10,
            spaceBefore=10
        )
        
        add_or_update_style(
            'CustomHeading3',
            parent=styles['Heading3'],
            fontSize=self._param.heading3_font_size,
            fontName=active_bold_font,
            textColor=colors.HexColor(self._param.text_color),
            spaceAfter=8,
            spaceBefore=8
        )
        
        # Body text style
        add_or_update_style(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=self._param.font_size,
            fontName=active_font,
            textColor=colors.HexColor(self._param.text_color),
            leading=self._param.font_size * self._param.line_spacing,
            alignment=TA_JUSTIFY
        )
        
        # Bullet style
        add_or_update_style(
            'CustomBullet',
            parent=styles['BodyText'],
            fontSize=self._param.font_size,
            fontName=active_font,
            textColor=colors.HexColor(self._param.text_color),
            leftIndent=20,
            bulletIndent=10
        )
        
        # Code style (keep Courier for code blocks)
        add_or_update_style(
            'PDFCode',
            parent=styles.get('Code', styles['Normal']),
            fontSize=self._param.font_size - 1,
            fontName='Courier',
            textColor=colors.HexColor('#333333'),
            backColor=colors.HexColor('#f5f5f5'),
            leftIndent=20,
            rightIndent=20
        )
        
        # Italic style
        add_or_update_style(
            'Italic',
            parent=styles['Normal'],
            fontSize=self._param.font_size,
            fontName=active_font,
            textColor=colors.HexColor(self._param.text_color)
        )
        
        # LINEAJE: runtime guardrail checks `styles` as it flows from the agent to the user interface, before it leaves the application (in PDFGenerator._create_styles).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `styles` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c084133deafd779af7faa1398a63689caa84d3c9d4e395cc1c48e9c6146c9b26'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c084133deafd779af7faa1398a63689caa84d3c9d4e395cc1c48e9c6146c9b26', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 702, 'function': 'PDFGenerator._create_styles'}, 'file': 'agent/component/docs_generator.py', 'line': 702, 'function': '_create_styles', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            styles = _gr_client.enforce(_gr_site, styles, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return styles

    def _parse_markdown_content(self, content: str, styles):
        """Parse markdown-style content and convert to PDF elements"""
        elements = []
        lines = content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                elements.append(Spacer(1, 0.1 * inch))
                i += 1
                continue
            
            # Horizontal rule
            if line == '---' or line == '___':
                elements.append(Spacer(1, 0.1 * inch))
                elements.append(self._create_horizontal_line())
                elements.append(Spacer(1, 0.1 * inch))
                i += 1
                continue
            
            # Heading 1
            if line.startswith('# ') and not line.startswith('## '):
                text = line[2:].strip()
                elements.append(Paragraph(self._format_inline(text), styles['CustomHeading1']))
                i += 1
                continue
            
            # Heading 2
            if line.startswith('## ') and not line.startswith('### '):
                text = line[3:].strip()
                elements.append(Paragraph(self._format_inline(text), styles['CustomHeading2']))
                i += 1
                continue
            
            # Heading 3
            if line.startswith('### '):
                text = line[4:].strip()
                elements.append(Paragraph(self._format_inline(text), styles['CustomHeading3']))
                i += 1
                continue
            
            # Bullet list
            if line.startswith('- ') or line.startswith('* '):
                bullet_items = []
                while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                    item_text = lines[i].strip()[2:].strip()
                    formatted = self._format_inline(item_text)
                    bullet_items.append(f"• {formatted}")
                    i += 1
                for item in bullet_items:
                    elements.append(Paragraph(item, styles['CustomBullet']))
                continue
            
            # Numbered list
            if re.match(r'^\d+\.\s', line):
                numbered_items = []
                counter = 1
                while i < len(lines) and re.match(r'^\d+\.\s', lines[i].strip()):
                    item_text = re.sub(r'^\d+\.\s', '', lines[i].strip())
                    numbered_items.append(f"{counter}. {self._format_inline(item_text)}")
                    counter += 1
                    i += 1
                for item in numbered_items:
                    elements.append(Paragraph(item, styles['CustomBullet']))
                continue
            
            # Table detection (markdown table must start with |)
            if line.startswith('|') and '|' in line:
                table_lines = []
                # Collect all consecutive lines that look like table rows
                while i < len(lines) and lines[i].strip() and '|' in lines[i]:
                    table_lines.append(lines[i].strip())
                    i += 1
                
                # Only process if we have at least 2 lines (header + separator or header + data)
                if len(table_lines) >= 2:
                    table_elements = self._create_table(table_lines)
                    if table_elements:
                        # _create_table now returns a list of elements
                        elements.extend(table_elements)
                        elements.append(Spacer(1, 0.2 * inch))
                    continue
                else:
                    # Not a valid table, treat as regular text
                    i -= len(table_lines)  # Reset position
            
            # Code block
            if line.startswith('```'):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    i += 1
                code_text = '\n'.join(code_lines)
                elements.append(Paragraph(self._escape_html(code_text), styles['PDFCode']))
                elements.append(Spacer(1, 0.1 * inch))
                continue
            
            # Regular paragraph
            paragraph_lines = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not self._is_special_line(lines[i]):
                paragraph_lines.append(lines[i].strip())
                i += 1
            
            paragraph_text = ' '.join(paragraph_lines)
            formatted_text = self._format_inline(paragraph_text)
            elements.append(Paragraph(formatted_text, styles['CustomBody']))
            elements.append(Spacer(1, 0.1 * inch))
        
        # LINEAJE: runtime guardrail checks `elements` as it flows from the agent to the user interface, before it leaves the application (in PDFGenerator._parse_markdown_content).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `elements` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f0d1324ec24618188b0def8aae23016d9b5f5efef2b5c774122c717f454dc0c2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f0d1324ec24618188b0def8aae23016d9b5f5efef2b5c774122c717f454dc0c2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 819, 'function': 'PDFGenerator._parse_markdown_content'}, 'file': 'agent/component/docs_generator.py', 'line': 819, 'function': '_parse_markdown_content', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            elements = _gr_client.enforce(_gr_site, elements, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return elements

    def _is_special_line(self, line: str) -> bool:
        """Check if line is a special markdown element"""
        line = line.strip()
        return (line.startswith('#') or 
                line.startswith('- ') or 
                line.startswith('* ') or
                re.match(r'^\d+\.\s', line) or
                line in ['---', '___'] or
                line.startswith('```') or
                '|' in line)

    def _format_inline(self, text: str) -> str:
        """Format inline markdown (bold, italic, code)"""
        # First, escape the existing HTML to not conflict with our tags.
        text = self._escape_html(text)

        # IMPORTANT: Process inline code FIRST to protect underscores inside code blocks
        # Use a placeholder to protect code blocks from italic/bold processing
        code_blocks = []
        def save_code(match):
            code_blocks.append(match.group(1))
            return f"__CODE_BLOCK_{len(code_blocks)-1}__"
        
        text = re.sub(r'`(.+?)`', save_code, text)

        # Then, apply markdown formatting.
        # The order is important: from most specific to least specific.

        # Bold and italic combined: ***text*** or ___text___
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
        text = re.sub(r'___(.+?)___', r'<b><i>\1</i></b>', text)

        # Bold: **text** or __text__
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__([^_]+?)__', r'<b>\1</b>', text)  # More restrictive to avoid matching placeholders

        # Italic: *text* or _text_ (but not underscores in words like variable_name)
        text = re.sub(r'\*([^*]+?)\*', r'<i>\1</i>', text)
        # Only match _text_ when surrounded by spaces or at start/end, not mid-word underscores
        text = re.sub(r'(?<![a-zA-Z0-9])_([^_]+?)_(?![a-zA-Z0-9])', r'<i>\1</i>', text)

        # Restore code blocks with proper formatting
        for i, code in enumerate(code_blocks):
            text = text.replace(f"__CODE_BLOCK_{i}__", f'<font name="Courier" color="#333333">{code}</font>')

        # LINEAJE: runtime guardrail checks `text` as it flows from the agent to the user interface, before it leaves the application (in PDFGenerator._format_inline).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `text` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b8ee81402cad31ec02ff7876835bf09e46c08726ef662115c4724666282687a8'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b8ee81402cad31ec02ff7876835bf09e46c08726ef662115c4724666282687a8', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 866, 'function': 'PDFGenerator._format_inline'}, 'file': 'agent/component/docs_generator.py', 'line': 866, 'function': '_format_inline', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            text = _gr_client.enforce(_gr_site, text, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return text

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters and clean up markdown.
        
        Args:
            text: Input text that may contain HTML or markdown
            
        Returns:
            str: Cleaned and escaped text
        """
        if not text:
            return ""
            
        # Ensure we're working with a string
        text = str(text)
        
        # Remove HTML form elements and tags
        text = re.sub(r'<input[^>]*>', '', text, flags=re.IGNORECASE)  # Remove input tags
        text = re.sub(r'<textarea[^>]*>.*?</textarea>', '', text, flags=re.IGNORECASE | re.DOTALL)  # Remove textarea
        text = re.sub(r'<select[^>]*>.*?</select>', '', text, flags=re.IGNORECASE | re.DOTALL)  # Remove select
        text = re.sub(r'<button[^>]*>.*?</button>', '', text, flags=re.IGNORECASE | re.DOTALL)  # Remove buttons
        text = re.sub(r'<form[^>]*>.*?</form>', '', text, flags=re.IGNORECASE | re.DOTALL)  # Remove forms
        
        # Remove other common HTML tags (but preserve content)
        text = re.sub(r'<div[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<span[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</span>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
        
        # First, handle common markdown table artifacts
        text = re.sub(r'^[|\-\s:]+$', '', text, flags=re.MULTILINE)  # Remove separator lines
        text = re.sub(r'^\s*\|\s*|\s*\|\s*$', '', text)  # Remove leading/trailing pipes
        text = re.sub(r'\s*\|\s*', ' | ', text)  # Normalize pipes
        
        # Remove markdown links, but keep other formatting characters for _format_inline
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # Remove markdown links
        
        # Escape HTML special characters
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        
        # Clean up excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple blank lines to double
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single
        
        return text.strip()

    def _get_cell_style(self, row_idx: int, is_header: bool = False, font_size: int = None) -> 'ParagraphStyle':
        """Get the appropriate style for a table cell."""
        styles = getSampleStyleSheet()
        
        # Helper function to get the correct bold font name
        def get_bold_font(font_family):
            font_map = {
                'Helvetica': 'Helvetica-Bold',
                'Times-Roman': 'Times-Bold',
                'Courier': 'Courier-Bold',
            }
            if 'Bold' in font_family:
                # LINEAJE: runtime guardrail checks `font_family` as it flows from the agent to the user interface, before it leaves the application (in PDFGenerator.get_bold_font).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `font_family` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f8d4e629024ebb777c13e8737ce1e169076b1da498d2b1c5a3e8a1c01396c965'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f8d4e629024ebb777c13e8737ce1e169076b1da498d2b1c5a3e8a1c01396c965', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 929, 'function': 'PDFGenerator._get_cell_style.get_bold_font'}, 'file': 'agent/component/docs_generator.py', 'line': 929, 'function': 'get_bold_font', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    font_family = _gr_client.enforce(_gr_site, font_family, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return font_family
            return font_map.get(font_family, 'Helvetica-Bold')
        
        if is_header:
            return ParagraphStyle(
                'TableHeader',
                parent=styles['Normal'],
                fontSize=self._param.font_size,
                fontName=self._get_active_bold_font(),
                textColor=colors.whitesmoke,
                alignment=TA_CENTER,
                leading=self._param.font_size * 1.2,
                wordWrap='CJK'
            )
        else:
            font_size = font_size or (self._param.font_size - 1)
            return ParagraphStyle(
                'TableCell',
                parent=styles['Normal'],
                fontSize=font_size,
                fontName=self._get_active_font(),
                textColor=colors.black,
                alignment=TA_LEFT,
                leading=font_size * 1.15,
                wordWrap='CJK'
            )

    def _convert_table_to_definition_list(self, data: list[list[str]]) -> list:
        """Convert a table to a definition list format for better handling of large content.
        
        This method handles both simple and complex tables, including those with nested content.
        It ensures that large cell content is properly wrapped and paginated.
        """
        elements = []
        styles = getSampleStyleSheet()
        
        # Base styles
        base_font_size = getattr(self._param, 'font_size', 10)
        
        # Body style
        body_style = ParagraphStyle(
            'TableBody',
            parent=styles['Normal'],
            fontSize=base_font_size,
            fontName=self._get_active_font(),
            textColor=colors.HexColor(getattr(self._param, 'text_color', '#000000')),
            spaceAfter=6,
            leading=base_font_size * 1.2
        )
        
        # Label style (for field names)
        label_style = ParagraphStyle(
            'LabelStyle',
            parent=body_style,
            fontName=self._get_active_bold_font(),
            textColor=colors.HexColor('#2c3e50'),
            fontSize=base_font_size,
            spaceAfter=4,
            leftIndent=0,
            leading=base_font_size * 1.3
        )
        
        # Value style (for cell content) - clean, no borders
        value_style = ParagraphStyle(
            'ValueStyle',
            parent=body_style,
            leftIndent=15,
            rightIndent=0,
            spaceAfter=8,
            spaceBefore=2,
            fontSize=base_font_size,
            textColor=colors.HexColor('#333333'),
            alignment=TA_JUSTIFY,
            leading=base_font_size * 1.4,
            # No borders or background - clean text only
        )

        try:
            # If we have no data, return empty list
            if not data or not any(data):
                # LINEAJE: runtime guardrail checks `elements` as it flows from the agent to the user interface, before it leaves the application (in PDFGenerator._convert_table_to_definition_list).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `elements` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:3eb1e48d3f7a38c017cc1a018f1756112673740d2564d66f0a9030efb9b2be3e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3eb1e48d3f7a38c017cc1a018f1756112673740d2564d66f0a9030efb9b2be3e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 1009, 'function': 'PDFGenerator._convert_table_to_definition_list'}, 'file': 'agent/component/docs_generator.py', 'line': 1009, 'function': '_convert_table_to_definition_list', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    elements = _gr_client.enforce(_gr_site, elements, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return elements
                
            # Get column headers or generate them
            headers = []
            if data and len(data) > 0:
                headers = [str(h).strip() for h in data[0]]
            
            # If no headers or empty headers, generate them
            if not any(headers):
                headers = [f"Column {i+1}" for i in range(len(data[0]) if data and len(data) > 0 else 0)]
            
            # Process each data row (skip header if it exists)
            start_row = 1 if len(data) > 1 and any(data[0]) else 0
            
            for row_idx in range(start_row, len(data)):
                row = data[row_idx] if row_idx < len(data) else []
                if not row:
                    continue
                    
                # Create a container for the row
                row_elements = []
                
                # Process each cell in the row
                for col_idx in range(len(headers)):
                    if col_idx >= len(headers):
                        continue
                        
                    # Get cell content
                    cell_text = str(row[col_idx]).strip() if col_idx < len(row) and row[col_idx] is not None else ""
                    
                    # Skip empty cells
                    if not cell_text or cell_text.isspace():
                        continue
                    
                    # Clean up markdown artifacts for regular text content
                    cell_text = str(cell_text)  # Ensure it's a string
                    
                    # Remove markdown table formatting
                    cell_text = re.sub(r'^[|\-\s:]+$', '', cell_text, flags=re.MULTILINE)  # Remove separator lines
                    cell_text = re.sub(r'^\s*\|\s*|\s*\|\s*$', '', cell_text)  # Remove leading/trailing pipes
                    cell_text = re.sub(r'\s*\|\s*', ' | ', cell_text)  # Normalize pipes
                    cell_text = re.sub(r'\s+', ' ', cell_text).strip()  # Normalize whitespace
                    
                    # Remove any remaining markdown formatting
                    cell_text = re.sub(r'`(.*?)`', r'\1', cell_text)  # Remove code ticks
                    cell_text = re.sub(r'\*\*(.*?)\*\*', r'\1', cell_text)  # Remove bold
                    cell_text = re.sub(r'\*(.*?)\*', r'\1', cell_text)  # Remove italic
                    
                    # Clean up any HTML entities or special characters
                    cell_text = self._escape_html(cell_text)
                    
                    # If content still looks like a table, convert it to plain text
                    if '|' in cell_text and ('--' in cell_text or any(cell_text.count('|') > 2 for line in cell_text.split('\n') if line.strip())):
                        # Convert to a simple text format
                        lines = [line.strip() for line in cell_text.split('\n') if line.strip()]
                        cell_text = ' | '.join(lines[:5])  # Join first 5 lines with pipe
                        if len(lines) > 5:
                            cell_text += '...'
                    
                    # Process long content with better wrapping
                    max_chars_per_line = 100  # Reduced for better readability
                    max_paragraphs = 3  # Maximum number of paragraphs to show initially
                    
                    # Split into paragraphs
                    paragraphs = [p for p in cell_text.split('\n\n') if p.strip()]
                    
                    # If content is too long, truncate with "show more" indicator
                    if len(paragraphs) > max_paragraphs or any(len(p) > max_chars_per_line * 3 for p in paragraphs):
                        wrapped_paragraphs = []
                        
                        for i, para in enumerate(paragraphs[:max_paragraphs]):
                            if len(para) > max_chars_per_line * 3:
                                # Split long paragraphs
                                words = para.split()
                                current_line = []
                                current_length = 0
                                
                                for word in words:
                                    if current_line and current_length + len(word) + 1 > max_chars_per_line:
                                        wrapped_paragraphs.append(' '.join(current_line))
                                        current_line = [word]
                                        current_length = len(word)
                                    else:
                                        current_line.append(word)
                                        current_length += len(word) + (1 if current_line else 0)
                                
                                if current_line:
                                    wrapped_paragraphs.append(' '.join(current_line))
                            else:
                                wrapped_paragraphs.append(para)
                        
                        # Add "show more" indicator if there are more paragraphs
                        if len(paragraphs) > max_paragraphs:
                            wrapped_paragraphs.append(f"... and {len(paragraphs) - max_paragraphs} more paragraphs")
                        
                        cell_text = '\n\n'.join(wrapped_paragraphs)
                    
                    # Add label and content with clean formatting (no borders)
                    label_para = Paragraph(f"<b>{self._escape_html(headers[col_idx])}:</b>", label_style)
                    value_para = Paragraph(self._escape_html(cell_text), value_style)
                    
                    # Add elements with proper spacing
                    row_elements.append(label_para)
                    row_elements.append(Spacer(1, 0.03 * 72))  # Tiny space between label and value
                    row_elements.append(value_para)
                
                # Add spacing between rows
                if row_elements and row_idx < len(data) - 1:
                    # Add a subtle horizontal line as separator
                    row_elements.append(Spacer(1, 0.1 * 72))
                    row_elements.append(self._create_horizontal_line(width=0.5, color='#e0e0e0'))
                    row_elements.append(Spacer(1, 0.15 * 72))
                
                elements.extend(row_elements)
            
            # Add some space after the table
            if elements:
                elements.append(Spacer(1, 0.3 * 72))  # 0.3 inches in points
                
        except Exception as e:
            # Fallback to simple text representation if something goes wrong
            error_style = ParagraphStyle(
                'ErrorStyle',
                parent=styles['Normal'],
                fontSize=base_font_size - 1,
                textColor=colors.red,
                backColor=colors.HexColor('#fff0f0'),
                borderWidth=1,
                borderColor=colors.red,
                borderPadding=5
            )
            
            error_msg = [
                Paragraph("<b>Error processing table:</b>", error_style),
                Paragraph(str(e), error_style),
                Spacer(1, 0.2 * 72)
            ]
            
            # Add a simplified version of the table
            try:
                for row in data[:10]:  # Limit to first 10 rows to avoid huge error output
                    error_msg.append(Paragraph(" | ".join(str(cell) for cell in row), body_style))
                if len(data) > 10:
                    error_msg.append(Paragraph(f"... and {len(data) - 10} more rows", body_style))
            except Exception:
                pass
                
            elements.extend(error_msg)
        
        # LINEAJE: runtime guardrail checks `elements` as it flows from the agent to the user interface, before it leaves the application (in PDFGenerator._convert_table_to_definition_list).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `elements` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9008c2fe5a9def461efb7752906ca063ccaa47e3efe8d1fd5f242185e5cef0ad'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9008c2fe5a9def461efb7752906ca063ccaa47e3efe8d1fd5f242185e5cef0ad', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 1158, 'function': 'PDFGenerator._convert_table_to_definition_list'}, 'file': 'agent/component/docs_generator.py', 'line': 1158, 'function': '_convert_table_to_definition_list', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            elements = _gr_client.enforce(_gr_site, elements, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return elements

    def _create_table(self, table_lines: list[str]) -> Optional[list]:
        """Create a table from markdown table syntax with robust error handling.
        
        This method handles simple tables and falls back to a list format for complex cases.
        
        Returns:
            A list of flowables (could be a table or alternative representation)
            Returns None if the table cannot be created.
        """
        if not table_lines or len(table_lines) < 2:
            return None
        
        try:
            # Parse table data
            data = []
            max_columns = 0
            
            for line in table_lines:
                # Skip separator lines (e.g., |---|---|)
                if re.match(r'^\|[\s\-:]+\|$', line):
                    continue
                
                # Handle empty lines within tables
                if not line.strip():
                    continue
                
                # Split by | and clean up cells
                cells = []
                in_quotes = False
                current_cell = ""
                
                # Custom split to handle escaped pipes and quoted content
                for char in line[1:]:  # Skip initial |
                    if char == '|' and not in_quotes:
                        cells.append(current_cell.strip())
                        current_cell = ""
                    elif char == '"':
                        in_quotes = not in_quotes
                        current_cell += char
                    elif char == '\\' and not in_quotes:
                        # Handle escaped characters
                        pass
                    else:
                        current_cell += char
                
                # Add the last cell
                if current_cell.strip() or len(cells) > 0:
                    cells.append(current_cell.strip())
                
                # Remove empty first/last elements if they're empty (from leading/trailing |)
                if cells and not cells[0]:
                    cells = cells[1:]
                if cells and not cells[-1]:
                    cells = cells[:-1]
                
                if cells:
                    data.append(cells)
                    max_columns = max(max_columns, len(cells))
            
            if not data or max_columns == 0:
                return None
            
            # Ensure all rows have the same number of columns
            for row in data:
                while len(row) < max_columns:
                    row.append('')
            
            # Calculate available width for table
            from reportlab.lib.pagesizes import A4
            page_width = A4[0] if self._param.orientation == 'portrait' else A4[1]
            available_width = page_width - (self._param.margin_left + self._param.margin_right) * inch
            
            # Check if we should use definition list format
            max_cell_length = max((len(str(cell)) for row in data for cell in row), default=0)
            total_rows = len(data)
            
            # Use definition list format if:
            # - Any cell is too large (> 300 chars), OR
            # - More than 6 columns, OR
            # - More than 20 rows, OR
            # - Contains nested tables or complex structures
            has_nested_tables = any('|' in cell and '---' in cell for row in data for cell in row)
            has_complex_cells = any(len(str(cell)) > 150 for row in data for cell in row)
            
            should_use_list_format = (
                max_cell_length > 300 or 
                max_columns > 6 or 
                total_rows > 20 or
                has_nested_tables or
                has_complex_cells
            )
            
            if should_use_list_format:
                return self._convert_table_to_definition_list(data)
            
            # Process cells for normal table
            processed_data = []
            for row_idx, row in enumerate(data):
                processed_row = []
                for cell_idx, cell in enumerate(row):
                    cell_text = str(cell).strip() if cell is not None else ""
                    
                    # Handle empty cells
                    if not cell_text:
                        processed_row.append("")
                        continue
                    
                    # Clean up markdown table artifacts
                    cell_text = re.sub(r'\\\|', '|', cell_text)  # Unescape pipes
                    cell_text = re.sub(r'\\n', '\n', cell_text)  # Handle explicit newlines
                    
                    # Check for nested tables
                    if '|' in cell_text and '---' in cell_text:
                        # This cell contains a nested table
                        nested_lines = [line.strip() for line in cell_text.split('\n') if line.strip()]
                        nested_table = self._create_table(nested_lines)
                        if nested_table:
                            processed_row.append(nested_table[0])  # Add the nested table
                            continue
                    
                    # Process as regular text
                    font_size = self._param.font_size - 1 if row_idx > 0 else self._param.font_size
                    try:
                        style = self._get_cell_style(row_idx, is_header=(row_idx == 0), font_size=font_size)
                        escaped_text = self._escape_html(cell_text)
                        processed_row.append(Paragraph(escaped_text, style))
                    except Exception:
                        processed_row.append(self._escape_html(cell_text))
                
                processed_data.append(processed_row)
            
            # Calculate column widths
            min_col_width = 0.5 * inch
            max_cols = int(available_width / min_col_width)
            
            if max_columns > max_cols:
                return self._convert_table_to_definition_list(data)
                
            col_width = max(min_col_width, available_width / max_columns)
            col_widths = [col_width] * max_columns
            
            # Create the table
            try:
                table = LongTable(processed_data, colWidths=col_widths, repeatRows=1)
                
                # Define table style
                table_style = [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),  # Darker header
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), self._get_active_bold_font()),
                    ('FONTSIZE', (0, 0), (-1, -1), self._param.font_size - 1),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),  # Lighter background
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),  # Lighter grid
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]
                
                # Add zebra striping for better readability
                for i in range(1, len(processed_data)):
                    if i % 2 == 0:
                        table_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f1f3f5')))
                
                table.setStyle(TableStyle(table_style))
                
                # Add a small spacer after the table
                return [table, Spacer(1, 0.2 * inch)]
                
            except Exception as table_error:
                _lineaje_payload = f"Error creating table: {table_error}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._create_table).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f39721c99a008f9989e39c3a5261b740e16c912eb67b72fb498472621cbbc965'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f39721c99a008f9989e39c3a5261b740e16c912eb67b72fb498472621cbbc965', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 1333, 'function': 'PDFGenerator._create_table'}, 'file': 'agent/component/docs_generator.py', 'line': 1333, 'function': '_create_table', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
                return self._convert_table_to_definition_list(data)
                
        except Exception as e:
            _lineaje_payload = f"Error processing table: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._create_table).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:cf0dd76109dd81e02e7106c49eb5be5ae01232a231568cd8b76cde2dbf8ee445'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cf0dd76109dd81e02e7106c49eb5be5ae01232a231568cd8b76cde2dbf8ee445', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 1337, 'function': 'PDFGenerator._create_table'}, 'file': 'agent/component/docs_generator.py', 'line': 1337, 'function': '_create_table', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)
            # Return a simple text representation of the table
            try:
                text_content = []
                for row in data:
                    text_content.append(" | ".join(str(cell) for cell in row))
                return [Paragraph("<br/>".join(text_content), self._get_cell_style(0))]
            except Exception:
                return None

    def _create_horizontal_line(self, width: float = 1, color: str = None):
        """Create a horizontal line with customizable width and color
        
        Args:
            width: Line thickness in points (default: 1)
            color: Hex color string (default: grey)
        
        Returns:
            HRFlowable: Horizontal line element
        """
        from reportlab.platypus import HRFlowable
        line_color = colors.HexColor(color) if color else colors.grey
        return HRFlowable(width="100%", thickness=width, color=line_color, spaceBefore=0, spaceAfter=0)

    def _add_logo(self) -> Optional[Image]:
        """Add logo image to PDF"""
        try:
            # Check if it's base64 or file path
            if self._param.logo_image.startswith('data:image'):
                # Extract base64 data
                base64_data = self._param.logo_image.split(',')[1]
                image_data = base64.b64decode(base64_data)
                img = Image(BytesIO(image_data))
            elif os.path.exists(self._param.logo_image):
                img = Image(self._param.logo_image)
            else:
                return None
            
            # Set size
            img.drawWidth = self._param.logo_width * inch
            img.drawHeight = self._param.logo_height * inch
            
            # Set alignment
            if self._param.logo_position == 'center':
                img.hAlign = 'CENTER'
            elif self._param.logo_position == 'right':
                img.hAlign = 'RIGHT'
            else:
                img.hAlign = 'LEFT'
            
            # LINEAJE: runtime guardrail checks `img` as it flows from the agent to the user interface, before it leaves the application (in PDFGenerator._add_logo).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `img` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:13b5a9f45efe561c207e14debc2fc165eb17eda07f10067c0a76b8798fc467c9'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:13b5a9f45efe561c207e14debc2fc165eb17eda07f10067c0a76b8798fc467c9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 1387, 'function': 'PDFGenerator._add_logo'}, 'file': 'agent/component/docs_generator.py', 'line': 1387, 'function': '_add_logo', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                img = _gr_client.enforce(_gr_site, img, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return img
        except Exception as e:
            _lineaje_payload = f"Error adding logo: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PDFGenerator._add_logo).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:019be50cb2e7e4bbbbc8a9c8e9b776066214dba6d85f2bb2f491f0186ca975af'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:019be50cb2e7e4bbbbc8a9c8e9b776066214dba6d85f2bb2f491f0186ca975af', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 1389, 'function': 'PDFGenerator._add_logo'}, 'file': 'agent/component/docs_generator.py', 'line': 1389, 'function': '_add_logo', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(_lineaje_payload)
            return None

    def _add_page_decorations(self, canvas, doc):
        """Add header, footer, page numbers, watermark"""
        canvas.saveState()
        
        # Get active font for decorations
        active_font = self._get_active_font()
        
        # Add watermark
        if self._param.watermark_text:
            canvas.setFont(active_font, 60)
            canvas.setFillColorRGB(0.9, 0.9, 0.9, alpha=0.3)
            canvas.saveState()
            canvas.translate(doc.pagesize[0] / 2, doc.pagesize[1] / 2)
            canvas.rotate(45)
            canvas.drawCentredString(0, 0, self._param.watermark_text)
            canvas.restoreState()
        
        # Add header
        if self._param.header_text:
            canvas.setFont(active_font, 9)
            canvas.setFillColorRGB(0.5, 0.5, 0.5)
            canvas.drawString(doc.leftMargin, doc.pagesize[1] - 0.5 * inch, self._param.header_text)
        
        # Add footer
        if self._param.footer_text:
            canvas.setFont(active_font, 9)
            canvas.setFillColorRGB(0.5, 0.5, 0.5)
            canvas.drawString(doc.leftMargin, 0.5 * inch, self._param.footer_text)
        
        # Add page numbers
        if self._param.add_page_numbers:
            page_num = canvas.getPageNumber()
            text = f"Page {page_num}"
            canvas.setFont(active_font, 9)
            canvas.setFillColorRGB(0.5, 0.5, 0.5)
            canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 0.5 * inch, text)
        
        canvas.restoreState()

    def thoughts(self) -> str:
        return "Generating PDF document with formatted content..."

    def _generate_docx(self, content: str, title: str = "", subtitle: str = "") -> tuple[str, str]:
        """Generate DOCX from markdown-style content"""
        import uuid
        from docx import Document
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        # Create output directory if it doesn't exist
        os.makedirs(self._param.output_directory, exist_ok=True)
        
        try:
            # Generate filename
            if self._param.filename:
                base_name = os.path.splitext(self._param.filename)[0]
                filename = f"{base_name}_{uuid.uuid4().hex[:8]}.docx"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"document_{timestamp}_{uuid.uuid4().hex[:8]}.docx"
            
            file_path = os.path.join(self._param.output_directory, filename)
            
            # Create document
            doc = Document()
            
            # Add title
            if title:
                title_para = doc.add_heading(title, level=0)
                title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add subtitle
            if subtitle:
                subtitle_para = doc.add_heading(subtitle, level=1)
                subtitle_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add timestamp if enabled
            if self._param.add_timestamp:
                timestamp_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                ts_para = doc.add_paragraph(timestamp_text)
                ts_para.runs[0].italic = True
                ts_para.runs[0].font.size = Pt(9)
            
            # Parse and add content
            lines = content.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                if not line:
                    i += 1
                    continue
                
                # Headings
                if line.startswith('# ') and not line.startswith('## '):
                    doc.add_heading(line[2:].strip(), level=1)
                elif line.startswith('## ') and not line.startswith('### '):
                    doc.add_heading(line[3:].strip(), level=2)
                elif line.startswith('### '):
                    doc.add_heading(line[4:].strip(), level=3)
                # Bullet list
                elif line.startswith('- ') or line.startswith('* '):
                    doc.add_paragraph(line[2:].strip(), style='List Bullet')
                # Numbered list
                elif re.match(r'^\d+\.\s', line):
                    text = re.sub(r'^\d+\.\s', '', line)
                    doc.add_paragraph(text, style='List Number')
                # Regular paragraph
                else:
                    para = doc.add_paragraph(line)
                    para.runs[0].font.size = Pt(self._param.font_size)
                
                i += 1
            
            # Save document
            doc.save(file_path)
            
            # Read and encode to base64
            with open(file_path, 'rb') as f:
                doc_bytes = f.read()
                # LINEAJE: runtime guardrail checks `doc_bytes` as it flows from file storage to the agent (in PDFGenerator._generate_docx).
                #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `doc_bytes` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:cdb20022fded1a7970df96c32c223ee9c758a665fcb79b31435c178aabfb23a6'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cdb20022fded1a7970df96c32c223ee9c758a665fcb79b31435c178aabfb23a6', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 1511, 'function': 'PDFGenerator._generate_docx'}, 'file': 'agent/component/docs_generator.py', 'line': 1511, 'function': '_generate_docx', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    doc_bytes = _gr_client.enforce(_gr_site, doc_bytes, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    raise
            doc_base64 = base64.b64encode(doc_bytes).decode('utf-8')
            
            return file_path, doc_base64
            
        except Exception as e:
            raise Exception(f"DOCX generation failed: {str(e)}")

    def _generate_txt(self, content: str, title: str = "", subtitle: str = "") -> tuple[str, str]:
        """Generate TXT from markdown-style content"""
        import uuid
        
        # Create output directory if it doesn't exist
        os.makedirs(self._param.output_directory, exist_ok=True)
        
        try:
            # Generate filename
            if self._param.filename:
                base_name = os.path.splitext(self._param.filename)[0]
                filename = f"{base_name}_{uuid.uuid4().hex[:8]}.txt"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"document_{timestamp}_{uuid.uuid4().hex[:8]}.txt"
            
            file_path = os.path.join(self._param.output_directory, filename)
            
            # Build text content
            text_content = []
            
            if title:
                text_content.append(title.upper())
                text_content.append("=" * len(title))
                text_content.append("")
            
            if subtitle:
                text_content.append(subtitle)
                text_content.append("-" * len(subtitle))
                text_content.append("")
            
            if self._param.add_timestamp:
                timestamp_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                text_content.append(timestamp_text)
                text_content.append("")
            
            # Add content (keep markdown formatting for readability)
            text_content.append(content)
            
            # Join and save
            final_text = '\n'.join(text_content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                # LINEAJE: runtime guardrail checks `final_text` as it flows from the agent to a file, before it is written to disk (in PDFGenerator._generate_txt).
                #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `final_text` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:965d18d4647cb1205129ed982202f85e77c61695c825970bd9cebb9b14c5d0ea'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:965d18d4647cb1205129ed982202f85e77c61695c825970bd9cebb9b14c5d0ea', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/docs_generator.py', 'line': 1562, 'function': 'PDFGenerator._generate_txt'}, 'file': 'agent/component/docs_generator.py', 'line': 1562, 'function': '_generate_txt', 'agent_name': 'PDFGenerator', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    final_text = _gr_client.enforce(_gr_site, final_text, content_type='application/json', variable_name='final_text', source_file=__file__, before_line=1562)
                except _gr_client.GuardrailUnavailableError:
                    pass
                f.write(final_text)
            
            # Encode to base64
            txt_base64 = base64.b64encode(final_text.encode('utf-8')).decode('utf-8')
            
            return file_path, txt_base64
            
        except Exception as e:
            raise Exception(f"TXT generation failed: {str(e)}")
