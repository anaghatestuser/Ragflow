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
import os
from agent.canvas import Canvas
from common import settings

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    dsl_default_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "dsl_examples",
        "retrieval_and_generate.json",
    )
    parser.add_argument('-s', '--dsl', default=dsl_default_path, help="input dsl", action='store', required=True)
    parser.add_argument('-t', '--tenant_id', default=False, help="Tenant ID", action='store', required=True)
    parser.add_argument('-m', '--stream', default=False, help="Stream output", action='store_true', required=False)
    args = parser.parse_args()

    settings.init_settings()
    canvas = Canvas(open(args.dsl, "r").read(), args.tenant_id)
    try:
        _gr_client_mcedaf3c8 = (lambda _s, _n: _s.modules.get(_n) or (lambda _u, _h: (lambda _sp: (lambda _m: [_s.modules.__setitem__(_n, _m), _sp.loader.exec_module(_m), _m][2])(_u.module_from_spec(_sp)))(_u.spec_from_file_location(_n, next((_d / 'gr_stub_client.py' for _d in [_h, *_h.parents][:8] if (_d / 'gr_stub_client.py').is_file()), _h / 'gr_stub_client.py'))))(__import__('importlib.util').util, __import__('pathlib').Path(globals().get('__file__') or '.').resolve().parent))(__import__('sys'), '_lineaje_gr_stub_client')
    except Exception:
        __import__('sys').modules.pop('_lineaje_gr_stub_client', None)
        _gr_client_mcedaf3c8 = type('_lineaje_gr_unavailable', (), {'STUB_API': 999999, 'GuardrailUnavailableError': type('GuardrailUnavailableError', (PermissionError,), {}), 'SiteDescriptor': staticmethod(lambda *a, **k: None), 'new_interaction_id': staticmethod(lambda *a, **k: None), 'enforce': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_request': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_reply': staticmethod(lambda _s, _p, *a, **k: _p)})
    # LINEAJE: runtime guardrail checks `canvas` as it flows from file storage to the agent.
    #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `canvas` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:c2b92e38c383a84ebf8b513912f5dd7b64a0a4a4d718165f74a8f09489933cd6'
    _gr_site_mcedaf3c8 = _gr_client_mcedaf3c8.SiteDescriptor(site_id='site:sha256:c2b92e38c383a84ebf8b513912f5dd7b64a0a4a4d718165f74a8f09489933cd6', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/test/client.py', 'line': 34, 'function': ''}, 'file': 'agent/test/client.py', 'line': 34, 'not_on_graph': True})
    try:
        canvas = _gr_client_mcedaf3c8.enforce(_gr_site_mcedaf3c8, canvas, content_type='application/json')
    except _gr_client_mcedaf3c8.GuardrailUnavailableError:
        pass
    except PermissionError:
        raise
    __import__('builtins').list(map(globals().pop, ('_gr_client_mcedaf3c8', '_gr_site_mcedaf3c8'), (None,) * 2))
    if canvas.get_prologue():
        print(f"==================== Bot =====================\n>    {canvas.get_prologue()}", end='')
    query = ""
    while True:
        canvas.reset(True)
        query = input("\n==================== User =====================\n> ")
        ans = canvas.run(query=query)
        print("==================== Bot =====================\n>    ", end='')
        for ans in canvas.run(query=query):
            try:
                _gr_client_mcedaf3c8 = (lambda _s, _n: _s.modules.get(_n) or (lambda _u, _h: (lambda _sp: (lambda _m: [_s.modules.__setitem__(_n, _m), _sp.loader.exec_module(_m), _m][2])(_u.module_from_spec(_sp)))(_u.spec_from_file_location(_n, next((_d / 'gr_stub_client.py' for _d in [_h, *_h.parents][:8] if (_d / 'gr_stub_client.py').is_file()), _h / 'gr_stub_client.py'))))(__import__('importlib.util').util, __import__('pathlib').Path(globals().get('__file__') or '.').resolve().parent))(__import__('sys'), '_lineaje_gr_stub_client')
            except Exception:
                __import__('sys').modules.pop('_lineaje_gr_stub_client', None)
                _gr_client_mcedaf3c8 = type('_lineaje_gr_unavailable', (), {'STUB_API': 999999, 'GuardrailUnavailableError': type('GuardrailUnavailableError', (PermissionError,), {}), 'SiteDescriptor': staticmethod(lambda *a, **k: None), 'new_interaction_id': staticmethod(lambda *a, **k: None), 'enforce': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_request': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_reply': staticmethod(lambda _s, _p, *a, **k: _p)})
            # LINEAJE: runtime guardrail checks `ans` as it flows from the agent to the application log, before it is written to the log.
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `ans` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ce5da279e23384ee8ab54138ea5d5d2e9e333dd431b58c71462c3331e9ed09d0'
            _gr_site_mcedaf3c8 = _gr_client_mcedaf3c8.SiteDescriptor(site_id='site:sha256:ce5da279e23384ee8ab54138ea5d5d2e9e333dd431b58c71462c3331e9ed09d0', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/test/client.py', 'line': 44, 'function': ''}, 'file': 'agent/test/client.py', 'line': 44, 'not_on_graph': True})
            try:
                ans = _gr_client_mcedaf3c8.enforce(_gr_site_mcedaf3c8, ans, content_type='application/json')
            except _gr_client_mcedaf3c8.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            __import__('builtins').list(map(globals().pop, ('_gr_client_mcedaf3c8', '_gr_site_mcedaf3c8'), (None,) * 2))
            print(ans, end='\n', flush=True)

        print(canvas.path)
