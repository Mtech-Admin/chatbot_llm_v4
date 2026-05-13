"""
Intent Classification - Determines routing for user query
"""

import logging
import re
from typing import Literal, Optional, Any, List

from app.config import get_llm_client, get_model_name, settings
from app.llm.chat_completions import chat_completions_create
from app.llm.conversation_budget import format_trimmed_history_block
from app.models.message import MessageRole
from app.orchestrator.state import OrchestratorState, orch_get

logger = logging.getLogger(__name__)

_ACTION_MARKERS = (
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
    "approve",
    "reject",
    "check in",
    "check out",
    "checkin",
    "checkout",
)


def _has_action_intent(msg: str) -> bool:
    return any(re.search(rf"\b{re.escape(marker)}\b", msg) for marker in _ACTION_MARKERS)


def _classify_intent_fast(user_message: str) -> Optional[str]:
    msg = (user_message or "").lower().strip()
    if not msg:
        return "unknown"

    has_action = _has_action_intent(msg)

    if has_action:
        return "redirect_to_portal"

    if re.search(r"\b(attendance|present|absent|late|early leaving|punch|check[- ]?in time|check[- ]?out time)\b", msg):
        return "attendance_inquiry"

    if re.search(r"\b(public holiday|official holiday|holiday list|holiday calendar|upcoming holiday|next holiday)\b", msg):
        return "holiday_inquiry"

    if "policy" in msg or "admissible" in msg or "eligibility" in msg:
        return "policy_inquiry"

    if re.search(r"\bvpf\b|voluntary\s*provident", msg):
        return "vpf_inquiry"

    if re.search(r"\bnoc\b|no\s+objection|ex\s*-?\s*india|outside job|visa|passport|higher studies|online course", msg):
        return "noc_inquiry"

    if re.search(r"\bleave\b", msg):
        return "leave_inquiry"

    if re.search(
        r"\b(profile|pan|aadhaar|aadhar|ifsc|department|designation|reporting\s+manager"
        r"|employee\s*(?:id|number|no\b)|date\s+of\s+joining|\bdoj\b|\bdob\b"
        r"|\bfull\s+name\b|\bmy\s+name\b|\bi\s+(?:was\s+)?born\b|\bwho\s+am\s+i\b"
        r"|\babout\s+(?:myself|me)\b|\bpersonal\s+details?\b"
        r"|\bi'?m\b|\bi\s+am\b|\b(call(?:ed)?\s+me|my\s+details?)\b|\bmy\s+surname\b"
        r"|\bmiddle\s+name\b|\blast\s+name\b|\bfamily\s+name\b"
        # token "name" only with possessive/my/what/am — avoids unrelated "name this"
        r"|(?:what|who|tell|show|know|remember)\s+.+\s+name\b|\bname\s*\?"
        r"|\bmy\s+(?:registered\s*)?name\b)",
        msg,
    ):
        return "profile_inquiry"

    return None


_STICKY_ELIGIBLE_INTENTS = frozenset(
    {
        "attendance_inquiry",
        "profile_inquiry",
        "noc_inquiry",
        "vpf_inquiry",
        "policy_inquiry",
        "holiday_inquiry",
        "leave_inquiry",
    }
)


def _looks_like_contextual_followup(user_message: str, conversation_history: List[Any]) -> bool:
    """True when the utterance plausibly continues the last specialist answer (not a fresh topic)."""
    if not conversation_history:
        return False
    tail = conversation_history[-10:]
    if not any(getattr(m, "role", None) == MessageRole.ASSISTANT for m in tail):
        return False

    ml = (user_message or "").strip().lower()
    if not ml:
        return False

    standalone_greeting = bool(
        re.fullmatch(r"(hi|hello|hey|namaste)(\s+there)?[\s!.]*", ml, flags=re.I)
    )
    if standalone_greeting and len(ml) < 36:
        return False

    continuation_markers = (
        r"^\s*(yes|yeah|yep|nope|no|sure|ok|okay|please)\b",
        r"\b(full|more|complete)\s+breakdown\b",
        r"\b(more|full|complete)\s+details?\b",
        r"\bcomplete\s+information\b",
        r"\belaborate\b",
        r"\bwalk\s+me\s+through\b",
        r"\btell\s+me\s+(more|everything)\b",
        r"\bwhat\s+about\b",
        r"\bhow\s+about\b",
        r"\band\s+(for\s+|the\s+)?(same|that|those|above|previous|last)\b",
        r"\b(and|also)\s+then\b",
        r"\b(can|could)\s+you\s+(explain|expand|break\s*down)\b",
        r"\bas\s+I\s+said\b",
        r"\bgo\s+(ahead\s+)?(and\s+)?(continue|tell)\b",
        r"\bin\s+that\s+(case|matter)\b",
        r"\bprovide\b.+?\b(breakdown|details?)\b",
        r"\bgive\s+me\s+.+?\b(breakdown|details?)\b",
    )
    if any(re.search(p, ml, re.I) for p in continuation_markers):
        return True

    if re.search(
        r"\b(it|they|them|that\s+record|that\s+request|this\s+(one|request)|those|same\s+one"
        r"|the\s+above|previous\s+(reply|answer|month|period)|your\s+(last\s+)?(reply|answer))\b",
        ml,
        re.I,
    ):
        return True

    narrow_question = (
        bool(re.search(r"[?。？]", ml))
        and len(ml) <= 200
        and len(ml.split()) <= 22
        and bool(re.search(r"^\s*(why|when|where|how|who|which)\s+", ml, re.I))
    )
    return narrow_question


def _infer_sticky_topic_intent(state: Any) -> Optional[str]:
    """
    Re-use the session's last successful specialist routing when the user clearly continues that thread.
    """
    last = orch_get(state, "last_intent")
    if not last or last not in _STICKY_ELIGIBLE_INTENTS:
        return None
    if not _looks_like_contextual_followup(
        orch_get(state, "user_message", "") or "",
        orch_get(state, "conversation_history") or [],
    ):
        return None
    return last


INTENT_CLASSIFIER_PROMPT = """You are an expert intent classifier for an HR chatbot.

Analyze the user's message and classify it into ONE of these intents:

1. "attendance_inquiry" - User wants to check their attendance, daily records, status
   Examples: "Show my attendance", "What's my attendance for March?", "When did I check in today?"

2. "profile_inquiry" - User wants to VIEW their own employee / HR profile facts (read-only)
   Examples: "What is my PAN?", "My Aadhaar on record", "What is my employee ID?", "Who is my reporting manager?",
   "What department am I in?", "What is my designation?", "Show my profile", "What is my bank IFSC in HRMS?",
   "What is my office location?", "My date of joining", "What is my name?", "Who am I?"

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
- If the PRIOR ASSISTANT turn answered using one specialist domain above and the new user message CLEARLY CONTINUES that thread (follow-up detail, affirmation, narrower question about the same matter), classify as the SAME intent again — do NOT switch domains.
- If there's ANY ambiguity about actions vs viewing, prefer "redirect_to_portal" to be safe
- Respond ONLY with the intent name, nothing else

Prior conversation turns (helps resolve pronouns/follow-ups; may be "(none)" on the first query):
{history_snippet}

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
        heuristic_intent = _classify_intent_fast(orch_get(state, "user_message", "") or "")
        if heuristic_intent:
            logger.info(
                "Intent classified by fast heuristic for employee %s: %s",
                orch_get(state, "employee_id"),
                heuristic_intent,
            )
            return heuristic_intent  # type: ignore[return-value]

        sticky = _infer_sticky_topic_intent(state)
        if sticky:
            logger.info(
                "Intent sticky-continuity for employee %s: %s",
                orch_get(state, "employee_id"),
                sticky,
            )
            return sticky  # type: ignore[return-value]

        client = get_llm_client()
        model = get_model_name()
        
        history_snippet = format_trimmed_history_block(
            orch_get(state, "conversation_history") or [],
            settings.CONVERSATION_INTENT_HISTORY_TOKEN_BUDGET,
            header="Prior conversation:",
            empty_text="(none)",
        ).strip()

        prompt = INTENT_CLASSIFIER_PROMPT.format(
            history_snippet=history_snippet,
            user_message=orch_get(state, "user_message", "") or "",
        )

        response = await chat_completions_create(
            client,
            model=model,
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Low temperature for deterministic classification
        )
        sticky = _infer_sticky_topic_intent(state)

        intent_text = (response.choices[0].message.content or "").strip().lower()
        logger.info(
            "Intent classifier raw response for employee %s: %s",
            orch_get(state, "employee_id"),
            intent_text,
        )

        if not intent_text and sticky:
            logger.info(
                "Empty classifier reply; using sticky intent %s (employee %s)",
                sticky,
                orch_get(state, "employee_id"),
            )
            return sticky  # type: ignore[return-value]

        if not intent_text:
            silent = _classify_intent_fast(orch_get(state, "user_message", "") or "")
            if silent and silent != "unknown":
                logger.info(
                    "Empty classifier reply; using fast heuristic %s (employee %s)",
                    silent,
                    orch_get(state, "employee_id"),
                )
                return silent  # type: ignore[return-value]

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
            msg = (orch_get(state, "user_message", "") or "").lower()
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
                "my name",
                "full name",
                "second name",
                "who am i",
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
            if sticky:
                logger.info(
                    "Intent recovered via sticky continuity as %s (employee %s)",
                    sticky,
                    orch_get(state, "employee_id"),
                )
                return sticky  # type: ignore[return-value]
            logger.warning(
                "Intent classifier fallback to unknown for employee %s, raw='%s'",
                orch_get(state, "employee_id"),
                intent_text,
            )
            return "unknown"
    
    except Exception as e:
        logger.error(
            "Error classifying intent for employee %s: %s",
            orch_get(state, "employee_id"),
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
