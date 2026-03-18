"""Model evaluation utilities."""
import logging

import joblib
import numpy as np

from app.config import get_settings
from app.ml.trainer import FEATURE_NAMES, _generate_synthetic_samples

logger = logging.getLogger(__name__)
settings = get_settings()


def _extract_features_labels(test_data: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    X = np.array(
        [
            [
                float(s.get("conversion_rate", 0.0)),
                float(s.get("avg_satisfaction", 0.0)),
                float(s.get("click_count", 0)),
                float(s.get("view_count", 0)),
                float(s.get("session_duration", 0.0)),
            ]
            for s in test_data
        ],
        dtype=np.float32,
    )
    y = np.array([int(s.get("label", 0)) for s in test_data], dtype=np.int32)
    return X, y


def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
    """Compute AUC-ROC, F1, precision, recall, accuracy without scipy."""
    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0.0

    # Compute AUC-ROC via trapezoidal rule
    auc_roc = _compute_auc_roc(y_true, y_prob)

    return {
        "auc_roc": round(auc_roc, 4),
        "f1_score": round(f1, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "accuracy": round(accuracy, 4),
    }


def _compute_auc_roc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Compute AUC-ROC using the trapezoidal approximation (no scipy)."""
    thresholds = np.unique(np.concatenate([[0.0], np.sort(y_prob)[::-1], [1.0]]))
    tpr_list = []
    fpr_list = []
    pos = np.sum(y_true == 1)
    neg = np.sum(y_true == 0)
    if pos == 0 or neg == 0:
        return 0.5  # degenerate case

    for t in thresholds:
        pred = (y_prob >= t).astype(int)
        tp = np.sum((pred == 1) & (y_true == 1))
        fp = np.sum((pred == 1) & (y_true == 0))
        tpr_list.append(tp / pos)
        fpr_list.append(fp / neg)

    fpr_arr = np.array(fpr_list)
    tpr_arr = np.array(tpr_list)
    # Sort by FPR for trapz
    order = np.argsort(fpr_arr)
    return float(np.trapz(tpr_arr[order], fpr_arr[order]))


def evaluate_model(artifact_path: str, test_data: list[dict] | None = None) -> dict:
    """Load a saved model and evaluate it.

    Falls back to synthetic test data when test_data is None or too small.

    Returns a dict with: auc_roc, f1_score, precision, recall, accuracy,
    and passes_thresholds (bool).
    """
    model = joblib.load(artifact_path)

    if not test_data or len(test_data) < 30:
        logger.warning(
            "Insufficient test data (%d rows), using synthetic evaluation set",
            len(test_data) if test_data else 0,
        )
        X_test, y_true = _generate_synthetic_samples(150)
    else:
        X_test, y_true = _extract_features_labels(test_data)

    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    metrics = _compute_metrics(y_true, y_pred, y_prob)
    metrics["passes_thresholds"] = (
        metrics["auc_roc"] >= settings.min_auc and metrics["f1_score"] >= settings.min_f1
    )

    logger.info(
        "Evaluation results: auc=%.4f, f1=%.4f, passes=%s",
        metrics["auc_roc"],
        metrics["f1_score"],
        metrics["passes_thresholds"],
    )
    return metrics
