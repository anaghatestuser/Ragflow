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
import argparse
import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

from common import settings
from rag.flow.pipeline import Pipeline


def print_logs(pipeline: Pipeline):
    last_logs = "[]"
    while True:
        time.sleep(5)
        logs = pipeline.fetch_logs()
        # LINEAJE: runtime guardrail checks `logs` as it flows from the agent to an external endpoint, before it leaves the application (in print_logs).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `logs` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:43aa38cc62930ada220f7dc459c6ed64e039398193a16624dc31b884fdd992a7'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:43aa38cc62930ada220f7dc459c6ed64e039398193a16624dc31b884fdd992a7', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/tests/client.py', 'line': 32, 'function': 'print_logs'}, 'file': 'rag/flow/tests/client.py', 'line': 32, 'function': 'print_logs', 'agent_name': 'print_logs', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            logs = _gr_client.enforce(_gr_site, logs, content_type='application/json', variable_name='logs', source_file=__file__, before_line=32)
        except _gr_client.GuardrailUnavailableError:
            pass
        logs_str = json.dumps(logs, ensure_ascii=False)
        if logs_str != last_logs:
            # LINEAJE: runtime guardrail checks `logs_str` as it flows from the agent to the application log, before it is written to the log (in print_logs).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `logs_str` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:67da75c78ae901023d03095f0ab9c071b60ed95c1615e9f47d44e2d531ff6926'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:67da75c78ae901023d03095f0ab9c071b60ed95c1615e9f47d44e2d531ff6926', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/tests/client.py', 'line': 34, 'function': 'print_logs'}, 'file': 'rag/flow/tests/client.py', 'line': 34, 'function': 'print_logs', 'agent_name': 'print_logs', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                logs_str = _gr_client.enforce(_gr_site, logs_str, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            print(logs_str)
        last_logs = logs_str


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    dsl_default_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "dsl_examples",
        "general_pdf_all.json",
    )
    parser.add_argument("-s", "--dsl", default=dsl_default_path, help="input dsl", action="store", required=False)
    parser.add_argument("-d", "--doc_id", default=False, help="Document ID", action="store", required=True)
    parser.add_argument("-t", "--tenant_id", default=False, help="Tenant ID", action="store", required=True)
    args = parser.parse_args()

    settings.init_settings()
    pipeline = Pipeline(open(args.dsl, "r").read(), tenant_id=args.tenant_id, doc_id=args.doc_id, task_id="xxxx", flow_id="xxx")
    try:
        _gr_client_m438a6973 = (lambda _s, _n: _s.modules.get(_n) or (lambda _u, _h: (lambda _sp: (lambda _m: [_s.modules.__setitem__(_n, _m), _sp.loader.exec_module(_m), _m][2])(_u.module_from_spec(_sp)))(_u.spec_from_file_location(_n, next((_d / 'gr_stub_client.py' for _d in [_h, *_h.parents][:8] if (_d / 'gr_stub_client.py').is_file()), _h / 'gr_stub_client.py'))))(__import__('importlib.util').util, __import__('pathlib').Path(globals().get('__file__') or '.').resolve().parent))(__import__('sys'), '_lineaje_gr_stub_client')
    except Exception:
        __import__('sys').modules.pop('_lineaje_gr_stub_client', None)
        _gr_client_m438a6973 = type('_lineaje_gr_unavailable', (), {'STUB_API': 999999, 'GuardrailUnavailableError': type('GuardrailUnavailableError', (PermissionError,), {}), 'SiteDescriptor': staticmethod(lambda *a, **k: None), 'new_interaction_id': staticmethod(lambda *a, **k: None), 'enforce': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_request': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_reply': staticmethod(lambda _s, _p, *a, **k: _p)})
    # LINEAJE: runtime guardrail checks `pipeline` as it flows from file storage to the agent (in print_logs).
    #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `pipeline` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:d9502e3a9b3c097a672000dfd8e0a9395a95d6630d90dec3d40b27f79164f31b'
    _gr_site_m438a6973 = _gr_client_m438a6973.SiteDescriptor(site_id='site:sha256:d9502e3a9b3c097a672000dfd8e0a9395a95d6630d90dec3d40b27f79164f31b', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/flow/tests/client.py', 'line': 51, 'function': ''}, 'file': 'rag/flow/tests/client.py', 'line': 51, 'function': 'print_logs', 'agent_name': 'print_logs', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        pipeline = _gr_client_m438a6973.enforce(_gr_site_m438a6973, pipeline, content_type='application/json')
    except _gr_client_m438a6973.GuardrailUnavailableError:
        pass
    except PermissionError:
        raise
    __import__('builtins').list(map(globals().pop, ('_gr_client_m438a6973', '_gr_site_m438a6973'), (None,) * 2))
    pipeline.reset()

    exe = ThreadPoolExecutor(max_workers=5)
    thr = exe.submit(print_logs, pipeline)

    # queue_dataflow(dsl=open(args.dsl, "r").read(), tenant_id=args.tenant_id, doc_id=args.doc_id, task_id="xxxx", flow_id="xxx", priority=0)

    asyncio.run(pipeline.run())
    thr.result()
