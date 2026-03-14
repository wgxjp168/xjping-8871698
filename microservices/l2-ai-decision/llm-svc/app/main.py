"""
大模型调用服务 (LLM Service)
L2-AI决策中枢 - Port: 8011
功能: 封装OpenAI/Claude/文心一言，统一调用接口，支持流式输出
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.api.v1 import llm_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[{settings.APP_NAME}] 初始化LLM客户端...")
    yield
    print(f"[{settings.APP_NAME}] 服务关闭")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI采购决策平台 - 大模型统一调用服务",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(llm_router, prefix="/api/v1/llm", tags=["大模型调用"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
