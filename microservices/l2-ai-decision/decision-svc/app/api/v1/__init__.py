"""
决策编排服务 API 路由 v1
"""
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse

from app.models.request import DecisionRequest, ClarificationRequest
from app.models.response import DecisionResponse
from app.service.decision_orchestrator import decision_orchestrator

decision_router = APIRouter()


@decision_router.post(
    "/analyze",
    response_model=DecisionResponse,
    summary="采购决策分析",
    description="""
提交采购需求，获取 AI 决策报告。

**决策流程**:
1. 意图识别（B2B/B2C，品牌状态，商品类别，结构化参数）
2. 多平台商品数据采集
3. 三维度评分引擎排序（品质/性价比/不推荐）
4. 大模型生成采购决策报告

**返回状态**:
- `success` — 完整决策报告
- `need_clarification` — 需要追问，返回追问问题列表
- `error` — 决策失败
""",
)
async def analyze(request: DecisionRequest) -> DecisionResponse:
    return await decision_orchestrator.decide(request)


@decision_router.post(
    "/clarify",
    response_model=DecisionResponse,
    summary="追问后决策",
    description="用户回答追问后，补充信息并重新发起决策",
)
async def clarify(request: ClarificationRequest) -> DecisionResponse:
    return await decision_orchestrator.decide_with_clarification(request)


@decision_router.get(
    "/capabilities",
    summary="服务能力信息",
    description="返回当前 L2 决策中枢支持的评分模型、平台、状态等信息",
)
async def capabilities():
    return {
        "service": "ilbuy-decision-svc",
        "version": "1.0.0",
        "layer": "L2-AI决策中枢",
        "scoring_models": {
            "B2B": {
                "description": "企业采购评分模型",
                "dimensions": ["供应商资质(30%)", "信用等级(25%)", "店龄(20%)", "认证资质(15%)", "价格竞争力(10%)"],
            },
            "B2C_BRAND": {
                "description": "B2C已定品牌评分模型",
                "dimensions": ["正品保障(35%)", "销量(20%)", "质量(20%)", "服务(15%)", "用户评价(10%)"],
            },
            "B2C_NO_BRAND": {
                "description": "B2C未定品牌评分模型",
                "dimensions": ["参数匹配(25%)", "质量(20%)", "销量(20%)", "服务(15%)", "用户评价(10%)", "店铺资历(10%)"],
            },
        },
        "supported_platforms": ["京东", "天猫", "淘宝", "拼多多", "1688", "唯品会", "苏宁"],
        "llm_providers": ["OpenAI GPT-4", "Claude", "文心一言"],
        "decision_pipeline": [
            "1. 多模态意图识别",
            "2. B2B/B2C用户分类",
            "3. 品牌状态检测",
            "4. 结构化参数提取",
            "5. 多平台数据采集",
            "6. 三模型评分引擎",
            "7. 品质款/性价比款双轨推荐",
            "8. 大模型报告生成",
        ],
    }
