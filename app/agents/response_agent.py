"""
Final response reviewer agent.
Ensures user-facing responses stay clear, friendly, and non-technical.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.config import get_llm_client, get_review_model_fallback_chain

logger = logging.getLogger(__name__)

REVIEW_PROMPT = """You are the final response reviewer for DMRC HRMS Chatbot.

Your job:
1) Rewrite the draft response into clear, user-readable text.
2) Never expose backend/system/debug/API details.
3) If the user message is ONLY a short greeting (hi/hello/namaste/good morning etc.) with no other request,
   respond with EXACTLY this text and nothing else:
   Hello. How can I assist you today?
4) Keep meaning and factual content of the draft.
5) Keep response concise and professional.
5b) Do not add facts, numbers, or caveats that are not already supported by the draft (no guessing).
6) Do not mention internal components (agent, tool, API, endpoint, upload script, database, schema, logs).
7) If draft indicates a technical/system failure, return a calm user-friendly line like:
   "I am unable to fetch that right now. Please try again in a moment."
   If the draft says a field is not available / not on record / not in HRMS, keep that meaning
   (do not rewrite it as a system failure).

Return only the final user-facing response text.
"""


def _looks_like_greeting(text: str) -> bool:
    value = text.strip().lower()
    return bool(re.search(r"\b(hi|hello|hey|namaste|good morning|good afternoon|good evening)\b", value))


def _is_pure_greeting(user_message: str) -> bool:
    """
    Detect short greeting-only inputs so we don't append capability menus.
    """
    raw = user_message.strip()
    if not raw:
        return False
    if len(raw) > 48:
        return False
    if any(ch in raw for ch in ("?", "!", ":")):
        return False
    lowered = raw.lower()
    if not _looks_like_greeting(lowered):
        return False
    # Allow a tiny tail like "there" / "team" but not real questions
    tokens = re.findall(r"[a-zA-Z]+", lowered)
    if len(tokens) > 4:
        return False
    return True


def _fallback_cleanup(text: str, user_message: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return "I am unable to fetch that right now. Please try again in a moment."

    blocked_keywords = [
        "api",
        "endpoint",
        "schema",
        "database",
        "upload",
        "script",
        "traceback",
        "error code",
        "http",
        "server",
    ]
    if any(k in cleaned.lower() for k in blocked_keywords):
        cleaned = "I am unable to fetch that right now. Please try again in a moment."

    # Strip hallucinated "tool" text some models emit when a prior tool failed
    if re.search(r"!function_call|function_call\s*:", cleaned, re.IGNORECASE):
        cleaned = "I am unable to fetch that right now. Please try again in a moment."

    if _is_pure_greeting(user_message):
        return "Hello. How can I assist you today?"
    return cleaned


async def review_user_response(user_message: str, draft_response: str, language: str = "en") -> str:
    if _is_pure_greeting(user_message):
        return "Hello. How can I assist you today?"
    client = get_llm_client()
    prompt = (
        f"User message: {user_message}\n"
        f"Draft response: {draft_response}\n"
        f"Language: {language}\n"
        "Final response:"
    )
    last_exc: Optional[Exception] = None
    for model in get_review_model_fallback_chain():
        try:
            response = await client.chat.completions.create(
                model=model,
                max_tokens=300,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": REVIEW_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            final_text = (response.choices[0].message.content or "").strip()
            if not final_text:
                return _fallback_cleanup(draft_response, user_message)
            return final_text
        except Exception as exc:
            last_exc = exc
            logger.warning("Response review failed for model %s: %s", model, str(exc))
    if last_exc:
        logger.warning("All review model attempts failed, using fallback cleanup")
    return _fallback_cleanup(draft_response, user_message)
