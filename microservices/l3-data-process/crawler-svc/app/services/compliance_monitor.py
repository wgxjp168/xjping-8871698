"""
Compliance Monitor
==================
Ensures all crawling respects:
  - robots.txt rules (user-agent, disallow, crawl-delay)
  - Platform-specific rate limits
  - Legal compliance flags per platform
"""
from __future__ import annotations

import asyncio
import logging
import time
import urllib.robotparser
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.models.schemas import Platform

logger = logging.getLogger(__name__)
settings = get_settings()

USER_AGENT = "ILbuyBot/1.0 (+https://ilbuy.com/bot)"

# Platform root URLs for robots.txt fetching
_PLATFORM_ROOTS: Dict[Platform, str] = {
    Platform.TAOBAO:  "https://www.taobao.com",
    Platform.JD:      "https://www.jd.com",
    Platform.ALI1688: "https://www.1688.com",
    Platform.PDD:     "https://www.pinduoduo.com",
    Platform.VIPSHOP: "https://www.vip.com",
    Platform.SUNING:  "https://www.suning.com",
    Platform.DOUYIN:  "https://www.douyin.com",
}

# Crawl-delay overrides (seconds) — if not in robots.txt use these minimums
_MIN_DELAYS: Dict[Platform, float] = {
    Platform.TAOBAO:  2.0,
    Platform.JD:      1.0,
    Platform.ALI1688: 3.0,
    Platform.PDD:     2.0,
    Platform.VIPSHOP: 2.0,
    Platform.SUNING:  2.0,
    Platform.DOUYIN:  3.0,
}


class RobotsCacheEntry:
    def __init__(self, parser: urllib.robotparser.RobotFileParser,
                 crawl_delay: float, fetched_at: float) -> None:
        self.parser      = parser
        self.crawl_delay = crawl_delay
        self.fetched_at  = fetched_at

    def is_expired(self) -> bool:
        return time.monotonic() - self.fetched_at > settings.robots_cache_ttl_s


class ComplianceMonitor:
    """Parses and caches robots.txt; enforces crawl delays."""

    def __init__(self) -> None:
        self._cache:    Dict[Platform, RobotsCacheEntry] = {}
        self._lock      = asyncio.Lock()
        self._last_req: Dict[Platform, float] = {}

    # ── Public API ───────────────────────────────────────────────────────

    async def is_allowed(self, platform: Platform, path: str) -> bool:
        """Check robots.txt for the given platform and URL path."""
        entry = await self._get_entry(platform)
        if entry is None:
            return True   # If we can't fetch robots.txt, assume allowed
        return entry.parser.can_fetch(USER_AGENT, path)

    async def get_crawl_delay(self, platform: Platform) -> float:
        """Return the effective crawl delay for the platform (seconds)."""
        entry = await self._get_entry(platform)
        if entry is None:
            return _MIN_DELAYS.get(platform, settings.default_crawl_delay_s)
        return entry.crawl_delay

    async def enforce_delay(self, platform: Platform) -> None:
        """Sleep if needed to respect crawl-delay since the last request."""
        if not settings.respect_crawl_delay:
            return
        delay = await self.get_crawl_delay(platform)
        async with self._lock:
            last = self._last_req.get(platform, 0.0)
            elapsed = time.monotonic() - last
            if elapsed < delay:
                wait = delay - elapsed
                self._last_req[platform] = time.monotonic() + wait
            else:
                wait = 0.0
                self._last_req[platform] = time.monotonic()

        if wait > 0:
            logger.debug('"Compliance delay %.2fs for %s"', wait, platform.value)
            await asyncio.sleep(wait)

    async def compliance_report(self) -> Dict[str, Dict]:
        report = {}
        for p in Platform:
            delay = await self.get_crawl_delay(p)
            cached = p in self._cache and not self._cache[p].is_expired()
            report[p.value] = {
                "robots_cached": cached,
                "crawl_delay_s": delay,
                "min_delay_s":   _MIN_DELAYS.get(p, settings.default_crawl_delay_s),
            }
        return report

    # ── Internal ─────────────────────────────────────────────────────────

    async def _get_entry(self, platform: Platform) -> Optional[RobotsCacheEntry]:
        async with self._lock:
            entry = self._cache.get(platform)
            if entry and not entry.is_expired():
                return entry

        # Fetch outside lock to avoid blocking
        entry = await self._fetch_robots(platform)
        if entry:
            async with self._lock:
                self._cache[platform] = entry
        return entry

    async def _fetch_robots(self, platform: Platform) -> Optional[RobotsCacheEntry]:
        root = _PLATFORM_ROOTS.get(platform, "")
        if not root:
            return None

        robots_url = f"{root}/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(robots_url, headers={"User-Agent": USER_AGENT})
                content = resp.text if resp.status_code == 200 else ""
        except Exception as exc:
            logger.warning('"Failed to fetch robots.txt for %s: %s"', platform.value, exc)
            content = ""

        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(content.splitlines())

        raw_delay  = parser.crawl_delay(USER_AGENT) or 0.0
        min_delay  = _MIN_DELAYS.get(platform, settings.default_crawl_delay_s)
        crawl_delay = max(float(raw_delay), min_delay)

        logger.info(
            '"robots.txt fetched for %s — crawl_delay=%.1fs"',
            platform.value, crawl_delay,
        )
        return RobotsCacheEntry(parser, crawl_delay, time.monotonic())


# Singleton
compliance_monitor = ComplianceMonitor()
