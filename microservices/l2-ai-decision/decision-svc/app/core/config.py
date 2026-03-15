"""
Configuration settings for the Decision Service.
Uses Pydantic Settings to load from environment variables or .env file.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application configuration loaded from environment."""

    env: str = Field(default="development", description="Deployment environment")
    port: int = Field(default=8012, description="Port to listen on")

    # Downstream service URLs
    intent_svc_url: str = Field(
        default="http://intent-svc:8011",
        description="Intent service base URL",
    )
    llm_svc_url: str = Field(
        default="http://llm-svc:8013",
        description="LLM service base URL",
    )
    l3_data_svc_url: str = Field(
        default="http://l3-data-svc:8031",
        description="L3 data service base URL",
    )
    l3_product_svc_url: str = Field(
        default="http://l3-product-svc:8032",
        description="L3 product service base URL",
    )

    # HTTP client timeouts (seconds)
    http_timeout: float = Field(default=5.0, description="HTTP client timeout")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")

    # Decision cache TTL (seconds)
    decision_cache_ttl: int = Field(default=3600, description="Decision cache TTL in seconds")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
