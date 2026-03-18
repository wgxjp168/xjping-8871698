import asyncio
import json
import logging
from datetime import datetime
import aio_pika
from aio_pika import ExchangeType
from app.config import get_settings
from app.db.database import AsyncSessionLocal
from app.services import deploy_service
from app.models.schemas import DeploymentRequest

logger = logging.getLogger(__name__)
settings = get_settings()


async def start_consumer():
    """Consume l8.model.ready messages and auto-trigger deployment."""
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=5)

        exchange = await channel.declare_exchange(
            settings.rabbitmq_exchange, ExchangeType.TOPIC, durable=True
        )
        queue = await channel.declare_queue(settings.rabbitmq_input_queue, durable=True)
        await queue.bind(exchange, routing_key=settings.rabbitmq_input_routing_key)

        logger.info("model-ready consumer started, listening on %s", settings.rabbitmq_input_routing_key)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        payload = json.loads(message.body)
                        await _process_model_ready_event(payload)
                    except Exception as exc:
                        logger.error("Error processing l8.model.ready message: %s", exc, exc_info=True)

    except asyncio.CancelledError:
        logger.info("model-ready consumer cancelled")
    except Exception as exc:
        logger.error("model-ready consumer connection failed, retrying in 5s: %s", exc)
        await asyncio.sleep(5)
        asyncio.create_task(start_consumer())


async def _process_model_ready_event(payload: dict):
    """Parse ModelReadyEvent and auto-trigger deployment."""
    model_version_id = payload.get("model_version_id", "")
    version_tag = payload.get("version_tag", "")
    artifact_path = payload.get("artifact_path", "")
    auc_roc = payload.get("auc_roc")
    f1_score = payload.get("f1_score")
    approved_at = payload.get("approved_at", datetime.utcnow().isoformat())

    logger.info(
        "Received l8.model.ready: version=%s auc_roc=%s f1_score=%s approved_at=%s",
        version_tag, auc_roc, f1_score, approved_at,
    )

    req = DeploymentRequest(
        model_version_id=model_version_id,
        version_tag=version_tag,
        artifact_path=artifact_path,
        deployment_strategy="BLUE_GREEN",
    )

    async with AsyncSessionLocal() as db:
        deployment = await deploy_service.create_deployment(db, req)
        result = await deploy_service.execute_deployment(db, deployment.id)
        if result and result.status == "ACTIVE":
            logger.info(
                "Auto-deployment succeeded: id=%s version=%s",
                result.id, result.version_tag,
            )
        else:
            status = result.status if result else "unknown"
            logger.error(
                "Auto-deployment failed: id=%s version=%s status=%s",
                result.id if result else "N/A", version_tag, status,
            )
