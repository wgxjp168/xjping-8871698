from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=128)
    description: Optional[str] = None
    experiment_type: str = "MODEL_AB"
    traffic_percentage: float = Field(50.0, ge=1.0, le=99.0)
    target_metric: str = "conversion_rate"
    control_model_version_id: Optional[str] = None
    variant_model_version_id: Optional[str] = None

class ExperimentResponse(BaseModel):
    id: str
    name: str
    status: str
    experiment_type: str
    traffic_percentage: float
    target_metric: str
    control_metric_value: Optional[float]
    variant_metric_value: Optional[float]
    p_value: Optional[float]
    winner: Optional[str]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}

class TrainingJobCreate(BaseModel):
    trigger_reason: str = "MANUAL"
    hyperparameters: Optional[Dict[str, Any]] = None

class TrainingJobResponse(BaseModel):
    id: str
    status: str
    model_version_id: Optional[str]
    trigger_reason: str
    progress_pct: int
    log: str
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}

class ModelVersionResponse(BaseModel):
    id: str
    version_tag: str
    model_type: str
    training_samples: Optional[int]
    auc_roc: Optional[float]
    f1_score: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    status: str
    approved: bool
    created_at: datetime

    model_config = {"from_attributes": True}

class ModelReadyEvent(BaseModel):
    """Published to l8.model.ready → model-deploy-svc"""
    model_version_id: str
    version_tag: str
    artifact_path: str
    auc_roc: float
    f1_score: float
    approved_at: str
