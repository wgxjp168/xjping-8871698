"""
Unit tests for platform adapters — mock-data fallback, API error codes, signing.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import CrawlFilters, Platform, RawProduct
from app.services.platforms import get_adapter, all_adapters
from app.services.platforms.base import BasePlatformAdapter, PlatformAPIError
from app.services.platforms.taobao import TaobaoAdapter
from app.services.platforms.jd import JDAdapter
from app.services.platforms.ali1688 import Ali1688Adapter
from app.services.platforms.pinduoduo import PinduoduoAdapter


# ── Registry ──────────────────────────────────────────────────────────────────

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


# ── BasePlatformAdapter helpers ───────────────────────────────────────────────

class TestBasePlatformAdapterHelpers:
    @pytest.fixture
    def adapter(self):
        return TaobaoAdapter()

    def test_get_nested_simple(self, adapter):
        data = {"a": {"b": {"c": 42}}}
        assert adapter._get_nested(data, "a.b.c") == 42

    def test_get_nested_missing_key(self, adapter):
        data = {"a": {}}
        assert adapter._get_nested(data, "a.b.c") is None

    def test_get_nested_non_dict_node(self, adapter):
        data = {"a": "string"}
        assert adapter._get_nested(data, "a.b") is None

    def test_check_api_error_success_response(self, adapter):
        # No error_response key → should not raise
        data = {"tbk_item_get_response": {"result": {}}}
        adapter.check_api_error(data)   # must not raise

    def test_check_api_error_raises_on_error_code(self, adapter):
        data = {"error_response": {"code": "27", "zh_desc": "访问受限"}}
        with pytest.raises(PlatformAPIError) as exc_info:
            adapter.check_api_error(data)
        assert exc_info.value.code == "27"
        assert "访问受限" in exc_info.value.message

    def test_is_rate_limit_error(self, adapter):
        err = PlatformAPIError("27", "rate limited")
        assert adapter.is_rate_limit_error(err) is True

    def test_is_ban_error(self, adapter):
        err = PlatformAPIError("50", "ip banned")
        assert adapter.is_ban_error(err) is True

    def test_is_not_ban_error(self, adapter):
        err = PlatformAPIError("99999", "unknown")
        assert adapter.is_ban_error(err) is False


# ── Taobao ────────────────────────────────────────────────────────────────────

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
    async def test_search_falls_back_to_mock_on_network_error(self, adapter):
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

    @pytest.mark.asyncio
    async def test_search_falls_back_to_mock_on_api_error_and_reports_ban(self, adapter):
        """When the JSON body contains a ban error code, report_ban() must be called."""
        fake_resp = MagicMock()
        fake_resp.json.return_value = {
            "error_response": {"code": "50", "zh_desc": "IP封禁"}
        }
        mock_ban = AsyncMock()
        with patch(
            "app.services.api_manager.api_manager.call",
            new_callable=AsyncMock,
            return_value=fake_resp,
        ), patch(
            "app.services.compliance_monitor.compliance_monitor.enforce_delay",
            new_callable=AsyncMock,
        ), patch(
            "app.services.proxy_manager.proxy_manager.get_proxy",
            new_callable=AsyncMock,
            return_value="http://proxy:8080",
        ), patch(
            "app.services.proxy_manager.proxy_manager.report_ban",
            mock_ban,
        ):
            products = await adapter.search("测试", max_results=2)
        mock_ban.assert_called_once_with("http://proxy:8080")
        assert len(products) > 0   # mock fallback returned

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


# ── JD ────────────────────────────────────────────────────────────────────────

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

    @pytest.mark.asyncio
    async def test_search_reports_ban_on_api_error(self, adapter):
        fake_resp = MagicMock()
        fake_resp.json.return_value = {
            "error_response": {"code": "ISP_PERMISSION_DENY", "zh_desc": "权限拒绝"}
        }
        mock_ban = AsyncMock()
        with patch(
            "app.services.api_manager.api_manager.call",
            new_callable=AsyncMock,
            return_value=fake_resp,
        ), patch(
            "app.services.compliance_monitor.compliance_monitor.enforce_delay",
            new_callable=AsyncMock,
        ), patch(
            "app.services.proxy_manager.proxy_manager.get_proxy",
            new_callable=AsyncMock,
            return_value="http://1.2.3.4:8080",
        ), patch(
            "app.services.proxy_manager.proxy_manager.report_ban",
            mock_ban,
        ):
            products = await adapter.search("手机")
        mock_ban.assert_called_once_with("http://1.2.3.4:8080")


# ── Ali1688 ───────────────────────────────────────────────────────────────────

class TestAli1688Adapter:
    @pytest.fixture
    def adapter(self):
        return Ali1688Adapter()

    def test_sign_is_added_to_params(self, adapter):
        """Regression: sign must be present in the params dict after _sign() call."""
        params = {
            "app_key": "MOCK_KEY",
            "timestamp": "123456",
            "keywords": "test",
            "beginPage": "1",
            "pageSize": "10",
        }
        sig = adapter._sign(params)
        assert len(sig) == 32
        assert sig == sig.upper()

    def test_sign_changes_with_params(self, adapter):
        params_a = {"app_key": "K", "keywords": "手机"}
        params_b = {"app_key": "K", "keywords": "电脑"}
        assert adapter._sign(params_a) != adapter._sign(params_b)

    def test_mock_products_valid(self, adapter):
        products = adapter._mock_products("螺丝", 3, None, None)
        assert len(products) == 3
        for p in products:
            assert p.platform == Platform.ALI1688
            assert p.price > 0

    @pytest.mark.asyncio
    async def test_search_includes_sign_in_api_call(self, adapter):
        """Verify that the call() receives params with a 'sign' key."""
        captured_params = {}

        async def fake_call(platform, method, url, *, params=None, **kwargs):
            captured_params.update(params or {})
            raise Exception("stop here")  # trigger mock fallback

        with patch(
            "app.services.api_manager.api_manager.call",
            side_effect=fake_call,
        ), patch(
            "app.services.compliance_monitor.compliance_monitor.enforce_delay",
            new_callable=AsyncMock,
        ), patch(
            "app.services.proxy_manager.proxy_manager.get_proxy",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.proxy_manager.proxy_manager.report_failure",
            new_callable=AsyncMock,
        ):
            await adapter.search("测试商品", max_results=5)

        assert "sign" in captured_params, "sign must be included in params"
        assert len(captured_params["sign"]) == 32


# ── PDD ───────────────────────────────────────────────────────────────────────

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


# ── CrawlFilters ──────────────────────────────────────────────────────────────

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
