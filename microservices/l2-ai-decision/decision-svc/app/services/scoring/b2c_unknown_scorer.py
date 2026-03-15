"""
B2C Unknown-Brand Scoring Model (B2C未定品牌评分).

Used when the buyer has NOT committed to a specific brand and we are ranking
candidate products to surface the best options.  Returns a ScoreResult for a
single candidate; callers iterate over a product list and sort by total_score.
"""
from __future__ import annotations

import logging
from typing import Any

from app.models.schemas import FactorDetail, Grade, ScoreResult

logger = logging.getLogger(__name__)

DIMENSION_WEIGHTS: dict[str, float] = {
    "category_fit": 0.25,
    "budget_match": 0.30,
    "feature_richness": 0.20,
    "popularity": 0.15,
    "value_for_money": 0.10,
}


def _grade_from_score(score: float) -> Grade:
    if score >= 85:
        return Grade.A
    if score >= 70:
        return Grade.B
    if score >= 55:
        return Grade.C
    return Grade.D


class B2CUnknownScorerModel:
    """
    Scores candidate products for a B2C buyer who hasn't fixed on a brand.

    Expected context keys:
        user_need_category      str     category/use-case stated by user (e.g. 'gaming laptop')
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
    """

    def score(self, context: dict[str, Any]) -> ScoreResult:
        factors: list[FactorDetail] = []
        data_present = 0

        # ------------------------------------------------------------------ #
        # 1. Category Fit (weight=0.25)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["category_fit"]
        user_need: str = context.get("user_need_category", "").lower()
        prod_cat: str = context.get("product_category", "").lower()
        prod_tags: list[str] = [t.lower() for t in context.get("product_tags", [])]

        if not user_need:
            cat_score = 60.0
        elif user_need == prod_cat:
            cat_score = 100.0
            data_present += 2
        elif user_need in prod_cat or prod_cat in user_need:
            cat_score = 85.0
            data_present += 2
        else:
            # Check tag overlap
            user_tokens = set(user_need.split())
            tag_hits = sum(1 for tok in user_tokens if any(tok in t for t in prod_tags))
            if tag_hits > 0:
                cat_score = 60.0 + min(30.0, tag_hits * 10.0)
                data_present += 1
            else:
                cat_score = 30.0

        cat_explanation = (
            f"用户需求类别: '{context.get('user_need_category', '')}'"
            f"，产品类别: '{context.get('product_category', '')}'"
            f"，标签命中: {sum(1 for t in prod_tags if any(tok in t for tok in user_need.split()))}"
            f"，类别匹配评分 {cat_score:.1f}"
        )
        factors.append(FactorDetail(
            name="category_fit",
            score=cat_score,
            weight=weight,
            explanation=cat_explanation,
            weighted_contribution=cat_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # 2. Budget Match (weight=0.30)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["budget_match"]
        price: float = float(context.get("product_price", 0))
        budget_min: float = float(context.get("budget_min", 0))
        budget_max: float = float(context.get("budget_max", 0))

        if price <= 0 or (budget_min <= 0 and budget_max <= 0):
            budget_score = 60.0
        else:
            if budget_max <= 0:
                budget_max = budget_min * 1.5  # infer max if only min given
            if budget_min <= 0:
                budget_min = 0

            if budget_min <= price <= budget_max:
                # Inside range — best score at ~85% of max (sweet spot)
                sweet_spot = budget_min + (budget_max - budget_min) * 0.85
                distance = abs(price - sweet_spot) / (budget_max - budget_min + 1)
                budget_score = 100.0 - distance * 20.0
            elif price < budget_min:
                # Below min budget — slight discount concern
                ratio = price / budget_min
                budget_score = 70.0 + ratio * 15.0  # closer to min = better
            else:
                # Over max budget
                over_ratio = (price - budget_max) / (budget_max + 1)
                budget_score = max(5.0, 75.0 - over_ratio * 100.0)

            data_present += 3

        budget_explanation = (
            f"价格 ¥{price:.2f}，预算范围 ¥{budget_min:.2f}-¥{budget_max:.2f}"
            f"，预算匹配评分 {budget_score:.1f}"
        )
        factors.append(FactorDetail(
            name="budget_match",
            score=budget_score,
            weight=weight,
            explanation=budget_explanation,
            weighted_contribution=budget_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # 3. Feature Richness (weight=0.20)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["feature_richness"]
        spec_count: int = int(context.get("product_spec_count", 0))
        avg_spec: int = int(context.get("category_avg_spec_count", 10))

        if avg_spec <= 0:
            avg_spec = 10

        ratio = spec_count / avg_spec
        if ratio >= 1.5:
            feat_score = 100.0
        elif ratio >= 1.0:
            feat_score = 70.0 + (ratio - 1.0) / 0.5 * 30.0
        elif ratio >= 0.5:
            feat_score = 40.0 + (ratio - 0.5) / 0.5 * 30.0
        else:
            feat_score = max(0.0, ratio / 0.5 * 40.0)

        if "product_spec_count" in context:
            data_present += 1
        if "category_avg_spec_count" in context:
            data_present += 1

        feat_explanation = (
            f"产品规格数量 {spec_count}，类目均值 {avg_spec}"
            f"（比率 {ratio:.2f}），功能丰富度评分 {feat_score:.1f}"
        )
        factors.append(FactorDetail(
            name="feature_richness",
            score=feat_score,
            weight=weight,
            explanation=feat_explanation,
            weighted_contribution=feat_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # 4. Popularity (weight=0.15)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["popularity"]
        sales_rank: int = int(context.get("sales_rank", 500))
        max_rank: int = int(context.get("max_sales_rank", 1000))
        review_count: int = int(context.get("review_count", 0))
        avg_rating: float = float(context.get("average_rating", 3.0))

        if max_rank <= 0:
            max_rank = 1000

        # Sales rank score: rank=1 → 100, rank=max_rank → 0
        sales_rank_score = max(0.0, (1.0 - (sales_rank - 1) / max_rank) * 100.0)

        # Review count score: log-normalised
        import math
        if review_count <= 0:
            review_count_score = 0.0
        elif review_count >= 10000:
            review_count_score = 100.0
        else:
            review_count_score = min(100.0, math.log10(review_count + 1) / math.log10(10001) * 100.0)

        # Blend: sales_rank 50% + review_count 30% + rating 20%
        rating_score = (avg_rating / 5.0) * 100.0
        popularity_score = (
            sales_rank_score * 0.50
            + review_count_score * 0.30
            + rating_score * 0.20
        )

        if "sales_rank" in context:
            data_present += 1
        if "review_count" in context:
            data_present += 1
        if "average_rating" in context:
            data_present += 1

        pop_explanation = (
            f"销售排名第 {sales_rank}（评分 {sales_rank_score:.1f}），"
            f"{review_count} 条评价（评分 {review_count_score:.1f}），"
            f"均分 {avg_rating:.1f}/5（评分 {rating_score:.1f}），"
            f"综合热度 {popularity_score:.1f}"
        )
        factors.append(FactorDetail(
            name="popularity",
            score=popularity_score,
            weight=weight,
            explanation=pop_explanation,
            weighted_contribution=popularity_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # 5. Value for Money (weight=0.10)
        # ------------------------------------------------------------------ #
        weight = DIMENSION_WEIGHTS["value_for_money"]

        # Features-per-yuan: normalised against a reference of 1 spec / ¥100
        if price > 0 and spec_count > 0:
            features_per_yuan = spec_count / price  # specs per ¥
            # Reference: 0.1 spec/¥ → 100 points
            ref = 0.10
            vfm_ratio = features_per_yuan / ref
            if vfm_ratio >= 1.0:
                vfm_score = min(100.0, 75.0 + vfm_ratio * 10.0)
            else:
                vfm_score = max(10.0, vfm_ratio * 75.0)
            data_present += 1
        else:
            vfm_score = 55.0  # neutral default

        # Also factor in rating vs price
        if price > 0:
            rating_per_100_yuan = (avg_rating / 5.0) * 100.0 / (price / 100.0 + 1)
            vfm_score = vfm_score * 0.6 + min(100.0, rating_per_100_yuan * 5) * 0.4

        vfm_score = max(0.0, min(100.0, vfm_score))

        vfm_explanation = (
            f"每元功能数 {spec_count / max(price, 1):.4f}"
            f"，性价比综合评分 {vfm_score:.1f}"
        )
        factors.append(FactorDetail(
            name="value_for_money",
            score=vfm_score,
            weight=weight,
            explanation=vfm_explanation,
            weighted_contribution=vfm_score * weight,
        ))

        # ------------------------------------------------------------------ #
        # Aggregate
        # ------------------------------------------------------------------ #
        total_score = sum(f.weighted_contribution for f in factors)
        total_score = round(min(100.0, max(0.0, total_score)), 2)
        dimension_scores = {f.name: round(f.score, 2) for f in factors}
        grade = _grade_from_score(total_score)

        # Confidence based on data completeness (13 data points above)
        confidence = round(min(1.0, data_present / 13), 3)

        logger.info(
            "B2C-Unknown score: total=%.2f grade=%s confidence=%.3f",
            total_score, grade, confidence,
        )

        return ScoreResult(
            total_score=total_score,
            dimension_scores=dimension_scores,
            grade=grade,
            confidence=confidence,
            factors=factors,
        )

    def score_candidates(
        self, candidates: list[dict[str, Any]]
    ) -> list[tuple[dict[str, Any], ScoreResult]]:
        """
        Score a list of candidate products and return the top-3 sorted by score.

        Each candidate dict is the scoring context for one product.
        Returns list of (candidate_context, ScoreResult) tuples, best first.
        """
        scored = [(c, self.score(c)) for c in candidates]
        scored.sort(key=lambda x: x[1].total_score, reverse=True)
        return scored[:3]


# Singleton
b2c_unknown_scorer = B2CUnknownScorerModel()
