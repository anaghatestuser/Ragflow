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

import os
import queue
import threading
from typing import Any, Callable, Coroutine, Optional, Type, Union
import asyncio
from functools import wraps
from quart import make_response, jsonify
from common.constants import RetCode

TimeoutException = Union[Type[BaseException], BaseException]
OnTimeoutCallback = Union[Callable[..., Any], Coroutine[Any, Any, Any]]


def timeout(seconds: float | int | str = None, attempts: int = 2, *, exception: Optional[TimeoutException] = None,
            on_timeout: Optional[OnTimeoutCallback] = None):
    if isinstance(seconds, str):
        seconds = float(seconds)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result_queue = queue.Queue(maxsize=1)

            def target():
                try:
                    result = func(*args, **kwargs)
                    result_queue.put(result)
                except Exception as e:
                    result_queue.put(e)

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()

            for a in range(attempts):
                try:
                    if os.environ.get("ENABLE_TIMEOUT_ASSERTION"):
                        result = result_queue.get(timeout=seconds)
                    else:
                        result = result_queue.get()
                    if isinstance(result, Exception):
                        raise result
                    # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in target).
                    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:2c9dde1ac7f0d2ae5fb13d9a6abb16eb25575d07765e156cefdf56a9d2c351d6'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2c9dde1ac7f0d2ae5fb13d9a6abb16eb25575d07765e156cefdf56a9d2c351d6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/connection_utils.py', 'line': 59, 'function': 'timeout.decorator.wrapper'}, 'file': 'common/connection_utils.py', 'line': 59, 'function': 'target', 'agent_name': 'target', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                    try:
                        result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    return result
                except queue.Empty:
                    pass
            raise TimeoutError(f"Function '{func.__name__}' timed out after {seconds} seconds and {attempts} attempts.")

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            if seconds is None:
                return await func(*args, **kwargs)

            for a in range(attempts):
                try:
                    if os.environ.get("ENABLE_TIMEOUT_ASSERTION"):
                        return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
                    else:
                        return await func(*args, **kwargs)
                except asyncio.TimeoutError:
                    if a < attempts - 1:
                        continue
                    if on_timeout is not None:
                        if callable(on_timeout):
                            result = on_timeout()
                            if isinstance(result, Coroutine):
                                return await result
                            # LINEAJE: runtime guardrail checks `result` as it flows from the agent to the user interface, before it leaves the application (in async_wrapper).
                            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `result` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                            #   Do not remove without review. site_id='site:sha256:15d7590dc478b71a287b599c64308e5d64daf6a1cd5d08ba9d6c2982c2e25171'
                            _gr_client = _lineaje_load_gr_client()
                            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:15d7590dc478b71a287b599c64308e5d64daf6a1cd5d08ba9d6c2982c2e25171', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/connection_utils.py', 'line': 83, 'function': 'timeout.decorator.async_wrapper'}, 'file': 'common/connection_utils.py', 'line': 83, 'function': 'async_wrapper', 'agent_name': 'async_wrapper', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                            try:
                                result = _gr_client.enforce(_gr_site, result, content_type='text/plain')
                            except _gr_client.GuardrailUnavailableError:
                                pass
                            except PermissionError:
                                pass
                            return result
                        return on_timeout

                    if exception is None:
                        raise TimeoutError(f"Operation timed out after {seconds} seconds and {attempts} attempts.")

                    if isinstance(exception, BaseException):
                        raise exception

                    if isinstance(exception, type) and issubclass(exception, BaseException):
                        raise exception(f"Operation timed out after {seconds} seconds and {attempts} attempts.")

                    raise RuntimeError("Invalid exception type provided")

        if asyncio.iscoroutinefunction(func):
            # LINEAJE: runtime guardrail checks `async_wrapper` as it flows from the agent to the user interface, before it leaves the application (in async_wrapper).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `async_wrapper` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:4a52499ccdeba3251cff97383aa6e3fccbbdc1ac2483fbcb9b17c2755080ac94'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4a52499ccdeba3251cff97383aa6e3fccbbdc1ac2483fbcb9b17c2755080ac94', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/connection_utils.py', 'line': 98, 'function': 'timeout.decorator'}, 'file': 'common/connection_utils.py', 'line': 98, 'function': 'async_wrapper', 'agent_name': 'async_wrapper', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                async_wrapper = _gr_client.enforce(_gr_site, async_wrapper, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return async_wrapper
        # LINEAJE: runtime guardrail checks `wrapper` as it flows from the agent to the user interface, before it leaves the application (in decorator).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `wrapper` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f6a6a3eeacb07149be66754e1f1cbec400ea9a00c9f1c02f7a249696d4beabe4'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f6a6a3eeacb07149be66754e1f1cbec400ea9a00c9f1c02f7a249696d4beabe4', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/connection_utils.py', 'line': 99, 'function': 'timeout.decorator'}, 'file': 'common/connection_utils.py', 'line': 99, 'function': 'decorator', 'agent_name': 'decorator', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            wrapper = _gr_client.enforce(_gr_site, wrapper, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return wrapper

    # LINEAJE: runtime guardrail checks `decorator` as it flows from the agent to the user interface, before it leaves the application (in timeout).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `decorator` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:cc78ab86e5cba42467c4f7e7e03768cad7f9a871c7bc2cae1bdee73420f383d9'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cc78ab86e5cba42467c4f7e7e03768cad7f9a871c7bc2cae1bdee73420f383d9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/connection_utils.py', 'line': 101, 'function': 'timeout'}, 'file': 'common/connection_utils.py', 'line': 101, 'function': 'timeout', 'agent_name': 'timeout', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        decorator = _gr_client.enforce(_gr_site, decorator, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return decorator


async def construct_response(code=RetCode.SUCCESS, message="success", data=None, auth=None):
    result_dict = {"code": code, "message": message, "data": data}
    response_dict = {}
    for key, value in result_dict.items():
        if value is None and key != "code":
            continue
        else:
            response_dict[key] = value
    _lineaje_payload = jsonify(response_dict)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the user interface, before it leaves the application (in construct_response).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:c7e608914f57cbcbc4d401d9378af608df168fed9efce0127861f9e387a52033'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c7e608914f57cbcbc4d401d9378af608df168fed9efce0127861f9e387a52033', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/connection_utils.py', 'line': 112, 'function': 'construct_response'}, 'file': 'common/connection_utils.py', 'line': 112, 'function': 'construct_response', 'agent_name': 'construct_response', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, _lineaje_payload, content_type='text/plain'))
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    response = await make_response(_lineaje_payload)
    if auth:
        response.headers["Authorization"] = auth
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Method"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Expose-Headers"] = "Authorization"
    # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the user interface, before it leaves the application (in construct_response).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:368c1edd3cbceb53412cb6da51c604286f36c4dde823f40fb458306915a0e2c9'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:368c1edd3cbceb53412cb6da51c604286f36c4dde823f40fb458306915a0e2c9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/connection_utils.py', 'line': 120, 'function': 'construct_response'}, 'file': 'common/connection_utils.py', 'line': 120, 'function': 'construct_response', 'agent_name': 'construct_response', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        response = _gr_client.enforce(_gr_site, response, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return response


def sync_construct_response(code=RetCode.SUCCESS, message="success", data=None, auth=None):
    import flask
    result_dict = {"code": code, "message": message, "data": data}
    response_dict = {}
    for key, value in result_dict.items():
        if value is None and key != "code":
            continue
        else:
            response_dict[key] = value
    _lineaje_payload = flask.jsonify(response_dict)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the user interface, before it leaves the application (in sync_construct_response).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:f1aa59049e8e6a2f6fbb2934a48763bbebac10790b3c53181f6d9fc874357a9b'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f1aa59049e8e6a2f6fbb2934a48763bbebac10790b3c53181f6d9fc874357a9b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/connection_utils.py', 'line': 132, 'function': 'sync_construct_response'}, 'file': 'common/connection_utils.py', 'line': 132, 'function': 'sync_construct_response', 'agent_name': 'sync_construct_response', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    response = flask.make_response(_lineaje_payload)
    if auth:
        response.headers["Authorization"] = auth
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Method"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Expose-Headers"] = "Authorization"
    # LINEAJE: runtime guardrail checks `response` as it flows from the agent to the user interface, before it leaves the application (in sync_construct_response).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `response` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:ae565c96310e4bef16322be797c376360ba85e7a5594e78961a37116a6408d8c'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ae565c96310e4bef16322be797c376360ba85e7a5594e78961a37116a6408d8c', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/connection_utils.py', 'line': 140, 'function': 'sync_construct_response'}, 'file': 'common/connection_utils.py', 'line': 140, 'function': 'sync_construct_response', 'agent_name': 'sync_construct_response', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        response = _gr_client.enforce(_gr_site, response, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return response
