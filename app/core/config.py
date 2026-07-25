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

    # Database
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
    def validate_production_secrets(self) -> "Settings":
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
