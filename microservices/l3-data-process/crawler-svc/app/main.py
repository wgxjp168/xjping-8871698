"""
数据采集服务 (Crawler Service)
L3-数据采集与处理层 - Port: 8030
功能: 7大电商平台API合规采集，频率控制，代理管理
平台: 淘宝/天猫/京东/拼多多/1688/唯品会/苏宁/抖音
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.api.v1 import crawler_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[{settings.APP_NAME}] 初始化API管理器和代理IP池...")
    yield
    print(f"[{settings.APP_NAME}] 关闭采集服务")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI采购决策平台 - 电商数据采集服务",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
register_exception_handlers(app)
app.include_router(crawler_router, prefix="/api/v1/crawler", tags=["数据采集"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
