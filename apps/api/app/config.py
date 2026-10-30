"""Environment configuration. All values come from environment variables (.env locally).

Secrets never leave the server. The frontend receives only its own public config.
The repo-root .env is shared by the API and Vite; apps/api/.env may override it.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_API_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _API_DIR.parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_REPO_ROOT / ".env", _API_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Persistence
    database_url: str = "sqlite:///./ghostrange.db"

    # API
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ]

    # Nebius Token Factory (NVIDIA Nemotron) — optional; empty means degraded-AI mode
    nebius_api_key: str | None = None
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1"
    nebius_model: str | None = None

    # Tavily — optional threat-intel context, never required for the core demo
    tavily_api_key: str | None = None

    @field_validator("nebius_api_key", "tavily_api_key", "nebius_model", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        # The shipped .env.example leaves these blank; an empty string must mean
        # "not configured", never "configured with an empty key".
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()