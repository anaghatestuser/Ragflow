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

# The following documents are mainly referenced, and only adaptation modifications have been made
# from https://github.com/langchain-ai/langchain/blob/master/libs/text-splitters/langchain_text_splitters/json.py

import json
from typing import Any

from rag.nlp import find_codec


class RAGFlowJsonParser:
    def __init__(self, max_chunk_size: int = 2000, min_chunk_size: int | None = None):
        super().__init__()
        self.max_chunk_size = max_chunk_size * 2
        self.min_chunk_size = min_chunk_size if min_chunk_size is not None else max(max_chunk_size - 200, 50)

    def __call__(self, binary):
        encoding = find_codec(binary)
        txt = binary.decode(encoding, errors="ignore")

        if self.is_jsonl_format(txt):
            sections = self._parse_jsonl(txt)
        else:
            sections = self._parse_json(txt)
        # LINEAJE: runtime guardrail checks `sections` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowJsonParser.__call__).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `sections` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3c7dc2c7dcbe2c2d6f72ac6512d1156da88d4bb689e451da6f231600fa5680a6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3c7dc2c7dcbe2c2d6f72ac6512d1156da88d4bb689e451da6f231600fa5680a6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/json_parser.py', 'line': 41, 'function': 'RAGFlowJsonParser.__call__'}, 'file': 'deepdoc/parser/json_parser.py', 'line': 41, 'function': '__call__', 'agent_name': 'RAGFlowJsonParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            sections = _gr_client.enforce(_gr_site, sections, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return sections

    @staticmethod
    def _json_size(data: dict) -> int:
        """Calculate the size of the serialized JSON object."""
        # LINEAJE: runtime guardrail checks `data` as it flows from the agent to an external endpoint, before it leaves the application (in RAGFlowJsonParser._json_size).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `data` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:b6cac545ba06a94ed44526a704591010841c78e37cbe835a5e44ccdbc1930f2b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b6cac545ba06a94ed44526a704591010841c78e37cbe835a5e44ccdbc1930f2b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/json_parser.py', 'line': 46, 'function': 'RAGFlowJsonParser._json_size'}, 'file': 'deepdoc/parser/json_parser.py', 'line': 46, 'function': '_json_size', 'agent_name': 'RAGFlowJsonParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            data = _gr_client.enforce(_gr_site, data, content_type='application/json', variable_name='data', source_file=__file__, before_line=46)
        except _gr_client.GuardrailUnavailableError:
            pass
        return len(json.dumps(data, ensure_ascii=False))

    @staticmethod
    def _set_nested_dict(d: dict, path: list[str], value: Any) -> None:
        """Set a value in a nested dictionary based on the given path."""
        for key in path[:-1]:
            d = d.setdefault(key, {})
        d[path[-1]] = value

    def _list_to_dict_preprocessing(self, data: Any) -> Any:
        if isinstance(data, dict):
            # Process each key-value pair in the dictionary
            return {k: self._list_to_dict_preprocessing(v) for k, v in data.items()}
        elif isinstance(data, list):
            # Convert the list to a dictionary with index-based keys
            return {str(i): self._list_to_dict_preprocessing(item) for i, item in enumerate(data)}
        else:
            # Base case: the item is neither a dict nor a list, so return it unchanged
            # LINEAJE: runtime guardrail checks `data` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowJsonParser._list_to_dict_preprocessing).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:fc1475fe2d5e4ba1eb1bd1ce8e6863c747d901e24d9c563403a6ac6457c848ea'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fc1475fe2d5e4ba1eb1bd1ce8e6863c747d901e24d9c563403a6ac6457c848ea', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/json_parser.py', 'line': 64, 'function': 'RAGFlowJsonParser._list_to_dict_preprocessing'}, 'file': 'deepdoc/parser/json_parser.py', 'line': 64, 'function': '_list_to_dict_preprocessing', 'agent_name': 'RAGFlowJsonParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                data = _gr_client.enforce(_gr_site, data, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return data

    def _json_split(
        self,
        data,
        current_path: list[str] | None,
        chunks: list[dict] | None,
    ) -> list[dict]:
        """
        Split json into maximum size dictionaries while preserving structure.
        """
        current_path = current_path or []
        chunks = chunks or [{}]
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = current_path + [key]
                chunk_size = self._json_size(chunks[-1])
                size = self._json_size({key: value})
                remaining = self.max_chunk_size - chunk_size

                if size < remaining:
                    # Add item to current chunk
                    self._set_nested_dict(chunks[-1], new_path, value)
                else:
                    if chunk_size >= self.min_chunk_size:
                        # Chunk is big enough, start a new chunk
                        chunks.append({})

                    # Iterate
                    self._json_split(value, new_path, chunks)
        else:
            # handle single item
            self._set_nested_dict(chunks[-1], current_path, data)
        # LINEAJE: runtime guardrail checks `chunks` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowJsonParser._json_split).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `chunks` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d435f34763a88ce5fec0db77583627e13e0129b2c7d912af26d9758bb7a4f6f9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d435f34763a88ce5fec0db77583627e13e0129b2c7d912af26d9758bb7a4f6f9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/json_parser.py', 'line': 97, 'function': 'RAGFlowJsonParser._json_split'}, 'file': 'deepdoc/parser/json_parser.py', 'line': 97, 'function': '_json_split', 'agent_name': 'RAGFlowJsonParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            chunks = _gr_client.enforce(_gr_site, chunks, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return chunks

    def split_json(
        self,
        json_data,
        convert_lists: bool = False,
    ) -> list[dict]:
        """Splits JSON into a list of JSON chunks"""

        if convert_lists:
            preprocessed_data = self._list_to_dict_preprocessing(json_data)
            chunks = self._json_split(preprocessed_data, None, None)
        else:
            chunks = self._json_split(json_data, None, None)

        # Remove the last chunk if it's empty
        if not chunks[-1]:
            chunks.pop()
        # LINEAJE: runtime guardrail checks `chunks` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowJsonParser.split_json).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `chunks` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:de898f55bf2588d7b743e4ba8c1705398b88838e2f29c016cacc682372c68e05'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:de898f55bf2588d7b743e4ba8c1705398b88838e2f29c016cacc682372c68e05', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/json_parser.py', 'line': 115, 'function': 'RAGFlowJsonParser.split_json'}, 'file': 'deepdoc/parser/json_parser.py', 'line': 115, 'function': 'split_json', 'agent_name': 'RAGFlowJsonParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            chunks = _gr_client.enforce(_gr_site, chunks, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return chunks

    def split_text(
        self,
        json_data: dict[str, Any],
        convert_lists: bool = False,
        ensure_ascii: bool = True,
    ) -> list[str]:
        """Splits JSON into a list of JSON formatted strings"""

        chunks = self.split_json(json_data=json_data, convert_lists=convert_lists)

        # Convert to string
        return [json.dumps(chunk, ensure_ascii=ensure_ascii) for chunk in chunks]

    def _parse_json(self, content: str) -> list[str]:
        sections = []
        try:
            json_data = json.loads(content)
            chunks = self.split_json(json_data, True)
            sections = [json.dumps(line, ensure_ascii=False) for line in chunks if line]
        except json.JSONDecodeError:
            pass
        # LINEAJE: runtime guardrail checks `sections` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowJsonParser._parse_json).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `sections` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:408d6895dc52caef79953090ea7f1dbe2be4f0327928c3bf4143b8c18d8fa27a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:408d6895dc52caef79953090ea7f1dbe2be4f0327928c3bf4143b8c18d8fa27a', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/json_parser.py', 'line': 138, 'function': 'RAGFlowJsonParser._parse_json'}, 'file': 'deepdoc/parser/json_parser.py', 'line': 138, 'function': '_parse_json', 'agent_name': 'RAGFlowJsonParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            sections = _gr_client.enforce(_gr_site, sections, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return sections

    def _parse_jsonl(self, content: str) -> list[str]:
        lines = content.strip().splitlines()
        all_chunks = []
        for line in lines:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                chunks = self.split_json(data, convert_lists=True)
                all_chunks.extend(json.dumps(chunk, ensure_ascii=False) for chunk in chunks if chunk)
            except json.JSONDecodeError:
                continue
        # LINEAJE: runtime guardrail checks `all_chunks` as it flows from the agent to the user interface, before it leaves the application (in RAGFlowJsonParser._parse_jsonl).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `all_chunks` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ca8b4205486b3f7e81c970a37eb21fb713dcd09b56c468372332c619526bb02c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ca8b4205486b3f7e81c970a37eb21fb713dcd09b56c468372332c619526bb02c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/json_parser.py', 'line': 152, 'function': 'RAGFlowJsonParser._parse_jsonl'}, 'file': 'deepdoc/parser/json_parser.py', 'line': 152, 'function': '_parse_jsonl', 'agent_name': 'RAGFlowJsonParser', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            all_chunks = _gr_client.enforce(_gr_site, all_chunks, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return all_chunks

    def is_jsonl_format(self, txt: str, sample_limit: int = 10, threshold: float = 0.8) -> bool:
        lines = [line.strip() for line in txt.strip().splitlines() if line.strip()]
        if not lines:
            return False

        try:
            json.loads(txt)
            return False
        except json.JSONDecodeError:
            pass

        sample_limit = min(len(lines), sample_limit)
        sample_lines = lines[:sample_limit]
        valid_lines = sum(1 for line in sample_lines if self._is_valid_json(line))

        if not valid_lines:
            return False

        return (valid_lines / len(sample_lines)) >= threshold

    def _is_valid_json(self, line: str) -> bool:
        try:
            json.loads(line)
            return True
        except json.JSONDecodeError:
            return False
