# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License
"""
Reference:
 - [graphrag](https://github.com/microsoft/graphrag)
 - [LightRag](https://github.com/HKUDS/LightRAG)
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


import asyncio
import dataclasses
import html
import json
import logging
import os
import re
import time
from collections import defaultdict
from hashlib import md5
from typing import Any, Callable, Set, Tuple

import networkx as nx
import numpy as np
import xxhash
from networkx.readwrite import json_graph

from common.misc_utils import get_uuid
from common.connection_utils import timeout
from rag.nlp import rag_tokenizer, search
from rag.utils.redis_conn import REDIS_CONN
from common import settings
from common.doc_store.doc_store_base import OrderByExpr

GRAPH_FIELD_SEP = "<SEP>"

ErrorHandlerFn = Callable[[BaseException | None, str | None, dict | None], None]

chat_limiter = asyncio.Semaphore(int(os.environ.get("MAX_CONCURRENT_CHATS", 10)))


@dataclasses.dataclass
class GraphChange:
    removed_nodes: Set[str] = dataclasses.field(default_factory=set)
    added_updated_nodes: Set[str] = dataclasses.field(default_factory=set)
    removed_edges: Set[Tuple[str, str]] = dataclasses.field(default_factory=set)
    added_updated_edges: Set[Tuple[str, str]] = dataclasses.field(default_factory=set)


def perform_variable_replacements(input: str, history: list[dict] | None = None, variables: dict | None = None) -> str:
    """Perform variable replacements on the input string and in a chat log."""
    if history is None:
        history = []
    if variables is None:
        variables = {}
    result = input

    def replace_all(input: str) -> str:
        result = input
        for k, v in variables.items():
            result = result.replace(f"{{{k}}}", str(v))
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in GraphChange.replace_all).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:5f8eb1e5529fad36588b3d352840616b2d752676ea9f89f4b0b58a6defc0ab7e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5f8eb1e5529fad36588b3d352840616b2d752676ea9f89f4b0b58a6defc0ab7e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 60, 'function': 'perform_variable_replacements.replace_all'}, 'file': 'graphrag/utils.py', 'line': 60, 'function': 'replace_all', 'agent_name': 'GraphChange', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result

    result = replace_all(result)
    for i, entry in enumerate(history):
        if entry.get("role") == "system":
            entry["content"] = replace_all(entry.get("content") or "")

    # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in perform_variable_replacements).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:8d1dfdae662391258030d0cf4189ca4677090c37644e8c07dbe71013559b03e9'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8d1dfdae662391258030d0cf4189ca4677090c37644e8c07dbe71013559b03e9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 67, 'function': 'perform_variable_replacements'}, 'file': 'graphrag/utils.py', 'line': 67, 'function': 'perform_variable_replacements', 'agent_name': 'perform_variable_replacements', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return result


def clean_str(input: Any) -> str:
    """Clean an input string by removing HTML escapes, control characters, and other unwanted characters."""
    # If we get non-string input, just give it back
    if not isinstance(input, str):
        # LINEAJE: runtime guardrail checks `input` as it flows from the agent to the user interface, before it leaves the application (in clean_str).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `input` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a8c19942b4c23f0e44b11ecb0a6449a5413c4b1b54c09c80c8eb3eda08323c91'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a8c19942b4c23f0e44b11ecb0a6449a5413c4b1b54c09c80c8eb3eda08323c91', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 74, 'function': 'clean_str'}, 'file': 'graphrag/utils.py', 'line': 74, 'function': 'clean_str', 'agent_name': 'clean_str', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            input = _gr_client.enforce(_gr_site, input, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return input

    result = html.unescape(input.strip())
    # https://stackoverflow.com/questions/4324790/removing-control-characters-from-a-string-in-python
    return re.sub(r"[\"\x00-\x1f\x7f-\x9f]", "", result)


def dict_has_keys_with_types(data: dict, expected_fields: list[tuple[str, type]]) -> bool:
    """Return True if the given dictionary has the given keys with the given types."""
    for field, field_type in expected_fields:
        if field not in data:
            return False

        value = data[field]
        if not isinstance(value, field_type):
            return False
    return True


def get_llm_cache(llmnm, txt, history, genconf):
    hasher = xxhash.xxh64()
    hasher.update((str(llmnm)+str(txt)+str(history)+str(genconf)).encode("utf-8"))

    k = hasher.hexdigest()
    bin = REDIS_CONN.get(k)
    if not bin:
        return None
    # LINEAJE: runtime guardrail checks `bin` as it flows from the agent to the user interface, before it leaves the application (in get_llm_cache).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `bin` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e2fc065fc46312dd09c3d95ba323de870e43adccf6d8d4c74b215d44d8a81704'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e2fc065fc46312dd09c3d95ba323de870e43adccf6d8d4c74b215d44d8a81704', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 101, 'function': 'get_llm_cache'}, 'file': 'graphrag/utils.py', 'line': 101, 'function': 'get_llm_cache', 'agent_name': 'get_llm_cache', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        bin = _gr_client.enforce(_gr_site, bin, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return bin


def set_llm_cache(llmnm, txt, v, history, genconf):
    hasher = xxhash.xxh64()
    hasher.update((str(llmnm)+str(txt)+str(history)+str(genconf)).encode("utf-8"))
    k = hasher.hexdigest()
    REDIS_CONN.set(k, v.encode("utf-8"), 24 * 3600)


def get_embed_cache(llmnm, txt):
    hasher = xxhash.xxh64()
    hasher.update(str(llmnm).encode("utf-8"))
    hasher.update(str(txt).encode("utf-8"))

    k = hasher.hexdigest()
    bin = REDIS_CONN.get(k)
    if not bin:
        return
    return np.array(json.loads(bin))


def set_embed_cache(llmnm, txt, arr):
    hasher = xxhash.xxh64()
    hasher.update(str(llmnm).encode("utf-8"))
    hasher.update(str(txt).encode("utf-8"))

    k = hasher.hexdigest()
    arr = json.dumps(arr.tolist() if isinstance(arr, np.ndarray) else arr)
    REDIS_CONN.set(k, arr.encode("utf-8"), 24 * 3600)


def get_tags_from_cache(kb_ids):
    hasher = xxhash.xxh64()
    hasher.update(str(kb_ids).encode("utf-8"))

    k = hasher.hexdigest()
    bin = REDIS_CONN.get(k)
    if not bin:
        return
    # LINEAJE: runtime guardrail checks `bin` as it flows from the agent to the user interface, before it leaves the application (in get_tags_from_cache).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `bin` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:4c52efe572e971f949e442565312678fd863898d02bbbed4f7ee231407233392'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4c52efe572e971f949e442565312678fd863898d02bbbed4f7ee231407233392', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 141, 'function': 'get_tags_from_cache'}, 'file': 'graphrag/utils.py', 'line': 141, 'function': 'get_tags_from_cache', 'agent_name': 'get_tags_from_cache', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        bin = _gr_client.enforce(_gr_site, bin, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return bin


def set_tags_to_cache(kb_ids, tags):
    hasher = xxhash.xxh64()
    hasher.update(str(kb_ids).encode("utf-8"))

    k = hasher.hexdigest()
    # LINEAJE: runtime guardrail checks `tags` as it flows from the agent to an external endpoint, before it leaves the application (in set_tags_to_cache).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `tags` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:506fbc023b92d8d0a7f715c38ee5367a9b6c853d7a1c63d721fd1a2eafe6bcb8'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:506fbc023b92d8d0a7f715c38ee5367a9b6c853d7a1c63d721fd1a2eafe6bcb8', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 149, 'function': 'set_tags_to_cache'}, 'file': 'graphrag/utils.py', 'line': 149, 'function': 'set_tags_to_cache', 'agent_name': 'set_tags_to_cache', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        tags = _gr_client.enforce(_gr_site, tags, content_type='application/json', variable_name='tags', source_file=__file__, before_line=149)
    except _gr_client.GuardrailUnavailableError:
        pass
    REDIS_CONN.set(k, json.dumps(tags).encode("utf-8"), 600)


def tidy_graph(graph: nx.Graph, callback, check_attribute: bool = True):
    """
    Ensure all nodes and edges in the graph have some essential attribute.
    """

    def is_valid_item(node_attrs: dict) -> bool:
        valid_node = True
        for attr in ["description", "source_id"]:
            if attr not in node_attrs:
                valid_node = False
                break
        # LINEAJE: runtime guardrail checks `valid_node` as it flows from the agent to the user interface, before it leaves the application (in GraphChange.is_valid_item).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `valid_node` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9480c6633e98d25333a0334a273f43de936b3d78fe0f4fe5b61cdfd9eb3062c0'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9480c6633e98d25333a0334a273f43de936b3d78fe0f4fe5b61cdfd9eb3062c0', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 163, 'function': 'tidy_graph.is_valid_item'}, 'file': 'graphrag/utils.py', 'line': 163, 'function': 'is_valid_item', 'agent_name': 'GraphChange', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            valid_node = _gr_client.enforce(_gr_site, valid_node, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return valid_node

    if check_attribute:
        purged_nodes = []
        for node, node_attrs in graph.nodes(data=True):
            if not is_valid_item(node_attrs):
                purged_nodes.append(node)
        for node in purged_nodes:
            graph.remove_node(node)
        if purged_nodes and callback:
            callback(msg=f"Purged {len(purged_nodes)} nodes from graph due to missing essential attributes.")

    purged_edges = []
    for source, target, attr in graph.edges(data=True):
        if check_attribute:
            if not is_valid_item(attr):
                purged_edges.append((source, target))
        if "keywords" not in attr:
            attr["keywords"] = []
    for source, target in purged_edges:
        graph.remove_edge(source, target)
    if purged_edges and callback:
        callback(msg=f"Purged {len(purged_edges)} edges from graph due to missing essential attributes.")


def get_from_to(node1, node2):
    if node1 < node2:
        return (node1, node2)
    else:
        return (node2, node1)


def graph_merge(g1: nx.Graph, g2: nx.Graph, change: GraphChange):
    """Merge graph g2 into g1 in place."""
    for node_name, attr in g2.nodes(data=True):
        change.added_updated_nodes.add(node_name)
        if not g1.has_node(node_name):
            g1.add_node(node_name, **attr)
            continue
        node = g1.nodes[node_name]
        node["description"] += GRAPH_FIELD_SEP + attr["description"]
        # A node's source_id indicates which chunks it came from.
        node["source_id"] += attr["source_id"]

    for source, target, attr in g2.edges(data=True):
        change.added_updated_edges.add(get_from_to(source, target))
        edge = g1.get_edge_data(source, target)
        if edge is None:
            g1.add_edge(source, target, **attr)
            continue
        edge["weight"] += attr.get("weight", 0)
        edge["description"] += GRAPH_FIELD_SEP + attr["description"]
        edge["keywords"] += attr["keywords"]
        # A edge's source_id indicates which chunks it came from.
        edge["source_id"] += attr["source_id"]

    for node_degree in g1.degree:
        g1.nodes[str(node_degree[0])]["rank"] = int(node_degree[1])
    # A graph's source_id indicates which documents it came from.
    if "source_id" not in g1.graph:
        g1.graph["source_id"] = []
    g1.graph["source_id"] += g2.graph.get("source_id", [])
    # LINEAJE: runtime guardrail checks `g1` as it flows from the agent to the user interface, before it leaves the application (in graph_merge).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `g1` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:1fc94bfbbda12cce06fb8e740cdfd8e479512099d9b7f7b73f7be846dc608bbd'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1fc94bfbbda12cce06fb8e740cdfd8e479512099d9b7f7b73f7be846dc608bbd', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 225, 'function': 'graph_merge'}, 'file': 'graphrag/utils.py', 'line': 225, 'function': 'graph_merge', 'agent_name': 'graph_merge', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        g1 = _gr_client.enforce(_gr_site, g1, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return g1


def compute_args_hash(*args):
    return md5(str(args).encode()).hexdigest()


def handle_single_entity_extraction(
    record_attributes: list[str],
    chunk_key: str,
):
    if len(record_attributes) < 4 or record_attributes[0] != '"entity"':
        return None
    # add this record as a node in the G
    entity_name = clean_str(record_attributes[1].upper())
    if not entity_name.strip():
        return None
    entity_type = clean_str(record_attributes[2].upper())
    entity_description = clean_str(record_attributes[3])
    entity_source_id = chunk_key
    return dict(
        entity_name=entity_name.upper(),
        entity_type=entity_type.upper(),
        description=entity_description,
        source_id=entity_source_id,
    )


def handle_single_relationship_extraction(record_attributes: list[str], chunk_key: str):
    if len(record_attributes) < 5 or record_attributes[0] != '"relationship"':
        return None
    # add this record as edge
    source = clean_str(record_attributes[1].upper())
    target = clean_str(record_attributes[2].upper())
    edge_description = clean_str(record_attributes[3])

    edge_keywords = clean_str(record_attributes[4])
    edge_source_id = chunk_key
    weight = float(record_attributes[-1]) if is_float_regex(record_attributes[-1]) else 1.0
    pair = sorted([source.upper(), target.upper()])
    return dict(
        src_id=pair[0],
        tgt_id=pair[1],
        weight=weight,
        description=edge_description,
        keywords=edge_keywords,
        source_id=edge_source_id,
        metadata={"created_at": time.time()},
    )


def pack_user_ass_to_openai_messages(*args: str):
    roles = ["user", "assistant"]
    return [{"role": roles[i % 2], "content": content} for i, content in enumerate(args)]


def split_string_by_multi_markers(content: str, markers: list[str]) -> list[str]:
    """Split a string by multiple markers"""
    if not markers:
        return [content]
    results = re.split("|".join(re.escape(marker) for marker in markers), content)
    return [r.strip() for r in results if r.strip()]


def is_float_regex(value):
    return bool(re.match(r"^[-+]?[0-9]*\.?[0-9]+$", value))


def chunk_id(chunk):
    return xxhash.xxh64((chunk["content_with_weight"] + chunk["kb_id"]).encode("utf-8")).hexdigest()


async def graph_node_to_chunk(kb_id, embd_mdl, ent_name, meta, chunks):
    # LINEAJE: runtime guardrail checks `meta` as it flows from the agent to an external endpoint, before it leaves the application (in graph_node_to_chunk).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `meta` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:034eddf8339ab0bdc654506ad4c3181880ff73b34754bfa575740b2c7e9faa97'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:034eddf8339ab0bdc654506ad4c3181880ff73b34754bfa575740b2c7e9faa97', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 298, 'function': 'graph_node_to_chunk'}, 'file': 'graphrag/utils.py', 'line': 298, 'function': 'graph_node_to_chunk', 'agent_name': 'graph_node_to_chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        meta = _gr_client.enforce(_gr_site, meta, content_type='application/json', variable_name='meta', source_file=__file__, before_line=298)
    except _gr_client.GuardrailUnavailableError:
        pass
    global chat_limiter
    enable_timeout_assertion = os.environ.get("ENABLE_TIMEOUT_ASSERTION")
    # LINEAJE: runtime guardrail checks `meta` as it flows from the agent to an external endpoint, before it leaves the application (in graph_node_to_chunk).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `meta` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:9b073c269b8dacf69d31a483990880621578a585bfaa6db9138c4550d9b9250f'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9b073c269b8dacf69d31a483990880621578a585bfaa6db9138c4550d9b9250f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 300, 'function': 'graph_node_to_chunk'}, 'file': 'graphrag/utils.py', 'line': 300, 'function': 'graph_node_to_chunk', 'agent_name': 'graph_node_to_chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        meta = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, meta, content_type='application/json', variable_name='meta', source_file=__file__, before_line=300))
    except _gr_client.GuardrailUnavailableError:
        pass
    chunk = {
        "id": get_uuid(),
        "important_kwd": [ent_name],
        "title_tks": rag_tokenizer.tokenize(ent_name),
        "entity_kwd": ent_name,
        "knowledge_graph_kwd": "entity",
        "entity_type_kwd": meta["entity_type"],
        "content_with_weight": json.dumps(meta, ensure_ascii=False),
        "content_ltks": rag_tokenizer.tokenize(meta["description"]),
        "source_id": meta["source_id"],
        "kb_id": kb_id,
        "available_int": 0,
    }
    chunk["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(chunk["content_ltks"])
    ebd = get_embed_cache(embd_mdl.llm_name, ent_name)
    if ebd is None:
        async with chat_limiter:
            timeout = 3 if enable_timeout_assertion else 30000000
            ebd, _ = await asyncio.wait_for(
                asyncio.to_thread(embd_mdl.encode, [ent_name]),
                timeout=timeout
            )
        ebd = ebd[0]
        set_embed_cache(embd_mdl.llm_name, ent_name, ebd)
    assert ebd is not None
    chunk["q_%d_vec" % len(ebd)] = ebd
    chunks.append(chunk)


@timeout(3, 3)
def get_relation(tenant_id, kb_id, from_ent_name, to_ent_name, size=1):
    ents = from_ent_name
    if isinstance(ents, str):
        ents = [from_ent_name]
    if isinstance(to_ent_name, str):
        to_ent_name = [to_ent_name]
    ents.extend(to_ent_name)
    ents = list(set(ents))
    conds = {"fields": ["content_with_weight"], "size": size, "from_entity_kwd": ents, "to_entity_kwd": ents, "knowledge_graph_kwd": ["relation"]}
    res = []
    es_res = settings.retriever.search(conds, search.index_name(tenant_id), [kb_id] if isinstance(kb_id, str) else kb_id)
    # LINEAJE: runtime guardrail checks `es_res` as it flows from a vector store to the agent, after the tool returns (in get_relation).
    #   Detected: this statement moves data from a vector store to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `es_res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e45957c50dbca524653c9aaa31930fe08d56e10ca5d2cbc52700aa937d230213'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e45957c50dbca524653c9aaa31930fe08d56e10ca5d2cbc52700aa937d230213', phase='post_tool', boundary={'source': 'vector_store', 'sink': 'agent_context'}, fail_mode='ALLOW_WITH_AUDIT', source_type='vector_store', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 340, 'function': 'get_relation'}, 'file': 'graphrag/utils.py', 'line': 340, 'function': 'get_relation', 'agent_name': 'get_relation', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        es_res = _gr_client.enforce(_gr_site, es_res, content_type='application/json', variable_name='es_res', source_file=__file__, before_line=340)
    except _gr_client.GuardrailUnavailableError:
        pass
    for id in es_res.ids:
        try:
            if size == 1:
                return json.loads(es_res.field[id]["content_with_weight"])
            res.append(json.loads(es_res.field[id]["content_with_weight"]))
        except Exception:
            continue
    # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in get_relation).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:679e3edce818e88ccedfe4b412590f09fb2fec1884d4f5201c6e0bc12f716f83'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:679e3edce818e88ccedfe4b412590f09fb2fec1884d4f5201c6e0bc12f716f83', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 348, 'function': 'get_relation'}, 'file': 'graphrag/utils.py', 'line': 348, 'function': 'get_relation', 'agent_name': 'get_relation', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return res


async def graph_edge_to_chunk(kb_id, embd_mdl, from_ent_name, to_ent_name, meta, chunks):
    # LINEAJE: runtime guardrail checks `meta` as it flows from the agent to an external endpoint, before it leaves the application (in graph_edge_to_chunk).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `meta` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:4a0ccd221abb447bdde0cdcde4d777b005e7c2118b696b54250aaa22ae026f49'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4a0ccd221abb447bdde0cdcde4d777b005e7c2118b696b54250aaa22ae026f49', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 352, 'function': 'graph_edge_to_chunk'}, 'file': 'graphrag/utils.py', 'line': 352, 'function': 'graph_edge_to_chunk', 'agent_name': 'graph_edge_to_chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        meta = _gr_client.enforce(_gr_site, meta, content_type='application/json', variable_name='meta', source_file=__file__, before_line=352)
    except _gr_client.GuardrailUnavailableError:
        pass
    enable_timeout_assertion = os.environ.get("ENABLE_TIMEOUT_ASSERTION")
    # LINEAJE: runtime guardrail checks `meta` as it flows from the agent to an external endpoint, before it leaves the application (in graph_edge_to_chunk).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `meta` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:cee74137bd2c90aca4a7e2700c9e931ff01819b292b1d198e1f52a5c01e11f7c'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cee74137bd2c90aca4a7e2700c9e931ff01819b292b1d198e1f52a5c01e11f7c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 353, 'function': 'graph_edge_to_chunk'}, 'file': 'graphrag/utils.py', 'line': 353, 'function': 'graph_edge_to_chunk', 'agent_name': 'graph_edge_to_chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        meta = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, meta, content_type='application/json', variable_name='meta', source_file=__file__, before_line=353))
    except _gr_client.GuardrailUnavailableError:
        pass
    chunk = {
        "id": get_uuid(),
        "from_entity_kwd": from_ent_name,
        "to_entity_kwd": to_ent_name,
        "knowledge_graph_kwd": "relation",
        "content_with_weight": json.dumps(meta, ensure_ascii=False),
        "content_ltks": rag_tokenizer.tokenize(meta["description"]),
        "important_kwd": meta["keywords"],
        "source_id": meta["source_id"],
        "weight_int": int(meta["weight"]),
        "kb_id": kb_id,
        "available_int": 0,
    }
    chunk["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(chunk["content_ltks"])
    txt = f"{from_ent_name}->{to_ent_name}"
    ebd = get_embed_cache(embd_mdl.llm_name, txt)
    if ebd is None:
        async with chat_limiter:
            timeout = 3 if enable_timeout_assertion else 300000000
            ebd, _ = await asyncio.wait_for(
                asyncio.to_thread(
                    embd_mdl.encode,
                    [txt + f": {meta['description']}"]
                ),
                timeout=timeout
            )
        ebd = ebd[0]
        set_embed_cache(embd_mdl.llm_name, txt, ebd)
    assert ebd is not None
    chunk["q_%d_vec" % len(ebd)] = ebd
    chunks.append(chunk)


async def does_graph_contains(tenant_id, kb_id, doc_id):
    # Get doc_ids of graph
    fields = ["source_id"]
    condition = {
        "knowledge_graph_kwd": ["graph"],
        "removed_kwd": "N",
    }
    res = await asyncio.to_thread(
        settings.docStoreConn.search,
        fields, [], condition, [], OrderByExpr(),
        0, 1, search.index_name(tenant_id), [kb_id]
    )
    fields2 = settings.docStoreConn.get_fields(res, fields)
    graph_doc_ids = set()
    for chunk_id in fields2.keys():
        graph_doc_ids = set(fields2[chunk_id]["source_id"])
    return doc_id in graph_doc_ids


async def get_graph_doc_ids(tenant_id, kb_id) -> list[str]:
    conds = {"fields": ["source_id"], "removed_kwd": "N", "size": 1, "knowledge_graph_kwd": ["graph"]}
    res = await asyncio.to_thread(
        settings.retriever.search,
        conds,
        search.index_name(tenant_id),
        [kb_id]
    )
    doc_ids = []
    if res.total == 0:
        # LINEAJE: runtime guardrail checks `doc_ids` as it flows from the agent to the user interface, before it leaves the application (in get_graph_doc_ids).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `doc_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:41108d4d68543bace81014f3bc97f162d6f4d8e3ef3693087192a28cb93b246d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:41108d4d68543bace81014f3bc97f162d6f4d8e3ef3693087192a28cb93b246d', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 415, 'function': 'get_graph_doc_ids'}, 'file': 'graphrag/utils.py', 'line': 415, 'function': 'get_graph_doc_ids', 'agent_name': 'get_graph_doc_ids', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            doc_ids = _gr_client.enforce(_gr_site, doc_ids, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return doc_ids
    for id in res.ids:
        doc_ids = res.field[id]["source_id"]
    # LINEAJE: runtime guardrail checks `doc_ids` as it flows from the agent to the user interface, before it leaves the application (in get_graph_doc_ids).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `doc_ids` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:bc94ca6169418cf0777afaf7a5f0340d53be8bd1b10599e27551241f26bf174c'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bc94ca6169418cf0777afaf7a5f0340d53be8bd1b10599e27551241f26bf174c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 418, 'function': 'get_graph_doc_ids'}, 'file': 'graphrag/utils.py', 'line': 418, 'function': 'get_graph_doc_ids', 'agent_name': 'get_graph_doc_ids', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        doc_ids = _gr_client.enforce(_gr_site, doc_ids, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return doc_ids


async def get_graph(tenant_id, kb_id, exclude_rebuild=None):
    conds = {"fields": ["content_with_weight", "removed_kwd", "source_id"], "size": 1, "knowledge_graph_kwd": ["graph"]}
    res = await asyncio.to_thread(
        settings.retriever.search,
        conds,
        search.index_name(tenant_id),
        [kb_id]
    )
    if not res.total == 0:
        for id in res.ids:
            try:
                if res.field[id]["removed_kwd"] == "N":
                    g = json_graph.node_link_graph(json.loads(res.field[id]["content_with_weight"]), edges="edges")
                    if "source_id" not in g.graph:
                        g.graph["source_id"] = res.field[id]["source_id"]
                else:
                    g = await rebuild_graph(tenant_id, kb_id, exclude_rebuild)
                # LINEAJE: runtime guardrail checks `g` as it flows from the agent to the user interface, before it leaves the application (in get_graph).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `g` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:039cbc5d5ff3a95090b9d0bd1b7ce28e103c5d3f52c346a83a494a350d60cf34'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:039cbc5d5ff3a95090b9d0bd1b7ce28e103c5d3f52c346a83a494a350d60cf34', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 438, 'function': 'get_graph'}, 'file': 'graphrag/utils.py', 'line': 438, 'function': 'get_graph', 'agent_name': 'get_graph', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    g = _gr_client.enforce(_gr_site, g, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return g
            except Exception:
                continue
    result = None
    # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in get_graph).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:309cab8f95993f147ff381e46dac9537766a75f717bd960b568f4bdeb1f45260'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:309cab8f95993f147ff381e46dac9537766a75f717bd960b568f4bdeb1f45260', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 442, 'function': 'get_graph'}, 'file': 'graphrag/utils.py', 'line': 442, 'function': 'get_graph', 'agent_name': 'get_graph', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return result


async def set_graph(tenant_id: str, kb_id: str, embd_mdl, graph: nx.Graph, change: GraphChange, callback):
    # LINEAJE: runtime guardrail checks `graph` as it flows from the agent to an external endpoint, before it leaves the application (in set_graph).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `graph` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:1fd82eaeea8f185bcce92a88e2bfff25516d5a9b96ed13c23e4f888caeab74ec'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1fd82eaeea8f185bcce92a88e2bfff25516d5a9b96ed13c23e4f888caeab74ec', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 446, 'function': 'set_graph'}, 'file': 'graphrag/utils.py', 'line': 446, 'function': 'set_graph', 'agent_name': 'set_graph', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        graph = _gr_client.enforce(_gr_site, graph, content_type='application/json', variable_name='graph', source_file=__file__, before_line=446)
    except _gr_client.GuardrailUnavailableError:
        pass
    global chat_limiter
    start = asyncio.get_running_loop().time()

    await asyncio.to_thread(
        settings.docStoreConn.delete,
        {"knowledge_graph_kwd": ["graph", "subgraph"]},
        search.index_name(tenant_id),
        kb_id
    )

    if change.removed_nodes:
        await asyncio.to_thread(
            settings.docStoreConn.delete,
            {"knowledge_graph_kwd": ["entity"], "entity_kwd": sorted(change.removed_nodes)},
            search.index_name(tenant_id),
            kb_id
        )

    if change.removed_edges:

        async def del_edges(from_node, to_node):
            async with chat_limiter:
                await asyncio.to_thread(
                    settings.docStoreConn.delete,
                    {"knowledge_graph_kwd": ["relation"], "from_entity_kwd": from_node, "to_entity_kwd": to_node},
                    search.index_name(tenant_id),
                    kb_id
                )

        tasks = []
        for from_node, to_node in change.removed_edges:
            tasks.append(asyncio.create_task(del_edges(from_node, to_node)))

        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            _lineaje_payload = f"Error while deleting edges: {e}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in GraphChange.del_edges).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:dd5a2d42d6d35ecd30606e956e73ca82e66959aafac7cc0253dcb01f8fcda81f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dd5a2d42d6d35ecd30606e956e73ca82e66959aafac7cc0253dcb01f8fcda81f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 482, 'function': 'set_graph'}, 'file': 'graphrag/utils.py', 'line': 482, 'function': 'del_edges', 'agent_name': 'GraphChange', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.error(_lineaje_payload)
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    now = asyncio.get_running_loop().time()
    if callback:
        callback(msg=f"set_graph removed {len(change.removed_nodes)} nodes and {len(change.removed_edges)} edges from index in {now - start:.2f}s.")
    start = now

    chunks = [
        {
            "id": get_uuid(),
            "content_with_weight": json.dumps(nx.node_link_data(graph, edges="edges"), ensure_ascii=False),
            "knowledge_graph_kwd": "graph",
            "kb_id": kb_id,
            "source_id": graph.graph.get("source_id", []),
            "available_int": 0,
            "removed_kwd": "N",
        }
    ]

    # generate updated subgraphs
    for source in graph.graph["source_id"]:
        subgraph = graph.subgraph([n for n in graph.nodes if source in graph.nodes[n]["source_id"]]).copy()
        subgraph.graph["source_id"] = [source]
        for n in subgraph.nodes:
            subgraph.nodes[n]["source_id"] = [source]
        chunks.append(
            {
                "id": get_uuid(),
                "content_with_weight": json.dumps(nx.node_link_data(subgraph, edges="edges"), ensure_ascii=False),
                "knowledge_graph_kwd": "subgraph",
                "kb_id": kb_id,
                "source_id": [source],
                "available_int": 0,
                "removed_kwd": "N",
            }
        )

    tasks = []
    for ii, node in enumerate(change.added_updated_nodes):
        node_attrs = graph.nodes[node]
        tasks.append(asyncio.create_task(
            graph_node_to_chunk(kb_id, embd_mdl, node, node_attrs, chunks)
        ))
        if ii % 100 == 9 and callback:
            callback(msg=f"Get embedding of nodes: {ii}/{len(change.added_updated_nodes)}")
    try:
        await asyncio.gather(*tasks, return_exceptions=False)
    except Exception as e:
        _lineaje_payload = f"Error in get_embedding_of_nodes: {e}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in set_graph).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:2e51640ea6f40b897a365996cc8d305693cc854750de6595cd187e08ca96936b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2e51640ea6f40b897a365996cc8d305693cc854750de6595cd187e08ca96936b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 534, 'function': 'set_graph'}, 'file': 'graphrag/utils.py', 'line': 534, 'function': 'set_graph', 'agent_name': 'set_graph', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(_lineaje_payload)
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise

    tasks = []
    for ii, (from_node, to_node) in enumerate(change.added_updated_edges):
        edge_attrs = graph.get_edge_data(from_node, to_node)
        if not edge_attrs:
            continue
        tasks.append(asyncio.create_task(
            graph_edge_to_chunk(kb_id, embd_mdl, from_node, to_node, edge_attrs, chunks)
        ))
        if ii % 100 == 9 and callback:
            callback(msg=f"Get embedding of edges: {ii}/{len(change.added_updated_edges)}")
    try:
        await asyncio.gather(*tasks, return_exceptions=False)
    except Exception as e:
        _lineaje_payload = f"Error in get_embedding_of_edges: {e}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in set_graph).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:778459ad0dd83110871f616ee273fd5a7323d790b6a4aba923f502f71020cab9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:778459ad0dd83110871f616ee273fd5a7323d790b6a4aba923f502f71020cab9', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 553, 'function': 'set_graph'}, 'file': 'graphrag/utils.py', 'line': 553, 'function': 'set_graph', 'agent_name': 'set_graph', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(_lineaje_payload)
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise

    now = asyncio.get_running_loop().time()
    if callback:
        callback(msg=f"set_graph converted graph change to {len(chunks)} chunks in {now - start:.2f}s.")
    start = now

    enable_timeout_assertion = os.environ.get("ENABLE_TIMEOUT_ASSERTION")
    es_bulk_size = 4
    for b in range(0, len(chunks), es_bulk_size):
        timeout = 3 if enable_timeout_assertion else 30000000
        doc_store_result = await asyncio.wait_for(
            asyncio.to_thread(
                settings.docStoreConn.insert,
                chunks[b : b + es_bulk_size],
                search.index_name(tenant_id),
                kb_id
            ),
            timeout=timeout
        )
        if b % 100 == es_bulk_size and callback:
            callback(msg=f"Insert chunks: {b}/{len(chunks)}")
        if doc_store_result:
            error_message = f"Insert chunk error: {doc_store_result}, please check log file and Elasticsearch/Infinity status!"
            raise Exception(error_message)
    now = asyncio.get_running_loop().time()
    if callback:
        callback(msg=f"set_graph added/updated {len(change.added_updated_nodes)} nodes and {len(change.added_updated_edges)} edges from index in {now - start:.2f}s.")


def is_continuous_subsequence(subseq, seq):
    def find_all_indexes(tup, value):
        indexes = []
        start = 0
        while True:
            try:
                index = tup.index(value, start)
                indexes.append(index)
                start = index + 1
            except ValueError:
                break
        # LINEAJE: runtime guardrail checks `indexes` as it flows from the agent to the user interface, before it leaves the application (in GraphChange.find_all_indexes).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `indexes` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:1c3e3435df8ac05a9e55233abd3d32bc20a91cd510ba53f6a5aa3c6a8c52925d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1c3e3435df8ac05a9e55233abd3d32bc20a91cd510ba53f6a5aa3c6a8c52925d', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 598, 'function': 'is_continuous_subsequence.find_all_indexes'}, 'file': 'graphrag/utils.py', 'line': 598, 'function': 'find_all_indexes', 'agent_name': 'GraphChange', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            indexes = _gr_client.enforce(_gr_site, indexes, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return indexes

    index_list = find_all_indexes(seq, subseq[0])
    for idx in index_list:
        if idx != len(seq) - 1:
            if seq[idx + 1] == subseq[-1]:
                return True
    return False


def merge_tuples(list1, list2):
    result = []
    for tup in list1:
        last_element = tup[-1]
        if last_element in tup[:-1]:
            result.append(tup)
        else:
            matching_tuples = [t for t in list2 if t[0] == last_element]
            already_match_flag = 0
            for match in matching_tuples:
                matchh = (match[1], match[0])
                if is_continuous_subsequence(match, tup) or is_continuous_subsequence(matchh, tup):
                    continue
                already_match_flag = 1
                merged_tuple = tup + match[1:]
                result.append(merged_tuple)
            if not already_match_flag:
                result.append(tup)
    # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in merge_tuples).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:0ab316cbe1fb8dc9084f5675f9e71da6bcfaa0e6c1638585b625216be778bb8b'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0ab316cbe1fb8dc9084f5675f9e71da6bcfaa0e6c1638585b625216be778bb8b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 626, 'function': 'merge_tuples'}, 'file': 'graphrag/utils.py', 'line': 626, 'function': 'merge_tuples', 'agent_name': 'merge_tuples', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return result


def get_entity_type2samples(idxnms, kb_ids: list):
    es_res = settings.retriever.search({"knowledge_graph_kwd": "ty2ents", "kb_id": kb_ids, "size": 10000, "fields": ["content_with_weight"]},idxnms,kb_ids)
    # LINEAJE: runtime guardrail checks `es_res` as it flows from a vector store to the agent, after the tool returns (in get_entity_type2samples).
    #   Detected: this statement moves data from a vector store to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `es_res` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:73f9b0b9acaf1f80ca99ab3554e70f3f1bc95d4a104ca02306111930d55d4b42'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:73f9b0b9acaf1f80ca99ab3554e70f3f1bc95d4a104ca02306111930d55d4b42', phase='post_tool', boundary={'source': 'vector_store', 'sink': 'agent_context'}, fail_mode='ALLOW_WITH_AUDIT', source_type='vector_store', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 630, 'function': 'get_entity_type2samples'}, 'file': 'graphrag/utils.py', 'line': 630, 'function': 'get_entity_type2samples', 'agent_name': 'get_entity_type2samples', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        es_res = _gr_client.enforce(_gr_site, es_res, content_type='application/json', variable_name='es_res', source_file=__file__, before_line=630)
    except _gr_client.GuardrailUnavailableError:
        pass

    res = defaultdict(list)
    for id in es_res.ids:
        smp = es_res.field[id].get("content_with_weight")
        # LINEAJE: runtime guardrail checks `smp` as it flows from an external API to the agent, after the tool returns (in get_entity_type2samples).
        #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `smp` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c2678856089f6fd3fbf88299859f5ea101ce2852f84d5548999d4ed03d2692c3'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c2678856089f6fd3fbf88299859f5ea101ce2852f84d5548999d4ed03d2692c3', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 634, 'function': 'get_entity_type2samples'}, 'file': 'graphrag/utils.py', 'line': 634, 'function': 'get_entity_type2samples', 'agent_name': 'get_entity_type2samples', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            smp = _gr_client.enforce(_gr_site, smp, content_type='application/json', variable_name='smp', source_file=__file__, before_line=634)
        except _gr_client.GuardrailUnavailableError:
            pass
        if not smp:
            continue
        try:
            smp = json.loads(smp)
        except Exception as e:
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in get_entity_type2samples).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ec5170f0815a8a16382eed011c503ed52bd05a1e61bee18fec772d41e9b08392'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ec5170f0815a8a16382eed011c503ed52bd05a1e61bee18fec772d41e9b08392', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 640, 'function': 'get_entity_type2samples'}, 'file': 'graphrag/utils.py', 'line': 640, 'function': 'get_entity_type2samples', 'agent_name': 'get_entity_type2samples', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                e = _gr_client.enforce(_gr_site, e, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)

        for ty, ents in smp.items():
            res[ty].extend(ents)
    # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in get_entity_type2samples).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:962f5c74cf605afef87bfbb702a68184d13bcaab27e2967e56f7af74a65f3aea'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:962f5c74cf605afef87bfbb702a68184d13bcaab27e2967e56f7af74a65f3aea', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 644, 'function': 'get_entity_type2samples'}, 'file': 'graphrag/utils.py', 'line': 644, 'function': 'get_entity_type2samples', 'agent_name': 'get_entity_type2samples', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return res


def flat_uniq_list(arr, key):
    res = []
    for a in arr:
        a = a[key]
        if isinstance(a, list):
            res.extend(a)
        else:
            res.append(a)
    return list(set(res))


async def rebuild_graph(tenant_id, kb_id, exclude_rebuild=None):
    graph = nx.Graph()
    flds = ["knowledge_graph_kwd", "content_with_weight", "source_id"]
    bs = 256
    for i in range(0, 1024 * bs, bs):
        es_res = await asyncio.to_thread(
            settings.docStoreConn.search,
            flds, [], {"kb_id": kb_id, "knowledge_graph_kwd": ["subgraph"]},
            [], OrderByExpr(), i, bs, search.index_name(tenant_id), [kb_id]
        )
        # tot = settings.docStoreConn.get_total(es_res)
        es_res = settings.docStoreConn.get_fields(es_res, flds)

        if len(es_res) == 0:
            break

        for id, d in es_res.items():
            assert d["knowledge_graph_kwd"] == "subgraph"
            if isinstance(exclude_rebuild, list):
                if sum([n in d["source_id"] for n in exclude_rebuild]):
                    continue
            elif exclude_rebuild in d["source_id"]:
                continue

            next_graph = json_graph.node_link_graph(json.loads(d["content_with_weight"]), edges="edges")
            merged_graph = nx.compose(graph, next_graph)
            merged_source = {n: graph.nodes[n]["source_id"] + next_graph.nodes[n]["source_id"] for n in graph.nodes & next_graph.nodes}
            nx.set_node_attributes(merged_graph, merged_source, "source_id")
            if "source_id" in graph.graph:
                merged_graph.graph["source_id"] = graph.graph["source_id"] + next_graph.graph["source_id"]
            else:
                merged_graph.graph["source_id"] = next_graph.graph["source_id"]
            graph = merged_graph

    if len(graph.nodes) == 0:
        return None
    graph.graph["source_id"] = sorted(graph.graph["source_id"])
    # LINEAJE: runtime guardrail checks `graph` as it flows from the agent to the user interface, before it leaves the application (in rebuild_graph).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `graph` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:52b61c0183fe212ebcf87c6c003bd8334daea6da26593f5da4deb6a0ef1193ad'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:52b61c0183fe212ebcf87c6c003bd8334daea6da26593f5da4deb6a0ef1193ad', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/utils.py', 'line': 695, 'function': 'rebuild_graph'}, 'file': 'graphrag/utils.py', 'line': 695, 'function': 'rebuild_graph', 'agent_name': 'rebuild_graph', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        graph = _gr_client.enforce(_gr_site, graph, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return graph
