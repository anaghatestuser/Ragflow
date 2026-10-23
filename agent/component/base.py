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
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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

import asyncio
import re
import time
from abc import ABC
import builtins
import json
import os
import logging
from typing import Any, List, Union
import pandas as pd
from agent import settings
from common.connection_utils import timeout

_FEEDED_DEPRECATED_PARAMS = "_feeded_deprecated_params"
_DEPRECATED_PARAMS = "_deprecated_params"
_USER_FEEDED_PARAMS = "_user_feeded_params"
_IS_RAW_CONF = "_is_raw_conf"


class ComponentParamBase(ABC):
    def __init__(self):
        self.message_history_window_size = 13
        self.inputs = {}
        self.outputs = {}
        self.description = ""
        self.max_retries = 0
        self.delay_after_error = 2.0
        self.exception_method = None
        self.exception_default_value = None
        self.exception_goto = None
        self.debug_inputs = {}

    def set_name(self, name: str):
        self._name = name
        return self

    def check(self):
        raise NotImplementedError("Parameter Object should be checked.")

    @classmethod
    def _get_or_init_deprecated_params_set(cls):
        if not hasattr(cls, _DEPRECATED_PARAMS):
            setattr(cls, _DEPRECATED_PARAMS, set())
        return getattr(cls, _DEPRECATED_PARAMS)

    def _get_or_init_feeded_deprecated_params_set(self, conf=None):
        if not hasattr(self, _FEEDED_DEPRECATED_PARAMS):
            if conf is None:
                setattr(self, _FEEDED_DEPRECATED_PARAMS, set())
            else:
                setattr(
                    self,
                    _FEEDED_DEPRECATED_PARAMS,
                    set(conf[_FEEDED_DEPRECATED_PARAMS]),
                )
        return getattr(self, _FEEDED_DEPRECATED_PARAMS)

    def _get_or_init_user_feeded_params_set(self, conf=None):
        if not hasattr(self, _USER_FEEDED_PARAMS):
            if conf is None:
                setattr(self, _USER_FEEDED_PARAMS, set())
            else:
                setattr(self, _USER_FEEDED_PARAMS, set(conf[_USER_FEEDED_PARAMS]))
        return getattr(self, _USER_FEEDED_PARAMS)

    def get_user_feeded(self):
        return self._get_or_init_user_feeded_params_set()

    def get_feeded_deprecated_params(self):
        return self._get_or_init_feeded_deprecated_params_set()

    @property
    def _deprecated_params_set(self):
        return {name: True for name in self.get_feeded_deprecated_params()}

    def __str__(self):
        _lineaje_payload = self.as_dict()
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to an external endpoint, before it leaves the application (in ComponentParamBase.__str__).
        #   Detected: this statement moves data from the agent to an external endpoint with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `_lineaje_payload` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:a85737b3c25d2719d50186b695a23f8d807d01432e8f4c8157b94f4bd3f15c4e'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:a85737b3c25d2719d50186b695a23f8d807d01432e8f4c8157b94f4bd3f15c4e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'external_endpoint'}, fail_mode='ALLOW_WITH_AUDIT', source_type='agent', destination_type='external', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 93, 'function': 'ComponentParamBase.__str__'}, 'file': 'agent/component/base.py', 'line': 93, 'function': '__str__', 'agent_name': 'ComponentParamBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json', variable_name='_lineaje_payload', source_file=__file__, before_line=93)
        except _gr_client.GuardrailUnavailableError:
            pass
        return json.dumps(_lineaje_payload, ensure_ascii=False)

    def as_dict(self):
        def _recursive_convert_obj_to_dict(obj):
            ret_dict = {}
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, dict) or (v and type(v).__name__ not in dir(builtins)):
                        ret_dict[k] = _recursive_convert_obj_to_dict(v)
                    else:
                        ret_dict[k] = v
                # LINEAJE: runtime guardrail checks `ret_dict` as it flows from the agent to the user interface, before it leaves the application (in ComponentParamBase._recursive_convert_obj_to_dict).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `ret_dict` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:b8bd92afa680ec1d787081dc3a76b94c43d15e6a32ebab5500edb89169a20607'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b8bd92afa680ec1d787081dc3a76b94c43d15e6a32ebab5500edb89169a20607', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 104, 'function': 'ComponentParamBase.as_dict._recursive_convert_obj_to_dict'}, 'file': 'agent/component/base.py', 'line': 104, 'function': '_recursive_convert_obj_to_dict', 'agent_name': 'ComponentParamBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    ret_dict = _gr_client.enforce(_gr_site, ret_dict, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return ret_dict

            for attr_name in list(obj.__dict__):
                if attr_name in [_FEEDED_DEPRECATED_PARAMS, _DEPRECATED_PARAMS, _USER_FEEDED_PARAMS, _IS_RAW_CONF]:
                    continue
                # get attr
                attr = getattr(obj, attr_name)
                if isinstance(attr, pd.DataFrame):
                    ret_dict[attr_name] = attr.to_dict()
                    continue
                if isinstance(attr, dict) or (attr and type(attr).__name__ not in dir(builtins)):
                    ret_dict[attr_name] = _recursive_convert_obj_to_dict(attr)
                else:
                    ret_dict[attr_name] = attr

            # LINEAJE: runtime guardrail checks `ret_dict` as it flows from the agent to the user interface, before it leaves the application (in ComponentParamBase._recursive_convert_obj_to_dict).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `ret_dict` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:4ef32f0eafeb94e45083ff2004a3b60452415a1b59a982ff2e03d8a859598cde'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4ef32f0eafeb94e45083ff2004a3b60452415a1b59a982ff2e03d8a859598cde', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 119, 'function': 'ComponentParamBase.as_dict._recursive_convert_obj_to_dict'}, 'file': 'agent/component/base.py', 'line': 119, 'function': '_recursive_convert_obj_to_dict', 'agent_name': 'ComponentParamBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                ret_dict = _gr_client.enforce(_gr_site, ret_dict, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return ret_dict

        return _recursive_convert_obj_to_dict(self)

    def update(self, conf, allow_redundant=False):
        update_from_raw_conf = conf.get(_IS_RAW_CONF, True)
        if update_from_raw_conf:
            deprecated_params_set = self._get_or_init_deprecated_params_set()
            feeded_deprecated_params_set = (
                self._get_or_init_feeded_deprecated_params_set()
            )
            user_feeded_params_set = self._get_or_init_user_feeded_params_set()
            setattr(self, _IS_RAW_CONF, False)
        else:
            feeded_deprecated_params_set = (
                self._get_or_init_feeded_deprecated_params_set(conf)
            )
            user_feeded_params_set = self._get_or_init_user_feeded_params_set(conf)

        def _recursive_update_param(param, config, depth, prefix):
            if depth > settings.PARAM_MAXDEPTH:
                raise ValueError("Param define nesting too deep!!!, can not parse it")

            inst_variables = param.__dict__
            redundant_attrs = []
            for config_key, config_value in config.items():
                # redundant attr
                if config_key not in inst_variables:
                    if not update_from_raw_conf and config_key.startswith("_"):
                        setattr(param, config_key, config_value)
                    else:
                        setattr(param, config_key, config_value)
                        # redundant_attrs.append(config_key)
                    continue

                full_config_key = f"{prefix}{config_key}"

                if update_from_raw_conf:
                    # add user feeded params
                    user_feeded_params_set.add(full_config_key)

                    # update user feeded deprecated param set
                    if full_config_key in deprecated_params_set:
                        feeded_deprecated_params_set.add(full_config_key)

                # supported attr
                attr = getattr(param, config_key)
                if type(attr).__name__ in dir(builtins) or attr is None:
                    setattr(param, config_key, config_value)

                else:
                    # recursive set obj attr
                    sub_params = _recursive_update_param(
                        attr, config_value, depth + 1, prefix=f"{prefix}{config_key}."
                    )
                    setattr(param, config_key, sub_params)

            if not allow_redundant and redundant_attrs:
                raise ValueError(
                    f"cpn `{getattr(self, '_name', type(self))}` has redundant parameters: `{[redundant_attrs]}`"
                )

            # LINEAJE: runtime guardrail checks `param` as it flows from the agent to the user interface, before it leaves the application (in ComponentParamBase._recursive_update_param).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `param` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:ffd0d7a44bd3c757a5ce8434f4455f4207b10d4da44fd5f099c1b799cac0fd82'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ffd0d7a44bd3c757a5ce8434f4455f4207b10d4da44fd5f099c1b799cac0fd82', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 181, 'function': 'ComponentParamBase.update._recursive_update_param'}, 'file': 'agent/component/base.py', 'line': 181, 'function': '_recursive_update_param', 'agent_name': 'ComponentParamBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                param = _gr_client.enforce(_gr_site, param, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return param

        return _recursive_update_param(param=self, config=conf, depth=0, prefix="")

    def extract_not_builtin(self):
        def _get_not_builtin_types(obj):
            ret_dict = {}
            for variable in obj.__dict__:
                attr = getattr(obj, variable)
                if attr and type(attr).__name__ not in dir(builtins):
                    ret_dict[variable] = _get_not_builtin_types(attr)

            # LINEAJE: runtime guardrail checks `ret_dict` as it flows from the agent to the user interface, before it leaves the application (in ComponentParamBase._get_not_builtin_types).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `ret_dict` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:83cca40cefde378464b5f3a8666e1b23a6ae75cbae4bda134ae0b04742908510'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:83cca40cefde378464b5f3a8666e1b23a6ae75cbae4bda134ae0b04742908510', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 193, 'function': 'ComponentParamBase.extract_not_builtin._get_not_builtin_types'}, 'file': 'agent/component/base.py', 'line': 193, 'function': '_get_not_builtin_types', 'agent_name': 'ComponentParamBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                ret_dict = _gr_client.enforce(_gr_site, ret_dict, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return ret_dict

        return _get_not_builtin_types(self)

    def validate(self):
        self.builtin_types = dir(builtins)
        self.func = {
            "ge": self._greater_equal_than,
            "le": self._less_equal_than,
            "in": self._in,
            "not_in": self._not_in,
            "range": self._range,
        }
        home_dir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
        param_validation_path_prefix = home_dir + "/param_validation/"

        param_name = type(self).__name__
        param_validation_path = "/".join(
            [param_validation_path_prefix, param_name + ".json"]
        )

        validation_json = None

        try:
            with open(param_validation_path, "r") as fin:
                validation_json = json.loads(fin.read())
        except BaseException:
            return

        self._validate_param(self, validation_json)

    def _validate_param(self, param_obj, validation_json):
        default_section = type(param_obj).__name__
        var_list = param_obj.__dict__

        for variable in var_list:
            attr = getattr(param_obj, variable)

            if type(attr).__name__ in self.builtin_types or attr is None:
                if variable not in validation_json:
                    continue

                validation_dict = validation_json[default_section][variable]
                value = getattr(param_obj, variable)
                value_legal = False

                for op_type in validation_dict:
                    if self.func[op_type](value, validation_dict[op_type]):
                        value_legal = True
                        break

                if not value_legal:
                    raise ValueError(
                        "Please check runtime conf, {} = {} does not match user-parameter restriction".format(
                            variable, value
                        )
                    )

            elif variable in validation_json:
                self._validate_param(attr, validation_json)

    @staticmethod
    def check_string(param, description):
        if type(param).__name__ not in ["str"]:
            raise ValueError(description + " {} not supported, should be string type".format(param))

    @staticmethod
    def check_empty(param, description):
        if not param:
            raise ValueError(description + " does not support empty value.")

    @staticmethod
    def check_positive_integer(param, description):
        if type(param).__name__ not in ["int", "long"] or param <= 0:
            raise ValueError(description + " {} not supported, should be positive integer".format(param))

    @staticmethod
    def check_positive_number(param, description):
        if type(param).__name__ not in ["float", "int", "long"] or param <= 0:
            raise ValueError(description + " {} not supported, should be positive numeric".format(param))

    @staticmethod
    def check_nonnegative_number(param, description):
        if type(param).__name__ not in ["float", "int", "long"] or param < 0:
            raise ValueError(description + " {} not supported, should be non-negative numeric".format(param))

    @staticmethod
    def check_decimal_float(param, description):
        if type(param).__name__ not in ["float", "int"] or param < 0 or param > 1:
            raise ValueError(description + " {} not supported, should be a float number in range [0, 1]".format(param))

    @staticmethod
    def check_boolean(param, description):
        if type(param).__name__ != "bool":
            raise ValueError(description + " {} not supported, should be bool type".format(param))

    @staticmethod
    def check_open_unit_interval(param, description):
        if type(param).__name__ not in ["float"] or param <= 0 or param >= 1:
            raise ValueError(description + " should be a numeric number between 0 and 1 exclusively")

    @staticmethod
    def check_valid_value(param, description, valid_values):
        if param not in valid_values:
            raise ValueError(description + " {} is not supported, it should be in {}".format(param, valid_values))

    @staticmethod
    def check_defined_type(param, description, types):
        if type(param).__name__ not in types:
            raise ValueError(description + " {} not supported, should be one of {}".format(param, types))

    @staticmethod
    def check_and_change_lower(param, valid_list, description=""):
        if type(param).__name__ != "str":
            raise ValueError(description + " {} not supported, should be one of {}".format(param, valid_list))

        lower_param = param.lower()
        if lower_param in valid_list:
            # LINEAJE: runtime guardrail checks `lower_param` as it flows from the agent to the user interface, before it leaves the application (in ComponentParamBase.check_and_change_lower).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `lower_param` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:274d022b210f68a4f93a922b6a71105d78da7c07d7c9e87448e173bdf29319d2'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:274d022b210f68a4f93a922b6a71105d78da7c07d7c9e87448e173bdf29319d2', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 311, 'function': 'ComponentParamBase.check_and_change_lower'}, 'file': 'agent/component/base.py', 'line': 311, 'function': 'check_and_change_lower', 'agent_name': 'ComponentParamBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                lower_param = _gr_client.enforce(_gr_site, lower_param, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return lower_param
        else:
            raise ValueError(description + " {} not supported, should be one of {}".format(param, valid_list))

    @staticmethod
    def _greater_equal_than(value, limit):
        return value >= limit - settings.FLOAT_ZERO

    @staticmethod
    def _less_equal_than(value, limit):
        return value <= limit + settings.FLOAT_ZERO

    @staticmethod
    def _range(value, ranges):
        in_range = False
        for left_limit, right_limit in ranges:
            if (
                    left_limit - settings.FLOAT_ZERO
                    <= value
                    <= right_limit + settings.FLOAT_ZERO
            ):
                in_range = True
                break

        # LINEAJE: runtime guardrail checks `in_range` as it flows from the agent to the user interface, before it leaves the application (in ComponentParamBase._range).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `in_range` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:c2117d54678fa97c09ec61921949372a6ea5d438473807da9f4ec5490585b7cb'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c2117d54678fa97c09ec61921949372a6ea5d438473807da9f4ec5490585b7cb', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 335, 'function': 'ComponentParamBase._range'}, 'file': 'agent/component/base.py', 'line': 335, 'function': '_range', 'agent_name': 'ComponentParamBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            in_range = _gr_client.enforce(_gr_site, in_range, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return in_range

    @staticmethod
    def _in(value, right_value_list):
        return value in right_value_list

    @staticmethod
    def _not_in(value, wrong_value_list):
        return value not in wrong_value_list

    def _warn_deprecated_param(self, param_name, description):
        if self._deprecated_params_set.get(param_name):
            _lineaje_payload = f"{description} {param_name} is deprecated and ignored in this version."
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ComponentParamBase._warn_deprecated_param).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:f074b999b4ffb9a1f9deb4f69a6c5eb31f8a0d1542430debe7cec71cee3b50d7'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f074b999b4ffb9a1f9deb4f69a6c5eb31f8a0d1542430debe7cec71cee3b50d7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 347, 'function': 'ComponentParamBase._warn_deprecated_param'}, 'file': 'agent/component/base.py', 'line': 347, 'function': '_warn_deprecated_param', 'agent_name': 'ComponentParamBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(
                _lineaje_payload
            )

    def _warn_to_deprecate_param(self, param_name, description, new_param):
        if self._deprecated_params_set.get(param_name):
            _lineaje_payload = (f"{description} {param_name} will be deprecated in future release; "
                f"please use {new_param} instead.")
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in ComponentParamBase._warn_to_deprecate_param).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:18247b070c95689dcb193f581fa165bca6f6bb7ce3f4de2b4a4a6074a5249318'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:18247b070c95689dcb193f581fa165bca6f6bb7ce3f4de2b4a4a6074a5249318', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 353, 'function': 'ComponentParamBase._warn_to_deprecate_param'}, 'file': 'agent/component/base.py', 'line': 353, 'function': '_warn_to_deprecate_param', 'agent_name': 'ComponentParamBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.warning(
                _lineaje_payload
            )
            return True
        return False


class ComponentBase(ABC):
    component_name: str
    thread_limiter = asyncio.Semaphore(int(os.environ.get("MAX_CONCURRENT_CHATS", 10)))
    variable_ref_patt = r"\{* *\{([a-zA-Z:0-9]+@[A-Za-z0-9_.-]+|sys\.[A-Za-z0-9_.]+|env\.[A-Za-z0-9_.]+)\} *\}*"

    def __str__(self):
        """
        {
            "component_name": "Begin",
            "params": {}
        }
        """
        return """{{
            "component_name": "{}",
            "params": {}
        }}""".format(self.component_name,
                     self._param
                     )

    def __init__(self, canvas, id, param: ComponentParamBase):
        from agent.canvas import Graph  # Local import to avoid cyclic dependency
        assert isinstance(canvas, Graph), "canvas must be an instance of Canvas"
        self._canvas = canvas
        self._id = id
        self._param = param
        self._param.check()

    def is_canceled(self) -> bool:
        return self._canvas.is_canceled()

    def check_if_canceled(self, message: str = "") -> bool:
        if self.is_canceled():
            task_id = getattr(self._canvas, 'task_id', 'unknown')
            log_message = f"Task {task_id} has been canceled"
            if message:
                log_message += f" during {message}"
            # LINEAJE: runtime guardrail checks `log_message` as it flows from the agent to the application log, before it is written to the log (in ComponentBase.check_if_canceled).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `log_message` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:e25f17609653557152feda3201eb10bfe45c4c34b0d2da8f05be1a4f3c44bbf7'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e25f17609653557152feda3201eb10bfe45c4c34b0d2da8f05be1a4f3c44bbf7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 397, 'function': 'ComponentBase.check_if_canceled'}, 'file': 'agent/component/base.py', 'line': 397, 'function': 'check_if_canceled', 'agent_name': 'ComponentBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                log_message = _gr_client.enforce(_gr_site, log_message, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.info(log_message)
            self.set_output("_ERROR", "Task has been canceled")
            return True
        return False

    def invoke(self, **kwargs) -> dict[str, Any]:
        self.set_output("_created_time", time.perf_counter())
        try:
            self._invoke(**kwargs)
        except Exception as e:
            if self.get_exception_default_value():
                self.set_exception_default_value()
            else:
                self.set_output("_ERROR", str(e))
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in ComponentBase.invoke).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:443eb0fbc393d669f646ba7ff7d9cfb4994a92ffd95a4f8603a34c8550c7faf6'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:443eb0fbc393d669f646ba7ff7d9cfb4994a92ffd95a4f8603a34c8550c7faf6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 411, 'function': 'ComponentBase.invoke'}, 'file': 'agent/component/base.py', 'line': 411, 'function': 'invoke', 'agent_name': 'ComponentBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                e = _gr_client.enforce(_gr_site, e, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)
        self._param.debug_inputs = {}
        self.set_output("_elapsed_time", time.perf_counter() - self.output("_created_time"))
        return self.output()

    async def invoke_async(self, **kwargs) -> dict[str, Any]:
        """
        Async wrapper for component invocation.
        Prefers coroutine `_invoke_async` if present; otherwise falls back to `_invoke`.
        Handles timing and error recording consistently with `invoke`.
        """
        self.set_output("_created_time", time.perf_counter())
        try:
            if self.check_if_canceled("Component processing"):
                return

            fn_async = getattr(self, "_invoke_async", None)
            if fn_async and asyncio.iscoroutinefunction(fn_async):
                await fn_async(**kwargs)
            elif asyncio.iscoroutinefunction(self._invoke):
                await self._invoke(**kwargs)
            else:
                await asyncio.to_thread(self._invoke, **kwargs)
        except Exception as e:
            if self.get_exception_default_value():
                self.set_exception_default_value()
            else:
                self.set_output("_ERROR", str(e))
            # LINEAJE: runtime guardrail checks `e` as it flows from the agent to the application log, before it is written to the log (in ComponentBase.invoke_async).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `e` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:7a35c56ce6662d281e5b928dcbb81dbf588d232c2de97994665d456cfc072b15'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7a35c56ce6662d281e5b928dcbb81dbf588d232c2de97994665d456cfc072b15', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 439, 'function': 'ComponentBase.invoke_async'}, 'file': 'agent/component/base.py', 'line': 439, 'function': 'invoke_async', 'agent_name': 'ComponentBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                e = await __import__('asyncio').to_thread(lambda: _gr_client.enforce(_gr_site, e, content_type='application/json'))
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(e)
        self._param.debug_inputs = {}
        self.set_output("_elapsed_time", time.perf_counter() - self.output("_created_time"))
        return self.output()

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 10 * 60)))
    def _invoke(self, **kwargs):
        raise NotImplementedError()

    def output(self, var_nm: str = None) -> Union[dict[str, Any], Any]:
        if var_nm:
            return self._param.outputs.get(var_nm, {}).get("value", "")
        return {k: o.get("value") for k, o in self._param.outputs.items()}

    def set_output(self, key: str, value: Any):
        if key not in self._param.outputs:
            self._param.outputs[key] = {"value": None, "type": str(type(value))}
        self._param.outputs[key]["value"] = value

    def error(self):
        return self._param.outputs.get("_ERROR", {}).get("value")

    def reset(self, only_output=False):
        outputs: dict = self._param.outputs  # for better performance
        for k in outputs.keys():
            outputs[k]["value"] = None
        if only_output:
            return

        inputs: dict = self._param.inputs  # for better performance
        for k in inputs.keys():
            inputs[k]["value"] = None
        self._param.debug_inputs = {}

    def get_input(self, key: str = None) -> Union[Any, dict[str, Any]]:
        if key:
            return self._param.inputs.get(key, {}).get("value")

        res = {}
        for var, o in self.get_input_elements().items():
            v = self.get_param(var)
            if v is None:
                continue
            if isinstance(v, str) and self._canvas.is_reff(v):
                self.set_input_value(var, self._canvas.get_variable_value(v))
            else:
                self.set_input_value(var, v)
            res[var] = self.get_input_value(var)
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in ComponentBase.get_input).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:98a54faa9bf91166df3cf5fe44e5af66226c4f4e4e8c2704858f1bbbe20ede6b'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:98a54faa9bf91166df3cf5fe44e5af66226c4f4e4e8c2704858f1bbbe20ede6b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 487, 'function': 'ComponentBase.get_input'}, 'file': 'agent/component/base.py', 'line': 487, 'function': 'get_input', 'agent_name': 'ComponentBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    def get_input_values(self) -> Union[Any, dict[str, Any]]:
        if self._param.debug_inputs:
            return self._param.debug_inputs

        return {var: self.get_input_value(var) for var, o in self.get_input_elements().items()}

    def get_input_elements_from_text(self, txt: str) -> dict[str, dict[str, str]]:
        res = {}
        for r in re.finditer(self.variable_ref_patt, txt, flags=re.IGNORECASE | re.DOTALL):
            exp = r.group(1)
            cpn_id, var_nm = exp.split("@") if exp.find("@") > 0 else ("", exp)
            res[exp] = {
                "name": (self._canvas.get_component_name(cpn_id) + f"@{var_nm}") if cpn_id else exp,
                "value": self._canvas.get_variable_value(exp),
                "_retrieval": self._canvas.get_variable_value(f"{cpn_id}@_references") if cpn_id else None,
                "_cpn_id": cpn_id
            }
        # LINEAJE: runtime guardrail checks `res` as it flows from the agent to the user interface, before it leaves the application (in ComponentBase.get_input_elements_from_text).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `res` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:92103d62d15bba516c11641009d51f79259ecf6c5560cab2111141f4895ab416'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:92103d62d15bba516c11641009d51f79259ecf6c5560cab2111141f4895ab416', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 506, 'function': 'ComponentBase.get_input_elements_from_text'}, 'file': 'agent/component/base.py', 'line': 506, 'function': 'get_input_elements_from_text', 'agent_name': 'ComponentBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            res = _gr_client.enforce(_gr_site, res, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return res

    def get_input_elements(self) -> dict[str, Any]:
        return self._param.inputs

    def get_input_form(self) -> dict[str, dict]:
        return self._param.get_input_form()

    def set_input_value(self, key: str, value: Any) -> None:
        if key not in self._param.inputs:
            self._param.inputs[key] = {"value": None}
        self._param.inputs[key]["value"] = value

    def get_input_value(self, key: str) -> Any:
        if key not in self._param.inputs:
            return None
        return self._param.inputs[key].get("value")

    def get_component_name(self, cpn_id) -> str:
        return self._canvas.get_component(cpn_id)["obj"].component_name.lower()

    def get_param(self, name):
        if hasattr(self._param, name):
            return getattr(self._param, name)
        return None

    def debug(self, **kwargs):
        return self._invoke(**kwargs)

    def get_parent(self) -> Union[object, None]:
        pid = self._canvas.get_component(self._id).get("parent_id")
        if not pid:
            return None
        return self._canvas.get_component(pid)["obj"]

    def get_upstream(self) -> List[str]:
        cpn_nms = self._canvas.get_component(self._id)['upstream']
        # LINEAJE: runtime guardrail checks `cpn_nms` as it flows from the agent to the user interface, before it leaves the application (in ComponentBase.get_upstream).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `cpn_nms` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:9ca04a8efaf31656989620fcbf936d9ac20684e3de14573f5299d66a5accd873'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9ca04a8efaf31656989620fcbf936d9ac20684e3de14573f5299d66a5accd873', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 543, 'function': 'ComponentBase.get_upstream'}, 'file': 'agent/component/base.py', 'line': 543, 'function': 'get_upstream', 'agent_name': 'ComponentBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            cpn_nms = _gr_client.enforce(_gr_site, cpn_nms, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return cpn_nms

    def get_downstream(self) -> List[str]:
        cpn_nms = self._canvas.get_component(self._id)['downstream']
        # LINEAJE: runtime guardrail checks `cpn_nms` as it flows from the agent to the user interface, before it leaves the application (in ComponentBase.get_downstream).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `cpn_nms` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:31915817b1ae32fc2d3433e531d1fcd8196d5d0bc4509ae0bcd9cf99d1613712'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:31915817b1ae32fc2d3433e531d1fcd8196d5d0bc4509ae0bcd9cf99d1613712', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 547, 'function': 'ComponentBase.get_downstream'}, 'file': 'agent/component/base.py', 'line': 547, 'function': 'get_downstream', 'agent_name': 'ComponentBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            cpn_nms = _gr_client.enforce(_gr_site, cpn_nms, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return cpn_nms

    @staticmethod
    def string_format(content: str, kv: dict[str, str]) -> str:
        for n, v in kv.items():
            def repl(_match, val=v):
                return str(val) if val is not None else ""

            content = re.sub(
                r"\{%s\}" % re.escape(n),
                repl,
                content
            )
        # LINEAJE: runtime guardrail checks `content` as it flows from the agent to the user interface, before it leaves the application (in ComponentBase.string_format).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `content` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:18683676bec98652c294b278d8f51437e9e461e1bca6041cd152dea0dbeec2f5'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:18683676bec98652c294b278d8f51437e9e461e1bca6041cd152dea0dbeec2f5', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/component/base.py', 'line': 560, 'function': 'ComponentBase.string_format'}, 'file': 'agent/component/base.py', 'line': 560, 'function': 'string_format', 'agent_name': 'ComponentBase', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            content = _gr_client.enforce(_gr_site, content, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return content

    def exception_handler(self):
        if not self._param.exception_method:
            return None
        return {
            "goto": self._param.exception_goto,
            "default_value": self._param.exception_default_value
        }

    def get_exception_default_value(self):
        if self._param.exception_method != "comment":
            return ""
        return self._param.exception_default_value

    def set_exception_default_value(self):
        self.set_output("result", self.get_exception_default_value())

    def thoughts(self) -> str:
        raise NotImplementedError()
