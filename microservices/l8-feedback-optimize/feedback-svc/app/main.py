import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from app.config import get_settings
from app.db.database import create_tables
from app.services import mq_service
from app.routers import feedback, health
from app.consumers.delivery_consumer import start_consumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting feedback-svc...")
    await create_tables()
    await mq_service.connect()
    consumer_task = asyncio.create_task(start_consumer())
    yield
    # Shutdown
    consumer_task.cancel()
    await mq_service.disconnect()
    logger.info("feedback-svc stopped")


app = FastAPI(
    title="ILbuy Feedback Service",
    description="L8 user feedback collection with NLP sentiment analysis",
    version="1.0.0",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app, endpoint="/actuator/prometheus")

app.include_router(health.router)
app.include_router(feedback.router)


@app.get("/")
async def root():
    return {"service": settings.app_name, "port": settings.port, "status": "running"}
