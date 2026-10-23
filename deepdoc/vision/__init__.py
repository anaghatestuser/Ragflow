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
import io
import sys
import threading

import pdfplumber

from .ocr import OCR
from .recognizer import Recognizer
from .layout_recognizer import AscendLayoutRecognizer
from .layout_recognizer import LayoutRecognizer4YOLOv10 as LayoutRecognizer
from .table_structure_recognizer import TableStructureRecognizer

LOCK_KEY_pdfplumber = "global_shared_lock_pdfplumber"
if LOCK_KEY_pdfplumber not in sys.modules:
    sys.modules[LOCK_KEY_pdfplumber] = threading.Lock()


def init_in_out(args):
    import os
    import traceback

    from PIL import Image

    from common.file_utils import traversal_files

    images = []
    outputs = []

    if not os.path.exists(args.output_dir):
        os.mkdir(args.output_dir)

    def pdf_pages(fnm, zoomin=3):
        nonlocal outputs, images
        with sys.modules[LOCK_KEY_pdfplumber]:
            pdf = pdfplumber.open(fnm)
            images = [p.to_image(resolution=72 * zoomin).annotated for i, p in enumerate(pdf.pages)]

        for i, page in enumerate(images):
            outputs.append(os.path.split(fnm)[-1] + f"_{i}.jpg")
        pdf.close()

    def images_and_outputs(fnm):
        nonlocal outputs, images
        if fnm.split(".")[-1].lower() == "pdf":
            pdf_pages(fnm)
            return
        try:
            fp = open(fnm, "rb")
            # LINEAJE: runtime guardrail checks `fp` as it flows from file storage to the agent (in images_and_outputs).
            #   Detected: this statement moves data from file storage to the agent with no runtime policy check (detection confidence: medium).
            #   Decision: the Guardrail evaluates AI_APP_SEC_070, AI_DAT_SEC_023, AI_DAT_SEC_024; sensitive values in `fp` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:40d8d2a3497e7eb620db0129b0b9d4b8929a66ec64fffc87277a81e0279d7b02'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:40d8d2a3497e7eb620db0129b0b9d4b8929a66ec64fffc87277a81e0279d7b02', phase='file_upload', boundary={'source': 'file_upload', 'sink': 'agent_context'}, fail_mode='BLOCK', source_type='file_storage', destination_type='agent', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/vision/__init__.py', 'line': 63, 'function': 'init_in_out.images_and_outputs'}, 'file': 'deepdoc/vision/__init__.py', 'line': 63, 'function': 'images_and_outputs', 'agent_name': 'images_and_outputs', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                fp = _gr_client.enforce(_gr_site, fp, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                raise
            binary = fp.read()
            fp.close()
            images.append(Image.open(io.BytesIO(binary)).convert("RGB"))
            outputs.append(os.path.split(fnm)[-1])
        except Exception:
            traceback.print_exc()

    if os.path.isdir(args.inputs):
        for fnm in traversal_files(args.inputs):
            images_and_outputs(fnm)
    else:
        images_and_outputs(args.inputs)

    for i in range(len(outputs)):
        outputs[i] = os.path.join(args.output_dir, outputs[i])

    return images, outputs


__all__ = [
    "OCR",
    "Recognizer",
    "LayoutRecognizer",
    "AscendLayoutRecognizer",
    "TableStructureRecognizer",
    "init_in_out",
]
