"""
FastAPI application entry point for llm-svc.

Lifecycle:
  startup  – log configuration, validate at least one LLM provider is ready
  shutdown – graceful cleanup (client sessions closed by GC/async context managers)
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.services.llm_client import llm_client

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG if settings.env == "development" else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
    # ---- startup ----
    logger.info(
        "llm-svc starting (env=%s, port=%d, primary_provider=%s)",
        settings.env,
        settings.port,
        settings.llm_provider,
    )

    statuses = llm_client.get_provider_statuses()
    available_providers = [
        name for name, info in statuses.items() if info["available"]
    ]

    if not available_providers:
        logger.warning(
            "No LLM providers are available – all API keys may be missing. "
            "Service will start but every chat request will fail."
        )
    else:
        logger.info("Available LLM providers: %s", available_providers)

    yield

    # ---- shutdown ----
    logger.info("llm-svc shutting down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title="ILbuy LLM Service",
        description=(
            "Unified LLM gateway for the ILbuy L2 AI Decision Hub. "
            "Supports OpenAI, Anthropic, and Baidu Wenxin providers with "
            "automatic fallback, retry logic, and structured response parsing."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Trace-ID middleware
    # ------------------------------------------------------------------
    @app.middleware("http")
    async def trace_id_middleware(request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID") or uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    app.include_router(router)

    return app


app = create_app()
