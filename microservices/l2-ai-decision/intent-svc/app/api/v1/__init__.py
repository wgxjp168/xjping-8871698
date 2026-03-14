from fastapi import APIRouter
from app.models.request import IntentRequest, IntentResponse
from app.service.intent_service import intent_service

intent_router = APIRouter()


@intent_router.post("/analyze", response_model=IntentResponse, summary="意图分析")
async def analyze_intent(request: IntentRequest):
    """
    多模态意图分析接口

    - 支持文本/图片/链接/语音输入
    - 识别 B2B/B2C 用户类型
    - 检测品牌（已定/未定）
    - 提取结构化参数（材质/尺寸/容量/功率等）
    - 判断是否需要追问
    """
    return await intent_service.analyze(request)


@intent_router.get("/brands", summary="获取已知品牌列表")
async def get_known_brands():
    """获取系统内置品牌库"""
    from app.service.intent_service import KNOWN_BRANDS
    return {"brands": list(KNOWN_BRANDS), "total": len(KNOWN_BRANDS)}
