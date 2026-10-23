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

import datetime


def refactor(cv):
    for n in [
        "raw_txt",
        "parser_name",
        "inference",
        "ori_text",
        "use_time",
        "time_stat",
    ]:
        if n in cv and cv[n] is not None:
            del cv[n]
    cv["is_deleted"] = 0
    if "basic" not in cv:
        cv["basic"] = {}
    if cv["basic"].get("photo2"):
        del cv["basic"]["photo2"]

    for n in [
        "education",
        "work",
        "certificate",
        "project",
        "language",
        "skill",
        "training",
    ]:
        if n not in cv or cv[n] is None:
            continue
        if isinstance(cv[n], dict):
            cv[n] = [v for _, v in cv[n].items()]
        if not isinstance(cv[n], list):
            del cv[n]
            continue
        vv = []
        for v in cv[n]:
            if "external" in v and v["external"] is not None:
                del v["external"]
            vv.append(v)
        cv[n] = {str(i): vv[i] for i in range(len(vv))}

    basics = [
        ("basic_salary_month", "salary_month"),
        ("expect_annual_salary_from", "expect_annual_salary"),
    ]
    for n, t in basics:
        if cv["basic"].get(n):
            cv["basic"][t] = cv["basic"][n]
            del cv["basic"][n]

    work = sorted(
        [v for _, v in cv.get("work", {}).items()],
        key=lambda x: x.get("start_time", ""),
    )
    edu = sorted(
        [v for _, v in cv.get("education", {}).items()],
        key=lambda x: x.get("start_time", ""),
    )

    if work:
        cv["basic"]["work_start_time"] = work[0].get("start_time", "")
        cv["basic"]["management_experience"] = (
            "Y"
            if any([w.get("management_experience", "") == "Y" for w in work])
            else "N"
        )
        cv["basic"]["annual_salary"] = work[-1].get("annual_salary_from", "0")

        for n in [
            "annual_salary_from",
            "annual_salary_to",
            "industry_name",
            "position_name",
            "responsibilities",
            "corporation_type",
            "scale",
            "corporation_name",
        ]:
            cv["basic"][n] = work[-1].get(n, "")

    if edu:
        for n in ["school_name", "discipline_name"]:
            if n in edu[-1]:
                cv["basic"][n] = edu[-1][n]

    cv["basic"]["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "contact" not in cv:
        cv["contact"] = {}
    if not cv["contact"].get("name"):
        cv["contact"]["name"] = cv["basic"].get("name", "")
    # LINEAJE: runtime guardrail checks `cv` as it flows from the agent to the user interface, before it leaves the application (in refactor).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `cv` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:58c3393bc558407aed3bb4b6373b231555ebe04783ea1d99982573ec3923ec01'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:58c3393bc558407aed3bb4b6373b231555ebe04783ea1d99982573ec3923ec01', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/resume/__init__.py', 'line': 109, 'function': 'refactor'}, 'file': 'deepdoc/parser/resume/__init__.py', 'line': 109, 'function': 'refactor', 'agent_name': 'refactor', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        cv = _gr_client.enforce(_gr_site, cv, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return cv
