import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.schemas import ExperimentCreate, ExperimentResponse
from app.services import experiment_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    body: ExperimentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new A/B experiment in DRAFT state."""
    exp = await experiment_service.create_experiment(db, body)
    return exp


@router.get("", response_model=list[ExperimentResponse])
async def list_experiments(db: AsyncSession = Depends(get_db)):
    """List all experiments ordered by creation date (newest first)."""
    experiments = await experiment_service.list_experiments(db)
    return experiments


@router.post("/{exp_id}/start", response_model=ExperimentResponse)
async def start_experiment(exp_id: str, db: AsyncSession = Depends(get_db)):
    """Start a DRAFT experiment (changes status to RUNNING)."""
    exp = await experiment_service.start_experiment(db, exp_id)
    if exp is None:
        raise HTTPException(status_code=404, detail=f"Experiment {exp_id!r} not found")
    return exp


@router.post("/{exp_id}/complete", response_model=ExperimentResponse)
async def complete_experiment(exp_id: str, db: AsyncSession = Depends(get_db)):
    """Complete an experiment: run statistical analysis and set winner."""
    exp = await experiment_service.complete_experiment(db, exp_id)
    if exp is None:
        raise HTTPException(status_code=404, detail=f"Experiment {exp_id!r} not found")
    return exp


@router.get("/{exp_id}/results")
async def get_experiment_results(exp_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed analysis results for an experiment."""
    analysis = await experiment_service.analyze_experiment(db, exp_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Experiment {exp_id!r} not found")
    return {"experiment_id": exp_id, **analysis}
