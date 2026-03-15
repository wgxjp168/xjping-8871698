"""Unit tests for ComplianceMonitor."""
import time
from unittest.mock import AsyncMock, patch

import pytest

from app.models.schemas import Platform
from app.services.compliance_monitor import (
    ComplianceMonitor, RobotsCacheEntry, _MIN_DELAYS,
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
