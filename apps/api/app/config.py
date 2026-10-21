"""Environment configuration. All values come from environment variables (.env locally).

Secrets never leave the server. The frontend receives only its own public config.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Persistence
    database_url: str = "sqlite:///./ghostrange.db"

    # API
    cors_origins: list[str] = ["http://localhost:5173"]

    # Nebius Token Factory (NVIDIA Nemotron) — optional; empty means degraded-AI mode
    nebius_api_key: str | None = None
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1"
    nebius_model: str | None = None

    # Tavily — optional threat-intel context, never required for the core demo
    tavily_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()