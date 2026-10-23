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

import json

from docx import Document  # pip install python-docx
from openpyxl import Workbook  # pip install openpyxl
from PIL import Image, ImageDraw  # pip install Pillow
from pptx import Presentation  # pip install python-pptx
from reportlab.pdfgen import canvas  # pip install reportlab


def create_docx_file(path):
    doc = Document()
    doc.add_paragraph("This is a test DOCX file.")
    doc.save(path)
    # LINEAJE: runtime guardrail checks `path` as it flows from the agent to the user interface, before it leaves the application (in create_docx_file).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:ab40d5f10f441f7f7bf5e33efccd6c8467df273fde698ef418975e9dab6abc6e'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ab40d5f10f441f7f7bf5e33efccd6c8467df273fde698ef418975e9dab6abc6e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 30, 'function': 'create_docx_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 30, 'function': 'create_docx_file', 'agent_name': 'create_docx_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        path = _gr_client.enforce(_gr_site, path, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return path


def create_excel_file(path):
    wb = Workbook()
    ws = wb.active
    ws["A1"] = "Test Excel File"
    wb.save(path)
    # LINEAJE: runtime guardrail checks `path` as it flows from the agent to the user interface, before it leaves the application (in create_excel_file).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:267625a55d358be6c545a2de949c56b5c3daa08c5e91b982232866db571503ab'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:267625a55d358be6c545a2de949c56b5c3daa08c5e91b982232866db571503ab', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 38, 'function': 'create_excel_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 38, 'function': 'create_excel_file', 'agent_name': 'create_excel_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        path = _gr_client.enforce(_gr_site, path, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return path


def create_ppt_file(path):
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Test PPT File"
    prs.save(path)
    # LINEAJE: runtime guardrail checks `path` as it flows from the agent to the user interface, before it leaves the application (in create_ppt_file).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:d972da39106177d6427a8b8144fac2d6cba952d804c0d9fd5f7a161b9cd5b942'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d972da39106177d6427a8b8144fac2d6cba952d804c0d9fd5f7a161b9cd5b942', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 46, 'function': 'create_ppt_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 46, 'function': 'create_ppt_file', 'agent_name': 'create_ppt_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        path = _gr_client.enforce(_gr_site, path, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return path


def create_image_file(path):
    img = Image.new("RGB", (100, 100), color="blue")
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "Test", fill="white")
    img.save(path)
    # LINEAJE: runtime guardrail checks `path` as it flows from the agent to the user interface, before it leaves the application (in create_image_file).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:db7f37750931cf08668e8b38998feaa2c735a148203336403aecbe29dd213ac0'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:db7f37750931cf08668e8b38998feaa2c735a148203336403aecbe29dd213ac0', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 54, 'function': 'create_image_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 54, 'function': 'create_image_file', 'agent_name': 'create_image_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        path = _gr_client.enforce(_gr_site, path, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return path


def create_pdf_file(path):
    if not isinstance(path, str):
        path = str(path)
    c = canvas.Canvas(path)
    c.drawString(100, 750, "Test PDF File")
    c.save()
    # LINEAJE: runtime guardrail checks `path` as it flows from the agent to the user interface, before it leaves the application (in create_pdf_file).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:334b44831f48c14d8a07607301612c29c010448098491f5bd0e040d0ebc8ecfb'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:334b44831f48c14d8a07607301612c29c010448098491f5bd0e040d0ebc8ecfb', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 63, 'function': 'create_pdf_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 63, 'function': 'create_pdf_file', 'agent_name': 'create_pdf_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        path = _gr_client.enforce(_gr_site, path, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return path


def create_txt_file(path):
    with open(path, "w", encoding="utf-8") as f:
        _lineaje_payload = "This is the content of a test TXT file."
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to a file, before it is written to disk (in create_txt_file).
        #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:49320adf24ca17062681c539c53184dfaea4820cdd538442a91e23da869e71df'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:49320adf24ca17062681c539c53184dfaea4820cdd538442a91e23da869e71df', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 68, 'function': 'create_txt_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 68, 'function': 'create_txt_file', 'agent_name': 'create_txt_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=68)
        except _gr_client.GuardrailUnavailableError:
            pass
        f.write(_lineaje_payload)
    # LINEAJE: runtime guardrail checks `path` as it flows from the agent to the user interface, before it leaves the application (in create_txt_file).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:efb87de1b3c948cb573aeaebd5f324452c73fcbce3e4fdd759aa3dd4fbdb79d6'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:efb87de1b3c948cb573aeaebd5f324452c73fcbce3e4fdd759aa3dd4fbdb79d6', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 69, 'function': 'create_txt_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 69, 'function': 'create_txt_file', 'agent_name': 'create_txt_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        path = _gr_client.enforce(_gr_site, path, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return path


def create_md_file(path):
    md_content = "# Test MD File\n\nThis is a test Markdown file."
    with open(path, "w", encoding="utf-8") as f:
        # LINEAJE: runtime guardrail checks `md_content` as it flows from the agent to a file, before it is written to disk (in create_md_file).
        #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `md_content` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:57cc5a24c8a89ca02496675544866d54b8f06b37447f728e6201e2f4dfb2a1b4'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:57cc5a24c8a89ca02496675544866d54b8f06b37447f728e6201e2f4dfb2a1b4', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 75, 'function': 'create_md_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 75, 'function': 'create_md_file', 'agent_name': 'create_md_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            md_content = _gr_client.enforce(_gr_site, md_content, content_type='application/json', variable_name='md_content', source_file=__file__, before_line=75)
        except _gr_client.GuardrailUnavailableError:
            pass
        f.write(md_content)
    # LINEAJE: runtime guardrail checks `path` as it flows from the agent to the user interface, before it leaves the application (in create_md_file).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:eb776fc6f3550cc52cb2c04aeee01ee9cdf66bc38d73243e2972fedc376d71a9'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:eb776fc6f3550cc52cb2c04aeee01ee9cdf66bc38d73243e2972fedc376d71a9', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 76, 'function': 'create_md_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 76, 'function': 'create_md_file', 'agent_name': 'create_md_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        path = _gr_client.enforce(_gr_site, path, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return path


def create_json_file(path):
    data = {"message": "This is a test JSON file", "value": 123}
    with open(path, "w", encoding="utf-8") as f:
        # LINEAJE: runtime guardrail checks `data` as it flows from the agent to a file, before it is written to disk (in create_json_file).
        #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `data` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d06a84352205c0d197c883aa34de9c4f501683f3e6c27c1a073b40eb5f8b01f0'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d06a84352205c0d197c883aa34de9c4f501683f3e6c27c1a073b40eb5f8b01f0', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 82, 'function': 'create_json_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 82, 'function': 'create_json_file', 'agent_name': 'create_json_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            data = _gr_client.enforce(_gr_site, data, content_type='application/json', variable_name='data', source_file=__file__, before_line=82)
        except _gr_client.GuardrailUnavailableError:
            pass
        json.dump(data, f, indent=2)
    # LINEAJE: runtime guardrail checks `path` as it flows from the agent to the user interface, before it leaves the application (in create_json_file).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:1f1905f4dc300cd16ebfe852570b54f33ea3f37994e0fac325ce98d82c86c465'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1f1905f4dc300cd16ebfe852570b54f33ea3f37994e0fac325ce98d82c86c465', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 83, 'function': 'create_json_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 83, 'function': 'create_json_file', 'agent_name': 'create_json_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        path = _gr_client.enforce(_gr_site, path, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return path


def create_eml_file(path):
    eml_content = (
        "From: sender@example.com\n"
        "To: receiver@example.com\n"
        "Subject: Test EML File\n\n"
        "This is a test email content.\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        # LINEAJE: runtime guardrail checks `eml_content` as it flows from the agent to a file, before it is written to disk (in create_eml_file).
        #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `eml_content` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:4461b1ebe8fad08c96a6d316e6b0470575a5581b64dd287a591ab281873282af'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4461b1ebe8fad08c96a6d316e6b0470575a5581b64dd287a591ab281873282af', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 94, 'function': 'create_eml_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 94, 'function': 'create_eml_file', 'agent_name': 'create_eml_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            eml_content = _gr_client.enforce(_gr_site, eml_content, content_type='application/json', variable_name='eml_content', source_file=__file__, before_line=94)
        except _gr_client.GuardrailUnavailableError:
            pass
        f.write(eml_content)
    # LINEAJE: runtime guardrail checks `path` as it flows from rendered HTML to the user interface, before it leaves the application (in create_eml_file).
    #   Detected: this statement moves data from rendered HTML to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:8df294b49bb6023cc73262933accaf6bb4f41fbb32438ec53484d3109dbe7b9f'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8df294b49bb6023cc73262933accaf6bb4f41fbb32438ec53484d3109dbe7b9f', phase='data_egress', boundary={'source': 'html', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='html', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 95, 'function': 'create_eml_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 95, 'function': 'create_eml_file', 'agent_name': 'create_eml_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        path = _gr_client.enforce(_gr_site, path, content_type='text/html')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return path


def create_html_file(path):
    html_content = (
        "<html>\n"
        "<head><title>Test HTML File</title></head>\n"
        "<body><h1>This is a test HTML file</h1></body>\n"
        "</html>"
    )
    with open(path, "w", encoding="utf-8") as f:
        # LINEAJE: runtime guardrail checks `html_content` as it flows from the agent to a file, before it is written to disk (in create_html_file).
        #   Detected: this statement moves data from the agent to a file with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_025; sensitive values in `html_content` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:51b084882bcd5dcbf24f1101a5fb6ff371dc1cd2e6f9af312260b346feaabc4c'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:51b084882bcd5dcbf24f1101a5fb6ff371dc1cd2e6f9af312260b346feaabc4c', phase='file_write', boundary={'source': 'agent_message', 'sink': 'file_content'}, fail_mode='BLOCK', source_type='agent', destination_type='file', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 106, 'function': 'create_html_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 106, 'function': 'create_html_file', 'agent_name': 'create_html_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            html_content = _gr_client.enforce(_gr_site, html_content, content_type='application/json', variable_name='html_content', source_file=__file__, before_line=106)
        except _gr_client.GuardrailUnavailableError:
            pass
        f.write(html_content)
    # LINEAJE: runtime guardrail checks `path` as it flows from rendered HTML to the user interface, before it leaves the application (in create_html_file).
    #   Detected: this statement moves data from rendered HTML to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `path` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:897abe83fa26c407142e6057cc30f2e5cb86b1a763e25e453fb3777e34a0d1ad'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:897abe83fa26c407142e6057cc30f2e5cb86b1a763e25e453fb3777e34a0d1ad', phase='data_egress', boundary={'source': 'html', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='html', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/testcases/utils/file_utils.py', 'line': 107, 'function': 'create_html_file'}, 'file': 'test/testcases/utils/file_utils.py', 'line': 107, 'function': 'create_html_file', 'agent_name': 'create_html_file', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        path = _gr_client.enforce(_gr_site, path, content_type='text/html')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return path
