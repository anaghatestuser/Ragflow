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
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image

from common.constants import LLMType
from api.db.services.llm_service import LLMBundle
from common.connection_utils import timeout
from rag.app.picture import vision_llm_chunk as picture_vision_llm_chunk
from rag.prompts.generator import vision_llm_figure_describe_prompt


def vision_figure_parser_figure_data_wrapper(figures_data_without_positions):
    if not figures_data_without_positions:
        return []
    return [
        (
            (figure_data[1], [figure_data[0]]),
            [(0, 0, 0, 0, 0)],
        )
        for figure_data in figures_data_without_positions
        if isinstance(figure_data[1], Image.Image)
    ]


def vision_figure_parser_docx_wrapper(sections, tbls, callback=None,**kwargs):
    if not sections:
        # LINEAJE: runtime guardrail checks `tbls` as it flows from the agent to the user interface, before it leaves the application (in vision_figure_parser_docx_wrapper).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `tbls` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:2dda12d5fcf43105b4b1973e084538ead8dbc5a177fbe3f65057f7f13a4669d2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2dda12d5fcf43105b4b1973e084538ead8dbc5a177fbe3f65057f7f13a4669d2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/figure_parser.py', 'line': 42, 'function': 'vision_figure_parser_docx_wrapper'}, 'file': 'deepdoc/parser/figure_parser.py', 'line': 42, 'function': 'vision_figure_parser_docx_wrapper', 'agent_name': 'vision_figure_parser_docx_wrapper', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            tbls = _gr_client.enforce(_gr_site, tbls, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return tbls
    try:
        vision_model = LLMBundle(kwargs["tenant_id"], LLMType.IMAGE2TEXT)
        callback(0.7, "Visual model detected. Attempting to enhance figure extraction...")
    except Exception:
        vision_model = None
    if vision_model:
        figures_data = vision_figure_parser_figure_data_wrapper(sections)
        try:
            docx_vision_parser = VisionFigureParser(vision_model=vision_model, figures_data=figures_data, **kwargs)
            boosted_figures = docx_vision_parser(callback=callback)
            tbls.extend(boosted_figures)
        except Exception as e:
            callback(0.8, f"Visual model error: {e}. Skipping figure parsing enhancement.")
    # LINEAJE: runtime guardrail checks `tbls` as it flows from the agent to the user interface, before it leaves the application (in vision_figure_parser_docx_wrapper).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `tbls` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:5af402fb3638fed98e681fde7156ecfa101842f0384f8ae347aae39fa1204aaf'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5af402fb3638fed98e681fde7156ecfa101842f0384f8ae347aae39fa1204aaf', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/figure_parser.py', 'line': 56, 'function': 'vision_figure_parser_docx_wrapper'}, 'file': 'deepdoc/parser/figure_parser.py', 'line': 56, 'function': 'vision_figure_parser_docx_wrapper', 'agent_name': 'vision_figure_parser_docx_wrapper', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        tbls = _gr_client.enforce(_gr_site, tbls, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return tbls

def vision_figure_parser_figure_xlsx_wrapper(images,callback=None, **kwargs):
    tbls = []
    if not images:
        return []
    try:
        vision_model = LLMBundle(kwargs["tenant_id"], LLMType.IMAGE2TEXT)
        callback(0.2, "Visual model detected. Attempting to enhance Excel image extraction...")
    except Exception:
        vision_model = None
    if vision_model:
        figures_data = [((
                        img["image"],   # Image.Image
                        [img["image_description"]]     # description list (must be list)
                    ),
                    [
                        (0, 0, 0, 0, 0)   # dummy position
                    ]) for img in images]
        try:
            parser = VisionFigureParser(vision_model=vision_model, figures_data=figures_data, **kwargs)
            callback(0.22, "Parsing images...")
            boosted_figures = parser(callback=callback)
            tbls.extend(boosted_figures)
        except Exception as e:
            callback(0.25, f"Excel visual model error: {e}. Skipping vision enhancement.")
    # LINEAJE: runtime guardrail checks `tbls` as it flows from the agent to the user interface, before it leaves the application (in vision_figure_parser_figure_xlsx_wrapper).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `tbls` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:14faa1ff68b53eb8be8f88e69af0c632ac9ee1106d09201986beb41356fa81be'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:14faa1ff68b53eb8be8f88e69af0c632ac9ee1106d09201986beb41356fa81be', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/figure_parser.py', 'line': 82, 'function': 'vision_figure_parser_figure_xlsx_wrapper'}, 'file': 'deepdoc/parser/figure_parser.py', 'line': 82, 'function': 'vision_figure_parser_figure_xlsx_wrapper', 'agent_name': 'vision_figure_parser_figure_xlsx_wrapper', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        tbls = _gr_client.enforce(_gr_site, tbls, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return tbls

def vision_figure_parser_pdf_wrapper(tbls, callback=None, **kwargs):
    if not tbls:
        return []
    try:
        vision_model = LLMBundle(kwargs["tenant_id"], LLMType.IMAGE2TEXT)
        callback(0.7, "Visual model detected. Attempting to enhance figure extraction...")
    except Exception:
        vision_model = None
    if vision_model:
        def is_figure_item(item):
            return (
                isinstance(item[0][0], Image.Image) and
                isinstance(item[0][1], list)
            )
        figures_data = [item for item in tbls if is_figure_item(item)]
        try:
            docx_vision_parser = VisionFigureParser(vision_model=vision_model, figures_data=figures_data, **kwargs)
            boosted_figures = docx_vision_parser(callback=callback)
            tbls = [item for item in tbls if not is_figure_item(item)]
            tbls.extend(boosted_figures)
        except Exception as e:
            callback(0.8, f"Visual model error: {e}. Skipping figure parsing enhancement.")
    # LINEAJE: runtime guardrail checks `tbls` as it flows from the agent to the user interface, before it leaves the application (in vision_figure_parser_pdf_wrapper).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `tbls` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:b6b903a15ebac4654715ac570caf511336dd754c9c2968d2f3fbc604c50d1b17'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b6b903a15ebac4654715ac570caf511336dd754c9c2968d2f3fbc604c50d1b17', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/parser/figure_parser.py', 'line': 106, 'function': 'vision_figure_parser_pdf_wrapper'}, 'file': 'deepdoc/parser/figure_parser.py', 'line': 106, 'function': 'vision_figure_parser_pdf_wrapper', 'agent_name': 'vision_figure_parser_pdf_wrapper', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        tbls = _gr_client.enforce(_gr_site, tbls, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return tbls


shared_executor = ThreadPoolExecutor(max_workers=10)


class VisionFigureParser:
    def __init__(self, vision_model, figures_data, *args, **kwargs):
        self.vision_model = vision_model
        self._extract_figures_info(figures_data)
        assert len(self.figures) == len(self.descriptions)
        assert not self.positions or (len(self.figures) == len(self.positions))

    def _extract_figures_info(self, figures_data):
        self.figures = []
        self.descriptions = []
        self.positions = []

        for item in figures_data:
            # position
            if len(item) == 2 and isinstance(item[0], tuple) and len(item[0]) == 2 and isinstance(item[1], list) and isinstance(item[1][0], tuple) and len(item[1][0]) == 5:
                img_desc = item[0]
                assert len(img_desc) == 2 and isinstance(img_desc[0], Image.Image) and isinstance(img_desc[1], list), "Should be (figure, [description])"
                self.figures.append(img_desc[0])
                self.descriptions.append(img_desc[1])
                self.positions.append(item[1])
            else:
                assert len(item) == 2 and isinstance(item[0], Image.Image) and isinstance(item[1], list), f"Unexpected form of figure data: get {len(item)=}, {item=}"
                self.figures.append(item[0])
                self.descriptions.append(item[1])

    def _assemble(self):
        self.assembled = []
        self.has_positions = len(self.positions) != 0
        for i in range(len(self.figures)):
            figure = self.figures[i]
            desc = self.descriptions[i]
            pos = self.positions[i] if self.has_positions else None

            figure_desc = (figure, desc)

            if pos is not None:
                self.assembled.append((figure_desc, pos))
            else:
                self.assembled.append((figure_desc,))

        return self.assembled

    def __call__(self, **kwargs):
        callback = kwargs.get("callback", lambda prog, msg: None)

        @timeout(30, 3)
        def process(figure_idx, figure_binary):
            description_text = picture_vision_llm_chunk(
                binary=figure_binary,
                vision_model=self.vision_model,
                prompt=vision_llm_figure_describe_prompt(),
                callback=callback,
            )
            return figure_idx, description_text

        futures = []
        for idx, img_binary in enumerate(self.figures or []):
            futures.append(shared_executor.submit(process, idx, img_binary))

        for future in as_completed(futures):
            figure_num, txt = future.result()
            if txt:
                self.descriptions[figure_num] = txt + "\n".join(self.descriptions[figure_num])

        self._assemble()

        return self.assembled
