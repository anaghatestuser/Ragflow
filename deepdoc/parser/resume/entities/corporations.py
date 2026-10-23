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

import logging
import re
import json
import os
import pandas as pd
from rag.nlp import rag_tokenizer
from . import regions


current_file_path = os.path.dirname(os.path.abspath(__file__))
GOODS = pd.read_csv(
    os.path.join(current_file_path, "res/corp_baike_len.csv"), sep="\t", header=0
).fillna(0)
GOODS["cid"] = GOODS["cid"].astype(str)
GOODS = GOODS.set_index(["cid"])
CORP_TKS = json.load(
    open(os.path.join(current_file_path, "res/corp.tks.freq.json"), "r",encoding="utf-8")
)
GOOD_CORP = json.load(open(os.path.join(current_file_path, "res/good_corp.json"), "r",encoding="utf-8"))
CORP_TAG = json.load(open(os.path.join(current_file_path, "res/corp_tag.json"), "r",encoding="utf-8"))


def baike(cid, default_v=0):
    global GOODS
    try:
        return GOODS.loc[str(cid), "len"]
    except Exception:
        pass
    # LINEAJE: runtime guardrail checks `default_v` as it flows from the agent to the user interface, before it leaves the application (in baike).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `default_v` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:8e3f014809b9b69cbeac3193d06bec37aa3f9c9c65bb69dc7fea75140986c878'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8e3f014809b9b69cbeac3193d06bec37aa3f9c9c65bb69dc7fea75140986c878', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/resume/entities/corporations.py', 'line': 45, 'function': 'baike'}, 'file': 'deepdoc/parser/resume/entities/corporations.py', 'line': 45, 'function': 'baike', 'agent_name': 'baike', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        default_v = _gr_client.enforce(_gr_site, default_v, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return default_v


def corpNorm(nm, add_region=True):
    global CORP_TKS
    if not nm or not isinstance(nm, str):
        return ""
    nm = rag_tokenizer.tradi2simp(rag_tokenizer.strQ2B(nm)).lower()
    nm = re.sub(r"&amp;", "&", nm)
    nm = re.sub(r"[\(\)（）\+'\"\t \*\\【】-]+", " ", nm)
    nm = re.sub(
        r"([—-]+.*| +co\..*|corp\..*| +inc\..*| +ltd.*)", "", nm, count=10000, flags=re.IGNORECASE
    )
    nm = re.sub(
        r"(计算机|技术|(技术|科技|网络)*有限公司|公司|有限|研发中心|中国|总部)$",
        "",
        nm,
        count=10000,
        flags=re.IGNORECASE,
    )
    if not nm or (len(nm) < 5 and not regions.isName(nm[0:2])):
        # LINEAJE: runtime guardrail checks `nm` as it flows from the agent to the user interface, before it leaves the application (in corpNorm).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `nm` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:166d2f1fb8e8ed3ed83b35048d939c22d69437c066ad190d97162b963c113e91'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:166d2f1fb8e8ed3ed83b35048d939c22d69437c066ad190d97162b963c113e91', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/resume/entities/corporations.py', 'line': 66, 'function': 'corpNorm'}, 'file': 'deepdoc/parser/resume/entities/corporations.py', 'line': 66, 'function': 'corpNorm', 'agent_name': 'corpNorm', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            nm = _gr_client.enforce(_gr_site, nm, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return nm

    tks = rag_tokenizer.tokenize(nm).split()
    reg = [t for i, t in enumerate(tks) if regions.isName(t) and (t != "中国" or i > 0)]
    nm = ""
    for t in tks:
        if regions.isName(t) or t in CORP_TKS:
            continue
        if re.match(r"[0-9a-zA-Z\\,.]+", t) and re.match(r".*[0-9a-zA-Z\,.]+$", nm):
            nm += " "
        nm += t

    r = re.search(r"^([^a-z0-9 \(\)&]{2,})[a-z ]{4,}$", nm.strip())
    if r:
        nm = r.group(1)
    r = re.search(r"^([a-z ]{3,})[^a-z0-9 \(\)&]{2,}$", nm.strip())
    if r:
        nm = r.group(1)
    return nm.strip() + (("" if not reg else "(%s)" % reg[0]) if add_region else "")


def rmNoise(n):
    n = re.sub(r"[\(（][^()（）]+[)）]", "", n)
    n = re.sub(r"[,. &（）()]+", "", n)
    # LINEAJE: runtime guardrail checks `n` as it flows from the agent to the user interface, before it leaves the application (in rmNoise).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `n` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:943c354f3adcd0fa3385f66d8b2867bc875f1cd2b7dee051d3b94b7a873512f6'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:943c354f3adcd0fa3385f66d8b2867bc875f1cd2b7dee051d3b94b7a873512f6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/resume/entities/corporations.py', 'line': 90, 'function': 'rmNoise'}, 'file': 'deepdoc/parser/resume/entities/corporations.py', 'line': 90, 'function': 'rmNoise', 'agent_name': 'rmNoise', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        n = _gr_client.enforce(_gr_site, n, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return n


GOOD_CORP = set([corpNorm(rmNoise(c), False) for c in GOOD_CORP])
for c, v in CORP_TAG.items():
    cc = corpNorm(rmNoise(c), False)
    if not cc:
        logging.debug(c)
CORP_TAG = {corpNorm(rmNoise(c), False): v for c, v in CORP_TAG.items()}


def is_good(nm):
    global GOOD_CORP
    if nm.find("外派") >= 0:
        return False
    nm = rmNoise(nm)
    nm = corpNorm(nm, False)
    for n in GOOD_CORP:
        if re.match(r"[0-9a-zA-Z]+$", n):
            if n == nm:
                return True
        elif nm.find(n) >= 0:
            return True
    return False


def corp_tag(nm):
    global CORP_TAG
    nm = rmNoise(nm)
    nm = corpNorm(nm, False)
    for n in CORP_TAG.keys():
        if re.match(r"[0-9a-zA-Z., ]+$", n):
            if n == nm:
                return CORP_TAG[n]
        elif nm.find(n) >= 0:
            if len(n) < 3 and len(nm) / len(n) >= 2:
                continue
            return CORP_TAG[n]
    return []
