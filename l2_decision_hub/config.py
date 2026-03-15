"""Configuration for the L2 Decision Hub."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Anthropic API
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-4-6"
    claude_max_tokens: int = 8192

    # Hub settings
    hub_max_concurrent: int = 5
    hub_auto_execute: bool = True

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False

    # Logging
    log_level: str = "INFO"


settings = Settings()
