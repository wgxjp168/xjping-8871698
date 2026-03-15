"""
Configuration settings for the LLM service.
Uses pydantic-settings for environment variable management.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service identity
    env: Literal["development", "staging", "production"] = Field(
        default="development", description="Runtime environment"
    )
    port: int = Field(default=8011, description="Service listen port")
    service_name: str = Field(default="llm-svc", description="Service name for logging/tracing")

    # LLM provider selection
    llm_provider: Literal["openai", "anthropic", "wenxin"] = Field(
        default="openai",
        description="Primary LLM provider: openai | anthropic | wenxin",
    )

    # OpenAI settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o", description="OpenAI model identifier")

    # Anthropic settings
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-opus-4-6", description="Anthropic model identifier"
    )

    # Wenxin (Baidu ERNIE) settings
    wenxin_api_key: Optional[str] = Field(default=None, description="Baidu Wenxin API key")
    wenxin_secret_key: Optional[str] = Field(
        default=None, description="Baidu Wenxin secret key"
    )
    wenxin_model_url: str = Field(
        default=(
            "https://aip.baidubce.com/rpc/2.0/ai_custom/v1"
            "/wenxinworkshop/chat/completions_pro"
        ),
        description="Wenxin ERNIE-Bot Pro endpoint",
    )
    wenxin_token_url: str = Field(
        default="https://aip.baidubce.com/oauth/2.0/token",
        description="Wenxin OAuth token endpoint",
    )

    # Request settings
    request_timeout: int = Field(default=60, description="LLM API call timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts per request")

    # CORS
    cors_origins: list[str] = Field(default=["*"], description="Allowed CORS origins")

    # ---------------------------------------------------------------------------
    # Derived helpers (not loaded from env)
    # ---------------------------------------------------------------------------

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def openai_available(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def anthropic_available(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def wenxin_available(self) -> bool:
        return bool(self.wenxin_api_key and self.wenxin_secret_key)


settings = Settings()
