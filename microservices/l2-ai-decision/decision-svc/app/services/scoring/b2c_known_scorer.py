"""
B2C Known-Brand Scoring Model (B2C已定品牌评分).

Used when the buyer has specified a target brand and we are evaluating whether
a particular product listing matches their needs.
"""
from __future__ import annotations

import logging
from typing import Any

from app.models.schemas import FactorDetail, Grade, ScoreResult

logger = logging.getLogger(__name__)

DIMENSION_WEIGHTS: dict[str, float] = {
    "price_value": 0.30,
    "brand_match": 0.25,
    "spec_match": 0.25,
    "availability": 0.10,
    "review_score": 0.10,
}


def _grade_from_score(score: float) -> Grade:
    if score >= 85:
        return Grade.A
    if score >= 70:
        return Grade.B
    if score >= 55:
        return Grade.C
    return Grade.D


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
    """

    def score(self, context: dict[str, Any]) -> ScoreResult:
        factors: list[FactorDetail] = []
        data_present = 0

        # ------------------------------------------------------------------ #
        # 1. Price / Value (weight=0.30)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["price_value"]
        product_price: float = float(context.get("product_price", 0))
        budget: float = float(context.get("budget", 0))
        promotion: bool = bool(context.get("promotion_available", False))

        if budget > 0 and product_price > 0:
            ratio = product_price / budget  # <1 = under budget, >1 = over budget
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
            pv_score = 60.0  # neutral default

        if promotion:
            pv_score = min(100.0, pv_score + 10.0)
            data_present += 1

        pv_explanation = (
            f"产品价格 ¥{product_price:.2f}，预算 ¥{budget:.2f}"
            + (f"（价格比率 {product_price / budget:.2f}）" if budget > 0 else "（预算未设置）")
            + ("，有促销优惠" if promotion else "")
            + f"，价格价值评分 {pv_score:.1f}"
        )
        factors.append(FactorDetail(
            name="price_value",
            score=pv_score,
            weight=weight,
            explanation=pv_explanation,
            weighted_contribution=pv_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # 2. Brand Match (weight=0.25)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["brand_match"]
        target_brand: str = context.get("target_brand", "").lower().strip()
        product_brand: str = context.get("product_brand", "").lower().strip()
        authorized: bool = bool(context.get("is_authorized_dealer", False))

        if not target_brand or not product_brand:
            brand_score = 60.0
        elif target_brand == product_brand:
            brand_score = 100.0
            data_present += 2
        elif target_brand in product_brand or product_brand in target_brand:
            # Partial match (e.g. "Apple" vs "Apple Inc")
            brand_score = 80.0
            data_present += 2
        else:
            brand_score = 10.0
            data_present += 2

        if authorized and brand_score >= 80:
            brand_score = min(100.0, brand_score + 10.0)
            data_present += 1

        brand_explanation = (
            f"目标品牌: '{context.get('target_brand', '')}'"
            f"，产品品牌: '{context.get('product_brand', '')}'"
            f"{'（官方授权渠道）' if authorized else ''}"
            f"，品牌匹配评分 {brand_score:.1f}"
        )
        factors.append(FactorDetail(
            name="brand_match",
            score=brand_score,
            weight=weight,
            explanation=brand_explanation,
            weighted_contribution=brand_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # 3. Spec Match (weight=0.25)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["spec_match"]
        required_specs: dict = context.get("required_specs", {})
        product_specs: dict = context.get("product_specs", {})

        if not required_specs:
            spec_score = 70.0  # No requirements stated → neutral
        else:
            matched = 0
            total_req = len(required_specs)
            for key, req_val in required_specs.items():
                prod_val = product_specs.get(key)
                if prod_val is None:
                    continue
                if isinstance(req_val, (int, float)) and isinstance(prod_val, (int, float)):
                    if prod_val >= req_val * 0.95:  # 5% tolerance
                        matched += 1
                elif str(req_val).lower() == str(prod_val).lower():
                    matched += 1
            overlap = matched / total_req if total_req > 0 else 0.0
            spec_score = overlap * 100.0
            data_present += 1

        spec_explanation = (
            f"需求规格 {len(required_specs)} 项"
            + (
                f"，匹配 {int(spec_score * len(required_specs) / 100)} 项"
                if required_specs
                else "（未指定规格需求）"
            )
            + f"，规格匹配评分 {spec_score:.1f}"
        )
        factors.append(FactorDetail(
            name="spec_match",
            score=spec_score,
            weight=weight,
            explanation=spec_explanation,
            weighted_contribution=spec_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # 4. Availability (weight=0.10)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["availability"]
        in_stock: bool = bool(context.get("in_stock", True))
        delivery_days: int = int(context.get("delivery_time_days", 7))

        if not in_stock:
            avail_score = 20.0
        else:
            if delivery_days <= 1:
                avail_score = 100.0
            elif delivery_days <= 3:
                avail_score = 100.0 - (delivery_days - 1) / 2 * 15.0
            elif delivery_days <= 7:
                avail_score = 85.0 - (delivery_days - 3) / 4 * 25.0
            else:
                avail_score = max(30.0, 60.0 - (delivery_days - 7) * 3.0)

        data_present += 1 if "in_stock" in context else 0
        data_present += 1 if "delivery_time_days" in context else 0

        avail_explanation = (
            f"{'现货' if in_stock else '无货/预售'}"
            f"，预计到货 {delivery_days} 天"
            f"，库存&交付评分 {avail_score:.1f}"
        )
        factors.append(FactorDetail(
            name="availability",
            score=avail_score,
            weight=weight,
            explanation=avail_explanation,
            weighted_contribution=avail_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # 5. Review Score (weight=0.10)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["review_score"]
        avg_rating: float = float(context.get("average_rating", 3.0))
        review_count: int = int(context.get("review_count", 0))

        # Core score: rating normalised to 0-100
        base_review_score = (avg_rating / 5.0) * 100.0

        # Weight by review count (more reviews = higher confidence multiplier)
        if review_count >= 1000:
            count_multiplier = 1.0
        elif review_count >= 100:
            count_multiplier = 0.85 + (review_count - 100) / 900 * 0.15
        elif review_count >= 10:
            count_multiplier = 0.65 + (review_count - 10) / 90 * 0.20
        else:
            count_multiplier = max(0.5, review_count / 10 * 0.65)

        review_score = base_review_score * count_multiplier

        data_present += 1 if "average_rating" in context else 0
        data_present += 1 if "review_count" in context else 0

        review_explanation = (
            f"用户评分 {avg_rating:.1f}/5.0（{review_count} 条评价）"
            f"，评论可信度权重 {count_multiplier:.2f}"
            f"，用户口碑评分 {review_score:.1f}"
        )
        factors.append(FactorDetail(
            name="review_score",
            score=review_score,
            weight=weight,
            explanation=review_explanation,
            weighted_contribution=review_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # Aggregate
        # ------------------------------------------------------------------ #
        total_score = sum(f.weighted_contribution for f in factors)
        total_score = round(min(100.0, max(0.0, total_score)), 2)
        dimension_scores = {f.name: round(f.score, 2) for f in factors}
        grade = _grade_from_score(total_score)

        # Confidence driven by data completeness (max 11 data points above)
        confidence = round(min(1.0, data_present / 11), 3)

        logger.info(
            "B2C-Known score: total=%.2f grade=%s confidence=%.3f",
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
b2c_known_scorer = B2CKnownScorerModel()
