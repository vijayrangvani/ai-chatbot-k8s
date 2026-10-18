"""Settings from environment variables / .env. Add a field here for every new config value."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ai-chatbot"
    environment: str = "dev"  # dev / staging / prod
    log_level: str = "INFO"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b"
    database_url: str = "postgresql+psycopg://app:app@localhost:5432/chatdb"
    redis_url: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
