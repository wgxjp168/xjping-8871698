from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DeploymentResponse(BaseModel):
    id: str
    model_version_id: str
    version_tag: str
    status: str
    deployment_strategy: str
    is_active: bool
    deployed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DeploymentRequest(BaseModel):
    model_version_id: str
    version_tag: str
    artifact_path: str
    deployment_strategy: str = "BLUE_GREEN"


class ModelDeployedEvent(BaseModel):
    model_version_id: str
    version_tag: str
    artifact_path: str
    deployed_at: datetime


class RollbackRequest(BaseModel):
    reason: str
