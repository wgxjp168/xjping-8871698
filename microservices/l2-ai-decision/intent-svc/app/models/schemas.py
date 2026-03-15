"""
Pydantic schemas for ILbuy Intent Service API.
Defines request/response models for intent recognition, entity extraction,
and brand detection endpoints.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class IntentEnum(str, Enum):
    """Exhaustive list of user-intent categories for ILbuy e-commerce."""

    PURCHASE_INQUIRY = "PURCHASE_INQUIRY"       # 购买咨询
    PRICE_QUERY = "PRICE_QUERY"                 # 价格查询
    SPEC_QUERY = "SPEC_QUERY"                   # 规格查询
    COMPARISON = "COMPARISON"                   # 商品对比
    RECOMMENDATION = "RECOMMENDATION"           # 推荐请求
    COMPLAINT = "COMPLAINT"                     # 投诉
    AFTER_SALES = "AFTER_SALES"                 # 售后服务
    LOGISTICS = "LOGISTICS"                     # 物流查询
    RETURN = "RETURN"                           # 退货
    EXCHANGE = "EXCHANGE"                       # 换货
    BUDGET_INQUIRY = "BUDGET_INQUIRY"           # 预算咨询
    BRAND_QUERY = "BRAND_QUERY"                 # 品牌查询
    CATEGORY_BROWSE = "CATEGORY_BROWSE"         # 分类浏览
    CUSTOM_ORDER = "CUSTOM_ORDER"               # 定制订单
    OTHER = "OTHER"                             # 其他


class BrandStatusEnum(str, Enum):
    """Classification of how well the user has identified their desired brand."""

    KNOWN = "KNOWN"       # User clearly specified a brand and/or model
    UNKNOWN = "UNKNOWN"   # User has no brand preference
    PARTIAL = "PARTIAL"   # Brand mentioned but model is unspecified


# ---------------------------------------------------------------------------
# Intent Recognition
# ---------------------------------------------------------------------------


class IntentRecognizeRequest(BaseModel):
    """Request body for POST /intent/recognize."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User input text in Chinese (or mixed language).",
        examples=["我想买一台小米手机，预算3000元以内"],
    )
    context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional conversation context (e.g., previous intents, product category).",
    )
    session_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Optional session identifier for multi-turn conversation tracking.",
    )


class SubIntentScore(BaseModel):
    """A secondary intent candidate with its confidence score."""

    intent: IntentEnum
    confidence: float = Field(ge=0.0, le=1.0)


class IntentRecognizeResponse(BaseModel):
    """Response body for POST /intent/recognize."""

    intent: IntentEnum = Field(..., description="Primary detected intent.")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score [0, 1].")
    sub_intents: list[SubIntentScore] = Field(
        default_factory=list,
        description="Up to 3 secondary intent candidates sorted by descending confidence.",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Echoed session_id from the request.",
    )


# ---------------------------------------------------------------------------
# Entity Extraction
# ---------------------------------------------------------------------------


class EntityExtractRequest(BaseModel):
    """Request body for POST /entity/extract."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User input text to extract entities from.",
        examples=["我要买小米13 Pro 8+256，预算5000元以内"],
    )
    intent: Optional[str] = Field(
        default=None,
        description="Detected intent (used to guide entity extraction heuristics).",
    )


class ExtractedEntities(BaseModel):
    """Structured product/shopping entities parsed from user text."""

    brand: Optional[str] = Field(default=None, description="Brand name, e.g. 小米, 华为")
    model: Optional[str] = Field(default=None, description="Product model, e.g. Mate60 Pro")
    budget_min: Optional[float] = Field(default=None, description="Minimum budget in CNY (¥)")
    budget_max: Optional[float] = Field(default=None, description="Maximum budget in CNY (¥)")
    category: Optional[str] = Field(default=None, description="Product category, e.g. 手机, 电视")
    specs: Optional[dict[str, Any]] = Field(
        default=None,
        description="Key product specifications, e.g. {ram: '8GB', storage: '256GB'}",
    )
    quantity: Optional[int] = Field(default=None, description="Requested quantity")
    delivery_time: Optional[str] = Field(
        default=None,
        description="Requested delivery time, e.g. '明天', '3天内'",
    )


class RawEntity(BaseModel):
    """Raw entity span before normalisation."""

    entity_type: str
    value: str
    start: int
    end: int
    confidence: float = Field(ge=0.0, le=1.0)


class EntityExtractResponse(BaseModel):
    """Response body for POST /entity/extract."""

    entities: ExtractedEntities = Field(..., description="Structured entity values.")
    raw_entities: list[RawEntity] = Field(
        default_factory=list,
        description="All raw entity spans detected, including overlaps.",
    )


# ---------------------------------------------------------------------------
# Brand Detection
# ---------------------------------------------------------------------------


class BrandDetectRequest(BaseModel):
    """Request body for POST /brand/detect."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User input text.",
        examples=["我要买华为Mate60 Pro"],
    )
    entities: dict[str, Any] = Field(
        default_factory=dict,
        description="Pre-extracted entities (output of /entity/extract).",
    )


class BrandDetectResponse(BaseModel):
    """Response body for POST /brand/detect."""

    brand_status: BrandStatusEnum = Field(
        ...,
        description="Whether the user's brand preference is KNOWN, UNKNOWN, or PARTIAL.",
    )
    brand_name: Optional[str] = Field(
        default=None,
        description="Detected brand name when status is KNOWN or PARTIAL.",
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence [0, 1].")
    reasoning: str = Field(
        ...,
        description="Human-readable explanation of how the status was determined.",
    )
