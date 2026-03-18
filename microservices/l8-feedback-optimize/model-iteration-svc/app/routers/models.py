import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.schemas import TrainingJobCreate, TrainingJobResponse, ModelVersionResponse
from app.services import training_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.post("/train", response_model=TrainingJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_training(
    body: TrainingJobCreate = TrainingJobCreate(),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a model training job."""
    job = await training_service.trigger_training(
        db, trigger_reason=body.trigger_reason
    )
    return job


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get the status of a training job by ID."""
    job = await training_service.get_training_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Training job {job_id!r} not found")
    return job


@router.get("/versions", response_model=list[ModelVersionResponse])
async def list_model_versions(db: AsyncSession = Depends(get_db)):
    """List all model versions ordered by creation date (newest first)."""
    versions = await training_service.list_model_versions(db)
    return versions


@router.post(
    "/versions/{version_id}/approve",
    response_model=ModelVersionResponse,
)
async def approve_model_version(version_id: str, db: AsyncSession = Depends(get_db)):
    """Approve a model version, publish l8.model.ready event."""
    mv = await training_service.approve_model(db, version_id)
    if mv is None:
        raise HTTPException(status_code=404, detail=f"ModelVersion {version_id!r} not found")
    return mv
