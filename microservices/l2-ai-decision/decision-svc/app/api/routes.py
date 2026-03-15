"""
FastAPI router for the Decision Service.

Endpoints:
  POST /decision/analyze        — full 8-step decision flow
  POST /decision/score          — score-only (no explanation)
  POST /decision/rules          — rules-only evaluation
  GET  /decision/report/{id}    — retrieve cached report
  POST /decision/report/generate — generate a new report
  GET  /decision/health
  GET  /health
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.models.schemas import (
    BrandStatus,
    DecisionAnalyzeRequest,
    DecisionAnalyzeResponse,
    HealthResponse,
    ReportFormat,
    ReportRequest,
    ReportResponse,
    RuleResult,
    ScoreResult,
    ScoringContext,
)
from app.services.decision_engine import decision_engine
from app.services.report_generator import report_generator
from app.services.rule_engine import rule_engine
from app.services.scoring.b2b_scorer import b2b_scorer
from app.services.scoring.b2c_known_scorer import b2c_known_scorer
from app.services.scoring.b2c_unknown_scorer import b2c_unknown_scorer

logger = logging.getLogger(__name__)

router = APIRouter()


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #

@router.get("/health", response_model=HealthResponse, tags=["health"])
@router.get("/decision/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """Liveness / readiness health check."""
    return HealthResponse(status="ok", service="decision-svc", version="1.0.0")


# --------------------------------------------------------------------------- #
# Full decision flow
# --------------------------------------------------------------------------- #

@router.post(
    "/decision/analyze",
    response_model=DecisionAnalyzeResponse,
    tags=["decision"],
    summary="Full 8-step AI decision analysis",
)
async def analyze(request: DecisionAnalyzeRequest) -> DecisionAnalyzeResponse:
    """
    Execute the complete 8-step AI decision flow:
    1. Validate input
    2. Determine scoring context (B2B / B2C_KNOWN / B2C_UNKNOWN)
    3. Enrich context from L3 services (with mock fallback)
    4. Apply rule engine (8 pre-defined rules)
    5. Calculate dimension scores using the appropriate scorer
    6. Fetch optional LLM insights
    7. Generate SHAP-inspired explainability
    8. Compile and return the decision response
    """
    try:
        response = await decision_engine.analyze(request)
        return response
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error in decision analysis")
        raise HTTPException(status_code=500, detail=f"Decision analysis failed: {exc}") from exc


# --------------------------------------------------------------------------- #
# Score-only endpoint
# --------------------------------------------------------------------------- #

class ScoreOnlyRequest(DecisionAnalyzeRequest):
    """Reuse DecisionAnalyzeRequest; scoring_context can be passed explicitly."""
    scoring_context: ScoringContext | None = None


@router.post(
    "/decision/score",
    response_model=ScoreResult,
    tags=["decision"],
    summary="Score-only evaluation (no explanation or rules)",
)
async def score_only(request: ScoreOnlyRequest) -> ScoreResult:
    """
    Run only the scoring step.  If scoring_context is not provided it is
    inferred from intent/entities/brand_status.  Useful for fast scoring
    without the full 8-step flow overhead.
    """
    try:
        # Determine context if not provided
        if request.scoring_context is None:
            ctx = decision_engine._step_determine_scoring_context(
                request.intent, request.entities, request.brand_status
            )
        else:
            ctx = request.scoring_context

        # Build a minimal enriched context from request data
        context: dict[str, Any] = {
            **request.entities,
            **request.user_context,
            "session_id": request.session_id,
            "intent": request.intent,
        }
        # Add mock market/product data for any missing keys
        context.update(decision_engine._mock_product_data(request.entities))
        context.update(decision_engine._mock_market_data(request.entities))

        # Prefer provided values over mocks
        context.update(request.entities)
        context.update(request.user_context)

        return decision_engine._step_calculate_scores(context, ctx)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Error in score-only endpoint")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# --------------------------------------------------------------------------- #
# Rules-only endpoint
# --------------------------------------------------------------------------- #

@router.post(
    "/decision/rules",
    response_model=RuleResult,
    tags=["decision"],
    summary="Rules-only evaluation",
)
async def rules_only(request: DecisionAnalyzeRequest) -> RuleResult:
    """
    Run only the rule engine step.  Returns violations and warnings without
    scoring.  Useful for quick compliance checks.
    """
    try:
        context: dict[str, Any] = {
            **request.entities,
            **request.user_context,
            "session_id": request.session_id,
            "intent": request.intent,
        }
        return rule_engine.evaluate(context)
    except Exception as exc:
        logger.exception("Error in rules-only endpoint")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# --------------------------------------------------------------------------- #
# Report endpoints
# --------------------------------------------------------------------------- #

@router.get(
    "/decision/report/{decision_id}",
    tags=["report"],
    summary="Get cached decision report",
)
async def get_report(
    decision_id: str,
    fmt: ReportFormat = Query(default=ReportFormat.JSON, alias="format"),
) -> Any:
    """
    Retrieve a report for a previously analyzed decision (served from cache).
    Use ?format=markdown to get a Markdown-formatted report.
    """
    decision = decision_engine.get_cached(decision_id)
    if not decision:
        raise HTTPException(
            status_code=404, detail=f"Decision '{decision_id}' not found in cache"
        )

    report_resp = report_generator.generate(decision, fmt=fmt.value)

    if fmt == ReportFormat.MARKDOWN:
        return PlainTextResponse(content=report_resp.report, media_type="text/markdown")

    return report_resp


@router.post(
    "/decision/report/generate",
    response_model=ReportResponse,
    tags=["report"],
    summary="Generate a decision report from cached decision",
)
async def generate_report(request: ReportRequest) -> ReportResponse:
    """
    Generate a full report for a cached decision.  Supports JSON and Markdown
    output formats.
    """
    decision = decision_engine.get_cached(request.decision_id)
    if not decision:
        raise HTTPException(
            status_code=404, detail=f"Decision '{request.decision_id}' not found in cache"
        )

    return report_generator.generate(decision, fmt=request.format.value)
