"""
VPF (Voluntary Provident Fund) — read-only list/detail via HRMS:
POST /vpf-request/find-all, POST /vpf-request/find-one
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

from app.tools.hrms_client import hrms_client
from app.tools.hrms_unwrap import unwrap_hrms_fully
from app.tools.noc_tools import (  # reuse list total + workflow phrase helpers
    _extract_total_from_list_payload,
    parse_workflow_status_codes_for_count_breakdown,
)
from app.tools.vpf_status import expand_vpf_statuses_in_payload

logger = logging.getLogger(__name__)


def _error_result(code: str, message: str) -> Dict[str, Any]:
    return {"status": "error", "error_code": code, "message": message}


def _success_payload(raw: Any) -> Dict[str, Any]:
    expanded = expand_vpf_statuses_in_payload(raw)
    return {"status": "success", "data": expanded}


def _friendly_error(code: str) -> str:
    return {
        "access_denied": "You do not have access to this VPF information.",
        "not_found": "No matching VPF request was found.",
        "unauthorized": "Your login could not be validated for HRMS. Please sign in again and retry.",
        "timeout": "The request took too long. Please try again.",
    }.get(code, "Something went wrong while fetching VPF data.")


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


VPF_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_my_vpf_requests",
            "description": (
                "List the logged-in employee's VPF (Voluntary Provident Fund) requests in HRMS "
                "(the same data as the app for the current session token — not for another user). "
                "Use pagination and optional filters. Status fields in results use full labels, not single letters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {
                        "type": "string",
                        "description": "Page number (default 1).",
                    },
                    "limit": {
                        "type": "string",
                        "description": "Page size (default 20, max 50).",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search by reference number (optional).",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Filter range start (ISO). Use with end_date.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Filter range end (ISO). Use with start_date.",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status letter or label if needed.",
                    },
                    "request_status": {
                        "type": "string",
                        "description": "Filter by RequestStatus / workflow code (e.g. A for Approved).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_vpf_request_details",
            "description": "Full details for one VPF request by numeric database id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "VPF request id (number as string, from list results).",
                    }
                },
                "required": ["request_id"],
            },
        },
    },
]


async def list_my_vpf_requests(
    jwt_token: str,
    page: Union[int, str] = 1,
    limit: Union[int, str] = 20,
    query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    request_status: Optional[str] = None,
) -> Dict[str, Any]:
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

    result = await hrms_client.call_api(
        "/vpf-request/find-all", jwt_token, method="POST", body=body
    )
    if "error" in result:
        return _error_result(result["error"], _friendly_error(result["error"]))
    payload = unwrap_hrms_fully(result)
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        logger.info(
            "VPF find-all: total=%s rows_on_page=%s",
            payload.get("total"),
            len(payload["data"]),
        )
    return _success_payload(payload)


async def get_vpf_request_details(jwt_token: str, request_id: str) -> Dict[str, Any]:
    rid = (request_id or "").strip()
    if not rid:
        return _error_result("invalid_request_id", "request_id is required.")
    try:
        num_id = int(rid)
    except ValueError:
        return _error_result("invalid_request_id", "request_id must be a number.")

    result = await hrms_client.call_api(
        "/vpf-request/find-one", jwt_token, method="POST", body={"id": num_id}
    )
    if "error" in result:
        return _error_result(result["error"], _friendly_error(result["error"]))
    payload = unwrap_hrms_fully(result)
    return _success_payload(payload)


def message_asks_for_vpf_count(user_message: str) -> bool:
    m = (user_message or "").lower()
    if not m.strip():
        return False
    if re.search(
        r"\b(vpf|voluntary\s*provident|provident\s*fund|employee\s*vpf)\b", m
    ) and re.search(r"\b(how many|number of|count|total)\b", m):
        return True
    if re.search(r"\b(how many|number of|count|total)\b", m) and re.search(
        r"\bvpf\s+request", m
    ):
        return True
    return False


async def count_vpf_requests_for_employee(
    jwt_token: str,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period_label: Optional[str] = None,
    request_status: Optional[str] = None,
) -> Dict[str, Any]:
    result = await list_my_vpf_requests(
        jwt_token,
        page=1,
        limit=1,
        start_date=start_date,
        end_date=end_date,
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
            "message": "The service did not return a total count for VPF requests.",
        }
    out: Dict[str, Any] = {
        "status": "success",
        "total": int(total),
    }
    if period_label:
        out["period_label"] = period_label
    if request_status:
        out["request_status_filter"] = request_status
    return out


def compact_vpf_tool_payload_for_llm(result: Dict[str, Any]) -> Dict[str, Any]:
    if result.get("status") != "success":
        return result
    data = result.get("data")
    if isinstance(data, dict) and "data" in data and isinstance(data.get("data"), list):
        rows = data["data"]
        preview = rows[:8]
        return {
            "status": "success",
            "summary": {
                "total": data.get("total"),
                "page": data.get("page"),
                "limit": data.get("limit"),
                "totalPages": data.get("totalPages"),
                "preview_rows": expand_vpf_statuses_in_payload(preview),
                "preview_row_count": len(preview),
                "full_row_count_on_page": len(rows),
            },
        }
    if isinstance(data, dict):
        return {"status": "success", "summary": data}
    return {"status": "success", "summary": data}


def vpf_tool_json_for_llm(result: Dict[str, Any], *, max_chars: int = 10_000) -> str:
    compacted = compact_vpf_tool_payload_for_llm(result)
    text = json.dumps(compacted, ensure_ascii=False, default=str)
    if len(text) <= max_chars:
        return text
    return json.dumps(
        {"_truncated": True, "preview": text[: max_chars - 400]},
        ensure_ascii=False,
    )
