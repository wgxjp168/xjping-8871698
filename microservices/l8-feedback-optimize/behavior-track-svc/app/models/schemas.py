from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    CLICK = "CLICK"
    PAGE_VIEW = "PAGE_VIEW"
    REPORT_VIEW = "REPORT_VIEW"
    REPORT_DOWNLOAD = "REPORT_DOWNLOAD"
    REPORT_SHARE = "REPORT_SHARE"
    CONVERSION = "CONVERSION"
    SATISFACTION_SIGNAL = "SATISFACTION_SIGNAL"  # implicit: scroll depth, time-on-page
    SEARCH = "SEARCH"
    RECOMMENDATION_CLICK = "RECOMMENDATION_CLICK"

class TrackEventRequest(BaseModel):
    event_type: EventType
    user_id: str
    session_id: str
    channel: str
    report_id: Optional[str] = None
    item_id: Optional[str] = None
    page_url: Optional[str] = None
    extra: Optional[dict] = None  # e.g., scroll_depth, time_on_page
    event_time: Optional[str] = None  # ISO8601, defaults to server time

class BatchTrackRequest(BaseModel):
    events: List[TrackEventRequest] = Field(..., min_length=1, max_length=500)

class TrackEventResponse(BaseModel):
    event_id: str
    status: str = "ACCEPTED"

class FunnelMetrics(BaseModel):
    report_id: str
    view_count: int
    detail_count: int
    cart_count: int
    purchase_count: int
    conversion_rate: float

class BehaviorAggregatedEvent(BaseModel):
    """Outgoing event to model-iteration-svc"""
    aggregation_id: str
    period_start: str
    period_end: str
    total_events: int
    unique_users: int
    avg_session_duration: float
    conversion_rate: float
    avg_satisfaction: Optional[float]
    top_report_ids: List[str]
    feature_summary: dict  # summary for feature engineering
