"""
Router - Routes requests to appropriate specialist agents
"""

import logging
from app.orchestrator.state import OrchestratorState
from app.agents.attendance_agent import AttendanceAgent
from app.agents.policy_agent import PolicyAgent
from app.agents.profile_agent import ProfileAgent
from app.agents.noc_agent import NocAgent
from app.orchestrator.intent import validate_read_only_constraint, get_redirect_message

logger = logging.getLogger(__name__)

# Initialize agents
attendance_agent = AttendanceAgent()
policy_agent = PolicyAgent()
profile_agent = ProfileAgent()
noc_agent = NocAgent()

async def route_request(state: OrchestratorState) -> OrchestratorState:
    """
    Route request to appropriate agent based on intent
    """
    
    logger.info(
        "Routing decision start: employee=%s intent=%s session=%s",
        state.employee_id,
        state.intent,
        state.session_id,
    )

    # Step 1: Check read-only constraint
    is_allowed, redirect_code = validate_read_only_constraint(state.intent, state.user_message)
    
    if not is_allowed:
        state.response_message = get_redirect_message(state.user_message)
        state.requires_action = True
        logger.info(f"Redirecting user {state.employee_id} to portal")
        return state
    
    # Step 2: Route to specialist agent based on intent
    if state.intent == "attendance_inquiry":
        logger.info(f"Routing {state.employee_id} to attendance_agent")
        state = await attendance_agent.process(state)

    elif state.intent == "profile_inquiry":
        logger.info("Routing %s to profile_agent", state.employee_id)
        state = await profile_agent.process(state)

    elif state.intent == "noc_inquiry":
        logger.info("Routing %s to noc_agent", state.employee_id)
        state = await noc_agent.process(state)

    elif state.intent == "policy_inquiry":
        logger.info(f"Routing {state.employee_id} to policy_agent")
        state = await policy_agent.process(state)
    
    elif state.intent == "holiday_inquiry":
        # TODO: Implement policy agent
        logger.info("Holiday inquiry routed to placeholder response for employee %s", state.employee_id)
        state.response_message = "Holiday and leave policy features coming soon. Please check the HRMS portal for current policies."
    
    elif state.intent == "unknown":
        logger.info("Unknown intent fallback triggered for employee %s", state.employee_id)
        state.response_message = (
            "I'm not sure what you're looking for. I can help you with:\n"
            "- Check your attendance records\n"
            "- View your daily attendance\n"
            "- See team attendance (if you're a manager)\n"
            "- Look up your employee profile details (for example PAN or department)\n"
            "- Check your NOC requests (outside job, ex-India, visa/passport, etc.)\n\n"
            "What would you like to know?"
        )
    
    else:
        logger.warning("Unhandled intent '%s' for employee %s", state.intent, state.employee_id)
        state.response_message = "I didn't understand that request. Could you rephrase it?"
    
    return state
