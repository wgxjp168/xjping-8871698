"""Decision data models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DecisionState(str, Enum):
    """Lifecycle states of a decision."""
    PENDING = "pending"          # Queued, awaiting processing
    REASONING = "reasoning"      # AI is thinking
    DECIDED = "decided"          # Decision reached
    EXECUTING = "executing"      # Handler is executing
    COMPLETED = "completed"      # Successfully completed
    FAILED = "failed"            # Processing failed
    CANCELLED = "cancelled"      # Cancelled before completion


class DecisionType(str, Enum):
    """Category of decision to be made."""
    STRATEGIC = "strategic"      # High-level strategic choices
    TACTICAL = "tactical"        # Mid-level tactical actions
    OPERATIONAL = "operational"  # Routine operational decisions
    RISK = "risk"                # Risk assessment and mitigation
    RESOURCE = "resource"        # Resource allocation
    ESCALATION = "escalation"    # Escalation handling
    CUSTOM = "custom"            # User-defined decision type


class DecisionResult(BaseModel):
    """The outcome produced by the AI reasoning engine."""
    action: str = Field(description="The recommended action to take")
    reasoning: str = Field(description="Explanation of why this action was chosen")
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score in the decision (0-1)"
    )
    alternatives: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Alternative actions with their trade-offs",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution parameters for the chosen action",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from the reasoning process",
    )


class Decision(BaseModel):
    """A decision request flowing through the hub."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique decision identifier",
    )
    type: DecisionType = Field(
        default=DecisionType.OPERATIONAL,
        description="Category of this decision",
    )
    state: DecisionState = Field(
        default=DecisionState.PENDING,
        description="Current lifecycle state",
    )
    priority: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Priority level (1=LOW … 5=EMERGENCY)",
    )
    title: str = Field(description="Short human-readable title")
    description: str = Field(description="Detailed description of the decision needed")
    input_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured input data relevant to this decision",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Hard constraints the decision must satisfy",
    )
    objectives: list[str] = Field(
        default_factory=list,
        description="Goals the decision should optimise for",
    )
    result: DecisionResult | None = Field(
        default=None,
        description="The AI-produced decision result (set after reasoning)",
    )
    error: str | None = Field(
        default=None,
        description="Error message if state is FAILED",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)

    def transition(self, new_state: DecisionState) -> None:
        """Update state and timestamp."""
        self.state = new_state
        self.updated_at = datetime.utcnow()
        if new_state in (DecisionState.COMPLETED, DecisionState.FAILED):
            self.completed_at = datetime.utcnow()
