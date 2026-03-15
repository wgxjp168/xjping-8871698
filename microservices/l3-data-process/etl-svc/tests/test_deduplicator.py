"""Unit tests for Deduplicator."""
import pytest

from app.models.schemas import Platform, RawProduct
from app.services.deduplicator import (
    Deduplicator, _normalise_title, _prices_close, _title_fingerprint,
)


def make_product(platform=Platform.JD, product_id="p001", title="测试商品",
                 price=99.9, review_count=100, **kwargs) -> RawProduct:
    return RawProduct(
        platform=platform, product_id=product_id,
        title=title, price=price, review_count=review_count, **kwargs,
    )


class TestHelpers:
    def test_normalise_title(self):
        t = _normalise_title("Apple iPhone 15 Pro (黑色/256GB)")
        assert "(" not in t
        assert t == t.lower()

    def test_fingerprint_deterministic(self):
        f1 = _title_fingerprint("小米手机 Xiaomi 13")
        f2 = _title_fingerprint("小米手机 Xiaomi 13")
        assert f1 == f2

    def test_fingerprint_different_titles(self):
        f1 = _title_fingerprint("苹果手机")
        f2 = _title_fingerprint("华为手机")
        assert f1 != f2

    def test_prices_close_within_5pct(self):
        assert _prices_close(100.0, 104.9) is True
        assert _prices_close(100.0, 106.0) is False

    def test_prices_close_zero(self):
        assert _prices_close(0.0, 100.0) is False


class TestDeduplicator:
    @pytest.fixture
    def dedup(self):
        return Deduplicator()

    def test_no_duplicates(self, dedup):
        products = [
            make_product(product_id="a", title="商品A", price=100.0),
            make_product(product_id="b", title="商品B", price=200.0),
        ]
        unique, dupes = dedup.deduplicate(products)
        assert len(unique) == 2
        assert dupes == 0

    def test_same_platform_same_id(self, dedup):
        p1 = make_product(product_id="x", title="商品", price=100.0, review_count=10)
        p2 = make_product(product_id="x", title="商品", price=100.0, review_count=200)
        unique, dupes = dedup.deduplicate([p1, p2])
        assert len(unique) == 1
        assert dupes == 1
        # Keep the richer one (higher review_count)
        assert unique[0].review_count == 200

    def test_cross_platform_same_product(self, dedup):
        # Same product on two platforms, almost same price
        p1 = make_product(platform=Platform.JD,      product_id="j1",
                           title="苹果iPhone15手机 黑色 256GB", price=7000.0, review_count=100)
        p2 = make_product(platform=Platform.TAOBAO,  product_id="t1",
                           title="苹果iPhone15手机 黑色 256GB", price=7100.0, review_count=500)
        unique, dupes = dedup.deduplicate([p1, p2])
        # Should be collapsed to 1 (prices within 5%)
        assert len(unique) == 1
        assert dupes == 1
        # Keep the one with more reviews
        assert unique[0].review_count == 500

    def test_different_price_same_title_kept(self, dedup):
        # Same title but very different prices → different products (e.g. 64GB vs 256GB)
        p1 = make_product(product_id="a", title="iPhone15手机", price=5999.0)
        p2 = make_product(product_id="b", title="iPhone15手机", price=7999.0)
        unique, dupes = dedup.deduplicate([p1, p2])
        assert len(unique) == 2

    def test_empty_batch(self, dedup):
        unique, dupes = dedup.deduplicate([])
        assert unique == []
        assert dupes == 0

    def test_single_product(self, dedup):
        p = make_product()
        unique, dupes = dedup.deduplicate([p])
        assert len(unique) == 1
        assert dupes == 0
