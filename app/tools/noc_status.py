"""
NOC workflow status codes (single-letter keys) → full labels for user-facing replies.
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, Tuple

NOC_STATUS_LABELS: dict[str, str] = {
    "N": "New",
    "T": "To Be Approved",
    "P": "Partially Approved",
    "A": "Approved",
    "R": "Rejected",
    "D": "Processing Complete",
    "X": "Deleted",
    "B": "To Be Processed",
    "C": "Closed",
    "K": "Cancelled",
    "S": "Settled",
}

WORKFLOW_STATUS_LETTERS: FrozenSet[str] = frozenset(NOC_STATUS_LABELS.keys())

# (lowercase phrase, letter) longest phrase first — used to match user wording to HRMS codes
NOC_STATUS_PHRASES_ORDERED: Tuple[Tuple[str, str], ...] = tuple(
    sorted(
        ((label.lower().strip(), code) for code, label in NOC_STATUS_LABELS.items()),
        key=lambda x: (-len(x[0]), x[1]),
    )
)

_STATUS_KEYS: FrozenSet[str] = frozenset({"status", "requestStatus"})


def expand_noc_status_value(value: Any) -> Any:
    """Map a single-letter status code to its full label; pass through otherwise."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    s = value.strip()
    if len(s) == 1:
        return NOC_STATUS_LABELS.get(s.upper(), value)
    return value


def expand_noc_statuses_in_payload(obj: Any) -> Any:
    """Recursively expand `status` / `requestStatus` fields for NOC payloads."""
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if k in _STATUS_KEYS:
                out[k] = expand_noc_status_value(v)
            else:
                out[k] = expand_noc_statuses_in_payload(v)
        return out
    if isinstance(obj, list):
        return [expand_noc_statuses_in_payload(x) for x in obj]
    return obj
