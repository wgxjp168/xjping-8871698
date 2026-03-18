import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.config import get_settings
from app.db.database import create_tables
from app.services import mq_service
from app.routers import health, models, experiments
from app.consumers.behavior_consumer import start_consumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting model-iteration-svc...")
    await create_tables()
    await mq_service.connect()
    consumer_task = asyncio.create_task(start_consumer())
    yield
    consumer_task.cancel()
    await mq_service.disconnect()
    logger.info("model-iteration-svc stopped")


app = FastAPI(
    title="ILbuy Model Iteration Service",
    description="L8 XGBoost model training, evaluation and A/B experiment management",
    version="1.0.0",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app, endpoint="/actuator/prometheus")

app.include_router(health.router)
app.include_router(models.router)
app.include_router(experiments.router)


@app.get("/")
async def root():
    return {"service": settings.app_name, "port": settings.port, "status": "running"}
