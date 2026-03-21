"""
Configuration settings for ILbuy Intent Service.
Uses Pydantic Settings for environment variable management.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    env: Literal["development", "staging", "production"] = "development"
    port: int = 8010
    log_level: str = "INFO"
    service_name: str = "intent-svc"
    version: str = "1.0.0"

    # Downstream service URLs
    llm_svc_url: str = "http://llm-svc:8011"

    # Hugging Face / Transformers
    hf_model_name: str = "hfl/chinese-roberta-wwm-ext"
    nlp_device: str = "cpu"

    # CORS
    allowed_origins: list[str] = ["*"]

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        return self.env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()


# Module-level convenience alias
settings = get_settings()
