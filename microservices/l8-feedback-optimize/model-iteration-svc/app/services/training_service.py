"""Training orchestration service."""
import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.model_version import ModelVersion, TrainingJob

logger = logging.getLogger(__name__)
settings = get_settings()


async def trigger_training(
    db: AsyncSession,
    trigger_reason: str = "MANUAL",
    samples: Optional[list[dict]] = None,
) -> TrainingJob:
    """Create a TrainingJob record, run train + evaluate, update records.

    When ``samples`` is None the trainer will use synthetic data so that the
    job can always complete successfully in demo / test environments.
    """
    # Create TrainingJob
    job = TrainingJob(
        id=str(uuid.uuid4()),
        status="PENDING",
        trigger_reason=trigger_reason,
        progress_pct=0,
        log="",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Mark RUNNING
    job.status = "RUNNING"
    job.started_at = datetime.utcnow()
    job.progress_pct = 10
    job.log = "Training started\n"
    await db.commit()

    try:
        # --- Train ---
        from app.ml.trainer import train_model

        logger.info("Training model (job=%s, reason=%s)", job.id, trigger_reason)
        train_result = await _run_in_thread(train_model, samples)

        job.progress_pct = 60
        job.log += f"Model trained: {train_result['artifact_path']}\n"
        await db.commit()

        # --- Evaluate ---
        from app.ml.evaluator import evaluate_model

        eval_result = await _run_in_thread(
            evaluate_model, train_result["artifact_path"], None
        )

        job.progress_pct = 90
        job.log += (
            f"Evaluation done: auc={eval_result['auc_roc']}, f1={eval_result['f1_score']}\n"
        )
        await db.commit()

        # --- Create ModelVersion ---
        model_status = "EVALUATED" if eval_result["passes_thresholds"] else "FAILED"
        mv = ModelVersion(
            id=str(uuid.uuid4()),
            version_tag=train_result["version_tag"],
            model_type="xgboost_recommendation",
            artifact_path=train_result["artifact_path"],
            training_samples=train_result["training_samples"],
            feature_names=train_result["feature_names"],
            hyperparameters=train_result["hyperparameters"],
            auc_roc=eval_result["auc_roc"],
            f1_score=eval_result["f1_score"],
            precision=eval_result["precision"],
            recall=eval_result["recall"],
            accuracy=eval_result["accuracy"],
            status=model_status,
            approved=False,
            training_job_id=job.id,
        )
        db.add(mv)
        await db.commit()
        await db.refresh(mv)

        # Finalize job
        job.status = "SUCCESS"
        job.model_version_id = mv.id
        job.progress_pct = 100
        job.log += f"ModelVersion created: {mv.id} (status={model_status})\n"
        job.completed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(job)

        logger.info(
            "Training job %s completed: model_version=%s, status=%s",
            job.id,
            mv.id,
            model_status,
        )

    except Exception as exc:
        logger.error("Training job %s failed: %s", job.id, exc, exc_info=True)
        job.status = "FAILED"
        job.error_message = str(exc)
        job.completed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(job)

    return job


async def get_training_job(db: AsyncSession, job_id: str) -> Optional[TrainingJob]:
    result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
    return result.scalar_one_or_none()


async def list_model_versions(db: AsyncSession) -> list[ModelVersion]:
    result = await db.execute(
        select(ModelVersion).order_by(ModelVersion.created_at.desc())
    )
    return list(result.scalars().all())


async def approve_model(db: AsyncSession, model_version_id: str) -> Optional[ModelVersion]:
    """Mark a model version APPROVED and publish l8.model.ready event."""
    result = await db.execute(
        select(ModelVersion).where(ModelVersion.id == model_version_id)
    )
    mv = result.scalar_one_or_none()
    if mv is None:
        return None

    mv.status = "APPROVED"
    mv.approved = True
    mv.deployed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(mv)

    # Publish event to model-deploy-svc
    from app.services import mq_service

    event = {
        "model_version_id": mv.id,
        "version_tag": mv.version_tag,
        "artifact_path": mv.artifact_path or "",
        "auc_roc": mv.auc_roc or 0.0,
        "f1_score": mv.f1_score or 0.0,
        "approved_at": mv.deployed_at.isoformat(),
    }
    await mq_service.publish(settings.rabbitmq_output_routing_key, event)
    logger.info("Published l8.model.ready for model_version=%s", mv.id)

    return mv


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _run_in_thread(fn, *args):
    """Run a synchronous (CPU-bound) function in the default thread pool."""
    import asyncio
    import functools

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(fn, *args))
