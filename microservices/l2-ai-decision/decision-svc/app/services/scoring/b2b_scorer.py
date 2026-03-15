"""
B2B Scoring Model.

Scores a purchase decision from a business-to-business perspective across six
weighted dimensions.  All raw dimension scores are 0-100; the total is the
weighted sum.
"""
from __future__ import annotations

import logging
import math
from typing import Any

from app.models.schemas import FactorDetail, Grade, ScoreResult

logger = logging.getLogger(__name__)

# Dimension weights — must sum to 1.0
DIMENSION_WEIGHTS: dict[str, float] = {
    "price_competitiveness": 0.25,
    "supplier_reliability": 0.20,
    "delivery_capability": 0.20,
    "quality_compliance": 0.15,
    "after_service": 0.10,
    "min_order_qty_fit": 0.10,
}


def _grade_from_score(score: float) -> Grade:
    if score >= 85:
        return Grade.A
    if score >= 70:
        return Grade.B
    if score >= 55:
        return Grade.C
    return Grade.D


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
    """

    def score(self, context: dict[str, Any]) -> ScoreResult:
        factors: list[FactorDetail] = []
        data_completeness_count = 0
        total_signals = 13

        # ------------------------------------------------------------------ #
        # 1. Price Competitiveness (weight=0.25)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["price_competitiveness"]
        market_price_ratio: float = context.get("market_price_ratio", 1.0)
        bulk_discount: bool = bool(context.get("bulk_discount_available", False))

        # Lower ratio = cheaper than market = better score
        # ratio=0.7 → 100, ratio=1.0 → 75, ratio=1.3 → 40, ratio>=1.5 → 10
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

        data_completeness_count += 1 if "market_price_ratio" in context else 0
        price_explanation = (
            f"市场价格比率 {market_price_ratio:.2f}"
            f"{'（含批量折扣）' if bulk_discount else ''}"
            f"，竞争力评分 {price_score:.1f}"
        )
        factors.append(FactorDetail(
            name="price_competitiveness",
            score=price_score,
            weight=weight,
            explanation=price_explanation,
            weighted_contribution=price_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # 2. Supplier Reliability (weight=0.20)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["supplier_reliability"]
        brand_tier: str = context.get("brand_tier", "C").upper()
        cert_count: int = int(context.get("certification_count", 0))
        years: int = int(context.get("years_in_market", 0))

        tier_score = {"A": 100.0, "B": 70.0, "C": 40.0}.get(brand_tier, 40.0)

        # Each certification adds up to 5 points (cap at 6 certs = +30)
        cert_bonus = min(30.0, cert_count * 5.0)

        # Years in market: 0-3y=0, 5y=20, 10y=40, 20y+=60 (cap)
        if years <= 3:
            years_score = years * 5.0
        elif years <= 10:
            years_score = 15.0 + (years - 3) / 7 * 25.0
        else:
            years_score = 40.0 + min(20.0, (years - 10) * 2.0)

        reliability_score = min(100.0, tier_score * 0.5 + cert_bonus * 0.3 + years_score * 0.2)

        if "brand_tier" in context:
            data_completeness_count += 1
        if "certification_count" in context:
            data_completeness_count += 1
        if "years_in_market" in context:
            data_completeness_count += 1

        reliability_explanation = (
            f"供应商级别 {brand_tier}（基础分 {tier_score:.0f}），"
            f"拥有 {cert_count} 项认证，"
            f"市场运营 {years} 年，"
            f"综合可靠性评分 {reliability_score:.1f}"
        )
        factors.append(FactorDetail(
            name="supplier_reliability",
            score=reliability_score,
            weight=weight,
            explanation=reliability_explanation,
            weighted_contribution=reliability_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # 3. Delivery Capability (weight=0.20)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["delivery_capability"]
        lead_time: int = int(context.get("lead_time_days", 14))
        stock_avail: float = float(context.get("stock_availability", 0.5))

        # Lead time: ≤3 days=100, 7=80, 14=55, 30=30, >30 declines further
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

        stock_score = stock_avail * 100.0  # linear 0-100

        delivery_score = lead_score * 0.6 + stock_score * 0.4

        if "lead_time_days" in context:
            data_completeness_count += 1
        if "stock_availability" in context:
            data_completeness_count += 1

        delivery_explanation = (
            f"交货周期 {lead_time} 天（评分 {lead_score:.1f}），"
            f"库存充足率 {stock_avail * 100:.0f}%（评分 {stock_score:.1f}），"
            f"交付能力综合评分 {delivery_score:.1f}"
        )
        factors.append(FactorDetail(
            name="delivery_capability",
            score=delivery_score,
            weight=weight,
            explanation=delivery_explanation,
            weighted_contribution=delivery_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # 4. Quality & Compliance (weight=0.15)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["quality_compliance"]
        has_quality_cert: bool = bool(context.get("has_quality_cert", False))
        return_rate: float = float(context.get("return_rate", 0.05))

        cert_score = 100.0 if has_quality_cert else 50.0

        # Return rate: 0%=100, 1%=90, 5%=60, 10%=20, >10% declines further
        if return_rate <= 0.01:
            return_score = 100.0 - return_rate / 0.01 * 10.0
        elif return_rate <= 0.05:
            return_score = 90.0 - (return_rate - 0.01) / 0.04 * 30.0
        elif return_rate <= 0.10:
            return_score = 60.0 - (return_rate - 0.05) / 0.05 * 40.0
        else:
            return_score = max(0.0, 20.0 - (return_rate - 0.10) * 200.0)

        quality_score = cert_score * 0.55 + return_score * 0.45

        if "has_quality_cert" in context:
            data_completeness_count += 1
        if "return_rate" in context:
            data_completeness_count += 1

        quality_explanation = (
            f"{'已' if has_quality_cert else '未'}获质量认证，"
            f"历史退货率 {return_rate * 100:.1f}%（评分 {return_score:.1f}），"
            f"质量合规综合评分 {quality_score:.1f}"
        )
        factors.append(FactorDetail(
            name="quality_compliance",
            score=quality_score,
            weight=weight,
            explanation=quality_explanation,
            weighted_contribution=quality_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # 5. After-Sales Service (weight=0.10)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["after_service"]
        warranty_months: int = int(context.get("warranty_months", 12))
        support_hours: float = float(context.get("support_response_hours", 48.0))

        # Warranty: <6m=40, 12m=70, 24m=90, 36m+=100
        if warranty_months < 6:
            warranty_score = max(0.0, warranty_months / 6 * 40.0)
        elif warranty_months < 12:
            warranty_score = 40.0 + (warranty_months - 6) / 6 * 30.0
        elif warranty_months < 24:
            warranty_score = 70.0 + (warranty_months - 12) / 12 * 20.0
        else:
            warranty_score = min(100.0, 90.0 + (warranty_months - 24) / 12 * 10.0)

        # Support response: ≤4h=100, 24h=70, 48h=40, >48h declines
        if support_hours <= 4:
            support_score = 100.0
        elif support_hours <= 24:
            support_score = 100.0 - (support_hours - 4) / 20 * 30.0
        elif support_hours <= 48:
            support_score = 70.0 - (support_hours - 24) / 24 * 30.0
        else:
            support_score = max(10.0, 40.0 - (support_hours - 48) / 24 * 15.0)

        after_service_score = warranty_score * 0.5 + support_score * 0.5

        if "warranty_months" in context:
            data_completeness_count += 1
        if "support_response_hours" in context:
            data_completeness_count += 1

        after_service_explanation = (
            f"质保期 {warranty_months} 个月（评分 {warranty_score:.1f}），"
            f"平均响应 {support_hours:.0f} 小时（评分 {support_score:.1f}），"
            f"售后服务综合评分 {after_service_score:.1f}"
        )
        factors.append(FactorDetail(
            name="after_service",
            score=after_service_score,
            weight=weight,
            explanation=after_service_explanation,
            weighted_contribution=after_service_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # 6. Minimum Order Quantity Fit (weight=0.10)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["min_order_qty_fit"]
        order_qty: int = int(context.get("order_quantity", 1))
        moq: int = int(context.get("min_order_quantity", 1))

        if moq <= 0:
            moq_fit_score = 100.0
        else:
            ratio = order_qty / moq
            if ratio >= 1.0:
                # Meets or exceeds MOQ — reward meeting it cleanly
                moq_fit_score = min(100.0, 70.0 + min(30.0, (ratio - 1.0) * 15.0))
            else:
                # Below MOQ — linear penalty
                moq_fit_score = max(0.0, ratio * 70.0)

        if "order_quantity" in context:
            data_completeness_count += 1
        if "min_order_quantity" in context:
            data_completeness_count += 1

        moq_explanation = (
            f"订单数量 {order_qty}，最小起订量 {moq}"
            f"（比率 {order_qty / max(moq, 1):.2f}），"
            f"MOQ 匹配度评分 {moq_fit_score:.1f}"
        )
        factors.append(FactorDetail(
            name="min_order_qty_fit",
            score=moq_fit_score,
            weight=weight,
            explanation=moq_explanation,
            weighted_contribution=moq_fit_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # Aggregate
        # ------------------------------------------------------------------ #
        total_score = sum(f.weighted_contribution for f in factors)
        total_score = round(min(100.0, max(0.0, total_score)), 2)

        dimension_scores = {f.name: round(f.score, 2) for f in factors}
        grade = _grade_from_score(total_score)

        # Confidence: based on data completeness
        confidence = round(min(1.0, data_completeness_count / total_signals), 3)
        # Boost confidence slightly when grade boundary is clear
        if total_score >= 90 or total_score <= 40:
            confidence = min(1.0, confidence + 0.05)

        logger.info(
            "B2B score: total=%.2f grade=%s confidence=%.3f",
            total_score, grade, confidence,
        )

        return ScoreResult(
            total_score=total_score,
            dimension_scores=dimension_scores,
            grade=grade,
            confidence=confidence,
            factors=factors,
        )


# Singleton
b2b_scorer = B2BScorerModel()
