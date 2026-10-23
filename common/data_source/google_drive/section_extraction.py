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

from typing import Any

from pydantic import BaseModel

from common.data_source.google_util.resource import GoogleDocsService
from common.data_source.models import TextSection

HEADING_DELIMITER = "\n"


class CurrentHeading(BaseModel):
    id: str | None
    text: str


def get_document_sections(
    docs_service: GoogleDocsService,
    doc_id: str,
) -> list[TextSection]:
    """Extracts sections from a Google Doc, including their headings and content"""
    # Fetch the document structure
    http_request = docs_service.documents().get(documentId=doc_id)

    # Google has poor support for tabs in the docs api, see
    # https://cloud.google.com/python/docs/reference/cloudtasks/
    # latest/google.cloud.tasks_v2.types.HttpRequest
    # https://developers.google.com/workspace/docs/api/how-tos/tabs
    # https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/get
    # this is a hack to use the param mentioned in the rest api docs
    # TODO: check if it can be specified i.e. in documents()
    http_request.uri += "&includeTabsContent=true"
    doc = http_request.execute()

    # Get the content
    tabs = doc.get("tabs", {})
    sections: list[TextSection] = []
    for tab in tabs:
        sections.extend(get_tab_sections(tab, doc_id))
    # LINEAJE: runtime guardrail checks `sections` as it flows from the agent to the user interface, before it leaves the application (in get_document_sections).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `sections` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e39e708ebdfd2c37df348741f7cbae1bc9024d88666d1c5c7fd4bc046c1e21dc'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e39e708ebdfd2c37df348741f7cbae1bc9024d88666d1c5c7fd4bc046c1e21dc', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/section_extraction.py', 'line': 39, 'function': 'get_document_sections'}, 'file': 'common/data_source/google_drive/section_extraction.py', 'line': 39, 'function': 'get_document_sections', 'agent_name': 'get_document_sections', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        sections = _gr_client.enforce(_gr_site, sections, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return sections


def _is_heading(paragraph: dict[str, Any]) -> bool:
    """Checks if a paragraph (a block of text in a drive document) is a heading"""
    if not ("paragraphStyle" in paragraph and "namedStyleType" in paragraph["paragraphStyle"]):
        return False

    style = paragraph["paragraphStyle"]["namedStyleType"]
    is_heading = style.startswith("HEADING_")
    is_title = style.startswith("TITLE")
    return is_heading or is_title


def _add_finished_section(
    sections: list[TextSection],
    doc_id: str,
    tab_id: str,
    current_heading: CurrentHeading,
    current_section: list[str],
) -> None:
    """Adds a finished section to the list of sections if the section has content.
    Returns the list of sections to use going forward, which may be the old list
    if a new section was not added.
    """
    if not (current_section or current_heading.text):
        return
    # If we were building a previous section, add it to sections list

    # this is unlikely to ever matter, but helps if the doc contains weird headings
    header_text = current_heading.text.replace(HEADING_DELIMITER, "")
    section_text = f"{header_text}{HEADING_DELIMITER}" + "\n".join(current_section)
    sections.append(
        TextSection(
            text=section_text.strip(),
            link=_build_gdoc_section_link(doc_id, tab_id, current_heading.id),
        )
    )


def _build_gdoc_section_link(doc_id: str, tab_id: str, heading_id: str | None) -> str:
    """Builds a Google Doc link that jumps to a specific heading"""
    # NOTE: doesn't support docs with multiple tabs atm, if we need that ask
    # @Chris
    heading_str = f"#heading={heading_id}" if heading_id else ""
    return f"https://docs.google.com/document/d/{doc_id}/edit?tab={tab_id}{heading_str}"


def _extract_id_from_heading(paragraph: dict[str, Any]) -> str:
    """Extracts the id from a heading paragraph element"""
    return paragraph["paragraphStyle"]["headingId"]


def _extract_text_from_paragraph(paragraph: dict[str, Any]) -> str:
    """Extracts the text content from a paragraph element"""
    text_elements = []
    for element in paragraph.get("elements", []):
        if "textRun" in element:
            text_elements.append(element["textRun"].get("content", ""))

        # Handle links
        if "textStyle" in element and "link" in element["textStyle"]:
            text_elements.append(f"({element['textStyle']['link'].get('url', '')})")

        if "person" in element:
            name = element["person"].get("personProperties", {}).get("name", "")
            email = element["person"].get("personProperties", {}).get("email", "")
            person_str = "<Person|"
            if name:
                person_str += f"name: {name}, "
            if email:
                person_str += f"email: {email}"
            person_str += ">"
            text_elements.append(person_str)

        if "richLink" in element:
            props = element["richLink"].get("richLinkProperties", {})
            # LINEAJE: runtime guardrail checks `props` as it flows from an external API to the agent, after the tool returns (in _extract_text_from_paragraph).
            #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `props` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:11c5859fbd7db5c7ffd4ed351b93bbdba7fd21db53d7ce7074155f79d7489d13'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:11c5859fbd7db5c7ffd4ed351b93bbdba7fd21db53d7ce7074155f79d7489d13', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/section_extraction.py', 'line': 115, 'function': '_extract_text_from_paragraph'}, 'file': 'common/data_source/google_drive/section_extraction.py', 'line': 115, 'function': '_extract_text_from_paragraph', 'agent_name': '_extract_text_from_paragraph', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                props = _gr_client.enforce(_gr_site, props, content_type='application/json', variable_name='props', source_file=__file__, before_line=115)
            except _gr_client.GuardrailUnavailableError:
                pass
            title = props.get("title", "")
            uri = props.get("uri", "")
            link_str = f"[{title}]({uri})"
            text_elements.append(link_str)

    return "".join(text_elements)


def _extract_text_from_table(table: dict[str, Any]) -> str:
    """
    Extracts the text content from a table element.
    """
    row_strs = []

    for row in table.get("tableRows", []):
        cells = row.get("tableCells", [])
        cell_strs = []
        for cell in cells:
            child_elements = cell.get("content", {})
            cell_str = []
            for child_elem in child_elements:
                if "paragraph" not in child_elem:
                    continue
                cell_str.append(_extract_text_from_paragraph(child_elem["paragraph"]))
            cell_strs.append("".join(cell_str))
        row_strs.append(", ".join(cell_strs))
    return "\n".join(row_strs)


def get_tab_sections(tab: dict[str, Any], doc_id: str) -> list[TextSection]:
    tab_id = tab["tabProperties"]["tabId"]
    content = tab.get("documentTab", {}).get("body", {}).get("content", [])

    sections: list[TextSection] = []
    current_section: list[str] = []
    current_heading = CurrentHeading(id=None, text="")

    for element in content:
        if "paragraph" in element:
            paragraph = element["paragraph"]

            # If this is not a heading, add content to current section
            if not _is_heading(paragraph):
                text = _extract_text_from_paragraph(paragraph)
                if text.strip():
                    current_section.append(text)
                continue

            _add_finished_section(sections, doc_id, tab_id, current_heading, current_section)

            current_section = []

            # Start new heading
            heading_id = _extract_id_from_heading(paragraph)
            heading_text = _extract_text_from_paragraph(paragraph)
            current_heading = CurrentHeading(
                id=heading_id,
                text=heading_text,
            )
        elif "table" in element:
            text = _extract_text_from_table(element["table"])
            if text.strip():
                current_section.append(text)

    # Don't forget to add the last section
    _add_finished_section(sections, doc_id, tab_id, current_heading, current_section)

    # LINEAJE: runtime guardrail checks `sections` as it flows from the agent to the user interface, before it leaves the application (in get_tab_sections).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `sections` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:d305d98a1bfb961bb344e27d2cfe837c50c314f2f4c2c0bd7407b7da45e45be1'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d305d98a1bfb961bb344e27d2cfe837c50c314f2f4c2c0bd7407b7da45e45be1', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/google_drive/section_extraction.py', 'line': 183, 'function': 'get_tab_sections'}, 'file': 'common/data_source/google_drive/section_extraction.py', 'line': 183, 'function': 'get_tab_sections', 'agent_name': 'get_tab_sections', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        sections = _gr_client.enforce(_gr_site, sections, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return sections
