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
import json
import os
import sys
import time
import argparse
from collections import defaultdict

from common import settings
from common.constants import LLMType
from api.db.services.llm_service import LLMBundle
from api.db.services.knowledgebase_service import KnowledgebaseService
from common.misc_utils import get_uuid
from rag.nlp import tokenize, search
from ranx import evaluate
from ranx import Qrels, Run
import pandas as pd
from tqdm import tqdm

global max_docs
max_docs = sys.maxsize


class Benchmark:
    def __init__(self, kb_id):
        self.kb_id = kb_id
        e, self.kb = KnowledgebaseService.get_by_id(kb_id)
        self.similarity_threshold = self.kb.similarity_threshold
        self.vector_similarity_weight = self.kb.vector_similarity_weight
        self.embd_mdl = LLMBundle(self.kb.tenant_id, LLMType.EMBEDDING, llm_name=self.kb.embd_id, lang=self.kb.language)
        self.tenant_id = ''
        self.index_name = ''
        self.initialized_index = False

    def _get_retrieval(self, qrels):
        # Need to wait for the ES and Infinity index to be ready
        time.sleep(20)
        run = defaultdict(dict)
        query_list = list(qrels.keys())
        for query in query_list:
            ranks = settings.retriever.retrieval(query, self.embd_mdl, self.tenant_id, [self.kb.id], 1, 30,
                                            0.0, self.vector_similarity_weight)
            # LINEAJE: runtime guardrail checks `ranks` as it flows from a vector store to the agent, after the tool returns (in Benchmark._get_retrieval).
            #   Detected: this statement moves data from a vector store to the agent with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `ranks` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:b862b97208d7b2a919690a8c0587e1c9397ed3cf88919e67dc652305274dc886'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b862b97208d7b2a919690a8c0587e1c9397ed3cf88919e67dc652305274dc886', phase='post_tool', boundary={'source': 'vector_store', 'sink': 'agent_context'}, fail_mode='ALLOW_WITH_AUDIT', source_type='vector_store', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 55, 'function': 'Benchmark._get_retrieval'}, 'file': 'rag/benchmark.py', 'line': 55, 'function': '_get_retrieval', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                ranks = _gr_client.enforce(_gr_site, ranks, content_type='application/json', variable_name='ranks', source_file=__file__, before_line=55)
            except _gr_client.GuardrailUnavailableError:
                pass
            if len(ranks["chunks"]) == 0:
                _lineaje_payload = f"deleted query: {query}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Benchmark._get_retrieval).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:ca282085e7dc3db8863282ded7d6fd96a4ef1be4645d5c0615e1207bd935f437'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ca282085e7dc3db8863282ded7d6fd96a4ef1be4645d5c0615e1207bd935f437', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 58, 'function': 'Benchmark._get_retrieval'}, 'file': 'rag/benchmark.py', 'line': 58, 'function': '_get_retrieval', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
                del qrels[query]
                continue
            for c in ranks["chunks"]:
                c.pop("vector", None)
                run[query][c["chunk_id"]] = c["similarity"]
        # LINEAJE: runtime guardrail checks `run` as it flows from the agent to the user interface, before it leaves the application (in Benchmark._get_retrieval).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `run` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:92d5e46187e35aff34038253880defdc5bace57cb0051ec5a223c635b32e92e9'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:92d5e46187e35aff34038253880defdc5bace57cb0051ec5a223c635b32e92e9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 64, 'function': 'Benchmark._get_retrieval'}, 'file': 'rag/benchmark.py', 'line': 64, 'function': '_get_retrieval', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            run = _gr_client.enforce(_gr_site, run, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return run

    def embedding(self, docs):
        texts = [d["content_with_weight"] for d in docs]
        embeddings, _ = self.embd_mdl.encode(texts)
        assert len(docs) == len(embeddings)
        vector_size = 0
        for i, d in enumerate(docs):
            v = embeddings[i]
            vector_size = len(v)
            d["q_%d_vec" % len(v)] = v
        return docs, vector_size

    def init_index(self, vector_size: int):
        if self.initialized_index:
            return
        if settings.docStoreConn.index_exist(self.index_name, self.kb_id):
            settings.docStoreConn.delete_idx(self.index_name, self.kb_id)
        settings.docStoreConn.create_idx(self.index_name, self.kb_id, vector_size)
        self.initialized_index = True

    def ms_marco_index(self, file_path, index_name):
        qrels = defaultdict(dict)
        texts = defaultdict(dict)
        docs_count = 0
        docs = []
        filelist = sorted(os.listdir(file_path))

        for fn in filelist:
            if docs_count >= max_docs:
                break
            if not fn.endswith(".parquet"):
                continue
            data = pd.read_parquet(os.path.join(file_path, fn))
            for i in tqdm(range(len(data)), colour="green", desc="Tokenizing:" + fn):
                if docs_count >= max_docs:
                    break
                query = data.iloc[i]['query']
                for rel, text in zip(data.iloc[i]['passages']['is_selected'], data.iloc[i]['passages']['passage_text']):
                    d = {
                        "id": get_uuid(),
                        "kb_id": self.kb.id,
                        "docnm_kwd": "xxxxx",
                        "doc_id": "ksksks"
                    }
                    tokenize(d, text, "english")
                    docs.append(d)
                    texts[d["id"]] = text
                    qrels[query][d["id"]] = int(rel)
                if len(docs) >= 32:
                    docs_count += len(docs)
                    docs, vector_size = self.embedding(docs)
                    self.init_index(vector_size)
                    # LINEAJE: runtime guardrail checks `docs` as it flows from the RAG pipeline to a vector store, before the tool runs (in Benchmark.ms_marco_index).
                    #   Detected: this statement moves data from the RAG pipeline to a vector store with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `docs` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:939ba4cadd15d35828ae202e2056f87736b83145a013f2522df5616ddb8d85f6'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:939ba4cadd15d35828ae202e2056f87736b83145a013f2522df5616ddb8d85f6', phase='pre_tool', boundary={'source': 'rag_pipeline', 'sink': 'vector_store'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='vector_store', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 117, 'function': 'Benchmark.ms_marco_index'}, 'file': 'rag/benchmark.py', 'line': 117, 'function': 'ms_marco_index', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        docs = _gr_client.enforce(_gr_site, docs, content_type='application/json', variable_name='docs', source_file=__file__, before_line=117)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    settings.docStoreConn.insert(docs, self.index_name, self.kb_id)
                    docs = []

        if docs:
            docs, vector_size = self.embedding(docs)
            self.init_index(vector_size)
            # LINEAJE: runtime guardrail checks `docs` as it flows from the RAG pipeline to a vector store, before the tool runs (in Benchmark.ms_marco_index).
            #   Detected: this statement moves data from the RAG pipeline to a vector store with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `docs` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:757649ea6c524d1b04a21dbbb206050cbe135207f5c0965ecc1cd11c7df3fcba'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:757649ea6c524d1b04a21dbbb206050cbe135207f5c0965ecc1cd11c7df3fcba', phase='pre_tool', boundary={'source': 'rag_pipeline', 'sink': 'vector_store'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='vector_store', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 123, 'function': 'Benchmark.ms_marco_index'}, 'file': 'rag/benchmark.py', 'line': 123, 'function': 'ms_marco_index', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                docs = _gr_client.enforce(_gr_site, docs, content_type='application/json', variable_name='docs', source_file=__file__, before_line=123)
            except _gr_client.GuardrailUnavailableError:
                pass
            settings.docStoreConn.insert(docs, self.index_name, self.kb_id)
        return qrels, texts

    def trivia_qa_index(self, file_path, index_name):
        qrels = defaultdict(dict)
        texts = defaultdict(dict)
        docs_count = 0
        docs = []
        filelist = sorted(os.listdir(file_path))
        for fn in filelist:
            if docs_count >= max_docs:
                break
            if not fn.endswith(".parquet"):
                continue
            data = pd.read_parquet(os.path.join(file_path, fn))
            for i in tqdm(range(len(data)), colour="green", desc="Indexing:" + fn):
                if docs_count >= max_docs:
                    break
                query = data.iloc[i]['question']
                for rel, text in zip(data.iloc[i]["search_results"]['rank'],
                                     data.iloc[i]["search_results"]['search_context']):
                    d = {
                        "id": get_uuid(),
                        "kb_id": self.kb.id,
                        "docnm_kwd": "xxxxx",
                        "doc_id": "ksksks"
                    }
                    tokenize(d, text, "english")
                    docs.append(d)
                    texts[d["id"]] = text
                    qrels[query][d["id"]] = int(rel)
                if len(docs) >= 32:
                    docs_count += len(docs)
                    docs, vector_size = self.embedding(docs)
                    self.init_index(vector_size)
                    # LINEAJE: runtime guardrail checks `docs` as it flows from the RAG pipeline to a vector store, before the tool runs (in Benchmark.trivia_qa_index).
                    #   Detected: this statement moves data from the RAG pipeline to a vector store with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `docs` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:9291c2d5934a8fa77a92b97cd0bac924845130a908804bcf195efcd6e35aed2e'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9291c2d5934a8fa77a92b97cd0bac924845130a908804bcf195efcd6e35aed2e', phase='pre_tool', boundary={'source': 'rag_pipeline', 'sink': 'vector_store'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='vector_store', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 158, 'function': 'Benchmark.trivia_qa_index'}, 'file': 'rag/benchmark.py', 'line': 158, 'function': 'trivia_qa_index', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        docs = _gr_client.enforce(_gr_site, docs, content_type='application/json', variable_name='docs', source_file=__file__, before_line=158)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    settings.docStoreConn.insert(docs,self.index_name)
                    docs = []

        docs, vector_size = self.embedding(docs)
        self.init_index(vector_size)
        # LINEAJE: runtime guardrail checks `docs` as it flows from the RAG pipeline to a vector store, before the tool runs (in Benchmark.trivia_qa_index).
        #   Detected: this statement moves data from the RAG pipeline to a vector store with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `docs` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e127449ae331128906b92aa2993145cd64728a49e6e158dd9948dc174f7001c8'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e127449ae331128906b92aa2993145cd64728a49e6e158dd9948dc174f7001c8', phase='pre_tool', boundary={'source': 'rag_pipeline', 'sink': 'vector_store'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='vector_store', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 163, 'function': 'Benchmark.trivia_qa_index'}, 'file': 'rag/benchmark.py', 'line': 163, 'function': 'trivia_qa_index', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            docs = _gr_client.enforce(_gr_site, docs, content_type='application/json', variable_name='docs', source_file=__file__, before_line=163)
        except _gr_client.GuardrailUnavailableError:
            pass
        settings.docStoreConn.insert(docs, self.index_name)
        return qrels, texts

    def miracl_index(self, file_path, corpus_path, index_name):
        corpus_total = {}
        for corpus_file in os.listdir(corpus_path):
            tmp_data = pd.read_json(os.path.join(corpus_path, corpus_file), lines=True)
            for index, i in tmp_data.iterrows():
                corpus_total[i['docid']] = i['text']

        topics_total = {}
        for topics_file in os.listdir(os.path.join(file_path, 'topics')):
            if 'test' in topics_file:
                continue
            tmp_data = pd.read_csv(os.path.join(file_path, 'topics', topics_file), sep='\t', names=['qid', 'query'])
            for index, i in tmp_data.iterrows():
                topics_total[i['qid']] = i['query']

        qrels = defaultdict(dict)
        texts = defaultdict(dict)
        docs_count = 0
        docs = []
        for qrels_file in os.listdir(os.path.join(file_path, 'qrels')):
            if 'test' in qrels_file:
                continue
            if docs_count >= max_docs:
                break

            tmp_data = pd.read_csv(os.path.join(file_path, 'qrels', qrels_file), sep='\t',
                                   names=['qid', 'Q0', 'docid', 'relevance'])
            for i in tqdm(range(len(tmp_data)), colour="green", desc="Indexing:" + qrels_file):
                if docs_count >= max_docs:
                    break
                query = topics_total[tmp_data.iloc[i]['qid']]
                text = corpus_total[tmp_data.iloc[i]['docid']]
                rel = tmp_data.iloc[i]['relevance']
                d = {
                    "id": get_uuid(),
                    "kb_id": self.kb.id,
                    "docnm_kwd": "xxxxx",
                    "doc_id": "ksksks"
                }
                tokenize(d, text, 'english')
                docs.append(d)
                texts[d["id"]] = text
                qrels[query][d["id"]] = int(rel)
                if len(docs) >= 32:
                    docs_count += len(docs)
                    docs, vector_size = self.embedding(docs)
                    self.init_index(vector_size)
                    # LINEAJE: runtime guardrail checks `docs` as it flows from the RAG pipeline to a vector store, before the tool runs (in Benchmark.miracl_index).
                    #   Detected: this statement moves data from the RAG pipeline to a vector store with no runtime policy check (detection confidence: medium).
                    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `docs` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:508dbebac8ead876426222b455a07ea8785ccf3b0d639a8d9fca6da1774fc523'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:508dbebac8ead876426222b455a07ea8785ccf3b0d639a8d9fca6da1774fc523', phase='pre_tool', boundary={'source': 'rag_pipeline', 'sink': 'vector_store'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='vector_store', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 213, 'function': 'Benchmark.miracl_index'}, 'file': 'rag/benchmark.py', 'line': 213, 'function': 'miracl_index', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        docs = _gr_client.enforce(_gr_site, docs, content_type='application/json', variable_name='docs', source_file=__file__, before_line=213)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    settings.docStoreConn.insert(docs, self.index_name)
                    docs = []

        docs, vector_size = self.embedding(docs)
        self.init_index(vector_size)
        # LINEAJE: runtime guardrail checks `docs` as it flows from the RAG pipeline to a vector store, before the tool runs (in Benchmark.miracl_index).
        #   Detected: this statement moves data from the RAG pipeline to a vector store with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `docs` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:410fd0876754bbae82adfad379558ecc2ca8e5ade56fbfb9bcffb24e4222bf05'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:410fd0876754bbae82adfad379558ecc2ca8e5ade56fbfb9bcffb24e4222bf05', phase='pre_tool', boundary={'source': 'rag_pipeline', 'sink': 'vector_store'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='vector_store', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 218, 'function': 'Benchmark.miracl_index'}, 'file': 'rag/benchmark.py', 'line': 218, 'function': 'miracl_index', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            docs = _gr_client.enforce(_gr_site, docs, content_type='application/json', variable_name='docs', source_file=__file__, before_line=218)
        except _gr_client.GuardrailUnavailableError:
            pass
        settings.docStoreConn.insert(docs, self.index_name)
        return qrels, texts

    def save_results(self, qrels, run, texts, dataset, file_path):
        keep_result = []
        run_keys = list(run.keys())
        for run_i in tqdm(range(len(run_keys)), desc="Calculating ndcg@10 for single query"):
            key = run_keys[run_i]
            keep_result.append({'query': key, 'qrel': qrels[key], 'run': run[key],
                                'ndcg@10': evaluate({key: qrels[key]}, {key: run[key]}, "ndcg@10")})
        keep_result = sorted(keep_result, key=lambda kk: kk['ndcg@10'])
        with open(os.path.join(file_path, dataset + 'result.md'), 'w', encoding='utf-8') as f:
            _lineaje_payload = '## Score For Every Query\n'
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to a file, before it is written to disk (in Benchmark.save_results).
            #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:c65022d4255167f210023c9c7e3cfe1b39cfefe191a55cc7c69f1ea9d80a7f90'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c65022d4255167f210023c9c7e3cfe1b39cfefe191a55cc7c69f1ea9d80a7f90', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 230, 'function': 'Benchmark.save_results'}, 'file': 'rag/benchmark.py', 'line': 230, 'function': 'save_results', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=230)
            except _gr_client.GuardrailUnavailableError:
                pass
            f.write(_lineaje_payload)
            for keep_result_i in keep_result:
                _lineaje_payload = '### query: ' + keep_result_i['query'] + ' ndcg@10:' + str(keep_result_i['ndcg@10']) + '\n'
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to a file, before it is written to disk (in Benchmark.save_results).
                #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:40c2c463272c8ea91731e13e719c2ece2a6817fa1eb10b1453532c0d70e920c5'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:40c2c463272c8ea91731e13e719c2ece2a6817fa1eb10b1453532c0d70e920c5', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 232, 'function': 'Benchmark.save_results'}, 'file': 'rag/benchmark.py', 'line': 232, 'function': 'save_results', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=232)
                except _gr_client.GuardrailUnavailableError:
                    pass
                f.write(_lineaje_payload)
                scores = [[i[0], i[1]] for i in keep_result_i['run'].items()]
                scores = sorted(scores, key=lambda kk: kk[1])
                for score in scores[:10]:
                    _lineaje_payload = '- text: ' + str(texts[score[0]]) + '\t qrel: ' + str(score[1]) + '\n'
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to a file, before it is written to disk (in Benchmark.save_results).
                    #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:d2339c14fe5e1c53a97ce3ce354853086f508e06bc2c91d1c7f649dfe7a3bf90'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d2339c14fe5e1c53a97ce3ce354853086f508e06bc2c91d1c7f649dfe7a3bf90', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 236, 'function': 'Benchmark.save_results'}, 'file': 'rag/benchmark.py', 'line': 236, 'function': 'save_results', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=236)
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    f.write(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `qrels` as it flows from the agent to a file, before it is written to disk (in Benchmark.save_results).
        #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `qrels` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:34459ac19fea73abf9141094051443a2459aeb945a30b92f34d5221405459e28'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:34459ac19fea73abf9141094051443a2459aeb945a30b92f34d5221405459e28', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 237, 'function': 'Benchmark.save_results'}, 'file': 'rag/benchmark.py', 'line': 237, 'function': 'save_results', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            qrels = _gr_client.enforce(_gr_site, qrels, content_type='application/json', variable_name='qrels', source_file=__file__, before_line=237)
        except _gr_client.GuardrailUnavailableError:
            pass
        json.dump(qrels, open(os.path.join(file_path, dataset + '.qrels.json'), "w+", encoding='utf-8'), indent=2)
        # LINEAJE: runtime guardrail checks `run` as it flows from the agent to a file, before it is written to disk (in Benchmark.save_results).
        #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `run` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:fdba5be1a0f7166fec8b49cce44a3ba8093743dfcb776d2af40fe0a2142ad9d1'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:fdba5be1a0f7166fec8b49cce44a3ba8093743dfcb776d2af40fe0a2142ad9d1', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 238, 'function': 'Benchmark.save_results'}, 'file': 'rag/benchmark.py', 'line': 238, 'function': 'save_results', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            run = _gr_client.enforce(_gr_site, run, content_type='application/json', variable_name='run', source_file=__file__, before_line=238)
        except _gr_client.GuardrailUnavailableError:
            pass
        json.dump(run, open(os.path.join(file_path, dataset + '.run.json'), "w+", encoding='utf-8'), indent=2)
        _lineaje_payload = os.path.join(file_path, dataset + '_result.md')
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Benchmark.save_results).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e51a00e0faee16d9615aec996d91e34576df6aeff72cfba5bcf1513bc9b31c44'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e51a00e0faee16d9615aec996d91e34576df6aeff72cfba5bcf1513bc9b31c44', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 239, 'function': 'Benchmark.save_results'}, 'file': 'rag/benchmark.py', 'line': 239, 'function': 'save_results', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        print(_lineaje_payload, 'Saved!')

    def __call__(self, dataset, file_path, miracl_corpus=''):
        if dataset == "ms_marco_v1.1":
            self.tenant_id = "benchmark_ms_marco_v11"
            self.index_name = search.index_name(self.tenant_id)
            qrels, texts = self.ms_marco_index(file_path, "benchmark_ms_marco_v1.1")
            run = self._get_retrieval(qrels)
            # LINEAJE: runtime guardrail checks `dataset` as it flows from the agent to the application log, before it is written to the log (in Benchmark.__call__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `dataset` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:4b4b9892cbb53bdcfb5784b4702f00dd5b8206a06e31275e2c3feb4aed3497e1'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4b4b9892cbb53bdcfb5784b4702f00dd5b8206a06e31275e2c3feb4aed3497e1', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 247, 'function': 'Benchmark.__call__'}, 'file': 'rag/benchmark.py', 'line': 247, 'function': '__call__', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                dataset = _gr_client.enforce(_gr_site, dataset, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(dataset, evaluate(Qrels(qrels), Run(run), ["ndcg@10", "map@5", "mrr@10"]))
            self.save_results(qrels, run, texts, dataset, file_path)
        if dataset == "trivia_qa":
            self.tenant_id = "benchmark_trivia_qa"
            self.index_name = search.index_name(self.tenant_id)
            qrels, texts = self.trivia_qa_index(file_path, "benchmark_trivia_qa")
            run = self._get_retrieval(qrels)
            # LINEAJE: runtime guardrail checks `dataset` as it flows from the agent to the application log, before it is written to the log (in Benchmark.__call__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `dataset` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0ee966a06d5613f8d0be82ae37972a877b594e92e36ce657eb05691f8dcd3b77'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0ee966a06d5613f8d0be82ae37972a877b594e92e36ce657eb05691f8dcd3b77', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 254, 'function': 'Benchmark.__call__'}, 'file': 'rag/benchmark.py', 'line': 254, 'function': '__call__', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                dataset = _gr_client.enforce(_gr_site, dataset, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(dataset, evaluate(Qrels(qrels), Run(run), ["ndcg@10", "map@5", "mrr@10"]))
            self.save_results(qrels, run, texts, dataset, file_path)
        if dataset == "miracl":
            for lang in ['ar', 'bn', 'de', 'en', 'es', 'fa', 'fi', 'fr', 'hi', 'id', 'ja', 'ko', 'ru', 'sw', 'te', 'th',
                         'yo', 'zh']:
                if not os.path.isdir(os.path.join(file_path, 'miracl-v1.0-' + lang)):
                    _lineaje_payload = 'Directory: ' + os.path.join(file_path, 'miracl-v1.0-' + lang) + ' not found!'
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Benchmark.__call__).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:1eefa1f0db3b49a896da57e0f447df8bf97a30b5726c5c62c4967f4f09efb8fc'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1eefa1f0db3b49a896da57e0f447df8bf97a30b5726c5c62c4967f4f09efb8fc', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 260, 'function': 'Benchmark.__call__'}, 'file': 'rag/benchmark.py', 'line': 260, 'function': '__call__', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    print(_lineaje_payload)
                    continue
                if not os.path.isdir(os.path.join(file_path, 'miracl-v1.0-' + lang, 'qrels')):
                    _lineaje_payload = 'Directory: ' + os.path.join(file_path, 'miracl-v1.0-' + lang, 'qrels') + 'not found!'
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Benchmark.__call__).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:ad5a1ede71dc110b1bbe3b3db53618dd9b7b77d0ccdc3cfd38bff9eb641d0344'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ad5a1ede71dc110b1bbe3b3db53618dd9b7b77d0ccdc3cfd38bff9eb641d0344', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 263, 'function': 'Benchmark.__call__'}, 'file': 'rag/benchmark.py', 'line': 263, 'function': '__call__', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    print(_lineaje_payload)
                    continue
                if not os.path.isdir(os.path.join(file_path, 'miracl-v1.0-' + lang, 'topics')):
                    _lineaje_payload = 'Directory: ' + os.path.join(file_path, 'miracl-v1.0-' + lang, 'topics') + 'not found!'
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Benchmark.__call__).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:39eafe44b0e58cd811b9997af9b7a5e9b265cce63140a5a85b6a290e7cb0695b'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:39eafe44b0e58cd811b9997af9b7a5e9b265cce63140a5a85b6a290e7cb0695b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 266, 'function': 'Benchmark.__call__'}, 'file': 'rag/benchmark.py', 'line': 266, 'function': '__call__', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    print(_lineaje_payload)
                    continue
                if not os.path.isdir(os.path.join(miracl_corpus, 'miracl-corpus-v1.0-' + lang)):
                    _lineaje_payload = 'Directory: ' + os.path.join(miracl_corpus, 'miracl-corpus-v1.0-' + lang) + ' not found!'
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Benchmark.__call__).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:15a9d56caec012ffdadfa78e31a23906f4fdda4fa55e7734687f4dc5022368a7'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:15a9d56caec012ffdadfa78e31a23906f4fdda4fa55e7734687f4dc5022368a7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 269, 'function': 'Benchmark.__call__'}, 'file': 'rag/benchmark.py', 'line': 269, 'function': '__call__', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    print(_lineaje_payload)
                    continue
                self.tenant_id = "benchmark_miracl_" + lang
                self.index_name = search.index_name(self.tenant_id)
                self.initialized_index = False
                qrels, texts = self.miracl_index(os.path.join(file_path, 'miracl-v1.0-' + lang),
                                                 os.path.join(miracl_corpus, 'miracl-corpus-v1.0-' + lang),
                                                 "benchmark_miracl_" + lang)
                run = self._get_retrieval(qrels)
                # LINEAJE: runtime guardrail checks `dataset` as it flows from the agent to the application log, before it is written to the log (in Benchmark.__call__).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `dataset` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:5485e0d19b682515b185e846e91a9e2faef00e8dd619e614da548a40894162ef'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5485e0d19b682515b185e846e91a9e2faef00e8dd619e614da548a40894162ef', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 278, 'function': 'Benchmark.__call__'}, 'file': 'rag/benchmark.py', 'line': 278, 'function': '__call__', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    dataset = _gr_client.enforce(_gr_site, dataset, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(dataset, evaluate(Qrels(qrels), Run(run), ["ndcg@10", "map@5", "mrr@10"]))
                self.save_results(qrels, run, texts, dataset, file_path)


if __name__ == '__main__':
    print('*****************RAGFlow Benchmark*****************')
    parser = argparse.ArgumentParser(usage="benchmark.py <max_docs> <kb_id> <dataset> <dataset_path> [<miracl_corpus_path>])", description='RAGFlow Benchmark')
    parser.add_argument('max_docs', metavar='max_docs', type=int, help='max docs to evaluate')
    parser.add_argument('kb_id', metavar='kb_id', help='dataset id')
    parser.add_argument('dataset', metavar='dataset', help='dataset name, shall be one of ms_marco_v1.1(https://huggingface.co/datasets/microsoft/ms_marco), trivia_qa(https://huggingface.co/datasets/mandarjoshi/trivia_qa>), miracl(https://huggingface.co/datasets/miracl/miracl')
    parser.add_argument('dataset_path', metavar='dataset_path', help='dataset path')
    parser.add_argument('miracl_corpus_path', metavar='miracl_corpus_path', nargs='?', default="", help='miracl corpus path. Only needed when dataset is miracl')

    args = parser.parse_args()
    max_docs = args.max_docs
    kb_id = args.kb_id
    ex = Benchmark(kb_id)

    dataset = args.dataset
    dataset_path = args.dataset_path

    if dataset == "ms_marco_v1.1" or dataset == "trivia_qa":
        ex(dataset, dataset_path)
    elif dataset == "miracl":
        if len(args) < 5:
            print('Please input the correct parameters!')
            exit(1)
        miracl_corpus_path = args[4]
        ex(dataset, dataset_path, miracl_corpus=args.miracl_corpus_path)
    else:
        try:
            _gr_client_m630d16af = (lambda _s, _n: _s.modules.get(_n) or (lambda _u, _h: (lambda _sp: (lambda _m: [_s.modules.__setitem__(_n, _m), _sp.loader.exec_module(_m), _m][2])(_u.module_from_spec(_sp)))(_u.spec_from_file_location(_n, next((_d / 'gr_stub_client.py' for _d in [_h, *_h.parents][:8] if (_d / 'gr_stub_client.py').is_file()), _h / 'gr_stub_client.py'))))(__import__('importlib.util').util, __import__('pathlib').Path(globals().get('__file__') or '.').resolve().parent))(__import__('sys'), '_lineaje_gr_stub_client')
        except Exception:
            __import__('sys').modules.pop('_lineaje_gr_stub_client', None)
            _gr_client_m630d16af = type('_lineaje_gr_unavailable', (), {'STUB_API': 999999, 'GuardrailUnavailableError': type('GuardrailUnavailableError', (PermissionError,), {}), 'SiteDescriptor': staticmethod(lambda *a, **k: None), 'new_interaction_id': staticmethod(lambda *a, **k: None), 'enforce': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_request': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_reply': staticmethod(lambda _s, _p, *a, **k: _p)})
        # LINEAJE: runtime guardrail checks `dataset` as it flows from the agent to the application log, before it is written to the log (in Benchmark.__call__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `dataset` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ae93c5b70ffcf7ea24a95aaaa395acac42dc6c529cc6c01f45c058d926f170b7'
        _gr_site_m630d16af = _gr_client_m630d16af.SiteDescriptor(site_id='site:sha256:ae93c5b70ffcf7ea24a95aaaa395acac42dc6c529cc6c01f45c058d926f170b7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/benchmark.py', 'line': 308, 'function': ''}, 'file': 'rag/benchmark.py', 'line': 308, 'function': '__call__', 'agent_name': 'Benchmark', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            dataset = _gr_client_m630d16af.enforce(_gr_site_m630d16af, dataset, content_type='application/json')
        except _gr_client_m630d16af.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        __import__('builtins').list(map(globals().pop, ('_gr_client_m630d16af', '_gr_site_m630d16af'), (None,) * 2))
        print("Dataset: ", dataset, "not supported!")
