import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.feedback import FollowUpSchedule
from app.models.schemas import DeliveryEvent
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def schedule_followup(event: DeliveryEvent, db: AsyncSession) -> FollowUpSchedule:
    """
    Schedule a follow-up survey 24h after delivery.
    Called when L6 delivery.completed event is received.
    """
    # Check if already scheduled
    result = await db.execute(
        select(FollowUpSchedule).where(
            FollowUpSchedule.report_id == event.report_id,
            FollowUpSchedule.user_id == event.user_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        logger.info(f"Follow-up already scheduled for report={event.report_id} user={event.user_id}")
        return existing

    delivery_time = datetime.fromisoformat(event.delivery_time.replace("Z", "+00:00"))
    scheduled_at = delivery_time + timedelta(hours=settings.followup_delay_hours)

    schedule = FollowUpSchedule(
        report_id=event.report_id,
        user_id=event.user_id,
        channel=event.channel,
        delivery_time=delivery_time,
        scheduled_at=scheduled_at,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    logger.info(f"Scheduled follow-up id={schedule.id} at={scheduled_at}")
    return schedule


async def get_due_followups(db: AsyncSession) -> list[FollowUpSchedule]:
    """Return unsent follow-ups that are due (scheduled_at <= now)."""
    now = datetime.utcnow()
    result = await db.execute(
        select(FollowUpSchedule).where(
            FollowUpSchedule.sent == False,
            FollowUpSchedule.scheduled_at <= now,
        )
    )
    return list(result.scalars().all())


async def mark_followup_sent(schedule: FollowUpSchedule, db: AsyncSession):
    schedule.sent = True
    schedule.sent_at = datetime.utcnow()
    db.add(schedule)
    await db.commit()
