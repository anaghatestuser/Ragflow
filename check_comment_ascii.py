#!/usr/bin/env python3

"""
Check whether given python files contain non-ASCII comments.

How to check the whole git repo:

```
$ git ls-files -z -- '*.py' | xargs -0 python3 check_comment_ascii.py
```
"""
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


import sys
import tokenize
import ast
import pathlib
import re

ASCII = re.compile(r"^[\n -~]*\Z")  # Printable ASCII + newline


def check(src: str, name: str) -> int:
    """
    docstring line 1
    docstring line 2
    """
    ok = 1
    # A common comment begins with `#`
    with tokenize.open(src) as fp:
        for tk in tokenize.generate_tokens(fp.readline):
            if tk.type == tokenize.COMMENT and not ASCII.fullmatch(tk.string):
                _lineaje_payload = f"{name}:{tk.start[0]}: non-ASCII comment: {tk.string}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in check).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:12439b8bd95ba6cca70aa9f4c1c5372b39a90889371b24e22fef091b3cfde15d'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:12439b8bd95ba6cca70aa9f4c1c5372b39a90889371b24e22fef091b3cfde15d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'check_comment_ascii.py', 'line': 32, 'function': 'check'}, 'file': 'check_comment_ascii.py', 'line': 32, 'function': 'check', 'agent_name': 'check', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
                ok = 0
    # A docstring begins and ends with `'''`
    for node in ast.walk(ast.parse(pathlib.Path(src).read_text(), filename=name)):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
            if (doc := ast.get_docstring(node)) and not ASCII.fullmatch(doc):
                _lineaje_payload = f"{name}:{node.lineno}: non-ASCII docstring: {doc}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in check).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:c750da594abef0f7cc5c1a237c787b019e7dd35b8adb9f37beb9e2b42081c1de'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c750da594abef0f7cc5c1a237c787b019e7dd35b8adb9f37beb9e2b42081c1de', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'check_comment_ascii.py', 'line': 38, 'function': 'check'}, 'file': 'check_comment_ascii.py', 'line': 38, 'function': 'check', 'agent_name': 'check', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                print(_lineaje_payload)
                ok = 0
    # LINEAJE: runtime guardrail checks `ok` as it flows from the agent to the user interface, before it leaves the application (in check).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `ok` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:f9ae606429de9e07e1f9937e118dba151e38354a4df5e7487d215921e4ee15ea'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f9ae606429de9e07e1f9937e118dba151e38354a4df5e7487d215921e4ee15ea', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'check_comment_ascii.py', 'line': 40, 'function': 'check'}, 'file': 'check_comment_ascii.py', 'line': 40, 'function': 'check', 'agent_name': 'check', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        ok = _gr_client.enforce(_gr_site, ok, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return ok


if __name__ == "__main__":
    status = 0
    for file in sys.argv[1:]:
        if not check(file, file):
            status = 1
    sys.exit(status)
