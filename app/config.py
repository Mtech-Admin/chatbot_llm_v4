import os
from typing import Literal, Optional, Tuple

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote, quote_plus


def _normalize_postgresql_connection_url(url: str) -> str:
    """
    Percent-encode username/password so characters like @ in the password are not
    parsed as the userinfo/host boundary (e.g. ...:Admin@123@localhost...).
    """
    u = url.strip()
    prefixes = ("postgresql+psycopg2://", "postgresql://", "postgres://")
    prefix = None
    for p in prefixes:
        if u.startswith(p):
            prefix = p
            rest = u[len(p) :]
            break
    if not prefix:
        return u
    at = rest.rfind("@")
    if at <= 0:
        return u
    userinfo, hostpart = rest[:at], rest[at + 1 :]
    colon = userinfo.find(":")
    if colon < 0:
        return u
    user, password = userinfo[:colon], userinfo[colon + 1 :]
    return f"{prefix}{user}:{quote(password, safe='')}@{hostpart}"


def _redis_url_with_password(
    url: str, username: str = "", password: str = ""
) -> str:
    """
    If REDIS_PASSWORD is set and the URL has no userinfo, insert :password@ or user:pass@.
    Use when the server has requirepass / ACL and REDIS_URL is only host:port.
    """
    u = (url or "").strip()
    pwd = (password or "").strip()
    if not pwd:
        return u
    if "://" not in u:
        return u
    scheme, rest = u.split("://", 1)
    if "@" in rest:
        return u
    user = (username or "").strip()
    if user:
        auth = f"{quote(user, safe='')}:{quote(pwd, safe='')}@"
    else:
        auth = f":{quote(pwd, safe='')}@"
    return f"{scheme}://{auth}{rest}"


class Settings(BaseSettings):
    """Application configuration"""
    
    # LLM Configuration
    LLM_PROVIDER: Literal["groq", "vllm", "deepinfra"] = "groq"
    GROQ_API_KEY: str = ""
    VLLM_BASE_URL: str = "http://localhost:8000/v1"
    # DeepInfra — OpenAI-compatible API (https://deepinfra.com/dash/api_keys)
    DEEPINFRA_BASE_URL: str = "https://api.deepinfra.com/v1/openai"
    DEEPINFRA_API_KEY: str = Field(
        default="",
        validation_alias=AliasChoices("DEEPINFRA_API_KEY", "DEEPINFRA_TOKEN"),
    )
    DEEPINFRA_MODEL: str = "deepseek-ai/DeepSeek-V3"
    # Optional: model id for final response polish only (same OpenAI-compatible API as main LLM).
    # If empty, uses the main model. Set a smaller instruct model to cut ~50% latency on review calls.
    LLM_REVIEW_MODEL: str = "Qwen/Qwen3.5-4B"
    ENABLE_RESPONSE_REVIEW: bool = False
    POLICY_RAG_ENABLED: bool = True
    POLICY_RAG_DOC_CONFIDENCE_THRESHOLD: float = 0.26
    POLICY_RAG_FAQ_CONFIDENCE_THRESHOLD: float = 0.25
    POLICY_RAG_TOP_K: int = 5

    # HRMS API Configuration
    HRMS_BASE_URL: str = "http://localhost:3001/api"
    HRMS_TIMEOUT: int = 15
    
    # SSO/JWT Configuration
    SSO_PUBLIC_KEY: str = ""
    SECRET_KEY: str = "dev_secret_key_change_in_production"
    # GET /v1/chat/history — HS256 tokens verified with this secret (falls back to SECRET_KEY if empty).
    JWT_SECRET: str = ""
    
    # Database — same PostgreSQL as DMRC_HRMS_API (TypeORM migrations own policy_qa, chatbot_conversations).
    # If set, overrides POSTGRES_*-built URL (e.g. paste the same DATABASE URL as Nest uses for Postgres).
    CHATBOT_DATABASE_URL: str = ""
    POSTGRES_HOST: str = "localhost"
    POSTGRES_LOCAL_PORT: int = 5432
    POSTGRES_USERNAME: str = "chatbot"
    POSTGRES_PASSWORD: str = "chatbot_dev"
    POSTGRES_DATABASE: str = "postgres"
    DATABASE_URL: str = ""
    
    # Redis — if the server uses requirepass, set REDIS_PASSWORD or use redis://:pass@host:6379/0
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_USERNAME: str = ""
    REDIS_PASSWORD: str = "406de28661f5fb0a"
    SESSION_TTL: int = 1800  # 30 minutes
    MEMORY_TTL: int = 86400 * 7  # 7 days
    
    # Application Configuration
    APP_NAME: str = "DMRC HRMS Chatbot"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env.local",
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _build_database_url(self):
        override = (self.CHATBOT_DATABASE_URL or "").strip()
        if override:
            self.DATABASE_URL = _normalize_postgresql_connection_url(override)
            return self
        escaped_password = quote_plus(self.POSTGRES_PASSWORD)
        self.DATABASE_URL = (
            f"postgresql://{self.POSTGRES_USERNAME}:{escaped_password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_LOCAL_PORT}/{self.POSTGRES_DATABASE}"
        )
        return self

    @model_validator(mode="after")
    def _apply_redis_auth(self):
        self.REDIS_URL = _redis_url_with_password(
            self.REDIS_URL,
            self.REDIS_USERNAME,
            self.REDIS_PASSWORD,
        )
        return self

settings = Settings()
_llm_client = None
_llm_client_signature: Optional[Tuple[str, str, str]] = None


def _groq_api_key() -> str:
    return (settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "") or "").strip()


def _deepinfra_api_key() -> str:
    """Resolve token from Settings or OS env (PM2 / shell sometimes only set DEEPINFRA_TOKEN)."""
    return (
        (settings.DEEPINFRA_API_KEY or "").strip()
        or os.environ.get("DEEPINFRA_TOKEN", "").strip()
        or os.environ.get("DEEPINFRA_API_KEY", "").strip()
    )


def get_llm_client():
    """Return AsyncOpenAI client for Groq, vLLM, or DeepInfra (OpenAI-compatible)."""
    from openai import AsyncOpenAI

    global _llm_client
    global _llm_client_signature

    provider = settings.LLM_PROVIDER
    base_url = ""
    api_key = ""
    if provider == "groq":
        api_key = _groq_api_key()
        base_url = "https://api.groq.com/openai/v1"
    elif provider == "vllm":
        api_key = "not-needed"
        base_url = settings.VLLM_BASE_URL
    elif provider == "deepinfra":
        api_key = _deepinfra_api_key()
        base_url = settings.DEEPINFRA_BASE_URL.rstrip("/")

    signature = (provider, base_url, api_key)
    if _llm_client is not None and _llm_client_signature == signature:
        return _llm_client

    if settings.LLM_PROVIDER == "groq":
        if not api_key:
            raise ValueError(
                "LLM_PROVIDER=groq requires GROQ_API_KEY (non-empty). "
                "Set it in .env.local or the process environment."
            )
        _llm_client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        _llm_client_signature = signature
        return _llm_client
    if settings.LLM_PROVIDER == "vllm":
        _llm_client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        _llm_client_signature = signature
        return _llm_client
    if settings.LLM_PROVIDER == "deepinfra":
        if not api_key:
            raise ValueError(
                "LLM_PROVIDER=deepinfra requires DEEPINFRA_TOKEN or DEEPINFRA_API_KEY "
                "(non-empty). Set it in .env.local or PM2 env."
            )
        _llm_client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        _llm_client_signature = signature
        return _llm_client
    raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")


def get_model_name() -> str:
    """Model id passed to chat.completions (provider-specific)."""
    if settings.LLM_PROVIDER == "groq":
        return "llama-3.3-70b-versatile"
    if settings.LLM_PROVIDER == "vllm":
        return "Qwen/Qwen2.5-14B-Instruct-AWQ"
    if settings.LLM_PROVIDER == "deepinfra":
        return settings.DEEPINFRA_MODEL
    raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")


def get_review_model_name() -> str:
    """Model for `review_user_response` only; defaults to main model if unset."""
    override = (settings.LLM_REVIEW_MODEL or "").strip()
    if override:
        return override
    return get_model_name()


def get_review_model_fallback_chain() -> list[str]:
    """
    Models to try for response review, in order: optional fast model, then main chat model.
    Used when the review model id is wrong or unavailable on the provider.
    """
    main = get_model_name()
    r = (settings.LLM_REVIEW_MODEL or "").strip()
    if r and r != main:
        return [r, main]
    return [main]
