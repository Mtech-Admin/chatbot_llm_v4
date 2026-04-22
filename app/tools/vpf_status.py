"""
VPF workflow status codes — same single-letter map as NOC (RequestStatus / Status in HRMS).
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet

# Same labels as NOC (SAP workflow codes)
VPF_STATUS_LABELS: dict[str, str] = {
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

_VPF_STATUS_KEYS: FrozenSet[str] = frozenset(
    {
        "status",
        "requestStatus",
        "Status",
        "RequestStatus",
    }
)


def expand_vpf_status_value(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    s = value.strip()
    if len(s) == 1:
        return VPF_STATUS_LABELS.get(s.upper(), value)
    return value


def expand_vpf_statuses_in_payload(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if k in _VPF_STATUS_KEYS:
                out[k] = expand_vpf_status_value(v)
            else:
                out[k] = expand_vpf_statuses_in_payload(v)
        return out
    if isinstance(obj, list):
        return [expand_vpf_statuses_in_payload(x) for x in obj]
    return obj
