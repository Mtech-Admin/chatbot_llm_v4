"""
LangGraph Orchestrator - Coordinates conversation flow using state graph
"""

import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from app.orchestrator.state import OrchestratorState
from app.orchestrator.intent import classify_intent
from app.orchestrator.router import route_request
from app.gateway.session import session_manager
from app.models.message import Message, MessageRole

logger = logging.getLogger(__name__)

def build_orchestrator_graph() -> StateGraph:
    """Build LangGraph state machine for orchestration"""
    
    workflow = StateGraph(OrchestratorState)
    
    # Node 1: Classify Intent
    async def classify_intent_node(state: OrchestratorState) -> Dict[str, Any]:
        """Classify user intent"""
        logger.info(f"Classifying intent for user {state.employee_id}")
        intent = await classify_intent(state)
        state.intent = intent
        logger.info(f"Intent classified as: {intent}")
        return {"intent": intent}
    
    # Node 2: Route to agent
    async def route_node(state: OrchestratorState) -> Dict[str, Any]:
        """Route to appropriate agent"""
        logger.info(f"Routing user {state.employee_id} with intent {state.intent}")
        state = await route_request(state)
        return {
            "response_message": state.response_message,
            "routing_agent": state.routing_agent,
            "requires_action": state.requires_action,
            "sources": state.sources,
            "skip_response_review": state.skip_response_review,
        }
    
    # Node 3: Save to memory
    async def save_memory_node(state: OrchestratorState) -> Dict[str, Any]:
        """Save conversation to session memory"""
        # Save user message
        user_msg = Message(
            role=MessageRole.USER,
            content=state.user_message
        )
        await session_manager.add_message(state.session_id, user_msg)
        
        # Save assistant response
        assistant_msg = Message(
            role=MessageRole.ASSISTANT,
            content=state.response_message
        )
        await session_manager.add_message(state.session_id, assistant_msg)
        
        logger.info(f"Saved conversation to memory for session {state.session_id}")
        return {}
    
    # Add nodes
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("route", route_node)
    workflow.add_node("save_memory", save_memory_node)
    
    # Add edges
    workflow.set_entry_point("classify_intent")
    workflow.add_edge("classify_intent", "route")
    workflow.add_edge("route", "save_memory")
    workflow.add_edge("save_memory", END)
    
    return workflow.compile()

# Global orchestrator instance
orchestrator = None

def get_orchestrator():
    """Get or create global orchestrator"""
    global orchestrator
    if orchestrator is None:
        orchestrator = build_orchestrator_graph()
    return orchestrator

async def process_message(state: OrchestratorState) -> OrchestratorState:
    """
    Process user message through orchestration pipeline
    
    Args:
        state: Initial orchestrator state
    
    Returns:
        Final orchestrator state with response
    """
    orchestrator_graph = get_orchestrator()
    
    # Convert state to dict for graph execution
    state_dict = {
        "user_message": state.user_message,
        "employee_id": state.employee_id,
        "employee_role": state.employee_role,
        "jwt_token": state.jwt_token,
        "session_id": state.session_id,
        "language": state.language,
        "employee_profile": state.employee_profile,
        "conversation_history": state.conversation_history,
        "intent": state.intent,
        "routing_agent": state.routing_agent,
        "response_message": state.response_message,
        "sources": state.sources,
        "skip_response_review": getattr(state, "skip_response_review", False),
    }
    
    # Execute graph
    result = await orchestrator_graph.ainvoke(state_dict)
    
    # Update state with result
    state.intent = result.get("intent", state.intent)
    state.response_message = result.get("response_message", state.response_message)
    state.routing_agent = result.get("routing_agent", state.routing_agent)
    state.requires_action = result.get("requires_action", state.requires_action)
    state.sources = result.get("sources", state.sources)
    state.skip_response_review = bool(
        result.get("skip_response_review", state.skip_response_review)
    )

    return state
