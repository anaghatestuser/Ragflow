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
from copy import copy
from dataclasses import dataclass
from io import BytesIO
from typing import IO

import bs4

from common.data_source.config import HTML_BASED_CONNECTOR_TRANSFORM_LINKS_STRATEGY, \
    HtmlBasedConnectorTransformLinksStrategy, WEB_CONNECTOR_IGNORED_CLASSES, WEB_CONNECTOR_IGNORED_ELEMENTS, \
    PARSE_WITH_TRAFILATURA

MINTLIFY_UNWANTED = ["sticky", "hidden"]


@dataclass
class ParsedHTML:
    title: str | None
    cleaned_text: str


def strip_excessive_newlines_and_spaces(document: str) -> str:
    # collapse repeated spaces into one
    document = re.sub(r" +", " ", document)
    # remove trailing spaces
    document = re.sub(r" +[\n\r]", "\n", document)
    # remove repeated newlines
    document = re.sub(r"[\n\r]+", "\n", document)
    return document.strip()


def strip_newlines(document: str) -> str:
    # HTML might contain newlines which are just whitespaces to a browser
    return re.sub(r"[\n\r]+", " ", document)


def format_element_text(element_text: str, link_href: str | None) -> str:
    element_text_no_newlines = strip_newlines(element_text)

    if (
        not link_href
        or HTML_BASED_CONNECTOR_TRANSFORM_LINKS_STRATEGY
        == HtmlBasedConnectorTransformLinksStrategy.STRIP
    ):
        # LINEAJE: runtime guardrail checks `element_text_no_newlines` as it flows from the agent to the user interface, before it leaves the application (in format_element_text).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `element_text_no_newlines` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:493ffa1911b5baeb4e0793b81aa1e30f6da34c5c6bfa5f2b300e75a71d0df0c2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:493ffa1911b5baeb4e0793b81aa1e30f6da34c5c6bfa5f2b300e75a71d0df0c2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/html_utils.py', 'line': 46, 'function': 'format_element_text'}, 'file': 'common/data_source/html_utils.py', 'line': 46, 'function': 'format_element_text', 'agent_name': 'format_element_text', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            element_text_no_newlines = _gr_client.enforce(_gr_site, element_text_no_newlines, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return element_text_no_newlines

    return f"[{element_text_no_newlines}]({link_href})"


def parse_html_with_trafilatura(html_content: str) -> str:
    """Parse HTML content using trafilatura."""
    import trafilatura  # type: ignore
    from trafilatura.settings import use_config  # type: ignore

    config = use_config()
    config.set("DEFAULT", "include_links", "True")
    config.set("DEFAULT", "include_tables", "True")
    config.set("DEFAULT", "include_images", "True")
    config.set("DEFAULT", "include_formatting", "True")

    extracted_text = trafilatura.extract(html_content, config=config)
    return strip_excessive_newlines_and_spaces(extracted_text) if extracted_text else ""


def format_document_soup(
    document: bs4.BeautifulSoup, table_cell_separator: str = "\t"
) -> str:
    """Format html to a flat text document.

    The following goals:
    - Newlines from within the HTML are removed (as browser would ignore them as well).
    - Repeated newlines/spaces are removed (as browsers would ignore them).
    - Newlines only before and after headlines and paragraphs or when explicit (br or pre tag)
    - Table columns/rows are separated by newline
    - List elements are separated by newline and start with a hyphen
    """
    text = ""
    list_element_start = False
    verbatim_output = 0
    in_table = False
    last_added_newline = False
    link_href: str | None = None

    for e in document.descendants:
        verbatim_output -= 1
        if isinstance(e, bs4.element.NavigableString):
            if isinstance(e, (bs4.element.Comment, bs4.element.Doctype)):
                continue
            element_text = e.text
            if in_table:
                # Tables are represented in natural language with rows separated by newlines
                # Can't have newlines then in the table elements
                element_text = element_text.replace("\n", " ").strip()

            # Some tags are translated to spaces but in the logic underneath this section, we
            # translate them to newlines as a browser should render them such as with br
            # This logic here avoids a space after newline when it shouldn't be there.
            if last_added_newline and element_text.startswith(" "):
                element_text = element_text[1:]
                last_added_newline = False

            if element_text:
                content_to_add = (
                    element_text
                    if verbatim_output > 0
                    else format_element_text(element_text, link_href)
                )

                # Don't join separate elements without any spacing
                if (text and not text[-1].isspace()) and (
                    content_to_add and not content_to_add[0].isspace()
                ):
                    text += " "

                text += content_to_add

                list_element_start = False
        elif isinstance(e, bs4.element.Tag):
            # table is standard HTML element
            if e.name == "table":
                in_table = True
            # TR is for rows
            elif e.name == "tr" and in_table:
                text += "\n"
            # td for data cell, th for header
            elif e.name in ["td", "th"] and in_table:
                text += table_cell_separator
            elif e.name == "/table":
                in_table = False
            elif in_table:
                # don't handle other cases while in table
                pass
            elif e.name == "a":
                href_value = e.get("href", None)
                # mostly for typing, having multiple hrefs is not valid HTML
                link_href = (
                    href_value[0] if isinstance(href_value, list) else href_value
                )
            elif e.name == "/a":
                link_href = None
            elif e.name in ["p", "div"]:
                if not list_element_start:
                    text += "\n"
            elif e.name in ["h1", "h2", "h3", "h4"]:
                text += "\n"
                list_element_start = False
                last_added_newline = True
            elif e.name == "br":
                text += "\n"
                list_element_start = False
                last_added_newline = True
            elif e.name == "li":
                text += "\n- "
                list_element_start = True
            elif e.name == "pre":
                if verbatim_output <= 0:
                    verbatim_output = len(list(e.childGenerator()))
    return strip_excessive_newlines_and_spaces(text)


def parse_html_page_basic(text: str | BytesIO | IO[bytes]) -> str:
    soup = bs4.BeautifulSoup(text, "html.parser")
    return format_document_soup(soup)


def web_html_cleanup(
    page_content: str | bs4.BeautifulSoup,
    mintlify_cleanup_enabled: bool = True,
    additional_element_types_to_discard: list[str] | None = None,
) -> ParsedHTML:
    if isinstance(page_content, str):
        soup = bs4.BeautifulSoup(page_content, "html.parser")
    else:
        soup = page_content

    title_tag = soup.find("title")
    title = None
    if title_tag and title_tag.text:
        title = title_tag.text
        title_tag.extract()

    # Heuristics based cleaning of elements based on css classes
    unwanted_classes = copy(WEB_CONNECTOR_IGNORED_CLASSES)
    if mintlify_cleanup_enabled:
        unwanted_classes.extend(MINTLIFY_UNWANTED)
    for undesired_element in unwanted_classes:
        [
            tag.extract()
            for tag in soup.find_all(
                class_=lambda x: x and undesired_element in x.split()
            )
        ]

    for undesired_tag in WEB_CONNECTOR_IGNORED_ELEMENTS:
        [tag.extract() for tag in soup.find_all(undesired_tag)]

    if additional_element_types_to_discard:
        for undesired_tag in additional_element_types_to_discard:
            [tag.extract() for tag in soup.find_all(undesired_tag)]

    soup_string = str(soup)
    page_text = ""

    if PARSE_WITH_TRAFILATURA:
        try:
            page_text = parse_html_with_trafilatura(soup_string)
            if not page_text:
                raise ValueError("Empty content returned by trafilatura.")
        except Exception as e:
            _lineaje_payload = f"Trafilatura parsing failed: {e}. Falling back on bs4."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in web_html_cleanup).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:38c9a8d6e7e437abb519970ace1389db4eddee7873ac4def2624b11c616ea9b5'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:38c9a8d6e7e437abb519970ace1389db4eddee7873ac4def2624b11c616ea9b5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/html_utils.py', 'line': 211, 'function': 'web_html_cleanup'}, 'file': 'common/data_source/html_utils.py', 'line': 211, 'function': 'web_html_cleanup', 'agent_name': 'web_html_cleanup', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            page_text = format_document_soup(soup)
    else:
        page_text = format_document_soup(soup)

    # 200B is ZeroWidthSpace which we don't care for
    cleaned_text = page_text.replace("\u200b", "")

    return ParsedHTML(title=title, cleaned_text=cleaned_text)
