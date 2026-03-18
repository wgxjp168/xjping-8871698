import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    # Status: DRAFT / RUNNING / PAUSED / COMPLETED / ABORTED
    status: Mapped[str] = mapped_column(String(32), default="DRAFT")
    # Type: MODEL_AB / UI_AB / FEATURE_FLAG
    experiment_type: Mapped[str] = mapped_column(String(32), default="MODEL_AB")

    # Traffic allocation
    traffic_percentage: Mapped[float] = mapped_column(Float, default=50.0)  # % to send to variant

    # Target metric
    target_metric: Mapped[str] = mapped_column(String(64), default="conversion_rate")

    # Results
    control_metric_value: Mapped[float] = mapped_column(Float, nullable=True)
    variant_metric_value: Mapped[float] = mapped_column(Float, nullable=True)
    p_value: Mapped[float] = mapped_column(Float, nullable=True)
    winner: Mapped[str] = mapped_column(String(16), nullable=True)  # CONTROL / VARIANT / INCONCLUSIVE

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class ExperimentVariant(Base):
    __tablename__ = "experiment_variants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)  # CONTROL / VARIANT_A / VARIANT_B
    model_version_id: Mapped[str] = mapped_column(String(36), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    user_count: Mapped[int] = mapped_column(Integer, default=0)
    conversion_count: Mapped[int] = mapped_column(Integer, default=0)
    satisfaction_sum: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
