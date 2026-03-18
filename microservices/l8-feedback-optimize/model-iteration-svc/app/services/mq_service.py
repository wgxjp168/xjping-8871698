import json
import logging
import aio_pika
from aio_pika import ExchangeType
from typing import Optional
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_connection: Optional[aio_pika.RobustConnection] = None
_channel: Optional[aio_pika.Channel] = None
_exchange: Optional[aio_pika.Exchange] = None


async def connect():
    global _connection, _channel, _exchange
    try:
        _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        _channel = await _connection.channel()
        _exchange = await _channel.declare_exchange(
            settings.rabbitmq_exchange, ExchangeType.TOPIC, durable=True
        )
        logger.info("RabbitMQ producer connected")
    except Exception as e:
        logger.warning(f"RabbitMQ connect failed (stub mode): {e}")


async def disconnect():
    global _connection
    if _connection and not _connection.is_closed:
        await _connection.close()
        logger.info("RabbitMQ connection closed")


async def publish(routing_key: str, payload: dict):
    global _exchange
    if _exchange is None:
        logger.warning(f"MQ not connected, skipping publish to {routing_key}: {payload}")
        return
    try:
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await _exchange.publish(message, routing_key=routing_key)
        logger.info(f"Published to {routing_key}: {list(payload.keys())}")
    except Exception as e:
        logger.error(f"Publish error to {routing_key}: {e}", exc_info=True)
