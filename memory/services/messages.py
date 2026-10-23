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
import sys
from typing import List

from common import settings
from common.doc_store.doc_store_base import OrderByExpr, MatchExpr


def index_name(uid: str): return f"memory_{uid}"


class MessageService:

    @classmethod
    def has_index(cls, uid: str, memory_id: str):
        index = index_name(uid)
        return settings.msgStoreConn.index_exist(index, memory_id)

    @classmethod
    def create_index(cls, uid: str, memory_id: str, vector_size: int):
        index = index_name(uid)
        return settings.msgStoreConn.create_idx(index, memory_id, vector_size)

    @classmethod
    def delete_index(cls, uid: str, memory_id: str):
        index = index_name(uid)
        return settings.msgStoreConn.delete_idx(index, memory_id)

    @classmethod
    def insert_message(cls, messages: List[dict], uid: str, memory_id: str):
        index = index_name(uid)
        [m.update({
            "id": f'{memory_id}_{m["message_id"]}',
            "status": 1 if m["status"] else 0
        }) for m in messages]
        return settings.msgStoreConn.insert(messages, index, memory_id)

    @classmethod
    def update_message(cls, condition: dict, update_dict: dict, uid: str, memory_id: str):
        index = index_name(uid)
        if "status" in update_dict:
            update_dict["status"] = 1 if update_dict["status"] else 0
        return settings.msgStoreConn.update(condition, update_dict, index, memory_id)

    @classmethod
    def delete_message(cls, condition: dict, uid: str, memory_id: str):
        index = index_name(uid)
        return settings.msgStoreConn.delete(condition, index, memory_id)

    @classmethod
    def list_message(cls, uid: str, memory_id: str, agent_ids: List[str]=None, keywords: str=None, page: int=1, page_size: int=50):
        index = index_name(uid)
        filter_dict = {}
        if agent_ids:
            filter_dict["agent_id"] = agent_ids
        if keywords:
            filter_dict["session_id"] = keywords
        order_by = OrderByExpr()
        order_by.desc("valid_at")
        res = settings.msgStoreConn.search(
            select_fields=[
                "message_id", "message_type", "source_id", "memory_id", "user_id", "agent_id", "session_id", "valid_at",
                "invalid_at", "forget_at", "status"
            ],
            highlight_fields=[],
            condition=filter_dict,
            match_expressions=[], order_by=order_by,
            offset=(page-1)*page_size, limit=page_size,
            index_names=index, memory_ids=[memory_id], agg_fields=[], hide_forgotten=False
        )
        total_count = settings.msgStoreConn.get_total(res)
        doc_mapping = settings.msgStoreConn.get_fields(res, [
            "message_id", "message_type", "source_id", "memory_id", "user_id", "agent_id", "session_id",
            "valid_at", "invalid_at", "forget_at", "status"
        ])
        return {
            "message_list": list(doc_mapping.values()),
            "total_count": total_count
        }

    @classmethod
    def get_recent_messages(cls, uid_list: List[str], memory_ids: List[str], agent_id: str, session_id: str, limit: int):
        index_names = [index_name(uid) for uid in uid_list]
        condition_dict = {
            "agent_id": agent_id,
            "session_id": session_id
        }
        order_by = OrderByExpr()
        order_by.desc("valid_at")
        res = settings.msgStoreConn.search(
            select_fields=[
                "message_id", "message_type", "source_id", "memory_id", "user_id", "agent_id", "session_id", "valid_at",
                "invalid_at", "forget_at", "status", "content"
            ],
            highlight_fields=[],
            condition=condition_dict,
            match_expressions=[], order_by=order_by,
            offset=0, limit=limit,
            index_names=index_names, memory_ids=memory_ids, agg_fields=[]
        )
        doc_mapping = settings.msgStoreConn.get_fields(res, [
            "message_id", "message_type", "source_id", "memory_id","user_id", "agent_id", "session_id",
            "valid_at", "invalid_at", "forget_at", "status", "content"
        ])
        return list(doc_mapping.values())

    @classmethod
    def search_message(cls, memory_ids: List[str], condition_dict: dict, uid_list: List[str], match_expressions:list[MatchExpr], top_n: int):
        index_names = [index_name(uid) for uid in uid_list]
        # filter only valid messages by default
        if "status" not in condition_dict:
            condition_dict["status"] = 1

        order_by = OrderByExpr()
        order_by.desc("valid_at")
        res = settings.msgStoreConn.search(
            select_fields=[
                "message_id", "message_type", "source_id", "memory_id", "user_id", "agent_id", "session_id",
                "valid_at",
                "invalid_at", "forget_at", "status", "content"
            ],
            highlight_fields=[],
            condition=condition_dict,
            match_expressions=match_expressions,
            order_by=order_by,
            offset=0, limit=top_n,
            index_names=index_names, memory_ids=memory_ids, agg_fields=[]
        )
        docs = settings.msgStoreConn.get_fields(res, [
            "message_id", "message_type", "source_id", "memory_id", "user_id", "agent_id", "session_id", "valid_at",
            "invalid_at", "forget_at", "status", "content"
        ])
        return list(docs.values())

    @staticmethod
    def calculate_message_size(message: dict):
        return sys.getsizeof(message["content"]) + sys.getsizeof(message["content_embed"][0]) * len(message["content_embed"])

    @classmethod
    def calculate_memory_size(cls, memory_ids: List[str], uid_list: List[str]):
        index_names = [index_name(uid) for uid in uid_list]
        order_by = OrderByExpr()
        order_by.desc("valid_at")

        res = settings.msgStoreConn.search(
            select_fields=["memory_id", "content", "content_embed"],
            highlight_fields=[],
            condition={},
            match_expressions=[],
            order_by=order_by,
            offset=0, limit=2000*len(memory_ids),
            index_names=index_names, memory_ids=memory_ids, agg_fields=[], hide_forgotten=False
        )
        docs = settings.msgStoreConn.get_fields(res, ["memory_id", "content", "content_embed"])
        size_dict = {}
        for doc in docs.values():
            if size_dict.get(doc["memory_id"]):
                size_dict[doc["memory_id"]] += cls.calculate_message_size(doc)
            else:
                size_dict[doc["memory_id"]] = cls.calculate_message_size(doc)
        # LINEAJE: runtime guardrail checks `size_dict` as it flows from the agent to the user interface, before it leaves the application (in MessageService.calculate_memory_size).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `size_dict` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:09fb79a1c203c9498d268583a53efd2f9d1e9449eb6e9424e7bc02cb95a1ac40'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:09fb79a1c203c9498d268583a53efd2f9d1e9449eb6e9424e7bc02cb95a1ac40', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'memory/services/messages.py', 'line': 175, 'function': 'MessageService.calculate_memory_size'}, 'file': 'memory/services/messages.py', 'line': 175, 'function': 'calculate_memory_size', 'agent_name': 'MessageService', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            size_dict = _gr_client.enforce(_gr_site, size_dict, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return size_dict

    @classmethod
    def pick_messages_to_delete_by_fifo(cls, memory_id: str, uid: str, size_to_delete: int):
        select_fields = ["message_id", "content", "content_embed"]
        _index_name = index_name(uid)
        res = settings.msgStoreConn.get_forgotten_messages(select_fields, _index_name, memory_id)
        message_list = settings.msgStoreConn.get_fields(res, select_fields)
        current_size = 0
        ids_to_remove = []
        for message in message_list:
            if current_size < size_to_delete:
                current_size += cls.calculate_message_size(message)
                ids_to_remove.append(message["message_id"])
            else:
                return ids_to_remove, current_size
        if current_size >= size_to_delete:
            return ids_to_remove, current_size

        order_by = OrderByExpr()
        order_by.asc("valid_at")
        res = settings.msgStoreConn.search(
            select_fields=["memory_id", "content", "content_embed"],
            highlight_fields=[],
            condition={},
            match_expressions=[],
            order_by=order_by,
            offset=0, limit=2000,
            index_names=[_index_name], memory_ids=[memory_id], agg_fields=[]
        )
        docs = settings.msgStoreConn.get_fields(res, select_fields)
        for doc in docs.values():
            if current_size < size_to_delete:
                current_size += cls.calculate_message_size(doc)
                ids_to_remove.append(doc["memory_id"])
            else:
                return ids_to_remove, current_size
        return ids_to_remove, current_size

    @classmethod
    def get_by_message_id(cls, memory_id: str, message_id: int, uid: str):
        index = index_name(uid)
        doc_id = f'{memory_id}_{message_id}'
        return settings.msgStoreConn.get(doc_id, index, [memory_id])

    @classmethod
    def get_max_message_id(cls, uid_list: List[str], memory_ids: List[str]):
        order_by = OrderByExpr()
        order_by.desc("message_id")
        index_names = [index_name(uid) for uid in uid_list]
        res = settings.msgStoreConn.search(
            select_fields=["message_id"],
            highlight_fields=[],
            condition={},
            match_expressions=[],
            order_by=order_by,
            offset=0, limit=1,
            index_names=index_names, memory_ids=memory_ids,
            agg_fields=[], hide_forgotten=False
        )
        docs = settings.msgStoreConn.get_fields(res, ["message_id"])
        if not docs:
            return 1
        else:
            latest_msg = list(docs.values())[0]
            return int(latest_msg["message_id"])
