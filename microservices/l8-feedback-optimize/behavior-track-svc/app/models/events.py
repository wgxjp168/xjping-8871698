import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class UserSession(Base):
    """Tracks per-user session level metrics."""
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    page_views: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    report_views: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    total_time_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ConversionFunnel(Base):
    """Tracks report → purchase conversion funnel stages."""
    __tablename__ = "conversion_funnels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    report_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)  # VIEW/DETAIL/CART/PURCHASE
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    converted: Mapped[bool] = mapped_column(Boolean, default=False)
    time_to_convert_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
