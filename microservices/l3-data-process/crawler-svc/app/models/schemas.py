"""
Pydantic schemas shared across crawler-svc.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Platform(str, Enum):
    TAOBAO   = "taobao"
    JD       = "jd"
    ALI1688  = "1688"
    PDD      = "pinduoduo"
    VIPSHOP  = "vipshop"
    SUNING   = "suning"
    DOUYIN   = "douyin"


class CrawlPriority(str, Enum):
    HIGH   = "high"
    NORMAL = "normal"
    LOW    = "low"


class CrawlStatus(str, Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"


class ProxyStatus(str, Enum):
    ACTIVE  = "active"
    FAILED  = "failed"
    BANNED  = "banned"


# ---------------------------------------------------------------------------
# Crawl request / response (from L2 decision-svc)
# ---------------------------------------------------------------------------

class CrawlFilters(BaseModel):
    price_min:    Optional[float] = Field(default=None, ge=0)
    price_max:    Optional[float] = Field(default=None, ge=0)
    brand:        Optional[str]   = None
    category:     Optional[str]   = None
    min_rating:   Optional[float] = Field(default=None, ge=0, le=5)
    in_stock_only: bool           = False


class CrawlRequest(BaseModel):
    """Triggered by L2 decision-svc when it needs fresh product data."""
    session_id:               str
    keywords:                 List[str] = Field(min_length=1)
    platforms:                List[Platform] = Field(default_factory=lambda: list(Platform))
    max_results_per_platform: int         = Field(default=20, ge=1, le=100)
    filters:                  CrawlFilters = Field(default_factory=CrawlFilters)
    priority:                 CrawlPriority = CrawlPriority.NORMAL
    callback_url:             Optional[str] = None   # ETL endpoint to push results


class CrawlJobResponse(BaseModel):
    job_id:     str
    session_id: str
    status:     CrawlStatus
    message:    str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScheduledCrawlRequest(BaseModel):
    """For registering recurring crawl tasks."""
    name:       str
    cron_expr:  str = Field(description="Cron expression e.g. '0 */6 * * *'")
    keywords:   List[str]
    platforms:  List[Platform]
    filters:    CrawlFilters = Field(default_factory=CrawlFilters)
    max_results_per_platform: int = 50
    enabled:    bool = True


# ---------------------------------------------------------------------------
# Raw product (output from platform adapters)
# ---------------------------------------------------------------------------

class RawProduct(BaseModel):
    """Unprocessed product record as returned by platform API."""
    platform:         Platform
    product_id:       str
    title:            str
    price:            float           = Field(ge=0)
    original_price:   Optional[float] = Field(default=None, ge=0)
    brand:            Optional[str]   = None
    category:         Optional[str]   = None
    sub_category:     Optional[str]   = None
    images:           List[str]       = Field(default_factory=list)
    specs:            Dict[str, Any]  = Field(default_factory=dict)
    sales_count:      int             = Field(default=0, ge=0)
    review_count:     int             = Field(default=0, ge=0)
    average_rating:   float           = Field(default=0.0, ge=0, le=5)
    shop_name:        Optional[str]   = None
    shop_rating:      float           = Field(default=0.0, ge=0, le=5)
    in_stock:         bool            = True
    delivery_days:    Optional[int]   = None
    promotion:        bool            = False
    promotion_price:  Optional[float] = None
    url:              Optional[str]   = None
    raw_data:         Dict[str, Any]  = Field(default_factory=dict)
    crawled_at:       datetime        = Field(default_factory=datetime.utcnow)
    session_id:       Optional[str]   = None
    job_id:           Optional[str]   = None

    @field_validator("price", "original_price", "promotion_price", mode="before")
    @classmethod
    def coerce_price(cls, v):
        if v is None:
            return v
        try:
            return float(str(v).replace("¥", "").replace(",", "").strip())
        except (ValueError, TypeError):
            return 0.0


class CrawlResult(BaseModel):
    job_id:      str
    session_id:  str
    platform:    Platform
    keyword:     str
    products:    List[RawProduct]
    total_found: int
    success:     bool
    error:       Optional[str] = None
    duration_ms: int           = 0
    crawled_at:  datetime      = Field(default_factory=datetime.utcnow)


class CrawlBatchResult(BaseModel):
    job_id:       str
    session_id:   str
    results:      List[CrawlResult]
    total_products: int
    success_count: int
    fail_count:   int
    duration_ms:  int


# ---------------------------------------------------------------------------
# Proxy
# ---------------------------------------------------------------------------

class ProxyRecord(BaseModel):
    host:         str
    port:         int
    protocol:     str             = "http"
    username:     Optional[str]   = None
    password:     Optional[str]   = None
    status:       ProxyStatus     = ProxyStatus.ACTIVE
    success_count: int            = 0
    fail_count:   int             = 0
    last_used:    Optional[datetime] = None
    last_checked: Optional[datetime] = None
    latency_ms:   Optional[int]   = None

    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 1.0


# ---------------------------------------------------------------------------
# Health / info
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status:   str
    service:  str = "crawler-svc"
    version:  str = "1.0.0"
    uptime_s: float


class PlatformStatus(BaseModel):
    platform:          Platform
    enabled:           bool
    rate_limit_rpm:    int
    current_rpm:       float
    proxy_required:    bool
    compliance_status: str


class ServiceInfo(BaseModel):
    platforms:        List[PlatformStatus]
    proxy_pool_size:  int
    active_jobs:      int
    scheduled_tasks:  int
