"""
Router - Routes requests to appropriate specialist agents
"""

import logging
import re
from typing import Optional

from app.orchestrator.state import OrchestratorState
from app.agents.attendance_agent import AttendanceAgent
from app.agents.policy_agent import PolicyAgent
from app.agents.profile_agent import ProfileAgent
from app.agents.noc_agent import NocAgent
from app.agents.leave_agent import LeaveAgent
from app.agents.vpf_agent import VpfAgent
from app.orchestrator.intent import validate_read_only_constraint, get_redirect_message

logger = logging.getLogger(__name__)

_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def _prefer_hindi(language: Optional[str], user_message: str) -> bool:
    """True when replies should follow Hindi — explicit preference or Hindi script in message."""
    code = (language or "en").strip().lower().split("-", maxsplit=1)[0]
    if code in ("hi", "hin", "hindi"):
        return True
    return bool(_DEVANAGARI_RE.search(user_message or ""))


def _unknown_intent_guide_text(hindi: bool) -> str:
    if hindi:
        return (
            "मुझे पूर्ण रूप से समझ नहीं आया कि आप क्या जानना चाहते हैं। मैं इन विषयों पर मदद कर सकता हूँ:\n"
            "- अपनी उपस्थिति (attendance) के रिकॉर्ड देखना\n"
            "- दैनिक उपस्थिति देखना\n"
            "- टीम की उपस्थिति (यदि आप प्रबंधक हैं)\n"
            "- कर्मचारी प्रोफ़ाइल विवरण देखना (जैसे PAN या विभाग)\n"
            "- NOC आवेदनों की जानकारी (outside job, ex-India, visa/passport आदि)\n"
            "- VPF (Voluntary Provident Fund) आवेदन और उनकी स्थिति\n"
            "- अवकाश शेष, अवकाश आवेदन और सार्वजनिक अवकाश कैलेंडर\n\n"
            "आप क्या जानना चाहेंगे?"
        )
    return (
        "I'm not sure what you're looking for. I can help you with:\n"
        "- Check your attendance records\n"
        "- View your daily attendance\n"
        "- See team attendance (if you're a manager)\n"
        "- Look up your employee profile details (for example PAN or department)\n"
        "- Check your NOC requests (outside job, ex-India, visa/passport, etc.)\n"
        "- View VPF (Voluntary Provident Fund) requests and status\n"
        "- View leave balances, leave requests, and the public holiday calendar\n\n"
        "What would you like to know?"
    )


def _is_pure_greeting(message: str) -> bool:
    raw = (message or "").strip()
    if not raw or len(raw) > 48:
        return False
    if any(ch in raw for ch in ("?", "!", ":")):
        return False
    raw_lower = raw.lower()
    if re.search(r"\b(hi|hello|hey|namaste|good morning|good afternoon|good evening)\b", raw_lower):
        tokens = re.findall(r"[a-zA-Z]+", raw_lower)
        return len(tokens) <= 4
    if _DEVANAGARI_RE.search(raw):
        hi_markers = ("नमस्ते", "नमस्कार", "प्रणाम", "सुप्रभात", "शुभ प्रभात", "हैलो", "हेलो")
        if len(raw) > 48 or not any(m in raw for m in hi_markers):
            return False
        words = re.findall(r"\S+", raw)
        return len(words) <= 6
    return False

# Initialize agents
attendance_agent = AttendanceAgent()
policy_agent = PolicyAgent()
profile_agent = ProfileAgent()
noc_agent = NocAgent()
leave_agent = LeaveAgent()
vpf_agent = VpfAgent()

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

    elif state.intent == "vpf_inquiry":
        logger.info("Routing %s to vpf_agent", state.employee_id)
        state = await vpf_agent.process(state)

    elif state.intent == "policy_inquiry":
        logger.info(f"Routing {state.employee_id} to policy_agent")
        state = await policy_agent.process(state)
    
    elif state.intent in ("leave_inquiry", "holiday_inquiry"):
        logger.info("Routing %s to leave_agent (intent=%s)", state.employee_id, state.intent)
        state = await leave_agent.process(state)
    
    elif state.intent == "unknown":
        logger.info("Unknown intent fallback triggered for employee %s", state.employee_id)
        use_hi = _prefer_hindi(state.language, state.user_message or "")
        if _is_pure_greeting(state.user_message):
            state.response_message = (
                "नमस्ते। आज मैं आपकी कैसे सहायता कर सकता हूँ?"
                if use_hi
                else "Hello. How can I assist you today?"
            )
        else:
            state.response_message = _unknown_intent_guide_text(use_hi)
    
    else:
        logger.warning("Unhandled intent '%s' for employee %s", state.intent, state.employee_id)
        use_hi = _prefer_hindi(state.language, state.user_message or "")
        state.response_message = (
            "मैं आपके अनुरोध को समझ नहीं पाया। कृपया दोबारा लिखें।"
            if use_hi
            else "I didn't understand that request. Could you rephrase it?"
        )
    
    return state
