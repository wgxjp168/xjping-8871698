"""
Pydantic schemas for etl-svc.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class ETLStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED  = "failed"


class Grade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


# ---------------------------------------------------------------------------
# Input: raw product from crawler-svc
# ---------------------------------------------------------------------------

class RawProduct(BaseModel):
    platform:         Platform
    product_id:       str
    title:            str
    price:            float            = 0.0
    original_price:   Optional[float]  = None
    brand:            Optional[str]    = None
    category:         Optional[str]    = None
    sub_category:     Optional[str]    = None
    images:           List[str]        = Field(default_factory=list)
    specs:            Dict[str, Any]   = Field(default_factory=dict)
    sales_count:      int              = 0
    review_count:     int              = 0
    average_rating:   float            = 0.0
    shop_name:        Optional[str]    = None
    shop_rating:      float            = 0.0
    in_stock:         bool             = True
    delivery_days:    Optional[int]    = None
    promotion:        bool             = False
    promotion_price:  Optional[float]  = None
    url:              Optional[str]    = None
    raw_data:         Dict[str, Any]   = Field(default_factory=dict)
    crawled_at:       Optional[datetime] = None
    session_id:       Optional[str]    = None
    job_id:           Optional[str]    = None


class ETLRequest(BaseModel):
    """Submitted by crawler-svc after collecting raw products."""
    job_id:          str
    session_id:      str
    raw_products:    List[RawProduct]
    deduplicate:     bool = True
    normalize:       bool = True
    compute_scores:  bool = True
    l4_ingest_url:   Optional[str] = None   # L4 data-store endpoint


# ---------------------------------------------------------------------------
# Output: cleaned + scored product
# ---------------------------------------------------------------------------

class ProductScore(BaseModel):
    """Pre-computed scoring dimensions for decision-svc consumption."""
    total_score:          float = Field(ge=0, le=100)
    grade:                Grade
    price_score:          float = Field(ge=0, le=100)
    popularity_score:     float = Field(ge=0, le=100)
    rating_score:         float = Field(ge=0, le=100)
    availability_score:   float = Field(ge=0, le=100)
    value_for_money_score: float = Field(ge=0, le=100)
    data_completeness:    float = Field(ge=0, le=1)
    computed_at:          datetime = Field(default_factory=datetime.utcnow)


class CleanProduct(BaseModel):
    """Processed, normalised, de-duplicated product record."""
    # Identity
    platform:         Platform
    product_id:       str
    canonical_id:     str               # platform:product_id
    dedupe_key:       str               # for cross-platform deduplication

    # Normalised fields
    title:            str
    title_cleaned:    str               # lowercased, punctuation removed
    price:            float
    original_price:   Optional[float]
    discount_pct:     Optional[float]   # (original-price)/original*100
    brand:            Optional[str]
    brand_normalised: Optional[str]     # lowercase, stripped
    category:         Optional[str]
    category_path:    List[str]         = Field(default_factory=list)
    specs:            Dict[str, str]    = Field(default_factory=dict)
    images:           List[str]

    # Quality metrics
    sales_count:      int
    review_count:     int
    average_rating:   float
    shop_name:        Optional[str]
    shop_rating:      float
    in_stock:         bool
    delivery_days:    Optional[int]
    promotion:        bool
    promotion_price:  Optional[float]
    url:              Optional[str]

    # Computed
    score:            ProductScore

    # Metadata
    crawled_at:       Optional[datetime]
    processed_at:     datetime = Field(default_factory=datetime.utcnow)
    session_id:       Optional[str]
    job_id:           Optional[str]
    is_mock:          bool = False


class ETLResult(BaseModel):
    job_id:              str
    session_id:          str
    status:              ETLStatus
    input_count:         int
    output_count:        int
    duplicate_count:     int
    invalid_count:       int
    products:            List[CleanProduct]
    l4_ingest_status:    Optional[str] = None
    processing_ms:       int
    processed_at:        datetime = Field(default_factory=datetime.utcnow)
    errors:              List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status:   str
    service:  str = "etl-svc"
    version:  str = "1.0.0"
    uptime_s: float


class ETLStats(BaseModel):
    total_processed:  int
    total_cleaned:    int
    total_duplicates: int
    total_invalid:    int
    avg_processing_ms: float
    uptime_s:         float
