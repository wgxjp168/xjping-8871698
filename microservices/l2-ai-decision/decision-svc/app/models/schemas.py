"""
Pydantic schemas for the Decision Service.
Defines all request/response models used across the API.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ScoringContext(str, Enum):
    """Determines which scoring model is applied."""
    B2B = "B2B"
    B2C_KNOWN = "B2C_KNOWN"        # Brand already decided
    B2C_UNKNOWN = "B2C_UNKNOWN"    # Brand not yet decided


class BrandStatus(str, Enum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    PARTIAL = "PARTIAL"


class ReportFormat(str, Enum):
    JSON = "json"
    MARKDOWN = "markdown"


class Grade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class FactorDetail(BaseModel):
    """Single scoring factor detail used inside ScoreResult."""
    name: str = Field(..., description="Factor identifier")
    score: float = Field(..., ge=0, le=100, description="Raw score 0-100")
    weight: float = Field(..., ge=0, le=1, description="Dimension weight")
    explanation: str = Field(..., description="Human-readable explanation")
    weighted_contribution: float = Field(
        default=0.0,
        description="Contribution to total score (score * weight)",
    )


# ---------------------------------------------------------------------------
# Core Request / Response Schemas
# ---------------------------------------------------------------------------

class DecisionAnalyzeRequest(BaseModel):
    """Payload for the main /decision/analyze endpoint."""
    session_id: str = Field(..., description="Unique session identifier")
    intent: str = Field(..., description="Parsed purchase intent")
    entities: dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted entities (brand, category, price, specs …)",
    )
    brand_status: BrandStatus = Field(
        default=BrandStatus.UNKNOWN,
        description="Whether the target brand is known/unknown/partial",
    )
    user_context: dict[str, Any] = Field(
        default_factory=dict,
        description="User profile, org type, budget, history …",
    )
    llm_analysis: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional pre-computed LLM analysis payload",
    )


class ScoreResult(BaseModel):
    """Aggregated scoring output from a scorer model."""
    total_score: float = Field(..., ge=0, le=100, description="Weighted total score")
    dimension_scores: dict[str, float] = Field(
        ...,
        description="Individual dimension name → score mapping",
    )
    grade: Grade = Field(..., description="Letter grade derived from total_score")
    confidence: float = Field(..., ge=0, le=1, description="Model confidence in this score")
    factors: list[FactorDetail] = Field(
        default_factory=list,
        description="Detailed factor breakdown with explanations",
    )
    # --- LLM enhancement fields (populated when LLM insight is applied) ---
    llm_adjusted_score: Optional[float] = Field(
        default=None,
        ge=0, le=100,
        description="Score after applying LLM dimension adjustments",
    )
    llm_adjusted_grade: Optional[Grade] = Field(
        default=None,
        description="Grade after LLM adjustment",
    )
    score_lower_bound: Optional[float] = Field(
        default=None,
        ge=0, le=100,
        description="Conservative lower bound (based on missing-data uncertainty)",
    )
    score_upper_bound: Optional[float] = Field(
        default=None,
        ge=0, le=100,
        description="Optimistic upper bound (based on missing-data uncertainty)",
    )

    @field_validator("grade", mode="before")
    @classmethod
    def derive_grade(cls, v: Any, info: Any) -> str:
        """Allow grade to be passed as a string directly."""
        return v


class RuleResult(BaseModel):
    """Output from the rule engine evaluation."""
    passed: bool = Field(..., description="True when no violations exist")
    violations: list[str] = Field(
        default_factory=list,
        description="Hard violations that block or flag the order",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Soft warnings that do not block but merit attention",
    )
    applied_rules: list[str] = Field(
        default_factory=list,
        description="IDs of rules that were evaluated",
    )


class DecisionAnalyzeResponse(BaseModel):
    """Full response from the 8-step decision flow."""
    decision_id: str = Field(
        default_factory=lambda: f"DEC-{uuid4().hex[:12].upper()}",
        description="Unique decision identifier",
    )
    session_id: str = Field(default="", description="Session identifier")
    scoring_context: ScoringContext = Field(..., description="Scoring model used")
    score_result: ScoreResult = Field(..., description="Scoring output")
    rule_result: RuleResult = Field(..., description="Rule engine output")
    recommendation: str = Field(..., description="Natural language recommendation")
    next_steps: list[str] = Field(
        default_factory=list,
        description="Ordered list of recommended next actions",
    )
    requires_human_review: bool = Field(
        default=False,
        description="True when manual review is warranted",
    )
    explanation: Optional[dict[str, Any]] = Field(
        default=None,
        description="SHAP-inspired explainability payload",
    )
    llm_insights: Optional[dict[str, Any]] = Field(
        default=None,
        description="Supplementary LLM insights (optional)",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Report Schemas
# ---------------------------------------------------------------------------

class ReportRequest(BaseModel):
    """Request to generate or retrieve a decision report."""
    decision_id: str = Field(..., description="Decision ID to report on")
    include_explanation: bool = Field(
        default=True,
        description="Whether to include explainability section",
    )
    format: ReportFormat = Field(
        default=ReportFormat.JSON,
        description="Output format: json or markdown",
    )


class ReportResponse(BaseModel):
    """Generated report response."""
    decision_id: str
    report: Any = Field(
        ...,
        description="Report payload: dict for JSON format, str for Markdown",
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "decision-svc"
    version: str = "1.0.0"
