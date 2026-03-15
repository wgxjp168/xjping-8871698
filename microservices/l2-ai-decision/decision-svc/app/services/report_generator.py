"""
ReportGenerator — produces structured JSON or rich Markdown reports from a
DecisionAnalyzeResponse.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from app.models.schemas import DecisionAnalyzeResponse, ReportResponse

logger = logging.getLogger(__name__)

_GRADE_EMOJI = {"A": "🏆", "B": "✅", "C": "⚠️", "D": "❌"}
_GRADE_CN = {"A": "优秀", "B": "良好", "C": "一般", "D": "较差"}
_SCORING_CONTEXT_CN = {
    "B2B": "企业采购（B2B）",
    "B2C_KNOWN": "个人采购·已定品牌（B2C Known）",
    "B2C_UNKNOWN": "个人采购·未定品牌（B2C Unknown）",
}


class ReportGenerator:
    """
    Generates decision reports in JSON or Markdown format.
    """

    def generate(
        self, decision: DecisionAnalyzeResponse, fmt: str = "json"
    ) -> ReportResponse:
        logger.info(
            "Generating %s report for decision %s", fmt, decision.decision_id
        )
        if fmt == "markdown":
            report: Any = self._generate_markdown_report(decision)
        else:
            report = self._generate_json_report(decision)

        return ReportResponse(
            decision_id=decision.decision_id,
            report=report,
            generated_at=datetime.utcnow(),
        )

    # ------------------------------------------------------------------ #
    # JSON report
    # ------------------------------------------------------------------ #

    def _generate_json_report(self, decision: DecisionAnalyzeResponse) -> dict[str, Any]:
        sr = decision.score_result
        rr = decision.rule_result

        return {
            "meta": {
                "decision_id": decision.decision_id,
                "generated_at": datetime.utcnow().isoformat(),
                "scoring_context": decision.scoring_context.value,
                "requires_human_review": decision.requires_human_review,
            },
            "executive_summary": {
                "recommendation": decision.recommendation,
                "grade": sr.grade,
                "total_score": sr.total_score,
                "confidence": sr.confidence,
                "passed_rules": rr.passed,
                "violation_count": len(rr.violations),
                "warning_count": len(rr.warnings),
            },
            "scoring": {
                "total_score": sr.total_score,
                "grade": sr.grade,
                "confidence": sr.confidence,
                "dimension_scores": sr.dimension_scores,
                "factors": [
                    {
                        "name": f.name,
                        "score": f.score,
                        "weight": f.weight,
                        "weighted_contribution": f.weighted_contribution,
                        "explanation": f.explanation,
                    }
                    for f in sr.factors
                ],
            },
            "rule_evaluation": {
                "passed": rr.passed,
                "applied_rules": rr.applied_rules,
                "violations": rr.violations,
                "warnings": rr.warnings,
            },
            "explainability": decision.explanation or {},
            "llm_insights": decision.llm_insights or {},
            "next_steps": decision.next_steps,
            "data_sources": {
                "l3_product_service": "attempted (fallback to mock if unavailable)",
                "l3_data_service": "attempted (fallback to mock if unavailable)",
                "llm_service": "attempted (optional, skipped if unavailable)",
                "rule_engine": "local Drools-inspired engine v1.0",
                "scoring_model": f"{decision.scoring_context.value} Scorer v1.0",
            },
        }

    # ------------------------------------------------------------------ #
    # Markdown report
    # ------------------------------------------------------------------ #

    def _generate_markdown_report(self, decision: DecisionAnalyzeResponse) -> str:
        sr = decision.score_result
        rr = decision.rule_result
        grade_emoji = _GRADE_EMOJI.get(sr.grade.value, "")
        grade_cn = _GRADE_CN.get(sr.grade.value, sr.grade.value)
        ctx_cn = _SCORING_CONTEXT_CN.get(decision.scoring_context.value, decision.scoring_context.value)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        lines: list[str] = []

        # ── Title ──────────────────────────────────────────────────────
        lines += [
            f"# {grade_emoji} ILbuy L2 AI 采购决策报告",
            "",
            f"> **决策编号**: `{decision.decision_id}`  ",
            f"> **生成时间**: {now}  ",
            f"> **决策模式**: {ctx_cn}  ",
            f"> **需人工审核**: {'是 ⚠️' if decision.requires_human_review else '否 ✅'}",
            "",
            "---",
            "",
        ]

        # ── 1. 决策摘要 ────────────────────────────────────────────────
        lines += [
            "## 📋 决策摘要",
            "",
            f"> {decision.recommendation}",
            "",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| 综合评分 | **{sr.total_score:.1f} / 100** |",
            f"| 评级 | **{sr.grade.value} — {grade_cn}** {grade_emoji} |",
            f"| 置信度 | {sr.confidence * 100:.1f}% |",
            f"| 规则检查 | {'✅ 通过' if rr.passed else '❌ 存在违规'} |",
            f"| 违规数量 | {len(rr.violations)} 项 |",
            f"| 预警数量 | {len(rr.warnings)} 项 |",
            "",
            "---",
            "",
        ]

        # ── 2. 评分详情 ────────────────────────────────────────────────
        lines += [
            "## 📊 评分详情",
            "",
            "| 评分维度 | 原始分 | 权重 | 加权贡献 | 说明 |",
            "|----------|--------|------|----------|------|",
        ]
        for f in sr.factors:
            bar = self._score_bar(f.score)
            lines.append(
                f"| {f.name} | {f.score:.1f} {bar} | {f.weight:.0%} "
                f"| {f.weighted_contribution:.2f} | {f.explanation[:60]}… |"
                if len(f.explanation) > 60
                else
                f"| {f.name} | {f.score:.1f} {bar} | {f.weight:.0%} "
                f"| {f.weighted_contribution:.2f} | {f.explanation} |"
            )
        lines += [
            "",
            f"**综合加权总分: {sr.total_score:.2f} 分**",
            "",
            "---",
            "",
        ]

        # ── 3. 规则检查 ────────────────────────────────────────────────
        lines += [
            "## 🔍 规则检查结果",
            "",
            f"共评估 **{len(rr.applied_rules)}** 条规则。",
            "",
        ]
        if rr.violations:
            lines.append("### ❌ 违规项（需立即处理）")
            lines.append("")
            for v in rr.violations:
                lines.append(f"- {v}")
            lines.append("")
        else:
            lines.append("✅ 无违规项。\n")

        if rr.warnings:
            lines.append("### ⚠️ 预警项（请知悉）")
            lines.append("")
            for w in rr.warnings:
                lines.append(f"- {w}")
            lines.append("")
        else:
            lines.append("✅ 无预警项。\n")

        lines += ["---", ""]

        # ── 4. 推荐理由 ────────────────────────────────────────────────
        lines += ["## 💡 推荐理由", ""]
        if decision.explanation:
            nl = decision.explanation.get("natural_language_summary", "")
            if nl:
                lines.append(nl)
                lines.append("")
            cf = decision.explanation.get("counterfactual", "")
            if cf:
                lines.append(f"**改进建议**: {cf}")
                lines.append("")

            top_pos = decision.explanation.get("top_positive_factors", [])
            if top_pos:
                lines.append("**主要优势**:")
                for fp in top_pos:
                    lines.append(
                        f"- 🟢 {fp.get('display_name', fp['name'])}"
                        f"（得分 {fp['raw_score']:.1f}，贡献 +{fp['importance']:.2f}）"
                    )
                lines.append("")

            top_neg = decision.explanation.get("top_negative_factors", [])
            if top_neg:
                lines.append("**主要不足**:")
                for fn in top_neg:
                    lines.append(
                        f"- 🔴 {fn.get('display_name', fn['name'])}"
                        f"（得分 {fn['raw_score']:.1f}，影响 {fn['importance']:.2f}）"
                    )
                lines.append("")
        else:
            lines.append("暂无详细解释数据。\n")

        lines += ["---", ""]

        # ── 5. 下一步行动 ──────────────────────────────────────────────
        lines += ["## 🚀 下一步行动", ""]
        for step in decision.next_steps:
            lines.append(f"- {step}")
        lines += ["", "---", ""]

        # ── 6. 数据来源说明 ────────────────────────────────────────────
        lines += [
            "## 📌 数据来源说明",
            "",
            "| 数据源 | 状态 |",
            "|--------|------|",
            "| L3 产品服务（l3-product-svc） | 尝试调用，不可用时使用模拟数据 |",
            "| L3 市场数据服务（l3-data-svc） | 尝试调用，不可用时使用模拟数据 |",
            "| LLM 分析服务（llm-svc） | 可选调用，不可用时跳过 |",
            "| 规则引擎 | 本地 Drools 风格引擎 v1.0 |",
            f"| 评分模型 | {decision.scoring_context.value} Scorer v1.0 |",
            "",
            f"---",
            f"*报告由 ILbuy L2 AI Decision Hub — decision-svc v1.0 自动生成*",
        ]

        return "\n".join(lines)

    @staticmethod
    def _score_bar(score: float) -> str:
        """Render a mini ASCII progress bar for a 0-100 score."""
        filled = round(score / 10)
        return "█" * filled + "░" * (10 - filled)


# Singleton
report_generator = ReportGenerator()
