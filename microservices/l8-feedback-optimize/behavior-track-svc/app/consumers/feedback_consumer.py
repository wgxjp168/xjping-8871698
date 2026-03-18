import json
import logging
import asyncio
from datetime import datetime, timedelta
import aio_pika
from aio_pika import ExchangeType
from sqlalchemy import select, func
from app.config import get_settings
from app.models.schemas import BehaviorAggregatedEvent
from app.services import clickhouse_service, mq_service
from app.db.database import AsyncSessionLocal
from app.models.events import UserSession, ConversionFunnel
from app.services.tracker_service import track_event
from app.models.schemas import TrackEventRequest, EventType
import uuid

logger = logging.getLogger(__name__)
settings = get_settings()


async def start_consumer():
    """Consume l8.feedback.collected and enrich behavior tracking."""
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=20)

        exchange = await channel.declare_exchange(
            settings.rabbitmq_exchange, ExchangeType.TOPIC, durable=True
        )
        queue = await channel.declare_queue(settings.rabbitmq_input_queue, durable=True)
        await queue.bind(exchange, routing_key=settings.rabbitmq_input_routing_key)

        logger.info("Behavior consumer started, listening for l8.feedback.collected")

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        payload = json.loads(message.body)
                        await _process_feedback_event(payload)
                    except Exception as e:
                        logger.error(f"Error processing feedback event: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Consumer error: {e}", exc_info=True)
        await asyncio.sleep(5)
        asyncio.create_task(start_consumer())


async def _process_feedback_event(payload: dict):
    """Convert feedback event into a behavior tracking event."""
    async with AsyncSessionLocal() as db:
        track_req = TrackEventRequest(
            event_type=EventType.SATISFACTION_SIGNAL,
            user_id=payload.get("user_id", ""),
            session_id=f"feedback-{payload.get('feedback_id', uuid.uuid4())}",
            channel=payload.get("channel", "UNKNOWN"),
            report_id=payload.get("report_id"),
            extra={
                "rating": payload.get("rating"),
                "sentiment_score": payload.get("sentiment_score"),
                "sentiment_label": payload.get("sentiment_label"),
                "source": "feedback",
            },
        )
        await track_event(track_req, db)


async def _compute_session_metrics(period_start: datetime, period_end: datetime) -> dict:
    """Compute avg_session_duration and conversion_rate from PostgreSQL for the period."""
    async with AsyncSessionLocal() as db:
        # avg session duration: sessions that ended within the period
        avg_result = await db.execute(
            select(func.avg(UserSession.total_time_seconds)).where(
                UserSession.started_at >= period_start,
                UserSession.started_at < period_end,
            )
        )
        avg_duration = avg_result.scalar_one_or_none() or 0.0

        # conversion_rate = sessions with >=1 conversion / total sessions in period
        total_sessions = await db.scalar(
            select(func.count()).select_from(UserSession).where(
                UserSession.started_at >= period_start,
                UserSession.started_at < period_end,
            )
        ) or 0
        converted_sessions = await db.scalar(
            select(func.count()).select_from(UserSession).where(
                UserSession.started_at >= period_start,
                UserSession.started_at < period_end,
                UserSession.conversions > 0,
            )
        ) or 0
        conversion_rate = converted_sessions / total_sessions if total_sessions > 0 else 0.0

        # avg_satisfaction: mean of satisfaction signals stored as extra in ClickHouse
        # (approximated here via conversion proxy; ClickHouse is the authoritative source)
        return {
            "avg_session_duration": round(float(avg_duration), 2),
            "conversion_rate": round(conversion_rate, 4),
        }


async def run_aggregation_job():
    """Periodically aggregate behavior data and publish to model-iteration-svc."""
    import uuid as uuid_module

    while True:
        await asyncio.sleep(settings.aggregation_interval_minutes * 60)
        try:
            now = datetime.utcnow()
            period_start = now - timedelta(minutes=settings.aggregation_interval_minutes)

            summary = clickhouse_service.aggregate_behavior_summary(period_start, now)
            session_metrics = await _compute_session_metrics(period_start, now)

            event = BehaviorAggregatedEvent(
                aggregation_id=str(uuid_module.uuid4()),
                period_start=period_start.isoformat(),
                period_end=now.isoformat(),
                total_events=summary.get("total_events", 0),
                unique_users=summary.get("unique_users", 0),
                avg_session_duration=session_metrics["avg_session_duration"],
                conversion_rate=session_metrics["conversion_rate"],
                avg_satisfaction=None,
                top_report_ids=summary.get("top_reports", []),
                feature_summary={**summary, **session_metrics},
            )

            await mq_service.publish(settings.rabbitmq_output_routing_key, event.model_dump())
            logger.info(
                "Published behavior aggregation: events=%s conversion_rate=%.4f",
                summary.get("total_events"),
                session_metrics["conversion_rate"],
            )
        except Exception as e:
            logger.error(f"Aggregation job error: {e}", exc_info=True)
