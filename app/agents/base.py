"""
Base Agent Class - Template for specialist agents
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.orchestrator.state import OrchestratorState
from app.models.message import Message
import logging

logger = logging.getLogger(__name__)

COMMON_RESPONSE_GUARDRAILS = """FINAL RESPONSE RULES:
- Return user-facing text only.
- Keep response concise, clear, and professional.
- Never expose backend/system/debug/API details.
- Do not mention internal components: agent, tool, API, endpoint, upload script, database, schema, logs.
- Do not add facts, numbers, or caveats not supported by available data.
- If the user message is ONLY a short greeting (hi/hello/namaste/good morning etc.) with no other request,
  respond with EXACTLY: Hello. How can I assist you today?
- If data cannot be fetched due to technical failure, respond calmly:
  I am unable to fetch that right now. Please try again in a moment.
- If a field/value is not available in records, state that clearly (do not call it a system failure)."""

class BaseAgent(ABC):
    """Base class for all specialist agents"""
    
    def __init__(self, agent_name: str, system_prompt: str):
        self.agent_name = agent_name
        self.system_prompt = f"{system_prompt}\n\n{COMMON_RESPONSE_GUARDRAILS}"
        self.tools = []
    
    @abstractmethod
    async def process(self, state: OrchestratorState) -> OrchestratorState:
        """
        Process user request and generate response.
        
        Args:
            state: Current orchestrator state
        
        Returns:
            Updated state with response
        """
        pass
    
    def _format_conversation_history(self, messages: List[Message]) -> str:
        """Format conversation history for LLM context"""
        if not messages:
            return "No previous conversation history."
        
        formatted = "Recent conversation:\n"
        for msg in messages[-8:]:  # Last 8 turns
            formatted += f"{msg.role.value}: {msg.content}\n"
        
        return formatted
    
    def _build_context_prompt(self, state: OrchestratorState) -> str:
        """Build system prompt with context"""
        history = self._format_conversation_history(state.conversation_history)
        
        return f"""{self.system_prompt}

EMPLOYEE CONTEXT:
- Employee ID: {state.employee_id}
- Role: {state.employee_role}
- Language: {state.language}

{history}

Current user message: {state.user_message}"""
    
    async def call_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        jwt_token: str
    ) -> Dict[str, Any]:
        """
        Call a tool and return result.
        Must be implemented by specific agents.
        """
        logger.error(f"Tool {tool_name} not implemented in {self.agent_name}")
        return {"error": "tool_not_found"}
