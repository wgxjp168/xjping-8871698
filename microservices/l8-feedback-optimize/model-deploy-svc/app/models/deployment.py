import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_version_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version_tag: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    # Status values: PENDING / DEPLOYING / ACTIVE / FAILED / ROLLED_BACK

    artifact_path: Mapped[str] = mapped_column(String(512), nullable=True)
    deployed_by: Mapped[str] = mapped_column(String(128), nullable=True)
    deployment_strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="BLUE_GREEN")
    # Strategy values: BLUE_GREEN / CANARY / IMMEDIATE

    canary_traffic_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    rollback_reason: Mapped[str] = mapped_column(Text, nullable=True)
    deployed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    rolled_back_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    logs: Mapped[list["DeploymentLog"]] = relationship("DeploymentLog", back_populates="deployment", cascade="all, delete-orphan")


class DeploymentLog(Base):
    __tablename__ = "deployment_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deployment_id: Mapped[str] = mapped_column(String(36), ForeignKey("deployments.id"), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="INFO")
    # Level values: INFO / WARN / ERROR
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    deployment: Mapped["Deployment"] = relationship("Deployment", back_populates="logs")
