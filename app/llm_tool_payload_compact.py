"""
Shrink HRMS tool JSON before follow-up LLM calls — keeps polish/reviewer flow but cuts prompt tokens.
"""

from __future__ import annotations

import json
import logging
from typing import Any, List

logger = logging.getLogger(__name__)

_DROP_KEYS = frozenset({"__metadata", "MultipleApprovers"})
_ATTACHMENT_KEYS = frozenset({"Attachments", "AttachmentDetails", "absenceTypeTimeAccount"})


def _truncate_str(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 20] + "…[truncated]"


def _compact_value(value: Any, *, max_str: int, max_list: int, _depth: int) -> Any:
    if _depth > 32:
        return "[depth-limit]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _truncate_str(value, max_str)
    if isinstance(value, list):
        if len(value) > max_list:
            head = [_compact_value(v, max_str=max_str, max_list=max_list, _depth=_depth + 1) for v in value[:max_list]]
            head.append({"_note": f"{len(value) - max_list} more items omitted"})
            return head
        return [_compact_value(v, max_str=max_str, max_list=max_list, _depth=_depth + 1) for v in value]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if k in _DROP_KEYS:
                continue
            if k in _ATTACHMENT_KEYS:
                if isinstance(v, dict) and not v:
                    out[k] = {}
                    continue
                ser = json.dumps(v, default=str)
                if len(ser) > 800:
                    out[k] = {"_omitted": f"payload ~{len(ser)} chars"}
                    continue
            out[k] = _compact_value(v, max_str=max_str, max_list=max_list, _depth=_depth + 1)
        return out
    return str(value)[:max_str]


def serialize_tool_result_for_llm(
    payload: Any,
    *,
    budget_chars: int = 22_000,
) -> str:
    """
    Return JSON string suitable for a `tool` message `content`, staying under ~budget_chars when possible.
    """
    tiers: List[tuple[int, int]] = [
        (400, 30),
        (280, 20),
        (180, 14),
        (100, 10),
    ]
    raw_len = len(json.dumps(payload, default=str, ensure_ascii=False))
    for max_str, max_list in tiers:
        compacted = _compact_value(payload, max_str=max_str, max_list=max_list, _depth=0)
        text = json.dumps(compacted, default=str, ensure_ascii=False)
        if len(text) <= budget_chars:
            if len(text) < raw_len:
                logger.info(
                    "Compacted tool payload for LLM: %s -> %s chars",
                    raw_len,
                    len(text),
                )
            return text
    text = json.dumps(
        _compact_value(payload, max_str=80, max_list=8, _depth=0),
        default=str,
        ensure_ascii=False,
    )
    logger.warning("Tool payload still large after compaction: %s chars", len(text))
    return text
