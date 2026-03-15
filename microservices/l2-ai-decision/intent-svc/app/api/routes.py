"""
API route definitions for ILbuy Intent Service.

Endpoints:
  POST /intent/recognize        → IntentRecognizeResponse (rule-based)
  POST /intent/recognize/smart  → IntentRecognizeResponse (LLM fallback on low confidence)
  POST /entity/extract          → EntityExtractResponse
  POST /brand/detect            → BrandDetectResponse
  GET  /health                  → HealthResponse
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.api.deps import get_brand_detector, get_entity_extractor, get_intent_recognizer
from app.core.config import get_settings
from app.models.schemas import (
    BrandDetectRequest,
    BrandDetectResponse,
    EntityExtractRequest,
    EntityExtractResponse,
    IntentRecognizeRequest,
    IntentRecognizeResponse,
)
from app.services.brand_detector import BrandDetector
from app.services.entity_extractor import EntityExtractor
from app.services.intent_recognizer import IntentRecognizer

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    summary="Health check",
    response_description="Service liveness and readiness status",
    tags=["Operations"],
)
async def health_check() -> dict[str, Any]:
    """
    Returns service health status.

    Used by Kubernetes liveness and readiness probes.
    """
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": settings.version,
        "env": settings.env,
    }


# ---------------------------------------------------------------------------
# Intent Recognition
# ---------------------------------------------------------------------------


@router.post(
    "/intent/recognize",
    response_model=IntentRecognizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Recognize intent from Chinese text",
    response_description="Primary intent, confidence score, and top-3 secondary intents",
    tags=["Intent"],
)
async def recognize_intent(
    request: Request,
    body: IntentRecognizeRequest,
    recognizer: IntentRecognizer = Depends(get_intent_recognizer),
) -> IntentRecognizeResponse:
    """
    Analyse Chinese e-commerce user text and return the most likely purchase intent.

    - **text**: User utterance in Chinese (up to 2000 characters).
    - **context**: Optional dict with conversation context (e.g. `previous_intent`).
    - **session_id**: Optional session identifier echoed back in the response.

    Returns the primary `intent`, a `confidence` score in [0, 1], and up to three
    secondary (`sub_intents`) candidates sorted by descending confidence.
    """
    start_ts = time.perf_counter()
    try:
        result = recognizer.recognize(
            text=body.text,
            context=body.context,
            session_id=body.session_id,
        )
    except Exception as exc:
        logger.exception("Intent recognition failed for session_id=%s", body.session_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent recognition error: {exc}",
        ) from exc

    elapsed_ms = (time.perf_counter() - start_ts) * 1000
    logger.info(
        "intent_recognize session=%s intent=%s confidence=%.4f latency_ms=%.1f",
        body.session_id,
        result.intent,
        result.confidence,
        elapsed_ms,
    )
    return result


@router.post(
    "/intent/recognize/smart",
    response_model=IntentRecognizeResponse,
    status_code=status.HTTP_200_OK,
    summary="Recognize intent with LLM fallback for low-confidence cases",
    response_description="Intent result, potentially LLM-disambiguated when confidence < 0.55",
    tags=["Intent"],
)
async def recognize_intent_smart(
    request: Request,
    body: IntentRecognizeRequest,
    recognizer: IntentRecognizer = Depends(get_intent_recognizer),
) -> IntentRecognizeResponse:
    """
    Layered intent recognition: rule-based first, then LLM disambiguation
    when calibrated confidence falls below the 0.55 threshold.

    Use this endpoint for user-facing flows where accuracy matters most.
    Use `/intent/recognize` for bulk/offline processing where latency is critical.
    """
    start_ts = time.perf_counter()
    try:
        result = await recognizer.recognize_with_llm_fallback(
            text=body.text,
            llm_svc_url=settings.llm_svc_url,
            context=body.context,
            session_id=body.session_id,
        )
    except Exception as exc:
        logger.exception(
            "Smart intent recognition failed for session_id=%s", body.session_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent recognition error: {exc}",
        ) from exc

    elapsed_ms = (time.perf_counter() - start_ts) * 1000
    logger.info(
        "intent_recognize_smart session=%s intent=%s confidence=%.4f latency_ms=%.1f",
        body.session_id,
        result.intent,
        result.confidence,
        elapsed_ms,
    )
    return result


# ---------------------------------------------------------------------------
# Entity Extraction
# ---------------------------------------------------------------------------


@router.post(
    "/entity/extract",
    response_model=EntityExtractResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured entities from Chinese shopping text",
    response_description="Structured entities and raw entity spans",
    tags=["Entity"],
)
async def extract_entities(
    request: Request,
    body: EntityExtractRequest,
    extractor: EntityExtractor = Depends(get_entity_extractor),
) -> EntityExtractResponse:
    """
    Extract structured product/shopping entities from Chinese text.

    Entities extracted include:
    - **brand**: e.g. `小米`, `华为`
    - **model**: e.g. `Mate60 Pro`, `iPhone 15`
    - **budget_min** / **budget_max**: budget bounds in CNY
    - **category**: e.g. `手机`, `冰箱`
    - **specs**: dict of spec key-values (ram, storage, screen_size, …)
    - **quantity**: integer unit count
    - **delivery_time**: requested delivery window
    """
    start_ts = time.perf_counter()
    try:
        result = extractor.extract(text=body.text, intent=body.intent)
    except Exception as exc:
        logger.exception("Entity extraction failed for text='%s'", body.text[:80])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Entity extraction error: {exc}",
        ) from exc

    elapsed_ms = (time.perf_counter() - start_ts) * 1000
    logger.info(
        "entity_extract brand=%s category=%s latency_ms=%.1f",
        result.entities.brand,
        result.entities.category,
        elapsed_ms,
    )
    return result


# ---------------------------------------------------------------------------
# Brand Detection
# ---------------------------------------------------------------------------


@router.post(
    "/brand/detect",
    response_model=BrandDetectResponse,
    status_code=status.HTTP_200_OK,
    summary="Classify user brand knowledge (KNOWN / PARTIAL / UNKNOWN)",
    response_description="Brand status, detected brand name, confidence, and reasoning",
    tags=["Brand"],
)
async def detect_brand(
    request: Request,
    body: BrandDetectRequest,
    detector: BrandDetector = Depends(get_brand_detector),
) -> BrandDetectResponse:
    """
    Determine whether the user has a specific brand/model in mind.

    | Status    | Meaning                                              |
    |-----------|------------------------------------------------------|
    | `KNOWN`   | User named a brand **and** a model number            |
    | `PARTIAL` | Brand mentioned but no specific model                |
    | `UNKNOWN` | No brand preference; user is seeking a recommendation|

    Pass pre-extracted `entities` from `/entity/extract` for best accuracy.
    """
    start_ts = time.perf_counter()
    try:
        result = detector.detect(text=body.text, entities=body.entities)
    except Exception as exc:
        logger.exception("Brand detection failed for text='%s'", body.text[:80])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Brand detection error: {exc}",
        ) from exc

    elapsed_ms = (time.perf_counter() - start_ts) * 1000
    logger.info(
        "brand_detect status=%s brand=%s confidence=%.4f latency_ms=%.1f",
        result.brand_status,
        result.brand_name,
        result.confidence,
        elapsed_ms,
    )
    return result


# ---------------------------------------------------------------------------
# Custom exception handlers (registered on app, exported for use in main.py)
# ---------------------------------------------------------------------------


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a structured 422 for Pydantic validation errors."""
    from fastapi.exceptions import RequestValidationError

    if isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation error",
                "detail": exc.errors(),
                "body": exc.body,
            },
        )
    raise exc
