"""Unit tests for ProxyManager."""
import pytest

from app.models.schemas import ProxyStatus
from app.services.proxy_manager import ProxyManager


class TestProxyManager:
    @pytest.fixture
    def mgr(self):
        return ProxyManager()

    @pytest.mark.asyncio
    async def test_add_proxy(self, mgr):
        record = await mgr.add_proxy("1.2.3.4", 8080)
        assert mgr.pool_size() == 1
        assert record.host == "1.2.3.4"

    @pytest.mark.asyncio
    async def test_no_duplicates(self, mgr):
        await mgr.add_proxy("1.2.3.4", 8080)
        await mgr.add_proxy("1.2.3.4", 8080)
        assert mgr.pool_size() == 1

    @pytest.mark.asyncio
    async def test_get_proxy_returns_none_when_empty(self, mgr):
        from app.core.config import get_settings
        settings = get_settings()
        if not settings.proxy_enabled:
            result = await mgr.get_proxy()
            assert result is None

    @pytest.mark.asyncio
    async def test_report_failure_marks_failed(self, mgr):
        await mgr.add_proxy("1.2.3.4", 8080)
        proxy_url = mgr._pool[0].url
        # Force fail count to threshold
        from app.core.config import get_settings
        threshold = get_settings().proxy_max_fail_count
        for _ in range(threshold):
            await mgr.report_failure(proxy_url)
        assert mgr._pool[0].status == ProxyStatus.FAILED

    @pytest.mark.asyncio
    async def test_report_success_increases_count(self, mgr):
        await mgr.add_proxy("1.2.3.4", 8080)
        proxy_url = mgr._pool[0].url
        await mgr.report_success(proxy_url)
        assert mgr._pool[0].success_count == 1

    @pytest.mark.asyncio
    async def test_pool_stats_counts(self, mgr):
        await mgr.add_proxy("1.2.3.4", 8080)
        await mgr.add_proxy("5.6.7.8", 8080)
        stats = mgr.pool_stats()
        assert stats["total"] == 2
        assert stats["active"] == 2

    def test_proxy_url_with_auth(self):
        from app.models.schemas import ProxyRecord
        p = ProxyRecord(host="h", port=80, username="u", password="p")
        assert "u:p@h:80" in p.url

    def test_proxy_url_no_auth(self):
        from app.models.schemas import ProxyRecord
        p = ProxyRecord(host="h", port=80)
        assert "@" not in p.url

    def test_success_rate_no_requests(self):
        from app.models.schemas import ProxyRecord
        p = ProxyRecord(host="h", port=80)
        assert p.success_rate == 1.0

    def test_success_rate_with_requests(self):
        from app.models.schemas import ProxyRecord
        p = ProxyRecord(host="h", port=80, success_count=8, fail_count=2)
        assert p.success_rate == pytest.approx(0.8)
