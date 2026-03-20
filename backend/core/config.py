"""
core/config.py
──────────────────────────────────────────────────────────────────────────────
Central configuration via Pydantic Settings.
All values read from environment variables / .env file.
Every other module imports from here — NEVER read os.getenv() directly.
"""
from __future__ import annotations

import secrets
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    ENV: str = Field("development", description="development | production")
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_hex(32),
        description="JWT signing secret — set explicitly in production",
    )
    ALLOWED_ORIGINS: str = Field(
        "http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated allowed CORS origins",
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://insightflow:insightflow@localhost:5432/insightflow"
    )
    REDIS_URL: str = Field("redis://localhost:6379/0")

    # ── Storage ──────────────────────────────────────────────────────────────
    DATA_DIR: str = Field("./data/users", description="Root path for user SQLite databases")
    MAX_CSV_SIZE_MB: int = Field(50, ge=1, le=500)
    MAX_DATASETS_PER_USER: int = Field(10, ge=1, le=100)

    @property
    def max_csv_bytes(self) -> int:
        return self.MAX_CSV_SIZE_MB * 1024 * 1024

    # ── LLM Providers ────────────────────────────────────────────────────────
    GROQ_API_KEY: str = Field("", description="Primary Groq API key")
    GROQ_API_KEY_2: str = Field("", description="Backup Groq key")
    GROQ_API_KEY_3: str = Field("", description="Third Groq key")
    GROQ_MODEL: str = Field("llama-3.3-70b-versatile")

    GEMINI_API_KEY: str = Field("", description="Primary Gemini API key")
    GEMINI_API_KEY_2: str = Field("", description="Backup Gemini key")
    GEMINI_MODEL: str = Field("gemini-2.0-flash")

    ANTHROPIC_API_KEY: str = Field("", description="Optional Anthropic key")
    OPENAI_API_KEY: str = Field("", description="Optional OpenAI key")

    LLM_CACHE_TTL_SECONDS: int = Field(600, description="Redis LLM response cache TTL")
    LLM_REQUEST_TIMEOUT: float = Field(45.0, description="Per-LLM-call timeout seconds")

    # ── Authentication ────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = Field("", description="Google OAuth2 client ID")
    GOOGLE_CLIENT_SECRET: str = Field("", description="Google OAuth2 client secret")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(15, ge=5, le=60)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, ge=1, le=30)

    ALGORITHM: str = "HS256"

    # ── Observability ─────────────────────────────────────────────────────────
    SENTRY_DSN: str = Field("", description="Sentry DSN — leave empty to disable")
    LOG_LEVEL: str = Field("INFO", description="DEBUG | INFO | WARNING | ERROR")

    # ── Rate limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_QUERY: str = Field("15/minute", description="NL query rate per user")
    RATE_LIMIT_UPLOAD: str = Field("5/minute", description="CSV upload rate per user")
    RATE_LIMIT_AUTH: str = Field("5/minute", description="Login attempts per IP")

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid:
            raise ValueError(f"LOG_LEVEL must be one of {valid}")
        return v_upper

    @field_validator("ENV")
    @classmethod
    def validate_env(cls, v: str) -> str:
        valid = {"development", "production", "test"}
        v_lower = v.lower()
        if v_lower not in valid:
            raise ValueError(f"ENV must be one of {valid}")
        return v_lower


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings singleton.
    Use this everywhere: `from core.config import get_settings; cfg = get_settings()`
    """
    return Settings()
