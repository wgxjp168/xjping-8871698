"""
B2B Scoring Model.

Scores a purchase decision from a business-to-business perspective across six
weighted dimensions.  All raw dimension scores are 0-100; the total is the
weighted sum.

New in this revision:
  - Dynamic weight adjustment based on sector / urgency / compliance signals.
  - score_with_llm_adjustments(): accepts LLM-suggested per-dimension deltas.
  - Confidence interval (lower_bound, upper_bound) based on data completeness.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from app.models.schemas import FactorDetail, Grade, ScoreResult

logger = logging.getLogger(__name__)

# Default dimension weights — must sum to 1.0
_BASE_WEIGHTS: dict[str, float] = {
    "price_competitiveness": 0.25,
    "supplier_reliability": 0.20,
    "delivery_capability": 0.20,
    "quality_compliance": 0.15,
    "after_service": 0.10,
    "min_order_qty_fit": 0.10,
}

_TOTAL_SIGNALS = 13  # number of context signals used for confidence calculation


def _grade_from_score(score: float) -> Grade:
    if score >= 85:
        return Grade.A
    if score >= 70:
        return Grade.B
    if score >= 55:
        return Grade.C
    return Grade.D


def _dynamic_weights(context: dict[str, Any]) -> dict[str, float]:
    """
    Adjust base weights based on contextual signals:

    - urgency=high   → delivery_capability weight + 0.05
    - compliance_strict=true → quality_compliance weight + 0.05
    - price_sensitive=true   → price_competitiveness weight + 0.05
    - long_term_contract=true → supplier_reliability weight + 0.05

    Excess weight is drawn from after_service and min_order_qty_fit proportionally.
    """
    weights = dict(_BASE_WEIGHTS)
    boosts: dict[str, float] = {}

    if str(context.get("urgency", "")).lower() == "high":
        boosts["delivery_capability"] = 0.05
    if context.get("compliance_strict"):
        boosts["quality_compliance"] = 0.05
    if context.get("price_sensitive"):
        boosts["price_competitiveness"] = 0.05
    if context.get("long_term_contract"):
        boosts["supplier_reliability"] = 0.05

    if not boosts:
        return weights

    total_boost = sum(boosts.values())
    # Drain from lower-priority dimensions proportionally
    drainable = ["after_service", "min_order_qty_fit"]
    drain_per = total_boost / len(drainable)
    for dim in drainable:
        weights[dim] = max(0.02, weights[dim] - drain_per)
    for dim, boost in boosts.items():
        weights[dim] = weights[dim] + boost

    # Renormalise to exactly 1.0
    total = sum(weights.values())
    return {k: round(v / total, 6) for k, v in weights.items()}


class B2BScorerModel:
    """
    Scores B2B purchase decisions.

    Expected context keys (all optional; missing keys produce conservative
    mid-range scores with reduced confidence):
        market_price_ratio      float   product_price / market_reference_price (1.0 = at market)
        bulk_discount_available bool    whether a volume discount is offered
        brand_tier              str     'A' | 'B' | 'C'  supplier tier classification
        certification_count     int     number of quality/compliance certifications held
        years_in_market         int     supplier years of operation
        lead_time_days          int     days from order to delivery
        stock_availability      float   0-1, fraction of line items in stock
        has_quality_cert        bool    ISO / relevant quality certification present
        return_rate             float   0-1, historical return/defect rate
        warranty_months         int     warranty duration in months
        support_response_hours  float   average support response time in hours
        order_quantity          int     requested order quantity
        min_order_quantity      int     supplier minimum order quantity

    Dynamic weight signals (optional):
        urgency                 str     'high' | 'normal' | 'low'
        compliance_strict       bool    strict regulatory environment
        price_sensitive         bool    cost is the primary driver
        long_term_contract      bool    evaluating for a long-term supplier
    """

    def score(self, context: dict[str, Any]) -> ScoreResult:
        """Standard scoring without LLM adjustments."""
        return self._compute(context, llm_adjustments=None)

    def score_with_llm_adjustments(
        self,
        context: dict[str, Any],
        llm_adjustments: Dict[str, float],
    ) -> ScoreResult:
        """
        Score with LLM-suggested per-dimension adjustments.

        llm_adjustments: dict mapping dimension name → delta (-20 to +20).
        The adjustments are clamped and applied after the base score is computed.
        """
        return self._compute(context, llm_adjustments=llm_adjustments)

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    def _compute(
        self,
        context: dict[str, Any],
        llm_adjustments: Optional[Dict[str, float]],
    ) -> ScoreResult:
        weights = _dynamic_weights(context)
        factors: list[FactorDetail] = []
        data_completeness_count = 0

        # ------------------------------------------------------------------ #
        # 1. Price Competitiveness
        # ------------------------------------------------------------------ #
        w = weights["price_competitiveness"]
        market_price_ratio: float = context.get("market_price_ratio", 1.0)
        bulk_discount: bool = bool(context.get("bulk_discount_available", False))

        if market_price_ratio <= 0.7:
            price_score = 100.0
        elif market_price_ratio <= 1.0:
            price_score = 75.0 + (1.0 - market_price_ratio) / 0.3 * 25.0
        elif market_price_ratio <= 1.3:
            price_score = 75.0 - (market_price_ratio - 1.0) / 0.3 * 35.0
        else:
            price_score = max(10.0, 40.0 - (market_price_ratio - 1.3) / 0.2 * 30.0)
        if bulk_discount:
            price_score = min(100.0, price_score + 8.0)
            data_completeness_count += 1
        if "market_price_ratio" in context:
            data_completeness_count += 1

        factors.append(FactorDetail(
            name="price_competitiveness",
            score=price_score,
            weight=w,
            explanation=(
                f"市场价格比率 {market_price_ratio:.2f}"
                f"{'（含批量折扣）' if bulk_discount else ''}"
                f"，竞争力评分 {price_score:.1f}"
            ),
            weighted_contribution=price_score * w,
        ))

        # ------------------------------------------------------------------ #
        # 2. Supplier Reliability
        # ------------------------------------------------------------------ #
        w = weights["supplier_reliability"]
        brand_tier = context.get("brand_tier", "C").upper()
        cert_count = int(context.get("certification_count", 0))
        years = int(context.get("years_in_market", 0))

        tier_score = {"A": 100.0, "B": 70.0, "C": 40.0}.get(brand_tier, 40.0)
        cert_bonus = min(30.0, cert_count * 5.0)
        if years <= 3:
            years_score = years * 5.0
        elif years <= 10:
            years_score = 15.0 + (years - 3) / 7 * 25.0
        else:
            years_score = 40.0 + min(20.0, (years - 10) * 2.0)
        reliability_score = min(100.0, tier_score * 0.5 + cert_bonus * 0.3 + years_score * 0.2)

        for k in ["brand_tier", "certification_count", "years_in_market"]:
            if k in context:
                data_completeness_count += 1

        factors.append(FactorDetail(
            name="supplier_reliability",
            score=reliability_score,
            weight=w,
            explanation=(
                f"供应商级别 {brand_tier}（基础分 {tier_score:.0f}），"
                f"拥有 {cert_count} 项认证，"
                f"市场运营 {years} 年，"
                f"综合可靠性评分 {reliability_score:.1f}"
            ),
            weighted_contribution=reliability_score * w,
        ))

        # ------------------------------------------------------------------ #
        # 3. Delivery Capability
        # ------------------------------------------------------------------ #
        w = weights["delivery_capability"]
        lead_time = int(context.get("lead_time_days", 14))
        stock_avail = float(context.get("stock_availability", 0.5))

        if lead_time <= 3:
            lead_score = 100.0
        elif lead_time <= 7:
            lead_score = 100.0 - (lead_time - 3) / 4 * 20.0
        elif lead_time <= 14:
            lead_score = 80.0 - (lead_time - 7) / 7 * 25.0
        elif lead_time <= 30:
            lead_score = 55.0 - (lead_time - 14) / 16 * 25.0
        else:
            lead_score = max(10.0, 30.0 - (lead_time - 30) * 0.5)

        delivery_score = lead_score * 0.6 + (stock_avail * 100.0) * 0.4

        for k in ["lead_time_days", "stock_availability"]:
            if k in context:
                data_completeness_count += 1

        factors.append(FactorDetail(
            name="delivery_capability",
            score=delivery_score,
            weight=w,
            explanation=(
                f"交货周期 {lead_time} 天（评分 {lead_score:.1f}），"
                f"库存充足率 {stock_avail * 100:.0f}%，"
                f"交付能力综合评分 {delivery_score:.1f}"
            ),
            weighted_contribution=delivery_score * w,
        ))

        # ------------------------------------------------------------------ #
        # 4. Quality & Compliance
        # ------------------------------------------------------------------ #
        w = weights["quality_compliance"]
        has_quality_cert = bool(context.get("has_quality_cert", False))
        return_rate = float(context.get("return_rate", 0.05))

        cert_score = 100.0 if has_quality_cert else 50.0
        if return_rate <= 0.01:
            return_score = 100.0 - return_rate / 0.01 * 10.0
        elif return_rate <= 0.05:
            return_score = 90.0 - (return_rate - 0.01) / 0.04 * 30.0
        elif return_rate <= 0.10:
            return_score = 60.0 - (return_rate - 0.05) / 0.05 * 40.0
        else:
            return_score = max(0.0, 20.0 - (return_rate - 0.10) * 200.0)
        quality_score = cert_score * 0.55 + return_score * 0.45

        for k in ["has_quality_cert", "return_rate"]:
            if k in context:
                data_completeness_count += 1

        factors.append(FactorDetail(
            name="quality_compliance",
            score=quality_score,
            weight=w,
            explanation=(
                f"{'已' if has_quality_cert else '未'}获质量认证，"
                f"历史退货率 {return_rate * 100:.1f}%，"
                f"质量合规综合评分 {quality_score:.1f}"
            ),
            weighted_contribution=quality_score * w,
        ))

        # ------------------------------------------------------------------ #
        # 5. After-Sales Service
        # ------------------------------------------------------------------ #
        w = weights["after_service"]
        warranty_months = int(context.get("warranty_months", 12))
        support_hours = float(context.get("support_response_hours", 48.0))

        if warranty_months < 6:
            warranty_score = max(0.0, warranty_months / 6 * 40.0)
        elif warranty_months < 12:
            warranty_score = 40.0 + (warranty_months - 6) / 6 * 30.0
        elif warranty_months < 24:
            warranty_score = 70.0 + (warranty_months - 12) / 12 * 20.0
        else:
            warranty_score = min(100.0, 90.0 + (warranty_months - 24) / 12 * 10.0)

        if support_hours <= 4:
            support_score = 100.0
        elif support_hours <= 24:
            support_score = 100.0 - (support_hours - 4) / 20 * 30.0
        elif support_hours <= 48:
            support_score = 70.0 - (support_hours - 24) / 24 * 30.0
        else:
            support_score = max(10.0, 40.0 - (support_hours - 48) / 24 * 15.0)

        after_service_score = warranty_score * 0.5 + support_score * 0.5

        for k in ["warranty_months", "support_response_hours"]:
            if k in context:
                data_completeness_count += 1

        factors.append(FactorDetail(
            name="after_service",
            score=after_service_score,
            weight=w,
            explanation=(
                f"质保期 {warranty_months} 个月（评分 {warranty_score:.1f}），"
                f"平均响应 {support_hours:.0f} 小时（评分 {support_score:.1f}），"
                f"售后服务综合评分 {after_service_score:.1f}"
            ),
            weighted_contribution=after_service_score * w,
        ))

        # ------------------------------------------------------------------ #
        # 6. MOQ Fit
        # ------------------------------------------------------------------ #
        w = weights["min_order_qty_fit"]
        order_qty = int(context.get("order_quantity", 1))
        moq = max(1, int(context.get("min_order_quantity", 1)))

        ratio = order_qty / moq
        if ratio >= 1.0:
            moq_fit_score = min(100.0, 70.0 + min(30.0, (ratio - 1.0) * 15.0))
        else:
            moq_fit_score = max(0.0, ratio * 70.0)

        for k in ["order_quantity", "min_order_quantity"]:
            if k in context:
                data_completeness_count += 1

        factors.append(FactorDetail(
            name="min_order_qty_fit",
            score=moq_fit_score,
            weight=w,
            explanation=(
                f"订单数量 {order_qty}，最小起订量 {moq}（比率 {ratio:.2f}），"
                f"MOQ 匹配度评分 {moq_fit_score:.1f}"
            ),
            weighted_contribution=moq_fit_score * w,
        ))

        # ------------------------------------------------------------------ #
        # Aggregate base score
        # ------------------------------------------------------------------ #
        total_score = round(
            min(100.0, max(0.0, sum(f.weighted_contribution for f in factors))), 2
        )
        dimension_scores = {f.name: round(f.score, 2) for f in factors}
        grade = _grade_from_score(total_score)

        # Confidence + uncertainty band based on data completeness
        completeness = data_completeness_count / _TOTAL_SIGNALS
        confidence = round(min(1.0, completeness + (0.05 if total_score >= 90 or total_score <= 40 else 0.0)), 3)
        missing_fraction = 1.0 - completeness
        score_lower = round(max(0.0, total_score - missing_fraction * 15), 2)
        score_upper = round(min(100.0, total_score + missing_fraction * 10), 2)

        # ------------------------------------------------------------------ #
        # Apply LLM adjustments (optional)
        # ------------------------------------------------------------------ #
        llm_adjusted_score: Optional[float] = None
        llm_adjusted_grade: Optional[Grade] = None

        if llm_adjustments:
            dim_scores_adj = dict(dimension_scores)
            adjusted_total = 0.0
            for f in factors:
                delta = float(llm_adjustments.get(f.name, 0.0))
                # Clamp adjustment to [-20, +20] range
                delta = max(-20.0, min(20.0, delta))
                adj_score = max(0.0, min(100.0, f.score + delta))
                dim_scores_adj[f.name] = round(adj_score, 2)
                adjusted_total += adj_score * f.weight

            llm_adjusted_score = round(min(100.0, max(0.0, adjusted_total)), 2)
            llm_adjusted_grade = _grade_from_score(llm_adjusted_score)
            logger.info(
                "B2B LLM adjustments applied: base=%.2f → adjusted=%.2f (%s)",
                total_score, llm_adjusted_score, llm_adjusted_grade,
            )

        logger.info(
            "B2B score: total=%.2f grade=%s confidence=%.3f ci=[%.1f, %.1f]",
            total_score, grade, confidence, score_lower, score_upper,
        )

        return ScoreResult(
            total_score=total_score,
            dimension_scores=dimension_scores,
            grade=grade,
            confidence=confidence,
            factors=factors,
            llm_adjusted_score=llm_adjusted_score,
            llm_adjusted_grade=llm_adjusted_grade,
            score_lower_bound=score_lower,
            score_upper_bound=score_upper,
        )


# Singleton
b2b_scorer = B2BScorerModel()
