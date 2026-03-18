import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.models.events import UserSession, ConversionFunnel
from app.models.schemas import (
    TrackEventRequest, BatchTrackRequest, TrackEventResponse, FunnelMetrics
)
from app.services import tracker_service
from app.services import clickhouse_service
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/track", tags=["behavior-tracking"])


@router.post("/event", response_model=TrackEventResponse, status_code=202)
async def track_event(event: TrackEventRequest, db: AsyncSession = Depends(get_db)):
    """Track a single user behavior event."""
    event_id = await tracker_service.track_event(event, db)
    return TrackEventResponse(event_id=event_id)


@router.post("/batch", status_code=202)
async def track_batch(body: BatchTrackRequest, db: AsyncSession = Depends(get_db)):
    """Batch track up to 500 events."""
    inserted = await tracker_service.track_batch(body.events, db)
    return {"status": "ACCEPTED", "inserted": inserted, "total": len(body.events)}


@router.get("/funnel/{report_id}", response_model=FunnelMetrics)
async def get_funnel(report_id: str, db: AsyncSession = Depends(get_db)):
    """Get conversion funnel metrics for a report."""
    result = await db.execute(
        select(ConversionFunnel.stage, func.count().label("cnt"))
        .where(ConversionFunnel.report_id == report_id)
        .group_by(ConversionFunnel.stage)
    )
    counts = {row.stage: row.cnt for row in result}

    view = counts.get("VIEW", 0)
    detail = counts.get("DETAIL", 0)
    cart = counts.get("CART", 0)
    purchase = counts.get("PURCHASE", 0)
    conversion_rate = purchase / view if view > 0 else 0.0

    return FunnelMetrics(
        report_id=report_id,
        view_count=view,
        detail_count=detail,
        cart_count=cart,
        purchase_count=purchase,
        conversion_rate=round(conversion_rate, 4),
    )


@router.get("/session/{user_id}")
async def get_user_sessions(
    user_id: str,
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get recent session metrics for a user."""
    result = await db.execute(
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .order_by(UserSession.created_at.desc())
        .limit(limit)
    )
    sessions = list(result.scalars().all())
    return [
        {
            "session_id": s.session_id,
            "channel": s.channel,
            "page_views": s.page_views,
            "clicks": s.clicks,
            "report_views": s.report_views,
            "conversions": s.conversions,
            "total_time_seconds": s.total_time_seconds,
            "started_at": s.started_at.isoformat() if s.started_at else None,
        }
        for s in sessions
    ]


@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """Get aggregate tracking metrics from PostgreSQL."""
    total_sessions = await db.scalar(select(func.count()).select_from(UserSession))
    total_conversions = await db.scalar(
        select(func.sum(UserSession.conversions)).select_from(UserSession)
    )
    total_report_views = await db.scalar(
        select(func.sum(UserSession.report_views)).select_from(UserSession)
    )
    return {
        "total_sessions": total_sessions or 0,
        "total_conversions": total_conversions or 0,
        "total_report_views": total_report_views or 0,
    }
