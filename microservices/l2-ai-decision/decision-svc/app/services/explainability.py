"""
ExplainabilityEngine — SHAP-inspired feature importance and natural-language explanations.

Provides:
  - Feature importance ranking based on weighted contribution deltas
  - Chinese natural-language explanations
  - Counterfactual reasoning ("if X changed, score would increase by Y")
"""
from __future__ import annotations

import logging
from typing import Any

from app.models.schemas import FactorDetail, Grade, ScoreResult

logger = logging.getLogger(__name__)

_GRADE_THRESHOLDS = {"A": 85.0, "B": 70.0, "C": 55.0, "D": 0.0}

_GRADE_LABELS = {
    Grade.A: "优秀",
    Grade.B: "良好",
    Grade.C: "一般",
    Grade.D: "较差",
}

_DIMENSION_CN = {
    "price_competitiveness": "价格竞争力",
    "supplier_reliability": "供应商可靠性",
    "delivery_capability": "交付能力",
    "quality_compliance": "质量合规",
    "after_service": "售后服务",
    "min_order_qty_fit": "MOQ 匹配度",
    "price_value": "价格价值",
    "brand_match": "品牌匹配",
    "spec_match": "规格匹配",
    "availability": "现货可用性",
    "review_score": "用户口碑",
    "category_fit": "类别匹配",
    "budget_match": "预算匹配",
    "feature_richness": "功能丰富度",
    "popularity": "市场热度",
    "value_for_money": "性价比",
}


class ExplainabilityEngine:
    """Provides SHAP-inspired explanations for scoring decisions."""

    # ------------------------------------------------------------------ #
    # Main entry point
    # ------------------------------------------------------------------ #

    def explain_score(self, score_result: ScoreResult, context: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a full explainability payload for the given ScoreResult.

        Returns a dict containing:
          - feature_importance: ranked list of factor contributions
          - top_positive_factors: top-N positive drivers
          - top_negative_factors: top-N negative drivers
          - natural_language_summary: Chinese text explanation
          - counterfactual: "what if" improvement text
        """
        importance = self._compute_feature_importance(score_result.factors)
        top_positive = self.highlight_key_factors(importance, top_n=3, positive_only=True)
        top_negative = self.highlight_key_factors(importance, top_n=3, positive_only=False)
        nl_summary = self.generate_natural_language_explanation(importance, locale="zh")
        counterfactual = self.generate_counterfactual(score_result, target_grade=None)

        return {
            "feature_importance": importance,
            "top_positive_factors": top_positive,
            "top_negative_factors": top_negative,
            "natural_language_summary": nl_summary,
            "counterfactual": counterfactual,
            "total_score": score_result.total_score,
            "grade": score_result.grade,
            "confidence": score_result.confidence,
        }

    # ------------------------------------------------------------------ #
    # Feature importance (SHAP-inspired)
    # ------------------------------------------------------------------ #

    def _compute_feature_importance(
        self, factors: list[FactorDetail]
    ) -> list[dict[str, Any]]:
        """
        Compute feature importance as the signed difference between a factor's
        weighted contribution and the expected contribution if that dimension
        were at the mean score (50 points).

        Positive importance = this factor is driving the score UP.
        Negative importance = this factor is dragging the score DOWN.
        """
        importance_list: list[dict[str, Any]] = []
        baseline_per_weight = 50.0  # baseline score if every dimension were 50

        for factor in factors:
            expected_contribution = baseline_per_weight * factor.weight
            actual_contribution = factor.weighted_contribution
            importance = actual_contribution - expected_contribution  # signed delta

            importance_list.append(
                {
                    "name": factor.name,
                    "display_name": _DIMENSION_CN.get(factor.name, factor.name),
                    "raw_score": round(factor.score, 2),
                    "weight": factor.weight,
                    "weighted_contribution": round(actual_contribution, 4),
                    "importance": round(importance, 4),
                    "direction": "positive" if importance >= 0 else "negative",
                    "explanation": factor.explanation,
                }
            )

        # Sort by absolute importance descending
        importance_list.sort(key=lambda x: abs(x["importance"]), reverse=True)
        return importance_list

    # ------------------------------------------------------------------ #
    # Top factors
    # ------------------------------------------------------------------ #

    def highlight_key_factors(
        self,
        factors: list[dict[str, Any]],
        top_n: int = 3,
        positive_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Return top-N positive or negative factors sorted by absolute importance."""
        direction = "positive" if positive_only else "negative"
        filtered = [f for f in factors if f["direction"] == direction]
        filtered.sort(key=lambda x: abs(x["importance"]), reverse=True)
        return filtered[:top_n]

    # ------------------------------------------------------------------ #
    # Natural language explanation
    # ------------------------------------------------------------------ #

    def generate_natural_language_explanation(
        self,
        factors: list[dict[str, Any]],
        locale: str = "zh",
    ) -> str:
        """Generate a Chinese natural-language explanation from factor importance list."""
        if not factors:
            return "暂无足够数据生成详细解释。"

        positives = [f for f in factors if f["direction"] == "positive"]
        negatives = [f for f in factors if f["direction"] == "negative"]

        parts: list[str] = []

        if positives:
            top_pos_names = "、".join(
                f["display_name"] for f in positives[:3]
            )
            parts.append(f"该产品的主要优势在于{top_pos_names}")

        if negatives:
            top_neg_names = "、".join(
                f["display_name"] for f in negatives[:3]
            )
            parts.append(f"主要不足体现在{top_neg_names}")

        # Highlight the strongest driver
        if factors:
            top = factors[0]
            direction_word = "提升" if top["direction"] == "positive" else "拉低"
            parts.append(
                f"其中「{top['display_name']}」对总分的影响最大"
                f"（贡献 {top['importance']:+.2f} 分），"
                f"{direction_word}了整体评分"
            )

        return "。".join(parts) + "。"

    # ------------------------------------------------------------------ #
    # Counterfactual
    # ------------------------------------------------------------------ #

    def generate_counterfactual(
        self,
        score_result: ScoreResult,
        target_grade: Grade | None,
    ) -> str:
        """
        Generate a counterfactual explanation:
        'If X were improved to Y, the score would increase by Z.'
        """
        current_score = score_result.total_score
        current_grade = score_result.grade

        # Determine target grade and required score
        if target_grade is None:
            # Auto-select next grade up
            grade_order = [Grade.D, Grade.C, Grade.B, Grade.A]
            current_idx = grade_order.index(current_grade)
            if current_idx >= len(grade_order) - 1:
                return f"当前评分 {current_score:.1f} 分，已达到最高评级（A级），继续保持即可。"
            target_grade = grade_order[current_idx + 1]

        target_score = _GRADE_THRESHOLDS[target_grade.value]
        gap = target_score - current_score

        if gap <= 0:
            return f"当前评分 {current_score:.1f} 分，已达到{_GRADE_LABELS[target_grade]}评级标准。"

        # Find the lowest-scoring factor (biggest drag)
        if not score_result.factors:
            return (
                f"当前评分 {current_score:.1f} 分，还需提升 {gap:.1f} 分方可达到"
                f"{_GRADE_LABELS[target_grade]}（{target_grade.value}级）标准。"
            )

        lowest_factor = min(score_result.factors, key=lambda f: f.score)
        dim_name = _DIMENSION_CN.get(lowest_factor.name, lowest_factor.name)

        # How much would total score increase if this factor went to 100?
        potential_gain = (100.0 - lowest_factor.score) * lowest_factor.weight
        # Required gain from this factor alone
        required_improvement = gap / lowest_factor.weight if lowest_factor.weight > 0 else 100

        return (
            f"当前评分 {current_score:.1f} 分（{_GRADE_LABELS[current_grade]}），"
            f"距{_GRADE_LABELS[target_grade]}（{target_grade.value}级）还差 {gap:.1f} 分。"
            f"建议重点改善「{dim_name}」维度（当前 {lowest_factor.score:.1f} 分），"
            f"若该项提升至满分可带来约 {potential_gain:.1f} 分的总分增益。"
        )


# Singleton
explainability_engine = ExplainabilityEngine()
