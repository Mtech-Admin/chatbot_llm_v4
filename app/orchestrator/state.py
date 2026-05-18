"""
Orchestrator State Schema - shared state across LangGraph nodes
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from app.models.message import Message


def orch_get(state: Any, key: str, default: Any = None) -> Any:
    """Read field from LangGraph state (dict-like or dataclass-like)."""
    if state is None:
        return default
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


@dataclass
class OrchestratorState:
    """State passed through LangGraph nodes"""
    
    # Input
    user_message: str
    employee_id: str
    employee_role: str
    jwt_token: str
    session_id: str
    language: str = "en"
    
    # Context
    employee_profile: Optional[Dict[str, Any]] = None
    conversation_history: List[Message] = field(default_factory=list)

    # Sanitized full-details blob from Redis cache (filled in gateway from session.context).
    cached_profile_snapshot: Optional[Dict[str, Any]] = None

    # Last routed specialist intent for this Redis session (continuity across turns).
    last_intent: Optional[str] = None

    # Processing
    intent: Optional[str] = None  # e.g., "attendance_inquiry", "redirect_to_portal"
    routing_agent: Optional[str] = None  # e.g., "attendance_agent"
    requires_tools: bool = False
    
    # Output
    response_message: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    is_read_only: bool = True
    requires_action: bool = False
    action_url: Optional[str] = None
    # When True, gateway skips LLM response review (deterministic agent output must not be altered).
    skip_response_review: bool = False
