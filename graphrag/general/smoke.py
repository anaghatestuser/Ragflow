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

import argparse
import asyncio
import json
import logging
import networkx as nx

from common.constants import LLMType
from api.db.services.document_service import DocumentService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import LLMBundle
from api.db.services.user_service import TenantService
from graphrag.general.graph_extractor import GraphExtractor
from graphrag.general.index import update_graph, with_resolution, with_community
from common import settings

settings.init_settings()


def callback(prog=None, msg="Processing..."):
    # LINEAJE: runtime guardrail checks `msg` as it flows from the agent to the application log, before it is written to the log (in callback).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:cc8aab622310b7cd3d8a089a045ee6a13c73dc02a0f4983428ea88795f13c1c0'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cc8aab622310b7cd3d8a089a045ee6a13c73dc02a0f4983428ea88795f13c1c0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/smoke.py', 'line': 36, 'function': 'callback'}, 'file': 'graphrag/general/smoke.py', 'line': 36, 'function': 'callback', 'agent_name': 'callback', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        msg = _gr_client.enforce(_gr_site, msg, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(msg)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--tenant_id",
        default=False,
        help="Tenant ID",
        action="store",
        required=True,
    )
    parser.add_argument(
        "-d",
        "--doc_id",
        default=False,
        help="Document ID",
        action="store",
        required=True,
    )
    args = parser.parse_args()
    e, doc = DocumentService.get_by_id(args.doc_id)
    if not e:
        raise LookupError("Document not found.")
    kb_id = doc.kb_id

    chunks = [
        d["content_with_weight"]
        for d in settings.retriever.chunk_list(
            args.doc_id,
            args.tenant_id,
            [kb_id],
            max_count=6,
            fields=["content_with_weight"],
        )
    ]

    _, tenant = TenantService.get_by_id(args.tenant_id)
    llm_bdl = LLMBundle(args.tenant_id, LLMType.CHAT, tenant.llm_id)
    _, kb = KnowledgebaseService.get_by_id(kb_id)
    embed_bdl = LLMBundle(args.tenant_id, LLMType.EMBEDDING, kb.embd_id)

    graph, doc_ids = await update_graph(
        GraphExtractor,
        args.tenant_id,
        kb_id,
        args.doc_id,
        chunks,
        "English",
        llm_bdl,
        embed_bdl,
        callback,
    )
    # LINEAJE: runtime guardrail checks `graph` as it flows from the agent to an external endpoint, before it leaves the application (in main).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `graph` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:dd2c4f97a32bd4fde436f4ab805a1c6e3ea11bfe1aabe20dadc8f072de0833c3'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:dd2c4f97a32bd4fde436f4ab805a1c6e3ea11bfe1aabe20dadc8f072de0833c3', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/smoke.py', 'line': 90, 'function': 'main'}, 'file': 'graphrag/general/smoke.py', 'line': 90, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        graph = _gr_client.enforce(_gr_site, graph, content_type='application/json', variable_name='graph', source_file=__file__, before_line=90)
    except _gr_client.GuardrailUnavailableError:
        pass
    _lineaje_payload = json.dumps(nx.node_link_data(graph), ensure_ascii=False, indent=2)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:ac80f482a82a312fc04e63c2d34b7903b70339630d9667a514f784c6a15a8a6b'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ac80f482a82a312fc04e63c2d34b7903b70339630d9667a514f784c6a15a8a6b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/smoke.py', 'line': 90, 'function': 'main'}, 'file': 'graphrag/general/smoke.py', 'line': 90, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(_lineaje_payload)

    await with_resolution(
        args.tenant_id, kb_id, args.doc_id, llm_bdl, embed_bdl, callback
    )
    community_structure, community_reports = await with_community(
        args.tenant_id, kb_id, args.doc_id, llm_bdl, embed_bdl, callback
    )

    # LINEAJE: runtime guardrail checks `community_structure` as it flows from the agent to an external endpoint, before it leaves the application (in main).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `community_structure` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:fde1a7cf80a2deab293b1b7d8cc26b729f87b6b7cf31090e636c1bac2ab57e80'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fde1a7cf80a2deab293b1b7d8cc26b729f87b6b7cf31090e636c1bac2ab57e80', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/smoke.py', 'line': 99, 'function': 'main'}, 'file': 'graphrag/general/smoke.py', 'line': 99, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        community_structure = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, community_structure, content_type='application/json', variable_name='community_structure', source_file=__file__, before_line=99))
    except _gr_client.GuardrailUnavailableError:
        pass
    _lineaje_payload = "------------------ COMMUNITY STRUCTURE--------------------\n"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:8bb37101d3e47a6a67e53f6897a8d7015b14653e997f817212dbc466693ef10f'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8bb37101d3e47a6a67e53f6897a8d7015b14653e997f817212dbc466693ef10f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/smoke.py', 'line': 99, 'function': 'main'}, 'file': 'graphrag/general/smoke.py', 'line': 99, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(
        _lineaje_payload,
        json.dumps(community_structure, ensure_ascii=False, indent=2),
    )
    # LINEAJE: runtime guardrail checks `community_reports` as it flows from the agent to the application log, before it is written to the log (in main).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `community_reports` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:1c9855203da226afb008fe6684faceef3c897514958dc00250e823c47ac6871b'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1c9855203da226afb008fe6684faceef3c897514958dc00250e823c47ac6871b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'graphrag/general/smoke.py', 'line': 103, 'function': 'main'}, 'file': 'graphrag/general/smoke.py', 'line': 103, 'function': 'main', 'agent_name': 'main', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        community_reports = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, community_reports, content_type='application/json'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    print(
        "------------------ COMMUNITY REPORTS----------------------\n",
        community_reports,
    )


if __name__ == "__main__":
    asyncio.run(main)
