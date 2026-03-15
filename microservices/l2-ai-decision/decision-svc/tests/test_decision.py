"""
Tests for the Decision Service — scoring models, rule engine, and API endpoints.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.schemas import (
    BrandStatus,
    DecisionAnalyzeRequest,
    Grade,
    ScoringContext,
)
from app.services.decision_engine import DecisionEngine
from app.services.scoring.b2b_scorer import B2BScorerModel
from app.services.scoring.b2c_known_scorer import B2CKnownScorerModel
from app.services.scoring.b2c_unknown_scorer import B2CUnknownScorerModel
from app.services.rule_engine import RuleEngine


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def b2b_scorer():
    return B2BScorerModel()


@pytest.fixture
def b2c_known_scorer():
    return B2CKnownScorerModel()


@pytest.fixture
def b2c_unknown_scorer():
    return B2CUnknownScorerModel()


@pytest.fixture
def rule_engine():
    return RuleEngine()


@pytest.fixture
def engine():
    return DecisionEngine()


# ── B2B Scorer Tests ───────────────────────────────────────────────────────

class TestB2BScorer:
    def test_score_returns_score_result(self, b2b_scorer):
        ctx = {
            "market_price_ratio": 0.95,
            "bulk_discount_available": True,
            "brand_tier": "A",
            "certification_count": 4,
            "years_in_market": 10,
            "lead_time_days": 5,
            "stock_availability": 0.9,
            "has_quality_cert": True,
            "return_rate": 0.02,
            "warranty_months": 24,
            "support_response_hours": 8,
            "order_quantity": 100,
            "min_order_quantity": 50,
        }
        result = b2b_scorer.score(ctx)
        assert 0 <= result.total_score <= 100
        assert result.grade in [Grade.A, Grade.B, Grade.C, Grade.D]
        assert 0 <= result.confidence <= 1
        assert len(result.factors) == 6

    def test_score_high_quality_supplier(self, b2b_scorer):
        ctx = {
            "market_price_ratio": 0.8,
            "bulk_discount_available": True,
            "brand_tier": "A",
            "certification_count": 6,
            "years_in_market": 15,
            "lead_time_days": 3,
            "stock_availability": 1.0,
            "has_quality_cert": True,
            "return_rate": 0.005,
            "warranty_months": 36,
            "support_response_hours": 2,
            "order_quantity": 200,
            "min_order_quantity": 10,
        }
        result = b2b_scorer.score(ctx)
        assert result.total_score >= 70, "High-quality supplier should score B or better"

    def test_score_poor_supplier(self, b2b_scorer):
        ctx = {
            "market_price_ratio": 1.5,
            "bulk_discount_available": False,
            "brand_tier": "C",
            "certification_count": 0,
            "years_in_market": 1,
            "lead_time_days": 60,
            "stock_availability": 0.2,
            "has_quality_cert": False,
            "return_rate": 0.15,
            "warranty_months": 3,
            "support_response_hours": 96,
            "order_quantity": 5,
            "min_order_quantity": 100,
        }
        result = b2b_scorer.score(ctx)
        assert result.total_score < 55, "Poor supplier should score C or D"

    def test_score_empty_context_uses_defaults(self, b2b_scorer):
        result = b2b_scorer.score({})
        assert 0 <= result.total_score <= 100


# ── B2C Known Scorer Tests ─────────────────────────────────────────────────

class TestB2CKnownScorer:
    def test_score_perfect_match(self, b2c_known_scorer):
        ctx = {
            "product_price": 3000.0,
            "budget": 3500.0,
            "promotion_available": True,
            "target_brand": "Apple",
            "product_brand": "Apple",
            "is_authorized_dealer": True,
            "required_specs": {"storage": 256, "color": "black"},
            "product_specs": {"storage": 256, "color": "black"},
            "in_stock": True,
            "delivery_time_days": 1,
            "average_rating": 4.8,
            "review_count": 5000,
        }
        result = b2c_known_scorer.score(ctx)
        assert result.total_score >= 70

    def test_score_brand_mismatch(self, b2c_known_scorer):
        ctx = {
            "product_price": 3000.0,
            "budget": 3500.0,
            "target_brand": "Apple",
            "product_brand": "Samsung",
            "in_stock": True,
            "average_rating": 4.5,
            "review_count": 1000,
        }
        result = b2c_known_scorer.score(ctx)
        # Brand mismatch (25% weight at score 10) should drag total down
        assert result.total_score < 80

    def test_score_out_of_budget(self, b2c_known_scorer):
        ctx = {
            "product_price": 6000.0,
            "budget": 3000.0,
            "target_brand": "Apple",
            "product_brand": "Apple",
            "in_stock": True,
            "average_rating": 4.5,
            "review_count": 1000,
        }
        result = b2c_known_scorer.score(ctx)
        # Price 2x over budget should give low price_value score
        price_factor = next(f for f in result.factors if f.name == "price_value")
        assert price_factor.score < 40


# ── B2C Unknown Scorer Tests ───────────────────────────────────────────────

class TestB2CUnknownScorer:
    def test_score_good_candidate(self, b2c_unknown_scorer):
        ctx = {
            "user_need_category": "手机",
            "product_category": "手机",
            "product_price": 3000.0,
            "budget_min": 2500.0,
            "budget_max": 4000.0,
            "product_spec_count": 8,
            "category_avg_spec_count": 6,
            "sales_rank": 3,
            "review_count": 15000,
            "average_rating": 4.7,
        }
        result = b2c_unknown_scorer.score(ctx)
        assert result.total_score >= 65

    def test_score_candidates_returns_top3(self, b2c_unknown_scorer):
        candidates = [
            {"product_price": 3000, "average_rating": 4.5, "sales_rank": 5, "review_count": 10000},
            {"product_price": 1500, "average_rating": 3.0, "sales_rank": 50, "review_count": 500},
            {"product_price": 2000, "average_rating": 4.2, "sales_rank": 20, "review_count": 3000},
            {"product_price": 5000, "average_rating": 4.8, "sales_rank": 1, "review_count": 20000},
        ]
        results = b2c_unknown_scorer.score_candidates(candidates)
        assert len(results) <= 3
        # Verify sorted descending
        scores = [r[1].total_score for r in results]
        assert scores == sorted(scores, reverse=True)


# ── Rule Engine Tests ──────────────────────────────────────────────────────

class TestRuleEngine:
    def test_no_violations_for_clean_order(self, rule_engine):
        ctx = {
            "in_stock": True,
            "budget_max": 5000,
            "product_price": 3000,
            "scoring_context": "B2C_KNOWN",
        }
        result = rule_engine.evaluate(ctx)
        assert result.passed is True
        assert len(result.violations) == 0

    def test_out_of_stock_violation(self, rule_engine):
        ctx = {
            "in_stock": False,
            "scoring_context": "B2C_KNOWN",
        }
        result = rule_engine.evaluate(ctx)
        assert any("库存" in v or "out_of_stock" in v.lower() or "缺货" in v
                   for v in result.violations + result.warnings)


# ── Decision Engine Integration Tests ─────────────────────────────────────

class TestDecisionEngine:
    @pytest.mark.asyncio
    async def test_analyze_b2c_unknown(self, engine):
        request = DecisionAnalyzeRequest(
            session_id="test-session-001",
            intent="PRODUCT_INQUIRY",
            entities={"category": "手机", "budget_max": 4000},
            brand_status=BrandStatus.UNKNOWN,
        )
        response = await engine.analyze(request)
        assert response.scoring_context == ScoringContext.B2C_UNKNOWN
        assert response.decision_id
        assert 0 <= response.score_result.total_score <= 100

    @pytest.mark.asyncio
    async def test_analyze_b2b(self, engine):
        request = DecisionAnalyzeRequest(
            session_id="test-session-002",
            intent="PURCHASE_INQUIRY",
            entities={"quantity": 100, "category": "打印机"},
            brand_status=BrandStatus.UNKNOWN,
            user_context={"customer_type": "enterprise"},
        )
        response = await engine.analyze(request)
        assert response.scoring_context == ScoringContext.B2B

    @pytest.mark.asyncio
    async def test_analyze_b2c_known(self, engine):
        request = DecisionAnalyzeRequest(
            session_id="test-session-003",
            intent="PRODUCT_INQUIRY",
            entities={"brand": "Apple", "category": "手机"},
            brand_status=BrandStatus.KNOWN,
        )
        response = await engine.analyze(request)
        assert response.scoring_context == ScoringContext.B2C_KNOWN

    @pytest.mark.asyncio
    async def test_cached_decision_retrievable(self, engine):
        request = DecisionAnalyzeRequest(
            session_id="cache-test-001",
            intent="PRODUCT_INQUIRY",
            entities={},
            brand_status=BrandStatus.UNKNOWN,
        )
        response = await engine.analyze(request)
        cached = engine.get_cached(response.decision_id)
        assert cached is not None
        assert cached.decision_id == response.decision_id

    @pytest.mark.asyncio
    async def test_validate_empty_intent_raises(self, engine):
        with pytest.raises(ValueError, match="intent"):
            engine._step1_validate(
                DecisionAnalyzeRequest(
                    session_id="x",
                    intent="",
                    brand_status=BrandStatus.UNKNOWN,
                )
            )


# ── API Endpoint Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_analyze_endpoint():
    payload = {
        "session_id": "api-test-001",
        "intent": "PRODUCT_INQUIRY",
        "entities": {"category": "手机", "budget_max": 4000},
        "brand_status": "UNKNOWN",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/decision/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "decision_id" in data
    assert "score_result" in data
    assert "recommendation" in data


@pytest.mark.asyncio
async def test_get_decision_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/decision/NONEXISTENT-ID")
    assert resp.status_code == 404
