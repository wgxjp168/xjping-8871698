"""
意图识别服务 (Intent Recognition Service)
L2-AI决策中枢 - Port: 8010
功能: NLP意图识别、实体提取、品牌检测、参数提取
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.api.v1 import intent_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化模型
    print(f"[{settings.APP_NAME}] 加载NLP模型...")
    yield
    print(f"[{settings.APP_NAME}] 服务关闭")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI采购决策平台 - 意图识别服务",
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

# 注册异常处理器
register_exception_handlers(app)

# 注册路由
app.include_router(intent_router, prefix="/api/v1/intent", tags=["意图识别"])


@app.get("/health", tags=["健康检查"])
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
