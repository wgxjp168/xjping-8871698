import json
import logging
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.events import UserSession, ConversionFunnel
from app.models.schemas import TrackEventRequest, EventType
from app.services import clickhouse_service

logger = logging.getLogger(__name__)


async def track_event(event: TrackEventRequest, db: AsyncSession) -> str:
    """Process and persist a single tracking event."""
    event_time = (
        datetime.fromisoformat(event.event_time.replace("Z", "+00:00"))
        if event.event_time
        else datetime.utcnow()
    )

    # Write to ClickHouse (L4)
    event_id = clickhouse_service.insert_event(
        event_type=event.event_type.value,
        user_id=event.user_id,
        session_id=event.session_id,
        channel=event.channel,
        report_id=event.report_id or "",
        item_id=event.item_id or "",
        page_url=event.page_url or "",
        extra=json.dumps(event.extra or {}),
        event_time=event_time,
    )

    # Update session counters in PostgreSQL
    await _update_session(event, db, event_time)

    # Track conversion funnel if applicable
    if event.event_type == EventType.REPORT_VIEW and event.report_id:
        await _upsert_funnel(event.user_id, event.report_id, "VIEW", event.channel, db)
    elif event.event_type == EventType.CONVERSION and event.report_id:
        await _upsert_funnel(event.user_id, event.report_id, "PURCHASE", event.channel, db, converted=True)
    elif event.event_type == EventType.RECOMMENDATION_CLICK and event.report_id:
        await _upsert_funnel(event.user_id, event.report_id, "DETAIL", event.channel, db)

    return event_id


async def track_batch(events: list[TrackEventRequest], db: AsyncSession) -> int:
    """Batch track events — write to ClickHouse in bulk, update PostgreSQL sessions per event."""
    rows = []
    for event in events:
        event_time = (
            datetime.fromisoformat(event.event_time.replace("Z", "+00:00"))
            if event.event_time
            else datetime.utcnow()
        )
        rows.append({
            "event_type": event.event_type.value,
            "user_id": event.user_id,
            "session_id": event.session_id,
            "channel": event.channel,
            "report_id": event.report_id or "",
            "item_id": event.item_id or "",
            "page_url": event.page_url or "",
            "extra": json.dumps(event.extra or {}),
            "event_time": event_time,
        })
        # Keep PostgreSQL session counters and conversion funnels in sync
        await _update_session(event, db, event_time)
        if event.event_type == EventType.REPORT_VIEW and event.report_id:
            await _upsert_funnel(event.user_id, event.report_id, "VIEW", event.channel, db)
        elif event.event_type == EventType.CONVERSION and event.report_id:
            await _upsert_funnel(event.user_id, event.report_id, "PURCHASE", event.channel, db, converted=True)
        elif event.event_type == EventType.RECOMMENDATION_CLICK and event.report_id:
            await _upsert_funnel(event.user_id, event.report_id, "DETAIL", event.channel, db)

    inserted = clickhouse_service.insert_batch(rows)
    return inserted


async def _update_session(event: TrackEventRequest, db: AsyncSession, event_time: datetime):
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == event.user_id,
            UserSession.session_id == event.session_id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        session = UserSession(
            user_id=event.user_id,
            session_id=event.session_id,
            channel=event.channel,
            started_at=event_time,
            clicks=0,
            page_views=0,
            report_views=0,
            conversions=0,
            total_time_seconds=0,
        )
        db.add(session)

    if event.event_type == EventType.CLICK:
        session.clicks += 1
    elif event.event_type == EventType.PAGE_VIEW:
        session.page_views += 1
    elif event.event_type == EventType.REPORT_VIEW:
        session.report_views += 1
    elif event.event_type == EventType.CONVERSION:
        session.conversions += 1

    if event.extra and "time_on_page" in event.extra:
        session.total_time_seconds += int(event.extra["time_on_page"])

    session.ended_at = event_time
    await db.commit()


async def _upsert_funnel(
    user_id: str, report_id: str, stage: str, channel: str,
    db: AsyncSession, converted: bool = False
):
    result = await db.execute(
        select(ConversionFunnel).where(
            ConversionFunnel.user_id == user_id,
            ConversionFunnel.report_id == report_id,
            ConversionFunnel.stage == stage,
        )
    )
    funnel = result.scalar_one_or_none()
    if not funnel:
        funnel = ConversionFunnel(
            user_id=user_id,
            report_id=report_id,
            stage=stage,
            channel=channel,
            converted=converted,
        )
        db.add(funnel)
    else:
        funnel.converted = converted
    await db.commit()
