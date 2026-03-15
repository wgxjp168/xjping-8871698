"""
ILbuy Intent Service — FastAPI application entry point.

Startup sequence:
1. Configure structured logging.
2. Pre-warm all NLP service singletons (IntentRecognizer, EntityExtractor, BrandDetector).
3. Register CORS middleware.
4. Mount API router.
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.deps import (
    get_brand_detector,
    get_entity_extractor,
    get_intent_recognizer,
)
from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------


def configure_logging() -> None:
    """Configure root logger with structured formatting."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ("transformers", "torch", "jieba"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


configure_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan context manager — model warm-up on startup
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    On startup:  Pre-initialise all NLP singletons so the first request
                 is not penalised with cold-start latency.
    On shutdown: Clean up resources (logging only for now).
    """
    startup_start = time.perf_counter()
    logger.info(
        "Starting %s v%s (env=%s, port=%d) …",
        settings.service_name,
        settings.version,
        settings.env,
        settings.port,
    )

    try:
        logger.info("Warming up IntentRecognizer …")
        recognizer = get_intent_recognizer()
        logger.info("IntentRecognizer ready.")

        logger.info("Warming up EntityExtractor …")
        extractor = get_entity_extractor()
        logger.info("EntityExtractor ready.")

        logger.info("Warming up BrandDetector …")
        detector = get_brand_detector()
        logger.info("BrandDetector ready.")

        elapsed = (time.perf_counter() - startup_start) * 1000
        logger.info("All NLP services initialised in %.0f ms.", elapsed)

    except Exception:
        logger.exception("Failed to initialise NLP services during startup.")
        raise

    yield  # Application runs here

    logger.info("Shutting down %s …", settings.service_name)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------


app = FastAPI(
    title="ILbuy Intent Service",
    description=(
        "Microservice for Chinese e-commerce intent recognition, "
        "entity extraction, and brand preference detection. "
        "Part of the ILbuy L2 AI Decision Hub."
    ),
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next: Any) -> Any:
    """Log method, path, and response time for every request."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %d  (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return 422 with structured error detail."""
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return 500 for unhandled exceptions."""
    logger.exception("Unhandled exception on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


app.include_router(router, prefix="")


# ---------------------------------------------------------------------------
# Entrypoint (for local development: python -m app.main)
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.is_development,
    )
