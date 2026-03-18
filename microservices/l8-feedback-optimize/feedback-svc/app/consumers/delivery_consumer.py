import json
import logging
import asyncio
import aio_pika
from aio_pika import ExchangeType
from app.config import get_settings
from app.models.schemas import DeliveryEvent
from app.services.followup_service import schedule_followup
from app.db.database import AsyncSessionLocal

logger = logging.getLogger(__name__)
settings = get_settings()


async def start_consumer():
    """Consume l6.delivery.completed events and schedule follow-up surveys."""
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=10)

        # Declare exchange (L6 publishes here)
        exchange = await channel.declare_exchange("ilbuy.l6", ExchangeType.TOPIC, durable=True)

        # Declare and bind our queue
        queue = await channel.declare_queue(settings.rabbitmq_input_queue, durable=True)
        await queue.bind(exchange, routing_key=settings.rabbitmq_input_routing_key)

        logger.info("Consumer started, waiting for l6.delivery.completed events")

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        payload = json.loads(message.body)
                        event = DeliveryEvent(**payload)
                        
                        if event.delivery_status != "DELIVERED":
                            logger.debug(f"Skipping non-delivered event for report={event.report_id}")
                            continue

                        async with AsyncSessionLocal() as db:
                            await schedule_followup(event, db)

                    except Exception as e:
                        logger.error(f"Error processing delivery event: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Consumer connection error: {e}", exc_info=True)
        await asyncio.sleep(5)
        asyncio.create_task(start_consumer())  # reconnect
