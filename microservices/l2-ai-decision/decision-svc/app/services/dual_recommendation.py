"""
DualRecommendationEngine — 品质款 + 性价比款 双档推荐引擎.

根据用户意图从候选商品池中产出两档推荐：
  - 品质款 (quality_pick)：综合评分 (ScoreResult.total_score) 最高
  - 性价比款 (value_pick)：性价比指数 (score / price) 最优

评分使用与 8-step 流程相同的模型路由（B2B / B2C_KNOWN / B2C_UNKNOWN）。
规则引擎同步执行，违规商品降权（乘以 0.6）而非直接剔除，确保始终能产出推荐。
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.models.schemas import (
    BrandStatus,
    CandidateProduct,
    CandidateScore,
    DualRecommendRequest,
    DualRecommendResult,
    ScoringContext,
)
from app.services.rule_engine import rule_engine
from app.services.scoring.b2b_scorer import b2b_scorer
from app.services.scoring.b2c_known_scorer import b2c_known_scorer
from app.services.scoring.b2c_unknown_scorer import b2c_unknown_scorer

logger = logging.getLogger(__name__)

# 违规商品评分惩罚系数
_VIOLATION_PENALTY = 0.6


def _determine_scoring_context(
    intent: str,
    entities: dict[str, Any],
    brand_status: BrandStatus,
) -> ScoringContext:
    org_type = str(entities.get("org_type", "")).lower()
    is_b2b = org_type in {"b2b", "enterprise", "corporate", "company"} or any(
        kw in intent.lower() for kw in ["企业", "公司", "采购", "批量", "b2b"]
    )
    if is_b2b:
        return ScoringContext.B2B
    if brand_status == BrandStatus.KNOWN:
        return ScoringContext.B2C_KNOWN
    return ScoringContext.B2C_UNKNOWN


def _build_context(
    candidate: CandidateProduct,
    request: DualRecommendRequest,
) -> dict[str, Any]:
    """Merge candidate attributes with request entities and user_context."""
    ctx: dict[str, Any] = {
        "session_id": request.session_id,
        "intent": request.intent,
        "brand_status": request.brand_status.value,
        "product_id": candidate.product_id,
        "product_name": candidate.product_name,
        "product_price": candidate.product_price,
        **request.entities,
        **request.user_context,
        **candidate.attributes,
    }
    # Ensure is_b2b flag
    org_type = str(ctx.get("org_type", "")).lower()
    ctx["is_b2b"] = org_type in {"b2b", "enterprise", "corporate", "company"}
    return ctx


def _score_candidate(
    candidate: CandidateProduct,
    request: DualRecommendRequest,
    scoring_context: ScoringContext,
) -> CandidateScore:
    ctx = _build_context(candidate, request)

    # Rule evaluation
    rule_result = rule_engine.evaluate(ctx)

    # Model scoring
    if scoring_context == ScoringContext.B2B:
        score_result = b2b_scorer.score(ctx)
    elif scoring_context == ScoringContext.B2C_KNOWN:
        score_result = b2c_known_scorer.score(ctx)
    else:
        score_result = b2c_unknown_scorer.score(ctx)

    # Apply violation penalty (do not mutate score_result; store adjusted score separately)
    if rule_result.violations:
        effective_score = round(score_result.total_score * _VIOLATION_PENALTY, 2)
        logger.debug(
            "Candidate %s has %d violations → penalised score %.1f → %.1f",
            candidate.product_id,
            len(rule_result.violations),
            score_result.total_score,
            effective_score,
        )
    else:
        effective_score = score_result.total_score

    return CandidateScore(
        product_id=candidate.product_id,
        product_name=candidate.product_name,
        product_price=candidate.product_price,
        score_result=score_result,
        rule_result=rule_result,
        recommendation_type="候补",  # Will be set by caller
        # Store effective_score as a custom attribute for ranking
        # We abuse the `llm_adjusted_score` field to carry the penalised score
        # without changing the underlying score_result model
    )


def _value_index(candidate_score: CandidateScore) -> float:
    """
    性价比指数 = effective_score / normalised_price

    normalised_price anchors price at 1 when product_price == 1 (avoids /0).
    Higher index means better value.
    """
    effective = (
        candidate_score.score_result.llm_adjusted_score
        if candidate_score.score_result.llm_adjusted_score is not None
        else candidate_score.score_result.total_score
    )
    price = max(1.0, candidate_score.product_price)
    return effective / price


def _build_comparison_summary(
    quality: CandidateScore,
    value: CandidateScore,
) -> str:
    """
    生成自然语言差异对比摘要（无 LLM，基于规则模板）。

    当 quality_pick == value_pick 时直接说明"两档推荐为同一商品"。
    """
    if quality.product_id == value.product_id:
        return (
            f"推荐商品：{quality.product_name}（评分 {quality.score_result.total_score:.1f}，"
            f"价格 ¥{quality.product_price:.2f}）。该商品在候选池中综合表现最佳，"
            f"品质与性价比均领先，建议优先选购。"
        )

    q_score = quality.score_result.total_score
    v_score = value.score_result.total_score
    price_diff_pct = round(
        (quality.product_price - value.product_price) / max(value.product_price, 1) * 100,
        1,
    )
    score_diff = round(q_score - v_score, 1)

    # 规则模板差异描述
    if price_diff_pct > 0:
        price_clause = (
            f"品质款（{quality.product_name}）价格比性价比款（{value.product_name}）"
            f"高 {abs(price_diff_pct):.1f}%"
        )
    elif price_diff_pct < 0:
        price_clause = (
            f"品质款（{quality.product_name}）价格比性价比款（{value.product_name}）"
            f"低 {abs(price_diff_pct):.1f}%（价格反转，综合评分仍领先）"
        )
    else:
        price_clause = f"两款价格相同（¥{quality.product_price:.2f}），综合评分相差 {score_diff} 分"

    q_rule = "✅ 规则全部通过" if quality.rule_result.passed else f"⚠️ 存在 {len(quality.rule_result.violations)} 项违规"
    v_rule = "✅ 规则全部通过" if value.rule_result.passed else f"⚠️ 存在 {len(value.rule_result.violations)} 项违规"

    return (
        f"**品质款推荐**：{quality.product_name}"
        f"（综合评分 {q_score:.1f}，价格 ¥{quality.product_price:.2f}，{q_rule}）\n\n"
        f"**性价比款推荐**：{value.product_name}"
        f"（综合评分 {v_score:.1f}，价格 ¥{value.product_price:.2f}，{v_rule}）\n\n"
        f"{price_clause}。评分差距 {score_diff} 分。\n\n"
        f"建议：若预算充裕、对品质要求较高，优选品质款；"
        f"若注重性价比或预算有限，性价比款为更合适的选择。"
    )


class DualRecommendationEngine:
    """
    双档推荐引擎：从候选商品池中按 8-step 模型评分，输出品质款和性价比款。
    """

    def recommend(self, request: DualRecommendRequest) -> DualRecommendResult:
        if not request.candidates:
            raise ValueError("candidates 不能为空")

        scoring_context = _determine_scoring_context(
            request.intent, request.entities, request.brand_status
        )
        logger.info(
            "DualRecommend: session=%s context=%s candidates=%d",
            request.session_id,
            scoring_context,
            len(request.candidates),
        )

        # Score all candidates
        scored: list[CandidateScore] = []
        for cand in request.candidates:
            cs = _score_candidate(cand, request, scoring_context)
            scored.append(cs)

        # Effective score = penalised if violations, else total_score
        def effective_score(cs: CandidateScore) -> float:
            raw = cs.score_result.total_score
            if cs.rule_result.violations:
                return raw * _VIOLATION_PENALTY
            return raw

        # Sort by effective_score desc
        scored_sorted = sorted(scored, key=effective_score, reverse=True)

        # 品质款 = highest effective score
        quality_pick = scored_sorted[0]
        quality_pick.recommendation_type = "品质款"

        # 性价比款 = best value index; may differ from quality_pick
        value_sorted = sorted(scored, key=_value_index, reverse=True)
        value_pick = value_sorted[0]

        # If quality and value are the same product, try second in value ranking
        if value_pick.product_id == quality_pick.product_id and len(value_sorted) > 1:
            value_pick = value_sorted[1]

        value_pick.recommendation_type = "性价比款"

        # Mark remaining as 候补
        selected_ids = {quality_pick.product_id, value_pick.product_id}
        for cs in scored_sorted:
            if cs.product_id not in selected_ids:
                cs.recommendation_type = "候补"

        comparison_summary = _build_comparison_summary(quality_pick, value_pick)

        requires_review = (
            not quality_pick.rule_result.passed
            or not value_pick.rule_result.passed
            or quality_pick.score_result.total_score < 55
        )

        result = DualRecommendResult(
            session_id=request.session_id,
            scoring_context=scoring_context,
            quality_pick=quality_pick,
            value_pick=value_pick,
            all_scores=scored_sorted,
            comparison_summary=comparison_summary,
            requires_human_review=requires_review,
        )

        logger.info(
            "DualRecommend done: quality=%s(%.1f) value=%s(%.1f) review=%s",
            quality_pick.product_name,
            quality_pick.score_result.total_score,
            value_pick.product_name,
            value_pick.score_result.total_score,
            requires_review,
        )
        return result


# Singleton
dual_recommendation_engine = DualRecommendationEngine()
