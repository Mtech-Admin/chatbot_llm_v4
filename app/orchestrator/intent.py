"""
Intent Classification - Determines routing for user query
"""

import logging
import re
from typing import Literal
from app.config import get_llm_client, get_model_name
from app.orchestrator.state import OrchestratorState

logger = logging.getLogger(__name__)

INTENT_CLASSIFIER_PROMPT = """You are an expert intent classifier for an HR chatbot.

Analyze the user's message and classify it into ONE of these intents:

1. "attendance_inquiry" - User wants to check their attendance, daily records, status
   Examples: "Show my attendance", "What's my attendance for March?", "When did I check in today?"

2. "profile_inquiry" - User wants to VIEW their own employee / HR profile facts (read-only)
   Examples: "What is my PAN?", "My Aadhaar on record", "What is my employee ID?", "Who is my reporting manager?",
   "What department am I in?", "What is my designation?", "Show my profile", "What is my bank IFSC in HRMS?",
   "What is my office location?", "My date of joining"

3. "redirect_to_portal" - User is asking to PERFORM an action (not read-only)
   Examples: "Apply for leave", "Update my address", "Submit reimbursement", "Check in"
   → For ANY write/action request, use this intent

4. "policy_inquiry" - User asks policy/rules/eligibility/admissibility questions
   Examples: "What leaves are admissible on PRCE basis?", "What is leave policy?"

5. "leave_inquiry" - User wants to VIEW leave information (read-only): leave types, balances, leave status, leave count, my leave requests, leave calendar
   Examples: "What leave types do I have?", "What is my casual leave balance?", "Show my leave requests", "Leave status last month", "How many leaves left?"

6. "holiday_inquiry" - User wants public / official holidays (organizational calendar), not personal leave
   Examples: "What are the public holidays?", "Upcoming holidays in 2026", "Holiday list"

7. "noc_inquiry" - User wants to VIEW their own NOC (No Objection Certificate) requests / status / details (read-only)
   Examples: "What is the status of my NOC?", "Show my outside job NOC requests", "Ex-India NOC status",
   "Visa passport NOC", "My reimbursement NOC", "Online courses NOC list", "Higher studies NOC details"

8. "vpf_inquiry" - User wants to VIEW VPF (Voluntary Provident Fund) requests, status, balance of requests, or details (read-only)
   Examples: "Show my VPF requests", "VPF status", "What is the status of my voluntary provident fund request?",
   "How many VPF requests do I have?"

9. "unknown" - User's intent doesn't fit above categories
   Examples: "Hi", "How are you?", "Tell me about DMRC"

Rules:
- If user wants to DO something (apply, update, submit, check-in, approve) → "redirect_to_portal"
- If user wants to VIEW/CHECK something about their attendance → "attendance_inquiry"
- If user wants to VIEW their own profile / identity / job / contact data (not policy, not attendance) → "profile_inquiry"
- If user wants to VIEW NOC request status or details (any NOC module) → "noc_inquiry"
- If user wants to VIEW VPF / Voluntary Provident Fund requests or status (not applying or withdrawing) → "vpf_inquiry"
- If user wants to VIEW leave balances, leave types, their leave requests/status, or leave calendar (not applying) → "leave_inquiry"
- If user asks about public holidays / holiday list / upcoming holidays (organizational calendar) → "holiday_inquiry"
- If the question is about leave *policy* or *rules* (admissibility, eligibility), prefer "policy_inquiry" over "leave_inquiry"
- If there's ANY ambiguity about actions vs viewing, prefer "redirect_to_portal" to be safe
- Respond ONLY with the intent name, nothing else

User message: {user_message}

Intent:"""

async def classify_intent(
    state: OrchestratorState,
) -> Literal[
    "attendance_inquiry",
    "profile_inquiry",
    "noc_inquiry",
    "vpf_inquiry",
    "policy_inquiry",
    "redirect_to_portal",
    "holiday_inquiry",
    "leave_inquiry",
    "unknown",
]:
    """
    Classify user intent using LLM
    
    Args:
        state: Orchestrator state with user message
    
    Returns:
        Intent classification
    """
    try:
        client = get_llm_client()
        model = get_model_name()
        
        prompt = INTENT_CLASSIFIER_PROMPT.format(user_message=state.user_message)
        
        response = await client.chat.completions.create(
            model=model,
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3  # Low temperature for deterministic classification
        )
        intent_text = (response.choices[0].message.content or "").strip().lower()
        logger.info(
            "Intent classifier raw response for employee %s: %s",
            state.employee_id,
            intent_text,
        )
        
        normalized_intent = intent_text.replace("-", "_").replace(" ", "_")

        # Parse response with tolerant matching for minor format variations
        if "attendance_inquiry" in normalized_intent or "attendance" in normalized_intent:
            return "attendance_inquiry"
        elif "profile_inquiry" in normalized_intent or (
            "profile" in normalized_intent and "attendance" not in normalized_intent
        ):
            return "profile_inquiry"
        elif "noc_inquiry" in normalized_intent or re.match(
            r"^noc(_|$|inquiry|request)", normalized_intent
        ):
            return "noc_inquiry"
        elif "vpf_inquiry" in normalized_intent or re.search(r"\bvpf\b", normalized_intent):
            return "vpf_inquiry"
        elif "policy_inquiry" in normalized_intent or "policy" in normalized_intent or "admissible" in normalized_intent:
            return "policy_inquiry"
        elif "redirect_to_portal" in normalized_intent or "redirect" in normalized_intent:
            return "redirect_to_portal"
        elif "leave_inquiry" in normalized_intent or re.match(
            r"^leave(_|$|inquiry)", normalized_intent
        ):
            return "leave_inquiry"
        elif "holiday_inquiry" in normalized_intent or "holiday" in normalized_intent:
            return "holiday_inquiry"
        else:
            # Heuristic fallbacks when the LLM intent string is off.
            msg = (state.user_message or "").lower()
            action_markers = [
                "update",
                "change",
                "modify",
                "add",
                "delete",
                "remove",
                "upload",
                "submit",
                "apply",
                "register",
                "enroll",
            ]
            has_action = any(
                re.search(rf"\b{re.escape(a)}\b", msg) for a in action_markers
            )

            noc_hit = (
                re.search(r"\bnoc\b", msg)
                or re.search(r"no\s+objection", msg)
                or "outside job" in msg
                or re.search(r"ex\s*-?\s*india", msg)
                or ("visa" in msg and "passport" in msg)
                or "higher studies" in msg
                or "online course" in msg
                or "reimbursement noc" in msg
                or "noc reimbursement" in msg
            )
            if noc_hit and not has_action:
                return "noc_inquiry"

            vpf_hit = (
                re.search(r"\bvpf\b", msg)
                or re.search(r"voluntary\s*provident", msg)
                or (
                    re.search(r"provident\s*fund", msg)
                    and re.search(r"\bvoluntary\b", msg)
                )
            )
            if vpf_hit and not has_action:
                return "vpf_inquiry"

            profile_markers = [
                "address",
                "pan",
                "pan number",
                "aadhaar",
                "aadhar",
                "ifsc",
                "bank",
                "department",
                "designation",
                "reporting manager",
                "manager",
                "date of joining",
                "doj",
                "dob",
                "employee id",
                "empid",
                "my profile",
            ]
            if any(p in msg for p in profile_markers) and not has_action:
                return "profile_inquiry"

            leave_markers = [
                "leave balance",
                "leave type",
                "types of leave",
                "casual leave",
                "earned leave",
                "annual leave",
                "sick leave",
                "my leave",
                "leave request",
                "leave status",
                "leave calendar",
                "how many leave",
                "remaining leave",
                "leave quota",
                "time account",
                "absence type",
            ]
            public_holiday_markers = [
                "public holiday",
                "official holiday",
                "holiday calendar",
                "list of holidays",
                "upcoming holiday",
                "next holiday",
                "is it a holiday",
            ]
            if any(p in msg for p in public_holiday_markers) and not has_action:
                return "holiday_inquiry"
            if any(p in msg for p in leave_markers) and not has_action:
                return "leave_inquiry"
            if re.search(r"\bleave\b", msg) and not has_action and "policy" not in msg:
                return "leave_inquiry"
            logger.warning(
                "Intent classifier fallback to unknown for employee %s, raw='%s'",
                state.employee_id,
                intent_text,
            )
            return "unknown"
    
    except Exception as e:
        logger.error(
            "Error classifying intent for employee %s: %s",
            state.employee_id,
            str(e),
            exc_info=True,
        )
        return "unknown"

def validate_read_only_constraint(intent: str, user_message: str) -> tuple[bool, str]:
    """
    Validate if request violates read-only constraint.
    Returns (is_valid, redirect_message)
    """
    # NOTE: Use word-boundary matching for short verbs like "add"
    # to avoid false positives (e.g. "address" contains "add").
    redirect_keywords = [
        "apply",
        "applying",
        "apply for",
        "submit",
        "submitting",
        "update",
        "updating",
        "change",
        "create",
        "add",
        "upload",
        "approve",
        "reject",
        "cancel",
        "delete",
        "remove",
        "modify",
        "register",
        "enroll",
        "subscribe",
        "check in",
        "check out",
        "checkin",
        "checkout",
    ]

    message_lower = user_message.lower()

    for keyword in redirect_keywords:
        # Phrases: keep simple substring match
        if " " in keyword:
            if keyword in message_lower:
                return False, "redirect_needed"
            continue

        # Single words: require word boundary match
        if re.search(rf"\b{re.escape(keyword)}\b", message_lower):
            return False, "redirect_needed"
    
    return True, ""

def get_redirect_message(user_message: str, hrms_portal_url: str = "https://hrms.dmrc.internal") -> str:
    """Get appropriate redirect message based on user's request"""
    
    if any(word in user_message.lower() for word in ["apply", "leave"]):
        action = "apply for leave"
    elif any(word in user_message.lower() for word in ["update", "change", "modify"]):
        action = "update your information"
    elif any(word in user_message.lower() for word in ["submit", "upload"]):
        action = "submit a request"
    elif any(word in user_message.lower() for word in ["check in", "checkin"]):
        action = "check in"
    elif any(word in user_message.lower() for word in ["approve", "reject"]):
        action = "manage approvals"
    else:
        action = "perform this action"
    
    return (
        f"I can help you view information, but I'm not able to {action} on your behalf. "
        f"Please use the HRMS portal directly to do this: {hrms_portal_url}\n\n"
        f"Is there anything you'd like to look up instead?"
    )
