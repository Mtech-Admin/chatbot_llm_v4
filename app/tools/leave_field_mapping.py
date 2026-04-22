"""
SAP leave request CUSTOMERxx field keys ↔ human-readable labels (DMRC HRMS).
API/DB store CUSTOMER01–CUSTOMER10; users ask using label phrases — map for answers.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Fieldname → FieldLabel (from HRMS / SAP metadata; multiple leave types may reuse keys with different semantics)
CUSTOMER_FIELD_LABELS: Dict[str, str] = {
    "CUSTOMER01": "Reason for Leave",
    "CUSTOMER02": "Location of accident",
    "CUSTOMER03": "Address During Leave",
    "CUSTOMER04": "Custom field (CUSTOMER04)",
    "CUSTOMER05": "City/District",
    "CUSTOMER06": "Hospitalization status",
    "CUSTOMER07": "Address Line 3",
    "CUSTOMER08": "Check if not for covid",
    "CUSTOMER09": "Reason for leave",
    "CUSTOMER10": "Forenoon/Afternoon/Full Day",
}

_CUSTOMER_KEY_RE = re.compile(r"^CUSTOMER(\d{1,2})$", re.IGNORECASE)


def label_for_customer_key(key: str) -> str:
    k = (key or "").strip().upper()
    return CUSTOMER_FIELD_LABELS.get(k, k or "Unknown field")


def _collect_customer_pairs(obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    pairs: List[Dict[str, Any]] = []
    for key in sorted(obj.keys()):
        m = _CUSTOMER_KEY_RE.match(key)
        if not m:
            continue
        val = obj.get(key)
        if val is None or val == "":
            continue
        pairs.append(
            {
                "field_key": key.upper(),
                "field_label": label_for_customer_key(key),
                "value": val,
            }
        )
    return pairs


def enrich_leave_record(record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Attach named_customer_fields for any CUSTOMERxx values on a single leave row."""
    if not record or not isinstance(record, dict):
        return record
    out = dict(record)
    pairs = _collect_customer_pairs(out)
    if pairs:
        out["named_customer_fields"] = pairs
    return out


def enrich_leave_payload(payload: Any) -> Any:
    """Recursively enrich dict/list leave payloads with named_customer_fields."""
    if payload is None:
        return payload
    if isinstance(payload, list):
        return [enrich_leave_payload(x) for x in payload]
    if isinstance(payload, dict):
        # Paginated shape { data: [...], total, page, ... }
        if "data" in payload and isinstance(payload.get("data"), list):
            inner = dict(payload)
            inner["data"] = [enrich_leave_record(x) if isinstance(x, dict) else x for x in payload["data"]]
            return inner
        # Single record or flat dict
        merged = {k: enrich_leave_payload(v) for k, v in payload.items()}
        if any(_CUSTOMER_KEY_RE.match(k) for k in merged.keys()):
            return enrich_leave_record(merged) or merged
        return merged
    return payload


def phrase_to_customer_keys(user_text: str) -> List[str]:
    """
    Rough reverse map: find which CUSTOMER keys the user might mean from natural language.
    Used for guiding answers when only a subset of fields is relevant.
    """
    t = (user_text or "").lower()
    hits: List[str] = []
    synonyms = [
        ("CUSTOMER01", ["reason for leave", "reason", "why leave"]),
        ("CUSTOMER02", ["location of accident", "accident location", "where accident"]),
        ("CUSTOMER03", ["address during leave", "address during", "where staying"]),
        ("CUSTOMER05", ["city", "district", "city/district"]),
        ("CUSTOMER06", ["hospitalization", "hospital"]),
        ("CUSTOMER07", ["address line 3", "line 3"]),
        ("CUSTOMER08", ["not for covid", "covid"]),
        ("CUSTOMER09", ["reason for leave"]),
        ("CUSTOMER10", ["forenoon", "afternoon", "full day", "half day"]),
    ]
    for key, phrases in synonyms:
        if any(p in t for p in phrases):
            hits.append(key)
    return list(dict.fromkeys(hits))
