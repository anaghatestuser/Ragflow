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

import io
import logging
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse, urlunparse

from googleapiclient.errors import HttpError  # type: ignore  # type: ignore
from googleapiclient.http import MediaIoBaseDownload  # type: ignore
from pydantic import BaseModel

from common.data_source.config import DocumentSource, FileOrigin
from common.data_source.google_drive.constant import DRIVE_FOLDER_TYPE, DRIVE_SHORTCUT_TYPE
from common.data_source.google_drive.model import GDriveMimeType, GoogleDriveFileType
from common.data_source.google_drive.section_extraction import HEADING_DELIMITER
from common.data_source.google_util.resource import GoogleDriveService, get_drive_service
from common.data_source.models import ConnectorFailure, Document, DocumentFailure, ImageSection, SlimDocument, TextSection
from common.data_source.utils import get_file_ext

# Image types that should be excluded from processing
EXCLUDED_IMAGE_TYPES = [
    "image/bmp",
    "image/tiff",
    "image/gif",
    "image/svg+xml",
    "image/avif",
]

GOOGLE_MIME_TYPES_TO_EXPORT = {
    GDriveMimeType.DOC.value: "text/plain",
    GDriveMimeType.SPREADSHEET.value: "text/csv",
    GDriveMimeType.PPT.value: "text/plain",
}

GOOGLE_NATIVE_EXPORT_TARGETS: dict[str, tuple[str, str]] = {
    GDriveMimeType.DOC.value: ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    GDriveMimeType.SPREADSHEET.value: ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    GDriveMimeType.PPT.value: ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
}
GOOGLE_NATIVE_EXPORT_FALLBACK: tuple[str, str] = ("application/pdf", ".pdf")

ACCEPTED_PLAIN_TEXT_FILE_EXTENSIONS = [
    ".txt",
    ".md",
    ".mdx",
    ".conf",
    ".log",
    ".json",
    ".csv",
    ".tsv",
    ".xml",
    ".yml",
    ".yaml",
    ".sql",
]

ACCEPTED_DOCUMENT_FILE_EXTENSIONS = [
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".eml",
    ".epub",
    ".html",
]

ACCEPTED_IMAGE_FILE_EXTENSIONS = [
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
]

ALL_ACCEPTED_FILE_EXTENSIONS = ACCEPTED_PLAIN_TEXT_FILE_EXTENSIONS + ACCEPTED_DOCUMENT_FILE_EXTENSIONS + ACCEPTED_IMAGE_FILE_EXTENSIONS

MAX_RETRIEVER_EMAILS = 20
CHUNK_SIZE_BUFFER = 64  # extra bytes past the limit to read
# This is not a standard valid Unicode char, it is used by the docs advanced API to
# represent smart chips (elements like dates and doc links).
SMART_CHIP_CHAR = "\ue907"
WEB_VIEW_LINK_KEY = "webViewLink"
# Fallback templates for generating web links when Drive omits webViewLink.
_FALLBACK_WEB_VIEW_LINK_TEMPLATES = {
    GDriveMimeType.DOC.value: "https://docs.google.com/document/d/{}/view",
    GDriveMimeType.SPREADSHEET.value: "https://docs.google.com/spreadsheets/d/{}/view",
    GDriveMimeType.PPT.value: "https://docs.google.com/presentation/d/{}/view",
}


class PermissionSyncContext(BaseModel):
    """
    This is the information that is needed to sync permissions for a document.
    """

    primary_admin_email: str
    google_domain: str


def onyx_document_id_from_drive_file(file: GoogleDriveFileType) -> str:
    link = file.get(WEB_VIEW_LINK_KEY)
    if not link:
        file_id = file.get("id")
        if not file_id:
            raise KeyError(f"Google Drive file missing both '{WEB_VIEW_LINK_KEY}' and 'id' fields.")
        mime_type = file.get("mimeType", "")
        template = _FALLBACK_WEB_VIEW_LINK_TEMPLATES.get(mime_type)
        if template is None:
            link = f"https://drive.google.com/file/d/{file_id}/view"
        else:
            link = template.format(file_id)
        # LINEAJE: runtime guardrail checks `file_id` as it flows from the agent to the application log, before it is written to the log (in onyx_document_id_from_drive_file).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `file_id` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:256c122885737bde56e8811cb999661b7d7aec1afddb53b273169d6625411847'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:256c122885737bde56e8811cb999661b7d7aec1afddb53b273169d6625411847', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 112, 'function': 'onyx_document_id_from_drive_file'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 112, 'function': 'onyx_document_id_from_drive_file', 'agent_name': 'onyx_document_id_from_drive_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            file_id = _gr_client.enforce(_gr_site, file_id, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(
            "Missing webViewLink for Google Drive file with id %s. Falling back to constructed link %s",
            file_id,
            link,
        )
    parsed_url = urlparse(link)
    parsed_url = parsed_url._replace(query="")  # remove query parameters
    spl_path = parsed_url.path.split("/")
    if spl_path and (spl_path[-1] in ["edit", "view", "preview"]):
        spl_path.pop()
        parsed_url = parsed_url._replace(path="/".join(spl_path))
    # Remove query parameters and reconstruct URL
    return urlunparse(parsed_url)


def _find_nth(haystack: str, needle: str, n: int, start: int = 0) -> int:
    start = haystack.find(needle, start)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start + len(needle))
        n -= 1
    # LINEAJE: runtime guardrail checks `start` as it flows from the agent to the user interface, before it leaves the application (in _find_nth).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `start` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e1d2bcb3da45d2b15d3508cfaf5e03aac02e21ed21f9c553b373c1835e81087a'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e1d2bcb3da45d2b15d3508cfaf5e03aac02e21ed21f9c553b373c1835e81087a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 132, 'function': '_find_nth'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 132, 'function': '_find_nth', 'agent_name': '_find_nth', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        start = _gr_client.enforce(_gr_site, start, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return start


def align_basic_advanced(basic_sections: list[TextSection | ImageSection], adv_sections: list[TextSection]) -> list[TextSection | ImageSection]:
    """Align the basic sections with the advanced sections.
    In particular, the basic sections contain all content of the file,
    including smart chips like dates and doc links. The advanced sections
    are separated by section headers and contain header-based links that
    improve user experience when they click on the source in the UI.

    There are edge cases in text matching (i.e. the heading is a smart chip or
    there is a smart chip in the doc with text containing the actual heading text)
    that make the matching imperfect; this is hence done on a best-effort basis.
    """
    if len(adv_sections) <= 1:
        # LINEAJE: runtime guardrail checks `basic_sections` as it flows from the agent to the user interface, before it leaves the application (in align_basic_advanced).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `basic_sections` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:0f4e8688e044424311db77675e37e14e46b7dc8857adc82f2291d70ee543324e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0f4e8688e044424311db77675e37e14e46b7dc8857adc82f2291d70ee543324e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 147, 'function': 'align_basic_advanced'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 147, 'function': 'align_basic_advanced', 'agent_name': 'align_basic_advanced', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            basic_sections = _gr_client.enforce(_gr_site, basic_sections, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return basic_sections  # no benefit from aligning

    basic_full_text = "".join([section.text for section in basic_sections if isinstance(section, TextSection)])
    new_sections: list[TextSection | ImageSection] = []
    heading_start = 0
    for adv_ind in range(1, len(adv_sections)):
        heading = adv_sections[adv_ind].text.split(HEADING_DELIMITER)[0]
        # retrieve the longest part of the heading that is not a smart chip
        heading_key = max(heading.split(SMART_CHIP_CHAR), key=len).strip()
        if heading_key == "":
            _lineaje_payload = f"Cannot match heading: {heading}, its link will come from the following section"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in align_basic_advanced).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3c25c3ce6ec04841bf78496a207bd141b5757281b5aa7aef2b1493ae742efd7e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3c25c3ce6ec04841bf78496a207bd141b5757281b5aa7aef2b1493ae742efd7e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 157, 'function': 'align_basic_advanced'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 157, 'function': 'align_basic_advanced', 'agent_name': 'align_basic_advanced', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            continue
        heading_offset = heading.find(heading_key)

        # count occurrences of heading str in previous section
        heading_count = adv_sections[adv_ind - 1].text.count(heading_key)

        prev_start = heading_start
        heading_start = _find_nth(basic_full_text, heading_key, heading_count, start=prev_start) - heading_offset
        if heading_start < 0:
            _lineaje_payload = f"Heading key {heading_key} from heading {heading} not found in basic text"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in align_basic_advanced).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:7584a95bfc7797b4cc7fa4084b2aa64a15562661fabe2dae0c174985f5ed5d67'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7584a95bfc7797b4cc7fa4084b2aa64a15562661fabe2dae0c174985f5ed5d67', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 167, 'function': 'align_basic_advanced'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 167, 'function': 'align_basic_advanced', 'agent_name': 'align_basic_advanced', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            heading_start = prev_start
            continue

        new_sections.append(
            TextSection(
                link=adv_sections[adv_ind - 1].link,
                text=basic_full_text[prev_start:heading_start],
            )
        )

    # handle last section
    new_sections.append(TextSection(link=adv_sections[-1].link, text=basic_full_text[heading_start:]))
    # LINEAJE: runtime guardrail checks `new_sections` as it flows from the agent to the user interface, before it leaves the application (in align_basic_advanced).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `new_sections` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:f08c80ce59f79e41da7f08e29da8704476b878c00749c29cc420711e79911a11'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f08c80ce59f79e41da7f08e29da8704476b878c00749c29cc420711e79911a11', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 180, 'function': 'align_basic_advanced'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 180, 'function': 'align_basic_advanced', 'agent_name': 'align_basic_advanced', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        new_sections = _gr_client.enforce(_gr_site, new_sections, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return new_sections


def is_valid_image_type(mime_type: str) -> bool:
    """
    Check if mime_type is a valid image type.

    Args:
        mime_type: The MIME type to check

    Returns:
        True if the MIME type is a valid image type, False otherwise
    """
    return bool(mime_type) and mime_type.startswith("image/") and mime_type not in EXCLUDED_IMAGE_TYPES


def is_gdrive_image_mime_type(mime_type: str) -> bool:
    """
    Return True if the mime_type is a common image type in GDrive.
    (e.g. 'image/png', 'image/jpeg')
    """
    return is_valid_image_type(mime_type)


def _get_extension_from_file(file: GoogleDriveFileType, mime_type: str, fallback: str = ".bin") -> str:
    file_name = file.get("name") or ""
    if file_name:
        suffix = Path(file_name).suffix
        if suffix:
            # LINEAJE: runtime guardrail checks `suffix` as it flows from the agent to the user interface, before it leaves the application (in _get_extension_from_file).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `suffix` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b428d90164e4b67c3e62fbbdbecba7bc98869b140ac8ab5a78c3551d5936f454'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b428d90164e4b67c3e62fbbdbecba7bc98869b140ac8ab5a78c3551d5936f454', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 209, 'function': '_get_extension_from_file'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 209, 'function': '_get_extension_from_file', 'agent_name': '_get_extension_from_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                suffix = _gr_client.enforce(_gr_site, suffix, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return suffix

    file_extension = file.get("fileExtension")
    if file_extension:
        return f".{file_extension.lstrip('.')}"

    guessed = mimetypes.guess_extension(mime_type or "")
    if guessed:
        # LINEAJE: runtime guardrail checks `guessed` as it flows from the agent to the user interface, before it leaves the application (in _get_extension_from_file).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `guessed` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:99ef8ea891daf33816683354ae6c0e8711ca83780f578a4787832e460fa9d5d4'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:99ef8ea891daf33816683354ae6c0e8711ca83780f578a4787832e460fa9d5d4', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 217, 'function': '_get_extension_from_file'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 217, 'function': '_get_extension_from_file', 'agent_name': '_get_extension_from_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            guessed = _gr_client.enforce(_gr_site, guessed, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return guessed

    # LINEAJE: runtime guardrail checks `fallback` as it flows from the agent to the user interface, before it leaves the application (in _get_extension_from_file).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `fallback` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e8b29171fcaa4ac08092c812b716b3f482a10449179a33237a27a38d255d4c9e'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e8b29171fcaa4ac08092c812b716b3f482a10449179a33237a27a38d255d4c9e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 219, 'function': '_get_extension_from_file'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 219, 'function': '_get_extension_from_file', 'agent_name': '_get_extension_from_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        fallback = _gr_client.enforce(_gr_site, fallback, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return fallback


def _download_file_blob(
    service: GoogleDriveService,
    file: GoogleDriveFileType,
    size_threshold: int,
    allow_images: bool,
) -> tuple[bytes, str] | None:
    mime_type = file.get("mimeType", "")
    file_id = file.get("id")
    if not file_id:
        _lineaje_payload = "Encountered Google Drive file without id."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _download_file_blob).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:517f5e53ea9125fe7c097ce4d9ce0def0eb7864a711be2ed265de7583271d0eb'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:517f5e53ea9125fe7c097ce4d9ce0def0eb7864a711be2ed265de7583271d0eb', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 231, 'function': '_download_file_blob'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 231, 'function': '_download_file_blob', 'agent_name': '_download_file_blob', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning(_lineaje_payload)
        return None

    if is_gdrive_image_mime_type(mime_type) and not allow_images:
        _lineaje_payload = f"Skipping image {file.get('name')} because allow_images is False."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _download_file_blob).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:34c073267e4cedb63a90dfabce06a44d6a3fa46fa7bdaaeaa7b56ea72e7f6857'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:34c073267e4cedb63a90dfabce06a44d6a3fa46fa7bdaaeaa7b56ea72e7f6857', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 235, 'function': '_download_file_blob'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 235, 'function': '_download_file_blob', 'agent_name': '_download_file_blob', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.debug(_lineaje_payload)
        return None

    blob: bytes = b""
    extension = ".bin"
    try:
        if mime_type in GOOGLE_NATIVE_EXPORT_TARGETS:
            export_mime, extension = GOOGLE_NATIVE_EXPORT_TARGETS[mime_type]
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            blob = _download_request(request, file_id, size_threshold)
        elif mime_type.startswith("application/vnd.google-apps"):
            export_mime, extension = GOOGLE_NATIVE_EXPORT_FALLBACK
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            blob = _download_request(request, file_id, size_threshold)
        else:
            extension = _get_extension_from_file(file, mime_type)
            blob = download_request(service, file_id, size_threshold)
    except HttpError:
        raise

    if not blob:
        return None
    if not extension:
        extension = _get_extension_from_file(file, mime_type)
    return blob, extension


def download_request(service: GoogleDriveService, file_id: str, size_threshold: int) -> bytes:
    """
    Download the file from Google Drive.
    """
    # For other file types, download the file
    # Use the correct API call for downloading files
    request = service.files().get_media(fileId=file_id)
    return _download_request(request, file_id, size_threshold)


def _download_request(request: Any, file_id: str, size_threshold: int) -> bytes:
    response_bytes = io.BytesIO()
    downloader = MediaIoBaseDownload(response_bytes, request, chunksize=size_threshold + CHUNK_SIZE_BUFFER)
    done = False
    while not done:
        download_progress, done = downloader.next_chunk()
        if download_progress.resumable_progress > size_threshold:
            _lineaje_payload = f"File {file_id} exceeds size threshold of {size_threshold}. Skipping2."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _download_request).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:8d03bc364c964b1ec5817f3ce9834d7ae9ad26125d9f527c4cdc881d5d2cc020'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8d03bc364c964b1ec5817f3ce9834d7ae9ad26125d9f527c4cdc881d5d2cc020', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 279, 'function': '_download_request'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 279, 'function': '_download_request', 'agent_name': '_download_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            return bytes()

    response = response_bytes.getvalue()
    if not response:
        _lineaje_payload = f"Failed to download {file_id}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in _download_request).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d467c48f660b5f6b9b5d44bb9c487c97a433316e6b79e8a591cc86e086f3e683'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d467c48f660b5f6b9b5d44bb9c487c97a433316e6b79e8a591cc86e086f3e683', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 284, 'function': '_download_request'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 284, 'function': '_download_request', 'agent_name': '_download_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning(_lineaje_payload)
        return bytes()
    # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the user interface, before it leaves the application (in _download_request).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:0790afdcdfe4c289dc8108aac1a0345d4197d9bcb43678d5b9d204e436f179ac'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0790afdcdfe4c289dc8108aac1a0345d4197d9bcb43678d5b9d204e436f179ac', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 286, 'function': '_download_request'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 286, 'function': '_download_request', 'agent_name': '_download_request', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        response = _gr_client.enforce(_gr_site, response, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return response


def _download_and_extract_sections_basic(
    file: dict[str, str],
    service: GoogleDriveService,
    allow_images: bool,
    size_threshold: int,
) -> list[TextSection | ImageSection]:
    """Extract text and images from a Google Drive file."""
    file_id = file["id"]
    file_name = file["name"]
    mime_type = file["mimeType"]
    link = file.get(WEB_VIEW_LINK_KEY, "")

    # For non-Google files, download the file
    # Use the correct API call for downloading files
    # lazy evaluation to only download the file if necessary
    def response_call() -> bytes:
        return download_request(service, file_id, size_threshold)

    if is_gdrive_image_mime_type(mime_type):
        # Skip images if not explicitly enabled
        if not allow_images:
            return []

        # Store images for later processing
        sections: list[TextSection | ImageSection] = []

        def store_image_and_create_section(**kwargs):
            pass

        try:
            section, embedded_id = store_image_and_create_section(
                image_data=response_call(),
                file_id=file_id,
                display_name=file_name,
                media_type=mime_type,
                file_origin=FileOrigin.CONNECTOR,
                link=link,
            )
            sections.append(section)
        except Exception as e:
            _lineaje_payload = f"Failed to process image {file_name}: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext.store_image_and_create_section).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:521fdb2599cf7566247f648801539e81d726360a838ecc5556b3a698543fe405'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:521fdb2599cf7566247f648801539e81d726360a838ecc5556b3a698543fe405', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 329, 'function': '_download_and_extract_sections_basic'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 329, 'function': 'store_image_and_create_section', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `sections` as it flows from the agent to the user interface, before it leaves the application (in PermissionSyncContext.response_call).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `sections` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:fecfae371906254438a5e3f004bd239d8abafa87b8c5290110145463994b4325'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fecfae371906254438a5e3f004bd239d8abafa87b8c5290110145463994b4325', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 330, 'function': '_download_and_extract_sections_basic'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 330, 'function': 'response_call', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            sections = _gr_client.enforce(_gr_site, sections, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return sections

    # For Google Docs, Sheets, and Slides, export as plain text
    if mime_type in GOOGLE_MIME_TYPES_TO_EXPORT:
        export_mime_type = GOOGLE_MIME_TYPES_TO_EXPORT[mime_type]
        # Use the correct API call for exporting files
        request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
        response = _download_request(request, file_id, size_threshold)
        if not response:
            _lineaje_payload = f"Failed to export {file_name} as {export_mime_type}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext.store_image_and_create_section).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:1efc2f1918069aff8221ebb7bc8ab26e9b1b51e22a64b71d4555cb9b171ea6e8'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1efc2f1918069aff8221ebb7bc8ab26e9b1b51e22a64b71d4555cb9b171ea6e8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 339, 'function': '_download_and_extract_sections_basic'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 339, 'function': 'store_image_and_create_section', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            return []

        text = response.decode("utf-8")
        return [TextSection(link=link, text=text)]

    # Process based on mime type
    if mime_type == "text/plain":
        try:
            text = response_call().decode("utf-8")
            return [TextSection(link=link, text=text)]
        except UnicodeDecodeError as e:
            _lineaje_payload = f"Failed to extract text from {file_name}: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext.store_image_and_create_section).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:cfac6298fcde64985334ef61d07f4b485e831c79063119c36b8db69e2b176303'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cfac6298fcde64985334ef61d07f4b485e831c79063119c36b8db69e2b176303', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 351, 'function': '_download_and_extract_sections_basic'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 351, 'function': 'store_image_and_create_section', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            return []

    elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":

        def docx_to_text_and_images(*args, **kwargs):
            return "docx_to_text_and_images"

        text, _ = docx_to_text_and_images(io.BytesIO(response_call()))
        return [TextSection(link=link, text=text)]

    elif mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":

        def xlsx_to_text(*args, **kwargs):
            return "xlsx_to_text"

        text = xlsx_to_text(io.BytesIO(response_call()), file_name=file_name)
        return [TextSection(link=link, text=text)] if text else []

    elif mime_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":

        def pptx_to_text(*args, **kwargs):
            return "pptx_to_text"

        text = pptx_to_text(io.BytesIO(response_call()), file_name=file_name)
        return [TextSection(link=link, text=text)] if text else []

    elif mime_type == "application/pdf":

        def read_pdf_file(*args, **kwargs):
            return "read_pdf_file"

        text, _pdf_meta, images = read_pdf_file(io.BytesIO(response_call()))
        pdf_sections: list[TextSection | ImageSection] = [TextSection(link=link, text=text)]

        # Process embedded images in the PDF
        try:
            for idx, (img_data, img_name) in enumerate(images):
                section, embedded_id = store_image_and_create_section(
                    image_data=img_data,
                    file_id=f"{file_id}_img_{idx}",
                    display_name=img_name or f"{file_name} - image {idx}",
                    file_origin=FileOrigin.CONNECTOR,
                )
                pdf_sections.append(section)
        except Exception as e:
            _lineaje_payload = f"Failed to process PDF images in {file_name}: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext.read_pdf_file).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d8a3fa4e48611a590907986d7da897f113c4e030857f2d2f5a867efa31a48b33'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d8a3fa4e48611a590907986d7da897f113c4e030857f2d2f5a867efa31a48b33', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 397, 'function': '_download_and_extract_sections_basic'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 397, 'function': 'read_pdf_file', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `pdf_sections` as it flows from the agent to the user interface, before it leaves the application (in PermissionSyncContext.response_call).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `pdf_sections` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:cd89afb326c4e76200c44a0c7e19c4b6f2991500d44cd616d93ea092461d400e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cd89afb326c4e76200c44a0c7e19c4b6f2991500d44cd616d93ea092461d400e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 398, 'function': '_download_and_extract_sections_basic'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 398, 'function': 'response_call', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            pdf_sections = _gr_client.enforce(_gr_site, pdf_sections, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return pdf_sections

    # Final attempt at extracting text
    file_ext = get_file_ext(file.get("name", ""))
    if file_ext not in ALL_ACCEPTED_FILE_EXTENSIONS:
        _lineaje_payload = f"Skipping file {file.get('name')} due to extension."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext.response_call).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3aade2709ff974f3ac50310e888f6271f2faf51962e2b6b1ccca93200f235e68'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3aade2709ff974f3ac50310e888f6271f2faf51962e2b6b1ccca93200f235e68', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 403, 'function': '_download_and_extract_sections_basic'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 403, 'function': 'response_call', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning(_lineaje_payload)
        return []

    try:

        def extract_file_text(*args, **kwargs):
            return "extract_file_text"

        text = extract_file_text(io.BytesIO(response_call()), file_name)
        return [TextSection(link=link, text=text)]
    except Exception as e:
        _lineaje_payload = f"Failed to extract text from {file_name}: {e}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext.response_call).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9f7a8e9737adb5a8bcd9a4ac2a7e051ea1c46166e056e6fe0896e21a1dc03ee0'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9f7a8e9737adb5a8bcd9a4ac2a7e051ea1c46166e056e6fe0896e21a1dc03ee0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 414, 'function': '_download_and_extract_sections_basic'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 414, 'function': 'response_call', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.warning(_lineaje_payload)
        return []


def _convert_drive_item_to_document(
    creds: Any,
    allow_images: bool,
    size_threshold: int,
    retriever_email: str,
    file: GoogleDriveFileType,
    # if not specified, we will not sync permissions
    # will also be a no-op if EE is not enabled
    permission_sync_context: PermissionSyncContext | None,
) -> Document | ConnectorFailure | None:
    """
    Main entry point for converting a Google Drive file => Document object.
    """

    def _get_drive_service() -> GoogleDriveService:
        return get_drive_service(creds, user_email=retriever_email)

    doc_id = "unknown"
    link = file.get(WEB_VIEW_LINK_KEY)

    try:
        if file.get("mimeType") in [DRIVE_SHORTCUT_TYPE, DRIVE_FOLDER_TYPE]:
            _lineaje_payload = "Skipping shortcut/folder."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext._get_drive_service).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f2bb7bd4f001d9acafbb9a5bd7633aded2ec19b7fc6eacb4a5ec56a43c58680f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f2bb7bd4f001d9acafbb9a5bd7633aded2ec19b7fc6eacb4a5ec56a43c58680f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 440, 'function': '_convert_drive_item_to_document'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 440, 'function': '_get_drive_service', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            return None

        size_str = file.get("size")
        if size_str:
            try:
                size_int = int(size_str)
            except ValueError:
                _lineaje_payload = f"Parsing string to int failed: size_str={size_str}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext._get_drive_service).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:271056e8cb7695bb31ad4b70ad969e56703754d195a66dc4778d2b7cd9f626cf'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:271056e8cb7695bb31ad4b70ad969e56703754d195a66dc4778d2b7cd9f626cf', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 448, 'function': '_convert_drive_item_to_document'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 448, 'function': '_get_drive_service', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.warning(_lineaje_payload)
            else:
                if size_int > size_threshold:
                    _lineaje_payload = f"{file.get('name')} exceeds size threshold of {size_threshold}. Skipping."
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext._get_drive_service).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:924423399c5535eb15708ca8707afb8aa9a993edd0f5050d8af3db2ab697248c'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:924423399c5535eb15708ca8707afb8aa9a993edd0f5050d8af3db2ab697248c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 451, 'function': '_convert_drive_item_to_document'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 451, 'function': '_get_drive_service', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.warning(_lineaje_payload)
                    return None

        blob_and_ext = _download_file_blob(
            service=_get_drive_service(),
            file=file,
            size_threshold=size_threshold,
            allow_images=allow_images,
        )

        if blob_and_ext is None:
            _lineaje_payload = f"Skipping file {file.get('name')} due to incompatible type or download failure."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext._get_drive_service).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:2215e270c3c0c335cb1158a81ccf5b9cde4569dbe8141744ae9dfd47ccf08fef'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2215e270c3c0c335cb1158a81ccf5b9cde4569dbe8141744ae9dfd47ccf08fef', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 462, 'function': '_convert_drive_item_to_document'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 462, 'function': '_get_drive_service', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            return None

        blob, extension = blob_and_ext
        if not blob:
            _lineaje_payload = f"Failed to download {file.get('name')}. Skipping."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext._get_drive_service).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:a7ed76f9d1ab5763a54855a65c35937a3e375c3712e7e1b5cf4b36ea4dbef896'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a7ed76f9d1ab5763a54855a65c35937a3e375c3712e7e1b5cf4b36ea4dbef896', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 467, 'function': '_convert_drive_item_to_document'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 467, 'function': '_get_drive_service', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            return None

        doc_id = onyx_document_id_from_drive_file(file)
        modified_time = file.get("modifiedTime")
        try:
            doc_updated_at = datetime.fromisoformat(modified_time.replace("Z", "+00:00")) if modified_time else datetime.now(timezone.utc)
        except ValueError:
            _lineaje_payload = f"Failed to parse modifiedTime for {file.get('name')}, defaulting to current time."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext._get_drive_service).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e259d20d4ce056b9f6bcb399c523480fa1b47a552e22a28c8b8057cc0cf22252'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e259d20d4ce056b9f6bcb399c523480fa1b47a552e22a28c8b8057cc0cf22252', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 475, 'function': '_convert_drive_item_to_document'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 475, 'function': '_get_drive_service', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            doc_updated_at = datetime.now(timezone.utc)

        return Document(
            id=doc_id,
            source=DocumentSource.GOOGLE_DRIVE,
            semantic_identifier=file.get("name", ""),
            blob=blob,
            extension=extension,
            size_bytes=len(blob),
            doc_updated_at=doc_updated_at,
        )
    except Exception as e:
        doc_id = "unknown"
        try:
            doc_id = onyx_document_id_from_drive_file(file)
        except Exception as e2:
            _lineaje_payload = f"Error getting document id from file: {e2}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext._get_drive_service).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:feb3fd1e54ced750383d3220693825b3b74c3f529c78d547661fedc77514df2c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:feb3fd1e54ced750383d3220693825b3b74c3f529c78d547661fedc77514df2c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 492, 'function': '_convert_drive_item_to_document'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 492, 'function': '_get_drive_service', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)

        file_name = file.get("name", doc_id)
        error_str = f"Error converting file '{file_name}' to Document as {retriever_email}: {e}"
        if isinstance(e, HttpError) and e.status_code == 403:
            _lineaje_payload = f"Uncommon permissions error while downloading file. User {retriever_email} was able to see file {file_name} but cannot download it."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext._get_drive_service).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:93a11c96447f07cedb589f5ed7900b69f8cb40ac5609efee042991bfe771d8e7'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:93a11c96447f07cedb589f5ed7900b69f8cb40ac5609efee042991bfe771d8e7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 497, 'function': '_convert_drive_item_to_document'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 497, 'function': '_get_drive_service', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(_lineaje_payload)
            # LINEAJE: runtime guardrail checks `error_str` as it flows from the agent to the application log, before it is written to the log (in PermissionSyncContext._get_drive_service).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_str` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:10e65626795c611113926149777e0e8c9a39adee6befba3beafca38b0db6729f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:10e65626795c611113926149777e0e8c9a39adee6befba3beafca38b0db6729f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 498, 'function': '_convert_drive_item_to_document'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 498, 'function': '_get_drive_service', 'agent_name': 'PermissionSyncContext', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                error_str = _gr_client.enforce(_gr_site, error_str, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(error_str)

        return ConnectorFailure(
            failed_document=DocumentFailure(
                document_id=doc_id,
                document_link=link,
            ),
            failed_entity=None,
            failure_message=error_str,
            exception=e,
        )


def convert_drive_item_to_document(
    creds: Any,
    allow_images: bool,
    size_threshold: int,
    # if not specified, we will not sync permissions
    # will also be a no-op if EE is not enabled
    permission_sync_context: PermissionSyncContext | None,
    retriever_emails: list[str],
    file: GoogleDriveFileType,
) -> Document | ConnectorFailure | None:
    """
    Attempt to convert a drive item to a document with each retriever email
    in order. returns upon a successful retrieval or a non-403 error.

    We used to always get the user email from the file owners when available,
    but this was causing issues with shared folders where the owner was not included in the service account
    now we use the email of the account that successfully listed the file. There are cases where a
    user that can list a file cannot download it, so we retry with file owners and admin email.
    """
    first_error = None
    doc_or_failure = None
    retriever_emails = retriever_emails[:MAX_RETRIEVER_EMAILS]
    # use seen instead of list(set()) to avoid re-ordering the retriever emails
    seen = set()
    for retriever_email in retriever_emails:
        if retriever_email in seen:
            continue
        seen.add(retriever_email)
        doc_or_failure = _convert_drive_item_to_document(
            creds,
            allow_images,
            size_threshold,
            retriever_email,
            file,
            permission_sync_context,
        )

        # There are a variety of permissions-based errors that occasionally occur
        # when retrieving files. Often when these occur, there is another user
        # that can successfully retrieve the file, so we try the next user.
        if doc_or_failure is None or isinstance(doc_or_failure, Document) or not (isinstance(doc_or_failure.exception, HttpError) and doc_or_failure.exception.status_code in [401, 403, 404]):
            # LINEAJE: runtime guardrail checks `doc_or_failure` as it flows from the agent to the user interface, before it leaves the application (in convert_drive_item_to_document).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `doc_or_failure` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:bd6194a5fc1098c6d766affed062889ffd6bafa157f7456b286eb55a706cccb5'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bd6194a5fc1098c6d766affed062889ffd6bafa157f7456b286eb55a706cccb5', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 552, 'function': 'convert_drive_item_to_document'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 552, 'function': 'convert_drive_item_to_document', 'agent_name': 'convert_drive_item_to_document', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                doc_or_failure = _gr_client.enforce(_gr_site, doc_or_failure, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return doc_or_failure

        if first_error is None:
            first_error = doc_or_failure
        else:
            first_error.failure_message += f"\n\n{doc_or_failure.failure_message}"

    if first_error and isinstance(first_error.exception, HttpError) and first_error.exception.status_code == 403:
        # This SHOULD happen very rarely, and we don't want to break the indexing process when
        # a high volume of 403s occurs early. We leave a verbose log to help investigate.
        _lineaje_payload = f"Skipping file id: {file.get('id')} name: {file.get('name')} due to 403 error.Attempted to retrieve with {retriever_emails},got the following errors: {first_error.failure_message}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in convert_drive_item_to_document).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:110fe3e61935bda3d7de180f7623a59319fc277207ebcb3d12437e2e86c4465e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:110fe3e61935bda3d7de180f7623a59319fc277207ebcb3d12437e2e86c4465e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 562, 'function': 'convert_drive_item_to_document'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 562, 'function': 'convert_drive_item_to_document', 'agent_name': 'convert_drive_item_to_document', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(
            _lineaje_payload
        )
        return None
    # LINEAJE: runtime guardrail checks `first_error` as it flows from the agent to the user interface, before it leaves the application (in convert_drive_item_to_document).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `first_error` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e9cd1174492d982e17370720339866eb62cfc2aa1ec5dd57f700f4a84009faef'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e9cd1174492d982e17370720339866eb62cfc2aa1ec5dd57f700f4a84009faef', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 566, 'function': 'convert_drive_item_to_document'}, 'file': 'common/data_source/google_drive/doc_conversion.py', 'line': 566, 'function': 'convert_drive_item_to_document', 'agent_name': 'convert_drive_item_to_document', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        first_error = _gr_client.enforce(_gr_site, first_error, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return first_error


def build_slim_document(
    creds: Any,
    file: GoogleDriveFileType,
    # if not specified, we will not sync permissions
    # will also be a no-op if EE is not enabled
    permission_sync_context: PermissionSyncContext | None,
) -> SlimDocument | None:
    if file.get("mimeType") in [DRIVE_FOLDER_TYPE, DRIVE_SHORTCUT_TYPE]:
        return None

    owner_email = cast(str | None, file.get("owners", [{}])[0].get("emailAddress"))

    def _get_external_access_for_raw_gdrive_file(*args, **kwargs):
        return None

    external_access = (
        _get_external_access_for_raw_gdrive_file(
            file=file,
            company_domain=permission_sync_context.google_domain,
            retriever_drive_service=(
                get_drive_service(
                    creds,
                    user_email=owner_email,
                )
                if owner_email
                else None
            ),
            admin_drive_service=get_drive_service(
                creds,
                user_email=permission_sync_context.primary_admin_email,
            ),
        )
        if permission_sync_context
        else None
    )
    return SlimDocument(
        id=onyx_document_id_from_drive_file(file),
        external_access=external_access,
    )
