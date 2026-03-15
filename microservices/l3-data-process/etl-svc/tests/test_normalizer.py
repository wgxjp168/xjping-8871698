"""Unit tests for Normalizer."""
import pytest

from app.models.schemas import Grade, Platform, ProductScore, RawProduct
from app.services.normalizer import (
    Normalizer,
    _clean_title, _compute_discount, _normalise_brand,
    _parse_category_path, _normalise_spec_value,
)


def _make_score() -> ProductScore:
    return ProductScore(
        total_score=75.0, grade=Grade.B,
        price_score=80.0, popularity_score=70.0,
        rating_score=75.0, availability_score=85.0,
        value_for_money_score=60.0, data_completeness=0.8,
    )


def _make_raw(**kwargs) -> RawProduct:
    defaults = dict(
        platform=Platform.JD,
        product_id="p001",
        title="小米13 Pro 手机 黑色",
        price=3999.0,
        original_price=4499.0,
        brand="小米",
        category="手机>智能手机>小米",
        specs={"颜色": "黑色", "存储": "256GB"},
        images=["https://img.jd.com/a.jpg"],
        review_count=2000,
        sales_count=5000,
        average_rating=4.7,
        in_stock=True,
        delivery_days=2,
    )
    defaults.update(kwargs)
    return RawProduct(**defaults)


class TestHelperFunctions:
    def test_clean_title(self):
        t = _clean_title("Apple iPhone15 Pro (黑色/256GB)！")
        assert "(" not in t
        assert t == t.lower()

    def test_compute_discount(self):
        assert _compute_discount(80.0, 100.0) == pytest.approx(20.0)
        assert _compute_discount(100.0, 80.0) is None  # orig < price
        assert _compute_discount(100.0, None) is None

    def test_normalise_brand_alias(self):
        assert _normalise_brand("苹果") == "Apple"
        assert _normalise_brand("apple") == "Apple"
        assert _normalise_brand("小米") == "Xiaomi"
        assert _normalise_brand("未知品牌") == "未知品牌"
        assert _normalise_brand(None) is None

    def test_parse_category_path(self):
        path = _parse_category_path("手机>智能手机>小米")
        assert path == ["手机", "智能手机", "小米"]

    def test_parse_category_path_pipe(self):
        path = _parse_category_path("家居|厨具|锅具")
        assert path == ["家居", "厨具", "锅具"]

    def test_parse_category_path_empty(self):
        assert _parse_category_path(None) == []

    def test_normalise_spec_bool_true(self):
        assert _normalise_spec_value("是") == "是"
        assert _normalise_spec_value("yes") == "是"
        assert _normalise_spec_value("true") == "是"
        assert _normalise_spec_value("支持") == "是"

    def test_normalise_spec_bool_false(self):
        assert _normalise_spec_value("否") == "否"
        assert _normalise_spec_value("no") == "否"


class TestNormalizer:
    @pytest.fixture
    def norm(self):
        return Normalizer()

    def test_canonical_id_format(self, norm):
        p = _make_raw()
        result = norm.normalise(p, _make_score())
        assert result.canonical_id == "jd:p001"

    def test_brand_normalised(self, norm):
        p = _make_raw(brand="小米")
        result = norm.normalise(p, _make_score())
        assert result.brand_normalised == "Xiaomi"

    def test_category_path_parsed(self, norm):
        result = norm.normalise(_make_raw(), _make_score())
        assert result.category_path == ["手机", "智能手机", "小米"]

    def test_discount_computed(self, norm):
        p = _make_raw(price=3999.0, original_price=4499.0)
        result = norm.normalise(p, _make_score())
        assert result.discount_pct == pytest.approx(
            (4499 - 3999) / 4499 * 100, abs=0.1
        )

    def test_title_cleaned_lowercase(self, norm):
        result = norm.normalise(_make_raw(), _make_score())
        assert result.title_cleaned == result.title_cleaned.lower()

    def test_spec_values_normalised(self, norm):
        p = _make_raw(specs={"防水": "是", "快充": "yes"})
        result = norm.normalise(p, _make_score())
        assert result.specs["防水"] == "是"
        assert result.specs["快充"] == "是"

    def test_score_attached(self, norm):
        score = _make_score()
        result = norm.normalise(_make_raw(), score)
        assert result.score.total_score == 75.0
        assert result.score.grade == Grade.B

    def test_is_mock_false_for_real_data(self, norm):
        p = _make_raw()
        result = norm.normalise(p, _make_score())
        assert result.is_mock is False

    def test_is_mock_true_for_mock_data(self, norm):
        p = _make_raw()
        p.raw_data = {"mock": True}
        result = norm.normalise(p, _make_score())
        assert result.is_mock is True
