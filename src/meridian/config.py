"""Application configuration, loaded from environment variables and .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"

    chroma_persist_dir: Path = Path("./data/chroma")


settings = Settings()
