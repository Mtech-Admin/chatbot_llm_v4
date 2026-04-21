"""
NOC module — read-only list/detail calls into DMRC HRMS API (no HRMS code changes).

NOC types (internal keys used by tools / agent):
- noc_exindia_requests      → POST /noc-ex-india/find-all-ex-india-req, find-one
- noc_visa_passport         → POST /noc-visa-passport/find-all, find-one
- noc_reimbursement         → POST /noc-reimbursement/find-all, find-one
- noc_outsidejobs           → POST /noc/find-all-noc-outjob-requests, noc-outjob-details-by-id
- noc_onlinecourses         → POST /noc-onlinecourses/find-all, find-one
- noc_higherstudies         → POST /noc-higherstudies/find-all, find-one
"""

from __future__ import annotations

import json
import re
from calendar import monthrange
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from app.tools.hrms_client import hrms_client
from app.tools.noc_status import (
    NOC_STATUS_PHRASES_ORDERED,
    WORKFLOW_STATUS_LETTERS,
    expand_noc_statuses_in_payload,
)

VALID_NOC_TYPES = frozenset(
    {
        "noc_exindia_requests",
        "noc_visa_passport",
        "noc_reimbursement",
        "noc_outsidejobs",
        "noc_onlinecourses",
        "noc_higherstudies",
    }
)

NOC_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_my_noc_requests",
            "description": (
                "List the logged-in employee's NOC requests of a given module type "
                "(ex-India, visa/passport, reimbursement, outside job, online courses, higher studies). "
                "Use pagination when the user asks to see recent requests or many rows. "
                "Do not guess totals from row previews: rely on the `total` field in the tool response summary only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "noc_type": {
                        "type": "string",
                        "description": (
                            "One of: noc_exindia_requests, noc_visa_passport, noc_reimbursement, "
                            "noc_outsidejobs, noc_onlinecourses, noc_higherstudies"
                        ),
                    },
                    "page": {
                        "type": "string",
                        "description": "Page number (default 1). Numeric string.",
                    },
                    "limit": {
                        "type": "string",
                        "description": "Page size (default 20, max 50). Numeric string.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional search text (reference number, etc.)",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Optional filter: range start (ISO date or datetime). Use with end_date.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Optional filter: range end (ISO date or datetime). Use with start_date.",
                    },
                    "status": {
                        "type": "string",
                        "description": "Optional HRMS list filter: internal status (e.g. approved) if supported.",
                    },
                    "request_status": {
                        "type": "string",
                        "description": "Optional HRMS list filter: workflow requestStatus code (e.g. A=Approved).",
                    },
                },
                "required": ["noc_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_noc_request_details",
            "description": (
                "Fetch full details for one NOC request by id (or SAP id string for outside-job details). "
                "Status fields are returned with full status labels (not single-letter codes)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "noc_type": {
                        "type": "string",
                        "description": (
                            "Same noc_type values as list_my_noc_requests. "
                            "For noc_outsidejobs, request_id is often the SAP-style string id."
                        ),
                    },
                    "request_id": {
                        "type": "string",
                        "description": "Primary request id (numeric string for most modules).",
                    },
                },
                "required": ["noc_type", "request_id"],
            },
        },
    },
]


def _to_int(value: Any, default: int, min_value: int = 1, max_value: Optional[int] = None) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    if parsed < min_value:
        return default
    if max_value is not None and parsed > max_value:
        return max_value
    return parsed


def _is_hrms_response_envelope(d: dict) -> bool:
    """True for Nest createResponse shape `{ status: number, message, data }` only."""
    if "data" not in d or "message" not in d:
        return False
    st = d.get("status")
    if isinstance(st, (int, float)):
        return True
    if isinstance(st, str) and st.strip().isdigit():
        return True
    return False


def _unwrap_hrms_payload(root: Dict[str, Any]) -> Any:
    """
    Strip nested CommonResponseDto wrappers.

    IMPORTANT: Many list endpoints return `data: { data: [...], total, page }`.
    We must NOT descend into the inner `data` array — that drops `total` and breaks counts.
    """
    if "error" in root:
        return root
    cur: Any = root
    for _ in range(8):
        if not isinstance(cur, dict):
            return cur
        if _is_hrms_response_envelope(cur):
            cur = cur["data"]
            continue
        return cur
    return cur


def _error_result(code: str, message: str) -> Dict[str, Any]:
    return {"status": "error", "error_code": code, "message": message}


def _success_payload(raw: Any) -> Dict[str, Any]:
    expanded = expand_noc_statuses_in_payload(raw)
    return {"status": "success", "data": expanded}


async def list_my_noc_requests(
    jwt_token: str,
    noc_type: str,
    page: Union[int, str] = 1,
    limit: Union[int, str] = 20,
    query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    request_status: Optional[str] = None,
) -> Dict[str, Any]:
    nt = (noc_type or "").strip()
    if nt not in VALID_NOC_TYPES:
        return _error_result("invalid_noc_type", f"Unknown noc_type: {noc_type}")

    safe_page = _to_int(page, default=1, min_value=1)
    safe_limit = _to_int(limit, default=20, min_value=1, max_value=50)
    body: Dict[str, Any] = {"page": safe_page, "limit": safe_limit}
    if query:
        body["query"] = str(query).strip()
    if start_date and end_date:
        body["startDate"] = str(start_date).strip()
        body["endDate"] = str(end_date).strip()
    if status is not None and str(status).strip() != "":
        body["status"] = str(status).strip()
    if request_status is not None and str(request_status).strip() != "":
        body["requestStatus"] = str(request_status).strip()

    routes = {
        "noc_exindia_requests": "/noc-ex-india/find-all-ex-india-req",
        "noc_visa_passport": "/noc-visa-passport/find-all",
        "noc_reimbursement": "/noc-reimbursement/find-all",
        "noc_outsidejobs": "/noc/find-all-noc-outjob-requests",
        "noc_onlinecourses": "/noc-onlinecourses/find-all",
        "noc_higherstudies": "/noc-higherstudies/find-all",
    }
    endpoint = routes[nt]
    result = await hrms_client.call_api(endpoint, jwt_token, method="POST", body=body)
    if "error" in result:
        return _error_result(result["error"], _friendly_error(result["error"]))

    payload = _unwrap_hrms_payload(result)
    return _success_payload(payload)


async def get_noc_request_details(jwt_token: str, noc_type: str, request_id: str) -> Dict[str, Any]:
    nt = (noc_type or "").strip()
    if nt not in VALID_NOC_TYPES:
        return _error_result("invalid_noc_type", f"Unknown noc_type: {noc_type}")

    rid = (request_id or "").strip()
    if not rid:
        return _error_result("invalid_request_id", "request_id is required.")

    if nt == "noc_outsidejobs":
        endpoint = "/noc/noc-outjob-details-by-id"
        body: Dict[str, Any] = {"id": rid}
    else:
        try:
            num_id = int(rid)
        except ValueError:
            return _error_result("invalid_request_id", "request_id must be a number for this NOC type.")
        endpoint = {
            "noc_exindia_requests": "/noc-ex-india/find-one",
            "noc_visa_passport": "/noc-visa-passport/find-one",
            "noc_reimbursement": "/noc-reimbursement/find-one",
            "noc_onlinecourses": "/noc-onlinecourses/find-one",
            "noc_higherstudies": "/noc-higherstudies/find-one",
        }[nt]
        body = {"id": num_id}

    result = await hrms_client.call_api(endpoint, jwt_token, method="POST", body=body)
    if "error" in result:
        return _error_result(result["error"], _friendly_error(result["error"]))

    payload = _unwrap_hrms_payload(result)
    return _success_payload(payload)


def _friendly_error(code: str) -> str:
    return {
        "access_denied": "You do not have access to this NOC information.",
        "not_found": "No matching NOC request was found.",
        "unauthorized": "Your session has expired. Please log in again.",
        "timeout": "The request took too long. Please try again.",
    }.get(code, "Something went wrong while fetching NOC data.")


# --- Count / type inference (no LLM): use HRMS `total` from list endpoints --------------------

NOC_TYPE_LABELS: Dict[str, str] = {
    "noc_outsidejobs": "outside job",
    "noc_exindia_requests": "ex-India travel",
    "noc_visa_passport": "visa / passport",
    "noc_reimbursement": "reimbursement",
    "noc_onlinecourses": "online courses",
    "noc_higherstudies": "higher studies",
}

# Match more specific NOC kinds first (order matters).
_NOC_TYPE_PATTERNS: List[Tuple[str, Tuple[str, ...]]] = [
    ("noc_outsidejobs", (r"\boutside\s*job", r"\bout\s*side\s*job", r"\boutsidejob\b")),
    ("noc_exindia_requests", (r"\bex\s*-?\s*india\b", r"\bexindia\b")),
    ("noc_onlinecourses", (r"\bonline\s*courses?\b", r"\bonlinecourse\b")),
    ("noc_higherstudies", (r"\bhigher\s*stud(?:y|ies)\b", r"\bhigherstudies\b")),
    ("noc_reimbursement", (r"\breimbursement\b", r"\breimb\b")),
    ("noc_visa_passport", (r"\bvisa\b", r"\bpassport\b")),
]


def message_asks_for_noc_count(user_message: str) -> bool:
    """True when the user wants a count / total — must be answered without LLM arithmetic."""
    m = (user_message or "").lower()
    if not m.strip():
        return False
    if re.search(r"\b(how many|how\s+many|number of|count\b)\b", m):
        return True
    if re.search(r"\btotal\b", m) and re.search(r"\b(noc|request)\b", m):
        return True
    return False


def infer_noc_type_from_message(user_message: str) -> Optional[str]:
    m = (user_message or "").lower()
    for noc_type, patterns in _NOC_TYPE_PATTERNS:
        if any(re.search(p, m) for p in patterns):
            return noc_type
    if re.search(r"\bnoc\b", m):
        # Generic "NOC" without module — caller should ask for clarification
        return None
    return None


_MONTH_NAME_TO_NUM: Dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def parse_month_filter_from_message(user_message: str) -> Optional[Tuple[str, str, str]]:
    """
    If the user names a calendar month, return (startDate, endDate, human_label) for HRMS list filters.
    Dates are YYYY-MM-DD inclusive range; HRMS uses BETWEEN on created_at.
    Year: explicit in text, else current calendar year (Asia/Kolkata date if available, else local).
    """
    text = (user_message or "").lower()
    month_num: Optional[int] = None
    month_token: Optional[str] = None
    for name, num in sorted(_MONTH_NAME_TO_NUM.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{re.escape(name)}\b", text):
            month_num = num
            month_token = name.capitalize()
            break
    if not month_num:
        return None

    year_m = re.search(r"\b(19\d{2}|20\d{2})\b", user_message or "")
    if year_m:
        year = int(year_m.group(1))
    else:
        try:
            from zoneinfo import ZoneInfo

            today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        except Exception:
            today = date.today()
        year = today.year

    last_day = monthrange(year, month_num)[1]
    start_d = date(year, month_num, 1)
    end_d = date(year, month_num, last_day)
    # Inclusive month window for timestamptz BETWEEN (HRMS servers use IST)
    start = f"{start_d.isoformat()}T00:00:00.000+05:30"
    end = f"{end_d.isoformat()}T23:59:59.999+05:30"
    label = f"{month_token or 'That month'} {year}"
    return (start, end, label)


def _extract_total_from_list_payload(data: Any) -> Optional[int]:
    """Find integer `total` on HRMS paginated list payloads (handles one extra `{ data: { ... } }` wrap)."""
    cur: Any = data
    for _ in range(5):
        if not isinstance(cur, dict):
            return None
        t = cur.get("total")
        if isinstance(t, int):
            return t
        if isinstance(t, str) and str(t).strip().isdigit():
            return int(str(t).strip())
        nxt = cur.get("data")
        if isinstance(nxt, dict):
            cur = nxt
            continue
        return None
    return None


async def count_noc_requests_for_employee(
    jwt_token: str,
    noc_type: str,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period_label: Optional[str] = None,
    status: Optional[str] = None,
    request_status: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return total NOC rows for the logged-in user for one module, using HRMS list `total`
    (single lightweight list call with limit=1).
    Optional start_date/end_date (both required together) filter like the HRMS find-all DTOs.
    """
    nt = (noc_type or "").strip()
    if nt not in VALID_NOC_TYPES:
        return _error_result("invalid_noc_type", f"Unknown noc_type: {noc_type}")
    result = await list_my_noc_requests(
        jwt_token,
        nt,
        page=1,
        limit=1,
        query=None,
        start_date=start_date,
        end_date=end_date,
        status=status,
        request_status=request_status,
    )
    if result.get("status") != "success":
        return result
    data = result.get("data")
    total = _extract_total_from_list_payload(data)
    if total is None:
        return {
            "status": "error",
            "error_code": "count_unavailable",
            "message": "The service did not return a total count for this NOC type.",
        }
    out: Dict[str, Any] = {
        "status": "success",
        "noc_type": nt,
        "noc_type_label": NOC_TYPE_LABELS.get(nt, nt),
        "total": total,
    }
    if period_label:
        out["period_label"] = period_label
    if status:
        out["status_filter"] = status
    if request_status:
        out["request_status_filter"] = request_status
    return out


_PHRASE_TO_CODE: Dict[str, str] = {
    phrase: code for phrase, code in NOC_STATUS_PHRASES_ORDERED
}
# Longest phrases first so alternation prefers e.g. "partially approved" over "approved"
_WORKFLOW_PHRASE_ALT = "|".join(
    re.escape(phrase) for phrase, _ in NOC_STATUS_PHRASES_ORDERED
)
_WORKFLOW_PHRASE_RE = re.compile(rf"\b(?:{_WORKFLOW_PHRASE_ALT})\b", re.IGNORECASE)
# Explicit HRMS letter after status / requestStatus / workflow
_EXPLICIT_WORKFLOW_CODE_RE = re.compile(
    r"(?:request\s*status|workflow\s*status|status)\s*[:=]?\s*[\"']?([NTPARDXBCKS])\b",
    re.IGNORECASE,
)


def parse_workflow_status_codes_for_count_breakdown(user_message: str) -> List[str]:
    """
    Detect which workflow status(es) the user asked to count in the same period as the main total.
    Uses labels from NOC_STATUS_LABELS (longest phrase wins overlaps, e.g. Partially Approved vs Approved).
    Also accepts explicit single-letter codes after status/requestStatus/workflow.
    """
    m = (user_message or "").strip()
    if not m:
        return []
    ml = m.lower()
    events: List[Tuple[int, str]] = []

    for mo in _EXPLICIT_WORKFLOW_CODE_RE.finditer(ml):
        letter = mo.group(1).upper()
        if letter in WORKFLOW_STATUS_LETTERS:
            events.append((mo.start(), letter))

    for mo in re.finditer(r"\b(?:how many|number of)\b", ml):
        start = mo.end()
        rest = ml[start:]
        next_q = re.search(r"\b(?:how many|number of)\b", rest)
        chunk = rest[: next_q.start() if next_q else len(rest)]
        chunk = chunk[:220]
        for pmo in _WORKFLOW_PHRASE_RE.finditer(chunk):
            key = pmo.group(0).lower()
            code = _PHRASE_TO_CODE.get(key)
            if code:
                events.append((start + pmo.start(), code))

    events.sort(key=lambda x: x[0])
    out: List[str] = []
    seen: set[str] = set()
    for _, code in events:
        if code not in seen:
            seen.add(code)
            out.append(code)
    return out


# --- Shrink payloads sent to Groq -------------------------------------------------------------

_DROP_KEYS = frozenset(
    {
        "documents",
        "education",
        "edu_documents",
        "employeeDetails",
        "approverDetails",
        "enabled_fields_json",
        "travelEntries",
    }
)


def _summarize_noc_row(row: Any) -> Any:
    if not isinstance(row, dict):
        return row
    slim: Dict[str, Any] = {}
    for key in (
        "id",
        "referenceNumber",
        "reference_number",
        "status",
        "requestStatus",
        "empId",
        "empID",
        "purposeOfVisit",
        "placeOfVisitNoc",
        "requestCreationDate",
        "created_at",
        "approverName",
        "natureOfOutsideJob",
        "WorkflowID",
        "Remarks",
    ):
        if key in row:
            slim[key] = row[key]
    if not slim and row:
        # fallback: keep a few arbitrary scalar keys
        for k, v in list(row.items())[:8]:
            if isinstance(v, (str, int, float, bool)) or v is None:
                slim[k] = v
    return slim


def compact_noc_tool_payload_for_llm(
    result: Dict[str, Any],
    *,
    max_list_preview: int = 12,
    max_str_len: int = 220,
) -> Any:
    """
    Reduce NOC list/detail JSON so Groq requests stay under TPM limits.
    Never rely on the LLM to count rows: preserve `total` when present.
    """
    if not isinstance(result, dict):
        return result
    if result.get("status") != "success":
        return result

    def shrink_value(val: Any, depth: int) -> Any:
        if depth <= 0:
            return None
        if isinstance(val, str):
            if len(val) > max_str_len:
                return val[: max_str_len - 3] + "..."
            return val
        if isinstance(val, (int, float, bool)) or val is None:
            return val
        if isinstance(val, list):
            if len(val) > max_list_preview:
                return [shrink_value(x, depth - 1) for x in val[:max_list_preview]] + [
                    {"_note": f"{len(val) - max_list_preview} more items omitted"}
                ]
            return [shrink_value(x, depth - 1) for x in val]
        if isinstance(val, dict):
            out: Dict[str, Any] = {}
            for k, v in val.items():
                if k in _DROP_KEYS:
                    if isinstance(v, list):
                        out[k] = {"_count_only": len(v)}
                    elif isinstance(v, dict):
                        out[k] = {"_omitted": "nested object"}
                    else:
                        out[k] = shrink_value(v, depth - 1)
                else:
                    out[k] = shrink_value(v, depth - 1)
            return out
        return str(val)[:max_str_len]

    data = result.get("data")
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        rows = data["data"]
        preview = [_summarize_noc_row(r) for r in rows[:max_list_preview]]
        return {
            "status": "success",
            "summary": {
                "total": data.get("total"),
                "page": data.get("page"),
                "limit": data.get("limit"),
                "totalPages": data.get("totalPages"),
                "preview_rows": preview,
                "preview_row_count": len(preview),
                "full_row_count_on_page": len(rows),
            },
        }

    if isinstance(data, dict):
        return {"status": "success", "summary": shrink_value(data, depth=6)}
    return {"status": "success", "summary": shrink_value(data, depth=6)}


def noc_tool_json_for_llm(result: Dict[str, Any], *, max_chars: int = 10000) -> str:
    """JSON-serialize a compacted tool result with a hard character ceiling."""
    compacted = compact_noc_tool_payload_for_llm(result)
    text = json.dumps(compacted, ensure_ascii=False, default=str)
    if len(text) <= max_chars:
        return text
    return json.dumps(
        {
            "_truncated": True,
            "preview": text[: max_chars - 400],
        },
        ensure_ascii=False,
    )
