"""
Chat completions helper: exponential backoff on rate limits (HTTP 429 / TPMquota).

Aligned with Sarvam error semantics (``insufficient_quota_error`` includes rate limits).
See https://docs.sarvam.ai/api-reference-docs/api-guides-tutorials/chat-completion/overview
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from openai import APIStatusError, RateLimitError
except ImportError:  # pragma: no cover
    APIStatusError = type("APIStatusError", (Exception,), {})  # type: ignore[misc, assignment]
    RateLimitError = type("RateLimitError", (Exception,), {})  # type: ignore[misc, assignment]


def _is_retryable_rate_limit(exc: BaseException) -> bool:
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError) and getattr(exc, "status_code", None) == 429:
        return True
    return False


async def chat_completions_create(client: Any, **kwargs: Any) -> Any:
    """
    Call ``client.chat.completions.create`` with retries on TPM / RPM throttling.

    Retries honor ``settings.LLM_CHAT_RATE_LIMIT_MAX_RETRIES`` and
    ``settings.LLM_CHAT_RATE_LIMIT_BASE_DELAY_SEC`` (exponential with jitter).
    """
    max_retries = max(1, settings.LLM_CHAT_RATE_LIMIT_MAX_RETRIES)
    base_delay = max(0.05, settings.LLM_CHAT_RATE_LIMIT_BASE_DELAY_SEC)

    last_exc: BaseException | None = None
    for attempt in range(max_retries):
        try:
            return await client.chat.completions.create(**kwargs)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            last_exc = exc
            if not _is_retryable_rate_limit(exc) or attempt >= max_retries - 1:
                raise
            wait_s = base_delay * (2**attempt)
            wait_s *= 0.5 + random.random()  # jitter 0.5×–1.5×
            logger.warning(
                "LLM rate limited (attempt %s/%s); retry in %.2fs: %s",
                attempt + 1,
                max_retries,
                wait_s,
                exc,
            )
            await asyncio.sleep(wait_s)

    assert last_exc is not None  # pragma: no cover
    raise last_exc
