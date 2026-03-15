"""
AI决策编排服务 (Decision Orchestration Service)
L2-AI决策中枢 - Port: 8012

职责：串联意图识别、数据采集、评分引擎、LLM报告，提供统一决策入口。
"""

import logging
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import decision_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[%s] 服务启动，端口 %d", settings.APP_NAME, settings.PORT)
    logger.info("[%s] intent-svc => %s", settings.APP_NAME, settings.INTENT_SVC_URL)
    logger.info("[%s] llm-svc   => %s", settings.APP_NAME, settings.LLM_SVC_URL)
    yield
    logger.info("[%s] 服务关闭", settings.APP_NAME)


app = FastAPI(
    title="ILbuy AI Decision Service",
    description=(
        "**我来购(ILbuy) L2-AI决策中枢**\n\n"
        "负责将用户的自然语言采购需求转化为结构化的AI决策报告。\n\n"
        "**核心流程**: 意图识别 → 数据采集 → 评分排序 → 报告生成"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 异常处理
register_exception_handlers(app)

# 路由
app.include_router(decision_router, prefix="/api/v1/decision", tags=["决策编排"])


@app.get("/health", tags=["健康检查"])
async def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "layer": "L2-AI决策中枢",
        "dependencies": {
            "intent_svc": settings.INTENT_SVC_URL,
            "llm_svc": settings.LLM_SVC_URL,
        },
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
