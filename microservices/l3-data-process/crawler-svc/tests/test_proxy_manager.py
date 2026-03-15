"""Unit tests for ProxyManager — including ban detection."""
import pytest
from datetime import datetime

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
    async def test_report_ban_marks_banned(self, mgr):
        """report_ban() immediately sets status to BANNED regardless of fail count."""
        await mgr.add_proxy("1.2.3.4", 8080)
        proxy_url = mgr._pool[0].url
        await mgr.report_ban(proxy_url)
        assert mgr._pool[0].status == ProxyStatus.BANNED

    @pytest.mark.asyncio
    async def test_banned_proxy_excluded_from_rotation(self, mgr):
        """BANNED proxies must not be returned by get_proxy()."""
        from unittest.mock import patch
        # Force proxy_enabled=True so get_proxy() actually checks the pool
        with patch("app.services.proxy_manager.settings") as mock_settings:
            mock_settings.proxy_enabled = True
            await mgr.add_proxy("1.2.3.4", 8080)
            proxy_url = mgr._pool[0].url
            await mgr.report_ban(proxy_url)
            result = await mgr.get_proxy()
            assert result is None   # only proxy is banned → pool empty

    @pytest.mark.asyncio
    async def test_banned_proxy_skipped_in_health_check(self, mgr):
        """_check_all() must skip BANNED proxies (not re-probe them)."""
        await mgr.add_proxy("1.2.3.4", 8080)
        proxy_url = mgr._pool[0].url
        await mgr.report_ban(proxy_url)
        # After ban, pool_copy in _check_all should be empty
        async with mgr._lock:
            probe_targets = [p for p in mgr._pool if p.status != ProxyStatus.BANNED]
        assert len(probe_targets) == 0

    @pytest.mark.asyncio
    async def test_pool_stats_counts(self, mgr):
        await mgr.add_proxy("1.2.3.4", 8080)
        await mgr.add_proxy("5.6.7.8", 8080)
        stats = mgr.pool_stats()
        assert stats["total"] == 2
        assert stats["active"] == 2

    @pytest.mark.asyncio
    async def test_pool_stats_includes_banned(self, mgr):
        await mgr.add_proxy("1.2.3.4", 8080)
        await mgr.add_proxy("5.6.7.8", 9090)
        await mgr.report_ban(mgr._pool[0].url)
        stats = mgr.pool_stats()
        assert stats["banned"] == 1
        assert stats["active"] == 1

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

    def test_last_used_is_datetime_after_get_proxy(self):
        """get_proxy() must store a datetime, not a float timestamp."""
        from app.models.schemas import ProxyRecord
        from app.services.proxy_manager import _utcnow
        p = ProxyRecord(host="h", port=80)
        p.last_used = _utcnow()
        assert isinstance(p.last_used, datetime)


class TestBanDetection:
    def test_403_triggers_ban(self):
        mgr = ProxyManager()
        assert mgr.check_response_for_ban("Forbidden", 403) is True

    def test_429_triggers_ban(self):
        mgr = ProxyManager()
        assert mgr.check_response_for_ban("Too many requests", 429) is True

    def test_200_no_captcha_not_ban(self):
        mgr = ProxyManager()
        assert mgr.check_response_for_ban("<html>normal page</html>", 200) is False

    def test_200_with_captcha_keyword_is_ban(self):
        mgr = ProxyManager()
        assert mgr.check_response_for_ban("请完成captcha验证后继续", 200) is True

    def test_200_with_chinese_captcha_keyword(self):
        mgr = ProxyManager()
        assert mgr.check_response_for_ban("请进行人机验证", 200) is True
