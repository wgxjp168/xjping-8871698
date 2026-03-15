"""FastAPI application factory for the L2 Decision Hub."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from l2_decision_hub.api.routes import router, set_hub
from l2_decision_hub.config import settings
from l2_decision_hub.core.engine import DecisionHub

logger = logging.getLogger(__name__)


def create_app(hub: DecisionHub | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        hub: An existing DecisionHub instance. If None, a new one is created
             from settings on startup.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if hub is not None:
            instance = hub
        else:
            instance = DecisionHub(
                api_key=settings.anthropic_api_key or None,
                model=settings.claude_model,
                max_concurrent=settings.hub_max_concurrent,
                auto_execute=settings.hub_auto_execute,
            )
        set_hub(instance)
        await instance.start()
        logger.info("L2-AI Decision Hub API started")
        yield
        await instance.stop()
        logger.info("L2-AI Decision Hub API stopped")

    app = FastAPI(
        title="L2-AI Decision Hub",
        description=(
            "Core AI decision-making engine powered by Claude. "
            "Submit decisions, track their lifecycle, and retrieve AI-generated recommendations."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")

    return app
