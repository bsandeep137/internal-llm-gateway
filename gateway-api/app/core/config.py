import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file (gateway-api/app/core/config.py → gateway-api/.env)
# so it is found regardless of the working directory uvicorn is launched from.
_ENV_FILE = os.path.join(os.path.dirname(__file__), "..", "..", ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/llmgateway"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    secret_key: str = "dev-secret-key-change-in-production"
    app_env: str = "development"
    # Redaction is always on for sensitive/internal; this flag controls public too
    redact_public_prompts: bool = False


settings = Settings()
