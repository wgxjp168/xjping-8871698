"""Unit tests for DataCleaner."""
import pytest

from app.models.schemas import Platform, RawProduct
from app.services.cleaner import DataCleaner, _clean_text


def make_product(**kwargs) -> RawProduct:
    defaults = dict(
        platform=Platform.JD,
        product_id="p001",
        title="京东测试商品",
        price=99.9,
        average_rating=4.5,
        review_count=100,
        sales_count=500,
        images=["https://img.jd.com/a.jpg"],
        specs={"颜色": "黑色"},
        shop_rating=4.8,
    )
    defaults.update(kwargs)
    return RawProduct(**defaults)


class TestCleanText:
    def test_removes_html_tags(self):
        assert _clean_text("<b>商品</b>名称") == "商品 名称"

    def test_collapses_whitespace(self):
        assert _clean_text("a  b   c") == "a b c"

    def test_strips_leading_trailing(self):
        assert _clean_text("  hello  ") == "hello"


class TestDataCleaner:
    @pytest.fixture
    def cleaner(self):
        return DataCleaner()

    def test_valid_product_passes(self, cleaner):
        p = make_product()
        cleaned, invalid = cleaner.clean_batch([p])
        assert len(cleaned) == 1
        assert invalid == 0

    def test_empty_product_id_dropped(self, cleaner):
        p = make_product(product_id="")
        cleaned, invalid = cleaner.clean_batch([p])
        assert len(cleaned) == 0
        assert invalid == 1

    def test_empty_title_dropped(self, cleaner):
        p = make_product(title="")
        cleaned, invalid = cleaner.clean_batch([p])
        assert invalid == 1

    def test_zero_price_dropped(self, cleaner):
        p = make_product(price=0.0)
        cleaned, invalid = cleaner.clean_batch([p])
        assert invalid == 1

    def test_rating_clamped(self, cleaner):
        p = make_product(average_rating=7.0)
        cleaned, _ = cleaner.clean_batch([p])
        assert cleaned[0].average_rating == 5.0

    def test_negative_sales_clamped(self, cleaner):
        p = make_product(sales_count=-100)
        cleaned, _ = cleaner.clean_batch([p])
        assert cleaned[0].sales_count == 0

    def test_invalid_image_urls_removed(self, cleaner):
        p = make_product(images=["https://valid.com/img.jpg", "not_a_url", "ftp://bad.com"])
        cleaned, _ = cleaner.clean_batch([p])
        assert cleaned[0].images == ["https://valid.com/img.jpg"]

    def test_html_stripped_from_title(self, cleaner):
        p = make_product(title="<b>超级</b>商品 <br/> 正品")
        cleaned, _ = cleaner.clean_batch([p])
        assert "<b>" not in cleaned[0].title
        assert "超级" in cleaned[0].title

    def test_empty_specs_removed(self, cleaner):
        p = make_product(specs={"颜色": "红色", "": "value", "key": ""})
        cleaned, _ = cleaner.clean_batch([p])
        assert "" not in cleaned[0].specs
        assert "颜色" in cleaned[0].specs

    def test_bad_original_price_cleared(self, cleaner):
        # original_price < price is invalid
        p = make_product(price=100.0, original_price=50.0)
        cleaned, _ = cleaner.clean_batch([p])
        assert cleaned[0].original_price is None

    def test_promotion_price_exceeding_price_cleared(self, cleaner):
        p = make_product(price=100.0, promotion_price=150.0)
        cleaned, _ = cleaner.clean_batch([p])
        assert cleaned[0].promotion_price is None

    def test_batch_mixed_valid_invalid(self, cleaner):
        products = [
            make_product(product_id="valid"),
            make_product(product_id=""),         # invalid
            make_product(title="ab"),             # title too short
        ]
        cleaned, invalid = cleaner.clean_batch(products)
        assert len(cleaned) == 1
        assert invalid == 2
