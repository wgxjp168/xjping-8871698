"""FastAPI route definitions for the L2 Decision Hub REST API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from l2_decision_hub.api.schemas import (
    DecisionResponse,
    DecisionResultSchema,
    HandlerInfo,
    HubStatusResponse,
    ListDecisionsResponse,
    SubmitDecisionRequest,
    SubmitDecisionResponse,
)
from l2_decision_hub.core.engine import DecisionHub
from l2_decision_hub.models.decision import DecisionState

logger = logging.getLogger(__name__)

router = APIRouter()

# The hub instance is injected via FastAPI's dependency system
_hub: DecisionHub | None = None


def get_hub() -> DecisionHub:
    if _hub is None:
        raise RuntimeError("DecisionHub not initialised")
    return _hub


def set_hub(hub: DecisionHub) -> None:
    global _hub
    _hub = hub


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@router.get("/health", tags=["system"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "L2-AI Decision Hub"}


# ------------------------------------------------------------------
# Hub status
# ------------------------------------------------------------------

@router.get("/status", response_model=HubStatusResponse, tags=["system"])
async def hub_status(hub: DecisionHub = Depends(get_hub)):
    """Return overall hub statistics and registered handlers."""
    state = hub.state_manager

    total = await state.count_decisions()
    pending = await state.count_decisions(DecisionState.PENDING)
    reasoning = await state.count_decisions(DecisionState.REASONING)
    completed = await state.count_decisions(DecisionState.COMPLETED)
    failed = await state.count_decisions(DecisionState.FAILED)

    handlers = [
        HandlerInfo(**h) for h in hub.router.registry.list_handlers()
    ]

    return HubStatusResponse(
        status="running",
        total_decisions=total,
        pending=pending,
        reasoning=reasoning,
        completed=completed,
        failed=failed,
        handlers=handlers,
    )


# ------------------------------------------------------------------
# Decisions
# ------------------------------------------------------------------

@router.post(
    "/decisions",
    response_model=SubmitDecisionResponse,
    status_code=202,
    tags=["decisions"],
)
async def submit_decision(
    request: SubmitDecisionRequest,
    hub: DecisionHub = Depends(get_hub),
):
    """Submit a new decision request for AI reasoning."""
    decision_id = await hub.submit(
        title=request.title,
        description=request.description,
        decision_type=request.decision_type,
        priority=request.priority,
        input_data=request.input_data,
        constraints=request.constraints,
        objectives=request.objectives,
        tags=request.tags,
        session_id=request.session_id,
    )
    return SubmitDecisionResponse(decision_id=decision_id)


@router.get(
    "/decisions",
    response_model=ListDecisionsResponse,
    tags=["decisions"],
)
async def list_decisions(
    state: DecisionState | None = Query(default=None),
    decision_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    hub: DecisionHub = Depends(get_hub),
):
    """List decisions with optional filtering."""
    decisions = await hub.list_decisions(
        state=state,
        decision_type=decision_type,
        limit=limit,
        offset=offset,
    )
    total = await hub.state_manager.count_decisions(state=state)
    return ListDecisionsResponse(
        decisions=[_to_response(d) for d in decisions],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/decisions/{decision_id}",
    response_model=DecisionResponse,
    tags=["decisions"],
)
async def get_decision(
    decision_id: str,
    hub: DecisionHub = Depends(get_hub),
):
    """Retrieve a decision by ID."""
    decision = await hub.get_decision(decision_id)
    if decision is None:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id!r} not found")
    return _to_response(decision)


@router.delete(
    "/decisions/{decision_id}",
    status_code=204,
    tags=["decisions"],
)
async def cancel_decision(
    decision_id: str,
    hub: DecisionHub = Depends(get_hub),
):
    """Cancel a pending decision."""
    cancelled = await hub.cancel(decision_id)
    if not cancelled:
        raise HTTPException(
            status_code=409,
            detail="Decision not found or not in a cancellable state",
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _to_response(decision) -> DecisionResponse:
    result_schema = None
    if decision.result:
        r = decision.result
        result_schema = DecisionResultSchema(
            action=r.action,
            reasoning=r.reasoning,
            confidence=r.confidence,
            alternatives=r.alternatives,
            parameters=r.parameters,
            metadata=r.metadata,
        )
    return DecisionResponse(
        id=decision.id,
        title=decision.title,
        description=decision.description,
        type=decision.type,
        state=decision.state,
        priority=decision.priority,
        input_data=decision.input_data,
        constraints=decision.constraints,
        objectives=decision.objectives,
        result=result_schema,
        error=decision.error,
        created_at=decision.created_at,
        updated_at=decision.updated_at,
        completed_at=decision.completed_at,
        tags=decision.tags,
    )
