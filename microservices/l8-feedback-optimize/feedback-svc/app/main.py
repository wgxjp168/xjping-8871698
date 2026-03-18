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
from app.services.followup_service import get_due_followups, mark_followup_sent
from app.db.database import AsyncSessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


async def _dispatch_followup_loop():
    """Every 30 min: find due follow-up schedules and publish reminder events."""
    while True:
        await asyncio.sleep(30 * 60)
        try:
            async with AsyncSessionLocal() as db:
                due = await get_due_followups(db)
                for schedule in due:
                    await mq_service.publish(
                        "l8.followup.due",
                        {
                            "schedule_id": schedule.id,
                            "report_id": schedule.report_id,
                            "user_id": schedule.user_id,
                            "channel": schedule.channel,
                            "scheduled_at": schedule.scheduled_at.isoformat(),
                        },
                    )
                    await mark_followup_sent(schedule, db)
            if due:
                logger.info("Dispatched %d follow-up reminders", len(due))
        except Exception as exc:
            logger.error("Follow-up dispatch error: %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting feedback-svc...")
    await create_tables()
    await mq_service.connect()
    consumer_task = asyncio.create_task(start_consumer())
    followup_task = asyncio.create_task(_dispatch_followup_loop())
    yield
    # Shutdown
    consumer_task.cancel()
    followup_task.cancel()
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
