"""
Leave & public holiday agent — read-only: types, balances, requests, calendar, holidays.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any, Dict

from app.agents.base import BaseAgent
from app.config import get_llm_client, get_model_name
from app.orchestrator.state import OrchestratorState
from app.tools.leave_field_mapping import CUSTOMER_FIELD_LABELS, phrase_to_customer_keys
from app.llm_tool_payload_compact import serialize_tool_result_for_llm
from app.tools.leave_tools import (
    LEAVE_TOOLS,
    get_leave_request_by_id,
    get_leave_types,
    get_my_leave_absence_types,
    get_my_leave_calendar,
    get_my_leave_requests,
    get_my_leave_time_accounts,
    get_my_saved_leave_requests,
    get_public_holiday_calendar,
    upcoming_holidays_from_payload,
)

logger = logging.getLogger(__name__)

_LABEL_REF = "\n".join(
    f"- {k}: {v}" for k, v in sorted(CUSTOMER_FIELD_LABELS.items())
)

LEAVE_AGENT_PROMPT = f"""You are the Leave & Holiday assistant for DMRC HRMS.

READ-ONLY: You only retrieve information. Never claim you submitted, approved, or changed leave.

Capabilities:
- Explain leave types / absence types available to the employee
- Leave balances and time accounts (quotas)
- Leave requests (status, dates, types) and leave calendar
- Public / official holiday calendar (including upcoming holidays)

CUSTOMER fields (SAP custom fields on leave rows):
APIs may return keys CUSTOMER01–CUSTOMER10. Tool results include `named_customer_fields` with human-readable labels.
When answering, always use the LABEL (e.g. "Reason for Leave"), not the raw key, unless the user asks for technical field names.

Label reference:
{_LABEL_REF}

If the user asks about a specific concept (e.g. address during leave, hospitalization), match it to the label above and quote the value from `named_customer_fields` or the corresponding CUSTOMERxx value.

Never paste huge raw JSON; summarize clearly with dates, leave type names, and status.

Authorization: Only the logged-in employee's data; tools default to their employee id.

For "upcoming holidays", prefer filtering mentally to future dates when the tool returns a full list, or describe the next several entries.

If a required tool argument is missing (e.g. date range for calendar), choose a reasonable default (current calendar year or next 12 months) and state what you used.

If any tool returns status "error" (including HRMS failure), do NOT invent a second call, fake function syntax, or new parameter names. Give a short, helpful message: the holiday list could not be loaded; suggest trying again or checking the HRMS portal. Never output strings like `!function_call:` or JSON tool calls in plain text.
"""


class LeaveAgent(BaseAgent):
    def __init__(self):
        super().__init__("leave_agent", LEAVE_AGENT_PROMPT)
        self.tools = LEAVE_TOOLS

    async def process(self, state: OrchestratorState) -> OrchestratorState:
        try:
            client = get_llm_client()
            model = get_model_name()
            current_date = datetime.utcnow().strftime("%Y-%m-%d")
            extra = ""
            keys_hint = phrase_to_customer_keys(state.user_message or "")
            if keys_hint:
                extra = f"\nUser may be asking about these custom fields: {', '.join(keys_hint)}.\n"

            context_prompt = (
                f"{self._build_context_prompt(state)}{extra}\n"
                f"DATE CONTEXT: Today is {current_date} (UTC). "
                f"Default calendar year for holidays: {date.today().year}.\n"
            )

            response = await client.chat.completions.create(
                model=model,
                max_tokens=2048,
                tools=self.tools,
                tool_choice="auto",
                messages=[
                    {"role": "system", "content": context_prompt},
                    {"role": "user", "content": state.user_message},
                ],
            )

            state = await self._process_response(response, state)
            state.routing_agent = "leave_agent"
            return state

        except Exception as e:
            logger.error(
                "Error in leave_agent for employee %s: %s",
                state.employee_id,
                str(e),
                exc_info=True,
            )
            state.response_message = (
                "I could not retrieve leave or holiday information right now. Please try again shortly."
            )
            state.routing_agent = "leave_agent"
            return state

    async def _process_response(self, response: Any, state: OrchestratorState) -> OrchestratorState:
        tool_results = []
        assistant_message = response.choices[0].message
        tool_calls = assistant_message.tool_calls or []

        if assistant_message.content:
            state.response_message = assistant_message.content

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments or "{}")
            logger.info(
                "leave_agent tool %s for employee %s args=%s",
                tool_name,
                state.employee_id,
                tool_args,
            )
            tool_result = await self.call_tool(tool_name, tool_args, state.jwt_token, state.employee_id)
            # Help model highlight upcoming holidays in one pass
            if tool_name == "get_public_holiday_calendar" and tool_result.get("status") == "success":
                raw = tool_result.get("data")
                if isinstance(raw, list):
                    tool_result["upcoming_holidays_preview"] = upcoming_holidays_from_payload(
                        raw, limit=15
                    )
            tool_results.append(
                {"tool_call_id": tool_call.id, "tool": tool_name, "result": tool_result}
            )

        if tool_results:
            client = get_llm_client()
            model = get_model_name()
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": state.user_message},
                {
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        tc.model_dump() if hasattr(tc, "model_dump") else tc for tc in tool_calls
                    ],
                },
            ]
            for tr in tool_results:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tr["tool_call_id"],
                        "content": serialize_tool_result_for_llm(tr["result"]),
                    }
                )
            final_response = await client.chat.completions.create(
                model=model,
                max_tokens=2048,
                messages=messages,
            )
            state.response_message = final_response.choices[0].message.content or state.response_message

        return state

    async def call_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        jwt_token: str,
        employee_id: str,
    ) -> Dict[str, Any]:
        eid = (tool_args.get("emp_id") or tool_args.get("employee_id") or employee_id) or ""
        eid = str(eid).strip()

        try:
            if tool_name == "get_leave_types":
                return await get_leave_types(jwt_token)

            if tool_name == "get_my_leave_absence_types":
                return await get_my_leave_absence_types(jwt_token, eid)

            if tool_name == "get_my_leave_time_accounts":
                return await get_my_leave_time_accounts(
                    jwt_token,
                    eid,
                    tool_args.get("leave_type"),
                    tool_args.get("from_date"),
                    tool_args.get("to_date"),
                )

            if tool_name == "get_my_leave_requests":
                fb = tool_args.get("filter_by") or "date"
                return await get_my_leave_requests(
                    jwt_token,
                    eid,
                    fb,
                    tool_args.get("date_from"),
                    tool_args.get("date_to"),
                )

            if tool_name == "get_my_leave_calendar":
                fd = tool_args.get("from_date")
                td = tool_args.get("to_date")
                if not fd or not td:
                    y = date.today().year
                    fd = fd or f"{y}-01-01"
                    td = td or f"{y}-12-31"
                return await get_my_leave_calendar(jwt_token, eid, fd, td)

            if tool_name == "get_my_saved_leave_requests":
                return await get_my_saved_leave_requests(
                    jwt_token,
                    eid or employee_id,
                    tool_args.get("page", 1),
                    tool_args.get("limit", 20),
                )

            if tool_name == "get_leave_request_by_id":
                rid = tool_args.get("request_id")
                if not rid:
                    return {"status": "error", "message": "request_id is required"}
                return await get_leave_request_by_id(jwt_token, str(rid))

            if tool_name == "get_public_holiday_calendar":
                y = tool_args.get("year")
                yi: int | None = None
                if y is not None and str(y).strip().isdigit():
                    yi = int(str(y).strip())
                return await get_public_holiday_calendar(jwt_token, yi)

            return {"error": "unknown_tool", "tool": tool_name}

        except Exception as e:
            logger.error("leave_agent tool error %s: %s", tool_name, e, exc_info=True)
            return {"status": "error", "message": str(e)}
