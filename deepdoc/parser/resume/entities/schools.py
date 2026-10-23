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
import json
import re
import copy
import pandas as pd

current_file_path = os.path.dirname(os.path.abspath(__file__))
TBL = pd.read_csv(
    os.path.join(current_file_path, "res/schools.csv"), sep="\t", header=0
).fillna("")
TBL["name_en"] = TBL["name_en"].map(lambda x: x.lower().strip())
GOOD_SCH = json.load(open(os.path.join(current_file_path, "res/good_sch.json"), "r",encoding="utf-8"))
GOOD_SCH = set([re.sub(r"[,. &（）()]+", "", c) for c in GOOD_SCH])


def loadRank(fnm):
    global TBL
    TBL["rank"] = 1000000
    with open(fnm, "r", encoding="utf-8") as f:
        # LINEAJE: runtime guardrail checks `f` as it flows from file storage to the agent (in loadRank).
        #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `f` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:299143fe7d42547fcbd67c00029adecd00ea67c5a2015f574aca9f2fea60291a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:299143fe7d42547fcbd67c00029adecd00ea67c5a2015f574aca9f2fea60291a', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/resume/entities/schools.py', 'line': 36, 'function': 'loadRank'}, 'file': 'deepdoc/parser/resume/entities/schools.py', 'line': 36, 'function': 'loadRank', 'agent_name': 'loadRank', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            f = _gr_client.enforce(_gr_site, f, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            raise
        while True:
            line = f.readline()
            if not line:
                break
            line = line.strip("\n").split(",")
            try:
                nm, rk = line[0].strip(), int(line[1])
                # assert len(TBL[((TBL.name_cn == nm) | (TBL.name_en == nm))]),f"<{nm}>"
                TBL.loc[((TBL.name_cn == nm) | (TBL.name_en == nm)), "rank"] = rk
            except Exception:
                pass


loadRank(os.path.join(current_file_path, "res/school.rank.csv"))


def split(txt):
    tks = []
    for t in re.sub(r"[ \t]+", " ", txt).split():
        if (
            tks
            and re.match(r".*[a-zA-Z]$", tks[-1])
            and re.match(r"[a-zA-Z]", t)
            and tks
        ):
            tks[-1] = tks[-1] + " " + t
        else:
            tks.append(t)
    # LINEAJE: runtime guardrail checks `tks` as it flows from the agent to the user interface, before it leaves the application (in split).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `tks` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:75fcca33f6d604f738935b035d5010700c05f9f1c083df860653e4a17a1600c4'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:75fcca33f6d604f738935b035d5010700c05f9f1c083df860653e4a17a1600c4', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/resume/entities/schools.py', 'line': 64, 'function': 'split'}, 'file': 'deepdoc/parser/resume/entities/schools.py', 'line': 64, 'function': 'split', 'agent_name': 'split', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        tks = _gr_client.enforce(_gr_site, tks, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return tks


def select(nm):
    global TBL
    if not nm:
        return
    if isinstance(nm, list):
        nm = str(nm[0])
    nm = split(nm)[0]
    nm = str(nm).lower().strip()
    nm = re.sub(r"[(（][^()（）]+[)）]", "", nm.lower())
    nm = re.sub(r"(^the |[,.&（）();；·]+|^(英国|美国|瑞士))", "", nm)
    nm = re.sub(r"大学.*学院", "大学", nm)
    tbl = copy.deepcopy(TBL)
    tbl["hit_alias"] = tbl["alias"].map(lambda x: nm in set(x.split("+")))
    res = tbl[((tbl.name_cn == nm) | (tbl.name_en == nm) | tbl.hit_alias)]
    if res.empty:
        return

    return json.loads(res.to_json(orient="records"))[0]


def is_good(nm):
    global GOOD_SCH
    nm = re.sub(r"[(（][^()（）]+[)）]", "", nm.lower())
    nm = re.sub(r"[''`‘’“”,. &（）();；]+", "", nm)
    return nm in GOOD_SCH
