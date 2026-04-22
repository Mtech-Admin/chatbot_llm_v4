"""
Unwrap HRMS JSON after ResponseInterceptor + createResponse.

Typical shape from httpx:
  { "data": { "status": 200, "message": "...", "data": <T> } }
where <T> is list payload { "data": [...], "total" } } or a single object.

See app/tools/leave_tools._unwrap_hrms_body (same idea).
"""

from __future__ import annotations

from typing import Any, Dict


def unwrap_hrms_api_payload(result: Dict[str, Any]) -> Any:
    """
    Return the inner business payload T. Pass through error-payload dicts unchanged.
    """
    if "error" in result:
        return result
    if not isinstance(result, dict):
        return result

    # ResponseInterceptor: root is { "data": createResponse }
    outer = result.get("data")
    if not isinstance(outer, dict):
        return result

    if "message" in outer and "data" in outer:
        return outer.get("data")

    # createResponse at root (rare, no extra interceptor)
    if "message" in result and "data" in result and "status" in result:
        return result.get("data")

    return result


def unwrap_hrms_fully(root: Dict[str, Any]) -> Any:
    """
    Apply unwrap_hrms_api_payload until fixed point (ResponseInterceptor + createResponse peeler).
    """
    if "error" in root:
        return root
    cur: Any = root
    for _ in range(6):
        if not isinstance(cur, dict):
            return cur
        nxt = unwrap_hrms_api_payload(cur)
        if nxt is cur:
            return cur
        cur = nxt
    return cur
