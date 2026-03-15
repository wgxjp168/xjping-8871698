"""Unit tests for ProductScorer."""
import pytest

from app.models.schemas import Grade, Platform, RawProduct
from app.services.scorer import (
    ProductScorer,
    _availability_score, _popularity_score, _price_score,
    _rating_score, _value_for_money_score, _grade, _data_completeness,
)


def make_product(**kwargs) -> RawProduct:
    defaults = dict(
        platform=Platform.JD,
        product_id="p001",
        title="测试商品",
        price=299.0,
        original_price=399.0,
        brand="品牌A",
        category="数码",
        specs={"颜色": "黑色", "内存": "8GB"},
        images=["https://img.jd.com/a.jpg"],
        review_count=500,
        sales_count=2000,
        average_rating=4.5,
        in_stock=True,
        delivery_days=2,
        shop_name="京东自营",
        promotion=False,
    )
    defaults.update(kwargs)
    return RawProduct(**defaults)


class TestScoringDimensions:
    def test_price_score_with_discount(self):
        score = _price_score(80.0, 100.0, False)
        assert score > 50.0

    def test_price_score_with_promotion(self):
        base  = _price_score(100.0, None, False)
        promo = _price_score(100.0, None, True)
        assert promo > base

    def test_price_score_zero_price(self):
        assert _price_score(0.0, None, False) == 50.0

    def test_price_score_range(self):
        for price in [1, 50, 500, 5000, 50000]:
            score = _price_score(price, None, False)
            assert 0.0 <= score <= 100.0

    def test_popularity_score_zero(self):
        assert _popularity_score(0, 0) == 20.0

    def test_popularity_score_high_sales(self):
        score = _popularity_score(100000, 50000)
        assert score > 90.0

    def test_popularity_score_range(self):
        score = _popularity_score(1000, 200)
        assert 0.0 <= score <= 100.0

    def test_rating_score_perfect(self):
        score = _rating_score(5.0, 10000)
        assert score == pytest.approx(100.0, abs=1.0)

    def test_rating_score_low_trust(self):
        # Few reviews → lower score even with perfect rating
        high_trust = _rating_score(5.0, 1000)
        low_trust  = _rating_score(5.0, 1)
        assert high_trust > low_trust

    def test_rating_score_zero_rating(self):
        assert _rating_score(0.0, 100) == 40.0

    def test_availability_out_of_stock(self):
        assert _availability_score(False, None) == 15.0

    def test_availability_next_day(self):
        score = _availability_score(True, 1)
        assert score == 100.0

    def test_availability_slow_delivery(self):
        slow = _availability_score(True, 14)
        fast = _availability_score(True, 1)
        assert fast > slow

    def test_vfm_no_specs(self):
        score = _value_for_money_score(100.0, 0, 4.0)
        assert 0.0 <= score <= 100.0

    def test_grade_boundaries(self):
        assert _grade(85.0) == Grade.A
        assert _grade(84.9) == Grade.B
        assert _grade(70.0) == Grade.B
        assert _grade(69.9) == Grade.C
        assert _grade(55.0) == Grade.C
        assert _grade(54.9) == Grade.D


class TestDataCompleteness:
    def test_full_product(self):
        p = make_product()
        completeness = _data_completeness(p)
        assert completeness >= 0.8

    def test_sparse_product(self):
        p = RawProduct(platform=Platform.JD, product_id="x", title="y", price=10.0)
        completeness = _data_completeness(p)
        assert completeness < 0.5


class TestProductScorer:
    @pytest.fixture
    def scorer(self):
        return ProductScorer()

    def test_score_returns_product_score(self, scorer):
        from app.models.schemas import ProductScore
        result = scorer.score(make_product())
        assert isinstance(result, ProductScore)

    def test_total_score_in_range(self, scorer):
        result = scorer.score(make_product())
        assert 0.0 <= result.total_score <= 100.0

    def test_high_quality_product_grade_a(self, scorer):
        p = make_product(
            price=199.0, original_price=399.0,
            sales_count=50000, review_count=10000,
            average_rating=4.9, in_stock=True, delivery_days=1,
            specs={f"k{i}": "v" for i in range(20)},
        )
        result = scorer.score(p)
        # High quality product should score A or B
        assert result.grade in (Grade.A, Grade.B)

    def test_low_quality_product_grade_d(self, scorer):
        p = make_product(
            price=9999.0, original_price=None,
            sales_count=0, review_count=0,
            average_rating=1.0, in_stock=False, delivery_days=30,
            specs={},
        )
        result = scorer.score(p)
        assert result.grade in (Grade.C, Grade.D)

    def test_score_batch_length(self, scorer):
        products = [make_product(product_id=str(i)) for i in range(5)]
        scores = scorer.score_batch(products)
        assert len(scores) == 5

    def test_data_completeness_in_score(self, scorer):
        result = scorer.score(make_product())
        assert 0.0 <= result.data_completeness <= 1.0

    def test_dimension_scores_in_range(self, scorer):
        result = scorer.score(make_product())
        for dim in [result.price_score, result.popularity_score,
                    result.rating_score, result.availability_score,
                    result.value_for_money_score]:
            assert 0.0 <= dim <= 100.0
