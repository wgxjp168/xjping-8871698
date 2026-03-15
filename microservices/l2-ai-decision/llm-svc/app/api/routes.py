"""
FastAPI router for all LLM service endpoints.

Routes:
  POST /llm/chat                – general multi-turn chat
  POST /llm/analyze/product     – structured product analysis
  POST /llm/analyze/decision    – decision-support context generation
  POST /llm/report/generate     – procurement report generation
  GET  /llm/providers           – list providers and their availability
  GET  /health                  – liveness probe
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import (
    ChatMessage,
    DecisionSupportRequest,
    DecisionSupportResponse,
    LLMChatRequest,
    LLMChatResponse,
    ProductAnalysisRequest,
    ProductAnalysisResponse,
    ReportGenerationRequest,
    ReportGenerationResponse,
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
    """Return availability status and model info for every configured provider."""
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
# Product analysis
# ---------------------------------------------------------------------------


@router.post(
    "/llm/analyze/product",
    response_model=ProductAnalysisResponse,
    summary="AI-powered product analysis against buyer requirements",
    tags=["analysis"],
)
async def analyze_product(request: ProductAnalysisRequest) -> ProductAnalysisResponse:
    """
    Analyse a product description against structured buyer requirements and
    return a comprehensive evaluation with match score and recommendation.
    """
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
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
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
    """
    Generate decision-support context, clarifying questions, confidence
    factors, and a preliminary recommendation based on parsed user intent
    and entities.
    """
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
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
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
    import time

    messages: list[ChatMessage] = prompt_builder.build_report_generation_prompt(
        decision_data=request.decision_data,
        scoring_result=request.scoring_result,
    )

    # Reports warrant higher token budgets and slightly lower temperature
    chat_request = LLMChatRequest(
        messages=messages,
        max_tokens=4096,
        temperature=0.2,
        context_type="report_generation",
    )

    start = time.monotonic()
    try:
        llm_response = await llm_client.chat(chat_request)
    except RuntimeError as exc:
        logger.error("Report generation LLM call failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    latency_ms = round((time.monotonic() - start) * 1000, 2)
    return ReportGenerationResponse(
        report=response_parser.clean_response(llm_response.content),
        provider=llm_response.provider,
        model=llm_response.model,
        latency_ms=latency_ms,
    )
