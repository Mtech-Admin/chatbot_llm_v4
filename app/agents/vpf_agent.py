"""
VPF agent — read-only: Voluntary Provident Fund requests (list, details, counts).
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
    parse_month_filter_from_message,
    parse_workflow_status_codes_for_count_breakdown,
)
from app.tools.vpf_status import VPF_STATUS_LABELS
from app.tools.vpf_tools import (
    VPF_TOOLS,
    count_vpf_requests_for_employee,
    get_vpf_request_details,
    list_my_vpf_requests,
    message_asks_for_vpf_count,
    vpf_tool_json_for_llm,
)

logger = logging.getLogger(__name__)

_STATUS_LEGEND = "\n".join(f"- {k}: {v}" for k, v in sorted(VPF_STATUS_LABELS.items()))

VPF_AGENT_PROMPT = f"""You are the VPF (Voluntary Provident Fund) assistant for DMRC HRMS.

You help employees VIEW their own VPF requests (amount, deduction month/year, reference number, approver, status).

READ-ONLY: You only retrieve information. Never claim you submitted, approved, or changed a VPF request.

Status codes in HRMS are often single letters. Tool results expand `Status` and `RequestStatus` to full labels.
Always describe status using the full label, not the letter.

Letter → label reference (for your understanding only):
{_STATUS_LEGEND}

Never paste raw JSON; summarize (reference number, amount, dates, approver, status).

Never infer totals from row previews — use a `total` or count summary from the tool when present.

Never mention APIs, endpoints, or internal field names unless the user asks how the system works.
"""


class VpfAgent(BaseAgent):
    def __init__(self):
        super().__init__("vpf_agent", VPF_AGENT_PROMPT)
        self.tools = VPF_TOOLS

    async def process(self, state: OrchestratorState) -> OrchestratorState:
        try:
            msg = (state.user_message or "").strip()
            if message_asks_for_vpf_count(msg):
                state.skip_response_review = True
                month_filter = parse_month_filter_from_message(msg)
                start_d = end_d = None
                period_phrase = ""
                if month_filter:
                    start_d, end_d, period_phrase = month_filter
                count_payload = await count_vpf_requests_for_employee(
                    state.jwt_token,
                    start_date=start_d,
                    end_date=end_d,
                    period_label=period_phrase if month_filter else None,
                )
                if count_payload.get("status") != "success":
                    state.response_message = count_payload.get(
                        "message",
                        "I could not retrieve that count right now. Please try again in a moment.",
                    )
                    state.routing_agent = "vpf_agent"
                    return state
                total = int(count_payload["total"])
                period = count_payload.get("period_label") or period_phrase
                scope = f" in {period}" if period else ""
                parts = [
                    f"You have {total} VPF request(s) on record{scope}."
                    if total != 0
                    else f"You have no VPF requests on record{scope}."
                ]
                if start_d and end_d and total:
                    for wf_code in parse_workflow_status_codes_for_count_breakdown(msg):
                        sub = await count_vpf_requests_for_employee(
                            state.jwt_token,
                            start_date=start_d,
                            end_date=end_d,
                            period_label=period_phrase if month_filter else None,
                            request_status=wf_code,
                        )
                        label_wf = NOC_STATUS_LABELS.get(wf_code, wf_code)
                        if sub.get("status") == "success":
                            parts.append(
                                f"Of those, {int(sub['total'])} have workflow status {label_wf}."
                            )
                state.response_message = " ".join(parts)
                state.routing_agent = "vpf_agent"
                return state

            client = get_llm_client()
            model = get_model_name()
            context_prompt = self._build_context_prompt(state)
            logger.info(
                "VPF agent started for employee %s, session %s",
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
            state.routing_agent = "vpf_agent"
            return state
        except Exception as e:
            logger.error(
                "Error in vpf_agent for employee %s: %s",
                state.employee_id,
                str(e),
                exc_info=True,
            )
            state.response_message = (
                "I was not able to load your VPF information right now. Please try again in a moment."
            )
            state.routing_agent = "vpf_agent"
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
            logger.info("VPF tool '%s' for employee %s args=%s", name, state.employee_id, args)
            if name == "list_my_vpf_requests":
                result = await list_my_vpf_requests(
                    state.jwt_token,
                    args.get("page", 1),
                    args.get("limit", 20),
                    args.get("query"),
                    start_date=(args.get("start_date") or args.get("startDate") or None),
                    end_date=(args.get("end_date") or args.get("endDate") or None),
                    status=args.get("status"),
                    request_status=args.get("request_status") or args.get("requestStatus"),
                )
            elif name == "get_vpf_request_details":
                result = await get_vpf_request_details(
                    state.jwt_token, str(args.get("request_id", ""))
                )
            else:
                result = {"status": "error", "message": f"Unknown tool: {name}"}
            tool_results.append(
                {"tool_call_id": tool_call.id, "tool": name, "result": result}
            )

        if not tool_results:
            if not state.response_message:
                state.response_message = (
                    "Ask me about your VPF requests (for example: list my VPF, status, or details for a request id)."
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
                    "content": vpf_tool_json_for_llm(tr["result"]),
                }
            )
        final_response = await client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=messages,
        )
        state.response_message = final_response.choices[0].message.content or state.response_message
        logger.info("VPF agent completed for employee %s", state.employee_id)
        return state
