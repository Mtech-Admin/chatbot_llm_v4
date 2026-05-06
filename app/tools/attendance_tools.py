"""
Attendance Agent Tools - READ-ONLY operations for viewing attendance data
All tools pass JWT token through to HRMS API
"""

from typing import Any, Dict, Optional, Union
from app.tools.hrms_client import hrms_client
import json

# Tool schemas for LLM
ATTENDANCE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_my_attendance",
            "description": "Get employee's attendance records for a specific month and year",
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": "string",
                        "description": "Month number (1-12)"
                    },
                    "year": {
                        "type": "string",
                        "description": "Year (e.g., yyyy)"
                    },
                    "page": {
                        "type": "string",
                        "description": "Page number for pagination (default 1). Numeric string allowed."
                    },
                    "limit": {
                        "type": "string",
                        "description": "Records per page (default 20). Numeric string allowed."
                    }
                },
                "required": ["month", "year"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_daily_attendance",
            "description": "Get employee's daily attendance record for a specific date",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    }
                },
                "required": ["date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_team_attendance",
            "description": "Get team's daily attendance (manager only)",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    }
                }
            }
        }
    }
]

async def get_my_attendance(
    jwt_token: str,
    month: str,
    year: str,
    page: Union[int, str] = 1,
    limit: Union[int, str] = 20,
) -> Dict[str, Any]:
    """
    Get employee's attendance records for a specific month/year
    
    Args:
        jwt_token: Employee's JWT token
        month: Month number (1-12)
        year: Year (e.g., yyyy)
        page: Page number (default 1)
        limit: Records per page (default 20)
    
    Returns:
        Attendance records from HRMS API
    """
    safe_page = _to_int(page, default=1, min_value=1)
    safe_limit = _to_int(limit, default=20, min_value=1, max_value=100)

    body = {
        "month": month,
        "year": year,
        "page": safe_page,
        "limit": safe_limit
    }
    
    result = await hrms_client.call_api(
        "/employee-attendance/my-attendance",
        jwt_token,
        method="POST",
        body=body
    )
    
    if "error" in result:
        return {
            "status": "error",
            "error_code": result["error"],
            "message": _error_message(result["error"])
        }
    
    payload = _extract_attendance_payload(result)
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    compact_rows = []
    for row in rows if isinstance(rows, list) else []:
        compact_rows.append(
            {
                "date": (row.get("check_in_time") or row.get("created_at") or "")[:10],
                "attendance_status": row.get("attendance_status"),
                "attendance_work_type": row.get("attendance_work_type"),
                "work_day_type": row.get("work_day_type"),
                "late_coming": bool(row.get("late_coming")),
                "early_leaving": bool(row.get("early_leaving")),
                "check_in_time": row.get("check_in_time"),
                "check_out_time": row.get("check_out_time"),
                "working_hours": row.get("working_hours"),
            }
        )

    return {
        "status": "success",
        "data": {
            "month": payload.get("month"),
            "year": payload.get("year"),
            "total": payload.get("total", 0),
            "present": payload.get("present", 0),
            "absent": payload.get("absent", 0),
            "half_day": payload.get("half_day", 0),
            "late_coming": payload.get("late_coming", 0),
            "early_leaving": payload.get("early_leaving", 0),
            "holiday": payload.get("holiday", 0),
            "records": compact_rows,
        },
        "pagination": {
            "page": safe_page,
            "limit": safe_limit,
            "total": payload.get("total", 0) if isinstance(payload, dict) else 0,
        }
    }

async def get_my_daily_attendance(
    jwt_token: str,
    date: str
) -> Dict[str, Any]:
    """
    Get employee's daily attendance record
    
    Args:
        jwt_token: Employee's JWT token
        date: Date in YYYY-MM-DD format
    
    Returns:
        Daily attendance record
    """
    body = {
        "date": date
    }
    
    result = await hrms_client.call_api(
        "/employee-attendance/my-daily-attendance",
        jwt_token,
        method="POST",
        body=body
    )
    
    if "error" in result:
        return {
            "status": "error",
            "error_code": result["error"],
            "message": _error_message(result["error"])
        }
    
    return {
        "status": "success",
        "data": result.get("data", {})
    }

async def get_team_attendance(
    jwt_token: str,
    employee_id: str,
    date: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get team's attendance (manager only - API enforces scope)
    
    Args:
        jwt_token: Manager's JWT token
        employee_id: Manager's employee ID (for audit logging)
        date: Single date in YYYY-MM-DD format
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
    
    Returns:
        Team attendance records
    """
    body = {}
    if date:
        body["date"] = date
    if from_date and to_date:
        body["from_date"] = from_date
        body["to_date"] = to_date
    
    result = await hrms_client.call_api(
        "/employee-attendance/team-daily-attendance",
        jwt_token,
        method="POST",
        body=body
    )
    
    if "error" in result:
        return {
            "status": "error",
            "error_code": result["error"],
            "message": _error_message(result["error"])
        }
    
    return {
        "status": "success",
        "data": result.get("data", [])
    }

def _error_message(error_code: str) -> str:
    """Get user-friendly error message"""
    messages = {
        "access_denied": "You don't have access to this information. Please contact HR or your manager.",
        "not_found": "No attendance records found for the requested period.",
        "unauthorized": "Your session has expired. Please log in again.",
        "timeout": "The request took too long. Please try again.",
    }
    return messages.get(error_code, "An error occurred while fetching attendance data.")


def _to_int(value: Any, default: int, min_value: int = 1, max_value: Optional[int] = None) -> int:
    """Parse int from model/tool inputs with safe bounds."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default

    if parsed < min_value:
        return default
    if max_value is not None and parsed > max_value:
        return max_value
    return parsed


def _extract_attendance_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize HRMS response shapes for attendance list endpoint.
    Common variants:
    - {"data": {"status": 201, "message": "...", "data": {...}}}
    - {"status": 201, "message": "...", "data": {...}}
    - {"data": {...}}
    """
    if not isinstance(result, dict):
        return {}
    top = result.get("data")
    if isinstance(top, dict):
        nested = top.get("data")
        if isinstance(nested, dict):
            return nested
        return top
    return {}
