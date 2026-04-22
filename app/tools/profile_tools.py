"""
Employee profile tools — read-only. Uses HRMS EmployeesController:
POST /employees/my-profile (JWT → req.user.id / empId → employeeProfile).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.tools.hrms_client import hrms_client

logger = logging.getLogger(__name__)

PROFILE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_my_employee_profile",
            "description": (
                "Fetch the logged-in employee's full HRMS profile (identity, job, contacts, "
                "addresses, banks, family, education, etc.). Use this to answer questions about "
                "the employee's own PAN, Aadhaar, department, designation, manager, and other "
                "profile fields returned by HRMS."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    }
]

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "token",
        "otp_code",
        "device_token",
        "device_id",
        "device_type",
        "left_face",
        "right_face",
        "top_face",
        "center_face",
    }
)


def _strip_sensitive(obj: Any) -> Any:
    """Remove secrets, auth fields, and large binary blobs from HRMS profile JSON."""
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for key, val in obj.items():
            lk = key.lower()
            if key in _SENSITIVE_KEYS or lk in _SENSITIVE_KEYS:
                continue
            if lk == "image" and isinstance(val, str) and len(val) > 240:
                continue
            out[key] = _strip_sensitive(val)
        return out
    if isinstance(obj, list):
        return [_strip_sensitive(x) for x in obj]
    return obj


def _error_message(error_code: str) -> str:
    messages = {
        "access_denied": "You do not have access to this profile information.",
        "not_found": "No profile record was found.",
        "unauthorized": (
            "HRMS could not accept your login token for profile data (unauthorized). "
            "Sign in again in the HRMS app or portal so you get a fresh token, then retry this chat."
        ),
        "timeout": "The request took too long. Please try again.",
    }
    return messages.get(error_code, "An error occurred while fetching profile data.")


def _looks_like_employee_profile(d: dict) -> bool:
    """Detect the TypeORM employee root (not an outer CommonResponseDto envelope)."""
    if d.get("empId") not in (None, ""):
        return True
    details = d.get("details")
    if isinstance(details, dict) and any(
        details.get(k) not in (None, "")
        for k in (
            "fullName",
            "firstname",
            "pay_scale",
            "panNumber",
            "aadhaarId",
            "department",
            "designationID",
            "email",
            "phone",
        )
    ):
        return True
    if isinstance(d.get("addresses"), list) and len(d["addresses"]) > 0:
        return True
    if isinstance(d.get("banks"), list) and len(d["banks"]) > 0:
        return True
    # employees table columns often present on serialized entity
    if d.get("usrid") not in (None, "") or d.get("is_verified") not in (None, ""):
        return True
    return False


def _unwrap_hrms_profile_payload(payload: Any) -> Any:
    """
    HRMS may return createResponse DTO once or nested (data inside data).
    Drill down until we reach the employee profile object.
    """
    cur: Any = payload
    for _ in range(8):
        if not isinstance(cur, dict):
            return cur
        if _looks_like_employee_profile(cur):
            return cur
        nxt = cur.get("data")
        if isinstance(nxt, dict):
            cur = nxt
            continue
        return cur
    logger.warning("Profile unwrap stopped at max depth; keys=%s", list(cur.keys())[:20] if isinstance(cur, dict) else type(cur))
    return cur


async def get_my_employee_profile(jwt_token: str) -> Dict[str, Any]:
    """
    Load current user's profile from HRMS (POST /employees/my-profile, empty body).
    """
    result = await hrms_client.call_api(
        "/employees/my-profile",
        jwt_token,
        method="POST",
        body={},
    )

    if "error" in result:
        return {
            "status": "error",
            "error_code": result["error"],
            "message": _error_message(result["error"]),
        }

    raw = result.get("data")
    if raw is None:
        return {"status": "error", "error_code": "empty_response", "message": _error_message("not_found")}

    entity = _unwrap_hrms_profile_payload(raw)
    if not isinstance(entity, dict) or not _looks_like_employee_profile(entity):
        logger.warning(
            "Unexpected profile payload shape after unwrap; top_keys=%s",
            list(entity.keys())[:30] if isinstance(entity, dict) else type(entity),
        )

    safe = _strip_sensitive(entity)
    return {"status": "success", "data": safe}
