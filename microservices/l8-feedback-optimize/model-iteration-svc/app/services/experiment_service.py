"""A/B experiment management service."""
import logging
import uuid
from datetime import datetime
from typing import Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.experiment import Experiment, ExperimentVariant
from app.models.schemas import ExperimentCreate

logger = logging.getLogger(__name__)
settings = get_settings()


async def create_experiment(db: AsyncSession, data: ExperimentCreate) -> Experiment:
    exp = Experiment(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        experiment_type=data.experiment_type,
        traffic_percentage=data.traffic_percentage,
        target_metric=data.target_metric,
        status="DRAFT",
    )
    db.add(exp)
    await db.flush()

    # Create CONTROL variant
    control = ExperimentVariant(
        id=str(uuid.uuid4()),
        experiment_id=exp.id,
        name="CONTROL",
        model_version_id=data.control_model_version_id,
        config={},
    )
    db.add(control)

    # Create VARIANT_A
    variant = ExperimentVariant(
        id=str(uuid.uuid4()),
        experiment_id=exp.id,
        name="VARIANT_A",
        model_version_id=data.variant_model_version_id,
        config={},
    )
    db.add(variant)

    await db.commit()
    await db.refresh(exp)
    return exp


async def start_experiment(db: AsyncSession, exp_id: str) -> Optional[Experiment]:
    result = await db.execute(select(Experiment).where(Experiment.id == exp_id))
    exp = result.scalar_one_or_none()
    if exp is None:
        return None
    exp.status = "RUNNING"
    exp.started_at = datetime.utcnow()
    await db.commit()
    await db.refresh(exp)
    return exp


async def record_outcome(
    db: AsyncSession,
    exp_id: str,
    variant_name: str,
    metric_value: float,
) -> None:
    """Update ExperimentVariant stats for a single outcome observation."""
    result = await db.execute(
        select(ExperimentVariant).where(
            ExperimentVariant.experiment_id == exp_id,
            ExperimentVariant.name == variant_name,
        )
    )
    variant = result.scalar_one_or_none()
    if variant is None:
        logger.warning("Variant %s not found for experiment %s", variant_name, exp_id)
        return

    variant.user_count += 1
    # Treat metric_value >= 1.0 as a conversion (binary), otherwise accumulate satisfaction
    if metric_value >= 1.0:
        variant.conversion_count += 1
    variant.satisfaction_sum += metric_value
    await db.commit()


async def analyze_experiment(db: AsyncSession, exp_id: str) -> dict:
    """Perform statistical analysis on experiment variants.

    Uses a proportion z-test (numpy) to compare conversion rates.
    Returns p_value and winner (CONTROL / VARIANT / INCONCLUSIVE).
    """
    result = await db.execute(select(Experiment).where(Experiment.id == exp_id))
    exp = result.scalar_one_or_none()
    if exp is None:
        return {}

    variants_result = await db.execute(
        select(ExperimentVariant).where(ExperimentVariant.experiment_id == exp_id)
    )
    variants = list(variants_result.scalars().all())

    control = next((v for v in variants if v.name == "CONTROL"), None)
    variant = next((v for v in variants if v.name == "VARIANT_A"), None)

    if control is None or variant is None:
        return {"error": "Missing CONTROL or VARIANT_A variant"}

    n_c = control.user_count
    n_v = variant.user_count
    x_c = control.conversion_count
    x_v = variant.conversion_count

    # Proportions
    p_c = x_c / n_c if n_c > 0 else 0.0
    p_v = x_v / n_v if n_v > 0 else 0.0

    # Two-proportion z-test (numpy, no scipy)
    p_value = _proportion_z_test(x_c, n_c, x_v, n_v)

    alpha = 1.0 - settings.ab_test_confidence_level
    min_n = settings.ab_test_min_sample_size

    if n_c < min_n or n_v < min_n:
        winner = "INCONCLUSIVE"
    elif p_value < alpha:
        winner = "VARIANT" if p_v > p_c else "CONTROL"
    else:
        winner = "INCONCLUSIVE"

    return {
        "control_metric_value": round(p_c, 4),
        "variant_metric_value": round(p_v, 4),
        "p_value": round(p_value, 6),
        "winner": winner,
        "control_n": n_c,
        "variant_n": n_v,
    }


async def complete_experiment(db: AsyncSession, exp_id: str) -> Optional[Experiment]:
    analysis = await analyze_experiment(db, exp_id)

    result = await db.execute(select(Experiment).where(Experiment.id == exp_id))
    exp = result.scalar_one_or_none()
    if exp is None:
        return None

    exp.status = "COMPLETED"
    exp.ended_at = datetime.utcnow()
    exp.control_metric_value = analysis.get("control_metric_value")
    exp.variant_metric_value = analysis.get("variant_metric_value")
    exp.p_value = analysis.get("p_value")
    exp.winner = analysis.get("winner", "INCONCLUSIVE")
    await db.commit()
    await db.refresh(exp)
    return exp


async def list_experiments(db: AsyncSession) -> list[Experiment]:
    result = await db.execute(
        select(Experiment).order_by(Experiment.created_at.desc())
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Statistical helper
# ---------------------------------------------------------------------------

def _proportion_z_test(x1: int, n1: int, x2: int, n2: int) -> float:
    """Two-proportion z-test; returns two-tailed p-value (numpy only)."""
    if n1 == 0 or n2 == 0:
        return 1.0

    p1 = x1 / n1
    p2 = x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)

    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0

    z = (p1 - p2) / se
    # Approximate two-tailed p-value via the normal CDF using the erf function
    # P(|Z| > |z|) = 2 * (1 - Phi(|z|))
    # Phi(z) = 0.5 * (1 + erf(z / sqrt(2)))
    from math import erf, sqrt
    p_value = 2.0 * (1.0 - 0.5 * (1.0 + erf(abs(z) / sqrt(2.0))))
    return float(np.clip(p_value, 0.0, 1.0))
