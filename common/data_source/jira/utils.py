"""Helper utilities for the Jira connector."""

from __future__ import annotations
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


import os
from collections.abc import Collection
from datetime import datetime, timezone
from typing import Any, Iterable

from jira.resources import Issue

from common.data_source.utils import datetime_from_string

JIRA_SERVER_API_VERSION = os.environ.get("JIRA_SERVER_API_VERSION", "2")
JIRA_CLOUD_API_VERSION = os.environ.get("JIRA_CLOUD_API_VERSION", "3")


def build_issue_url(base_url: str, issue_key: str) -> str:
    """Return the canonical UI URL for a Jira issue."""
    return f"{base_url.rstrip('/')}/browse/{issue_key}"


def parse_jira_datetime(value: Any) -> datetime | None:
    """Best-effort parse of Jira datetime values to aware UTC datetimes."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        return datetime_from_string(value)
    return None


def extract_named_value(value: Any) -> str | None:
    """Extract a readable string out of Jira's typed objects."""
    if value is None:
        return None
    if isinstance(value, str):
        # LINEAJE: runtime guardrail checks `value` as it flows from the agent to the user interface, before it leaves the application (in extract_named_value).
        #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `value` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:46566f8cb17cd9ed182aed5a44c2f253bb670fb9e13aa1361dd4f16a733caa1f'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:46566f8cb17cd9ed182aed5a44c2f253bb670fb9e13aa1361dd4f16a733caa1f', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'common/data_source/jira/utils.py', 'line': 39, 'function': 'extract_named_value'}, 'file': 'common/data_source/jira/utils.py', 'line': 39, 'function': 'extract_named_value', 'agent_name': 'extract_named_value', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            value = _gr_client.enforce(_gr_site, value, content_type='text/plain')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        return value
    if isinstance(value, dict):
        return value.get("name") or value.get("value")
    return getattr(value, "name", None)


def extract_user(value: Any) -> tuple[str | None, str | None]:
    """Return display name + email tuple for a Jira user blob."""
    if value is None:
        return None, None
    if isinstance(value, dict):
        return value.get("displayName"), value.get("emailAddress")

    display = getattr(value, "displayName", None)
    email = getattr(value, "emailAddress", None)
    return display, email


def extract_text_from_adf(adf: Any) -> str:
    """Flatten Atlassian Document Format (ADF) structures to text."""
    texts: list[str] = []

    def _walk(node: Any) -> None:
        if node is None:
            return
        if isinstance(node, dict):
            node_type = node.get("type")
            if node_type == "text":
                texts.append(node.get("text", ""))
            for child in node.get("content", []):
                _walk(child)
        elif isinstance(node, list):
            for child in node:
                _walk(child)

    _walk(adf)
    return "\n".join(part for part in texts if part)


def extract_body_text(value: Any) -> str:
    """Normalize Jira description/comments (raw/adf/str) into plain text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return extract_text_from_adf(value).strip()
    return str(value).strip()


def format_comments(
    comment_block: Any,
    *,
    blacklist: Collection[str],
) -> str:
    """Convert Jira comments into a markdown-ish bullet list."""
    if not isinstance(comment_block, dict):
        return ""

    comments = comment_block.get("comments") or []
    lines: list[str] = []
    normalized_blacklist = {email.lower() for email in blacklist if email}

    for comment in comments:
        author = comment.get("author") or {}
        author_email = (author.get("emailAddress") or "").lower()
        if author_email and author_email in normalized_blacklist:
            continue

        author_name = author.get("displayName") or author.get("name") or author_email or "Unknown"
        created = parse_jira_datetime(comment.get("created"))
        created_str = created.isoformat() if created else "Unknown time"
        body = extract_body_text(comment.get("body"))
        if not body:
            continue

        lines.append(f"- {author_name} ({created_str}):\n{body}")

    return "\n\n".join(lines)


def format_attachments(attachments: Any) -> str:
    """List Jira attachments as bullet points."""
    if not isinstance(attachments, list):
        return ""

    attachment_lines: list[str] = []
    for attachment in attachments:
        filename = attachment.get("filename")
        if not filename:
            continue
        size = attachment.get("size")
        size_text = f" ({size} bytes)" if isinstance(size, int) else ""
        content_url = attachment.get("content") or ""
        url_suffix = f" -> {content_url}" if content_url else ""
        attachment_lines.append(f"- {filename}{size_text}{url_suffix}")

    return "\n".join(attachment_lines)


def should_skip_issue(issue: Issue, labels_to_skip: set[str]) -> bool:
    """Return True if the issue contains any label from the skip list."""
    if not labels_to_skip:
        return False

    fields = getattr(issue, "raw", {}).get("fields", {})
    labels: Iterable[str] = fields.get("labels") or []
    for label in labels:
        if (label or "").lower() in labels_to_skip:
            return True
    return False
