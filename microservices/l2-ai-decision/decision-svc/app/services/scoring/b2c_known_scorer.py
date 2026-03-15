"""
B2C Known-Brand Scoring Model (B2C已定品牌评分).

Used when the buyer has specified a target brand and we are evaluating whether
a particular product listing matches their needs.

New in this revision:
  - score_with_llm_adjustments(): applies LLM-suggested dimension deltas.
  - Confidence interval (lower_bound, upper_bound) from data completeness.
  - Dynamic weight adjustment based on buyer priority signals.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.models.schemas import FactorDetail, Grade, ScoreResult

logger = logging.getLogger(__name__)

_BASE_WEIGHTS: dict[str, float] = {
    "price_value": 0.30,
    "brand_match": 0.25,
    "spec_match": 0.25,
    "availability": 0.10,
    "review_score": 0.10,
}

_TOTAL_SIGNALS = 11


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
    Adjust weights for B2C-Known based on context signals:
      - gift_purchase=true      → review_score weight + 0.05
      - urgent_delivery=true    → availability weight + 0.05
      - spec_critical=true      → spec_match weight + 0.05
    """
    weights = dict(_BASE_WEIGHTS)
    boosts: dict[str, float] = {}

    if context.get("gift_purchase"):
        boosts["review_score"] = 0.05
    if context.get("urgent_delivery"):
        boosts["availability"] = 0.05
    if context.get("spec_critical"):
        boosts["spec_match"] = 0.05

    if not boosts:
        return weights

    total_boost = sum(boosts.values())
    drainable = [d for d in ["price_value", "brand_match"] if d not in boosts]
    drain_per = total_boost / max(len(drainable), 1)
    for dim in drainable:
        weights[dim] = max(0.02, weights[dim] - drain_per)
    for dim, boost in boosts.items():
        weights[dim] = weights[dim] + boost

    total = sum(weights.values())
    return {k: round(v / total, 6) for k, v in weights.items()}


class B2CKnownScorerModel:
    """
    Scores a B2C purchase where the target brand is already decided.

    Expected context keys:
        product_price           float   product listing price
        budget                  float   user's stated budget
        promotion_available     bool    whether a promotion/coupon is active
        target_brand            str     brand the user wants
        product_brand           str     brand of the evaluated product
        is_authorized_dealer    bool    whether listing is from an official dealer
        required_specs          dict    key → expected value (str/int/float)
        product_specs           dict    key → actual value
        in_stock                bool    whether item is currently in stock
        delivery_time_days      int     estimated delivery days
        average_rating          float   product review average (0-5 scale)
        review_count            int     total number of reviews

    Dynamic weight signals (optional):
        gift_purchase           bool
        urgent_delivery         bool
        spec_critical           bool
    """

    def score(self, context: dict[str, Any]) -> ScoreResult:
        return self._compute(context, llm_adjustments=None)

    def score_with_llm_adjustments(
        self,
        context: dict[str, Any],
        llm_adjustments: Dict[str, float],
    ) -> ScoreResult:
        return self._compute(context, llm_adjustments=llm_adjustments)

    def _compute(
        self,
        context: dict[str, Any],
        llm_adjustments: Optional[Dict[str, float]],
    ) -> ScoreResult:
        weights = _dynamic_weights(context)
        factors: list[FactorDetail] = []
        data_present = 0

        # ------------------------------------------------------------------ #
        # 1. Price / Value
        # ------------------------------------------------------------------ #
        w = weights["price_value"]
        product_price = float(context.get("product_price", 0))
        budget = float(context.get("budget", 0))
        promotion = bool(context.get("promotion_available", False))

        if budget > 0 and product_price > 0:
            ratio = product_price / budget
            if ratio <= 0.7:
                pv_score = 100.0
            elif ratio <= 1.0:
                pv_score = 100.0 - (ratio - 0.7) / 0.3 * 25.0
            elif ratio <= 1.2:
                pv_score = 75.0 - (ratio - 1.0) / 0.2 * 40.0
            else:
                pv_score = max(5.0, 35.0 - (ratio - 1.2) / 0.3 * 30.0)
            data_present += 2
        else:
            pv_score = 60.0

        if promotion:
            pv_score = min(100.0, pv_score + 10.0)
            data_present += 1

        factors.append(FactorDetail(
            name="price_value",
            score=pv_score,
            weight=w,
            explanation=(
                f"产品价格 ¥{product_price:.2f}，预算 ¥{budget:.2f}"
                + (f"（比率 {product_price / budget:.2f}）" if budget > 0 else "（预算未设置）")
                + ("，有促销优惠" if promotion else "")
                + f"，价格价值评分 {pv_score:.1f}"
            ),
            weighted_contribution=pv_score * w,
        ))

        # ------------------------------------------------------------------ #
        # 2. Brand Match
        # ------------------------------------------------------------------ #
        w = weights["brand_match"]
        target_brand = context.get("target_brand", "").lower().strip()
        product_brand = context.get("product_brand", "").lower().strip()
        authorized = bool(context.get("is_authorized_dealer", False))

        if not target_brand or not product_brand:
            brand_score = 60.0
        elif target_brand == product_brand:
            brand_score = 100.0
            data_present += 2
        elif target_brand in product_brand or product_brand in target_brand:
            brand_score = 80.0
            data_present += 2
        else:
            brand_score = 10.0
            data_present += 2

        if authorized and brand_score >= 80:
            brand_score = min(100.0, brand_score + 10.0)
            data_present += 1

        factors.append(FactorDetail(
            name="brand_match",
            score=brand_score,
            weight=w,
            explanation=(
                f"目标品牌: '{context.get('target_brand', '')}'，"
                f"产品品牌: '{context.get('product_brand', '')}'"
                f"{'（官方授权渠道）' if authorized else ''}，"
                f"品牌匹配评分 {brand_score:.1f}"
            ),
            weighted_contribution=brand_score * w,
        ))

        # ------------------------------------------------------------------ #
        # 3. Spec Match
        # ------------------------------------------------------------------ #
        w = weights["spec_match"]
        required_specs = context.get("required_specs", {})
        product_specs = context.get("product_specs", {})

        if not required_specs:
            spec_score = 70.0
        else:
            matched = 0
            for key, req_val in required_specs.items():
                prod_val = product_specs.get(key)
                if prod_val is None:
                    continue
                if isinstance(req_val, (int, float)) and isinstance(prod_val, (int, float)):
                    if prod_val >= req_val * 0.95:
                        matched += 1
                elif str(req_val).lower() == str(prod_val).lower():
                    matched += 1
            spec_score = (matched / len(required_specs)) * 100.0
            data_present += 1

        factors.append(FactorDetail(
            name="spec_match",
            score=spec_score,
            weight=w,
            explanation=(
                f"需求规格 {len(required_specs)} 项"
                + (
                    f"，匹配 {int(spec_score * len(required_specs) / 100)} 项"
                    if required_specs
                    else "（未指定规格需求）"
                )
                + f"，规格匹配评分 {spec_score:.1f}"
            ),
            weighted_contribution=spec_score * w,
        ))

        # ------------------------------------------------------------------ #
        # 4. Availability
        # ------------------------------------------------------------------ #
        w = weights["availability"]
        in_stock = bool(context.get("in_stock", True))
        delivery_days = int(context.get("delivery_time_days", 7))

        if not in_stock:
            avail_score = 20.0
        elif delivery_days <= 1:
            avail_score = 100.0
        elif delivery_days <= 3:
            avail_score = 100.0 - (delivery_days - 1) / 2 * 15.0
        elif delivery_days <= 7:
            avail_score = 85.0 - (delivery_days - 3) / 4 * 25.0
        else:
            avail_score = max(30.0, 60.0 - (delivery_days - 7) * 3.0)

        for k in ["in_stock", "delivery_time_days"]:
            if k in context:
                data_present += 1

        factors.append(FactorDetail(
            name="availability",
            score=avail_score,
            weight=w,
            explanation=(
                f"{'现货' if in_stock else '无货/预售'}，"
                f"预计到货 {delivery_days} 天，"
                f"库存&交付评分 {avail_score:.1f}"
            ),
            weighted_contribution=avail_score * w,
        ))

        # ------------------------------------------------------------------ #
        # 5. Review Score
        # ------------------------------------------------------------------ #
        w = weights["review_score"]
        avg_rating = float(context.get("average_rating", 3.0))
        review_count = int(context.get("review_count", 0))

        base_review_score = (avg_rating / 5.0) * 100.0
        if review_count >= 1000:
            count_multiplier = 1.0
        elif review_count >= 100:
            count_multiplier = 0.85 + (review_count - 100) / 900 * 0.15
        elif review_count >= 10:
            count_multiplier = 0.65 + (review_count - 10) / 90 * 0.20
        else:
            count_multiplier = max(0.5, review_count / 10 * 0.65)

        review_score = base_review_score * count_multiplier

        for k in ["average_rating", "review_count"]:
            if k in context:
                data_present += 1

        factors.append(FactorDetail(
            name="review_score",
            score=review_score,
            weight=w,
            explanation=(
                f"用户评分 {avg_rating:.1f}/5.0（{review_count} 条评价），"
                f"可信度权重 {count_multiplier:.2f}，"
                f"用户口碑评分 {review_score:.1f}"
            ),
            weighted_contribution=review_score * w,
        ))

        # ------------------------------------------------------------------ #
        # Aggregate
        # ------------------------------------------------------------------ #
        total_score = round(
            min(100.0, max(0.0, sum(f.weighted_contribution for f in factors))), 2
        )
        dimension_scores = {f.name: round(f.score, 2) for f in factors}
        grade = _grade_from_score(total_score)

        completeness = data_present / _TOTAL_SIGNALS
        confidence = round(min(1.0, completeness), 3)
        missing = 1.0 - completeness
        score_lower = round(max(0.0, total_score - missing * 15), 2)
        score_upper = round(min(100.0, total_score + missing * 10), 2)

        # LLM adjustments
        llm_adjusted_score: Optional[float] = None
        llm_adjusted_grade: Optional[Grade] = None

        if llm_adjustments:
            adj_total = 0.0
            for f in factors:
                delta = max(-20.0, min(20.0, float(llm_adjustments.get(f.name, 0.0))))
                adj_score = max(0.0, min(100.0, f.score + delta))
                adj_total += adj_score * f.weight
            llm_adjusted_score = round(min(100.0, max(0.0, adj_total)), 2)
            llm_adjusted_grade = _grade_from_score(llm_adjusted_score)
            logger.info(
                "B2C-Known LLM adjustments applied: %.2f → %.2f (%s)",
                total_score, llm_adjusted_score, llm_adjusted_grade,
            )

        logger.info(
            "B2C-Known score: total=%.2f grade=%s confidence=%.3f ci=[%.1f, %.1f]",
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
b2c_known_scorer = B2CKnownScorerModel()
