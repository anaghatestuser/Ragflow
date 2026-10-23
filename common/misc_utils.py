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
import hashlib
import uuid
import requests
import threading
import subprocess
import sys
import os
import logging

def get_uuid():
    return uuid.uuid1().hex


def download_img(url):
    if not url:
        return ""
    response = requests.get(url)
    # LINEAJE: runtime guardrail checks `response` as it flows from an external API to the agent, after the tool returns (in download_img).
    #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `response` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:7f8d7f7c496be37fdc40544e230dc374a9c8759e46d559e5ff1710adb6fdb29a'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7f8d7f7c496be37fdc40544e230dc374a9c8759e46d559e5ff1710adb6fdb29a', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/misc_utils.py', 'line': 34, 'function': 'download_img'}, 'file': 'common/misc_utils.py', 'line': 34, 'function': 'download_img', 'agent_name': 'download_img', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        response = _gr_client.enforce(_gr_site, response, content_type='application/json', variable_name='response', source_file=__file__, before_line=34)
    except _gr_client.GuardrailUnavailableError:
        pass
    return "data:" + \
        response.headers.get('Content-Type', 'image/jpg') + ";" + \
        "base64," + base64.b64encode(response.content).decode("utf-8")


def hash_str2int(line: str, mod: int = 10 ** 8) -> int:
    return int(hashlib.sha1(line.encode("utf-8")).hexdigest(), 16) % mod

def convert_bytes(size_in_bytes: int) -> str:
    """
    Format size in bytes.
    """
    if size_in_bytes == 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    i = 0
    size = float(size_in_bytes)

    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1

    if i == 0 or size >= 100:
        return f"{size:.0f} {units[i]}"
    elif size >= 10:
        return f"{size:.1f} {units[i]}"
    else:
        return f"{size:.2f} {units[i]}"


def once(func):
    """
    A thread-safe decorator that ensures the decorated function runs exactly once,
    caching and returning its result for all subsequent calls. This prevents
    race conditions in multi-thread environments by using a lock to protect
    the execution state.

    Args:
        func (callable): The function to be executed only once.

    Returns:
        callable: A wrapper function that executes `func` on the first call
                  and returns the cached result thereafter.

    Example:
        @once
        def compute_expensive_value():
            print("Computing...")
            return 42

        # First call: executes and prints
        # Subsequent calls: return 42 without executing
    """
    executed = False
    result = None
    lock = threading.Lock()
    def wrapper(*args, **kwargs):
        nonlocal executed, result
        with lock:
            if not executed:
                executed = True
                result = func(*args, **kwargs)
        return result
    # LINEAJE: runtime guardrail checks `wrapper` as it flows from the agent to the user interface, before it leaves the application (in once).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `wrapper` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:bb00844713109966a33a2256ac1f567a7ee01b446926791866079b7c230615b3'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bb00844713109966a33a2256ac1f567a7ee01b446926791866079b7c230615b3', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/misc_utils.py', 'line': 99, 'function': 'once'}, 'file': 'common/misc_utils.py', 'line': 99, 'function': 'once', 'agent_name': 'once', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        wrapper = _gr_client.enforce(_gr_site, wrapper, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return wrapper

@once
def pip_install_torch():
    device = os.getenv("DEVICE", "cpu")
    if device=="cpu":
        return
    _lineaje_payload = "Installing pytorch"
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in pip_install_torch).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:6da356c48c10126b8df91e6a60fc72c6af8fc432fd9d50ea0e7035fc9964700d'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6da356c48c10126b8df91e6a60fc72c6af8fc432fd9d50ea0e7035fc9964700d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/misc_utils.py', 'line': 106, 'function': 'pip_install_torch'}, 'file': 'common/misc_utils.py', 'line': 106, 'function': 'pip_install_torch', 'agent_name': 'pip_install_torch', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.info(_lineaje_payload)
    pkg_names = ["torch>=2.5.0,<3.0.0"]
    subprocess.check_call([sys.executable, "-m", "pip", "install", *pkg_names])
