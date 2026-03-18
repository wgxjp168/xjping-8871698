import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(36), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)  # WECHAT/ALIPAY/WEB/APP

    # Rating & content
    rating: Mapped[int] = mapped_column(Integer, nullable=False)          # 1-5
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    tags: Mapped[str] = mapped_column(String(512), nullable=True)         # comma-separated

    # NLP sentiment
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0.0-1.0
    sentiment_label: Mapped[str] = mapped_column(String(16), nullable=True)  # POSITIVE/NEUTRAL/NEGATIVE
    sentiment_processed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Source
    source: Mapped[str] = mapped_column(String(32), default="USER_SUBMIT")  # USER_SUBMIT / FOLLOWUP

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class FollowUpSchedule(Base):
    __tablename__ = "followup_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    delivery_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # delivery_time + 24h
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    feedback_id: Mapped[str] = mapped_column(String(36), nullable=True)  # filled when feedback received
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
