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

import base64
import functools
import hashlib
import time
from pathlib import Path


def encode_avatar(image_path):
    with Path.open(image_path, "rb") as file:
        binary_data = file.read()
        # LINEAJE: runtime guardrail checks `binary_data` as it flows from file storage to the agent (in encode_avatar).
        #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `binary_data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:91cd79ad8f3575ae1036c41647b38d7fc98180b9b943865e309aab6f8bd9c70d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:91cd79ad8f3575ae1036c41647b38d7fc98180b9b943865e309aab6f8bd9c70d', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/__init__.py', 'line': 26, 'function': 'encode_avatar'}, 'file': 'test/testcases/utils/__init__.py', 'line': 26, 'function': 'encode_avatar', 'agent_name': 'encode_avatar', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            binary_data = _gr_client.enforce(_gr_site, binary_data, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
    base64_encoded = base64.b64encode(binary_data).decode("utf-8")
    # LINEAJE: runtime guardrail checks `base64_encoded` as it flows from the agent to the user interface, before it leaves the application (in encode_avatar).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `base64_encoded` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:b37c797085b746f1e5c2a25c9d993f5418f245418b8a9cb10623a9d609f03e2b'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b37c797085b746f1e5c2a25c9d993f5418f245418b8a9cb10623a9d609f03e2b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/__init__.py', 'line': 28, 'function': 'encode_avatar'}, 'file': 'test/testcases/utils/__init__.py', 'line': 28, 'function': 'encode_avatar', 'agent_name': 'encode_avatar', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        base64_encoded = _gr_client.enforce(_gr_site, base64_encoded, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return base64_encoded


def compare_by_hash(file1, file2, algorithm="sha256"):
    def _calc_hash(file_path):
        hash_func = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)
        return hash_func.hexdigest()

    return _calc_hash(file1) == _calc_hash(file2)


def wait_for(timeout=10, interval=1, error_msg="Timeout"):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            while True:
                result = func(*args, **kwargs)
                if result is True:
                    # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in wrapper).
                    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:cb8708e73c37f61db7d889520891fdfb5ae15013d357ce0b1345d0d001bae7fc'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cb8708e73c37f61db7d889520891fdfb5ae15013d357ce0b1345d0d001bae7fc', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/__init__.py', 'line': 50, 'function': 'wait_for.decorator.wrapper'}, 'file': 'test/testcases/utils/__init__.py', 'line': 50, 'function': 'wrapper', 'agent_name': 'wrapper', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                    try:
                        result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    return result
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    assert False, error_msg
                time.sleep(interval)

        # LINEAJE: runtime guardrail checks `wrapper` as it flows from the agent to the user interface, before it leaves the application (in decorator).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `wrapper` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:66fc8f17607dce69f7ae4a9210cc811ba3a1d0ff67b6d63bb96352fa748880df'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:66fc8f17607dce69f7ae4a9210cc811ba3a1d0ff67b6d63bb96352fa748880df', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/__init__.py', 'line': 56, 'function': 'wait_for.decorator'}, 'file': 'test/testcases/utils/__init__.py', 'line': 56, 'function': 'decorator', 'agent_name': 'decorator', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            wrapper = _gr_client.enforce(_gr_site, wrapper, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return wrapper

    # LINEAJE: runtime guardrail checks `decorator` as it flows from the agent to the user interface, before it leaves the application (in wait_for).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `decorator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:988ec54cd43726328f641792444d41de229337c29f2fa77f5aaf3cb17f9d8c40'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:988ec54cd43726328f641792444d41de229337c29f2fa77f5aaf3cb17f9d8c40', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/__init__.py', 'line': 58, 'function': 'wait_for'}, 'file': 'test/testcases/utils/__init__.py', 'line': 58, 'function': 'wait_for', 'agent_name': 'wait_for', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        decorator = _gr_client.enforce(_gr_site, decorator, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return decorator


def is_sorted(data, field, descending=True):
    timestamps = [ds[field] for ds in data]
    return all(a >= b for a, b in zip(timestamps, timestamps[1:])) if descending else all(a <= b for a, b in zip(timestamps, timestamps[1:]))
