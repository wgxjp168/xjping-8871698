import json
import logging
import asyncio
from datetime import datetime
import aio_pika
from aio_pika import ExchangeType
from app.config import get_settings
from app.models.schemas import BehaviorAggregatedEvent
from app.services import clickhouse_service, mq_service
from app.db.database import AsyncSessionLocal
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


async def run_aggregation_job():
    """Periodically aggregate behavior data and publish to model-iteration-svc."""
    from datetime import timedelta
    import uuid as uuid_module

    while True:
        await asyncio.sleep(settings.aggregation_interval_minutes * 60)
        try:
            now = datetime.utcnow()
            period_start = now - timedelta(minutes=settings.aggregation_interval_minutes)

            summary = clickhouse_service.aggregate_behavior_summary(period_start, now)

            event = BehaviorAggregatedEvent(
                aggregation_id=str(uuid_module.uuid4()),
                period_start=period_start.isoformat(),
                period_end=now.isoformat(),
                total_events=summary.get("total_events", 0),
                unique_users=summary.get("unique_users", 0),
                avg_session_duration=0.0,
                conversion_rate=0.0,
                avg_satisfaction=None,
                top_report_ids=summary.get("top_reports", []),
                feature_summary=summary,
            )

            await mq_service.publish(settings.rabbitmq_output_routing_key, event.model_dump())
            logger.info(f"Published behavior aggregation: events={summary.get('total_events')}")
        except Exception as e:
            logger.error(f"Aggregation job error: {e}", exc_info=True)
