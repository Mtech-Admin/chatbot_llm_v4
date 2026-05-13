"""
Token-budget helpers for conversation history.

Uses a conservative estimate (mixed heuristics for en/hi text) so we stay
safely under provider context limits without requiring provider-specific tokenizers.
"""

from __future__ import annotations

from typing import List

from app.config import settings
from app.models.message import Message


def effective_context_limit_tokens() -> int:
    """Rough input context ceiling for budgeting (provider / model aware)."""
    if settings.LLM_CONTEXT_WINDOW_OVERRIDE > 0:
        return settings.LLM_CONTEXT_WINDOW_OVERRIDE
    provider = settings.LLM_PROVIDER
    if provider == "sarvam":
        lowered = (settings.SARVAM_MODEL or "").lower()
        if "105" in lowered:
            return max(8192, settings.SARVAM_CONTEXT_WINDOW_TOKENS_105B)
        return max(8192, settings.SARVAM_CONTEXT_WINDOW_TOKENS_30B)
    if provider == "groq":
        return 128000
    if provider == "vllm":
        return max(8192, settings.VLLM_CONTEXT_WINDOW_FALLBACK_TOKENS)
    if provider == "deepinfra":
        return max(8192, settings.DEEPINFRA_CONTEXT_WINDOW_FALLBACK_TOKENS)
    return 64000


def format_trimmed_history_block(
    messages: List[Message],
    max_tokens_est: int,
    *,
    header: str = "Recent conversation:",
    empty_text: str = "No previous conversation history.",
) -> str:
    """Render trimmed dialogue for prompts (agents, routing, reviewers)."""
    trimmed = trim_conversation_messages(messages, max_tokens_est)
    if not trimmed:
        return empty_text
    lines = [header]
    for msg in trimmed:
        role_label = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
        lines.append(f"{role_label}: {msg.content}")
    return "\n".join(lines)


def estimate_text_tokens(text: str) -> int:
    """Rough input-token estimate for budgeting (not billing-accurate)."""
    if not text:
        return 0
    # Slightly conservative vs. pure len/4 for short English; ok for TPM/window guarding.
    return max(len(text) // 3, len(text.split()) // 2, 1)


def conversation_token_estimate(messages: List[Message]) -> int:
    return sum(estimate_text_tokens(m.content or "") for m in messages)


def trim_conversation_messages(
    messages: List[Message],
    max_tokens_est: int,
    *,
    max_message_count: int | None = None,
) -> List[Message]:
    """
    Drop oldest turns until estimated tokens and optional message count fit.

    Messages are assumed to arrive in chronological order as user/assistant pairs;
    trimming removes from the front two at a time when possible.
    """
    if not messages or max_tokens_est <= 0:
        return []

    msgs = list(messages)

    def over_budget() -> bool:
        if conversation_token_estimate(msgs) > max_tokens_est:
            return True
        if max_message_count is not None and len(msgs) > max_message_count:
            return True
        return False

    while over_budget():
        if len(msgs) >= 2:
            msgs = msgs[2:]
            continue
        if len(msgs) == 1:
            lone = msgs[0]
            content = lone.content or ""
            if estimate_text_tokens(content) <= max_tokens_est:
                break
            # Last resort: truncate a single oversized message (rare — bad client input).
            approx_chars = max(0, max_tokens_est * 3 - 20)
            trimmed = content[:approx_chars].rstrip()
            msgs[0] = lone.model_copy(
                update={
                    "content": (
                        f"{trimmed}\n\n[Earlier message truncated to fit session budget.]"
                    )
                }
            )
            break
        break

    return msgs


def trim_text_to_estimated_tokens(text: str, max_tokens_est: int) -> str:
    """Truncate a single blob (e.g. RAG evidence) to a token budget."""
    if not text or max_tokens_est <= 0:
        return ""
    if estimate_text_tokens(text) <= max_tokens_est:
        return text
    approx_chars = max(0, max_tokens_est * 3 - 48)
    out = text[:approx_chars].rstrip()
    return f"{out}\n\n[RAG context truncated to fit prompt budget.]"
