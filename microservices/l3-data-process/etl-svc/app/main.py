"""etl-svc — FastAPI application entry point."""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.routes import router

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('"etl-svc starting — env=%s port=%d"', settings.env, settings.port)
    yield
    logger.info('"etl-svc shutting down"')


app = FastAPI(
    title="ILbuy ETL Service",
    description=(
        "L3 ETL数据清洗服务 — 接收 crawler-svc 采集数据，"
        "执行清洗/去重/标准化/评分预计算，结果转发至 L4 数据存储层。"
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
