import os
from dataclasses import dataclass
from functools import lru_cache


def _split(value):
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./guardrails.db"
    llm_provider: str = "mock"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    secret_api_key: str = "sk-live-demo-51HfX9aQ2pLzR7vT3mKd"
    allowed_email_domains: tuple = ("company.example",)
    detection_threshold: float = 0.5
    cors_origins: tuple = ("http://localhost:5173", "http://localhost:8080")
    seed_on_start: bool = True


def load_settings(env=None):
    env = os.environ if env is None else env
    defaults = Settings()
    return Settings(
        database_url=env.get("DATABASE_URL", defaults.database_url),
        llm_provider=env.get("LLM_PROVIDER", defaults.llm_provider).lower(),
        anthropic_api_key=env.get("ANTHROPIC_API_KEY", defaults.anthropic_api_key),
        anthropic_model=env.get("ANTHROPIC_MODEL", defaults.anthropic_model),
        secret_api_key=env.get("SECRET_API_KEY", defaults.secret_api_key),
        allowed_email_domains=_split(env.get("ALLOWED_EMAIL_DOMAINS", ",".join(defaults.allowed_email_domains))),
        detection_threshold=float(env.get("DETECTION_THRESHOLD", defaults.detection_threshold)),
        cors_origins=_split(env.get("CORS_ORIGINS", ",".join(defaults.cors_origins))),
        seed_on_start=env.get("SEED_ON_START", "true").lower() in ("1", "true", "yes"),
    )


@lru_cache
def get_settings():
    return load_settings()
