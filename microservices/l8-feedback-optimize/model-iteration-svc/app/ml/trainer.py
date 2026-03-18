"""XGBoost recommendation model trainer."""
import logging
import os
import uuid
from datetime import datetime
from typing import Any

import joblib
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

FEATURE_NAMES = [
    "conversion_rate",
    "avg_satisfaction",
    "click_count",
    "view_count",
    "session_duration",
]

DEFAULT_HYPERPARAMETERS: dict[str, Any] = {
    "n_estimators": 100,
    "max_depth": 4,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "use_label_encoder": False,
    "eval_metric": "logloss",
    "random_state": 42,
}


def _build_feature_matrix(samples: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Convert list of sample dicts to X and y arrays."""
    X = np.array(
        [
            [
                float(s.get("conversion_rate", 0.0)),
                float(s.get("avg_satisfaction", 0.0)),
                float(s.get("click_count", 0)),
                float(s.get("view_count", 0)),
                float(s.get("session_duration", 0.0)),
            ]
            for s in samples
        ],
        dtype=np.float32,
    )
    y = np.array([int(s.get("label", 0)) for s in samples], dtype=np.int32)
    return X, y


def _generate_synthetic_samples(n: int = 200) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic training data when real data is insufficient."""
    rng = np.random.default_rng(seed=42)
    X = np.column_stack(
        [
            rng.uniform(0.0, 0.3, n),       # conversion_rate
            rng.uniform(1.0, 5.0, n),       # avg_satisfaction
            rng.integers(0, 500, n).astype(np.float32),  # click_count
            rng.integers(0, 1000, n).astype(np.float32),  # view_count
            rng.uniform(30.0, 600.0, n),    # session_duration
        ]
    ).astype(np.float32)
    # Label: positive if conversion_rate > 0.10 OR avg_satisfaction > 3.5
    y = ((X[:, 0] > 0.10) | (X[:, 1] > 3.5)).astype(np.int32)
    return X, y


def train_model(samples: list[dict] | None = None) -> dict:
    """Train an XGBoost classifier on behavior samples.

    Falls back to synthetic/demo mode when samples are None or too few to
    produce a meaningful model (threshold: 50 real samples).

    Returns a dict with:
        artifact_path, feature_names, hyperparameters, training_samples
    """
    try:
        from xgboost import XGBClassifier  # type: ignore
    except ImportError as exc:
        raise RuntimeError("xgboost is required") from exc

    os.makedirs(settings.model_store_path, exist_ok=True)

    synthetic = False
    if not samples or len(samples) < 50:
        logger.warning(
            "Insufficient real samples (%d), falling back to synthetic training data",
            len(samples) if samples else 0,
        )
        X, y = _generate_synthetic_samples(200)
        synthetic = True
    else:
        X, y = _build_feature_matrix(samples)
        if X.shape[0] < 50:
            logger.warning("After parsing, only %d samples available; using synthetic data", X.shape[0])
            X, y = _generate_synthetic_samples(200)
            synthetic = True

    hp = dict(DEFAULT_HYPERPARAMETERS)
    model = XGBClassifier(**{k: v for k, v in hp.items() if k != "random_state"}, random_state=hp["random_state"])
    model.fit(X, y)

    version_tag = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    artifact_filename = f"xgb_{version_tag}.joblib"
    artifact_path = os.path.join(settings.model_store_path, artifact_filename)
    joblib.dump(model, artifact_path)

    logger.info(
        "Model trained and saved to %s (synthetic=%s, samples=%d)",
        artifact_path,
        synthetic,
        X.shape[0],
    )

    return {
        "artifact_path": artifact_path,
        "feature_names": FEATURE_NAMES,
        "hyperparameters": hp,
        "training_samples": X.shape[0],
        "version_tag": version_tag,
        "synthetic": synthetic,
    }
