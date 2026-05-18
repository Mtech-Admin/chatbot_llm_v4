"""
Employee profile agent — answers read-only questions about the logged-in user's HRMS profile.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.config import get_llm_client, get_model_name
from app.llm.chat_completions import chat_completions_create
from app.orchestrator.state import OrchestratorState
from app.tools.profile_tools import (
    get_my_employee_profile,
    persist_profile_details_session_cache,
)

logger = logging.getLogger(__name__)

PROFILE_AGENT_PROMPT = """You are the Employee Profile Agent for DMRC HRMS.

Purpose: Answer questions about the logged-in employee's own HRMS profile (identity, job, tax IDs,
contact details, addresses, bank accounts shown in HRMS, reporting manager / manager / CO / supervisor, shift, etc.).

Synonyms (treat as the same read-only topic when the snapshot has the data):
- "Reporting manager", "manager", "boss", "supervisor", "controlling officer", "CO", "C.O." → use `details.manager` (nested name, email, phone, job/department text) and `details.reportingManagerID` / approvers if present.
- Work timing on record: "shift", "duty shift", "roster", "work schedule", "WS rule", "checkout type" → use `shift`, `employee_work_schedules` (e.g. `dWSRuleText`, `holidayCalID`, `workdays`, `wSrule`).

Rules:
- READ-ONLY: Never suggest or perform updates; if the user wants to change data, tell them to use the HRMS portal.
- Use ONLY facts present in the profile data JSON. If a field is missing or null, say it is not available in their HRMS record.
- Do not guess PAN, Aadhaar, bank account numbers, or any other value.
- Do not repeat huge tables unless asked; prefer a direct answer, then offer to share more.
- Never paste raw JSON in the reply; write natural language.
- Never mention APIs, endpoints, tools, or "HRMS response".
- Treat nested `details` as the main personal/job record when present (e.g. panNumber, department codes, designationID).
- Organizational names often appear under `department_job_org` inside `details` (department_name, designation_name, job_name, wing_name) and similarly under `details.manager` for the reporting manager.
- For the user's name or "what is my name": answer from the top-level `display_name` when present; otherwise combine `firstname`, `secondname`, `lsastname` (or `lastname`) from `details` only if those fields exist in the snapshot.
- For salary or pay-scale questions on record: use `details.basicSalary`, `details.pay_scale`, `details.category`, `details.vPFAmount` when present — do not invent amounts.
- Shift and timing questions: use `shift` (work_shift name, start/end, checkout_type, grace periods, break minutes) and `employee_work_schedules` (weekly pattern / holiday calendar text, `dWSRuleText`, `wSrule`) when provided.
- Reply in the user's language when the user writes in Hindi or English; keep proper nouns (shift codes, department names) as in the record.
- Family, schooling, tenure elsewhere: check `familyMembers`, `education`, `employers` (prior employers), plus `addresses`, `banks`, `approvers`, and `offices` as needed — only when the user asks.
"""


class ProfileAgent(BaseAgent):
    def __init__(self):
        super().__init__("profile_agent", PROFILE_AGENT_PROMPT)

    async def process(self, state: OrchestratorState) -> OrchestratorState:
        try:
            cached = state.cached_profile_snapshot
            fetched_from_network = False
            if isinstance(cached, dict) and cached.get("empId") not in (None, ""):
                if str(cached.get("empId")).strip() != str(state.employee_id).strip():
                    logger.warning(
                        "Profile cache empId mismatch; refetching. cache=%s state=%s",
                        cached.get("empId"),
                        state.employee_id,
                    )
                    cached = None
            if cached:
                logger.info(
                    "Profile agent using Redis session cache for employee %s session %s",
                    state.employee_id,
                    state.session_id,
                )
                profile_result = {"status": "success", "data": cached}
            else:
                profile_result = await get_my_employee_profile(state.jwt_token)
                fetched_from_network = profile_result.get("status") == "success"

            if profile_result.get("status") != "success":
                state.response_message = profile_result.get(
                    "message",
                    "I was not able to load your profile right now. Please try again in a moment.",
                )
                state.routing_agent = "profile_agent"
                return state

            safe_data = profile_result.get("data") or {}

            client = get_llm_client()
            model = get_model_name()
            context_prompt = self._build_context_prompt(state)
            profile_snapshot = self._build_profile_snapshot(safe_data)

            logger.info(
                "Profile agent started for employee %s, session %s (from_network=%s)",
                state.employee_id,
                state.session_id,
                fetched_from_network,
            )

            response = await chat_completions_create(
                client,
                model=model,
                max_tokens=2048,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"{context_prompt}\n\n"
                            "Use the profile snapshot below to answer the current user message.\n"
                            "If a requested field is not present, say it is not available on record.\n"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"User question: {state.user_message}\n\n"
                            f"Profile snapshot JSON:\n{json.dumps(profile_snapshot, ensure_ascii=False)}"
                        ),
                    },
                ],
            )

            state.response_message = (
                response.choices[0].message.content
                or "I could not find that profile detail right now."
            )
            state.routing_agent = "profile_agent"

            if fetched_from_network and isinstance(safe_data, dict) and safe_data:
                await persist_profile_details_session_cache(
                    state.session_id,
                    state.employee_id,
                    safe_data,
                )

            return state
        except Exception as e:
            logger.error(
                "Error in profile agent for employee %s: %s",
                state.employee_id,
                str(e),
                exc_info=True,
            )
            state.response_message = (
                "I was not able to load your profile right now. Please try again in a moment."
            )
            return state

    def _build_profile_snapshot(self, profile_data: Any) -> dict[str, Any]:
        """
        Structured slice of HRMS employee full-details for the LLM (omit bulky geometry).
        """

        def without_coords(office_list: Any) -> list[dict[str, Any]]:
            out: list[dict[str, Any]] = []
            for o in (office_list or [])[:12]:
                if not isinstance(o, dict):
                    continue
                trimmed = {k: v for k, v in o.items() if k != "coordinates"}
                out.append(trimmed)
            return out

        def mgr_block(mgr: Any) -> dict[str, Any]:
            if not isinstance(mgr, dict):
                return {}
            m_wing = mgr.get("manager_sap_department_designation_wings") or mgr.get(
                "sap_department_designation_wings"
            )
            m_desig = mgr.get("manager_designation_details") or mgr.get(
                "designation_details"
            )
            name_parts: list[str] = []
            for key in ("firstname", "secondname", "lsastname", "lastname"):
                v = mgr.get(key)
                if isinstance(v, str) and v.strip():
                    name_parts.append(v.strip())
            mgr_display = " ".join(name_parts)
            return {
                "empId": mgr.get("empId"),
                "firstname": mgr.get("firstname"),
                "secondname": mgr.get("secondname"),
                "lsastname": mgr.get("lsastname"),
                "manager_display_name": mgr_display,
                "email": mgr.get("email"),
                "phone": mgr.get("phone"),
                "department": mgr.get("department"),
                "designationID": mgr.get("designationID"),
                "pay_scale": mgr.get("pay_scale"),
                "employmentType": mgr.get("employmentType"),
                "date_of_joining": mgr.get("date_of_joining"),
                "designation_details": (
                    {
                        "shortText": (m_desig or {}).get("shortText"),
                        "longText": (m_desig or {}).get("longText"),
                    }
                    if isinstance(m_desig, dict)
                    else None
                ),
                "department_job": (
                    {
                        "department_name": (m_wing or {}).get("department_name"),
                        "wing_name": (m_wing or {}).get("wing_name"),
                        "job_name": (m_wing or {}).get("job_name"),
                        "designation_name": (m_wing or {}).get("designation_name"),
                    }
                    if isinstance(m_wing, dict)
                    else None
                ),
            }

        def compose_display_name(root: dict[str, Any], det: dict[str, Any]) -> str:
            full = det.get("fullName") or root.get("fullName")
            if isinstance(full, str):
                s = full.strip()
                if s:
                    return s
            parts: list[str] = []
            for key in ("firstname", "secondname", "lsastname", "lastname"):
                v = det.get(key)
                if isinstance(v, str):
                    t = v.strip()
                    if t:
                        parts.append(t)
            return " ".join(parts)

        def shift_summary(shift_blob: Any) -> dict[str, Any]:
            if not isinstance(shift_blob, dict):
                return {}
            ws = shift_blob.get("work_shift")
            if isinstance(ws, dict):
                return {
                    "verified": shift_blob.get("is_verified"),
                    "shift_name": ws.get("shift_name"),
                    "shift_code": ws.get("shift_code"),
                    "shift_description": ws.get("shift_description"),
                    "start_time": ws.get("start_time"),
                    "end_time": ws.get("end_time"),
                    "checkout_type": ws.get("checkout_type"),
                    "break_time_in_minutes": ws.get("break_time_in_minutes"),
                    "attendance_grace_time": ws.get("attendance_grace_time"),
                    "attendance_margin_time": ws.get("attendance_margin_time"),
                    "attendance_half_day_margin_time": ws.get(
                        "attendance_half_day_margin_time"
                    ),
                    "shift_end_grace_time": ws.get("shift_end_grace_time"),
                    "half_day_start_time": ws.get("half_day_start_time"),
                }
            return {"raw": shift_blob}

        if not isinstance(profile_data, dict):
            return {"profile": profile_data}

        details = profile_data.get("details") or {}
        dept_row = (
            details.get("sap_department_designation_wings")
            if isinstance(details.get("sap_department_designation_wings"), dict)
            else None
        )
        des_row = (
            details.get("designation_details")
            if isinstance(details.get("designation_details"), dict)
            else None
        )

        snapshot: dict[str, Any] = {
            "empId": profile_data.get("empId"),
            "usrid": profile_data.get("usrid"),
            "user_type": profile_data.get("user_type"),
            "login_on": profile_data.get("login_on"),
            "validity_window": {
                "validityStart": profile_data.get("validityStart"),
                "validityEnd": profile_data.get("validityEnd"),
            },
            "verification": {"is_verified": profile_data.get("is_verified")},
            "emp_role": profile_data.get("emp_role"),
            "employee_work_schedules": profile_data.get("employee_work_schedules"),
            "shift": shift_summary(profile_data.get("shift")),
            "employers": (profile_data.get("employers") or [])[:20],
            "details": {
                "fullName": details.get("fullName"),
                "firstname": details.get("firstname"),
                "secondname": details.get("secondname"),
                "lsastname": details.get("lsastname"),
                "email": details.get("email"),
                "phone": details.get("phone"),
                "blood_group": details.get("blood_group"),
                "marital_status": details.get("marital_status"),
                "birthdate": details.get("birthdate"),
                "birthplace": details.get("birthplace"),
                "nationality1": details.get("nationality1"),
                "gender": details.get("gender"),
                "date_of_joining": details.get("date_of_joining"),
                "wing": details.get("wing"),
                "employmentType": details.get("employmentType"),
                "category": details.get("category"),
                "empStatus": details.get("empStatus"),
                "department": details.get("department"),
                "designationID": details.get("designationID"),
                "pay_scale": details.get("pay_scale"),
                "basicSalary": details.get("basicSalary"),
                "vPFAmount": details.get("vPFAmount"),
                "lwp": details.get("lwp"),
                "aadhaarId": details.get("aadhaarId"),
                "panNumber": details.get("panNumber"),
                "reportingManagerID": details.get("reportingManagerID"),
                "reportingManagerName": details.get("reportingManagerName"),
                "designation_details": (
                    {
                        "shortText": des_row.get("shortText"),
                        "longText": des_row.get("longText"),
                    }
                    if des_row
                    else None
                ),
                "department_job_org": (
                    {
                        "department_name": dept_row.get("department_name"),
                        "wing_name": dept_row.get("wing_name"),
                        "job_name": dept_row.get("job_name"),
                        "designation_name": dept_row.get("designation_name"),
                    }
                    if dept_row
                    else None
                ),
                "manager": mgr_block(details.get("manager")),
            },
            "addresses": (profile_data.get("addresses") or [])[:24],
            "banks": (profile_data.get("banks") or [])[:8],
            "education": (profile_data.get("education") or [])[:24],
            "familyMembers": (profile_data.get("familyMembers") or [])[:24],
            "emergency_contacts": (profile_data.get("emergency_contacts") or [])[:12],
            "approvers": (profile_data.get("approvers") or [])[:12],
            "offices": without_coords(profile_data.get("offices")),
            "settings": profile_data.get("settings"),
            "verificationReasons": profile_data.get("verificationReasons"),
        }
        account_st = profile_data.get("status")
        if isinstance(account_st, str) and profile_data.get("details"):
            snapshot["account_lock_status_label"] = account_st
            snapshot["employment_status_emp_detail"] = details.get("empStatus")
        snapshot["display_name"] = compose_display_name(profile_data, details)
        return snapshot
