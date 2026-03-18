import json
import logging
import aio_pika
from aio_pika import ExchangeType
from app.config import get_settings
from typing import Any

logger = logging.getLogger(__name__)
settings = get_settings()

_connection: aio_pika.abc.AbstractConnection | None = None
_channel: aio_pika.abc.AbstractChannel | None = None
_exchange: aio_pika.abc.AbstractExchange | None = None


async def connect():
    global _connection, _channel, _exchange
    _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    _channel = await _connection.channel()
    _exchange = await _channel.declare_exchange(
        settings.rabbitmq_exchange, ExchangeType.TOPIC, durable=True
    )
    logger.info("RabbitMQ connected, exchange=%s", settings.rabbitmq_exchange)


async def disconnect():
    if _connection:
        await _connection.close()


async def publish(routing_key: str, payload: dict[str, Any]):
    if _exchange is None:
        logger.warning("MQ not connected, skipping publish routing_key=%s", routing_key)
        return
    body = json.dumps(payload, default=str).encode()
    await _exchange.publish(
        aio_pika.Message(body=body, content_type="application/json", delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=routing_key,
    )
    logger.debug("Published to %s: %s", routing_key, routing_key)


async def get_exchange() -> aio_pika.abc.AbstractExchange | None:
    return _exchange


async def get_channel() -> aio_pika.abc.AbstractChannel | None:
    return _channel
