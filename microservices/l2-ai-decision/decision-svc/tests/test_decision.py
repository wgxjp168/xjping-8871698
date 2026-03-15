"""
Test suite for decision-svc.

Tests cover:
  - B2B scoring
  - B2C Known-Brand scoring
  - B2C Unknown-Brand scoring
  - Rule engine budget violation
  - Full 8-step decision flow (mocked external services)
  - Markdown report generation
  - Explainability engine
  - Health endpoint
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# ── Adjust import path when running directly ──────────────────────────────
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def b2b_context() -> dict[str, Any]:
    return {
        "market_price_ratio": 0.95,
        "bulk_discount_available": True,
        "brand_tier": "A",
        "certification_count": 3,
        "years_in_market": 12,
        "lead_time_days": 5,
        "stock_availability": 0.90,
        "has_quality_cert": True,
        "return_rate": 0.01,
        "warranty_months": 24,
        "support_response_hours": 8,
        "order_quantity": 100,
        "min_order_quantity": 50,
        "is_b2b": True,
    }


@pytest.fixture
def b2c_known_context() -> dict[str, Any]:
    return {
        "product_price": 4999.0,
        "budget": 5500.0,
        "promotion_available": True,
        "target_brand": "Apple",
        "product_brand": "Apple",
        "is_authorized_dealer": True,
        "required_specs": {"storage": 256, "ram": 8},
        "product_specs": {"storage": 512, "ram": 16},
        "in_stock": True,
        "delivery_time_days": 2,
        "average_rating": 4.7,
        "review_count": 8500,
    }


@pytest.fixture
def b2c_unknown_context() -> dict[str, Any]:
    return {
        "user_need_category": "gaming laptop",
        "product_category": "gaming laptop",
        "product_tags": ["gaming", "laptop", "rtx", "high-performance"],
        "product_price": 7999.0,
        "budget_min": 6000.0,
        "budget_max": 9000.0,
        "product_spec_count": 18,
        "category_avg_spec_count": 12,
        "sales_rank": 45,
        "max_sales_rank": 1000,
        "review_count": 2300,
        "average_rating": 4.5,
    }


@pytest.fixture
def budget_violation_context() -> dict[str, Any]:
    return {
        "budget": 1000.0,
        "product_price": 1500.0,
        "is_b2b": False,
        "restricted_categories": [],
        "approved_brands": [],
    }


@pytest.fixture
def full_request_payload() -> dict[str, Any]:
    return {
        "session_id": "test-session-001",
        "intent": "购买企业笔记本电脑",
        "entities": {
            "product_price": 8999.0,
            "budget": 10000.0,
            "brand": "Lenovo",
            "category": "laptop",
            "org_type": "enterprise",
            "order_quantity": 20,
            "min_order_quantity": 10,
            "brand_tier": "A",
            "certification_count": 2,
            "years_in_market": 15,
            "lead_time_days": 7,
            "stock_availability": 0.85,
            "has_quality_cert": True,
            "return_rate": 0.02,
        },
        "brand_status": "KNOWN",
        "user_context": {
            "org_type": "enterprise",
            "approved_brands": ["Lenovo", "Dell", "HP"],
        },
        "llm_analysis": None,
    }


# --------------------------------------------------------------------------- #
# 1. B2B Scoring
# --------------------------------------------------------------------------- #

class TestB2BScoring:
    def test_score_returns_valid_range(self, b2b_context):
        from app.services.scoring.b2b_scorer import B2BScorerModel
        scorer = B2BScorerModel()
        result = scorer.score(b2b_context)
        assert 0.0 <= result.total_score <= 100.0

    def test_score_grade_is_valid(self, b2b_context):
        from app.services.scoring.b2b_scorer import B2BScorerModel
        from app.models.schemas import Grade
        scorer = B2BScorerModel()
        result = scorer.score(b2b_context)
        assert result.grade in (Grade.A, Grade.B, Grade.C, Grade.D)

    def test_high_quality_context_gets_high_score(self, b2b_context):
        from app.services.scoring.b2b_scorer import B2BScorerModel
        scorer = B2BScorerModel()
        result = scorer.score(b2b_context)
        # Strong supplier, low lead time, cert present → should score B or above
        assert result.total_score >= 70.0, f"Expected >=70, got {result.total_score}"

    def test_all_dimension_scores_in_range(self, b2b_context):
        from app.services.scoring.b2b_scorer import B2BScorerModel
        scorer = B2BScorerModel()
        result = scorer.score(b2b_context)
        for name, score in result.dimension_scores.items():
            assert 0.0 <= score <= 100.0, f"Dimension {name} out of range: {score}"

    def test_factors_have_explanations(self, b2b_context):
        from app.services.scoring.b2b_scorer import B2BScorerModel
        scorer = B2BScorerModel()
        result = scorer.score(b2b_context)
        assert len(result.factors) == 6
        for f in result.factors:
            assert f.explanation, f"Empty explanation for factor {f.name}"

    def test_confidence_between_0_and_1(self, b2b_context):
        from app.services.scoring.b2b_scorer import B2BScorerModel
        scorer = B2BScorerModel()
        result = scorer.score(b2b_context)
        assert 0.0 <= result.confidence <= 1.0

    def test_poor_supplier_gets_low_score(self):
        from app.services.scoring.b2b_scorer import B2BScorerModel
        scorer = B2BScorerModel()
        poor_context = {
            "market_price_ratio": 1.5,
            "bulk_discount_available": False,
            "brand_tier": "C",
            "certification_count": 0,
            "years_in_market": 1,
            "lead_time_days": 45,
            "stock_availability": 0.2,
            "has_quality_cert": False,
            "return_rate": 0.15,
            "warranty_months": 3,
            "support_response_hours": 96,
            "order_quantity": 5,
            "min_order_quantity": 50,
        }
        result = scorer.score(poor_context)
        assert result.total_score < 55.0, f"Expected <55, got {result.total_score}"


# --------------------------------------------------------------------------- #
# 2. B2C Known Scoring
# --------------------------------------------------------------------------- #

class TestB2CKnownScoring:
    def test_score_returns_valid_range(self, b2c_known_context):
        from app.services.scoring.b2c_known_scorer import B2CKnownScorerModel
        scorer = B2CKnownScorerModel()
        result = scorer.score(b2c_known_context)
        assert 0.0 <= result.total_score <= 100.0

    def test_exact_brand_match_boosts_score(self, b2c_known_context):
        from app.services.scoring.b2c_known_scorer import B2CKnownScorerModel
        scorer = B2CKnownScorerModel()
        result = scorer.score(b2c_known_context)
        # Apple exact match + authorized dealer
        brand_score = result.dimension_scores.get("brand_match", 0)
        assert brand_score >= 100.0

    def test_brand_mismatch_lowers_score(self, b2c_known_context):
        from app.services.scoring.b2c_known_scorer import B2CKnownScorerModel
        scorer = B2CKnownScorerModel()
        mismatch_ctx = {**b2c_known_context, "product_brand": "Samsung"}
        result = scorer.score(mismatch_ctx)
        brand_score = result.dimension_scores.get("brand_match", 100)
        assert brand_score < 30.0

    def test_over_budget_lowers_price_value(self, b2c_known_context):
        from app.services.scoring.b2c_known_scorer import B2CKnownScorerModel
        scorer = B2CKnownScorerModel()
        over_budget_ctx = {**b2c_known_context, "product_price": 9999.0, "budget": 5000.0}
        result = scorer.score(over_budget_ctx)
        pv = result.dimension_scores.get("price_value", 100)
        assert pv < 50.0

    def test_spec_match_with_all_requirements_met(self, b2c_known_context):
        from app.services.scoring.b2c_known_scorer import B2CKnownScorerModel
        scorer = B2CKnownScorerModel()
        result = scorer.score(b2c_known_context)
        # product_specs exceed required_specs
        spec_score = result.dimension_scores.get("spec_match", 0)
        assert spec_score == 100.0

    def test_five_factors_returned(self, b2c_known_context):
        from app.services.scoring.b2c_known_scorer import B2CKnownScorerModel
        scorer = B2CKnownScorerModel()
        result = scorer.score(b2c_known_context)
        assert len(result.factors) == 5


# --------------------------------------------------------------------------- #
# 3. B2C Unknown Scoring
# --------------------------------------------------------------------------- #

class TestB2CUnknownScoring:
    def test_score_returns_valid_range(self, b2c_unknown_context):
        from app.services.scoring.b2c_unknown_scorer import B2CUnknownScorerModel
        scorer = B2CUnknownScorerModel()
        result = scorer.score(b2c_unknown_context)
        assert 0.0 <= result.total_score <= 100.0

    def test_exact_category_match_high_score(self, b2c_unknown_context):
        from app.services.scoring.b2c_unknown_scorer import B2CUnknownScorerModel
        scorer = B2CUnknownScorerModel()
        result = scorer.score(b2c_unknown_context)
        cat_score = result.dimension_scores.get("category_fit", 0)
        assert cat_score >= 85.0

    def test_in_budget_gets_high_budget_score(self, b2c_unknown_context):
        from app.services.scoring.b2c_unknown_scorer import B2CUnknownScorerModel
        scorer = B2CUnknownScorerModel()
        result = scorer.score(b2c_unknown_context)
        budget_score = result.dimension_scores.get("budget_match", 0)
        # 7999 is within 6000-9000
        assert budget_score >= 85.0

    def test_score_candidates_returns_top3(self, b2c_unknown_context):
        from app.services.scoring.b2c_unknown_scorer import B2CUnknownScorerModel
        scorer = B2CUnknownScorerModel()
        candidates = [
            {**b2c_unknown_context, "product_price": 7000.0, "sales_rank": 10},
            {**b2c_unknown_context, "product_price": 12000.0, "sales_rank": 900},
            {**b2c_unknown_context, "product_price": 6500.0, "sales_rank": 200},
            {**b2c_unknown_context, "product_price": 8500.0, "sales_rank": 50},
        ]
        top3 = scorer.score_candidates(candidates)
        assert len(top3) == 3
        # Should be sorted best first
        scores = [r.total_score for _, r in top3]
        assert scores == sorted(scores, reverse=True)

    def test_five_dimensions_returned(self, b2c_unknown_context):
        from app.services.scoring.b2c_unknown_scorer import B2CUnknownScorerModel
        scorer = B2CUnknownScorerModel()
        result = scorer.score(b2c_unknown_context)
        assert len(result.factors) == 5


# --------------------------------------------------------------------------- #
# 4. Rule Engine — Budget Violation
# --------------------------------------------------------------------------- #

class TestRuleEngineBudgetViolation:
    def test_budget_violation_detected(self, budget_violation_context):
        from app.services.rule_engine import RuleEngine
        engine = RuleEngine()
        result = engine.evaluate(budget_violation_context)
        assert result.passed is False
        assert any("RULE_001" in v for v in result.violations)

    def test_no_violation_within_budget(self):
        from app.services.rule_engine import RuleEngine
        engine = RuleEngine()
        ctx = {
            "budget": 2000.0,
            "product_price": 1500.0,
            "is_b2b": False,
            "restricted_categories": [],
        }
        result = engine.evaluate(ctx)
        assert not any("RULE_001" in v for v in result.violations)

    def test_moq_violation_for_b2b(self):
        from app.services.rule_engine import RuleEngine
        engine = RuleEngine()
        ctx = {
            "is_b2b": True,
            "order_quantity": 5,
            "min_order_quantity": 20,
        }
        result = engine.evaluate(ctx)
        assert any("RULE_002" in v for v in result.violations)

    def test_restricted_category_violation(self):
        from app.services.rule_engine import RuleEngine
        engine = RuleEngine()
        ctx = {
            "product_category": "chemicals",
            "restricted_categories": ["chemicals", "explosives"],
        }
        result = engine.evaluate(ctx)
        assert any("RULE_005" in v for v in result.violations)

    def test_price_reasonableness_warning(self):
        from app.services.rule_engine import RuleEngine
        engine = RuleEngine()
        ctx = {
            "product_price": 9000.0,
            "market_reference_price": 2000.0,  # 4.5x → warning
        }
        result = engine.evaluate(ctx)
        assert any("RULE_007" in w for w in result.warnings)

    def test_all_8_rules_applied(self):
        from app.services.rule_engine import RuleEngine
        engine = RuleEngine()
        result = engine.evaluate({})
        assert len(result.applied_rules) == 8

    def test_passed_true_when_no_violations(self):
        from app.services.rule_engine import RuleEngine
        engine = RuleEngine()
        ctx = {
            "budget": 10000.0,
            "product_price": 5000.0,
            "is_b2b": False,
            "restricted_categories": [],
        }
        result = engine.evaluate(ctx)
        assert result.passed is True


# --------------------------------------------------------------------------- #
# 5. Full 8-step Decision Flow
# --------------------------------------------------------------------------- #

class TestFullDecisionFlow:
    @pytest.mark.asyncio
    async def test_full_flow_returns_response(self, full_request_payload):
        from app.models.schemas import DecisionAnalyzeRequest, DecisionAnalyzeResponse
        from app.services.decision_engine import DecisionEngine

        engine = DecisionEngine()
        request = DecisionAnalyzeRequest(**full_request_payload)

        # Mock external HTTP calls to avoid network dependency
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=Exception("Service unavailable"))
            mock_client_cls.return_value = mock_client

            response = await engine.analyze(request)

        assert isinstance(response, DecisionAnalyzeResponse)
        assert response.decision_id.startswith("DEC-")
        assert 0.0 <= response.score_result.total_score <= 100.0
        assert response.recommendation

    @pytest.mark.asyncio
    async def test_scoring_context_b2b_for_enterprise(self, full_request_payload):
        from app.models.schemas import DecisionAnalyzeRequest, ScoringContext
        from app.services.decision_engine import DecisionEngine

        engine = DecisionEngine()
        request = DecisionAnalyzeRequest(**full_request_payload)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=Exception("offline"))
            mock_client_cls.return_value = mock_client

            response = await engine.analyze(request)

        assert response.scoring_context == ScoringContext.B2B

    @pytest.mark.asyncio
    async def test_decision_cached_after_analysis(self, full_request_payload):
        from app.models.schemas import DecisionAnalyzeRequest
        from app.services.decision_engine import DecisionEngine

        engine = DecisionEngine()
        request = DecisionAnalyzeRequest(**full_request_payload)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=Exception("offline"))
            mock_client_cls.return_value = mock_client

            response = await engine.analyze(request)

        cached = engine.get_cached(response.decision_id)
        assert cached is not None
        assert cached.decision_id == response.decision_id

    @pytest.mark.asyncio
    async def test_rule_violations_trigger_human_review(self):
        from app.models.schemas import DecisionAnalyzeRequest
        from app.services.decision_engine import DecisionEngine

        engine = DecisionEngine()
        request = DecisionAnalyzeRequest(
            session_id="test-002",
            intent="购买化学品",
            entities={
                "product_price": 500.0,
                "budget": 300.0,
                "product_category": "chemicals",
                "restricted_categories": ["chemicals"],
            },
            brand_status="UNKNOWN",
            user_context={},
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=Exception("offline"))
            mock_client_cls.return_value = mock_client

            response = await engine.analyze(request)

        assert response.requires_human_review is True


# --------------------------------------------------------------------------- #
# 6. Report Generation — Markdown
# --------------------------------------------------------------------------- #

class TestReportGenerationMarkdown:
    def _make_decision(self) -> Any:
        from app.models.schemas import (
            DecisionAnalyzeResponse,
            FactorDetail,
            Grade,
            RuleResult,
            ScoreResult,
            ScoringContext,
        )
        score_result = ScoreResult(
            total_score=78.5,
            dimension_scores={"price_competitiveness": 80.0, "supplier_reliability": 75.0},
            grade=Grade.B,
            confidence=0.85,
            factors=[
                FactorDetail(
                    name="price_competitiveness",
                    score=80.0,
                    weight=0.25,
                    explanation="价格具有竞争力",
                    weighted_contribution=20.0,
                ),
                FactorDetail(
                    name="supplier_reliability",
                    score=75.0,
                    weight=0.20,
                    explanation="供应商可靠性良好",
                    weighted_contribution=15.0,
                ),
            ],
        )
        rule_result = RuleResult(
            passed=True,
            violations=[],
            warnings=["[RULE_004] 交货周期偏长"],
            applied_rules=["RULE_001", "RULE_004"],
        )
        return DecisionAnalyzeResponse(
            decision_id="DEC-TEST001",
            scoring_context=ScoringContext.B2B,
            score_result=score_result,
            rule_result=rule_result,
            recommendation="推荐采购，注意交货周期",
            next_steps=["1. 确认价格", "2. 提交审批"],
            requires_human_review=False,
        )

    def test_markdown_report_is_string(self):
        from app.services.report_generator import ReportGenerator
        gen = ReportGenerator()
        decision = self._make_decision()
        resp = gen.generate(decision, fmt="markdown")
        assert isinstance(resp.report, str)

    def test_markdown_contains_decision_id(self):
        from app.services.report_generator import ReportGenerator
        gen = ReportGenerator()
        decision = self._make_decision()
        resp = gen.generate(decision, fmt="markdown")
        assert "DEC-TEST001" in resp.report

    def test_markdown_has_all_sections(self):
        from app.services.report_generator import ReportGenerator
        gen = ReportGenerator()
        decision = self._make_decision()
        resp = gen.generate(decision, fmt="markdown")
        report = resp.report
        assert "决策摘要" in report
        assert "评分详情" in report
        assert "规则检查" in report
        assert "推荐理由" in report
        assert "下一步行动" in report
        assert "数据来源" in report

    def test_json_report_structure(self):
        from app.services.report_generator import ReportGenerator
        gen = ReportGenerator()
        decision = self._make_decision()
        resp = gen.generate(decision, fmt="json")
        assert isinstance(resp.report, dict)
        assert "executive_summary" in resp.report
        assert "scoring" in resp.report
        assert "rule_evaluation" in resp.report
        assert "next_steps" in resp.report
        assert "data_sources" in resp.report

    def test_report_response_has_generated_at(self):
        from app.services.report_generator import ReportGenerator
        gen = ReportGenerator()
        decision = self._make_decision()
        resp = gen.generate(decision, fmt="json")
        assert isinstance(resp.generated_at, datetime)


# --------------------------------------------------------------------------- #
# 7. Explainability Engine
# --------------------------------------------------------------------------- #

class TestExplainability:
    def _make_score_result(self) -> Any:
        from app.models.schemas import FactorDetail, Grade, ScoreResult
        return ScoreResult(
            total_score=72.0,
            dimension_scores={"price_value": 90.0, "brand_match": 100.0, "spec_match": 60.0},
            grade=Grade.B,
            confidence=0.80,
            factors=[
                FactorDetail(
                    name="price_value",
                    score=90.0,
                    weight=0.30,
                    explanation="价格低于预算",
                    weighted_contribution=27.0,
                ),
                FactorDetail(
                    name="brand_match",
                    score=100.0,
                    weight=0.25,
                    explanation="品牌完全匹配",
                    weighted_contribution=25.0,
                ),
                FactorDetail(
                    name="spec_match",
                    score=60.0,
                    weight=0.25,
                    explanation="规格部分匹配",
                    weighted_contribution=15.0,
                ),
            ],
        )

    def test_explain_score_returns_dict(self):
        from app.services.explainability import ExplainabilityEngine
        engine = ExplainabilityEngine()
        result = self._make_score_result()
        output = engine.explain_score(result, {})
        assert isinstance(output, dict)

    def test_feature_importance_sorted_by_abs(self):
        from app.services.explainability import ExplainabilityEngine
        engine = ExplainabilityEngine()
        result = self._make_score_result()
        importance = engine._compute_feature_importance(result.factors)
        abs_vals = [abs(i["importance"]) for i in importance]
        assert abs_vals == sorted(abs_vals, reverse=True)

    def test_natural_language_contains_chinese(self):
        from app.services.explainability import ExplainabilityEngine
        engine = ExplainabilityEngine()
        result = self._make_score_result()
        importance = engine._compute_feature_importance(result.factors)
        text = engine.generate_natural_language_explanation(importance, locale="zh")
        assert isinstance(text, str)
        # Check it contains at least one Chinese character
        assert any('\u4e00' <= c <= '\u9fff' for c in text)

    def test_counterfactual_identifies_improvement(self):
        from app.services.explainability import ExplainabilityEngine
        engine = ExplainabilityEngine()
        result = self._make_score_result()
        cf = engine.generate_counterfactual(result, target_grade=None)
        assert isinstance(cf, str)
        assert len(cf) > 0

    def test_highlight_top_positive_factors(self):
        from app.services.explainability import ExplainabilityEngine
        engine = ExplainabilityEngine()
        result = self._make_score_result()
        importance = engine._compute_feature_importance(result.factors)
        top_pos = engine.highlight_key_factors(importance, top_n=2, positive_only=True)
        assert all(f["direction"] == "positive" for f in top_pos)
        assert len(top_pos) <= 2

    def test_explain_score_has_all_keys(self):
        from app.services.explainability import ExplainabilityEngine
        engine = ExplainabilityEngine()
        result = self._make_score_result()
        output = engine.explain_score(result, {})
        required_keys = {
            "feature_importance",
            "top_positive_factors",
            "top_negative_factors",
            "natural_language_summary",
            "counterfactual",
        }
        assert required_keys.issubset(output.keys())


# --------------------------------------------------------------------------- #
# 8. Health endpoint
# --------------------------------------------------------------------------- #

class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_endpoint_returns_ok(self):
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "decision-svc"

    @pytest.mark.asyncio
    async def test_decision_health_endpoint_returns_ok(self):
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            response = client.get("/decision/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
