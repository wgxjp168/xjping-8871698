from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class Channel(str, Enum):
    WECHAT = "WECHAT"
    ALIPAY = "ALIPAY"
    WEB = "WEB"
    APP = "APP"

class SentimentLabel(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"

class FeedbackCreate(BaseModel):
    report_id: str
    user_id: str
    order_id: Optional[str] = None
    channel: Channel
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = None
    source: str = "USER_SUBMIT"

    @field_validator("rating")
    @classmethod
    def rating_in_range(cls, v):
        if not 1 <= v <= 5:
            raise ValueError("Rating must be between 1 and 5")
        return v

class FeedbackResponse(BaseModel):
    id: str
    report_id: str
    user_id: str
    order_id: Optional[str]
    channel: str
    rating: int
    comment: Optional[str]
    tags: Optional[str]
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}

class FeedbackAnalytics(BaseModel):
    total_count: int
    avg_rating: float
    positive_rate: float
    neutral_rate: float
    negative_rate: float
    rating_distribution: dict  # {1: count, 2: count, ...}

class DeliveryEvent(BaseModel):
    """Incoming event from L6 delivery-svc"""
    report_id: str
    user_id: str
    order_id: Optional[str] = None
    channel: str
    delivery_time: str  # ISO8601
    delivery_status: str  # DELIVERED/FAILED

class FeedbackCollectedEvent(BaseModel):
    """Outgoing event to behavior-track-svc"""
    feedback_id: str
    report_id: str
    user_id: str
    rating: int
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    channel: str
    created_at: str
