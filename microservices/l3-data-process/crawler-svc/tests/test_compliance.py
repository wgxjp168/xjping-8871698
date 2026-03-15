"""Unit tests for ComplianceMonitor — including check_before_crawl and counters."""
import time
from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import Platform
from app.services.compliance_monitor import (
    ComplianceMonitor, ComplianceViolation, RobotsCacheEntry, _MIN_DELAYS,
)
import urllib.robotparser


def _make_parser(disallow: str = "", crawl_delay: float = 0.0) -> urllib.robotparser.RobotFileParser:
    p = urllib.robotparser.RobotFileParser()
    lines = ["User-agent: *"]
    if disallow:
        lines.append(f"Disallow: {disallow}")
    if crawl_delay:
        lines.append(f"Crawl-delay: {crawl_delay}")
    p.parse(lines)
    return p


class TestComplianceMonitor:
    @pytest.fixture
    def monitor(self):
        return ComplianceMonitor()

    @pytest.mark.asyncio
    async def test_is_allowed_when_no_robots(self, monitor):
        # If we can't fetch robots.txt, assume allowed
        with patch.object(monitor, "_get_entry", return_value=None):
            assert await monitor.is_allowed(Platform.JD, "/product/123") is True

    @pytest.mark.asyncio
    async def test_is_allowed_with_disallow(self, monitor):
        parser = _make_parser(disallow="/admin")
        entry = RobotsCacheEntry(parser, 1.0, time.monotonic())
        with patch.object(monitor, "_get_entry", return_value=entry):
            assert await monitor.is_allowed(Platform.JD, "/product/1") is True
            assert await monitor.is_allowed(Platform.JD, "/admin/secret") is False

    @pytest.mark.asyncio
    async def test_get_crawl_delay_uses_min_delay(self, monitor):
        # When no robots.txt entry, returns platform minimum
        with patch.object(monitor, "_get_entry", return_value=None):
            delay = await monitor.get_crawl_delay(Platform.ALI1688)
            assert delay == _MIN_DELAYS[Platform.ALI1688]

    @pytest.mark.asyncio
    async def test_get_crawl_delay_respects_robots(self, monitor):
        parser = _make_parser(crawl_delay=5.0)
        entry = RobotsCacheEntry(parser, 5.0, time.monotonic())
        with patch.object(monitor, "_get_entry", return_value=entry):
            delay = await monitor.get_crawl_delay(Platform.TAOBAO)
            assert delay == 5.0

    @pytest.mark.asyncio
    async def test_enforce_delay_respects_min(self, monitor):
        monitor._last_req[Platform.JD] = time.monotonic()  # just requested
        with patch.object(monitor, "get_crawl_delay", return_value=0.05):
            t0 = time.monotonic()
            await monitor.enforce_delay(Platform.JD)
            elapsed = time.monotonic() - t0
            assert elapsed >= 0.04   # approximately respected

    def test_cache_entry_expires(self):
        parser = _make_parser()
        entry = RobotsCacheEntry(parser, 1.0, time.monotonic() - 999999)
        assert entry.is_expired() is True

    def test_cache_entry_fresh(self):
        parser = _make_parser()
        entry = RobotsCacheEntry(parser, 1.0, time.monotonic())
        assert entry.is_expired() is False


class TestCheckBeforeCrawl:
    @pytest.fixture
    def monitor(self):
        return ComplianceMonitor()

    @pytest.mark.asyncio
    async def test_allowed_path_increments_crawl_count(self, monitor):
        with patch.object(monitor, "is_allowed", AsyncMock(return_value=True)), \
             patch.object(monitor, "enforce_delay", AsyncMock()):
            await monitor.check_before_crawl(Platform.JD, "/product/123")
        assert monitor._crawl_count[Platform.JD] == 1
        assert monitor._blocked_count[Platform.JD] == 0

    @pytest.mark.asyncio
    async def test_disallowed_path_raises_and_increments_blocked(self, monitor):
        with patch.object(monitor, "is_allowed", AsyncMock(return_value=False)):
            with pytest.raises(ComplianceViolation, match="disallowed"):
                await monitor.check_before_crawl(Platform.TAOBAO, "/restricted")
        assert monitor._blocked_count[Platform.TAOBAO] == 1
        assert monitor._crawl_count[Platform.TAOBAO] == 0

    @pytest.mark.asyncio
    async def test_enforce_delay_called_for_allowed_path(self, monitor):
        mock_delay = AsyncMock()
        with patch.object(monitor, "is_allowed", AsyncMock(return_value=True)), \
             patch.object(monitor, "enforce_delay", mock_delay):
            await monitor.check_before_crawl(Platform.PDD, "/search")
        mock_delay.assert_called_once_with(Platform.PDD)

    @pytest.mark.asyncio
    async def test_enforce_delay_not_called_for_disallowed_path(self, monitor):
        mock_delay = AsyncMock()
        with patch.object(monitor, "is_allowed", AsyncMock(return_value=False)), \
             patch.object(monitor, "enforce_delay", mock_delay):
            with pytest.raises(ComplianceViolation):
                await monitor.check_before_crawl(Platform.DOUYIN, "/blocked")
        mock_delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_compliance_report_includes_counters(self, monitor):
        # Simulate 2 allowed + 1 blocked crawl on JD
        with patch.object(monitor, "is_allowed", AsyncMock(return_value=True)), \
             patch.object(monitor, "enforce_delay", AsyncMock()):
            await monitor.check_before_crawl(Platform.JD, "/a")
            await monitor.check_before_crawl(Platform.JD, "/b")
        with patch.object(monitor, "is_allowed", AsyncMock(return_value=False)):
            with pytest.raises(ComplianceViolation):
                await monitor.check_before_crawl(Platform.JD, "/blocked")

        with patch.object(monitor, "_get_entry", return_value=None):
            report = await monitor.compliance_report()

        assert report["jd"]["total_crawls"] == 2
        assert report["jd"]["blocked_crawls"] == 1

    @pytest.mark.asyncio
    async def test_default_path_is_root(self, monitor):
        """check_before_crawl() should default path to '/'."""
        mock_allowed = AsyncMock(return_value=True)
        with patch.object(monitor, "is_allowed", mock_allowed), \
             patch.object(monitor, "enforce_delay", AsyncMock()):
            await monitor.check_before_crawl(Platform.SUNING)
        mock_allowed.assert_called_once_with(Platform.SUNING, "/")


class TestPlatformMinDelays:
    """All 7 platforms must have a defined minimum delay."""

    def test_all_platforms_have_min_delay(self):
        for platform in Platform:
            assert platform in _MIN_DELAYS, f"Missing min delay for {platform}"
            assert _MIN_DELAYS[platform] >= 1.0, f"Min delay too low for {platform}"
