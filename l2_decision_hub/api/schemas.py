"""Pydantic request/response schemas for the REST API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from l2_decision_hub.models.decision import DecisionState, DecisionType, DecisionResult


# ------------------------------------------------------------------
# Request schemas
# ------------------------------------------------------------------

class SubmitDecisionRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200, description="Short decision title")
    description: str = Field(min_length=1, description="Detailed description")
    decision_type: DecisionType = Field(default=DecisionType.OPERATIONAL)
    priority: int = Field(default=2, ge=1, le=5, description="1=LOW … 5=EMERGENCY")
    input_data: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    session_id: str | None = None


# ------------------------------------------------------------------
# Response schemas
# ------------------------------------------------------------------

class DecisionResultSchema(BaseModel):
    action: str
    reasoning: str
    confidence: float
    alternatives: list[dict[str, Any]] = []
    parameters: dict[str, Any] = {}
    metadata: dict[str, Any] = {}


class DecisionResponse(BaseModel):
    id: str
    title: str
    description: str
    type: DecisionType
    state: DecisionState
    priority: int
    input_data: dict[str, Any] = {}
    constraints: list[str] = []
    objectives: list[str] = []
    result: DecisionResultSchema | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    tags: list[str] = []


class SubmitDecisionResponse(BaseModel):
    decision_id: str
    message: str = "Decision submitted successfully"


class ListDecisionsResponse(BaseModel):
    decisions: list[DecisionResponse]
    total: int
    limit: int
    offset: int


class HandlerInfo(BaseModel):
    name: str
    supported_types: list[str]
    min_priority: int


class HubStatusResponse(BaseModel):
    status: str
    total_decisions: int
    pending: int
    reasoning: int
    completed: int
    failed: int
    handlers: list[HandlerInfo]
