"""Application Configuration for SurakshaVani."""

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_default_database_url() -> str:
    # On Vercel serverless, root filesystem is read-only; /tmp is writable
    if os.getenv("VERCEL"):
        return "sqlite+aiosqlite:////tmp/surakshavani.db"
    return "sqlite+aiosqlite:///./surakshavani.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "SurakshaVani"
    APP_ENV: str = "dev"  # dev | demo | prod
    DEMO_MODE: bool = True
    SECRET_KEY: str = "surakshavani-secret-key-change-in-production-2026"
    
    # Database
    DATABASE_URL: str = Field(
        default_factory=get_default_database_url,
        description="Async database connection URL. Uses SQLite for zero-setup demo, Postgres in prod."
    )
    
    # Redis (Optional in local demo mode, fallback to in-memory)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Cryptographic keys
    HMAC_PEPPER: str = "surakshavani-pepper-for-blind-indexing-2026-secret"
    FIELD_ENCRYPTION_KEY: str = "7V8x9Z1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9="  # 32-byte urlsafe base64
    
    # Providers
    ASR_PROVIDER: str = "mock"  # mock | whisper_local | sarvam
    ASR_CONFIDENCE_MIN: float = 0.65
    
    LLM_PROVIDER: str = "recorded"  # recorded | anthropic
    LLM_MODEL: str = "claude-3-5-haiku-latest"
    ANTHROPIC_API_KEY: str = ""
    
    # Channels
    CHANNEL: str = "web_sim"  # web_sim | whatsapp_cloud | telegram
    WHATSAPP_VERIFY_TOKEN: str = "sv_verify_token_2026"
    WHATSAPP_APP_SECRET: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    
    # Operational Thresholds
    GOLDEN_HOUR_MINUTES: int = 60
    RATE_LIMIT_MSGS_PER_MIN: int = 20
    AUDIO_RETENTION_MINUTES: int = 10
    CONSOLE_ORIGIN: str = "http://localhost:8000"


settings = Settings()
