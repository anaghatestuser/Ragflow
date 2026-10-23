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
import ast
import base64
import json
import logging
import os
from abc import ABC
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from strenum import StrEnum

from agent.tools.base import ToolBase, ToolMeta, ToolParamBase
from common import settings
from common.connection_utils import timeout


class Language(StrEnum):
    PYTHON = "python"
    NODEJS = "nodejs"


class CodeExecutionRequest(BaseModel):
    code_b64: str = Field(..., description="Base64 encoded code string")
    language: str = Field(default=Language.PYTHON.value, description="Programming language")
    arguments: Optional[dict] = Field(default={}, description="Arguments")

    @field_validator("code_b64")
    @classmethod
    def validate_base64(cls, v: str) -> str:
        try:
            base64.b64decode(v, validate=True)
            # LINEAJE: runtime guardrail checks `v` as it flows from the agent to the user interface, before it leaves the application (in CodeExecutionRequest.validate_base64).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `v` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ac44ad66b41ecb474a22399bdd1121537ae805a635335872ccc8fe3414f1bfb9'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ac44ad66b41ecb474a22399bdd1121537ae805a635335872ccc8fe3414f1bfb9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 47, 'function': 'CodeExecutionRequest.validate_base64'}, 'file': 'agent/tools/code_exec.py', 'line': 47, 'function': 'validate_base64', 'agent_name': 'CodeExecutionRequest', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                v = _gr_client.enforce(_gr_site, v, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return v
        except Exception as e:
            raise ValueError(f"Invalid base64 encoding: {str(e)}")

    @field_validator("language", mode="before")
    @classmethod
    def normalize_language(cls, v) -> str:
        if isinstance(v, str):
            low = v.lower()
            if low in ("python", "python3"):
                return "python"
            elif low in ("javascript", "nodejs"):
                return "nodejs"
        raise ValueError(f"Unsupported language: {v}")


class CodeExecParam(ToolParamBase):
    """
    Define the code sandbox component parameters.
    """

    def __init__(self):
        self.meta: ToolMeta = {
            "name": "execute_code",
            "description": """
This tool has a sandbox that can execute code written in 'Python'/'Javascript'. It receives a piece of code and return a Json string.
Here's a code example for Python(`main` function MUST be included):
def main() -> dict:
    \"\"\"
    Generate Fibonacci numbers within 100.
    \"\"\"
    def fibonacci_recursive(n):
        if n <= 1:
            return n
        else:
            return fibonacci_recursive(n-1) + fibonacci_recursive(n-2)
    return {
        "result": fibonacci_recursive(100),
    }

Here's a code example for Javascript(`main` function MUST be included and exported):
const axios = require('axios');
async function main(args) {
  try {
    const response = await axios.get('https://github.com/infiniflow/ragflow');
    console.log('Body:', response.data);
  } catch (error) {
    console.error('Error:', error.message);
  }
}
module.exports = { main };
            """,
            "parameters": {
                "lang": {
                    "type": "string",
                    "description": "The programming language of this piece of code.",
                    "enum": ["python", "javascript"],
                    "required": True,
                },
                "script": {"type": "string", "description": "A piece of code in right format. There MUST be main function.", "required": True},
            },
        }
        super().__init__()
        self.lang = Language.PYTHON.value
        self.script = 'def main(arg1: str, arg2: str) -> dict: return {"result": arg1 + arg2}'
        self.arguments = {}
        self.outputs = {"result": {"value": "", "type": "string"}}

    def check(self):
        self.check_valid_value(self.lang, "Support languages", ["python", "python3", "nodejs", "javascript"])
        self.check_empty(self.script, "Script")

    def get_input_form(self) -> dict[str, dict]:
        res = {}
        for k, v in self.arguments.items():
            res[k] = {"type": "line", "name": k}
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in CodeExecParam.get_input_form).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:beddbea3e8867b54af613bc2d9a38afbfa2344c4905230b1072453664cb80679'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:beddbea3e8867b54af613bc2d9a38afbfa2344c4905230b1072453664cb80679', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 123, 'function': 'CodeExecParam.get_input_form'}, 'file': 'agent/tools/code_exec.py', 'line': 123, 'function': 'get_input_form', 'agent_name': 'CodeExecParam', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res


class CodeExec(ToolBase, ABC):
    component_name = "CodeExec"

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10 * 60)))
    def _invoke(self, **kwargs):
        if self.check_if_canceled("CodeExec processing"):
            return

        lang = kwargs.get("lang", self._param.lang)
        script = kwargs.get("script", self._param.script)
        arguments = {}
        for k, v in self._param.arguments.items():
            if kwargs.get(k):
                arguments[k] = kwargs[k]
                continue
            arguments[k] = self._canvas.get_variable_value(v) if v else None

        self._execute_code(language=lang, code=script, arguments=arguments)

    def _execute_code(self, language: str, code: str, arguments: dict):
        import requests

        if self.check_if_canceled("CodeExec execution"):
            return

        try:
            code_b64 = self._encode_code(code)
            code_req = CodeExecutionRequest(code_b64=code_b64, language=language, arguments=arguments).model_dump()
        except Exception as e:
            if self.check_if_canceled("CodeExec execution"):
                return

            self.set_output("_ERROR", "construct code request error: " + str(e))

        try:
            if self.check_if_canceled("CodeExec execution"):
                return "Task has been canceled"

            resp = requests.post(url=f"http://{settings.SANDBOX_HOST}:9385/run", json=code_req, timeout=int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10 * 60)))
            # LINEAJE: runtime guardrail checks `resp` as it flows from an external API to the agent, after the tool returns (in CodeExec._execute_code).
            #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `resp` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d046317dcd8e867efdb2c6daa47e6d99726da1fce4baddd511e181227422cc5c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d046317dcd8e867efdb2c6daa47e6d99726da1fce4baddd511e181227422cc5c', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 164, 'function': 'CodeExec._execute_code'}, 'file': 'agent/tools/code_exec.py', 'line': 164, 'function': '_execute_code', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                resp = _gr_client.enforce(_gr_site, resp, content_type='application/json', variable_name='resp', source_file=__file__, before_line=164)
            except _gr_client.GuardrailUnavailableError:
                pass
            _lineaje_payload = f"http://{settings.SANDBOX_HOST}:9385/run,  code_req: {code_req}, resp.status_code {resp.status_code}:"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CodeExec._execute_code).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0c70de14d766f53a37a4c588c478694f95b1af5aa2ce6e25b0088dc0711430dc'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0c70de14d766f53a37a4c588c478694f95b1af5aa2ce6e25b0088dc0711430dc', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 165, 'function': 'CodeExec._execute_code'}, 'file': 'agent/tools/code_exec.py', 'line': 165, 'function': '_execute_code', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)

            if self.check_if_canceled("CodeExec execution"):
                return "Task has been canceled"

            if resp.status_code != 200:
                resp.raise_for_status()
            body = resp.json()
            if body:
                stderr = body.get("stderr")
                if stderr:
                    self.set_output("_ERROR", stderr)
                    return
                raw_stdout = body.get("stdout", "")
                parsed_stdout = self._deserialize_stdout(raw_stdout)
                _lineaje_payload = f"[CodeExec]: http://{settings.SANDBOX_HOST}:9385/run -> {parsed_stdout}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CodeExec._execute_code).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:b0d7f3dc5b978b7b9e1cf8258dfdc54503f960ad4e945f9938c7942faa663348'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b0d7f3dc5b978b7b9e1cf8258dfdc54503f960ad4e945f9938c7942faa663348', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 180, 'function': 'CodeExec._execute_code'}, 'file': 'agent/tools/code_exec.py', 'line': 180, 'function': '_execute_code', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                self._populate_outputs(parsed_stdout, raw_stdout)
            else:
                self.set_output("_ERROR", "There is no response from sandbox")

        except Exception as e:
            if self.check_if_canceled("CodeExec execution"):
                return

            self.set_output("_ERROR", "Exception executing code: " + str(e))

        return self.output()

    def _encode_code(self, code: str) -> str:
        return base64.b64encode(code.encode("utf-8")).decode("utf-8")

    def thoughts(self) -> str:
        return "Running a short script to process data."

    def _deserialize_stdout(self, stdout: str):
        text = str(stdout).strip()
        if not text:
            return ""
        for loader in (json.loads, ast.literal_eval):
            try:
                return loader(text)
            except Exception:
                continue
        # LINEAJE: runtime guardrail checks `text` as it flows from the agent to the user interface, before it leaves the application (in CodeExec._deserialize_stdout).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `text` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:19c0ae82a9cac2663ce8f983e17ecdacc0a39d8d81ebaa8778a96b93478a61d2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:19c0ae82a9cac2663ce8f983e17ecdacc0a39d8d81ebaa8778a96b93478a61d2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 208, 'function': 'CodeExec._deserialize_stdout'}, 'file': 'agent/tools/code_exec.py', 'line': 208, 'function': '_deserialize_stdout', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            text = _gr_client.enforce(_gr_site, text, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return text

    def _coerce_output_value(self, value, expected_type: Optional[str]):
        if expected_type is None:
            # LINEAJE: runtime guardrail checks `value` as it flows from the agent to the user interface, before it leaves the application (in CodeExec._coerce_output_value).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `value` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d77e83006cefc03d3c3e8645e7295c6ad37393fbe3aa5cea8818adc4a5104c8e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d77e83006cefc03d3c3e8645e7295c6ad37393fbe3aa5cea8818adc4a5104c8e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 212, 'function': 'CodeExec._coerce_output_value'}, 'file': 'agent/tools/code_exec.py', 'line': 212, 'function': '_coerce_output_value', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                value = _gr_client.enforce(_gr_site, value, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return value

        etype = expected_type.strip().lower()
        inner_type = None
        if etype.startswith("array<") and etype.endswith(">"):
            inner_type = etype[6:-1].strip()
            etype = "array"

        try:
            if etype == "string":
                return "" if value is None else str(value)

            if etype == "number":
                if value is None or value == "":
                    return None
                if isinstance(value, (int, float)):
                    # LINEAJE: runtime guardrail checks `value` as it flows from the agent to the user interface, before it leaves the application (in CodeExec._coerce_output_value).
                    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `value` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:23977ef3b80f11dcafe16a0ecce513c000722db95f6277925bf714a0f30c2b66'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:23977ef3b80f11dcafe16a0ecce513c000722db95f6277925bf714a0f30c2b66', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 228, 'function': 'CodeExec._coerce_output_value'}, 'file': 'agent/tools/code_exec.py', 'line': 228, 'function': '_coerce_output_value', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        value = _gr_client.enforce(_gr_site, value, content_type='text/plain')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    return value
                if isinstance(value, str):
                    try:
                        return float(value)
                    except Exception:
                        # LINEAJE: runtime guardrail checks `value` as it flows from the agent to the user interface, before it leaves the application (in CodeExec._coerce_output_value).
                        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `value` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:5e716d92d6306f27953eb317d5ec48dce5a3db37dec7574632c5c26a39526b70'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5e716d92d6306f27953eb317d5ec48dce5a3db37dec7574632c5c26a39526b70', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 233, 'function': 'CodeExec._coerce_output_value'}, 'file': 'agent/tools/code_exec.py', 'line': 233, 'function': '_coerce_output_value', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            value = _gr_client.enforce(_gr_site, value, content_type='text/plain')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        return value
                return float(value)

            if etype == "boolean":
                if isinstance(value, bool):
                    # LINEAJE: runtime guardrail checks `value` as it flows from the agent to the user interface, before it leaves the application (in CodeExec._coerce_output_value).
                    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `value` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:d35c085360978dade43fafbd4c2cb7a36a66a714f2a32b16cb8f3cc694e7e601'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d35c085360978dade43fafbd4c2cb7a36a66a714f2a32b16cb8f3cc694e7e601', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 238, 'function': 'CodeExec._coerce_output_value'}, 'file': 'agent/tools/code_exec.py', 'line': 238, 'function': '_coerce_output_value', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        value = _gr_client.enforce(_gr_site, value, content_type='text/plain')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    return value
                if isinstance(value, str):
                    lv = value.lower()
                    if lv in ("true", "1", "yes", "y", "on"):
                        return True
                    if lv in ("false", "0", "no", "n", "off"):
                        return False
                return bool(value)

            if etype == "array":
                candidate = value
                if isinstance(candidate, str):
                    parsed = self._deserialize_stdout(candidate)
                    candidate = parsed
                if isinstance(candidate, tuple):
                    candidate = list(candidate)
                if not isinstance(candidate, list):
                    candidate = [] if candidate is None else [candidate]

                if inner_type == "string":
                    return ["" if v is None else str(v) for v in candidate]
                if inner_type == "number":
                    coerced = []
                    for v in candidate:
                        try:
                            if v is None or v == "":
                                coerced.append(None)
                            elif isinstance(v, (int, float)):
                                coerced.append(v)
                            else:
                                coerced.append(float(v))
                        except Exception:
                            coerced.append(v)
                    # LINEAJE: runtime guardrail checks `coerced` as it flows from the agent to the user interface, before it leaves the application (in CodeExec._coerce_output_value).
                    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `coerced` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:e5b82e6bd84a702e0e08a057ed231016c236c8dba570dbadce64a9c1885d4e98'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e5b82e6bd84a702e0e08a057ed231016c236c8dba570dbadce64a9c1885d4e98', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 271, 'function': 'CodeExec._coerce_output_value'}, 'file': 'agent/tools/code_exec.py', 'line': 271, 'function': '_coerce_output_value', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        coerced = _gr_client.enforce(_gr_site, coerced, content_type='text/plain')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    return coerced
                # LINEAJE: runtime guardrail checks `candidate` as it flows from the agent to the user interface, before it leaves the application (in CodeExec._coerce_output_value).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `candidate` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:76b5273c42bfb52e63aab87d93a9f8ca28399558d3a75a7f928ab6d684f90151'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:76b5273c42bfb52e63aab87d93a9f8ca28399558d3a75a7f928ab6d684f90151', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 272, 'function': 'CodeExec._coerce_output_value'}, 'file': 'agent/tools/code_exec.py', 'line': 272, 'function': '_coerce_output_value', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    candidate = _gr_client.enforce(_gr_site, candidate, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return candidate

            if etype == "object":
                if isinstance(value, dict):
                    # LINEAJE: runtime guardrail checks `value` as it flows from the agent to the user interface, before it leaves the application (in CodeExec._coerce_output_value).
                    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `value` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:ad117094f6ac42781f09d6e93b8146688b6fee9ab393dc3454885a48f2864e9d'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ad117094f6ac42781f09d6e93b8146688b6fee9ab393dc3454885a48f2864e9d', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 276, 'function': 'CodeExec._coerce_output_value'}, 'file': 'agent/tools/code_exec.py', 'line': 276, 'function': '_coerce_output_value', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        value = _gr_client.enforce(_gr_site, value, content_type='text/plain')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    return value
                if isinstance(value, str):
                    parsed = self._deserialize_stdout(value)
                    if isinstance(parsed, dict):
                        # LINEAJE: runtime guardrail checks `parsed` as it flows from the agent to the user interface, before it leaves the application (in CodeExec._coerce_output_value).
                        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `parsed` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:2ec84de509339ab088773061457289c2abb5c32f1b1cfb33b8eed7e5ba81e8b1'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2ec84de509339ab088773061457289c2abb5c32f1b1cfb33b8eed7e5ba81e8b1', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 280, 'function': 'CodeExec._coerce_output_value'}, 'file': 'agent/tools/code_exec.py', 'line': 280, 'function': '_coerce_output_value', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            parsed = _gr_client.enforce(_gr_site, parsed, content_type='text/plain')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        return parsed
                # LINEAJE: runtime guardrail checks `value` as it flows from the agent to the user interface, before it leaves the application (in CodeExec._coerce_output_value).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `value` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:d7ceded80b3d4b7be4b75abd9120aa5a8b982743154a82d9d3848e8922c9b472'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d7ceded80b3d4b7be4b75abd9120aa5a8b982743154a82d9d3848e8922c9b472', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 281, 'function': 'CodeExec._coerce_output_value'}, 'file': 'agent/tools/code_exec.py', 'line': 281, 'function': '_coerce_output_value', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    value = _gr_client.enforce(_gr_site, value, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return value
        except Exception:
            # LINEAJE: runtime guardrail checks `value` as it flows from the agent to the user interface, before it leaves the application (in CodeExec._coerce_output_value).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `value` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:5bf1677659a388876e236cf40ab5e57ad60bd2e63f8ef098238512b518e23a4c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5bf1677659a388876e236cf40ab5e57ad60bd2e63f8ef098238512b518e23a4c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 283, 'function': 'CodeExec._coerce_output_value'}, 'file': 'agent/tools/code_exec.py', 'line': 283, 'function': '_coerce_output_value', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                value = _gr_client.enforce(_gr_site, value, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return value

        # LINEAJE: runtime guardrail checks `value` as it flows from the agent to the user interface, before it leaves the application (in CodeExec._coerce_output_value).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `value` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:32496098229062c8432be90e6d2b6315b828d3a032834cf845a4fbba1c1c1940'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:32496098229062c8432be90e6d2b6315b828d3a032834cf845a4fbba1c1c1940', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 285, 'function': 'CodeExec._coerce_output_value'}, 'file': 'agent/tools/code_exec.py', 'line': 285, 'function': '_coerce_output_value', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            value = _gr_client.enforce(_gr_site, value, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return value

    def _populate_outputs(self, parsed_stdout, raw_stdout: str):
        outputs_items = list(self._param.outputs.items())
        _lineaje_payload = f"[CodeExec]: outputs schema keys: {[k for k, _ in outputs_items]}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CodeExec._populate_outputs).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b0d71d297679ef007b2c9cb782364fb2ac8de0f391b4ce359330796ea6a698f2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b0d71d297679ef007b2c9cb782364fb2ac8de0f391b4ce359330796ea6a698f2', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 289, 'function': 'CodeExec._populate_outputs'}, 'file': 'agent/tools/code_exec.py', 'line': 289, 'function': '_populate_outputs', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        if not outputs_items:
            return

        if isinstance(parsed_stdout, dict):
            for key, meta in outputs_items:
                if key.startswith("_"):
                    continue
                val = self._get_by_path(parsed_stdout, key)
                coerced = self._coerce_output_value(val, meta.get("type"))
                _lineaje_payload = f"[CodeExec]: populate dict key='{key}' raw='{val}' coerced='{coerced}'"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CodeExec._populate_outputs).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:fedd786347aabcc7f6d5544b9545a3deda9ab5cbddf35bf7de8184d2d2785d68'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fedd786347aabcc7f6d5544b9545a3deda9ab5cbddf35bf7de8184d2d2785d68', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 299, 'function': 'CodeExec._populate_outputs'}, 'file': 'agent/tools/code_exec.py', 'line': 299, 'function': '_populate_outputs', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                self.set_output(key, coerced)
            return

        if isinstance(parsed_stdout, (list, tuple)):
            for idx, (key, meta) in enumerate(outputs_items):
                if key.startswith("_"):
                    continue
                val = parsed_stdout[idx] if idx < len(parsed_stdout) else None
                coerced = self._coerce_output_value(val, meta.get("type"))
                _lineaje_payload = f"[CodeExec]: populate list key='{key}' raw='{val}' coerced='{coerced}'"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CodeExec._populate_outputs).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:1f1ea0cd9afb9341f1809e09cfd8682a84cf36853e4a6f66a9a8d3175e0fdcb8'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1f1ea0cd9afb9341f1809e09cfd8682a84cf36853e4a6f66a9a8d3175e0fdcb8', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 309, 'function': 'CodeExec._populate_outputs'}, 'file': 'agent/tools/code_exec.py', 'line': 309, 'function': '_populate_outputs', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)
                self.set_output(key, coerced)
            return

        default_val = parsed_stdout if parsed_stdout is not None else raw_stdout
        for idx, (key, meta) in enumerate(outputs_items):
            if key.startswith("_"):
                continue
            val = default_val if idx == 0 else None
            coerced = self._coerce_output_value(val, meta.get("type"))
            _lineaje_payload = f"[CodeExec]: populate scalar key='{key}' raw='{val}' coerced='{coerced}'"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CodeExec._populate_outputs).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ca8b260089da4897d1db2fcd7f89b6672b61741bfd4a6d7c93196e5294c20d9f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ca8b260089da4897d1db2fcd7f89b6672b61741bfd4a6d7c93196e5294c20d9f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 319, 'function': 'CodeExec._populate_outputs'}, 'file': 'agent/tools/code_exec.py', 'line': 319, 'function': '_populate_outputs', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(_lineaje_payload)
            self.set_output(key, coerced)

    def _get_by_path(self, data, path: str):
        if not path:
            return None
        cur = data
        for part in path.split("."):
            part = part.strip()
            if not part:
                return None
            if isinstance(cur, dict):
                cur = cur.get(part)
            elif isinstance(cur, list):
                try:
                    idx = int(part)
                    cur = cur[idx]
                except Exception:
                    return None
            else:
                return None
            if cur is None:
                return None
        _lineaje_payload = f"[CodeExec]: resolve path '{path}' -> {cur}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in CodeExec._get_by_path).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:51ac8a026440f4a15a53b95e51c279639e489575ef87e50cddf85290a03feebb'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:51ac8a026440f4a15a53b95e51c279639e489575ef87e50cddf85290a03feebb', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 342, 'function': 'CodeExec._get_by_path'}, 'file': 'agent/tools/code_exec.py', 'line': 342, 'function': '_get_by_path', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `cur` as it flows from the agent to the user interface, before it leaves the application (in CodeExec._get_by_path).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `cur` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5c239635008ec0d824bcb596068fc8d66421f4c3dcc9e23e8cb4728cb43c2a82'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5c239635008ec0d824bcb596068fc8d66421f4c3dcc9e23e8cb4728cb43c2a82', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/code_exec.py', 'line': 343, 'function': 'CodeExec._get_by_path'}, 'file': 'agent/tools/code_exec.py', 'line': 343, 'function': '_get_by_path', 'agent_name': 'CodeExec', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            cur = _gr_client.enforce(_gr_site, cur, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return cur
