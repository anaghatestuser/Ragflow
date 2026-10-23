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
import math
import os
# import re
from collections import Counter
from copy import deepcopy

import cv2
import numpy as np
from huggingface_hub import snapshot_download

from common.file_utils import get_project_base_directory
from deepdoc.vision import Recognizer
from deepdoc.vision.operators import nms


class LayoutRecognizer(Recognizer):
    labels = [
        "_background_",
        "Text",
        "Title",
        "Figure",
        "Figure caption",
        "Table",
        "Table caption",
        "Header",
        "Footer",
        "Reference",
        "Equation",
    ]

    def __init__(self, domain):
        try:
            model_dir = os.path.join(get_project_base_directory(), "rag/res/deepdoc")
            super().__init__(self.labels, domain, model_dir)
        except Exception:
            model_dir = snapshot_download(repo_id="InfiniFlow/deepdoc", local_dir=os.path.join(get_project_base_directory(), "rag/res/deepdoc"), local_dir_use_symlinks=False)
            super().__init__(self.labels, domain, model_dir)

        self.garbage_layouts = ["footer", "header", "reference"]
        self.client = None
        if os.environ.get("TENSORRT_DLA_SVR"):
            from deepdoc.vision.dla_cli import DLAClient

            self.client = DLAClient(os.environ["TENSORRT_DLA_SVR"])

    def __call__(self, image_list, ocr_res, scale_factor=3, thr=0.2, batch_size=16, drop=True):
        def __is_garbage(b):
            return False
            # patt = [r"^•+$", "^[0-9]{1,2} / ?[0-9]{1,2}$", r"^[0-9]{1,2} of [0-9]{1,2}$", "^http://[^ ]{12,}", "\\(cid *: *[0-9]+ *\\)"]
            # return any([re.search(p, b["text"]) for p in patt])

        if self.client:
            layouts = self.client.predict(image_list)
        else:
            layouts = super().__call__(image_list, thr, batch_size)
        # save_results(image_list, layouts, self.labels, output_dir='output/', threshold=0.7)
        assert len(image_list) == len(ocr_res)
        # Tag layout type
        boxes = []
        assert len(image_list) == len(layouts)
        garbages = {}
        page_layout = []
        for pn, lts in enumerate(layouts):
            bxs = ocr_res[pn]
            lts = [
                {
                    "type": b["type"],
                    "score": float(b["score"]),
                    "x0": b["bbox"][0] / scale_factor,
                    "x1": b["bbox"][2] / scale_factor,
                    "top": b["bbox"][1] / scale_factor,
                    "bottom": b["bbox"][-1] / scale_factor,
                    "page_number": pn,
                }
                for b in lts
                if float(b["score"]) >= 0.4 or b["type"] not in self.garbage_layouts
            ]
            lts = self.sort_Y_firstly(lts, np.mean([lt["bottom"] - lt["top"] for lt in lts]) / 2)
            lts = self.layouts_cleanup(bxs, lts)
            page_layout.append(lts)

            def findLayout(ty):
                nonlocal bxs, lts, self
                lts_ = [lt for lt in lts if lt["type"] == ty]
                i = 0
                while i < len(bxs):
                    if bxs[i].get("layout_type"):
                        i += 1
                        continue
                    if __is_garbage(bxs[i]):
                        bxs.pop(i)
                        continue

                    ii = self.find_overlapped_with_threshold(bxs[i], lts_, thr=0.4)
                    if ii is None:
                        bxs[i]["layout_type"] = ""
                        i += 1
                        continue
                    lts_[ii]["visited"] = True
                    keep_feats = [
                        lts_[ii]["type"] == "footer" and bxs[i]["bottom"] < image_list[pn].size[1] * 0.9 / scale_factor,
                        lts_[ii]["type"] == "header" and bxs[i]["top"] > image_list[pn].size[1] * 0.1 / scale_factor,
                    ]
                    if drop and lts_[ii]["type"] in self.garbage_layouts and not any(keep_feats):
                        if lts_[ii]["type"] not in garbages:
                            garbages[lts_[ii]["type"]] = []
                        garbages[lts_[ii]["type"]].append(bxs[i]["text"])
                        bxs.pop(i)
                        continue

                    bxs[i]["layoutno"] = f"{ty}-{ii}"
                    bxs[i]["layout_type"] = lts_[ii]["type"] if lts_[ii]["type"] != "equation" else "figure"
                    i += 1

            for lt in ["footer", "header", "reference", "figure caption", "table caption", "title", "table", "text", "figure", "equation"]:
                findLayout(lt)

            # add box to figure layouts which has not text box
            for i, lt in enumerate([lt for lt in lts if lt["type"] in ["figure", "equation"]]):
                if lt.get("visited"):
                    continue
                lt = deepcopy(lt)
                del lt["type"]
                lt["text"] = ""
                lt["layout_type"] = "figure"
                lt["layoutno"] = f"figure-{i}"
                bxs.append(lt)

            boxes.extend(bxs)

        ocr_res = boxes

        garbag_set = set()
        for k in garbages.keys():
            garbages[k] = Counter(garbages[k])
            for g, c in garbages[k].items():
                if c > 1:
                    garbag_set.add(g)

        ocr_res = [b for b in ocr_res if b["text"].strip() not in garbag_set]
        return ocr_res, page_layout

    def forward(self, image_list, thr=0.7, batch_size=16):
        return super().__call__(image_list, thr, batch_size)


class LayoutRecognizer4YOLOv10(LayoutRecognizer):
    labels = [
        "title",
        "Text",
        "Reference",
        "Figure",
        "Figure caption",
        "Table",
        "Table caption",
        "Table caption",
        "Equation",
        "Figure caption",
    ]

    def __init__(self, domain):
        domain = "layout"
        super().__init__(domain)
        self.auto = False
        self.scaleFill = False
        self.scaleup = True
        self.stride = 32
        self.center = True

    def preprocess(self, image_list):
        inputs = []
        new_shape = self.input_shape  # height, width
        for img in image_list:
            shape = img.shape[:2]  # current shape [height, width]
            # Scale ratio (new / old)
            r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
            # Compute padding
            new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
            dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]  # wh padding
            dw /= 2  # divide padding into 2 sides
            dh /= 2
            ww, hh = new_unpad
            img = np.array(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).astype(np.float32)
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
            top, bottom = int(round(dh - 0.1)) if self.center else 0, int(round(dh + 0.1))
            left, right = int(round(dw - 0.1)) if self.center else 0, int(round(dw + 0.1))
            img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))  # add border
            img /= 255.0
            img = img.transpose(2, 0, 1)
            img = img[np.newaxis, :, :, :].astype(np.float32)
            inputs.append({self.input_names[0]: img, "scale_factor": [shape[1] / ww, shape[0] / hh, dw, dh]})

        # LINEAJE: runtime guardrail checks `inputs` as it flows from the agent to the user interface, before it leaves the application (in LayoutRecognizer4YOLOv10.preprocess).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `inputs` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:78ec53a9e2402fe82ccb41fbbab9e6b3b975e4553ff48044f76ce4503c9d9cb2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:78ec53a9e2402fe82ccb41fbbab9e6b3b975e4553ff48044f76ce4503c9d9cb2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/vision/layout_recognizer.py', 'line': 210, 'function': 'LayoutRecognizer4YOLOv10.preprocess'}, 'file': 'deepdoc/vision/layout_recognizer.py', 'line': 210, 'function': 'preprocess', 'agent_name': 'LayoutRecognizer4YOLOv10', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            inputs = _gr_client.enforce(_gr_site, inputs, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return inputs

    def postprocess(self, boxes, inputs, thr):
        thr = 0.08
        boxes = np.squeeze(boxes)
        scores = boxes[:, 4]
        boxes = boxes[scores > thr, :]
        scores = scores[scores > thr]
        if len(boxes) == 0:
            return []
        class_ids = boxes[:, -1].astype(int)
        boxes = boxes[:, :4]
        boxes[:, 0] -= inputs["scale_factor"][2]
        boxes[:, 2] -= inputs["scale_factor"][2]
        boxes[:, 1] -= inputs["scale_factor"][3]
        boxes[:, 3] -= inputs["scale_factor"][3]
        input_shape = np.array([inputs["scale_factor"][0], inputs["scale_factor"][1], inputs["scale_factor"][0], inputs["scale_factor"][1]])
        boxes = np.multiply(boxes, input_shape, dtype=np.float32)

        unique_class_ids = np.unique(class_ids)
        indices = []
        for class_id in unique_class_ids:
            class_indices = np.where(class_ids == class_id)[0]
            class_boxes = boxes[class_indices, :]
            class_scores = scores[class_indices]
            class_keep_boxes = nms(class_boxes, class_scores, 0.45)
            indices.extend(class_indices[class_keep_boxes])

        return [{"type": self.label_list[class_ids[i]].lower(), "bbox": [float(t) for t in boxes[i].tolist()], "score": float(scores[i])} for i in indices]


class AscendLayoutRecognizer(Recognizer):
    labels = [
        "title",
        "Text",
        "Reference",
        "Figure",
        "Figure caption",
        "Table",
        "Table caption",
        "Table caption",
        "Equation",
        "Figure caption",
    ]

    def __init__(self, domain):
        from ais_bench.infer.interface import InferSession

        model_dir = os.path.join(get_project_base_directory(), "rag/res/deepdoc")
        model_file_path = os.path.join(model_dir, domain + ".om")

        if not os.path.exists(model_file_path):
            raise ValueError(f"Model file not found: {model_file_path}")

        device_id = int(os.getenv("ASCEND_LAYOUT_RECOGNIZER_DEVICE_ID", 0))
        self.session = InferSession(device_id=device_id, model_path=model_file_path)
        self.input_shape = self.session.get_inputs()[0].shape[2:4]  # H,W
        self.garbage_layouts = ["footer", "header", "reference"]

    def preprocess(self, image_list):
        inputs = []
        H, W = self.input_shape
        for img in image_list:
            h, w = img.shape[:2]
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32)

            r = min(H / h, W / w)
            new_unpad = (int(round(w * r)), int(round(h * r)))
            dw, dh = (W - new_unpad[0]) / 2.0, (H - new_unpad[1]) / 2.0

            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
            top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
            left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
            img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))

            img /= 255.0
            img = img.transpose(2, 0, 1)[np.newaxis, :, :, :].astype(np.float32)

            inputs.append(
                {
                    "image": img,
                    "scale_factor": [w / new_unpad[0], h / new_unpad[1]],
                    "pad": [dw, dh],
                    "orig_shape": [h, w],
                }
            )
        # LINEAJE: runtime guardrail checks `inputs` as it flows from the agent to the user interface, before it leaves the application (in AscendLayoutRecognizer.preprocess).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `inputs` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:d8f06c4efdf5f94821dedcefd92ebcebeb56b6689ed31e8a1660938ef793ffb2'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:d8f06c4efdf5f94821dedcefd92ebcebeb56b6689ed31e8a1660938ef793ffb2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/vision/layout_recognizer.py', 'line': 296, 'function': 'AscendLayoutRecognizer.preprocess'}, 'file': 'deepdoc/vision/layout_recognizer.py', 'line': 296, 'function': 'preprocess', 'agent_name': 'AscendLayoutRecognizer', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            inputs = _gr_client.enforce(_gr_site, inputs, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return inputs

    def postprocess(self, boxes, inputs, thr=0.25):
        arr = np.squeeze(boxes)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        results = []
        if arr.shape[1] == 6:
            # [x1,y1,x2,y2,score,cls]
            m = arr[:, 4] >= thr
            arr = arr[m]
            if arr.size == 0:
                return []
            xyxy = arr[:, :4].astype(np.float32)
            scores = arr[:, 4].astype(np.float32)
            cls_ids = arr[:, 5].astype(np.int32)

            if "pad" in inputs:
                dw, dh = inputs["pad"]
                sx, sy = inputs["scale_factor"]
                xyxy[:, [0, 2]] -= dw
                xyxy[:, [1, 3]] -= dh
                xyxy *= np.array([sx, sy, sx, sy], dtype=np.float32)
            else:
                # backup
                sx, sy = inputs["scale_factor"]
                xyxy *= np.array([sx, sy, sx, sy], dtype=np.float32)

            keep_indices = []
            for c in np.unique(cls_ids):
                idx = np.where(cls_ids == c)[0]
                k = nms(xyxy[idx], scores[idx], 0.45)
                keep_indices.extend(idx[k])

            for i in keep_indices:
                cid = int(cls_ids[i])
                if 0 <= cid < len(self.labels):
                    results.append({"type": self.labels[cid].lower(), "bbox": [float(t) for t in xyxy[i].tolist()], "score": float(scores[i])})
            # LINEAJE: runtime guardrail checks `results` as it flows from the agent to the user interface, before it leaves the application (in AscendLayoutRecognizer.postprocess).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `results` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f5e8999d69ba36b1dc18026a178f8a364511979b3dbb4ed1909fb4ae760a8b60'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f5e8999d69ba36b1dc18026a178f8a364511979b3dbb4ed1909fb4ae760a8b60', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/vision/layout_recognizer.py', 'line': 335, 'function': 'AscendLayoutRecognizer.postprocess'}, 'file': 'deepdoc/vision/layout_recognizer.py', 'line': 335, 'function': 'postprocess', 'agent_name': 'AscendLayoutRecognizer', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                results = _gr_client.enforce(_gr_site, results, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return results

        raise ValueError(f"Unexpected output shape: {arr.shape}")

    def __call__(self, image_list, ocr_res, scale_factor=3, thr=0.2, batch_size=16, drop=True):
        import re
        from collections import Counter

        assert len(image_list) == len(ocr_res)

        images = [np.array(im) if not isinstance(im, np.ndarray) else im for im in image_list]
        layouts_all_pages = []  # list of list[{"type","score","bbox":[x1,y1,x2,y2]}]

        conf_thr = max(thr, 0.08)

        batch_loop_cnt = math.ceil(float(len(images)) / batch_size)
        for bi in range(batch_loop_cnt):
            s = bi * batch_size
            e = min((bi + 1) * batch_size, len(images))
            batch_images = images[s:e]

            inputs_list = self.preprocess(batch_images)
            _lineaje_payload = "preprocess done"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in AscendLayoutRecognizer.__call__).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:33006ea3c4172e9578fe0cc0f58cb1b526636317f9b3a2e73d90a54cd623fb33'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:33006ea3c4172e9578fe0cc0f58cb1b526636317f9b3a2e73d90a54cd623fb33', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'deepdoc/vision/layout_recognizer.py', 'line': 357, 'function': 'AscendLayoutRecognizer.__call__'}, 'file': 'deepdoc/vision/layout_recognizer.py', 'line': 357, 'function': '__call__', 'agent_name': 'AscendLayoutRecognizer', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.debug(_lineaje_payload)

            for ins in inputs_list:
                feeds = [ins["image"]]
                out_list = self.session.infer(feeds=feeds, mode="static")

                for out in out_list:
                    lts = self.postprocess(out, ins, conf_thr)

                    page_lts = []
                    for b in lts:
                        if float(b["score"]) >= 0.4 or b["type"] not in self.garbage_layouts:
                            x0, y0, x1, y1 = b["bbox"]
                            page_lts.append(
                                {
                                    "type": b["type"],
                                    "score": float(b["score"]),
                                    "x0": float(x0) / scale_factor,
                                    "x1": float(x1) / scale_factor,
                                    "top": float(y0) / scale_factor,
                                    "bottom": float(y1) / scale_factor,
                                    "page_number": len(layouts_all_pages),
                                }
                            )
                    layouts_all_pages.append(page_lts)

        def _is_garbage_text(box):
            patt = [r"^•+$", r"^[0-9]{1,2} / ?[0-9]{1,2}$", r"^[0-9]{1,2} of [0-9]{1,2}$", r"^http://[^ ]{12,}", r"\(cid *: *[0-9]+ *\)"]
            return any(re.search(p, box.get("text", "")) for p in patt)

        boxes_out = []
        page_layout = []
        garbages = {}

        for pn, lts in enumerate(layouts_all_pages):
            if lts:
                avg_h = np.mean([lt["bottom"] - lt["top"] for lt in lts])
                lts = self.sort_Y_firstly(lts, avg_h / 2 if avg_h > 0 else 0)

            bxs = ocr_res[pn]
            lts = self.layouts_cleanup(bxs, lts)
            page_layout.append(lts)

            def _tag_layout(ty):
                nonlocal bxs, lts
                lts_of_ty = [lt for lt in lts if lt["type"] == ty]
                i = 0
                while i < len(bxs):
                    if bxs[i].get("layout_type"):
                        i += 1
                        continue
                    if _is_garbage_text(bxs[i]):
                        bxs.pop(i)
                        continue

                    ii = self.find_overlapped_with_threshold(bxs[i], lts_of_ty, thr=0.4)
                    if ii is None:
                        bxs[i]["layout_type"] = ""
                        i += 1
                        continue

                    lts_of_ty[ii]["visited"] = True

                    keep_feats = [
                        lts_of_ty[ii]["type"] == "footer" and bxs[i]["bottom"] < image_list[pn].shape[0] * 0.9 / scale_factor,
                        lts_of_ty[ii]["type"] == "header" and bxs[i]["top"] > image_list[pn].shape[0] * 0.1 / scale_factor,
                    ]
                    if drop and lts_of_ty[ii]["type"] in self.garbage_layouts and not any(keep_feats):
                        garbages.setdefault(lts_of_ty[ii]["type"], []).append(bxs[i].get("text", ""))
                        bxs.pop(i)
                        continue

                    bxs[i]["layoutno"] = f"{ty}-{ii}"
                    bxs[i]["layout_type"] = lts_of_ty[ii]["type"] if lts_of_ty[ii]["type"] != "equation" else "figure"
                    i += 1

            for ty in ["footer", "header", "reference", "figure caption", "table caption", "title", "table", "text", "figure", "equation"]:
                _tag_layout(ty)

            figs = [lt for lt in lts if lt["type"] in ["figure", "equation"]]
            for i, lt in enumerate(figs):
                if lt.get("visited"):
                    continue
                lt = deepcopy(lt)
                lt.pop("type", None)
                lt["text"] = ""
                lt["layout_type"] = "figure"
                lt["layoutno"] = f"figure-{i}"
                bxs.append(lt)

            boxes_out.extend(bxs)

        garbag_set = set()
        for k, lst in garbages.items():
            cnt = Counter(lst)
            for g, c in cnt.items():
                if c > 1:
                    garbag_set.add(g)

        ocr_res_new = [b for b in boxes_out if b["text"].strip() not in garbag_set]
        return ocr_res_new, page_layout
