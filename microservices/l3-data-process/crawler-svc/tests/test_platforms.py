"""
Unit tests for platform adapters — mock-data fallback path.
Tests that adapters always return valid RawProduct objects.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import CrawlFilters, Platform, RawProduct
from app.services.platforms import get_adapter, all_adapters
from app.services.platforms.taobao import TaobaoAdapter
from app.services.platforms.jd import JDAdapter
from app.services.platforms.pinduoduo import PinduoduoAdapter


def _mock_api_call(*args, **kwargs):
    """Simulate API call failure → forces mock_products fallback."""
    raise Exception("simulated network error")


class TestAdapterRegistry:
    def test_all_platforms_registered(self):
        adapters = all_adapters()
        for platform in Platform:
            assert platform in adapters

    def test_get_adapter_returns_correct_type(self):
        assert isinstance(get_adapter(Platform.TAOBAO), TaobaoAdapter)
        assert isinstance(get_adapter(Platform.JD), JDAdapter)

    def test_get_adapter_unknown_raises(self):
        with pytest.raises((ValueError, KeyError)):
            get_adapter("unknown")  # type: ignore


class TestTaobaoAdapter:
    @pytest.fixture
    def adapter(self):
        return TaobaoAdapter()

    def test_mock_products_returns_valid_data(self, adapter):
        products = adapter._mock_products("手机", 3, "sess1", "job1")
        assert len(products) == 3
        for p in products:
            assert isinstance(p, RawProduct)
            assert p.platform == Platform.TAOBAO
            assert p.price > 0
            assert p.session_id == "sess1"
            assert p.job_id == "job1"

    @pytest.mark.asyncio
    async def test_search_falls_back_to_mock_on_error(self, adapter):
        with patch(
            "app.services.api_manager.api_manager.call",
            new_callable=AsyncMock,
            side_effect=Exception("network error"),
        ), patch(
            "app.services.compliance_monitor.compliance_monitor.enforce_delay",
            new_callable=AsyncMock,
        ), patch(
            "app.services.proxy_manager.proxy_manager.get_proxy",
            new_callable=AsyncMock,
            return_value=None,
        ):
            products = await adapter.search("笔记本", max_results=3, session_id="s", job_id="j")
        assert len(products) > 0
        assert all(p.platform == Platform.TAOBAO for p in products)

    def test_sign_returns_uppercase_hex(self, adapter):
        params = {"a": "1", "b": "2"}
        sig = adapter._sign(params)
        assert sig == sig.upper()
        assert len(sig) == 32

    def test_safe_float_handles_yuan_symbol(self, adapter):
        assert adapter._safe_float("¥99.9") == pytest.approx(99.9)
        assert adapter._safe_float("1,299.00") == pytest.approx(1299.0)
        assert adapter._safe_float(None) == 0.0

    def test_safe_int_handles_wan(self, adapter):
        assert adapter._safe_int("1.2万") == 12000
        assert adapter._safe_int("500") == 500
        assert adapter._safe_int(None) == 0


class TestJDAdapter:
    @pytest.fixture
    def adapter(self):
        return JDAdapter()

    def test_mock_products_structure(self, adapter):
        products = adapter._mock_products("相机", 2, None, None)
        assert len(products) == 2
        for p in products:
            assert p.platform == Platform.JD
            assert "jd.com" in p.url

    def test_parse_empty_item(self, adapter):
        p = adapter._parse({})
        assert isinstance(p, RawProduct)
        assert p.price == 0.0


class TestPinduoduoAdapter:
    @pytest.fixture
    def adapter(self):
        return PinduoduoAdapter()

    def test_price_conversion_from_fen(self, adapter):
        item = {
            "goods_id": "123",
            "goods_name": "测试商品",
            "min_group_price": 9990,   # 99.90 yuan
            "market_fee": 19990,
        }
        p = adapter._parse(item)
        assert p.price == pytest.approx(99.90)
        assert p.original_price == pytest.approx(199.90)

    def test_mock_products_have_promotion(self, adapter):
        products = adapter._mock_products("服装", 5, None, None)
        assert all(p.promotion is True for p in products)


class TestCrawlFilters:
    def test_filters_optional_fields(self):
        f = CrawlFilters()
        assert f.price_min is None
        assert f.price_max is None
        assert f.in_stock_only is False

    def test_filters_validation(self):
        f = CrawlFilters(price_min=100.0, price_max=500.0, min_rating=4.0)
        assert f.price_min == 100.0
        assert f.min_rating == 4.0
