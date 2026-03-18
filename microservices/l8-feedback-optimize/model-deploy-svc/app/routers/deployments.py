import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.schemas import DeploymentRequest, DeploymentResponse, RollbackRequest
from app.services import deploy_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/deployments", tags=["deployments"])


@router.post("", response_model=DeploymentResponse, status_code=202)
async def create_and_execute_deployment(
    req: DeploymentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a deployment and immediately execute it (blue/green)."""
    deployment = await deploy_service.create_deployment(db, req)
    result = await deploy_service.execute_deployment(db, deployment.id)
    if result is None:
        raise HTTPException(status_code=500, detail="Deployment execution failed unexpectedly")
    return result


@router.get("", response_model=list[DeploymentResponse])
async def list_deployments(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List all deployments (most recent first)."""
    return await deploy_service.list_deployments(db, limit=limit)


@router.get("/active", response_model=DeploymentResponse)
async def get_active_deployment(db: AsyncSession = Depends(get_db)):
    """Get the currently active deployment."""
    deployment = await deploy_service.get_active_deployment(db)
    if deployment is None:
        raise HTTPException(status_code=404, detail="No active deployment found")
    return deployment


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(deployment_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific deployment by ID."""
    deployment = await deploy_service.get_deployment(db, deployment_id)
    if deployment is None:
        raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")
    return deployment


@router.post("/{deployment_id}/rollback", response_model=DeploymentResponse)
async def rollback_deployment(
    deployment_id: str,
    req: RollbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rollback a deployment and reactivate the previous active deployment."""
    deployment = await deploy_service.rollback_deployment(db, deployment_id, req.reason)
    if deployment is None:
        raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")
    return deployment
