from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DiagAssistAI API"
    api_v1_prefix: str = ""
    demo_mode: bool = True
    store_audio: bool = False

    database_url: str = "postgresql+psycopg://diagassist:diagassist@localhost:5432/diagassistai"

    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 720

    openai_api_key: str | None = None

    web_origins: str = "http://localhost:3000,http://web:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
