"""Application settings, read from environment variables (or a local `.env` file).

Every setting has a safe default for local development, so `uvicorn app.main:app`
works out of the box against the docker-compose Postgres and Redis.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# backend/app/config.py -> parents[2] is the repository root. Only used for the local-dev
# default; the Docker image sets MODEL_DIR explicitly.
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_DIR = REPO_ROOT / "artifacts" / "models" / "tfidf-logreg-1.0.0"

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://sentiment:sentiment@localhost:5432/sentiment"
    redis_url: str = "redis://localhost:6379/0"
    model_dir: Path = DEFAULT_MODEL_DIR

    cache_enabled: bool = True
    cache_ttl_seconds: int = Field(default=86_400, gt=0)

    max_text_length: int = Field(default=1_000, gt=0)
    batch_max_rows: int = Field(default=500, gt=0)
    batch_max_bytes: int = Field(default=1_000_000, gt=0)
    low_confidence_threshold: float = Field(default=0.55, ge=0, le=1)

    log_level: LogLevel = "INFO"
    # NoDecode: read the env var as a plain comma-separated string instead of JSON.
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    app_version: str = "1.0.0"
    environment: str = "development"

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        # Hosting platforms (e.g. Render) hand out `postgres://...` URLs. SQLAlchemy needs
        # the dialect+driver prefix to pick psycopg 3 rather than the default psycopg2.
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value.removeprefix(prefix)
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def uppercase_log_level(cls, value: str) -> str:
        return value.upper() if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    """Settings are read once per process; tests pass their own Settings to create_app()."""
    return Settings()
