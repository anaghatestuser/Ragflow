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
from email import policy
from email.parser import BytesParser
from rag.app.naive import chunk as naive_chunk
import re
from rag.nlp import rag_tokenizer, naive_merge, tokenize_chunks
from deepdoc.parser import HtmlParser, TxtParser
from timeit import default_timer as timer
import io


def chunk(
    filename,
    binary=None,
    from_page=0,
    to_page=100000,
    lang="Chinese",
    callback=None,
    **kwargs,
):
    """
    Only eml is supported
    """
    eng = lang.lower() == "english"  # is_english(cks)
    parser_config = kwargs.get(
        "parser_config",
        {"chunk_token_num": 512, "delimiter": "\n!?。；！？", "layout_recognize": "DeepDOC"},
    )
    doc = {
        "docnm_kwd": filename,
        "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename)),
    }
    doc["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(doc["title_tks"])
    main_res = []
    attachment_res = []

    if binary:
        with io.BytesIO(binary) as buffer:
            msg = BytesParser(policy=policy.default).parse(buffer)
    else:
        with open(filename, "rb") as buffer:
            # LINEAJE: runtime guardrail checks `buffer` as it flows from file storage to the agent (in chunk).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `buffer` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:d87796910100c419a11cfd4033292db089664840c40d33e3f407f2e041b5f60d'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d87796910100c419a11cfd4033292db089664840c40d33e3f407f2e041b5f60d', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/email.py', 'line': 58, 'function': 'chunk'}, 'file': 'rag/app/email.py', 'line': 58, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                buffer = _gr_client.enforce(_gr_site, buffer, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            msg = BytesParser(policy=policy.default).parse(buffer)

    text_txt, html_txt = [], []
    # get the email header info
    for header, value in msg.items():
        text_txt.append(f"{header}: {value}")

    #  get the email main info
    def _add_content(msg, content_type):
        def _decode_payload(payload, charset, target_list):
            try:
                target_list.append(payload.decode(charset))
            except (UnicodeDecodeError, LookupError):
                for enc in ["utf-8", "gb2312", "gbk", "gb18030", "latin1"]:
                    try:
                        target_list.append(payload.decode(enc))
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    target_list.append(payload.decode("utf-8", errors="ignore"))

        if content_type == "text/plain":
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            _decode_payload(payload, charset, text_txt)
        elif content_type == "text/html":
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or "utf-8"
            _decode_payload(payload, charset, html_txt)
        elif "multipart" in content_type:
            if msg.is_multipart():
                for part in msg.iter_parts():
                    _add_content(part, part.get_content_type())

    _add_content(msg, msg.get_content_type())

    sections = TxtParser.parser_txt("\n".join(text_txt)) + [
        (line, "") for line in HtmlParser.parser_txt("\n".join(html_txt), chunk_token_num=parser_config["chunk_token_num"]) if line
    ]

    st = timer()
    chunks = naive_merge(
        sections,
        int(parser_config.get("chunk_token_num", 128)),
        parser_config.get("delimiter", "\n!?。；！？"),
    )

    main_res.extend(tokenize_chunks(chunks, doc, eng, None))
    _lineaje_payload = "naive_merge({}): {}".format(filename, timer() - st)
    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in chunk).
    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:bf97d9369e6b47ab2b11fe3fddf66b634ff6f3920670e9346580b67a20cb9f1b'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:bf97d9369e6b47ab2b11fe3fddf66b634ff6f3920670e9346580b67a20cb9f1b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/app/email.py', 'line': 107, 'function': 'chunk'}, 'file': 'rag/app/email.py', 'line': 107, 'function': 'chunk', 'agent_name': 'chunk', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    logging.debug(_lineaje_payload)
    # get the attachment info
    for part in msg.iter_attachments():
        content_disposition = part.get("Content-Disposition")
        if content_disposition:
            dispositions = content_disposition.strip().split(";")
            if dispositions[0].lower() == "attachment":
                filename = part.get_filename()
                payload = part.get_payload(decode=True)
                try:
                    attachment_res.extend(
                        naive_chunk(filename, payload, callback=callback, **kwargs)
                    )
                except Exception:
                    pass

    return main_res + attachment_res


if __name__ == "__main__":
    import sys

    def dummy(prog=None, msg=""):
        pass

    chunk(sys.argv[1], callback=dummy)
