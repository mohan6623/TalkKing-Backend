from pydantic_settings import BaseSettings
from typing import Literal

class Settings(BaseSettings):
    ENVIRONMENT: Literal["production", "staging", "development"] = "development"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # AI API Keys
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    HUME_API_KEY: str = ""

    # Redis
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://127.0.0.1:6379/1"

    # CORS
    CORS_ORIGINS: list[str] = [
        "https://talkking.me",
        "https://www.talkking.me",
        "http://localhost:5173",
    ]

    # Monitoring
    SENTRY_DSN: str = ""
    DATADOG_API_KEY: str = ""

    # Email
    MAILGUN_API_KEY: str = ""
    MAILGUN_DOMAIN: str = "mail.talkking.me"

    class Config:
        env_file = ".env"

settings = Settings()
