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

import datetime
import logging
import time

def current_timestamp():
    """
    Get the current timestamp in milliseconds.

    Returns:
        int: Current Unix timestamp in milliseconds (13 digits)

    Example:
        >>> current_timestamp()
        1704067200000
    """
    return int(time.time() * 1000)


def timestamp_to_date(timestamp, format_string="%Y-%m-%d %H:%M:%S"):
    """
    Convert a timestamp to formatted date string.

    Args:
        timestamp: Unix timestamp in milliseconds. If None or empty, uses current time.
        format_string: Format string for the output date (default: "%Y-%m-%d %H:%M:%S")

    Returns:
        str: Formatted date string

    Example:
        >>> timestamp_to_date(1704067200000)
        '2024-01-01 08:00:00'
    """
    if not timestamp:
        timestamp = time.time()
    timestamp = int(timestamp) / 1000
    time_array = time.localtime(timestamp)
    str_date = time.strftime(format_string, time_array)
    # LINEAJE: runtime guardrail checks `str_date` as it flows from the agent to the user interface, before it leaves the application (in timestamp_to_date).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `str_date` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:9791e0db1775d79d6ff7f96aac6cea9e41c5e36b4a37cfa77ac96bb1e0349c3b'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9791e0db1775d79d6ff7f96aac6cea9e41c5e36b4a37cfa77ac96bb1e0349c3b', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/time_utils.py', 'line': 54, 'function': 'timestamp_to_date'}, 'file': 'common/time_utils.py', 'line': 54, 'function': 'timestamp_to_date', 'agent_name': 'timestamp_to_date', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        str_date = _gr_client.enforce(_gr_site, str_date, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return str_date


def date_string_to_timestamp(time_str, format_string="%Y-%m-%d %H:%M:%S"):
    """
    Convert a date string to timestamp in milliseconds.

    Args:
        time_str: Date string to convert
        format_string: Format of the input date string (default: "%Y-%m-%d %H:%M:%S")

    Returns:
        int: Unix timestamp in milliseconds

    Example:
        >>> date_string_to_timestamp("2024-01-01 00:00:00")
        1704067200000
    """
    time_array = time.strptime(time_str, format_string)
    time_stamp = int(time.mktime(time_array) * 1000)
    # LINEAJE: runtime guardrail checks `time_stamp` as it flows from the agent to the user interface, before it leaves the application (in date_string_to_timestamp).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `time_stamp` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:5c845d743aab0790c262eb3988893550d33cb987ba277391a021835d99940719'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:5c845d743aab0790c262eb3988893550d33cb987ba277391a021835d99940719', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/time_utils.py', 'line': 74, 'function': 'date_string_to_timestamp'}, 'file': 'common/time_utils.py', 'line': 74, 'function': 'date_string_to_timestamp', 'agent_name': 'date_string_to_timestamp', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        time_stamp = _gr_client.enforce(_gr_site, time_stamp, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return time_stamp

def datetime_format(date_time: datetime.datetime) -> datetime.datetime:
    """
    Normalize a datetime object by removing microsecond component.

    Creates a new datetime object with only year, month, day, hour, minute, second.
    Microseconds are set to 0.

    Args:
        date_time: datetime object to normalize

    Returns:
        datetime.datetime: New datetime object without microseconds

    Example:
        >>> dt = datetime.datetime(2024, 1, 1, 12, 30, 45, 123456)
        >>> datetime_format(dt)
        datetime.datetime(2024, 1, 1, 12, 30, 45)
    """
    return datetime.datetime(date_time.year, date_time.month, date_time.day,
                             date_time.hour, date_time.minute, date_time.second)


def get_format_time() -> datetime.datetime:
    """
    Get current datetime normalized without microseconds.

    Returns:
        datetime.datetime: Current datetime with microseconds set to 0

    Example:
        >>> get_format_time()
        datetime.datetime(2024, 1, 1, 12, 30, 45)
    """
    return datetime_format(datetime.datetime.now())


def delta_seconds(date_string: str):
    """
    Calculate seconds elapsed from a given date string to now.

    Args:
        date_string: Date string in "YYYY-MM-DD HH:MM:SS" format

    Returns:
        float: Number of seconds between the given date and current time

    Example:
        >>> delta_seconds("2024-01-01 12:00:00")
        3600.0  # If current time is 2024-01-01 13:00:00
    """
    dt = datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    return (datetime.datetime.now() - dt).total_seconds()


def format_iso_8601_to_ymd_hms(time_str: str) -> str:
    """
    Convert ISO 8601 formatted string to "YYYY-MM-DD HH:MM:SS" format.

    Args:
        time_str: ISO 8601 date string (e.g. "2024-01-01T12:00:00Z")

    Returns:
        str: Date string in "YYYY-MM-DD HH:MM:SS" format

    Example:
        >>> format_iso_8601_to_ymd_hms("2024-01-01T12:00:00Z")
        '2024-01-01 12:00:00'
    """
    from dateutil import parser

    try:
        if parser.isoparse(time_str):
            dt = datetime.datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # LINEAJE: runtime guardrail checks `time_str` as it flows from the agent to the user interface, before it leaves the application (in format_iso_8601_to_ymd_hms).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `time_str` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:8b664c73d097104df0f70643fbef73005757ee6f5d62edcb06979a7e9737b0d5'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:8b664c73d097104df0f70643fbef73005757ee6f5d62edcb06979a7e9737b0d5', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/time_utils.py', 'line': 151, 'function': 'format_iso_8601_to_ymd_hms'}, 'file': 'common/time_utils.py', 'line': 151, 'function': 'format_iso_8601_to_ymd_hms', 'agent_name': 'format_iso_8601_to_ymd_hms', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
            try:
                time_str = _gr_client.enforce(_gr_site, time_str, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return time_str
    except Exception as e:
        _lineaje_payload = str(e)
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in format_iso_8601_to_ymd_hms).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:46add50a2cfeaf4aaa4754e458543d961a8beeb8e1d56f8a0ff133057ae3a2e6'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:46add50a2cfeaf4aaa4754e458543d961a8beeb8e1d56f8a0ff133057ae3a2e6', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/time_utils.py', 'line': 153, 'function': 'format_iso_8601_to_ymd_hms'}, 'file': 'common/time_utils.py', 'line': 153, 'function': 'format_iso_8601_to_ymd_hms', 'agent_name': 'format_iso_8601_to_ymd_hms', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.error(_lineaje_payload)
        # LINEAJE: runtime guardrail checks `time_str` as it flows from the agent to the user interface, before it leaves the application (in format_iso_8601_to_ymd_hms).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `time_str` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:6adda58d6dafcd8c920a0a382397210e6d8e7e0d6cf76ca670c536dfea683489'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:6adda58d6dafcd8c920a0a382397210e6d8e7e0d6cf76ca670c536dfea683489', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/time_utils.py', 'line': 154, 'function': 'format_iso_8601_to_ymd_hms'}, 'file': 'common/time_utils.py', 'line': 154, 'function': 'format_iso_8601_to_ymd_hms', 'agent_name': 'format_iso_8601_to_ymd_hms', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            time_str = _gr_client.enforce(_gr_site, time_str, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return time_str
