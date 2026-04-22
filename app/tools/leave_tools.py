"""
Leave & public holiday tools — READ-ONLY HRMS API calls (JWT passthrough).
Mirrors DMRC_HRMS_API leave + public_holidays controllers.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Union

from app.tools.hrms_client import hrms_client
from app.tools.leave_field_mapping import enrich_leave_payload, enrich_leave_record

logger = logging.getLogger(__name__)


def _error_message(code: str) -> str:
    return {
        "access_denied": "You do not have access to this information.",
        "unauthorized": "Your session is not valid. Please sign in again.",
        "not_found": "No data was found for this request.",
        "timeout": "The HRMS service took too long to respond. Please try again.",
    }.get(code, "Something went wrong while contacting HRMS.")


def _unwrap_hrms_body(result: Dict[str, Any]) -> Any:
    """Unwrap { data: { status, message, data: T } } from ResponseInterceptor + createResponse."""
    if "error" in result:
        return None
    outer = result.get("data")
    if isinstance(outer, dict) and "data" in outer:
        return outer.get("data")
    return outer


async def _post(jwt_token: str, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    result = await hrms_client.call_api(path, jwt_token, method="POST", body=body)
    if "error" in result:
        return {
            "status": "error",
            "error_code": result["error"],
            "message": _error_message(result["error"]),
        }
    payload = _unwrap_hrms_body(result)
    return {"status": "success", "data": payload}


def _to_int(v: Union[int, str, None], default: int, *, min_value: int = 1, max_value: int = 500) -> int:
    try:
        if v is None or v == "":
            return default
        n = int(str(v).strip())
        return max(min_value, min(max_value, n))
    except (TypeError, ValueError):
        return default


# --- Tools exposed to LLM ---

LEAVE_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_leave_types",
            "description": "List leave type masters (codes, names, approvers) configured in HRMS.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_leave_absence_types",
            "description": "Absence/leave types available to the employee and related metadata (balances may appear per SAP rules).",
            "parameters": {
                "type": "object",
                "properties": {
                    "emp_id": {
                        "type": "string",
                        "description": "Employee ID; omit to use logged-in user.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_leave_time_accounts",
            "description": "Leave time accounts / quotas for the employee (balances, entitlements). Optional filters by leave type code and date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "emp_id": {"type": "string", "description": "Employee ID; omit for logged-in user."},
                    "leave_type": {"type": "string", "description": "Optional TimeAccountTypeCode / leave type code filter."},
                    "from_date": {"type": "string", "description": "YYYY-MM-DD start (optional)."},
                    "to_date": {"type": "string", "description": "YYYY-MM-DD end (optional)."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_leave_requests",
            "description": "Fetch leave requests for the employee. filter_by is required by HRMS (e.g. 'date'). Use date_range for a window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "emp_id": {"type": "string"},
                    "filter_by": {
                        "type": "string",
                        "description": "HRMS filter key, typically 'date' for date-based listing.",
                    },
                    "date_from": {"type": "string", "description": "YYYY-MM-DD"},
                    "date_to": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["filter_by"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_leave_calendar",
            "description": "Calendar view of leave/absences for the employee between two dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "emp_id": {"type": "string"},
                    "from_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "to_date": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["from_date", "to_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_saved_leave_requests",
            "description": "Paginated list of leave requests stored in HRMS for this employee (local DB mirror).",
            "parameters": {
                "type": "object",
                "properties": {
                    "emp_id": {"type": "string"},
                    "page": {"type": "string", "description": "Page number (default 1)."},
                    "limit": {"type": "string", "description": "Page size (default 20)."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_leave_request_by_id",
            "description": "Details for one leave request by RequestID, including CUSTOMER fields (mapped to labels in tool output).",
            "parameters": {
                "type": "object",
                "properties": {"request_id": {"type": "string", "description": "Leave RequestID from HRMS."}},
                "required": ["request_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_public_holiday_calendar",
            "description": "Official holiday list for a calendar year from HRMS (GET via POST /misc/holidays, master_holiday_calendar in DB). Use for upcoming holidays and full-year lists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {
                        "type": "string",
                        "description": "Calendar year (e.g. 2026). Omit to use the current year.",
                    }
                },
                "required": [],
            },
        },
    },
]


async def get_leave_types(jwt_token: str) -> Dict[str, Any]:
    return await _post(jwt_token, "/leave/leave-types", {})


async def get_my_leave_absence_types(jwt_token: str, emp_id: str) -> Dict[str, Any]:
    return await _post(jwt_token, "/leave/emp-leave-absence-type", {"empId": emp_id})


async def get_my_leave_time_accounts(
    jwt_token: str,
    emp_id: str,
    leave_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"empId": emp_id}
    if leave_type:
        body["leaveType"] = leave_type
    if from_date:
        body["fromDate"] = from_date
    if to_date:
        body["toDate"] = to_date
    return await _post(jwt_token, "/leave/emp-leave-time-accounts", body)


async def get_my_leave_requests(
    jwt_token: str,
    emp_id: str,
    filter_by: str,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"filter_by": filter_by, "empId": emp_id}
    if date_from and date_to:
        body["date_range"] = {"from": date_from, "to": date_to}
    out = await _post(jwt_token, "/leave/leave-requests", body)
    if out.get("status") == "success":
        out["data"] = enrich_leave_payload(out.get("data"))
    return out


async def get_my_leave_calendar(
    jwt_token: str,
    emp_id: str,
    from_date: str,
    to_date: str,
) -> Dict[str, Any]:
    body = {"empId": emp_id, "from": from_date, "to": to_date}
    out = await _post(jwt_token, "/leave/emp-leave-calendar", body)
    if out.get("status") == "success":
        out["data"] = enrich_leave_payload(out.get("data"))
    return out


async def get_my_saved_leave_requests(
    jwt_token: str,
    employee_id: str,
    page: Union[int, str] = 1,
    limit: Union[int, str] = 20,
) -> Dict[str, Any]:
    safe_page = _to_int(page, 1, min_value=1, max_value=5000)
    safe_limit = _to_int(limit, 20, min_value=1, max_value=100)
    body: Dict[str, Any] = {"EmployeeID": employee_id, "page": safe_page, "limit": safe_limit}
    out = await _post(jwt_token, "/leave/get-all-leaves", body)
    if out.get("status") == "success":
        out["data"] = enrich_leave_payload(out.get("data"))
    return out


async def get_leave_request_by_id(jwt_token: str, request_id: str) -> Dict[str, Any]:
    out = await _post(jwt_token, "/leave/get-leave-request-by-id", {"requestID": request_id})
    if out.get("status") == "success" and isinstance(out.get("data"), dict):
        out["data"] = enrich_leave_record(out["data"])
    return out


async def get_public_holiday_calendar(
    jwt_token: str,
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    HRMS: POST /misc/holidays with { year: number } — reads master_holiday_calendar (reliable, DB-backed).
    """
    y = year if year is not None else date.today().year
    try:
        y = int(y)
    except (TypeError, ValueError):
        y = date.today().year
    body = {"year": y}
    return await _post(jwt_token, "/misc/holidays", body)


def _parse_holiday_row_date(row: Dict[str, Any]) -> Optional[date]:
    """Date from master_holiday_calendar row or legacy SAP DTO row."""
    for key in (
        "date",
        "Date",
        "PublicHolidayDate",
        "publicHolidayDate",
        "HolidayDate",
    ):
        v = row.get(key)
        if v is None:
            continue
        if isinstance(v, str) and len(v) >= 10:
            try:
                y, m, d = int(v[0:4]), int(v[5:7]), int(v[8:10])
                return date(y, m, d)
            except (ValueError, TypeError):
                continue
    return None


def _sort_key_holiday_row(row: Dict[str, Any]) -> str:
    d = _parse_holiday_row_date(row)
    if d is not None:
        return d.isoformat()
    return str(row.get("Date") or row.get("date") or "")


def upcoming_holidays_from_payload(
    rows: Any,
    *,
    today: Optional[date] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Filter holiday list to items on or after today (master_holiday_calendar and SAP DTOs)."""
    td = today or date.today()
    if not isinstance(rows, list):
        return []
    upcoming: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        d = _parse_holiday_row_date(row)
        if d is not None:
            if d >= td:
                upcoming.append(row)
        else:
            # Unknown date shape — keep row so the LLM is not starved; user can still see the list
            upcoming.append(row)
    upcoming.sort(key=_sort_key_holiday_row)
    return upcoming[:limit]
