"""
大模型调用服务 API 路由 v1
"""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.models.request import (
    CompletionRequest, CompletionResponse,
    ReportRequest, ReportResponse,
)
from app.service.llm_service import LLMRequest, LLMProvider, llm_service
from app.core.config import settings

llm_router = APIRouter()


@llm_router.post(
    "/complete",
    response_model=CompletionResponse,
    summary="通用大模型补全",
    description="通用文本补全接口，支持 OpenAI / Claude / 文心一言",
)
async def complete(request: CompletionRequest) -> CompletionResponse:
    llm_req = LLMRequest(
        prompt=request.prompt,
        system_prompt=request.system_prompt,
        provider=LLMProvider(request.provider) if request.provider else None,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    content = await llm_service.complete(llm_req)
    return CompletionResponse(
        content=content,
        provider=llm_req.provider.value,
        model=_get_model_name(llm_req.provider),
    )


@llm_router.post(
    "/report",
    response_model=ReportResponse,
    summary="采购决策报告生成",
    description=(
        "根据意图分析结果和评分商品数据，生成结构化采购决策报告（Markdown格式）。\n\n"
        "由 `decision-svc` 内部调用，也可直接调用用于测试。"
    ),
)
async def generate_report(request: ReportRequest) -> ReportResponse:
    provider = LLMProvider(request.provider) if request.provider else None
    report = await llm_service.generate_purchase_report(
        user_type=request.user_type,
        brand_status=request.brand_status,
        product_category=request.product_category,
        products_data=request.products_data,
        user_requirements=request.user_requirements,
    )
    actual_provider = (provider or LLMProvider(settings.DEFAULT_PROVIDER)).value
    return ReportResponse(report=report, provider=actual_provider)


@llm_router.post(
    "/stream",
    summary="流式补全（SSE）",
    description="流式输出，适合实时展示长文本生成过程",
)
async def stream_complete(request: CompletionRequest):
    llm_req = LLMRequest(
        prompt=request.prompt,
        system_prompt=request.system_prompt,
        provider=LLMProvider(request.provider) if request.provider else None,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        stream=True,
    )

    async def event_generator():
        async for chunk in llm_service.stream_complete(llm_req):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@llm_router.get(
    "/providers",
    summary="可用模型提供商",
)
async def list_providers():
    return {
        "default": settings.DEFAULT_PROVIDER,
        "providers": {
            "openai": {
                "available": bool(settings.OPENAI_API_KEY),
                "model": settings.OPENAI_MODEL,
            },
            "claude": {
                "available": bool(settings.ANTHROPIC_API_KEY),
                "model": settings.CLAUDE_MODEL,
            },
            "ernie": {
                "available": bool(settings.ERNIE_API_KEY),
                "model": "ernie-bot-4",
            },
        },
    }


def _get_model_name(provider: LLMProvider) -> str:
    if provider == LLMProvider.OPENAI:
        return settings.OPENAI_MODEL
    if provider == LLMProvider.CLAUDE:
        return settings.CLAUDE_MODEL
    return "ernie-bot-4"
