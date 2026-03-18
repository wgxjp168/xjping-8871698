import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.deployment import Deployment, DeploymentLog
from app.models.schemas import DeploymentRequest, ModelDeployedEvent
from app.services import mq_service
from app.config import get_settings

try:
    import httpx as _httpx
except ImportError:
    _httpx = None  # type: ignore

logger = logging.getLogger(__name__)
settings = get_settings()


async def create_deployment(db: AsyncSession, req: DeploymentRequest) -> Deployment:
    """Create a new deployment record in PENDING status."""
    deployment = Deployment(
        model_version_id=req.model_version_id,
        version_tag=req.version_tag,
        artifact_path=req.artifact_path,
        deployment_strategy=req.deployment_strategy,
        status="PENDING",
        is_active=False,
    )
    db.add(deployment)
    await db.commit()
    await db.refresh(deployment)
    logger.info("Created deployment id=%s version=%s", deployment.id, deployment.version_tag)
    return deployment


async def execute_deployment(db: AsyncSession, deployment_id: str) -> Optional[Deployment]:
    """Execute blue/green deployment: deactivate old active, activate this one, publish event."""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    if deployment is None:
        return None

    # Mark as DEPLOYING
    deployment.status = "DEPLOYING"
    deployment.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(deployment)

    try:
        # Blue/green: deactivate all currently active deployments
        active_result = await db.execute(
            select(Deployment).where(Deployment.is_active == True, Deployment.id != deployment_id)  # noqa: E712
        )
        active_deployments = active_result.scalars().all()
        for active in active_deployments:
            active.is_active = False
            active.updated_at = datetime.utcnow()
            log = DeploymentLog(
                deployment_id=active.id,
                level="INFO",
                message=f"Deactivated by blue/green switch to deployment {deployment_id}",
            )
            db.add(log)

        # Activate the new deployment
        deployment.status = "ACTIVE"
        deployment.is_active = True
        deployment.deployed_at = datetime.utcnow()
        deployment.updated_at = datetime.utcnow()

        deploy_log = DeploymentLog(
            deployment_id=deployment.id,
            level="INFO",
            message=f"Deployment activated via {deployment.deployment_strategy} strategy",
        )
        db.add(deploy_log)

        await db.commit()
        await db.refresh(deployment)

        # Publish l8.model.deployed event
        event = ModelDeployedEvent(
            model_version_id=deployment.model_version_id,
            version_tag=deployment.version_tag,
            artifact_path=deployment.artifact_path or "",
            deployed_at=deployment.deployed_at,
        )
        await mq_service.publish(settings.rabbitmq_output_routing_key, event.model_dump())
        logger.info("Published l8.model.deployed for version=%s", deployment.version_tag)

        # Notify decision-svc to hot-reload the model (best-effort)
        await _notify_decision_svc_reload(deployment.artifact_path or "", deployment.version_tag)

    except Exception as exc:
        logger.error("Deployment execution failed for id=%s: %s", deployment_id, exc, exc_info=True)
        deployment.status = "FAILED"
        deployment.updated_at = datetime.utcnow()
        error_log = DeploymentLog(
            deployment_id=deployment.id,
            level="ERROR",
            message=f"Deployment failed: {exc}",
        )
        db.add(error_log)
        await db.commit()
        await db.refresh(deployment)

    return deployment


async def rollback_deployment(db: AsyncSession, deployment_id: str, reason: str) -> Optional[Deployment]:
    """Mark a deployment as ROLLED_BACK and reactivate the previous active deployment."""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()
    if deployment is None:
        return None

    deployment.status = "ROLLED_BACK"
    deployment.is_active = False
    deployment.rollback_reason = reason
    deployment.rolled_back_at = datetime.utcnow()
    deployment.updated_at = datetime.utcnow()

    rollback_log = DeploymentLog(
        deployment_id=deployment.id,
        level="WARN",
        message=f"Rolled back: {reason}",
    )
    db.add(rollback_log)

    # Find the most recent previously ACTIVE deployment (by deployed_at, excluding current)
    # Use is_active flag OR status==ACTIVE to handle partially-rolled-back states
    prev_result = await db.execute(
        select(Deployment)
        .where(
            Deployment.id != deployment_id,
            Deployment.status.in_(["ACTIVE"]),
            Deployment.rolled_back_at.is_(None),
        )
        .order_by(Deployment.deployed_at.desc())
        .limit(1)
    )
    prev_deployment = prev_result.scalar_one_or_none()
    if prev_deployment:
        prev_deployment.is_active = True
        prev_deployment.updated_at = datetime.utcnow()
        reactivate_log = DeploymentLog(
            deployment_id=prev_deployment.id,
            level="INFO",
            message=f"Reactivated after rollback of deployment {deployment_id}",
        )
        db.add(reactivate_log)
        logger.info("Reactivated previous deployment id=%s", prev_deployment.id)

    await db.commit()
    await db.refresh(deployment)
    logger.info("Rolled back deployment id=%s reason=%s", deployment_id, reason)
    return deployment


async def get_active_deployment(db: AsyncSession) -> Optional[Deployment]:
    """Return the currently active deployment, if any."""
    result = await db.execute(
        select(Deployment).where(Deployment.is_active == True).order_by(Deployment.deployed_at.desc()).limit(1)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def list_deployments(db: AsyncSession, limit: int = 20) -> list[Deployment]:
    """Return the most recent deployments."""
    result = await db.execute(
        select(Deployment).order_by(Deployment.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_deployment(db: AsyncSession, deployment_id: str) -> Optional[Deployment]:
    """Return a deployment by ID."""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    return result.scalar_one_or_none()


async def _notify_decision_svc_reload(artifact_path: str, version_tag: str) -> None:
    """POST to decision-svc /api/v1/models/reload so it hot-swaps the active model."""
    if _httpx is None:
        logger.warning("httpx not available; skipping decision-svc hot-reload")
        return
    url = f"{settings.decision_svc_url}/api/v1/models/reload"
    payload = {"artifact_path": artifact_path, "version_tag": version_tag}
    try:
        async with _httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code < 300:
                logger.info("decision-svc hot-reload triggered: version=%s", version_tag)
            else:
                logger.warning(
                    "decision-svc hot-reload returned %s: %s", resp.status_code, resp.text
                )
    except Exception as exc:
        logger.warning("decision-svc hot-reload failed (non-fatal): %s", exc)
