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
from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np

DEFAULT_MATCH_VECTOR_TOPN = 10
DEFAULT_MATCH_SPARSE_TOPN = 10
VEC = list | np.ndarray

@dataclass
class SparseVector:
    indices: list[int]
    values: list[float] | list[int] | None = None

    def __post_init__(self):
        assert (self.values is None) or (len(self.indices) == len(self.values))

    def to_dict_old(self):
        d = {"indices": self.indices}
        if self.values is not None:
            d["values"] = self.values
        # LINEAJE: runtime guardrail checks `d` as it flows from the agent to the user interface, before it leaves the application (in SparseVector.to_dict_old).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `d` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:30a0f8397d2c23f129571458be37afc32fd716fee01628e91841278aa5852332'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:30a0f8397d2c23f129571458be37afc32fd716fee01628e91841278aa5852332', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/doc_store_base.py', 'line': 36, 'function': 'SparseVector.to_dict_old'}, 'file': 'common/doc_store/doc_store_base.py', 'line': 36, 'function': 'to_dict_old', 'agent_name': 'SparseVector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            d = _gr_client.enforce(_gr_site, d, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return d

    def to_dict(self):
        if self.values is None:
            raise ValueError("SparseVector.values is None")
        result = {}
        for i, v in zip(self.indices, self.values):
            result[str(i)] = v
        # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in SparseVector.to_dict).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:83ffcdc5bea576225c3d3c19b697841b7ce9bf5b4bbbb5985f351d60c54431c2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:83ffcdc5bea576225c3d3c19b697841b7ce9bf5b4bbbb5985f351d60c54431c2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/doc_store/doc_store_base.py', 'line': 44, 'function': 'SparseVector.to_dict'}, 'file': 'common/doc_store/doc_store_base.py', 'line': 44, 'function': 'to_dict', 'agent_name': 'SparseVector', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return result

    @staticmethod
    def from_dict(d):
        return SparseVector(d["indices"], d.get("values"))

    def __str__(self):
        return f"SparseVector(indices={self.indices}{'' if self.values is None else f', values={self.values}'})"

    def __repr__(self):
        return str(self)

class MatchTextExpr:
    def __init__(
        self,
        fields: list[str],
        matching_text: str,
        topn: int,
        extra_options: dict | None = None,
    ):
        self.fields = fields
        self.matching_text = matching_text
        self.topn = topn
        self.extra_options = extra_options


class MatchDenseExpr:
    def __init__(
        self,
        vector_column_name: str,
        embedding_data: VEC,
        embedding_data_type: str,
        distance_type: str,
        topn: int = DEFAULT_MATCH_VECTOR_TOPN,
        extra_options: dict | None = None,
    ):
        self.vector_column_name = vector_column_name
        self.embedding_data = embedding_data
        self.embedding_data_type = embedding_data_type
        self.distance_type = distance_type
        self.topn = topn
        self.extra_options = extra_options


class MatchSparseExpr:
    def __init__(
        self,
        vector_column_name: str,
        sparse_data: SparseVector | dict,
        distance_type: str,
        topn: int,
        opt_params: dict | None = None,
    ):
        self.vector_column_name = vector_column_name
        self.sparse_data = sparse_data
        self.distance_type = distance_type
        self.topn = topn
        self.opt_params = opt_params


class MatchTensorExpr:
    def __init__(
        self,
        column_name: str,
        query_data: VEC,
        query_data_type: str,
        topn: int,
        extra_option: dict | None = None,
    ):
        self.column_name = column_name
        self.query_data = query_data
        self.query_data_type = query_data_type
        self.topn = topn
        self.extra_option = extra_option


class FusionExpr:
    def __init__(self, method: str, topn: int, fusion_params: dict | None = None):
        self.method = method
        self.topn = topn
        self.fusion_params = fusion_params


MatchExpr = MatchTextExpr | MatchDenseExpr | MatchSparseExpr | MatchTensorExpr | FusionExpr


class OrderByExpr:
    def __init__(self):
        self.fields = list()
    def asc(self, field: str):
        self.fields.append((field, 0))
        return self
    def desc(self, field: str):
        self.fields.append((field, 1))
        return self
    def fields(self):
        return self.fields


class DocStoreConnection(ABC):
    """
    Database operations
    """

    @abstractmethod
    def db_type(self) -> str:
        """
        Return the type of the database.
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def health(self) -> dict:
        """
        Return the health status of the database.
        """
        raise NotImplementedError("Not implemented")

    """
    Table operations
    """

    @abstractmethod
    def create_idx(self, index_name: str, dataset_id: str, vector_size: int):
        """
        Create an index with given name
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def delete_idx(self, index_name: str, dataset_id: str):
        """
        Delete an index with given name
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def index_exist(self, index_name: str, dataset_id: str) -> bool:
        """
        Check if an index with given name exists
        """
        raise NotImplementedError("Not implemented")

    """
    CRUD operations
    """

    @abstractmethod
    def search(
        self, select_fields: list[str],
            highlight_fields: list[str],
            condition: dict,
            match_expressions: list[MatchExpr],
            order_by: OrderByExpr,
            offset: int,
            limit: int,
            index_names: str|list[str],
            dataset_ids: list[str],
            agg_fields: list[str] | None = None,
            rank_feature: dict | None = None
    ):
        """
        Search with given conjunctive equivalent filtering condition and return all fields of matched documents
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def get(self, data_id: str, index_name: str, dataset_ids: list[str]) -> dict | None:
        """
        Get single chunk with given id
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def insert(self, rows: list[dict], index_name: str, dataset_id: str = None) -> list[str]:
        """
        Update or insert a bulk of rows
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def update(self, condition: dict, new_value: dict, index_name: str, dataset_id: str) -> bool:
        """
        Update rows with given conjunctive equivalent filtering condition
        """
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def delete(self, condition: dict, index_name: str, dataset_id: str) -> int:
        """
        Delete rows with given conjunctive equivalent filtering condition
        """
        raise NotImplementedError("Not implemented")

    """
    Helper functions for search result
    """

    @abstractmethod
    def get_total(self, res):
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def get_doc_ids(self, res):
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def get_fields(self, res, fields: list[str]) -> dict[str, dict]:
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def get_highlight(self, res, keywords: list[str], field_name: str):
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def get_aggregation(self, res, field_name: str):
        raise NotImplementedError("Not implemented")

    """
    SQL
    """
    @abstractmethod
    def sql(self, sql: str, fetch_size: int, format: str):
        """
        Run the sql generated by text-to-sql
        """
        raise NotImplementedError("Not implemented")
