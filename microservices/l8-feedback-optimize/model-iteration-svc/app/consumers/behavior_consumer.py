import json
import logging
import asyncio
import aio_pika
from aio_pika import ExchangeType
from app.config import get_settings
from app.db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)
settings = get_settings()

# Accumulated samples buffer between training runs
_sample_buffer: list[dict] = []


async def start_consumer():
    """Consume l8.behavior.aggregated messages and trigger training when ready."""
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        exchange = await channel.declare_exchange(
            settings.rabbitmq_exchange, ExchangeType.TOPIC, durable=True
        )
        queue = await channel.declare_queue(settings.rabbitmq_input_queue, durable=True)
        await queue.bind(exchange, routing_key=settings.rabbitmq_input_routing_key)

        logger.info(
            "Behavior consumer started, listening on %s",
            settings.rabbitmq_input_routing_key,
        )

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        payload = json.loads(message.body)
                        await _process_aggregated_event(payload)
                    except Exception as e:
                        logger.error(
                            "Error processing behavior aggregated event: %s", e, exc_info=True
                        )
    except asyncio.CancelledError:
        logger.info("Behavior consumer cancelled")
    except Exception as e:
        logger.error("Consumer error: %s", e, exc_info=True)
        await asyncio.sleep(5)
        asyncio.create_task(start_consumer())


async def _process_aggregated_event(payload: dict):
    """Process an l8.behavior.aggregated event.

    Appends the aggregated row to the in-memory sample buffer and triggers
    model training once we have enough samples.
    """
    global _sample_buffer

    # Map aggregation payload to feature vector expected by the trainer
    sample = {
        "conversion_rate": payload.get("conversion_rate", 0.0),
        "avg_satisfaction": payload.get("avg_satisfaction") or 0.0,
        "click_count": payload.get("total_events", 0),
        "view_count": payload.get("unique_users", 0),
        "session_duration": payload.get("avg_session_duration", 0.0),
        "label": 1 if (payload.get("conversion_rate") or 0.0) >= 0.05 else 0,
    }
    _sample_buffer.append(sample)

    logger.debug(
        "Buffer size: %d / %d", len(_sample_buffer), settings.min_training_samples
    )

    if len(_sample_buffer) >= settings.min_training_samples:
        samples_snapshot = list(_sample_buffer)
        _sample_buffer = []

        logger.info(
            "Threshold reached (%d samples), triggering model training",
            len(samples_snapshot),
        )
        async with AsyncSessionLocal() as db:
            from app.services.training_service import trigger_training

            try:
                await trigger_training(db, trigger_reason="AUTO", samples=samples_snapshot)
            except Exception as exc:
                logger.error("Auto-triggered training failed: %s", exc, exc_info=True)
