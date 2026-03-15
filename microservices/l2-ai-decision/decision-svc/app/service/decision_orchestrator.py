"""
L2 AI决策编排器（Decision Orchestrator）
核心职责：
  1. 调用 intent-svc 解析用户意图
  2. 调用 L3 数据采集层获取候选商品（当前使用桩实现）
  3. 使用评分引擎对商品排序
  4. 调用 llm-svc 生成采购决策报告
  5. 返回结构化决策结果
"""
import time
import logging
import json
from typing import Optional
import httpx

from app.core.config import settings
from app.core.exceptions import IntentServiceError, LLMServiceError
from app.models.request import DecisionRequest, ClarificationRequest
from app.models.response import (
    DecisionResponse, DecisionStatus, IntentSummary,
    ProductRecommendation, RecommendationLevel,
)
from app.service.scoring_service import ScoringService, ScoringModel, ProductData
from app.service.data_mock import get_mock_products

logger = logging.getLogger(__name__)

_scoring_svc = ScoringService()


class DecisionOrchestrator:
    """
    决策编排器：将 intent-svc / 数据采集 / 评分引擎 / llm-svc 串联成完整流水线
    """

    # ------------------------------------------------------------------ #
    # 公开接口
    # ------------------------------------------------------------------ #

    async def decide(self, req: DecisionRequest) -> DecisionResponse:
        """
        主决策流程：
          intent → collect → score → report
        """
        start = time.time()

        # Step 1: 意图分析
        intent_result = await self._call_intent_svc(req)
        if intent_result is None:
            return DecisionResponse(
                session_id=req.session_id,
                user_id=req.user_id,
                status=DecisionStatus.ERROR,
                processing_time_ms=self._elapsed(start),
            )

        intent_summary = self._build_intent_summary(intent_result)

        # Step 2: 如需追问，提前返回
        if intent_result.get("need_clarification"):
            return DecisionResponse(
                session_id=req.session_id,
                user_id=req.user_id,
                status=DecisionStatus.NEED_CLARIFICATION,
                intent=intent_summary,
                clarification_questions=intent_result.get("clarification_questions"),
                processing_time_ms=self._elapsed(start),
            )

        # Step 3: 数据采集（调用 L3 或使用桩实现）
        products_raw: list[ProductData] = await self._collect_products(intent_result)

        # Step 4: 评分排序
        scoring_model = self._choose_scoring_model(intent_result)
        scored = _scoring_svc.score_batch(products_raw, scoring_model)
        top_scored = scored[: settings.REPORT_TOP_N]

        recommendations = [self._to_recommendation(r, products_raw) for r in top_scored]
        quality_pick = next(
            (r for r in recommendations if r.recommendation_level == RecommendationLevel.QUALITY),
            recommendations[0] if recommendations else None,
        )
        value_pick = next(
            (r for r in recommendations if r.recommendation_level == RecommendationLevel.VALUE),
            recommendations[1] if len(recommendations) > 1 else quality_pick,
        )

        # Step 5: LLM 报告生成
        report = await self._generate_report(intent_result, top_scored, products_raw)

        return DecisionResponse(
            session_id=req.session_id,
            user_id=req.user_id,
            status=DecisionStatus.SUCCESS,
            intent=intent_summary,
            recommendations=recommendations,
            quality_pick=quality_pick,
            value_pick=value_pick,
            report=report,
            processing_time_ms=self._elapsed(start),
            data_sources=list({p.platform for p in products_raw}),
        )

    async def decide_with_clarification(self, req: ClarificationRequest) -> DecisionResponse:
        """追问后重新决策：合并原始需求与补充信息"""
        merged_content = f"{req.original_content}。补充信息：{req.answer}"
        new_req = DecisionRequest(
            session_id=req.session_id,
            user_id=req.user_id,
            content=merged_content,
        )
        return await self.decide(new_req)

    # ------------------------------------------------------------------ #
    # 内部方法
    # ------------------------------------------------------------------ #

    async def _call_intent_svc(self, req: DecisionRequest) -> Optional[dict]:
        """调用 intent-svc 进行意图分析"""
        payload = {
            "session_id": req.session_id,
            "user_id": req.user_id,
            "input_mode": req.input_mode,
            "content": req.content,
            "image_url": req.image_url,
            "link_url": req.link_url,
            "history": req.history or [],
        }
        try:
            async with httpx.AsyncClient(timeout=settings.INTENT_SVC_TIMEOUT) as client:
                resp = await client.post(
                    f"{settings.INTENT_SVC_URL}/api/v1/intent/analyze",
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.TimeoutException:
            logger.error("intent-svc 调用超时")
            raise IntentServiceError("意图识别服务响应超时")
        except httpx.HTTPStatusError as e:
            logger.error("intent-svc 返回错误状态: %s", e.response.status_code)
            raise IntentServiceError(f"意图识别服务错误: {e.response.status_code}")
        except Exception as e:
            logger.warning("intent-svc 不可达，使用本地兜底分析: %s", e)
            # 兜底：使用本地简单分析
            return self._fallback_intent_analysis(req)

    def _fallback_intent_analysis(self, req: DecisionRequest) -> dict:
        """兜底意图分析（intent-svc 不可用时）"""
        from app.service.local_intent import local_analyze
        return local_analyze(req.session_id, req.user_id, req.content)

    async def _collect_products(self, intent: dict) -> list[ProductData]:
        """
        数据采集：当前使用模拟数据，L3 服务就绪后替换为 HTTP 调用。
        """
        category = intent.get("product_category", "未知")
        brand = intent.get("extracted_params", {}).get("brand")
        user_type = intent.get("user_type", "B2C")

        products = get_mock_products(
            category=category,
            brand=brand,
            user_type=user_type,
        )
        logger.info("数据采集完成: category=%s brand=%s count=%d", category, brand, len(products))
        return products[: settings.MAX_CANDIDATES]

    def _choose_scoring_model(self, intent: dict) -> ScoringModel:
        """根据意图选择评分模型"""
        user_type = intent.get("user_type", "B2C")
        brand_status = intent.get("brand_status", "undecided")

        if user_type == "B2B":
            return ScoringModel.B2B
        if brand_status == "decided":
            return ScoringModel.B2C_BRAND
        return ScoringModel.B2C_NO_BRAND

    def _to_recommendation(self, score_result, raw_products: list[ProductData]) -> ProductRecommendation:
        """将评分结果 + 原始商品数据合并为推荐对象"""
        raw = next((p for p in raw_products if p.product_id == score_result.product_id), None)
        level_map = {
            "品质款": RecommendationLevel.QUALITY,
            "性价比款": RecommendationLevel.VALUE,
            "不推荐": RecommendationLevel.NOT_RECOMMENDED,
        }
        return ProductRecommendation(
            product_id=score_result.product_id,
            title=raw.title if raw else score_result.product_id,
            price=raw.price if raw else 0.0,
            platform=raw.platform if raw else "",
            total_score=score_result.total_score,
            dimension_scores=score_result.dimension_scores,
            recommendation_level=level_map.get(
                score_result.recommendation_level, RecommendationLevel.VALUE
            ),
            score_reason=score_result.score_reason,
            sales_volume=raw.sales_volume if raw else 0,
            rating=raw.rating if raw else 0.0,
            review_count=raw.review_count if raw else 0,
            shop_name=getattr(raw, "shop_name", None),
            is_official=raw.is_official if raw else False,
        )

    async def _generate_report(
        self, intent: dict, top_scored, raw_products: list[ProductData]
    ) -> str:
        """调用 llm-svc 生成采购决策报告"""
        products_data = [
            {
                "product_id": r.product_id,
                "title": next(
                    (p.title for p in raw_products if p.product_id == r.product_id),
                    r.product_id,
                ),
                "price": next(
                    (p.price for p in raw_products if p.product_id == r.product_id),
                    0.0,
                ),
                "platform": next(
                    (p.platform for p in raw_products if p.product_id == r.product_id),
                    "",
                ),
                "total_score": r.total_score,
                "recommendation_level": r.recommendation_level,
                "score_reason": r.score_reason,
                "dimension_scores": r.dimension_scores,
            }
            for r in top_scored
        ]

        payload = {
            "user_type": intent.get("user_type"),
            "brand_status": intent.get("brand_status"),
            "product_category": intent.get("product_category"),
            "products_data": products_data,
            "user_requirements": intent.get("extracted_params", {}),
        }

        try:
            async with httpx.AsyncClient(timeout=settings.LLM_SVC_TIMEOUT) as client:
                resp = await client.post(
                    f"{settings.LLM_SVC_URL}/api/v1/llm/report",
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json().get("report", "")
        except Exception as e:
            logger.warning("llm-svc 不可达，使用本地模板报告: %s", e)
            return self._fallback_report(intent, top_scored, raw_products)

    def _fallback_report(self, intent: dict, top_scored, raw_products: list[ProductData]) -> str:
        """LLM 不可用时的模板报告"""
        category = intent.get("product_category", "商品")
        user_type = intent.get("user_type", "B2C")
        lines = [
            f"## 采购决策报告 - {category}",
            "",
            f"**用户类型**: {user_type}",
            f"**需求类别**: {category}",
            "",
            "### 推荐商品排名",
        ]
        for idx, r in enumerate(top_scored, 1):
            raw = next((p for p in raw_products if p.product_id == r.product_id), None)
            title = raw.title if raw else r.product_id
            price = f"¥{raw.price:.0f}" if raw else "-"
            lines.append(f"{idx}. **{title}** | {price} | 评分: {r.total_score:.1f} | {r.recommendation_level}")
            lines.append(f"   {r.score_reason}")
        lines += [
            "",
            "### 采购建议",
            "- 建议选择排名第一的品质款以保障质量与售后",
            "- 如预算有限，可考虑性价比款",
            "- 优先选择官方旗舰店或官方授权渠道",
        ]
        return "\n".join(lines)

    @staticmethod
    def _build_intent_summary(intent: dict) -> IntentSummary:
        return IntentSummary(
            user_type=intent.get("user_type", "B2C"),
            brand_status=intent.get("brand_status", "undecided"),
            product_category=intent.get("product_category", "未知"),
            extracted_params=intent.get("extracted_params", {}),
            confidence=intent.get("confidence", 0.5),
        )

    @staticmethod
    def _elapsed(start: float) -> int:
        return int((time.time() - start) * 1000)


decision_orchestrator = DecisionOrchestrator()
