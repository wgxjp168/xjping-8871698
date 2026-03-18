import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.config import get_settings
from app.db.database import create_tables
from app.services import mq_service
from app.routers import health, deployments
from app.consumers.model_ready_consumer import start_consumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting model-deploy-svc on port %s...", settings.port)
    await create_tables()
    try:
        await mq_service.connect()
    except Exception as exc:
        logger.warning("RabbitMQ connect failed at startup (stub mode): %s", exc)

    consumer_task = asyncio.create_task(start_consumer())
    yield
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await mq_service.disconnect()
    logger.info("model-deploy-svc stopped")


app = FastAPI(
    title="ILbuy Model Deploy Service",
    description="L8 blue/green ML model deployment with rollback",
    version="1.0.0",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app, endpoint="/actuator/prometheus")

app.include_router(health.router)
app.include_router(deployments.router)


@app.get("/")
async def root():
    return {"service": settings.app_name, "port": settings.port, "status": "running"}
