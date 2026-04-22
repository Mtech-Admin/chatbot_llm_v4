"""
Attendance Agent - Specialist agent for viewing attendance data
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, Any
from app.config import get_llm_client, get_model_name
from app.agents.base import BaseAgent
from app.orchestrator.state import OrchestratorState
from app.llm_tool_payload_compact import serialize_tool_result_for_llm
from app.tools.attendance_tools import (
    ATTENDANCE_TOOLS,
    get_my_attendance,
    get_my_daily_attendance,
    get_team_attendance
)

logger = logging.getLogger(__name__)

ATTENDANCE_AGENT_PROMPT = """You are the Attendance & Presence Agent for DMRC HRMS.

Your purpose: Help employees view and understand their attendance records.

CAPABILITIES:
- View personal attendance records for any month/year
- Check daily attendance for a specific date
- For managers: View team's attendance records
- Answer questions about attendance patterns

CONSTRAINTS:
- READ-ONLY: You can ONLY view/retrieve data. You CANNOT check in, check out, or modify records.
- If user asks to check in/out, respond: "I can help you view your attendance records, but I cannot perform check-in or check-out. Please use the HRMS mobile app or portal to do this."
- Authorization: The HRMS API enforces what data you can see. If you get access_denied, tell user they don't have access.
- Accuracy: Always cite dates and numbers accurately from the API response.

COMMUNICATION:
- Be concise and professional
- Use employee's preferred language (en/hi)
- Provide clear, actionable information
- If data is unclear, ask for clarification

RESPONSE FORMAT:
- Start with a direct answer to their question
- Include relevant data (dates, status, counts)
- If there are multiple records, organize by date
- Always end with: "Would you like to see anything else about your attendance?"
"""

class AttendanceAgent(BaseAgent):
    """Specialist agent for attendance queries"""
    
    def __init__(self):
        super().__init__("attendance_agent", ATTENDANCE_AGENT_PROMPT)
        self.tools = ATTENDANCE_TOOLS
    
    async def process(self, state: OrchestratorState) -> OrchestratorState:
        """
        Process attendance query using LLM with tool calling
        """
        try:
            client = get_llm_client()
            model = get_model_name()
            logger.info(
                "Attendance agent started for employee %s, session %s",
                state.employee_id,
                state.session_id,
            )
            
            # Build context with system prompt
            context_prompt = self._build_context_prompt(state)
            current_date = datetime.utcnow().strftime("%Y-%m-%d")
            context_prompt = (
                f"{context_prompt}\n\n"
                f"DATE CONTEXT:\n- Today's date is {current_date} (UTC).\n"
                "- If user asks for a month without specifying year, use the current year."
            )
            
            # Call LLM with tools
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
            
            # Process response
            state = await self._process_response(response, state)
            
            return state
        
        except Exception as e:
            logger.error(
                "Error in attendance agent for employee %s: %s",
                state.employee_id,
                str(e),
                exc_info=True,
            )
            state.response_message = "I encountered an error while retrieving your attendance. Please try again."
            return state
    
    async def _process_response(self, response: Any, state: OrchestratorState) -> OrchestratorState:
        """
        Process LLM response, execute tools if needed, get final response
        """
        tool_results = []
        assistant_message = response.choices[0].message
        tool_calls = assistant_message.tool_calls or []

        if assistant_message.content:
            state.response_message = assistant_message.content

        logger.info(
            "Attendance agent model response received for employee %s, tool_calls=%s",
            state.employee_id,
            len(tool_calls),
        )

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments or "{}")
            if tool_name == "get_my_attendance":
                tool_args = self._normalize_attendance_args(tool_args, state.user_message)
            logger.info(
                "Executing attendance tool '%s' for employee %s with args=%s",
                tool_name,
                state.employee_id,
                tool_args,
            )
            tool_result = await self.call_tool(
                tool_name,
                tool_args,
                state.jwt_token,
                state.employee_id
            )
            tool_results.append({
                "tool_call_id": tool_call.id,
                "tool": tool_name,
                "result": tool_result
            })
        
        # If tools were called, make another LLM call with results
        if tool_results:
            logger.info(
                "Attendance agent completed %s tool call(s) for employee %s",
                len(tool_results),
                state.employee_id,
            )

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
            for tool_result in tool_results:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_result["tool_call_id"],
                        "content": serialize_tool_result_for_llm(tool_result["result"]),
                    }
                )

            final_response = await client.chat.completions.create(
                model=model,
                max_tokens=2048,
                messages=messages,
            )

            state.response_message = final_response.choices[0].message.content or state.response_message
            logger.info("Attendance agent produced final response for employee %s", state.employee_id)
        
        return state
    
    async def call_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        jwt_token: str,
        employee_id: str
    ) -> Dict[str, Any]:
        """Execute attendance tools"""
        
        try:
            if tool_name == "get_my_attendance":
                return await get_my_attendance(
                    jwt_token,
                    tool_args.get("month"),
                    tool_args.get("year"),
                    tool_args.get("page", 1),
                    tool_args.get("limit", 20)
                )
            
            elif tool_name == "get_my_daily_attendance":
                return await get_my_daily_attendance(
                    jwt_token,
                    tool_args.get("date")
                )
            
            elif tool_name == "get_team_attendance":
                return await get_team_attendance(
                    jwt_token,
                    employee_id,
                    tool_args.get("date"),
                    tool_args.get("from_date"),
                    tool_args.get("to_date")
                )
            
            else:
                logger.error(f"Unknown tool: {tool_name}")
                return {"error": "unknown_tool"}
        
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            return {"error": f"tool_error: {str(e)}"}

    def _normalize_attendance_args(self, tool_args: Dict[str, Any], user_message: str) -> Dict[str, Any]:
        """
        Ensure month-only requests default to current year.
        """
        normalized = dict(tool_args)
        explicit_year_in_query = re.search(r"\b(19|20)\d{2}\b", user_message) is not None
        if not explicit_year_in_query:
            normalized["year"] = str(datetime.utcnow().year)
        return normalized
