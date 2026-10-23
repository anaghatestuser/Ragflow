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

"""
ExcelProcessor Component

A component for reading, processing, and generating Excel files in RAGFlow agents.
Supports multiple Excel file inputs, data transformation, and Excel output generation.
"""
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
import os
from abc import ABC
from io import BytesIO

import pandas as pd

from agent.component.base import ComponentBase, ComponentParamBase
from api.db.services.file_service import FileService
from api.utils.api_utils import timeout
from common import settings
from common.misc_utils import get_uuid


class ExcelProcessorParam(ComponentParamBase):
    """
    Define the ExcelProcessor component parameters.
    """
    def __init__(self):
        super().__init__()
        # Input configuration
        self.input_files = []  # Variable references to uploaded files
        self.operation = "read"  # read, merge, transform, output
        
        # Processing options
        self.sheet_selection = "all"  # all, first, or comma-separated sheet names
        self.merge_strategy = "concat"  # concat, join
        self.join_on = ""  # Column name for join operations
        
        # Transform options (for LLM-guided transformations)
        self.transform_instructions = ""
        self.transform_data = ""  # Variable reference to transformation data
        
        # Output options
        self.output_format = "xlsx"  # xlsx, csv
        self.output_filename = "output"
        
        # Component outputs
        self.outputs = {
            "data": {
                "type": "object",
                "value": {}
            },
            "summary": {
                "type": "str",
                "value": ""
            },
            "markdown": {
                "type": "str",
                "value": ""
            }
        }
    
    def check(self):
        self.check_valid_value(
            self.operation, 
            "[ExcelProcessor] Operation", 
            ["read", "merge", "transform", "output"]
        )
        self.check_valid_value(
            self.output_format,
            "[ExcelProcessor] Output format",
            ["xlsx", "csv"]
        )
        return True


class ExcelProcessor(ComponentBase, ABC):
    """
    Excel processing component for RAGFlow agents.
    
    Operations:
    - read: Parse Excel files into structured data
    - merge: Combine multiple Excel files
    - transform: Apply data transformations based on instructions
    - output: Generate Excel file output
    """
    component_name = "ExcelProcessor"

    def get_input_form(self) -> dict[str, dict]:
        """Define input form for the component."""
        res = {}
        for ref in (self._param.input_files or []):
            for k, o in self.get_input_elements_from_text(ref).items():
                res[k] = {"name": o.get("name", ""), "type": "file"}
        if self._param.transform_data:
            for k, o in self.get_input_elements_from_text(self._param.transform_data).items():
                res[k] = {"name": o.get("name", ""), "type": "object"}
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in ExcelProcessor.get_input_form).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f055b70768f9fa70c925c5aaebc97335ec72d93e9e057efd684a9b29b2d65839'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f055b70768f9fa70c925c5aaebc97335ec72d93e9e057efd684a9b29b2d65839', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/excel_processor.py', 'line': 112, 'function': 'ExcelProcessor.get_input_form'}, 'file': 'agent/component/excel_processor.py', 'line': 112, 'function': 'get_input_form', 'agent_name': 'ExcelProcessor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10*60)))
    def _invoke(self, **kwargs):
        if self.check_if_canceled("ExcelProcessor processing"):
            return

        operation = self._param.operation.lower()
        
        if operation == "read":
            self._read_excels()
        elif operation == "merge":
            self._merge_excels()
        elif operation == "transform":
            self._transform_data()
        elif operation == "output":
            self._output_excel()
        else:
            self.set_output("summary", f"Unknown operation: {operation}")

    def _get_file_content(self, file_ref: str) -> tuple[bytes, str]:
        """
        Get file content from a variable reference.
        Returns (content_bytes, filename).
        """
        value = self._canvas.get_variable_value(file_ref)
        if value is None:
            return None, None
            
        # Handle different value formats
        if isinstance(value, dict):
            # File reference from Begin/UserFillUp component
            file_id = value.get("id") or value.get("file_id")
            created_by = value.get("created_by") or self._canvas.get_tenant_id()
            filename = value.get("name") or value.get("filename", "unknown.xlsx")
            if file_id:
                content = FileService.get_blob(created_by, file_id)
                return content, filename
        elif isinstance(value, list) and len(value) > 0:
            # List of file references - return first
            return self._get_file_content_from_list(value[0])
        elif isinstance(value, str):
            # Could be base64 encoded or a path
            if value.startswith("data:"):
                import base64
                # Extract base64 content
                _, encoded = value.split(",", 1)
                return base64.b64decode(encoded), "uploaded.xlsx"
                
        return None, None
    
    def _get_file_content_from_list(self, item) -> tuple[bytes, str]:
        """Extract file content from a list item."""
        if isinstance(item, dict):
            return self._get_file_content(item)
        return None, None

    def _parse_excel_to_dataframes(self, content: bytes, filename: str) -> dict[str, pd.DataFrame]:
        """Parse Excel content into a dictionary of DataFrames (one per sheet)."""
        try:
            excel_file = BytesIO(content)
            
            if filename.lower().endswith(".csv"):
                df = pd.read_csv(excel_file)
                return {"Sheet1": df}
            else:
                # Read all sheets
                xlsx = pd.ExcelFile(excel_file, engine='openpyxl')
                sheet_selection = self._param.sheet_selection
                
                if sheet_selection == "all":
                    sheets_to_read = xlsx.sheet_names
                elif sheet_selection == "first":
                    sheets_to_read = [xlsx.sheet_names[0]] if xlsx.sheet_names else []
                else:
                    # Comma-separated sheet names
                    requested = [s.strip() for s in sheet_selection.split(",")]
                    sheets_to_read = [s for s in requested if s in xlsx.sheet_names]
                
                dfs = {}
                for sheet in sheets_to_read:
                    dfs[sheet] = pd.read_excel(xlsx, sheet_name=sheet)
                # LINEAJE: runtime guardrail checks `dfs` as it flows from the agent to the user interface, before it leaves the application (in ExcelProcessor._parse_excel_to_dataframes).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `dfs` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:65658d2cb54ea88adbc749d4e3568a85ba96600e2b13380e4811257b86189ba5'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:65658d2cb54ea88adbc749d4e3568a85ba96600e2b13380e4811257b86189ba5', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/excel_processor.py', 'line': 194, 'function': 'ExcelProcessor._parse_excel_to_dataframes'}, 'file': 'agent/component/excel_processor.py', 'line': 194, 'function': '_parse_excel_to_dataframes', 'agent_name': 'ExcelProcessor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    dfs = _gr_client.enforce(_gr_site, dfs, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return dfs
                
        except Exception as e:
            _lineaje_payload = f"Error parsing Excel file {filename}: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ExcelProcessor._parse_excel_to_dataframes).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:381bbfc9896447c93dcf9e2a47799988aac5628508efb5d9c7dc4b18de02e0c5'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:381bbfc9896447c93dcf9e2a47799988aac5628508efb5d9c7dc4b18de02e0c5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/excel_processor.py', 'line': 197, 'function': 'ExcelProcessor._parse_excel_to_dataframes'}, 'file': 'agent/component/excel_processor.py', 'line': 197, 'function': '_parse_excel_to_dataframes', 'agent_name': 'ExcelProcessor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            return {}

    def _read_excels(self):
        """Read and parse Excel files into structured data."""
        all_data = {}
        summaries = []
        markdown_parts = []
        
        for file_ref in (self._param.input_files or []):
            if self.check_if_canceled("ExcelProcessor reading"):
                return
                
            # Get variable value
            value = self._canvas.get_variable_value(file_ref)
            self.set_input_value(file_ref, str(value)[:200] if value else "")
            
            if value is None:
                continue
            
            # Handle file content
            content, filename = self._get_file_content(file_ref)
            if content is None:
                continue
                
            # Parse Excel
            dfs = self._parse_excel_to_dataframes(content, filename)
            
            for sheet_name, df in dfs.items():
                key = f"{filename}_{sheet_name}" if len(dfs) > 1 else filename
                all_data[key] = df.to_dict(orient="records")
                
                # Build summary
                summaries.append(f"**{key}**: {len(df)} rows, {len(df.columns)} columns ({', '.join(df.columns.tolist()[:5])}{'...' if len(df.columns) > 5 else ''})")
                
                # Build markdown table
                markdown_parts.append(f"### {key}\n\n{df.head(10).to_markdown(index=False)}\n")
        
        # Set outputs
        self.set_output("data", all_data)
        self.set_output("summary", "\n".join(summaries) if summaries else "No Excel files found")
        self.set_output("markdown", "\n\n".join(markdown_parts) if markdown_parts else "No data")

    def _merge_excels(self):
        """Merge multiple Excel files/sheets into one."""
        all_dfs = []
        
        for file_ref in (self._param.input_files or []):
            if self.check_if_canceled("ExcelProcessor merging"):
                return
                
            value = self._canvas.get_variable_value(file_ref)
            self.set_input_value(file_ref, str(value)[:200] if value else "")
            
            if value is None:
                continue
                
            content, filename = self._get_file_content(file_ref)
            if content is None:
                continue
                
            dfs = self._parse_excel_to_dataframes(content, filename)
            all_dfs.extend(dfs.values())
        
        if not all_dfs:
            self.set_output("data", {})
            self.set_output("summary", "No data to merge")
            return
        
        # Merge strategy
        if self._param.merge_strategy == "concat":
            merged_df = pd.concat(all_dfs, ignore_index=True)
        elif self._param.merge_strategy == "join" and self._param.join_on:
            # Join on specified column
            merged_df = all_dfs[0]
            for df in all_dfs[1:]:
                merged_df = merged_df.merge(df, on=self._param.join_on, how="outer")
        else:
            merged_df = pd.concat(all_dfs, ignore_index=True)
        
        self.set_output("data", {"merged": merged_df.to_dict(orient="records")})
        self.set_output("summary", f"Merged {len(all_dfs)} sources into {len(merged_df)} rows, {len(merged_df.columns)} columns")
        self.set_output("markdown", merged_df.head(20).to_markdown(index=False))

    def _transform_data(self):
        """Apply transformations to data based on instructions or input data."""
        # Get the data to transform
        transform_ref = self._param.transform_data
        if not transform_ref:
            self.set_output("summary", "No transform data reference provided")
            return
            
        data = self._canvas.get_variable_value(transform_ref)
        self.set_input_value(transform_ref, str(data)[:300] if data else "")
        
        if data is None:
            self.set_output("summary", "Transform data is empty")
            return
        
        # Convert to DataFrame
        if isinstance(data, dict):
            # Could be {"sheet": [rows]} format
            if all(isinstance(v, list) for v in data.values()):
                # Multiple sheets
                all_markdown = []
                for sheet_name, rows in data.items():
                    df = pd.DataFrame(rows)
                    all_markdown.append(f"### {sheet_name}\n\n{df.to_markdown(index=False)}")
                self.set_output("data", data)
                self.set_output("markdown", "\n\n".join(all_markdown))
            else:
                df = pd.DataFrame([data])
                self.set_output("data", df.to_dict(orient="records"))
                self.set_output("markdown", df.to_markdown(index=False))
        elif isinstance(data, list):
            df = pd.DataFrame(data)
            self.set_output("data", df.to_dict(orient="records"))
            self.set_output("markdown", df.to_markdown(index=False))
        else:
            self.set_output("data", {"raw": str(data)})
            self.set_output("markdown", str(data))
        
        self.set_output("summary", "Transformed data ready for processing")

    def _output_excel(self):
        """Generate Excel file output from data."""
        # Get data from transform_data reference
        transform_ref = self._param.transform_data
        if not transform_ref:
            self.set_output("summary", "No data reference for output")
            return
            
        data = self._canvas.get_variable_value(transform_ref)
        self.set_input_value(transform_ref, str(data)[:300] if data else "")
        
        if data is None:
            self.set_output("summary", "No data to output")
            return
        
        try:
            # Prepare DataFrames
            if isinstance(data, dict):
                if all(isinstance(v, list) for v in data.values()):
                    # Multi-sheet format
                    dfs = {k: pd.DataFrame(v) for k, v in data.items()}
                else:
                    dfs = {"Sheet1": pd.DataFrame([data])}
            elif isinstance(data, list):
                dfs = {"Sheet1": pd.DataFrame(data)}
            else:
                self.set_output("summary", "Invalid data format for Excel output")
                return
            
            # Generate output
            doc_id = get_uuid()
            
            if self._param.output_format == "csv":
                # For CSV, only output first sheet
                first_df = list(dfs.values())[0]
                binary_content = first_df.to_csv(index=False).encode("utf-8")
                filename = f"{self._param.output_filename}.csv"
            else:
                # Excel output
                excel_io = BytesIO()
                with pd.ExcelWriter(excel_io, engine='openpyxl') as writer:
                    for sheet_name, df in dfs.items():
                        # Sanitize sheet name (max 31 chars, no special chars)
                        safe_name = sheet_name[:31].replace("/", "_").replace("\\", "_")
                        df.to_excel(writer, sheet_name=safe_name, index=False)
                excel_io.seek(0)
                binary_content = excel_io.read()
                filename = f"{self._param.output_filename}.xlsx"
            
            # Store file
            settings.STORAGE_IMPL.put(self._canvas._tenant_id, doc_id, binary_content)
            
            # Set attachment output
            self.set_output("attachment", {
                "doc_id": doc_id,
                "format": self._param.output_format,
                "file_name": filename
            })
            
            total_rows = sum(len(df) for df in dfs.values())
            self.set_output("summary", f"Generated {filename} with {len(dfs)} sheet(s), {total_rows} total rows")
            self.set_output("data", {k: v.to_dict(orient="records") for k, v in dfs.items()})
            
            _lineaje_payload = f"ExcelProcessor: Generated {filename} as {doc_id}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ExcelProcessor._output_excel).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:833aa85433e70b038870af482a01b52209df6b014c63f9944633953e0bdbb28c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:833aa85433e70b038870af482a01b52209df6b014c63f9944633953e0bdbb28c', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/excel_processor.py', 'line': 384, 'function': 'ExcelProcessor._output_excel'}, 'file': 'agent/component/excel_processor.py', 'line': 384, 'function': '_output_excel', 'agent_name': 'ExcelProcessor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            
        except Exception as e:
            _lineaje_payload = f"ExcelProcessor output error: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ExcelProcessor._output_excel).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9b0be2204e14d8eb2c23e21a2fa409c4b640446b2be036da0af80b6ea7dd9b34'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9b0be2204e14d8eb2c23e21a2fa409c4b640446b2be036da0af80b6ea7dd9b34', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/excel_processor.py', 'line': 387, 'function': 'ExcelProcessor._output_excel'}, 'file': 'agent/component/excel_processor.py', 'line': 387, 'function': '_output_excel', 'agent_name': 'ExcelProcessor', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            self.set_output("summary", f"Error generating output: {str(e)}")

    def thoughts(self) -> str:
        """Return component thoughts for UI display."""
        op = self._param.operation
        if op == "read":
            return "Reading Excel files..."
        elif op == "merge":
            return "Merging Excel data..."
        elif op == "transform":
            return "Transforming data..."
        elif op == "output":
            return "Generating Excel output..."
        return "Processing Excel..."
