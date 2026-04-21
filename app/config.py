from typing import Literal
from urllib.parse import quote, quote_plus
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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


class Settings(BaseSettings):
    """Application configuration"""
    
    # LLM Configuration
    LLM_PROVIDER: Literal["groq", "vllm"] = "groq"
    GROQ_API_KEY: str = ""
    VLLM_BASE_URL: str = "http://localhost:8000/v1"
    
    # HRMS API Configuration
    HRMS_BASE_URL: str = "http://localhost:3001/api"
    HRMS_TIMEOUT: int = 15
    
    # SSO/JWT Configuration
    SSO_PUBLIC_KEY: str = ""
    SECRET_KEY: str = "dev_secret_key_change_in_production"
    
    # Database — same PostgreSQL as DMRC_HRMS_API (TypeORM migrations own policy_qa, chatbot_conversations).
    # If set, overrides POSTGRES_*-built URL (e.g. paste the same DATABASE URL as Nest uses for Postgres).
    CHATBOT_DATABASE_URL: str = ""
    POSTGRES_HOST: str = "localhost"
    POSTGRES_LOCAL_PORT: int = 5432
    POSTGRES_USERNAME: str = "chatbot"
    POSTGRES_PASSWORD: str = "chatbot_dev"
    POSTGRES_DATABASE: str = "postgres"
    DATABASE_URL: str = ""
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"
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

settings = Settings()

def get_llm_client():
    """Get configured LLM client (Groq or vLLM)"""
    from openai import AsyncOpenAI
    
    if settings.LLM_PROVIDER == "groq":
        return AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.GROQ_API_KEY,
        )
    elif settings.LLM_PROVIDER == "vllm":
        return AsyncOpenAI(
            base_url=settings.VLLM_BASE_URL,
            api_key="not-needed",
        )
    else:
        raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")

def get_model_name() -> str:
    """Get configured model name based on LLM provider"""
    if settings.LLM_PROVIDER == "groq":
        return "llama-3.3-70b-versatile"
    elif settings.LLM_PROVIDER == "vllm":
        return "Qwen/Qwen2.5-14B-Instruct-AWQ"
    else:
        raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")
