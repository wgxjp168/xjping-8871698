import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.config import get_settings
from app.db.database import create_tables
from app.services import mq_service
from app.routers import track, health
from app.consumers.feedback_consumer import start_consumer, run_aggregation_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting behavior-track-svc...")
    await create_tables()
    await mq_service.connect()
    consumer_task = asyncio.create_task(start_consumer())
    agg_task = asyncio.create_task(run_aggregation_job())
    yield
    consumer_task.cancel()
    agg_task.cancel()
    await mq_service.disconnect()
    logger.info("behavior-track-svc stopped")


app = FastAPI(
    title="ILbuy Behavior Tracking Service",
    description="L8 user behavior tracking with ClickHouse analytics",
    version="1.0.0",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app, endpoint="/actuator/prometheus")

app.include_router(health.router)
app.include_router(track.router)


@app.get("/")
async def root():
    return {"service": settings.app_name, "port": settings.port, "status": "running"}
