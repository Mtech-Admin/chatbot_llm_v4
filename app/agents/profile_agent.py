"""
Employee profile agent — answers read-only questions about the logged-in user's HRMS profile.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import BaseAgent
from app.config import get_llm_client, get_model_name
from app.orchestrator.state import OrchestratorState
from app.tools.profile_tools import get_my_employee_profile

logger = logging.getLogger(__name__)

PROFILE_AGENT_PROMPT = """You are the Employee Profile Agent for DMRC HRMS.

Purpose: Answer questions about the logged-in employee's own HRMS profile (identity, job, tax IDs,
contact details, addresses, bank accounts shown in HRMS, reporting manager, etc.).

Rules:
- READ-ONLY: Never suggest or perform updates; if the user wants to change data, tell them to use the HRMS portal.
- Use ONLY facts present in the profile data JSON. If a field is missing or null, say it is not available in their HRMS record.
- Do not guess PAN, Aadhaar, bank account numbers, or any other value.
- Do not repeat huge tables unless asked; prefer a direct answer, then offer to share more.
- Never paste raw JSON in the reply; write natural language.
- Never mention APIs, endpoints, tools, or "HRMS response".
- Treat nested `details` as the main personal/job record when present (e.g. panNumber, aadhaarId, department, reportingManagerID).
"""


class ProfileAgent(BaseAgent):
    def __init__(self):
        super().__init__("profile_agent", PROFILE_AGENT_PROMPT)

    async def process(self, state: OrchestratorState) -> OrchestratorState:
        try:
            profile_result = await get_my_employee_profile(state.jwt_token)
            if profile_result.get("status") != "success":
                state.response_message = profile_result.get(
                    "message",
                    "I was not able to load your profile right now. Please try again in a moment.",
                )
                state.routing_agent = "profile_agent"
                return state

            client = get_llm_client()
            model = get_model_name()
            context_prompt = self._build_context_prompt(state)
            profile_snapshot = self._build_profile_snapshot(profile_result.get("data"))
            logger.info(
                "Profile agent started for employee %s, session %s",
                state.employee_id,
                state.session_id,
            )

            response = await client.chat.completions.create(
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
        Keep a compact profile context to avoid oversized prompts.
        """
        if not isinstance(profile_data, dict):
            return {"profile": profile_data}

        details = profile_data.get("details") or {}
        snapshot: dict[str, Any] = {
            "empId": profile_data.get("empId"),
            "details": {
                "fullName": details.get("fullName"),
                "firstname": details.get("firstname"),
                "lsastname": details.get("lsastname"),
                "email": details.get("email"),
                "phone": details.get("phone"),
                "department": details.get("department"),
                "designationID": details.get("designationID"),
                "pay_scale": details.get("pay_scale"),
                "aadhaarId": details.get("aadhaarId"),
                "panNumber": details.get("panNumber"),
                "reportingManagerID": details.get("reportingManagerID"),
                "birthdate": details.get("birthdate"),
                "employmentType": details.get("employmentType"),
                "category": details.get("category"),
            },
            "addresses": (profile_data.get("addresses") or [])[:3],
            "banks": (profile_data.get("banks") or [])[:2],
            "education": (profile_data.get("education") or [])[:3],
            "emergency_contacts": (profile_data.get("emergency_contacts") or [])[:3],
            "offices": (profile_data.get("offices") or [])[:2],
        }
        st = profile_data.get("status")
        if isinstance(st, str):
            snapshot["employment_status"] = st
        return snapshot
