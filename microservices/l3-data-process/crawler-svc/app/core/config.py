"""
Configuration — reads from environment variables with sensible defaults.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Service ──────────────────────────────────────────────────────────
    env:         str = "production"
    port:        int = 8030
    log_level:   str = "INFO"
    service_name: str = "crawler-svc"

    # ── Upstream / downstream URLs ────────────────────────────────────────
    etl_svc_url:      str = "http://etl-svc:8031"
    decision_svc_url: str = "http://decision-svc:8012"

    # ── Redis (proxy pool & job queue) ────────────────────────────────────
    redis_url:   str = "redis://redis:6379/2"
    redis_ttl_s: int = 3600

    # ── HTTP client ───────────────────────────────────────────────────────
    http_timeout_s:    float = 15.0
    http_max_retries:  int   = 3
    http_retry_delay_s: float = 2.0
    http_backoff_factor: float = 2.0

    # ── Rate limiting (requests per minute per platform) ──────────────────
    taobao_rpm:   int = 30
    jd_rpm:       int = 60
    ali1688_rpm:  int = 20
    pdd_rpm:      int = 40
    vipshop_rpm:  int = 30
    suning_rpm:   int = 30
    douyin_rpm:   int = 20

    # ── Proxy pool ────────────────────────────────────────────────────────
    proxy_enabled:         bool  = False
    proxy_pool_min_size:   int   = 5
    proxy_check_interval_s: int  = 300   # 5 minutes
    proxy_max_fail_count:  int   = 3
    proxy_timeout_s:       float = 10.0

    # ── Platform API keys (loaded from Secrets in production) ─────────────
    taobao_app_key:    str = ""
    taobao_app_secret: str = ""
    jd_app_key:        str = ""
    jd_app_secret:     str = ""
    ali1688_app_key:   str = ""
    ali1688_app_secret: str = ""
    pdd_client_id:     str = ""
    pdd_client_secret: str = ""
    vipshop_app_key:   str = ""
    suning_app_key:    str = ""
    douyin_app_key:    str = ""
    douyin_app_secret: str = ""

    # ── Compliance ────────────────────────────────────────────────────────
    robots_cache_ttl_s:  int  = 86400   # 24 h
    respect_crawl_delay: bool = True
    default_crawl_delay_s: float = 1.0

    # ── Scheduler ─────────────────────────────────────────────────────────
    scheduler_timezone: str = "Asia/Shanghai"
    default_cron_expr:  str = "0 */6 * * *"   # every 6 h

    # ── Job limits ────────────────────────────────────────────────────────
    max_concurrent_jobs: int = 10
    job_timeout_s:       int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()
