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
from typing import Any, Callable, Dict

import json_repair

from rag.prompts.generator import gen_meta_filter


def convert_conditions(metadata_condition):
    if metadata_condition is None:
        metadata_condition = {}
    op_mapping = {
        "is": "=",
        "not is": "≠"
    }
    return [
        {
            "op": op_mapping.get(cond["comparison_operator"], cond["comparison_operator"]),
            "key": cond["name"],
            "value": cond["value"]
        }
        for cond in metadata_condition.get("conditions", [])
    ]


def meta_filter(metas: dict, filters: list[dict], logic: str = "and"):
    doc_ids = set([])

    def filter_out(v2docs, operator, value):
        ids = []
        for input, docids in v2docs.items():

            if operator in ["=", "≠", ">", "<", "≥", "≤"]:
                try:
                    if isinstance(input, list):
                        input = input[0]
                    input = float(input)
                    value = float(value)
                except Exception:
                    pass
            if isinstance(input, str):
                input = input.lower()
            if isinstance(value, str):
                value = value.lower()

            for conds in [
                (operator == "contains", input in value if not isinstance(input, list) else all([i in value for i in input])),
                (operator == "not contains", input not in value if not isinstance(input, list) else all([i not in value for i in input])),
                (operator == "in", input in value if not isinstance(input, list) else all([i in value for i in input])),
                (operator == "not in", input not in value if not isinstance(input, list) else all([i not in value for i in input])),
                (operator == "start with", str(input).lower().startswith(str(value).lower())  if not isinstance(input, list) else "".join([str(i).lower() for i in input]).startswith(str(value).lower())),
                (operator == "end with", str(input).lower().endswith(str(value).lower())  if not isinstance(input, list) else "".join([str(i).lower() for i in input]).endswith(str(value).lower())),
                (operator == "empty", not input),
                (operator == "not empty", input),
                (operator == "=", input == value),
                (operator == "≠", input != value),
                (operator == ">", input > value),
                (operator == "<", input < value),
                (operator == "≥", input >= value),
                (operator == "≤", input <= value),
            ]:
                try:
                    if all(conds):
                        ids.extend(docids)
                        break
                except Exception:
                    pass
        # LINEAJE: runtime guardrail checks `ids` as it flows from the agent to the user interface, before it leaves the application (in filter_out).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3c1d436964b71f2f21d8e41352f810f060eec09bc31fceb0680af221f19b2868'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3c1d436964b71f2f21d8e41352f810f060eec09bc31fceb0680af221f19b2868', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/metadata_utils.py', 'line': 83, 'function': 'meta_filter.filter_out'}, 'file': 'common/metadata_utils.py', 'line': 83, 'function': 'filter_out', 'agent_name': 'filter_out', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            ids = _gr_client.enforce(_gr_site, ids, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return ids

    for k, v2docs in metas.items():
        for f in filters:
            if k != f["key"]:
                continue
            ids = filter_out(v2docs, f["op"], f["value"])
            if not doc_ids:
                doc_ids = set(ids)
            else:
                if logic == "and":
                    doc_ids = doc_ids & set(ids)
                else:
                    doc_ids = doc_ids | set(ids)
            if not doc_ids:
                return []
    return list(doc_ids)


async def apply_meta_data_filter(
    meta_data_filter: dict | None,
    metas: dict,
    question: str,
    chat_mdl: Any = None,
    base_doc_ids: list[str] | None = None,
    manual_value_resolver: Callable[[dict], dict] | None = None,
) -> list[str] | None:
    """
    Apply metadata filtering rules and return the filtered doc_ids.

    meta_data_filter supports three modes:
    - auto: generate filter conditions via LLM (gen_meta_filter)
    - semi_auto: generate conditions using selected metadata keys only
    - manual: directly filter based on provided conditions

    Returns:
        list of doc_ids, ["-999"] when manual filters yield no result, or None
        when auto/semi_auto filters return empty.
    """
    doc_ids = list(base_doc_ids) if base_doc_ids else []

    if not meta_data_filter:
        # LINEAJE: runtime guardrail checks `doc_ids` as it flows from the agent to the user interface, before it leaves the application (in apply_meta_data_filter).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `doc_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:dffcf56c89f3bb84008dcc3c502665176547534703688e19cc8c7c20ebf2e2e6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dffcf56c89f3bb84008dcc3c502665176547534703688e19cc8c7c20ebf2e2e6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/metadata_utils.py', 'line': 125, 'function': 'apply_meta_data_filter'}, 'file': 'common/metadata_utils.py', 'line': 125, 'function': 'apply_meta_data_filter', 'agent_name': 'apply_meta_data_filter', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            doc_ids = _gr_client.enforce(_gr_site, doc_ids, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return doc_ids

    method = meta_data_filter.get("method")

    if method == "auto":
        filters: dict = await gen_meta_filter(chat_mdl, metas, question)
        doc_ids.extend(meta_filter(metas, filters["conditions"], filters.get("logic", "and")))
        if not doc_ids:
            return None
    elif method == "semi_auto":
        selected_keys = meta_data_filter.get("semi_auto", [])
        if selected_keys:
            filtered_metas = {key: metas[key] for key in selected_keys if key in metas}
            if filtered_metas:
                filters: dict = await gen_meta_filter(chat_mdl, filtered_metas, question)
                doc_ids.extend(meta_filter(metas, filters["conditions"], filters.get("logic", "and")))
                if not doc_ids:
                    return None
    elif method == "manual":
        filters = meta_data_filter.get("manual", [])
        if manual_value_resolver:
            filters = [manual_value_resolver(flt) for flt in filters]
        doc_ids.extend(meta_filter(metas, filters, meta_data_filter.get("logic", "and")))
        if filters and not doc_ids:
            doc_ids = ["-999"]

    # LINEAJE: runtime guardrail checks `doc_ids` as it flows from the agent to the user interface, before it leaves the application (in apply_meta_data_filter).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `doc_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:00ba445a3e1ca362ad56418e393820bae4ff15e89cd1f74e32710a4321192e09'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:00ba445a3e1ca362ad56418e393820bae4ff15e89cd1f74e32710a4321192e09', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/metadata_utils.py', 'line': 151, 'function': 'apply_meta_data_filter'}, 'file': 'common/metadata_utils.py', 'line': 151, 'function': 'apply_meta_data_filter', 'agent_name': 'apply_meta_data_filter', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        doc_ids = _gr_client.enforce(_gr_site, doc_ids, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return doc_ids


def dedupe_list(values: list) -> list:
    seen = set()
    deduped = []
    for item in values:
        key = str(item)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    # LINEAJE: runtime guardrail checks `deduped` as it flows from the agent to the user interface, before it leaves the application (in dedupe_list).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `deduped` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:7ca72a99fcc12d60c236fdc036ecda162425b31a657f0ad14ed922ea79bb888f'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7ca72a99fcc12d60c236fdc036ecda162425b31a657f0ad14ed922ea79bb888f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/metadata_utils.py', 'line': 163, 'function': 'dedupe_list'}, 'file': 'common/metadata_utils.py', 'line': 163, 'function': 'dedupe_list', 'agent_name': 'dedupe_list', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        deduped = _gr_client.enforce(_gr_site, deduped, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return deduped


def update_metadata_to(metadata, meta):
    if not meta:
        # LINEAJE: runtime guardrail checks `metadata` as it flows from the agent to the user interface, before it leaves the application (in update_metadata_to).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `metadata` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c57e1434366052aa845c6080152136178a5f5d02455cb2b3e91e75f270af39d8'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c57e1434366052aa845c6080152136178a5f5d02455cb2b3e91e75f270af39d8', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/metadata_utils.py', 'line': 168, 'function': 'update_metadata_to'}, 'file': 'common/metadata_utils.py', 'line': 168, 'function': 'update_metadata_to', 'agent_name': 'update_metadata_to', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            metadata = _gr_client.enforce(_gr_site, metadata, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return metadata
    if isinstance(meta, str):
        try:
            meta = json_repair.loads(meta)
        except Exception:
            _lineaje_payload = "Meta data format error."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in update_metadata_to).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:33103d73af1417bed2da73ef63c180655c96401dcd5edc16816a23e318048b9a'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:33103d73af1417bed2da73ef63c180655c96401dcd5edc16816a23e318048b9a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/metadata_utils.py', 'line': 173, 'function': 'update_metadata_to'}, 'file': 'common/metadata_utils.py', 'line': 173, 'function': 'update_metadata_to', 'agent_name': 'update_metadata_to', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            # LINEAJE: runtime guardrail checks `metadata` as it flows from the agent to the user interface, before it leaves the application (in update_metadata_to).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `metadata` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:45ca857f4b086921860537ac07ddcc444e92abfb3cf0613adb5c75244a8daf66'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:45ca857f4b086921860537ac07ddcc444e92abfb3cf0613adb5c75244a8daf66', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/metadata_utils.py', 'line': 174, 'function': 'update_metadata_to'}, 'file': 'common/metadata_utils.py', 'line': 174, 'function': 'update_metadata_to', 'agent_name': 'update_metadata_to', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                metadata = _gr_client.enforce(_gr_site, metadata, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return metadata
    if not isinstance(meta, dict):
        # LINEAJE: runtime guardrail checks `metadata` as it flows from the agent to the user interface, before it leaves the application (in update_metadata_to).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `metadata` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:3b40845278464d2c3e1e91a9e28ca810789bc8370788af7505f84e2a5065d285'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3b40845278464d2c3e1e91a9e28ca810789bc8370788af7505f84e2a5065d285', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/metadata_utils.py', 'line': 176, 'function': 'update_metadata_to'}, 'file': 'common/metadata_utils.py', 'line': 176, 'function': 'update_metadata_to', 'agent_name': 'update_metadata_to', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            metadata = _gr_client.enforce(_gr_site, metadata, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return metadata

    for k, v in meta.items():
        if isinstance(v, list):
            v = [vv for vv in v if isinstance(vv, str)]
            if not v:
                continue
            v = dedupe_list(v)
        if not isinstance(v, list) and not isinstance(v, str):
            continue
        if k not in metadata:
            metadata[k] = v
            continue
        if isinstance(metadata[k], list):
            if isinstance(v, list):
                metadata[k].extend(v)
            else:
                metadata[k].append(v)
            metadata[k] = dedupe_list(metadata[k])
        else:
            metadata[k] = v

    # LINEAJE: runtime guardrail checks `metadata` as it flows from the agent to the user interface, before it leaves the application (in update_metadata_to).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `metadata` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:f92b4a6cd0034dfdaf386f3d189401531037129324dbfc9f594f224412753897'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f92b4a6cd0034dfdaf386f3d189401531037129324dbfc9f594f224412753897', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/metadata_utils.py', 'line': 198, 'function': 'update_metadata_to'}, 'file': 'common/metadata_utils.py', 'line': 198, 'function': 'update_metadata_to', 'agent_name': 'update_metadata_to', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        metadata = _gr_client.enforce(_gr_site, metadata, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return metadata


def metadata_schema(metadata: list|None) -> Dict[str, Any]:
    if not metadata:
        return {}
    properties = {}

    for item in metadata:
        key = item.get("key")
        if not key:
            continue

        prop_schema = {
            "description": item.get("description", "")
        }
        if "enum" in item and item["enum"]:
            prop_schema["enum"] = item["enum"]
            prop_schema["type"] = "string"

        properties[key] = prop_schema

    json_schema = {
        "type": "object",
        "properties": properties,
    }

    json_schema["additionalProperties"] = False
    # LINEAJE: runtime guardrail checks `json_schema` as it flows from the agent to the user interface, before it leaves the application (in metadata_schema).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `json_schema` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:88fd8e71637027a4658bb1e41fd1476fc96d88d1da05db65551a3d53f3d21eb6'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:88fd8e71637027a4658bb1e41fd1476fc96d88d1da05db65551a3d53f3d21eb6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/metadata_utils.py', 'line': 226, 'function': 'metadata_schema'}, 'file': 'common/metadata_utils.py', 'line': 226, 'function': 'metadata_schema', 'agent_name': 'metadata_schema', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        json_schema = _gr_client.enforce(_gr_site, json_schema, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return json_schema
