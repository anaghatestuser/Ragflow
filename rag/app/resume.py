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
import base64
import datetime
import json
import re
import pandas as pd
import requests
from api.db.services.knowledgebase_service import KnowledgebaseService
from rag.nlp import rag_tokenizer
from deepdoc.parser.resume import refactor
from deepdoc.parser.resume import step_one, step_two
from common.string_utils import remove_redundant_spaces

forbidden_select_fields4resume = [
    "name_pinyin_kwd", "edu_first_fea_kwd", "degree_kwd", "sch_rank_kwd", "edu_fea_kwd"
]


def remote_call(filename, binary):
    q = {
        "header": {
            "uid": 1,
            "user": "kevinhu",
            "log_id": filename
        },
        "request": {
            "p": {
                "request_id": "1",
                "encrypt_type": "base64",
                "filename": filename,
                "langtype": '',
                "fileori": base64.b64encode(binary).decode('utf-8')
            },
            "c": "resume_parse_module",
            "m": "resume_parse"
        }
    }
    for _ in range(3):
        try:
            # LINEAJE: runtime guardrail checks `q` as it flows from the agent to an external endpoint, before it leaves the application (in remote_call).
            #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `q` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:3b674929daffe4bc9bf099a5e213f0a98ff60c154e616a88d31e1707c94c5559'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:3b674929daffe4bc9bf099a5e213f0a98ff60c154e616a88d31e1707c94c5559', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/resume.py', 'line': 56, 'function': 'remote_call'}, 'file': 'rag/app/resume.py', 'line': 56, 'function': 'remote_call', 'agent_name': 'remote_call', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                q = _gr_client.enforce(_gr_site, q, content_type='application/json', variable_name='q', source_file=__file__, before_line=56)
            except _gr_client.GuardrailUnavailableError:
                pass
            resume = requests.post(
                "http://127.0.0.1:61670/tog",
                data=json.dumps(q))
            # LINEAJE: runtime guardrail checks `resume` as it flows from an external API to the agent, after the tool returns (in remote_call).
            #   Detected: this statement moves data from an external API to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `resume` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:5a94d5ce9ff3f3b753b57013f396131afd71a2b1eb35195391ca65017c5dcd9c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5a94d5ce9ff3f3b753b57013f396131afd71a2b1eb35195391ca65017c5dcd9c', phase='post_tool', boundary={'source': 'external_endpoint', 'sink': 'agent_message'}, fail_mode='ALLOW_WITH_AUDIT', source_type='api', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/resume.py', 'line': 56, 'function': 'remote_call'}, 'file': 'rag/app/resume.py', 'line': 56, 'function': 'remote_call', 'agent_name': 'remote_call', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                resume = _gr_client.enforce(_gr_site, resume, content_type='application/json', variable_name='resume', source_file=__file__, before_line=56)
            except _gr_client.GuardrailUnavailableError:
                pass
            resume = resume.json()["response"]["results"]
            resume = refactor(resume)
            for k in ["education", "work", "project",
                      "training", "skill", "certificate", "language"]:
                if not resume.get(k) and k in resume:
                    del resume[k]

            # LINEAJE: runtime guardrail checks `resume` as it flows from the agent to an external endpoint, before it leaves the application (in remote_call).
            #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `resume` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:0a2bdad3793a2e9c2df5771bcb9eee6e0b3102d7b4f9e372825d45ce635da829'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:0a2bdad3793a2e9c2df5771bcb9eee6e0b3102d7b4f9e372825d45ce635da829', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/resume.py', 'line': 66, 'function': 'remote_call'}, 'file': 'rag/app/resume.py', 'line': 66, 'function': 'remote_call', 'agent_name': 'remote_call', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                resume = _gr_client.enforce(_gr_site, resume, content_type='application/json', variable_name='resume', source_file=__file__, before_line=66)
            except _gr_client.GuardrailUnavailableError:
                pass
            resume = step_one.refactor(pd.DataFrame([{"resume_content": json.dumps(resume), "tob_resume_id": "x",
                                                      "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}]))
            resume = step_two.parse(resume)
            # LINEAJE: runtime guardrail checks `resume` as it flows from the agent to the user interface, before it leaves the application (in remote_call).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `resume` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:4883fbb659f2efd96ef8606d16ed4e2b82b7c5f6931be1e079bbb266e04a3f82'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4883fbb659f2efd96ef8606d16ed4e2b82b7c5f6931be1e079bbb266e04a3f82', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/resume.py', 'line': 69, 'function': 'remote_call'}, 'file': 'rag/app/resume.py', 'line': 69, 'function': 'remote_call', 'agent_name': 'remote_call', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                resume = _gr_client.enforce(_gr_site, resume, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return resume
        except Exception:
            _lineaje_payload = "Resume parser has not been supported yet!"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in remote_call).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:33caac4de1b12641072a26c16ad903b074c147583b39af75563c2a8ae60ef1e4'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:33caac4de1b12641072a26c16ad903b074c147583b39af75563c2a8ae60ef1e4', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/resume.py', 'line': 71, 'function': 'remote_call'}, 'file': 'rag/app/resume.py', 'line': 71, 'function': 'remote_call', 'agent_name': 'remote_call', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
    # LINEAJE: runtime guardrail checks `q` as it flows from the agent to an external endpoint, before it leaves the application (in remote_call).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `q` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:b3d514ac3cc1a03d86dd8602daaa0085065599e911c7aa434af58fbcbe53529e'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b3d514ac3cc1a03d86dd8602daaa0085065599e911c7aa434af58fbcbe53529e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/resume.py', 'line': 72, 'function': 'remote_call'}, 'file': 'rag/app/resume.py', 'line': 72, 'function': 'remote_call', 'agent_name': 'remote_call', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        q = _gr_client.enforce(_gr_site, q, content_type='application/json', variable_name='q', source_file=__file__, before_line=72)
    except _gr_client.GuardrailUnavailableError:
        pass
    return {}


def chunk(filename, binary=None, callback=None, **kwargs):
    """
    The supported file formats are pdf, docx and txt.
    To maximize the effectiveness, parse the resume correctly, please concat us: https://github.com/infiniflow/ragflow
    """
    if not re.search(r"\.(pdf|doc|docx|txt)$", filename, flags=re.IGNORECASE):
        raise NotImplementedError("file type not supported yet(pdf supported)")

    if not binary:
        with open(filename, "rb") as f:
            binary = f.read()
            # LINEAJE: runtime guardrail checks `binary` as it flows from file storage to the agent (in chunk).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `binary` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:cea032a392f0a7ec1d468f8f8526dd1aa8e252d6ff88c27bc018d10d0f91a47c'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:cea032a392f0a7ec1d468f8f8526dd1aa8e252d6ff88c27bc018d10d0f91a47c', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/resume.py', 'line': 85, 'function': 'chunk'}, 'file': 'rag/app/resume.py', 'line': 85, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                binary = _gr_client.enforce(_gr_site, binary, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise

    callback(0.2, "Resume parsing is going on...")
    resume = remote_call(filename, binary)
    if len(resume.keys()) < 7:
        callback(-1, "Resume is not successfully parsed.")
        raise Exception("Resume parser remote call fail!")
    callback(0.6, "Done parsing. Chunking...")
    # LINEAJE: runtime guardrail checks `resume` as it flows from the agent to an external endpoint, before it leaves the application (in chunk).
    #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: medium).
    #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `resume` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:e0b825f69d79efdabb462e97d54328adc66c2bc5595eccadf5b172090c061560'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e0b825f69d79efdabb462e97d54328adc66c2bc5595eccadf5b172090c061560', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/resume.py', 'line': 93, 'function': 'chunk'}, 'file': 'rag/app/resume.py', 'line': 93, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        resume = _gr_client.enforce(_gr_site, resume, content_type='application/json', variable_name='resume', source_file=__file__, before_line=93)
    except _gr_client.GuardrailUnavailableError:
        pass
    _lineaje_payload = "chunking resume: " + json.dumps(resume, ensure_ascii=False, indent=2)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in chunk).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:8867496103d513609423257b23e738b2f564734f20ce374fd518d0682e39afe5'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8867496103d513609423257b23e738b2f564734f20ce374fd518d0682e39afe5', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/resume.py', 'line': 93, 'function': 'chunk'}, 'file': 'rag/app/resume.py', 'line': 93, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.debug(_lineaje_payload)

    field_map = {
        "name_kwd": "姓名/名字",
        "name_pinyin_kwd": "姓名拼音/名字拼音",
        "gender_kwd": "性别（男，女）",
        "age_int": "年龄/岁/年纪",
        "phone_kwd": "电话/手机/微信",
        "email_tks": "email/e-mail/邮箱",
        "position_name_tks": "职位/职能/岗位/职责",
        "expect_city_names_tks": "期望城市",
        "work_exp_flt": "工作年限/工作年份/N年经验/毕业了多少年",
        "corporation_name_tks": "最近就职(上班)的公司/上一家公司",

        "first_school_name_tks": "第一学历毕业学校",
        "first_degree_kwd": "第一学历（高中，职高，硕士，本科，博士，初中，中技，中专，专科，专升本，MPA，MBA，EMBA）",
        "highest_degree_kwd": "最高学历（高中，职高，硕士，本科，博士，初中，中技，中专，专科，专升本，MPA，MBA，EMBA）",
        "first_major_tks": "第一学历专业",
        "edu_first_fea_kwd": "第一学历标签（211，留学，双一流，985，海外知名，重点大学，中专，专升本，专科，本科，大专）",

        "degree_kwd": "过往学历（高中，职高，硕士，本科，博士，初中，中技，中专，专科，专升本，MPA，MBA，EMBA）",
        "major_tks": "学过的专业/过往专业",
        "school_name_tks": "学校/毕业院校",
        "sch_rank_kwd": "学校标签（顶尖学校，精英学校，优质学校，一般学校）",
        "edu_fea_kwd": "教育标签（211，留学，双一流，985，海外知名，重点大学，中专，专升本，专科，本科，大专）",

        "corp_nm_tks": "就职过的公司/之前的公司/上过班的公司",
        "edu_end_int": "毕业年份",
        "industry_name_tks": "所在行业",

        "birth_dt": "生日/出生年份",
        "expect_position_name_tks": "期望职位/期望职能/期望岗位",
    }

    titles = []
    for n in ["name_kwd", "gender_kwd", "position_name_tks", "age_int"]:
        v = resume.get(n, "")
        if isinstance(v, list):
            v = v[0]
        if n.find("tks") > 0:
            v = remove_redundant_spaces(v)
        titles.append(str(v))
    doc = {
        "docnm_kwd": filename,
        "title_tks": rag_tokenizer.tokenize("-".join(titles) + "-简历")
    }
    doc["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(doc["title_tks"])
    pairs = []
    for n, m in field_map.items():
        if not resume.get(n):
            continue
        v = resume[n]
        if isinstance(v, list):
            v = " ".join(v)
        if n.find("tks") > 0:
            v = remove_redundant_spaces(v)
        pairs.append((m, str(v)))

    doc["content_with_weight"] = "\n".join(
        ["{}: {}".format(re.sub(r"（[^（）]+）", "", k), v) for k, v in pairs])
    doc["content_ltks"] = rag_tokenizer.tokenize(doc["content_with_weight"])
    doc["content_sm_ltks"] = rag_tokenizer.fine_grained_tokenize(doc["content_ltks"])
    for n, _ in field_map.items():
        if n not in resume:
            continue
        if isinstance(resume[n], list) and (
                len(resume[n]) == 1 or n not in forbidden_select_fields4resume):
            resume[n] = resume[n][0]
        if n.find("_tks") > 0:
            resume[n] = rag_tokenizer.fine_grained_tokenize(resume[n])
        doc[n] = resume[n]

    _lineaje_payload = "chunked resume to " + str(doc)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in chunk).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:36ab0cbce1bbd17e0f174a3758e5d77d47a79e7b4cc0f34cb7defea6561c0257'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:36ab0cbce1bbd17e0f174a3758e5d77d47a79e7b4cc0f34cb7defea6561c0257', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/resume.py', 'line': 165, 'function': 'chunk'}, 'file': 'rag/app/resume.py', 'line': 165, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.debug(_lineaje_payload)
    KnowledgebaseService.update_parser_config(
        kwargs["kb_id"], {"field_map": field_map})
    return [doc]


if __name__ == "__main__":
    import sys

    def dummy(a, b):
        pass
    chunk(sys.argv[1], callback=dummy)
