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
import asyncio
import nest_asyncio
nest_asyncio.apply()
import inspect
import json
import os
import random
import re
import logging
import tempfile
from functools import partial
from typing import Any

from agent.component.base import ComponentBase, ComponentParamBase
from jinja2 import Template as Jinja2Template

from common.connection_utils import timeout
from common.misc_utils import get_uuid
from common import settings


class MessageParam(ComponentParamBase):
    """
    Define the Message component parameters.
    """
    def __init__(self):
        super().__init__()
        self.content = []
        self.stream = True
        self.output_format = None  # default output format
        self.auto_play = False
        self.outputs = {
            "content": {
                "type": "str"
            }
        }

    def check(self):
        self.check_empty(self.content, "[Message] Content")
        self.check_boolean(self.stream, "[Message] stream")
        return True


class Message(ComponentBase):
    component_name = "Message"

    def get_input_elements(self) -> dict[str, Any]:
        return self.get_input_elements_from_text("".join(self._param.content))

    def get_kwargs(self, script:str, kwargs:dict = {}, delimiter:str=None) -> tuple[str, dict[str, str | list | Any]]:
        for k,v in self.get_input_elements_from_text(script).items():
            if k in kwargs:
                continue
            v = v["value"]
            if not v:
                v = ""
            ans = ""
            if isinstance(v, partial):
                iter_obj = v()
                if inspect.isasyncgen(iter_obj):
                    ans = asyncio.run(self._consume_async_gen(iter_obj))
                else:
                    for t in iter_obj:
                        ans += t
            elif isinstance(v, list) and delimiter:
                ans = delimiter.join([str(vv) for vv in v])
            elif not isinstance(v, str):
                try:
                    # LINEAJE: runtime guardrail checks `v` as it flows from the agent to an external endpoint, before it leaves the application (in Message.get_kwargs).
                    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `v` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:66096fcf0030423449a1d4ddedf1fc211c897910127e1e0adc7afbb08ebd42e5'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:66096fcf0030423449a1d4ddedf1fc211c897910127e1e0adc7afbb08ebd42e5', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/message.py', 'line': 84, 'function': 'Message.get_kwargs'}, 'file': 'agent/component/message.py', 'line': 84, 'function': 'get_kwargs', 'agent_name': 'Message', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        v = _gr_client.enforce(_gr_site, v, content_type='application/json', variable_name='v', source_file=__file__, before_line=84)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    ans = json.dumps(v, ensure_ascii=False)
                except Exception:
                    pass
            else:
                ans = v
            if not ans:
                ans = ""
            kwargs[k] = ans
            self.set_input_value(k, ans)

        _kwargs = {}
        for n, v in kwargs.items():
            _n = re.sub("[@:.]", "_", n)
            script = re.sub(r"\{%s\}" % re.escape(n), _n, script)
            _kwargs[_n] = v
        return script, _kwargs

    async def _consume_async_gen(self, agen):
        buf = ""
        async for t in agen:
            buf += t
        # LINEAJE: runtime guardrail checks `buf` as it flows from the agent to the user interface, before it leaves the application (in Message._consume_async_gen).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `buf` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1b0123ec7d9e4f6b538784f48b842508fc8153df216d24f5fdde57e916724b3d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1b0123ec7d9e4f6b538784f48b842508fc8153df216d24f5fdde57e916724b3d', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/message.py', 'line': 105, 'function': 'Message._consume_async_gen'}, 'file': 'agent/component/message.py', 'line': 105, 'function': '_consume_async_gen', 'agent_name': 'Message', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            buf = _gr_client.enforce(_gr_site, buf, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return buf

    async def _stream(self, rand_cnt:str):
        s = 0
        all_content = ""
        cache = {}
        for r in re.finditer(self.variable_ref_patt, rand_cnt, flags=re.DOTALL):
            if self.check_if_canceled("Message streaming"):
                return

            all_content += rand_cnt[s: r.start()]
            yield rand_cnt[s: r.start()]
            s = r.end()
            exp = r.group(1)
            if exp in cache:
                yield cache[exp]
                all_content += cache[exp]
                continue

            v = self._canvas.get_variable_value(exp)
            if v is None:
                v = ""
            if isinstance(v, partial):
                cnt = ""
                iter_obj = v()
                if inspect.isasyncgen(iter_obj):
                    async for t in iter_obj:
                        if self.check_if_canceled("Message streaming"):
                            return

                        all_content += t
                        cnt += t
                        yield t
                else:
                    for t in iter_obj:
                        if self.check_if_canceled("Message streaming"):
                            return

                        all_content += t
                        cnt += t
                        yield t
                self.set_input_value(exp, cnt)
                continue
            elif inspect.isawaitable(v):
                v = await v
            elif not isinstance(v, str):
                try:
                    # LINEAJE: runtime guardrail checks `v` as it flows from the agent to an external endpoint, before it leaves the application (in Message._stream).
                    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `v` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:daa75113900bbf1c9d458006f6babd7303beace7dfbec23beb81b9addbb5f811'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:daa75113900bbf1c9d458006f6babd7303beace7dfbec23beb81b9addbb5f811', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/message.py', 'line': 152, 'function': 'Message._stream'}, 'file': 'agent/component/message.py', 'line': 152, 'function': '_stream', 'agent_name': 'Message', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        v = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, v, content_type='application/json', variable_name='v', source_file=__file__, before_line=152))
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    v = json.dumps(v, ensure_ascii=False)
                except Exception:
                    v = str(v)
            yield v
            self.set_input_value(exp, v)
            all_content += v
            cache[exp] = v

        if s < len(rand_cnt):
            if self.check_if_canceled("Message streaming"):
                return

            all_content += rand_cnt[s: ]
            yield rand_cnt[s: ]

        self.set_output("content", all_content)
        self._convert_content(all_content)

    def _is_jinjia2(self, content:str) -> bool:
        patt = [
            r"\{%.*%\}", "{{", "}}"
        ]
        return any([re.search(p, content) for p in patt])

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10*60)))
    def _invoke(self, **kwargs):
        if self.check_if_canceled("Message processing"):
            return

        rand_cnt = random.choice(self._param.content)
        if self._param.stream and not self._is_jinjia2(rand_cnt):
            self.set_output("content", partial(self._stream, rand_cnt))
            return

        rand_cnt, kwargs = self.get_kwargs(rand_cnt, kwargs)
        template = Jinja2Template(rand_cnt)
        try:
            content = template.render(kwargs)
        except Exception:
            pass

        if self.check_if_canceled("Message processing"):
            return

        for n, v in kwargs.items():
            content = re.sub(n, v, content)

        self.set_output("content", content)
        self._convert_content(content)

    def thoughts(self) -> str:
        return ""

    def _parse_markdown_table_lines(self, table_lines: list):
        """
        Parse a list of Markdown table lines into a pandas DataFrame.
        
        Args:
            table_lines: List of strings, each representing a row in the Markdown table
                        (excluding separator lines like |---|---|)
        
        Returns:
            pandas DataFrame with the table data, or None if parsing fails
        """
        import pandas as pd
        
        if not table_lines:
            return None
        
        rows = []
        headers = None
        
        for line in table_lines:
            # Split by | and clean up
            cells = [cell.strip() for cell in line.split('|')]
            # Remove empty first and last elements from split (caused by leading/trailing |)
            cells = [c for c in cells if c]
            
            if headers is None:
                headers = cells
            else:
                rows.append(cells)
        
        if headers and rows:
            # Ensure all rows have same number of columns as headers
            normalized_rows = []
            for row in rows:
                while len(row) < len(headers):
                    row.append('')
                normalized_rows.append(row[:len(headers)])
            
            return pd.DataFrame(normalized_rows, columns=headers)
        
        return None

    def _convert_content(self, content):
        if not self._param.output_format:
            return

        import pypandoc
        doc_id = get_uuid()

        if self._param.output_format.lower() not in {"markdown", "html", "pdf", "docx", "xlsx"}:
            self._param.output_format = "markdown"

        try:
            if self._param.output_format in {"markdown", "html"}:
                if isinstance(content, str):
                    converted = pypandoc.convert_text(
                        content,
                        to=self._param.output_format,
                        format="markdown",
                    )
                else:
                    converted = pypandoc.convert_file(
                        content,
                        to=self._param.output_format,
                        format="markdown",
                    )

                binary_content = converted.encode("utf-8")

            elif self._param.output_format == "xlsx":
                import pandas as pd
                from io import BytesIO

                # Debug: log the content being parsed
                _lineaje_payload = f"XLSX Parser: Content length={len(content) if content else 0}, first 500 chars: {content[:500] if content else 'None'}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Message._convert_content).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:27993ef035340170656e943fefaaf65425b322502ff9354a194c36f9aa05aa31'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:27993ef035340170656e943fefaaf65425b322502ff9354a194c36f9aa05aa31', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/message.py', 'line': 279, 'function': 'Message._convert_content'}, 'file': 'agent/component/message.py', 'line': 279, 'function': '_convert_content', 'agent_name': 'Message', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                
                # Try to parse ALL Markdown tables from the content
                # Each table will be written to a separate sheet
                tables = []  # List of (sheet_name, dataframe)
                
                if isinstance(content, str):
                    lines = content.strip().split('\n')
                    _lineaje_payload = f"XLSX Parser: Total lines={len(lines)}, lines starting with '|': {sum(1 for line in lines if line.strip().startswith('|'))}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Message._convert_content).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:55216fc02b705f0283cb0b777d9cec08497353743740a432465db61060f224a9'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:55216fc02b705f0283cb0b777d9cec08497353743740a432465db61060f224a9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/message.py', 'line': 287, 'function': 'Message._convert_content'}, 'file': 'agent/component/message.py', 'line': 287, 'function': '_convert_content', 'agent_name': 'Message', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)
                    current_table_lines = []
                    current_table_title = None
                    pending_title = None
                    in_table = False
                    table_count = 0
                    
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        
                        # Check for potential table title (lines before a table)
                        # Look for patterns like "Table 1:", "## Table", or markdown headers
                        if not in_table and stripped and not stripped.startswith('|'):
                            # Check if this could be a table title
                            lower_stripped = stripped.lower()
                            if (lower_stripped.startswith('table') or 
                                stripped.startswith('#') or
                                ':' in stripped):
                                pending_title = stripped.lstrip('#').strip()
                        
                        if stripped.startswith('|') and '|' in stripped[1:]:
                            # Check if this is a separator line (|---|---|)
                            cleaned = stripped.replace(' ', '').replace('|', '').replace('-', '').replace(':', '')
                            if cleaned == '':
                                continue  # Skip separator line
                            
                            if not in_table:
                                # Starting a new table
                                in_table = True
                                current_table_lines = []
                                current_table_title = pending_title
                                pending_title = None
                            
                            current_table_lines.append(stripped)
                        
                        elif in_table and not stripped.startswith('|'):
                            # End of current table - save it
                            if current_table_lines:
                                df = self._parse_markdown_table_lines(current_table_lines)
                                if df is not None and not df.empty:
                                    table_count += 1
                                    # Generate sheet name
                                    if current_table_title:
                                        # Clean and truncate title for sheet name
                                        sheet_name = current_table_title[:31]
                                        sheet_name = sheet_name.replace('/', '_').replace('\\', '_').replace('*', '').replace('?', '').replace('[', '').replace(']', '').replace(':', '')
                                    else:
                                        sheet_name = f"Table_{table_count}"
                                    tables.append((sheet_name, df))
                            
                            # Reset for next table
                            in_table = False
                            current_table_lines = []
                            current_table_title = None
                            
                            # Check if this line could be a title for the next table
                            if stripped:
                                lower_stripped = stripped.lower()
                                if (lower_stripped.startswith('table') or 
                                    stripped.startswith('#') or
                                    ':' in stripped):
                                    pending_title = stripped.lstrip('#').strip()
                    
                    # Don't forget the last table if content ends with a table
                    if in_table and current_table_lines:
                        df = self._parse_markdown_table_lines(current_table_lines)
                        if df is not None and not df.empty:
                            table_count += 1
                            if current_table_title:
                                sheet_name = current_table_title[:31]
                                sheet_name = sheet_name.replace('/', '_').replace('\\', '_').replace('*', '').replace('?', '').replace('[', '').replace(']', '').replace(':', '')
                            else:
                                sheet_name = f"Table_{table_count}"
                            tables.append((sheet_name, df))
                
                # Fallback: if no tables found, create single sheet with content
                if not tables:
                    df = pd.DataFrame({"Content": [content if content else ""]})
                    tables = [("Data", df)]

                # Write all tables to Excel, each in a separate sheet
                excel_io = BytesIO()
                with pd.ExcelWriter(excel_io, engine='openpyxl') as writer:
                    used_names = set()
                    for sheet_name, df in tables:
                        # Ensure unique sheet names
                        original_name = sheet_name
                        counter = 1
                        while sheet_name in used_names:
                            suffix = f"_{counter}"
                            sheet_name = original_name[:31-len(suffix)] + suffix
                            counter += 1
                        used_names.add(sheet_name)
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                excel_io.seek(0)
                binary_content = excel_io.read()
                
                _lineaje_payload = f"Generated Excel with {len(tables)} sheet(s): {[t[0] for t in tables]}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Message._convert_content).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:ff326893bf11c3dcbac964ac781dfcd7fd7023d9d307def11646bbd78130a91b'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ff326893bf11c3dcbac964ac781dfcd7fd7023d9d307def11646bbd78130a91b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/message.py', 'line': 385, 'function': 'Message._convert_content'}, 'file': 'agent/component/message.py', 'line': 385, 'function': '_convert_content', 'agent_name': 'Message', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)

            else:  # pdf, docx
                with tempfile.NamedTemporaryFile(suffix=f".{self._param.output_format}", delete=False) as tmp:
                    tmp_name = tmp.name

                try:
                    if isinstance(content, str):
                        pypandoc.convert_text(
                            content,
                            to=self._param.output_format,
                            format="markdown",
                            outputfile=tmp_name,
                        )
                    else:
                        pypandoc.convert_file(
                            content,
                            to=self._param.output_format,
                            format="markdown",
                            outputfile=tmp_name,
                        )

                    with open(tmp_name, "rb") as f:
                        binary_content = f.read()
                        # LINEAJE: runtime guardrail checks `binary_content` as it flows from file storage to the agent (in Message._convert_content).
                        #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `binary_content` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:504f7fb2971ab33d31c5d89b27f0b4d53843261972b3677e802aa6b4f7425a10'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:504f7fb2971ab33d31c5d89b27f0b4d53843261972b3677e802aa6b4f7425a10', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/message.py', 'line': 408, 'function': 'Message._convert_content'}, 'file': 'agent/component/message.py', 'line': 408, 'function': '_convert_content', 'agent_name': 'Message', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            binary_content = _gr_client.enforce(_gr_site, binary_content, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            raise

                finally:
                    if os.path.exists(tmp_name):
                        # LINEAJE: runtime guardrail checks `tmp_name` as it flows from the agent to system, at a security decision (in Message._convert_content).
                        #   Detected: this statement moves data from the agent to system with no runtime policy check (detection confidence: medium).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_029; sensitive values in `tmp_name` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:03ff14cde710d1db1924850b32bd119d1ca2dc79d805e51b3fcc2624d16deab0'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:03ff14cde710d1db1924850b32bd119d1ca2dc79d805e51b3fcc2624d16deab0', phase='security_decision', boundary={'source': 'agent_message', 'sink': 'agent_message'}, fail_mode='BLOCK', source_type='agent', destination_type='system', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/message.py', 'line': 412, 'function': 'Message._convert_content'}, 'file': 'agent/component/message.py', 'line': 412, 'function': '_convert_content', 'agent_name': 'Message', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            tmp_name = _gr_client.enforce(_gr_site, tmp_name, content_type='application/json', variable_name='tmp_name', source_file=__file__, before_line=412)
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        os.remove(tmp_name)

            settings.STORAGE_IMPL.put(self._canvas._tenant_id, doc_id, binary_content)
            self.set_output("attachment", {
                "doc_id":doc_id,
                "format":self._param.output_format,
                "file_name":f"{doc_id[:8]}.{self._param.output_format}"})

            _lineaje_payload = f"Converted content uploaded as {doc_id} (format={self._param.output_format})"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Message._convert_content).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3bf639c18343303b840d7c1a0e5f9134d7ef8ec315a9b2a369c0abbef6aa44c9'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3bf639c18343303b840d7c1a0e5f9134d7ef8ec315a9b2a369c0abbef6aa44c9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/message.py', 'line': 420, 'function': 'Message._convert_content'}, 'file': 'agent/component/message.py', 'line': 420, 'function': '_convert_content', 'agent_name': 'Message', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)

        except Exception as e:
            _lineaje_payload = f"Error converting content to {self._param.output_format}: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Message._convert_content).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:35d732d446e61b160293e5d62248a58a4f28e3101877473b0d9276fe13b7bb36'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:35d732d446e61b160293e5d62248a58a4f28e3101877473b0d9276fe13b7bb36', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/message.py', 'line': 423, 'function': 'Message._convert_content'}, 'file': 'agent/component/message.py', 'line': 423, 'function': '_convert_content', 'agent_name': 'Message', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
