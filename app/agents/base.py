"""
Base Agent Class - Template for specialist agents
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.orchestrator.state import OrchestratorState
from app.models.message import Message
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all specialist agents"""
    
    def __init__(self, agent_name: str, system_prompt: str):
        self.agent_name = agent_name
        self.system_prompt = system_prompt
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
