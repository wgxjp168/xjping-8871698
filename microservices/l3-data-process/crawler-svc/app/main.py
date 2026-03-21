"""
crawler-svc — FastAPI application entry point
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.routes import router
from app.services.api_manager import api_manager
from app.services.compliance_monitor import compliance_monitor
from app.services.proxy_manager import proxy_manager
from app.services.scheduler import crawl_scheduler

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    logger.info('"crawler-svc starting up — env=%s port=%d"', settings.env, settings.port)
    await api_manager.start()
    await proxy_manager.start()
    crawl_scheduler.start()
    logger.info('"crawler-svc ready"')
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info('"crawler-svc shutting down"')
    crawl_scheduler.stop()
    await proxy_manager.stop()
    await api_manager.stop()


app = FastAPI(
    title="ILbuy Crawler Service",
    description=(
        "L3 数据采集服务 — 封装7大电商平台API，提供按需/定时采集、"
        "代理IP管理、合规监控。上游：L2 decision-svc；下游：etl-svc。"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-ID") or uuid.uuid4().hex
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    return response


app.include_router(router)
