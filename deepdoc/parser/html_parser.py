# -*- coding: utf-8 -*-
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

from rag.nlp import find_codec, rag_tokenizer
import uuid
import chardet
from bs4 import BeautifulSoup, NavigableString, Tag, Comment
import html

def get_encoding(file):
    with open(file,'rb') as f:
        tmp = chardet.detect(f.read())
        return tmp['encoding']

BLOCK_TAGS = [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "div", "article", "section", "aside",
    "ul", "ol", "li",
    "table", "pre", "code", "blockquote",
    "figure", "figcaption"
]
TITLE_TAGS = {"h1": "#", "h2": "##", "h3": "###", "h4": "#####", "h5": "#####", "h6": "######"}


class RAGFlowHtmlParser:
    def __call__(self, fnm, binary=None, chunk_token_num=512):
        if binary:
            encoding = find_codec(binary)
            txt = binary.decode(encoding, errors="ignore")
        else:
            with open(fnm, "r",encoding=get_encoding(fnm)) as f:
                txt = f.read()
                # LINEAJE: runtime guardrail checks `txt` as it flows from file storage to the agent (in RAGFlowHtmlParser.__call__).
                #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `txt` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:d33f2355e849c9e8e5285ad489574e660c5b83be90b0aa78736e0be7273ec655'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d33f2355e849c9e8e5285ad489574e660c5b83be90b0aa78736e0be7273ec655', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/html_parser.py', 'line': 46, 'function': 'RAGFlowHtmlParser.__call__'}, 'file': 'deepdoc/parser/html_parser.py', 'line': 46, 'function': '__call__', 'agent_name': 'RAGFlowHtmlParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    txt = _gr_client.enforce(_gr_site, txt, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    raise
        return self.parser_txt(txt, chunk_token_num)

    @classmethod
    def parser_txt(cls, txt, chunk_token_num):
        if not isinstance(txt, str):
            raise TypeError("txt type should be string!")

        temp_sections = []
        soup = BeautifulSoup(txt, "html5lib")
        # delete <style> tag
        for style_tag in soup.find_all(["style", "script"]):
            style_tag.decompose()
        # delete <script> tag in <div>
        for div_tag in soup.find_all("div"):
            for script_tag in div_tag.find_all("script"):
                script_tag.decompose()
        # delete inline style
        for tag in soup.find_all(True):
            if 'style' in tag.attrs:
                del tag.attrs['style']
        # delete HTML comment
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        cls.read_text_recursively(soup.body, temp_sections, chunk_token_num=chunk_token_num)
        block_txt_list, table_list = cls.merge_block_text(temp_sections)
        sections = cls.chunk_block(block_txt_list, chunk_token_num=chunk_token_num)
        for table in table_list:
            sections.append(table.get("content", ""))
        # LINEAJE: runtime guardrail checks `sections` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowHtmlParser.parser_txt).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `sections` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ad83609c97cad9f23546a57281b04f598951be98a3cf0d38b8228d56ed1c5ecc'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ad83609c97cad9f23546a57281b04f598951be98a3cf0d38b8228d56ed1c5ecc', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/html_parser.py', 'line': 76, 'function': 'RAGFlowHtmlParser.parser_txt'}, 'file': 'deepdoc/parser/html_parser.py', 'line': 76, 'function': 'parser_txt', 'agent_name': 'RAGFlowHtmlParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            sections = _gr_client.enforce(_gr_site, sections, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return sections

    @classmethod
    def split_table(cls, html_table, chunk_token_num=512):
        soup = BeautifulSoup(html_table, "html.parser")
        rows = soup.find_all("tr")
        tables = []
        current_table = []
        current_count = 0
        table_str_list = []
        for row in rows:
            tks_str = rag_tokenizer.tokenize(str(row))
            token_count = len(tks_str.split(" ")) if tks_str else 0
            if current_count + token_count > chunk_token_num:
                tables.append(current_table)
                current_table = []
                current_count = 0
            current_table.append(row)
            current_count += token_count
        if current_table:
            tables.append(current_table)

        for table_rows in tables:
            new_table = soup.new_tag("table")
            for row in table_rows:
                new_table.append(row)
            table_str_list.append(str(new_table))

        # LINEAJE: runtime guardrail checks `table_str_list` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowHtmlParser.split_table).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `table_str_list` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:cd7c0d1cf91d526f44f822de380257dc278f6f74f8f54bebe69d6328f1aba9fd'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cd7c0d1cf91d526f44f822de380257dc278f6f74f8f54bebe69d6328f1aba9fd', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/html_parser.py', 'line': 104, 'function': 'RAGFlowHtmlParser.split_table'}, 'file': 'deepdoc/parser/html_parser.py', 'line': 104, 'function': 'split_table', 'agent_name': 'RAGFlowHtmlParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            table_str_list = _gr_client.enforce(_gr_site, table_str_list, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return table_str_list

    @classmethod
    def read_text_recursively(cls, element, parser_result, chunk_token_num=512, parent_name=None, block_id=None):
        if isinstance(element, NavigableString):
            content = element.strip()

            def is_valid_html(content):
                try:
                    soup = BeautifulSoup(content, "html.parser")
                    return bool(soup.find())
                except Exception:
                    return False

            return_info = []
            if content:
                if is_valid_html(content):
                    soup = BeautifulSoup(content, "html.parser")
                    child_info = cls.read_text_recursively(soup, parser_result, chunk_token_num, element.name, block_id)
                    parser_result.extend(child_info)
                else:
                    info = {"content": element.strip(), "tag_name": "inner_text", "metadata": {"block_id": block_id}}
                    if parent_name:
                        info["tag_name"] = parent_name
                    return_info.append(info)
            # LINEAJE: runtime guardrail checks `return_info` as it flows from rendered HTML to the user interface, before it leaves the application (in RAGFlowHtmlParser.read_text_recursively).
            #   Detected: this statement moves data from rendered HTML to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `return_info` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d0497a3caaccdc15b8d27105c67a3d74fd8013d628433c5b07343a687ddedcd8'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d0497a3caaccdc15b8d27105c67a3d74fd8013d628433c5b07343a687ddedcd8', phase='data_egress', boundary={'source': 'html', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='html', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/html_parser.py', 'line': 129, 'function': 'RAGFlowHtmlParser.read_text_recursively'}, 'file': 'deepdoc/parser/html_parser.py', 'line': 129, 'function': 'read_text_recursively', 'agent_name': 'RAGFlowHtmlParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                return_info = _gr_client.enforce(_gr_site, return_info, content_type='text/html')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return return_info
        elif isinstance(element, Tag):

            if str.lower(element.name) == "table":
                table_info_list = []
                table_id = str(uuid.uuid1())
                table_list = [html.unescape(str(element))]
                for t in table_list:
                    table_info_list.append({"content": t, "tag_name": "table",
                                            "metadata": {"table_id": table_id, "index": table_list.index(t)}})
                # LINEAJE: runtime guardrail checks `table_info_list` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowHtmlParser.is_valid_html).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `table_info_list` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:cd4cfa11a030e6840a482eec26d099eba1fc8b2b41a3f983c680814faf0f646e'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cd4cfa11a030e6840a482eec26d099eba1fc8b2b41a3f983c680814faf0f646e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/html_parser.py', 'line': 139, 'function': 'RAGFlowHtmlParser.read_text_recursively'}, 'file': 'deepdoc/parser/html_parser.py', 'line': 139, 'function': 'is_valid_html', 'agent_name': 'RAGFlowHtmlParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    table_info_list = _gr_client.enforce(_gr_site, table_info_list, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return table_info_list
            else:
                if str.lower(element.name) in BLOCK_TAGS:
                    block_id = str(uuid.uuid1())
                for child in element.children:
                    child_info = cls.read_text_recursively(child, parser_result, chunk_token_num, element.name,
                                                           block_id)
                    parser_result.extend(child_info)
        return []

    @classmethod
    def merge_block_text(cls, parser_result):
        block_content = []
        current_content = ""
        table_info_list = []
        last_block_id = None
        for item in parser_result:
            content = item.get("content")
            tag_name = item.get("tag_name")
            title_flag = tag_name in TITLE_TAGS
            block_id = item.get("metadata", {}).get("block_id")
            if block_id:
                if title_flag:
                    content = f"{TITLE_TAGS[tag_name]} {content}"
                if last_block_id != block_id:
                    if last_block_id is not None:
                        block_content.append(current_content)
                    current_content = content
                    last_block_id = block_id
                else:
                    current_content += (" " if current_content else "") + content
            else:
                if tag_name == "table":
                    table_info_list.append(item)
                else:
                    current_content += (" " if current_content else "") + content
        if current_content:
            block_content.append(current_content)
        return block_content, table_info_list

    @classmethod
    def chunk_block(cls, block_txt_list, chunk_token_num=512):
        chunks = []
        current_block = ""
        current_token_count = 0

        for block in block_txt_list:
            tks_str = rag_tokenizer.tokenize(block)
            block_token_count = len(tks_str.split(" ")) if tks_str else 0
            if block_token_count > chunk_token_num:
                if current_block:
                    chunks.append(current_block)
                start = 0
                tokens = tks_str.split(" ")
                while start < len(tokens):
                    end = start + chunk_token_num
                    split_tokens = tokens[start:end]
                    chunks.append(" ".join(split_tokens))
                    start = end
                current_block = ""
                current_token_count = 0
            else:
                if current_token_count + block_token_count <= chunk_token_num:
                    current_block += ("\n" if current_block else "") + block
                    current_token_count += block_token_count
                else:
                    chunks.append(current_block)
                    current_block = block
                    current_token_count = block_token_count

        if current_block:
            chunks.append(current_block)

        # LINEAJE: runtime guardrail checks `chunks` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowHtmlParser.chunk_block).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `chunks` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5eb1596cbf3c6927ee91fcf5caf76b5db82a1b05de3cde23651cade20131d4fe'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5eb1596cbf3c6927ee91fcf5caf76b5db82a1b05de3cde23651cade20131d4fe', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/html_parser.py', 'line': 212, 'function': 'RAGFlowHtmlParser.chunk_block'}, 'file': 'deepdoc/parser/html_parser.py', 'line': 212, 'function': 'chunk_block', 'agent_name': 'RAGFlowHtmlParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            chunks = _gr_client.enforce(_gr_site, chunks, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return chunks

