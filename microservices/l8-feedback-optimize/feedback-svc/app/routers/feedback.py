import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.database import get_db
from app.models.feedback import Feedback
from app.models.schemas import FeedbackCreate, FeedbackResponse, FeedbackAnalytics, FeedbackCollectedEvent
from app.services.sentiment_service import analyze_sentiment_from_rating
from app.services import mq_service
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(body: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    """Submit user feedback for an AI report."""
    sentiment_score, sentiment_label = analyze_sentiment_from_rating(body.rating, body.comment)
    
    fb = Feedback(
        report_id=body.report_id,
        user_id=body.user_id,
        order_id=body.order_id,
        channel=body.channel.value,
        rating=body.rating,
        comment=body.comment,
        tags=",".join(body.tags) if body.tags else None,
        sentiment_score=sentiment_score,
        sentiment_label=sentiment_label,
        sentiment_processed=True,
        source=body.source,
    )
    db.add(fb)
    await db.commit()
    await db.refresh(fb)

    # Publish event to behavior-track-svc
    event = FeedbackCollectedEvent(
        feedback_id=fb.id,
        report_id=fb.report_id,
        user_id=fb.user_id,
        rating=fb.rating,
        sentiment_score=fb.sentiment_score,
        sentiment_label=fb.sentiment_label,
        channel=fb.channel,
        created_at=fb.created_at.isoformat(),
    )
    await mq_service.publish(settings.rabbitmq_output_routing_key, event.model_dump())
    logger.info(f"Feedback submitted id={fb.id} rating={fb.rating} sentiment={sentiment_label}")
    return fb


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(feedback_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    fb = result.scalar_one_or_none()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return fb


@router.get("/report/{report_id}", response_model=list[FeedbackResponse])
async def list_feedback_by_report(report_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Feedback).where(Feedback.report_id == report_id))
    return list(result.scalars().all())


@router.get("/user/{user_id}", response_model=list[FeedbackResponse])
async def list_feedback_by_user(
    user_id: str,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Feedback).where(Feedback.user_id == user_id).limit(limit)
    )
    return list(result.scalars().all())


@router.get("/analytics/summary", response_model=FeedbackAnalytics)
async def feedback_analytics(
    report_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = select(Feedback)
    if report_id:
        query = query.where(Feedback.report_id == report_id)
    result = await db.execute(query)
    feedbacks = list(result.scalars().all())

    if not feedbacks:
        return FeedbackAnalytics(
            total_count=0, avg_rating=0.0,
            positive_rate=0.0, neutral_rate=0.0, negative_rate=0.0,
            rating_distribution={str(i): 0 for i in range(1, 6)}
        )

    total = len(feedbacks)
    avg_rating = sum(f.rating for f in feedbacks) / total
    dist = {str(i): sum(1 for f in feedbacks if f.rating == i) for i in range(1, 6)}
    positive = sum(1 for f in feedbacks if f.sentiment_label == "POSITIVE")
    neutral = sum(1 for f in feedbacks if f.sentiment_label == "NEUTRAL")
    negative = sum(1 for f in feedbacks if f.sentiment_label == "NEGATIVE")

    return FeedbackAnalytics(
        total_count=total,
        avg_rating=round(avg_rating, 2),
        positive_rate=round(positive / total, 4),
        neutral_rate=round(neutral / total, 4),
        negative_rate=round(negative / total, 4),
        rating_distribution=dist,
    )
