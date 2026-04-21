"""
NOC agent — read-only: list and detail NOC requests across DMRC HRMS NOC modules.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from app.agents.base import BaseAgent
from app.config import get_llm_client, get_model_name
from app.orchestrator.state import OrchestratorState
from app.tools.noc_status import NOC_STATUS_LABELS
from app.tools.noc_tools import (
    NOC_TOOLS,
    NOC_TYPE_LABELS,
    count_noc_requests_for_employee,
    get_noc_request_details,
    infer_noc_type_from_message,
    list_my_noc_requests,
    message_asks_for_noc_count,
    noc_tool_json_for_llm,
    parse_workflow_status_codes_for_count_breakdown,
    parse_month_filter_from_message,
)

logger = logging.getLogger(__name__)

_STATUS_LEGEND = "\n".join(f"- {k}: {v}" for k, v in sorted(NOC_STATUS_LABELS.items()))

NOC_AGENT_PROMPT = f"""You are the NOC (No Objection Certificate) assistant for DMRC HRMS.

You help employees VIEW their own NOC requests across these modules (internal type keys):
- noc_exindia_requests — foreign / ex-India travel NOC
- noc_visa_passport — visa / passport NOC
- noc_reimbursement — reimbursement-related NOC
- noc_outsidejobs — outside employment / job NOC
- noc_onlinecourses — online courses NOC
- noc_higherstudies — higher studies NOC

READ-ONLY: You only retrieve information. Never claim you submitted, approved, or changed a request.

Status codes in HRMS are sometimes single letters. When you describe status to the user, always use the FULL label.
Tool results already expand `status` and `requestStatus` fields to full labels. Do not show single-letter codes in your answer.

Letter → label reference (for your understanding only; prefer wording from tool JSON):
{_STATUS_LEGEND}

If the user does not name a module, ask which NOC type they mean, or list recent items from the most likely module if they gave enough context.

Never paste raw JSON blobs; summarize clearly (reference number, dates, status, key fields).

Never infer counts, totals, or averages by reading preview rows. If you need how many requests exist,
the user should ask in plain language and the system will compute totals separately — only use a `total`
field when the tool summary explicitly includes it.

Never mention APIs, endpoints, tools, or internal keys unless the user explicitly asks how the system classifies modules.
"""


class NocAgent(BaseAgent):
    def __init__(self):
        super().__init__("noc_agent", NOC_AGENT_PROMPT)
        self.tools = NOC_TOOLS

    async def process(self, state: OrchestratorState) -> OrchestratorState:
        try:
            msg = (state.user_message or "").strip()
            if message_asks_for_noc_count(msg):
                state.skip_response_review = True
                noc_type = infer_noc_type_from_message(msg)
                if not noc_type:
                    state.response_message = (
                        "To give an exact total, which NOC type do you mean — outside job, ex-India travel, "
                        "visa/passport, reimbursement, online courses, or higher studies?"
                    )
                    state.routing_agent = "noc_agent"
                    return state
                month_filter = parse_month_filter_from_message(msg)
                start_d = end_d = None
                period_phrase = ""
                if month_filter:
                    start_d, end_d, period_phrase = month_filter
                count_payload = await count_noc_requests_for_employee(
                    state.jwt_token,
                    noc_type,
                    start_date=start_d,
                    end_date=end_d,
                    period_label=period_phrase if month_filter else None,
                )
                if count_payload.get("status") != "success":
                    state.response_message = count_payload.get(
                        "message",
                        "I could not retrieve that count right now. Please try again in a moment.",
                    )
                    state.routing_agent = "noc_agent"
                    return state
                total = int(count_payload["total"])
                label = count_payload.get("noc_type_label") or NOC_TYPE_LABELS.get(
                    noc_type, noc_type
                )
                period = count_payload.get("period_label") or period_phrase
                scope = f" in {period}" if period else ""
                if total == 0:
                    parts = [f"You have no {label} NOC requests{scope} on record."]
                else:
                    parts = [f"You have {total} {label} NOC request(s){scope} on record."]

                if start_d and end_d:
                    for wf_code in parse_workflow_status_codes_for_count_breakdown(msg):
                        sub = await count_noc_requests_for_employee(
                            state.jwt_token,
                            noc_type,
                            start_date=start_d,
                            end_date=end_d,
                            period_label=period_phrase if month_filter else None,
                            request_status=wf_code,
                        )
                        label_wf = NOC_STATUS_LABELS.get(
                            wf_code, wf_code
                        )
                        if sub.get("status") == "success":
                            n_sub = int(sub["total"])
                            parts.append(
                                f"Of those, {n_sub} have workflow status {label_wf}."
                            )
                        else:
                            parts.append(
                                f"I could not retrieve the count for workflow status {label_wf} in that same period from HRMS."
                            )

                state.response_message = " ".join(parts)
                state.routing_agent = "noc_agent"
                return state

            client = get_llm_client()
            model = get_model_name()
            context_prompt = self._build_context_prompt(state)
            logger.info(
                "NOC agent started for employee %s, session %s",
                state.employee_id,
                state.session_id,
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
            state.routing_agent = "noc_agent"
            return state
        except Exception as e:
            logger.error(
                "Error in NOC agent for employee %s: %s",
                state.employee_id,
                str(e),
                exc_info=True,
            )
            state.response_message = (
                "I was not able to load your NOC information right now. Please try again in a moment."
            )
            return state

    async def _process_response(self, response: Any, state: OrchestratorState) -> OrchestratorState:
        assistant_message = response.choices[0].message
        tool_calls = assistant_message.tool_calls or []

        if assistant_message.content:
            state.response_message = assistant_message.content

        tool_results: list[dict[str, Any]] = []
        for tool_call in tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
            logger.info(
                "NOC tool '%s' for employee %s args=%s",
                name,
                state.employee_id,
                args,
            )
            if name == "list_my_noc_requests":
                sd = args.get("start_date") or args.get("startDate")
                ed = args.get("end_date") or args.get("endDate")
                st = args.get("status")
                rs = args.get("request_status") or args.get("requestStatus")
                result = await list_my_noc_requests(
                    state.jwt_token,
                    args.get("noc_type", ""),
                    args.get("page", 1),
                    args.get("limit", 20),
                    args.get("query"),
                    start_date=str(sd).strip() if sd else None,
                    end_date=str(ed).strip() if ed else None,
                    status=str(st).strip() if st else None,
                    request_status=str(rs).strip() if rs else None,
                )
            elif name == "get_noc_request_details":
                result = await get_noc_request_details(
                    state.jwt_token,
                    args.get("noc_type", ""),
                    str(args.get("request_id", "")),
                )
            else:
                result = {"status": "error", "message": f"Unknown tool: {name}"}
            tool_results.append(
                {"tool_call_id": tool_call.id, "tool": name, "result": result}
            )

        if not tool_results:
            if not state.response_message:
                state.response_message = (
                    "Tell me which NOC you mean (for example outside job, ex-India travel, visa/passport, "
                    "reimbursement, online courses, or higher studies), and whether you want a list or a specific request id."
                )
            return state

        client = get_llm_client()
        model = get_model_name()
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": state.user_message},
            {
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    tc.model_dump() if hasattr(tc, "model_dump") else tc
                    for tc in tool_calls
                ],
            },
        ]
        for tr in tool_results:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tr["tool_call_id"],
                    "content": noc_tool_json_for_llm(tr["result"]),
                }
            )

        final_response = await client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=messages,
        )
        state.response_message = (
            final_response.choices[0].message.content or state.response_message
        )
        logger.info("NOC agent completed for employee %s", state.employee_id)
        return state
