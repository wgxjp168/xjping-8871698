"""
FastAPI application entry point for decision-svc.
"""
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

import uuid

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import router
from app.core.config import settings

# --------------------------------------------------------------------------- #
# Logging setup
# --------------------------------------------------------------------------- #

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("decision-svc")


# --------------------------------------------------------------------------- #
# Lifespan: initialise and tear down long-lived resources
# --------------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — run startup logic, then tear down on shutdown."""
    logger.info(
        "Starting decision-svc | env=%s | port=%d", settings.env, settings.port
    )
    logger.info("Intent SVC     : %s", settings.intent_svc_url)
    logger.info("LLM SVC        : %s", settings.llm_svc_url)
    logger.info("L3 Data SVC    : %s", settings.l3_data_svc_url)
    logger.info("L3 Product SVC : %s", settings.l3_product_svc_url)

    # Pre-import scorer singletons to trigger any lazy initialisation
    from app.services.scoring.b2b_scorer import b2b_scorer  # noqa: F401
    from app.services.scoring.b2c_known_scorer import b2c_known_scorer  # noqa: F401
    from app.services.scoring.b2c_unknown_scorer import b2c_unknown_scorer  # noqa: F401
    from app.services.rule_engine import rule_engine  # noqa: F401
    from app.services.decision_engine import decision_engine  # noqa: F401
    from app.services.report_generator import report_generator  # noqa: F401
    from app.services.explainability import explainability_engine  # noqa: F401
    from app.services.dual_recommendation import dual_recommendation_engine  # noqa: F401

    logger.info("All engines initialised — service ready")
    yield
    logger.info("decision-svc shutting down")


# --------------------------------------------------------------------------- #
# Application factory
# --------------------------------------------------------------------------- #

def create_app() -> FastAPI:
    app = FastAPI(
        title="ILbuy L2 AI Decision Hub — decision-svc",
        description=(
            "Purchase-decision microservice providing 8-step AI analysis, "
            "Drools-inspired rule evaluation, and multi-context scoring models "
            "for B2B, B2C Known-Brand, and B2C Unknown-Brand scenarios."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Trace-ID middleware ──────────────────────────────────────────────────
    # Reads X-Trace-ID from upstream (e.g. L1 API Gateway) and echoes it back
    # in every response.  Generates a new UUID when the header is absent.

    @app.middleware("http")
    async def trace_id_middleware(request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID") or uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(router)

    return app


app = create_app()


# --------------------------------------------------------------------------- #
# Direct execution
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=(settings.env == "development"),
        log_level=settings.log_level.lower(),
    )
