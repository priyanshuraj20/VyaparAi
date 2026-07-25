import re
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG_AI: bool = False  # Set to True in .env to show Developer AI Planner Reasoning header

    # WhatsApp Meta API
    OWNER_PHONE_NUMBER: str = "919608147859"
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "vyapar_ai_secret_verify_token"
    WHATSAPP_APP_SECRET: str = ""

    # Database (Supports local Postgres, Supabase, Neon, Railway & Render)
    DATABASE_URL: str = "postgresql+asyncpg://vyapar:vyapar_pass@postgres:5432/vyapar_db"
    SYNC_DATABASE_URL: str = "postgresql+psycopg2://vyapar:vyapar_pass@postgres:5432/vyapar_db"

    # OpenRouter LLM Provider
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "deepseek/deepseek-chat"
    OPENROUTER_VISION_MODEL: str = "openai/gpt-4o-mini"

    # Groq Provider (Ultra-fast latency)
    GROQ_API_KEY: str = ""

    # Upstash Redis (Temporary Conversation State & Idempotency ONLY)
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if not v:
            return v
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("SYNC_DATABASE_URL", mode="before")
    @classmethod
    def normalize_sync_database_url(cls, v: str) -> str:
        if not v:
            return v
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+psycopg2://", 1)
        if v.startswith("postgresql://") and "+psycopg2" not in v:
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    @field_validator("OWNER_PHONE_NUMBER", mode="before")
    @classmethod
    def normalize_phone_number(cls, v: str) -> str:
        if not v:
            return v
        cleaned = re.sub(r"\D", "", v)
        if len(cleaned) == 10:
            cleaned = "91" + cleaned
        return cleaned

    @model_validator(mode="after")
    def derive_sync_db_url_and_validate(self) -> "Settings":
        # Auto-derive SYNC_DATABASE_URL from DATABASE_URL if external cloud database is used
        if self.DATABASE_URL and ("@postgres:5432/" not in self.DATABASE_URL):
            if not self.SYNC_DATABASE_URL or ("@postgres:5432/" in self.SYNC_DATABASE_URL):
                sync_url = self.DATABASE_URL
                if "postgresql+asyncpg://" in sync_url:
                    sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
                elif "postgres://" in sync_url:
                    sync_url = sync_url.replace("postgres://", "postgresql+psycopg2://", 1)
                elif "postgresql://" in sync_url:
                    sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://", 1)
                self.SYNC_DATABASE_URL = sync_url

        if self.ENVIRONMENT == "production":
            missing = []
            if not self.WHATSAPP_ACCESS_TOKEN:
                missing.append("WHATSAPP_ACCESS_TOKEN")
            if not self.WHATSAPP_PHONE_NUMBER_ID:
                missing.append("WHATSAPP_PHONE_NUMBER_ID")
            if not self.OPENROUTER_API_KEY and not self.GROQ_API_KEY:
                missing.append("OPENROUTER_API_KEY or GROQ_API_KEY")
            if missing:
                raise ValueError(f"Missing required production environment variables: {', '.join(missing)}")
        return self


settings = Settings()
