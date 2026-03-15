"""etl-svc configuration."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env:          str = "production"
    port:         int = 8031
    log_level:    str = "INFO"
    service_name: str = "etl-svc"

    # Downstream: L4 data storage (接口预留)
    l4_data_svc_url:    str = "http://l4-data-svc:8040"
    l4_ingest_enabled:  bool = False        # enable when L4 is available
    l4_ingest_timeout:  float = 10.0

    # Redis (deduplication cache)
    redis_url:     str = "redis://redis:6379/3"
    dedupe_ttl_s:  int = 86400              # 24 h

    # ETL limits
    max_batch_size:   int = 1000
    min_title_len:    int = 3
    min_price:        float = 0.01
    max_price:        float = 999999.0

    # Scoring weights (used by scorer.py)
    weight_price:         float = 0.25
    weight_popularity:    float = 0.25
    weight_rating:        float = 0.25
    weight_availability:  float = 0.15
    weight_value:         float = 0.10


@lru_cache
def get_settings() -> Settings:
    return Settings()
