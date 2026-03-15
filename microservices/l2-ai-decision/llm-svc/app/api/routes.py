"""
FastAPI router for all LLM service endpoints.

Routes:
  POST /llm/chat                    – general multi-turn chat
  POST /llm/chat/stream             – SSE streaming chat (Anthropic native, others full-content)
  POST /llm/analyze/product         – structured product analysis
  POST /llm/analyze/decision        – decision-support context generation
  POST /llm/analyze/scoring         – LLM-enhanced scoring dimension insights
  POST /llm/intent/disambiguate     – resolve low-confidence intent via LLM
  POST /llm/report/generate         – procurement report generation
  GET  /llm/providers               – list providers and their availability
  GET  /health                      – liveness probe
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    ChatMessage,
    DecisionSupportRequest,
    DecisionSupportResponse,
    DimensionInsight,
    IntentCandidate,
    IntentDisambiguationRequest,
    IntentDisambiguationResponse,
    LLMChatRequest,
    LLMChatResponse,
    ProductAnalysisRequest,
    ProductAnalysisResponse,
    ReportGenerationRequest,
    ReportGenerationResponse,
    ScoringInsightRequest,
    ScoringInsightResponse,
)
from app.services.llm_client import llm_client
from app.services.prompt_builder import PromptBuilder
from app.services.response_parser import ResponseParser

logger = logging.getLogger(__name__)

router = APIRouter()
prompt_builder = PromptBuilder()
response_parser = ResponseParser()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/health", summary="Liveness probe", tags=["ops"])
async def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": "llm-svc"}


# ---------------------------------------------------------------------------
# Provider info
# ---------------------------------------------------------------------------


@router.get(
    "/llm/providers",
    summary="List available LLM providers",
    tags=["providers"],
)
async def list_providers() -> Dict[str, Any]:
    """Return availability status, model info, and thinking support for every provider."""
    statuses = llm_client.get_provider_statuses()
    return {"providers": statuses}


# ---------------------------------------------------------------------------
# General chat
# ---------------------------------------------------------------------------


@router.post(
    "/llm/chat",
    response_model=LLMChatResponse,
    summary="General multi-turn LLM chat",
    tags=["chat"],
)
async def chat(request: LLMChatRequest) -> LLMChatResponse:
    """
    Send a conversation to the configured LLM provider and return the
    assistant's reply with usage statistics and latency.

    Set enable_thinking=true to activate adaptive thinking on supported
    Anthropic models (claude-opus-4-6, claude-sonnet-4-6).
    """
    try:
        return await llm_client.chat(request)
    except RuntimeError as exc:
        logger.error("Chat request failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in /llm/chat")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal LLM service error",
        ) from exc


# ---------------------------------------------------------------------------
# Streaming chat (SSE)
# ---------------------------------------------------------------------------


@router.post(
    "/llm/chat/stream",
    summary="Streaming LLM chat (SSE)",
    tags=["chat"],
)
async def chat_stream(request: LLMChatRequest) -> StreamingResponse:
    """
    Stream LLM response tokens as Server-Sent Events.

    Each event is a JSON object: {"token": "..."}.
    A final event {"done": true} signals completion.

    Anthropic (claude-opus-4-6/sonnet-4-6) streams real token deltas.
    OpenAI and Wenxin return the full content as a single SSE event.
    """
    async def event_generator():
        try:
            async for token in llm_client.stream_chat(request):
                payload = json.dumps({"token": token}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            yield 'data: {"done": true}\n\n'
        except Exception as exc:  # noqa: BLE001
            logger.error("Stream error: %s", exc)
            err = json.dumps({"error": str(exc)}, ensure_ascii=False)
            yield f"data: {err}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Product analysis
# ---------------------------------------------------------------------------


@router.post(
    "/llm/analyze/product",
    response_model=ProductAnalysisResponse,
    summary="AI-powered product analysis against buyer requirements",
    tags=["analysis"],
)
async def analyze_product(request: ProductAnalysisRequest) -> ProductAnalysisResponse:
    messages: list[ChatMessage] = prompt_builder.build_product_analysis_prompt(
        product_desc=request.product_description,
        requirements=request.user_requirements,
        budget=request.budget_range,
    )
    chat_request = LLMChatRequest(
        messages=messages,
        max_tokens=2048,
        temperature=0.3,
        context_type="product_analysis",
    )
    try:
        llm_response = await llm_client.chat(chat_request)
    except RuntimeError as exc:
        logger.error("Product analysis LLM call failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    try:
        return response_parser.parse_product_analysis(llm_response.content)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to parse product analysis response: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse LLM response for product analysis",
        ) from exc


# ---------------------------------------------------------------------------
# Decision support
# ---------------------------------------------------------------------------


@router.post(
    "/llm/analyze/decision",
    response_model=DecisionSupportResponse,
    summary="AI decision-support context generation",
    tags=["analysis"],
)
async def analyze_decision(request: DecisionSupportRequest) -> DecisionSupportResponse:
    messages: list[ChatMessage] = prompt_builder.build_decision_support_prompt(
        intent=request.intent,
        entities=request.entities,
        brand_status=request.brand_status,
        context=request.user_context,
    )
    chat_request = LLMChatRequest(
        messages=messages,
        max_tokens=1536,
        temperature=0.4,
        context_type="decision_support",
    )
    try:
        llm_response = await llm_client.chat(chat_request)
    except RuntimeError as exc:
        logger.error("Decision support LLM call failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    try:
        return response_parser.parse_decision_support(llm_response.content)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to parse decision support response: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse LLM response for decision support",
        ) from exc


# ---------------------------------------------------------------------------
# Scoring insight  (NEW)
# LLM evaluates qualitative dimension signals for the rule-based scorer.
# ---------------------------------------------------------------------------


@router.post(
    "/llm/analyze/scoring",
    response_model=ScoringInsightResponse,
    summary="LLM-enhanced scoring dimension insights",
    tags=["analysis"],
)
async def analyze_scoring(request: ScoringInsightRequest) -> ScoringInsightResponse:
    """
    Ask the LLM to evaluate scoring dimensions that rule-based models may
    miss (brand sentiment, market trends, compliance nuances).

    Returns per-dimension adjustment suggestions and an overall assessment.
    Use enable_thinking=true for complex B2B scenarios.
    """
    messages: list[ChatMessage] = prompt_builder.build_scoring_insight_prompt(
        scoring_context=request.scoring_context,
        intent=request.intent,
        entities=request.entities,
        dimension_scores=request.dimension_scores,
        enriched_context=request.enriched_context,
    )
    chat_request = LLMChatRequest(
        messages=messages,
        max_tokens=2048,
        temperature=0.2,
        enable_thinking=True,   # always use adaptive thinking for scoring
        provider=request.provider,
        context_type="scoring_insight",
    )

    start = time.monotonic()
    try:
        llm_response = await llm_client.chat(chat_request)
    except RuntimeError as exc:
        logger.error("Scoring insight LLM call failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    latency_ms = round((time.monotonic() - start) * 1000, 2)

    # Parse structured response
    try:
        raw = response_parser.clean_response(llm_response.content)
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to parse scoring insight JSON: %s | content=%s",
                     exc, llm_response.content[:300])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse LLM scoring insight response",
        ) from exc

    # Build typed response
    try:
        dimension_insights = [
            DimensionInsight(**di) for di in data.get("dimension_insights", [])
        ]
        # Compute adjusted total: baseline + weighted LLM adjustments
        adjusted_total = float(data.get("adjusted_total", 0.0))
        if not adjusted_total and request.dimension_scores:
            # Fallback: apply adjustments to dimension scores manually
            base = sum(request.dimension_scores.values()) / max(
                len(request.dimension_scores), 1
            )
            adj = sum(di.adjustment for di in dimension_insights)
            adjusted_total = max(0.0, min(100.0, base + adj))

        return ScoringInsightResponse(
            dimension_insights=dimension_insights,
            risk_signals=data.get("risk_signals", []),
            opportunity_signals=data.get("opportunity_signals", []),
            overall_assessment=data.get("overall_assessment", ""),
            adjusted_total=round(adjusted_total, 2),
            provider=llm_response.provider,
            model=llm_response.model,
            latency_ms=latency_ms,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to build ScoringInsightResponse: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to structure scoring insight response",
        ) from exc


# ---------------------------------------------------------------------------
# Intent disambiguation  (NEW)
# Resolves low-confidence intent via LLM when rule engine is uncertain.
# ---------------------------------------------------------------------------


@router.post(
    "/llm/intent/disambiguate",
    response_model=IntentDisambiguationResponse,
    summary="LLM-based intent disambiguation for low-confidence cases",
    tags=["intent"],
)
async def disambiguate_intent(
    request: IntentDisambiguationRequest,
) -> IntentDisambiguationResponse:
    """
    When the rule-based intent recognizer confidence is below threshold
    (typically < 0.55), this endpoint asks the LLM to select the correct
    intent from the provided candidates using conversation context.

    Returns the disambiguated intent with a calibrated confidence score.
    """
    candidates_dicts = [c.model_dump() for c in request.candidates]
    messages: list[ChatMessage] = prompt_builder.build_intent_disambiguation_prompt(
        text=request.text,
        candidates=candidates_dicts,
        context=request.context,
    )
    chat_request = LLMChatRequest(
        messages=messages,
        max_tokens=512,
        temperature=0.1,    # low temperature for deterministic disambiguation
        provider=request.provider,
        context_type="intent_disambiguation",
    )

    start = time.monotonic()
    try:
        llm_response = await llm_client.chat(chat_request)
    except RuntimeError as exc:
        logger.error("Intent disambiguation LLM call failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    latency_ms = round((time.monotonic() - start) * 1000, 2)

    try:
        raw = response_parser.clean_response(llm_response.content)
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to parse disambiguation JSON: %s", exc)
        # Graceful degradation: return the highest-confidence candidate
        top = request.candidates[0] if request.candidates else None
        return IntentDisambiguationResponse(
            intent=top.intent if top else "OTHER",
            confidence=top.confidence if top else 0.3,
            rationale="LLM解析失败，回退至规则引擎最高置信候选。",
            sub_intents=[],
            provider=llm_response.provider,
            latency_ms=latency_ms,
        )

    sub_intents = [
        IntentCandidate(**si) for si in data.get("sub_intents", [])
    ]
    return IntentDisambiguationResponse(
        intent=data.get("intent", "OTHER"),
        confidence=float(data.get("confidence", 0.5)),
        rationale=data.get("rationale", ""),
        sub_intents=sub_intents,
        provider=llm_response.provider,
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


@router.post(
    "/llm/report/generate",
    response_model=ReportGenerationResponse,
    summary="Generate a procurement decision report",
    tags=["report"],
)
async def generate_report(request: ReportGenerationRequest) -> ReportGenerationResponse:
    """
    Generate a structured procurement decision report from aggregated
    decision data and scoring results.  Returns raw markdown report text.
    """
    messages: list[ChatMessage] = prompt_builder.build_report_generation_prompt(
        decision_data=request.decision_data,
        scoring_result=request.scoring_result,
    )
    # Reports warrant higher token budgets and slightly lower temperature
    chat_request = LLMChatRequest(
        messages=messages,
        max_tokens=4096,
        temperature=0.2,
        enable_thinking=True,   # deep reasoning for comprehensive reports
        context_type="report_generation",
    )

    start = time.monotonic()
    try:
        llm_response = await llm_client.chat(chat_request)
    except RuntimeError as exc:
        logger.error("Report generation LLM call failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc

    latency_ms = round((time.monotonic() - start) * 1000, 2)
    return ReportGenerationResponse(
        report=response_parser.clean_response(llm_response.content),
        provider=llm_response.provider,
        model=llm_response.model,
        latency_ms=latency_ms,
    )
