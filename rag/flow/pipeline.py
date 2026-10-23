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
import asyncio
import datetime
import json
import logging
import random
from timeit import default_timer as timer
from agent.canvas import Graph
from api.db.services.document_service import DocumentService
from api.db.services.task_service import has_canceled, TaskService, CANVAS_DEBUG_DOC_ID
from rag.utils.redis_conn import REDIS_CONN


class Pipeline(Graph):
    def __init__(self, dsl: str|dict, tenant_id=None, doc_id=None, task_id=None, flow_id=None):
        if isinstance(dsl, dict):
            # LINEAJE: runtime guardrail checks `dsl` as it flows from the agent to an external endpoint, before it leaves the application (in Pipeline.__init__).
            #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `dsl` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:877fefb868cfb8cc3bd1f1ca6cc353ef665f792935a3e14fcd42db9d9c8c9c0f'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:877fefb868cfb8cc3bd1f1ca6cc353ef665f792935a3e14fcd42db9d9c8c9c0f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/pipeline.py', 'line': 31, 'function': 'Pipeline.__init__'}, 'file': 'rag/flow/pipeline.py', 'line': 31, 'function': '__init__', 'agent_name': 'Pipeline', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                dsl = _gr_client.enforce(_gr_site, dsl, content_type='application/json', variable_name='dsl', source_file=__file__, before_line=31)
            except _gr_client.GuardrailUnavailableError:
                pass
            dsl = json.dumps(dsl, ensure_ascii=False)
        super().__init__(dsl, tenant_id, task_id)
        if doc_id == CANVAS_DEBUG_DOC_ID:
            doc_id = None
        self._doc_id = doc_id
        self._flow_id = flow_id
        self._kb_id = None
        if self._doc_id:
            self._kb_id = DocumentService.get_knowledgebase_id(doc_id)
            if not self._kb_id:
                self._doc_id = None

    def callback(self, component_name: str, progress: float | int | None = None, message: str = "") -> None:
        from common.exceptions import TaskCanceledException
        log_key = f"{self._flow_id}-{self.task_id}-logs"
        timestamp = timer()
        if has_canceled(self.task_id):
            progress = -1
            message += "[CANCEL]"
        try:
            bin = REDIS_CONN.get(log_key)
            obj = json.loads(bin.encode("utf-8"))
            if obj:
                if obj[-1]["component_id"] == component_name:
                    obj[-1]["trace"].append(
                        {
                            "progress": progress,
                            "message": message,
                            "datetime": datetime.datetime.now().strftime("%H:%M:%S"),
                            "timestamp": timestamp,
                            "elapsed_time": timestamp - obj[-1]["trace"][-1]["timestamp"],
                        }
                    )
                else:
                    obj.append(
                        {
                            "component_id": component_name,
                            "trace": [{"progress": progress, "message": message, "datetime": datetime.datetime.now().strftime("%H:%M:%S"), "timestamp": timestamp, "elapsed_time": 0}],
                        }
                    )
            else:
                obj = [
                    {
                        "component_id": component_name,
                        "trace": [{"progress": progress, "message": message, "datetime": datetime.datetime.now().strftime("%H:%M:%S"), "timestamp": timestamp, "elapsed_time": 0}],
                    }
                ]
            if component_name != "END" and self._doc_id and self.task_id:
                percentage = 1.0 / len(self.components.items())
                finished = 0.0
                for o in obj:
                    for t in o["trace"]:
                        if t["progress"] < 0:
                            finished = -1
                            break
                    if finished < 0:
                        break
                    finished += o["trace"][-1]["progress"] * percentage

                msg = ""
                if len(obj[-1]["trace"]) == 1:
                    msg += f"\n-------------------------------------\n[{self.get_component_name(o['component_id'])}]:\n"
                t = obj[-1]["trace"][-1]
                msg += "%s: %s\n" % (t["datetime"], t["message"])
                TaskService.update_progress(self.task_id, {"progress": finished, "progress_msg": msg})
            elif component_name == "END" and not self._doc_id:
                obj[-1]["trace"][-1]["dsl"] = json.loads(str(self))
            REDIS_CONN.set_obj(log_key, obj, 60 * 30)

        except Exception as e:
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in Pipeline.callback).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d41bb7a4406875476139ddba293d39f0a6c2eadc2eb17c18608cef7052ec4f0e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d41bb7a4406875476139ddba293d39f0a6c2eadc2eb17c18608cef7052ec4f0e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/pipeline.py', 'line': 101, 'function': 'Pipeline.callback'}, 'file': 'rag/flow/pipeline.py', 'line': 101, 'function': 'callback', 'agent_name': 'Pipeline', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                e = _gr_client.enforce(_gr_site, e, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)

        if has_canceled(self.task_id):
            raise TaskCanceledException(message)

    def fetch_logs(self):
        log_key = f"{self._flow_id}-{self.task_id}-logs"
        try:
            bin = REDIS_CONN.get(log_key)
            if bin:
                return json.loads(bin.encode("utf-8"))
        except Exception as e:
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in Pipeline.fetch_logs).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0a07d6a4eb448e865feb1eed699dfe4a658a6251025b619d9f08daeceff21a8e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0a07d6a4eb448e865feb1eed699dfe4a658a6251025b619d9f08daeceff21a8e', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/pipeline.py', 'line': 113, 'function': 'Pipeline.fetch_logs'}, 'file': 'rag/flow/pipeline.py', 'line': 113, 'function': 'fetch_logs', 'agent_name': 'Pipeline', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                e = _gr_client.enforce(_gr_site, e, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)
        return []


    async def run(self, **kwargs):
        log_key = f"{self._flow_id}-{self.task_id}-logs"
        try:
            REDIS_CONN.set_obj(log_key, [], 60 * 10)
        except Exception as e:
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in Pipeline.run).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:457dea64017a3c8ee1aae206bc6619cd4541e98441407d3398c44e1afc9bd704'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:457dea64017a3c8ee1aae206bc6619cd4541e98441407d3398c44e1afc9bd704', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/pipeline.py', 'line': 122, 'function': 'Pipeline.run'}, 'file': 'rag/flow/pipeline.py', 'line': 122, 'function': 'run', 'agent_name': 'Pipeline', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                e = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, e, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)
        self.error = ""
        if not self.path:
            self.path.append("File")
            cpn_obj = self.get_component_obj(self.path[0])
            await cpn_obj.invoke(**kwargs)
            if cpn_obj.error():
                self.error = "[ERROR]" + cpn_obj.error()
                self.callback(cpn_obj.component_name, -1, self.error)

        if self._doc_id:
            TaskService.update_progress(self.task_id, {
                "progress": random.randint(0, 5) / 100.0,
                "progress_msg": "Start the pipeline...",
                "begin_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

        idx = len(self.path) - 1
        cpn_obj = self.get_component_obj(self.path[idx])
        idx += 1
        self.path.extend(cpn_obj.get_downstream())

        while idx < len(self.path) and not self.error:
            last_cpn = self.get_component_obj(self.path[idx - 1])
            cpn_obj = self.get_component_obj(self.path[idx])

            async def invoke():
                nonlocal last_cpn, cpn_obj
                await cpn_obj.invoke(**last_cpn.output())
                #if inspect.iscoroutinefunction(cpn_obj.invoke):
                #    await cpn_obj.invoke(**last_cpn.output())
                #else:
                #    cpn_obj.invoke(**last_cpn.output())

            tasks = []
            tasks.append(asyncio.create_task(invoke()))
            await asyncio.gather(*tasks)

            if cpn_obj.error():
                self.error = "[ERROR]" + cpn_obj.error()
                self.callback(cpn_obj._id, -1, self.error)
                break
            idx += 1
            self.path.extend(cpn_obj.get_downstream())

        _lineaje_payload = self.get_component_obj(self.path[-1]).output()
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to an external endpoint, before it leaves the application (in Pipeline.run).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `_lineaje_payload` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:be05cdfbf62e6bdfa73814a890f9ab86c7553d0bc7fdacf4956e27b5156b5767'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:be05cdfbf62e6bdfa73814a890f9ab86c7553d0bc7fdacf4956e27b5156b5767', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/pipeline.py', 'line': 166, 'function': 'Pipeline.run'}, 'file': 'rag/flow/pipeline.py', 'line': 166, 'function': 'run', 'agent_name': 'Pipeline', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=166))
        except _gr_client.GuardrailUnavailableError:
            pass
        self.callback("END", 1 if not self.error else -1, json.dumps(_lineaje_payload, ensure_ascii=False))

        if not self.error:
            return self.get_component_obj(self.path[-1]).output()

        TaskService.update_progress(self.task_id, {
            "progress": -1,
            "progress_msg": f"[ERROR]: {self.error}"})

        return {}
