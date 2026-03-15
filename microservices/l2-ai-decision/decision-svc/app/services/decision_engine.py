"""
DecisionEngine — 8-step AI decision flow.

Each step is individually logged.  External service calls (L3 data, LLM)
use graceful fallback to mock data when the service is unavailable.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.models.schemas import (
    BrandStatus,
    DecisionAnalyzeRequest,
    DecisionAnalyzeResponse,
    RuleResult,
    ScoreResult,
    ScoringContext,
)
from app.services.explainability import ExplainabilityEngine
from app.services.rule_engine import rule_engine
from app.services.scoring.b2b_scorer import b2b_scorer
from app.services.scoring.b2c_known_scorer import b2c_known_scorer
from app.services.scoring.b2c_unknown_scorer import b2c_unknown_scorer

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Orchestrates the full 8-step purchase-decision analysis flow.
    """

    def __init__(self) -> None:
        self._explainability = ExplainabilityEngine()
        # In-memory decision cache {decision_id: DecisionAnalyzeResponse}
        self._cache: dict[str, DecisionAnalyzeResponse] = {}

    # ---------------------------------------------------------------------- #
    # Public entry point
    # ---------------------------------------------------------------------- #

    async def analyze(self, request: DecisionAnalyzeRequest) -> DecisionAnalyzeResponse:
        """Execute all 8 decision steps and return the consolidated response."""
        decision_id = f"DEC-{uuid.uuid4().hex[:12].upper()}"
        logger.info("Decision %s — starting analysis for session %s", decision_id, request.session_id)

        # Step 1: Validate input
        self._step_validate_input(request)

        # Step 2: Determine scoring context
        scoring_context = self._step_determine_scoring_context(
            request.intent, request.entities, request.brand_status
        )

        # Step 3: Enrich context
        enriched = await self._step_enrich_context(request)

        # Step 4: Apply rules
        rule_result = self._step_apply_rules(enriched)

        # Step 5: Calculate scores (base rule-based score)
        score_result = self._step_calculate_scores(enriched, scoring_context)

        # Step 6: Get LLM scoring insights and apply adjustments (optional, async)
        llm_insights = await self._step_get_llm_insights(enriched, request, score_result)
        if llm_insights:
            score_result = self._step_apply_llm_adjustments(
                score_result, scoring_context, enriched, llm_insights
            )

        # Step 7: Generate explanation
        explanation = self._step_generate_explanation(score_result, rule_result, enriched)

        # Step 8: Compile decision
        response = self._step_compile_decision(
            decision_id=decision_id,
            scoring_context=scoring_context,
            score_result=score_result,
            rule_result=rule_result,
            explanation=explanation,
            llm_insights=llm_insights,
            request=request,
        )

        # Cache for report retrieval
        self._cache[decision_id] = response
        logger.info(
            "Decision %s — completed. Grade=%s Score=%.2f Violations=%d",
            decision_id,
            score_result.grade,
            score_result.total_score,
            len(rule_result.violations),
        )
        return response

    def get_cached(self, decision_id: str) -> Optional[DecisionAnalyzeResponse]:
        return self._cache.get(decision_id)

    # ---------------------------------------------------------------------- #
    # Step 1 — Validate input
    # ---------------------------------------------------------------------- #

    def _step_validate_input(self, request: DecisionAnalyzeRequest) -> None:
        logger.debug("Step 1: validate_input — session=%s intent='%s'", request.session_id, request.intent)
        if not request.session_id:
            raise ValueError("session_id is required")
        if not request.intent:
            raise ValueError("intent is required")

    # ---------------------------------------------------------------------- #
    # Step 2 — Determine scoring context
    # ---------------------------------------------------------------------- #

    def _step_determine_scoring_context(
        self,
        intent: str,
        entities: dict[str, Any],
        brand_status: BrandStatus,
    ) -> ScoringContext:
        logger.debug("Step 2: determine_scoring_context — brand_status=%s", brand_status)

        # Detect B2B from entities/intent keywords
        org_type = str(entities.get("org_type", "")).lower()
        is_b2b_intent = any(
            kw in intent.lower()
            for kw in ["企业", "公司", "采购", "批量", "b2b", "corporate", "bulk"]
        )
        is_b2b_entity = org_type in {"b2b", "enterprise", "corporate", "company"}

        if is_b2b_intent or is_b2b_entity:
            ctx = ScoringContext.B2B
        elif brand_status == BrandStatus.KNOWN:
            ctx = ScoringContext.B2C_KNOWN
        else:
            ctx = ScoringContext.B2C_UNKNOWN

        logger.info("Step 2 result: ScoringContext=%s", ctx)
        return ctx

    # ---------------------------------------------------------------------- #
    # Step 3 — Enrich context
    # ---------------------------------------------------------------------- #

    async def _step_enrich_context(self, request: DecisionAnalyzeRequest) -> dict[str, Any]:
        logger.debug("Step 3: enrich_context")

        # Start with everything we already know
        context: dict[str, Any] = {
            "session_id": request.session_id,
            "intent": request.intent,
            "brand_status": request.brand_status.value,
            **request.entities,
            **request.user_context,
        }

        # Attempt to pull enriched product/market data from L3 services
        product_data = await self._fetch_l3_product_data(request.entities)
        market_data = await self._fetch_l3_market_data(request.entities)

        context.update(product_data)
        context.update(market_data)

        # Add is_b2b flag for rules
        org_type = str(context.get("org_type", "")).lower()
        context["is_b2b"] = org_type in {"b2b", "enterprise", "corporate", "company"}

        logger.info("Step 3 result: enriched context has %d keys", len(context))
        return context

    async def _fetch_l3_product_data(self, entities: dict[str, Any]) -> dict[str, Any]:
        """Attempt to fetch product data from L3 product service with mock fallback."""
        try:
            async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
                resp = await client.post(
                    f"{settings.l3_product_svc_url}/product/lookup",
                    json=entities,
                )
                if resp.status_code == 200:
                    logger.debug("L3 product service returned data")
                    return resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("L3 product service unavailable (%s), using mock data", exc)

        # Mock product data
        return self._mock_product_data(entities)

    async def _fetch_l3_market_data(self, entities: dict[str, Any]) -> dict[str, Any]:
        """Attempt to fetch market reference data from L3 data service with mock fallback."""
        try:
            async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
                resp = await client.post(
                    f"{settings.l3_data_svc_url}/market/reference",
                    json=entities,
                )
                if resp.status_code == 200:
                    logger.debug("L3 data service returned market data")
                    return resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("L3 data service unavailable (%s), using mock data", exc)

        return self._mock_market_data(entities)

    @staticmethod
    def _mock_product_data(entities: dict[str, Any]) -> dict[str, Any]:
        """Reasonable mock product data for testing / service-unavailable fallback."""
        price = float(entities.get("product_price", entities.get("price", 999.0)))
        return {
            "product_price": price,
            "product_brand": entities.get("brand", "GenericBrand"),
            "product_category": entities.get("category", "electronics"),
            "in_stock": True,
            "delivery_time_days": 3,
            "average_rating": 4.2,
            "review_count": 312,
            "product_spec_count": 12,
            "warranty_months": 12,
            "support_response_hours": 24,
            "lead_time_days": 3,
            "stock_availability": 0.85,
            "has_quality_cert": True,
            "return_rate": 0.02,
            "bulk_discount_available": price > 5000,
        }

    @staticmethod
    def _mock_market_data(entities: dict[str, Any]) -> dict[str, Any]:
        """Mock market reference data."""
        price = float(entities.get("product_price", entities.get("price", 999.0)))
        return {
            "market_reference_price": price * 0.95,
            "market_price_ratio": 1.05,
            "category_avg_spec_count": 10,
            "max_sales_rank": 1000,
            "sales_rank": 150,
            "brand_tier": "B",
            "certification_count": 2,
            "years_in_market": 8,
            "min_order_quantity": 1,
            "restricted_categories": [],
            "approved_brands": [],
        }

    # ---------------------------------------------------------------------- #
    # Step 4 — Apply rules
    # ---------------------------------------------------------------------- #

    def _step_apply_rules(self, context: dict[str, Any]) -> RuleResult:
        logger.debug("Step 4: apply_rules")
        result = rule_engine.evaluate(context)
        logger.info(
            "Step 4 result: passed=%s violations=%d warnings=%d",
            result.passed, len(result.violations), len(result.warnings),
        )
        return result

    # ---------------------------------------------------------------------- #
    # Step 5 — Calculate scores
    # ---------------------------------------------------------------------- #

    def _step_calculate_scores(
        self, context: dict[str, Any], scoring_context: ScoringContext
    ) -> ScoreResult:
        logger.debug("Step 5: calculate_scores — context=%s", scoring_context)

        if scoring_context == ScoringContext.B2B:
            result = b2b_scorer.score(context)
        elif scoring_context == ScoringContext.B2C_KNOWN:
            result = b2c_known_scorer.score(context)
        else:
            result = b2c_unknown_scorer.score(context)

        logger.info(
            "Step 5 result: score=%.2f grade=%s confidence=%.3f",
            result.total_score, result.grade, result.confidence,
        )
        return result

    # ---------------------------------------------------------------------- #
    # Step 5b — Apply LLM dimension adjustments to ScoreResult
    # ---------------------------------------------------------------------- #

    def _step_apply_llm_adjustments(
        self,
        score_result: ScoreResult,
        scoring_context: ScoringContext,
        context: dict[str, Any],
        llm_insights: dict[str, Any],
    ) -> ScoreResult:
        """
        Re-score using LLM-suggested per-dimension adjustments.

        dimension_insights from llm_insights is a list of
        {dimension, adjustment, signal, rationale, confidence}.
        Only adjustments with LLM confidence ≥ 0.6 are applied.
        """
        adjustments: dict[str, float] = {}
        for di in llm_insights.get("dimension_insights", []):
            dim = di.get("dimension", "")
            delta = float(di.get("adjustment", 0.0))
            llm_conf = float(di.get("confidence", 0.0))
            # Gate on LLM confidence to avoid noisy adjustments
            if llm_conf >= 0.6 and dim:
                adjustments[dim] = delta

        if not adjustments:
            return score_result

        if scoring_context == ScoringContext.B2B:
            updated = b2b_scorer.score_with_llm_adjustments(context, adjustments)
        elif scoring_context == ScoringContext.B2C_KNOWN:
            updated = b2c_known_scorer.score_with_llm_adjustments(context, adjustments)
        else:
            updated = b2c_unknown_scorer.score_with_llm_adjustments(context, adjustments)

        logger.info(
            "Step 5b: LLM adjustments applied to %d dimensions — "
            "base=%.2f adj=%.2f",
            len(adjustments),
            score_result.total_score,
            updated.llm_adjusted_score or updated.total_score,
        )
        return updated

    # ---------------------------------------------------------------------- #
    # Step 6 — LLM scoring insights (async, optional)
    #
    # Calls llm-svc /llm/analyze/scoring to get per-dimension LLM assessments
    # and applies the adjustment deltas to produce llm_adjusted_score.
    # Falls back gracefully when llm-svc is unavailable.
    # ---------------------------------------------------------------------- #

    async def _step_get_llm_insights(
        self,
        context: dict[str, Any],
        request: DecisionAnalyzeRequest,
        score_result: Optional[ScoreResult] = None,
    ) -> Optional[dict[str, Any]]:
        logger.debug("Step 6: get_llm_insights (scoring insight mode)")

        # If pre-computed analysis was provided, use it directly
        if request.llm_analysis:
            return request.llm_analysis

        # Determine scoring context string for the LLM
        org_type = str(context.get("org_type", "")).lower()
        if org_type in {"b2b", "enterprise", "corporate", "company"} or any(
            kw in request.intent.lower()
            for kw in ["企业", "公司", "采购", "批量"]
        ):
            scoring_ctx_str = "B2B"
        elif str(context.get("brand_status", "")).upper() == "KNOWN":
            scoring_ctx_str = "B2C_KNOWN"
        else:
            scoring_ctx_str = "B2C_UNKNOWN"

        dimension_scores: dict[str, float] = {}
        if score_result:
            dimension_scores = score_result.dimension_scores

        # Trim enriched context to relevant keys to keep prompt concise
        enriched_summary = {
            k: v for k, v in context.items()
            if k in {
                "product_brand", "product_category", "product_price",
                "market_price_ratio", "in_stock", "average_rating",
                "brand_tier", "lead_time_days", "has_quality_cert",
                "return_rate", "warranty_months",
            }
        }

        try:
            async with httpx.AsyncClient(timeout=settings.http_timeout) as client:
                payload = {
                    "scoring_context": scoring_ctx_str,
                    "intent": request.intent,
                    "entities": {
                        k: v for k, v in request.entities.items()
                        if k in {"brand", "category", "budget_max", "budget_min", "specs"}
                    },
                    "dimension_scores": dimension_scores,
                    "enriched_context": enriched_summary,
                }
                resp = await client.post(
                    f"{settings.llm_svc_url}/llm/analyze/scoring",
                    json=payload,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    logger.info(
                        "Step 6: LLM scoring insights obtained — "
                        "adjusted_total=%.2f risk_signals=%d",
                        data.get("adjusted_total", 0),
                        len(data.get("risk_signals", [])),
                    )
                    return data
                logger.warning(
                    "Step 6: LLM scoring service returned %d — skipping",
                    resp.status_code,
                )
        except Exception as exc:  # noqa: BLE001
            logger.info("Step 6: LLM service unavailable (%s), skipping insights", exc)

        return None

    # ---------------------------------------------------------------------- #
    # Step 7 — Generate explanation
    # ---------------------------------------------------------------------- #

    def _step_generate_explanation(
        self,
        score_result: ScoreResult,
        rule_result: RuleResult,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        logger.debug("Step 7: generate_explanation")
        explanation = self._explainability.explain_score(score_result, context)
        explanation["rule_summary"] = {
            "passed": rule_result.passed,
            "violation_count": len(rule_result.violations),
            "warning_count": len(rule_result.warnings),
        }
        logger.info("Step 7 result: explanation generated with %d factors", len(score_result.factors))
        return explanation

    # ---------------------------------------------------------------------- #
    # Step 8 — Compile decision
    # ---------------------------------------------------------------------- #

    def _step_compile_decision(
        self,
        decision_id: str,
        scoring_context: ScoringContext,
        score_result: ScoreResult,
        rule_result: RuleResult,
        explanation: dict[str, Any],
        llm_insights: Optional[dict[str, Any]],
        request: DecisionAnalyzeRequest,
    ) -> DecisionAnalyzeResponse:
        logger.debug("Step 8: compile_decision")

        recommendation = self._build_recommendation(
            score_result, rule_result, scoring_context, request
        )
        next_steps = self._build_next_steps(score_result, rule_result, scoring_context)
        requires_review = (
            not rule_result.passed
            or score_result.total_score < 55
            or len(rule_result.violations) > 0
        )

        return DecisionAnalyzeResponse(
            decision_id=decision_id,
            scoring_context=scoring_context,
            score_result=score_result,
            rule_result=rule_result,
            recommendation=recommendation,
            next_steps=next_steps,
            requires_human_review=requires_review,
            explanation=explanation,
            llm_insights=llm_insights,
            created_at=datetime.utcnow(),
        )

    # ---------------------------------------------------------------------- #
    # Helpers
    # ---------------------------------------------------------------------- #

    @staticmethod
    def _build_recommendation(
        score_result: ScoreResult,
        rule_result: RuleResult,
        scoring_context: ScoringContext,
        request: DecisionAnalyzeRequest,
    ) -> str:
        grade = score_result.grade
        violations = len(rule_result.violations)
        warnings = len(rule_result.warnings)

        if violations > 0:
            return (
                f"⚠️ 发现 {violations} 条合规问题，当前不建议推进采购。"
                f"请先解决违规项，再重新评估。"
            )

        if grade == "A":
            base = "该产品综合评分优秀，强烈推荐采购。"
        elif grade == "B":
            base = "该产品综合评分良好，推荐采购。"
        elif grade == "C":
            base = "该产品综合评分一般，建议谨慎评估后再决定。"
        else:
            base = "该产品综合评分较低，不建议当前方案，建议寻找替代品。"

        if warnings > 0:
            base += f" 注意：存在 {warnings} 条预警，请知悉。"

        if scoring_context == ScoringContext.B2B:
            base += " 企业采购需按内部审批流程执行。"

        return base

    @staticmethod
    def _build_next_steps(
        score_result: ScoreResult,
        rule_result: RuleResult,
        scoring_context: ScoringContext,
    ) -> list[str]:
        steps: list[str] = []

        if rule_result.violations:
            steps.append("1. 立即处理规则违规：" + "；".join(rule_result.violations[:2]))
        if rule_result.warnings:
            steps.append(f"2. 关注 {len(rule_result.warnings)} 条预警事项并评估风险")

        if score_result.total_score >= 85:
            steps.append("3. 确认最终报价后即可提交采购申请")
        elif score_result.total_score >= 70:
            steps.append("3. 与供应商协商价格及服务条款后提交采购申请")
        elif score_result.total_score >= 55:
            steps.append("3. 建议进一步比较同类产品后再做决策")
        else:
            steps.append("3. 建议重新筛选候选产品，当前选项综合评分偏低")

        if scoring_context == ScoringContext.B2B:
            steps.append("4. 提交内部采购审批流程（需附本决策报告）")
            steps.append("5. 签署供应商合同并安排交付时间表")
        else:
            steps.append("4. 确认收货地址及支付方式后下单")
            steps.append("5. 保存订单凭证，注意退换货政策")

        return steps


# Singleton
decision_engine = DecisionEngine()
