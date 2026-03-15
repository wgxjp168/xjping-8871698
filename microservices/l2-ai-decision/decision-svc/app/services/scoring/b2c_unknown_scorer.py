"""
B2C Unknown-Brand Scoring Model (B2C未定品牌评分).

Used when the buyer has NOT committed to a specific brand and we are ranking
candidate products to surface the best options.  Returns a ScoreResult for a
single candidate; callers iterate over a product list and sort by total_score.

New in this revision:
  - score_with_llm_adjustments(): applies LLM-suggested dimension deltas.
  - Confidence interval (lower_bound, upper_bound) from data completeness.
  - Dynamic weight adjustment based on buyer priority signals.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from app.models.schemas import FactorDetail, Grade, ScoreResult

logger = logging.getLogger(__name__)

_BASE_WEIGHTS: dict[str, float] = {
    "category_fit": 0.25,
    "budget_match": 0.30,
    "feature_richness": 0.20,
    "popularity": 0.15,
    "value_for_money": 0.10,
}

_TOTAL_SIGNALS = 13


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
    Adjust weights for B2C-Unknown based on context signals:
      - popularity_sensitive=true  → popularity weight + 0.05
      - budget_strict=true         → budget_match weight + 0.05
      - feature_focused=true       → feature_richness weight + 0.05
    """
    weights = dict(_BASE_WEIGHTS)
    boosts: dict[str, float] = {}

    if context.get("popularity_sensitive"):
        boosts["popularity"] = 0.05
    if context.get("budget_strict"):
        boosts["budget_match"] = 0.05
    if context.get("feature_focused"):
        boosts["feature_richness"] = 0.05

    if not boosts:
        return weights

    total_boost = sum(boosts.values())
    drainable = [d for d in ["value_for_money", "category_fit"] if d not in boosts]
    drain_per = total_boost / max(len(drainable), 1)
    for dim in drainable:
        weights[dim] = max(0.02, weights[dim] - drain_per)
    for dim, boost in boosts.items():
        weights[dim] = weights[dim] + boost

    total = sum(weights.values())
    return {k: round(v / total, 6) for k, v in weights.items()}


class B2CUnknownScorerModel:
    """
    Scores candidate products for a B2C buyer who hasn't fixed on a brand.

    Expected context keys:
        user_need_category      str     category/use-case stated by user
        product_category        str     category label of candidate product
        product_tags            list    keyword tags on the product
        product_price           float   listing price
        budget_min              float   lower bound of user budget
        budget_max              float   upper bound of user budget
        product_spec_count      int     number of spec attributes listed
        category_avg_spec_count int     average spec count for this category
        sales_rank              int     sales rank within category (lower=better)
        max_sales_rank          int     worst rank to normalise against (default 1000)
        review_count            int     total number of reviews
        average_rating          float   average review rating (0-5)

    Dynamic weight signals (optional):
        popularity_sensitive    bool
        budget_strict           bool
        feature_focused         bool
    """

    def score(self, context: dict[str, Any]) -> ScoreResult:
        return self._compute(context, llm_adjustments=None)

    def score_with_llm_adjustments(
        self,
        context: dict[str, Any],
        llm_adjustments: Dict[str, float],
    ) -> ScoreResult:
        return self._compute(context, llm_adjustments=llm_adjustments)

    def score_candidates(
        self, candidates: List[dict[str, Any]]
    ) -> List[Tuple[dict[str, Any], ScoreResult]]:
        """
        Score a list of candidate products; return top-3 sorted by score.
        Each candidate dict is the scoring context for one product.
        """
        scored = [(c, self._compute(c, llm_adjustments=None)) for c in candidates]
        scored.sort(key=lambda x: x[1].total_score, reverse=True)
        return scored[:3]

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
        data_present = 0

        # ------------------------------------------------------------------ #
        # 1. Category Fit
        # ------------------------------------------------------------------ #
        w = weights["category_fit"]
        user_need = context.get("user_need_category", "").lower()
        prod_cat = context.get("product_category", "").lower()
        prod_tags = [t.lower() for t in context.get("product_tags", [])]

        if not user_need:
            cat_score = 60.0
        elif user_need == prod_cat:
            cat_score = 100.0
            data_present += 2
        elif user_need in prod_cat or prod_cat in user_need:
            cat_score = 85.0
            data_present += 2
        else:
            user_tokens = set(user_need.split())
            tag_hits = sum(1 for tok in user_tokens if any(tok in t for t in prod_tags))
            if tag_hits > 0:
                cat_score = 60.0 + min(30.0, tag_hits * 10.0)
                data_present += 1
            else:
                cat_score = 30.0

        factors.append(FactorDetail(
            name="category_fit",
            score=cat_score,
            weight=w,
            explanation=(
                f"用户需求类别: '{context.get('user_need_category', '')}'，"
                f"产品类别: '{context.get('product_category', '')}'，"
                f"类别匹配评分 {cat_score:.1f}"
            ),
            weighted_contribution=cat_score * w,
        ))

        # ------------------------------------------------------------------ #
        # 2. Budget Match
        # ------------------------------------------------------------------ #
        w = weights["budget_match"]
        price = float(context.get("product_price", 0))
        budget_min = float(context.get("budget_min", 0))
        budget_max = float(context.get("budget_max", 0))

        if price <= 0 or (budget_min <= 0 and budget_max <= 0):
            budget_score = 60.0
        else:
            if budget_max <= 0:
                budget_max = budget_min * 1.5
            if budget_min <= 0:
                budget_min = 0

            if budget_min <= price <= budget_max:
                sweet_spot = budget_min + (budget_max - budget_min) * 0.85
                distance = abs(price - sweet_spot) / (budget_max - budget_min + 1)
                budget_score = 100.0 - distance * 20.0
            elif price < budget_min:
                ratio = price / budget_min
                budget_score = 70.0 + ratio * 15.0
            else:
                over_ratio = (price - budget_max) / (budget_max + 1)
                budget_score = max(5.0, 75.0 - over_ratio * 100.0)
            data_present += 3

        factors.append(FactorDetail(
            name="budget_match",
            score=budget_score,
            weight=w,
            explanation=(
                f"价格 ¥{price:.2f}，预算范围 ¥{budget_min:.2f}-¥{budget_max:.2f}，"
                f"预算匹配评分 {budget_score:.1f}"
            ),
            weighted_contribution=budget_score * w,
        ))

        # ------------------------------------------------------------------ #
        # 3. Feature Richness
        # ------------------------------------------------------------------ #
        w = weights["feature_richness"]
        spec_count = int(context.get("product_spec_count", 0))
        avg_spec = max(1, int(context.get("category_avg_spec_count", 10)))

        ratio_spec = spec_count / avg_spec
        if ratio_spec >= 1.5:
            feat_score = 100.0
        elif ratio_spec >= 1.0:
            feat_score = 70.0 + (ratio_spec - 1.0) / 0.5 * 30.0
        elif ratio_spec >= 0.5:
            feat_score = 40.0 + (ratio_spec - 0.5) / 0.5 * 30.0
        else:
            feat_score = max(0.0, ratio_spec / 0.5 * 40.0)

        for k in ["product_spec_count", "category_avg_spec_count"]:
            if k in context:
                data_present += 1

        factors.append(FactorDetail(
            name="feature_richness",
            score=feat_score,
            weight=w,
            explanation=(
                f"产品规格数量 {spec_count}，类目均值 {avg_spec}"
                f"（比率 {ratio_spec:.2f}），功能丰富度评分 {feat_score:.1f}"
            ),
            weighted_contribution=feat_score * w,
        ))

        # ------------------------------------------------------------------ #
        # 4. Popularity
        # ------------------------------------------------------------------ #
        w = weights["popularity"]
        sales_rank = int(context.get("sales_rank", 500))
        max_rank = max(1, int(context.get("max_sales_rank", 1000)))
        review_count = int(context.get("review_count", 0))
        avg_rating = float(context.get("average_rating", 3.0))

        sales_rank_score = max(0.0, (1.0 - (sales_rank - 1) / max_rank) * 100.0)

        if review_count <= 0:
            review_count_score = 0.0
        elif review_count >= 10000:
            review_count_score = 100.0
        else:
            review_count_score = min(
                100.0,
                math.log10(review_count + 1) / math.log10(10001) * 100.0,
            )

        rating_score = (avg_rating / 5.0) * 100.0
        popularity_score = (
            sales_rank_score * 0.50
            + review_count_score * 0.30
            + rating_score * 0.20
        )

        for k in ["sales_rank", "review_count", "average_rating"]:
            if k in context:
                data_present += 1

        factors.append(FactorDetail(
            name="popularity",
            score=popularity_score,
            weight=w,
            explanation=(
                f"销售排名第 {sales_rank}（评分 {sales_rank_score:.1f}），"
                f"{review_count} 条评价（评分 {review_count_score:.1f}），"
                f"均分 {avg_rating:.1f}/5，综合热度 {popularity_score:.1f}"
            ),
            weighted_contribution=popularity_score * w,
        ))

        # ------------------------------------------------------------------ #
        # 5. Value for Money
        # ------------------------------------------------------------------ #
        w = weights["value_for_money"]

        if price > 0 and spec_count > 0:
            features_per_yuan = spec_count / price
            ref = 0.10  # 0.1 spec/¥ = 100 pts
            vfm_ratio = features_per_yuan / ref
            vfm_score = min(100.0, 75.0 + vfm_ratio * 10.0) if vfm_ratio >= 1.0 else max(10.0, vfm_ratio * 75.0)
            data_present += 1
        else:
            vfm_score = 55.0

        if price > 0:
            rating_per_100_yuan = (avg_rating / 5.0) * 100.0 / (price / 100.0 + 1)
            vfm_score = vfm_score * 0.6 + min(100.0, rating_per_100_yuan * 5) * 0.4

        vfm_score = max(0.0, min(100.0, vfm_score))

        factors.append(FactorDetail(
            name="value_for_money",
            score=vfm_score,
            weight=w,
            explanation=(
                f"每元功能数 {spec_count / max(price, 1):.4f}，"
                f"性价比综合评分 {vfm_score:.1f}"
            ),
            weighted_contribution=vfm_score * w,
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
                "B2C-Unknown LLM adjustments applied: %.2f → %.2f (%s)",
                total_score, llm_adjusted_score, llm_adjusted_grade,
            )

        logger.info(
            "B2C-Unknown score: total=%.2f grade=%s confidence=%.3f ci=[%.1f, %.1f]",
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
b2c_unknown_scorer = B2CUnknownScorerModel()
