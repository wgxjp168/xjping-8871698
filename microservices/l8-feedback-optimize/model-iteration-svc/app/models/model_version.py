import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base

class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    model_type: Mapped[str] = mapped_column(String(64), default="xgboost_recommendation")
    artifact_path: Mapped[str] = mapped_column(String(512), nullable=True)

    # Training metadata
    training_samples: Mapped[int] = mapped_column(Integer, nullable=True)
    feature_names: Mapped[list] = mapped_column(JSON, default=list)
    hyperparameters: Mapped[dict] = mapped_column(JSON, default=dict)

    # Evaluation metrics
    auc_roc: Mapped[float] = mapped_column(Float, nullable=True)
    f1_score: Mapped[float] = mapped_column(Float, nullable=True)
    precision: Mapped[float] = mapped_column(Float, nullable=True)
    recall: Mapped[float] = mapped_column(Float, nullable=True)
    accuracy: Mapped[float] = mapped_column(Float, nullable=True)

    # Status: TRAINING / TRAINED / EVALUATED / APPROVED / DEPLOYED / RETIRED / FAILED
    status: Mapped[str] = mapped_column(String(32), default="TRAINING")
    approved: Mapped[bool] = mapped_column(Boolean, default=False)

    training_job_id: Mapped[str] = mapped_column(String(36), nullable=True)
    deployed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # Status: PENDING / RUNNING / SUCCESS / FAILED
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    model_version_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    trigger_reason: Mapped[str] = mapped_column(String(128), default="MANUAL")

    # Job progress
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    log: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
