"""
etl-svc API routes
==================
POST /etl/process         — receive raw products from crawler-svc, run ETL
GET  /etl/stats           — pipeline statistics
GET  /health              — health check
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.core.config import get_settings
from app.models.schemas import (
    ETLRequest, ETLResult, ETLStats, ETLStatus, HealthResponse,
)
from app.services.cleaner import data_cleaner
from app.services.deduplicator import deduplicator
from app.services.normalizer import normalizer
from app.services.scorer import product_scorer

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

_start_time = time.monotonic()

# Lightweight in-process counters (replace with Prometheus in production)
_stats = {
    "total_processed":  0,
    "total_cleaned":    0,
    "total_duplicates": 0,
    "total_invalid":    0,
    "processing_ms_sum": 0.0,
    "job_count":        0,
}


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["ops"])
async def health():
    return HealthResponse(
        status="ok",
        uptime_s=round(time.monotonic() - _start_time, 1),
    )


# ── ETL pipeline ──────────────────────────────────────────────────────────────

@router.post(
    "/etl/process",
    response_model=ETLResult,
    status_code=status.HTTP_200_OK,
    tags=["etl"],
    summary="Run ETL pipeline on raw product batch",
)
async def process_etl(
    request: ETLRequest,
    background_tasks: BackgroundTasks,
) -> ETLResult:
    """
    Receives raw product records from crawler-svc and runs the full ETL:
      1. Clean (validate + sanitise)
      2. Deduplicate (same-platform + cross-platform)
      3. Score (pre-compute ProductScore for each product)
      4. Normalise (produce CleanProduct)
      5. Forward to L4 data-store (async, if configured)
    """
    if len(request.raw_products) > settings.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size {len(request.raw_products)} exceeds max {settings.max_batch_size}",
        )

    t0 = time.monotonic()
    errors = []
    input_count = len(request.raw_products)

    # ── Step 1: Clean ─────────────────────────────────────────────────────
    cleaned, invalid_count = data_cleaner.clean_batch(request.raw_products)

    # ── Step 2: Deduplicate ───────────────────────────────────────────────
    if request.deduplicate:
        unique, dupe_count = deduplicator.deduplicate(cleaned)
    else:
        unique, dupe_count = cleaned, 0

    # ── Step 3: Score ─────────────────────────────────────────────────────
    scores = product_scorer.score_batch(unique) if request.compute_scores else []

    # ── Step 4: Normalise ─────────────────────────────────────────────────
    if request.normalize and scores:
        clean_products = normalizer.normalise_batch(unique, scores)
    else:
        # Minimal normalisation without full scoring
        from app.models.schemas import ProductScore, Grade
        default_score = ProductScore(
            total_score=50.0, grade=Grade.C,
            price_score=50.0, popularity_score=50.0,
            rating_score=50.0, availability_score=50.0,
            value_for_money_score=50.0, data_completeness=0.0,
        )
        clean_products = [normalizer.normalise(p, default_score) for p in unique]

    duration_ms = int((time.monotonic() - t0) * 1000)

    # ── Update counters ───────────────────────────────────────────────────
    _stats["total_processed"]   += input_count
    _stats["total_cleaned"]     += len(unique)
    _stats["total_duplicates"]  += dupe_count
    _stats["total_invalid"]     += invalid_count
    _stats["processing_ms_sum"] += duration_ms
    _stats["job_count"]         += 1

    logger.info(
        '"ETL job=%s: input=%d clean=%d dupes=%d invalid=%d ms=%d"',
        request.job_id[:8], input_count, len(unique), dupe_count, invalid_count, duration_ms,
    )

    result = ETLResult(
        job_id          = request.job_id,
        session_id      = request.session_id,
        status          = ETLStatus.SUCCESS if not errors else ETLStatus.PARTIAL,
        input_count     = input_count,
        output_count    = len(clean_products),
        duplicate_count = dupe_count,
        invalid_count   = invalid_count,
        products        = clean_products,
        processing_ms   = duration_ms,
        errors          = errors,
    )

    # ── Step 5: Forward to L4 (background, non-blocking) ─────────────────
    if settings.l4_ingest_enabled:
        ingest_url = request.l4_ingest_url or f"{settings.l4_data_svc_url}/ingest"
        background_tasks.add_task(_ingest_to_l4, result, ingest_url)

    return result


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/etl/stats", response_model=ETLStats, tags=["ops"])
async def etl_stats() -> ETLStats:
    n = max(_stats["job_count"], 1)
    return ETLStats(
        total_processed  = _stats["total_processed"],
        total_cleaned    = _stats["total_cleaned"],
        total_duplicates = _stats["total_duplicates"],
        total_invalid    = _stats["total_invalid"],
        avg_processing_ms = round(_stats["processing_ms_sum"] / n, 1),
        uptime_s         = round(time.monotonic() - _start_time, 1),
    )


# ── L4 ingestion helper ───────────────────────────────────────────────────────

async def _ingest_to_l4(result: ETLResult, url: str) -> None:
    """
    Background task: POST cleaned products to L4 data-store.
    Interface is pre-reserved; L4 must expose POST /ingest accepting ETLResult.
    """
    payload = {
        "job_id":     result.job_id,
        "session_id": result.session_id,
        "products":   [p.model_dump(mode="json") for p in result.products],
    }
    try:
        async with httpx.AsyncClient(timeout=settings.l4_ingest_timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        logger.info('"L4 ingest success: %d products → %s"', len(result.products), url)
    except Exception as exc:
        logger.error('"L4 ingest failed: %s"', exc)
