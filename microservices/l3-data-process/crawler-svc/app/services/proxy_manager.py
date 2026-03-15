"""
Proxy IP Pool Manager
=====================
Maintains a rotating pool of HTTP proxies with:
  - Health checking (async latency probes)
  - Automatic eviction on repeated failures
  - Round-robin rotation with success-rate weighting
  - Redis-backed persistence (optional)
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.models.schemas import ProxyRecord, ProxyStatus

logger = logging.getLogger(__name__)
settings = get_settings()

_PROBE_URL = "https://httpbin.org/ip"   # lightweight check endpoint


class ProxyManager:
    """Manages a pool of rotating proxy IPs."""

    def __init__(self) -> None:
        self._pool:       List[ProxyRecord] = []
        self._lock        = asyncio.Lock()
        self._rr_index    = 0
        self._check_task: Optional[asyncio.Task] = None

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        if not settings.proxy_enabled:
            logger.info('"Proxy pool disabled — running direct"')
            return
        await self._load_seed_proxies()
        self._check_task = asyncio.create_task(self._health_check_loop())
        logger.info('"Proxy manager started with %d proxies"', len(self._pool))

    async def stop(self) -> None:
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

    # ── Public API ───────────────────────────────────────────────────────

    async def get_proxy(self, prefer_fast: bool = True) -> Optional[str]:
        """Return a proxy URL or None if pool is empty / disabled."""
        if not settings.proxy_enabled:
            return None

        async with self._lock:
            active = [p for p in self._pool if p.status == ProxyStatus.ACTIVE]
            if not active:
                logger.warning('"No active proxies available"')
                return None

            if prefer_fast:
                # Weighted by success_rate; higher rate → more likely chosen
                weights = [max(0.01, p.success_rate) for p in active]
                chosen = random.choices(active, weights=weights, k=1)[0]
            else:
                chosen = active[self._rr_index % len(active)]
                self._rr_index += 1

            chosen.last_used = time.time()
            return chosen.url

    async def add_proxy(self, host: str, port: int, protocol: str = "http",
                        username: Optional[str] = None,
                        password: Optional[str] = None) -> ProxyRecord:
        record = ProxyRecord(
            host=host, port=port, protocol=protocol,
            username=username, password=password,
        )
        async with self._lock:
            # Deduplicate by host:port
            existing = {f"{p.host}:{p.port}" for p in self._pool}
            key = f"{host}:{port}"
            if key not in existing:
                self._pool.append(record)
                logger.info('"Added proxy %s"', key)
        return record

    async def report_failure(self, proxy_url: str) -> None:
        async with self._lock:
            for p in self._pool:
                if p.url == proxy_url:
                    p.fail_count += 1
                    if p.fail_count >= settings.proxy_max_fail_count:
                        p.status = ProxyStatus.FAILED
                        logger.warning('"Proxy %s:%d marked FAILED"', p.host, p.port)
                    break

    async def report_success(self, proxy_url: str) -> None:
        async with self._lock:
            for p in self._pool:
                if p.url == proxy_url:
                    p.success_count += 1
                    p.fail_count = max(0, p.fail_count - 1)
                    p.status = ProxyStatus.ACTIVE
                    break

    def pool_size(self) -> int:
        return len(self._pool)

    def active_count(self) -> int:
        return sum(1 for p in self._pool if p.status == ProxyStatus.ACTIVE)

    def pool_stats(self) -> Dict:
        active  = [p for p in self._pool if p.status == ProxyStatus.ACTIVE]
        failed  = [p for p in self._pool if p.status == ProxyStatus.FAILED]
        banned  = [p for p in self._pool if p.status == ProxyStatus.BANNED]
        avg_rate = (
            sum(p.success_rate for p in active) / len(active) if active else 0.0
        )
        return {
            "total":        len(self._pool),
            "active":       len(active),
            "failed":       len(failed),
            "banned":       len(banned),
            "avg_success_rate": round(avg_rate, 3),
        }

    # ── Internal ─────────────────────────────────────────────────────────

    async def _load_seed_proxies(self) -> None:
        """
        In production, load proxies from Redis / external provider.
        Here we keep the pool empty until proxies are added via add_proxy().
        """
        logger.info('"Proxy seed loaded (pool empty — add via API)"')

    async def _health_check_loop(self) -> None:
        while True:
            await asyncio.sleep(settings.proxy_check_interval_s)
            await self._check_all()

    async def _check_all(self) -> None:
        async with self._lock:
            pool_copy = list(self._pool)

        tasks = [self._probe(p) for p in pool_copy]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        async with self._lock:
            for proxy, result in zip(pool_copy, results):
                if isinstance(result, Exception):
                    proxy.fail_count += 1
                    if proxy.fail_count >= settings.proxy_max_fail_count:
                        proxy.status = ProxyStatus.FAILED
                else:
                    proxy.latency_ms = result
                    proxy.success_count += 1
                    proxy.status = ProxyStatus.ACTIVE
                    proxy.fail_count = max(0, proxy.fail_count - 1)
                proxy.last_checked = time.time()

        logger.info('"Proxy health check complete: %s"', self.pool_stats())

    async def _probe(self, proxy: ProxyRecord) -> int:
        """Returns latency_ms or raises on failure."""
        t0 = time.monotonic()
        async with httpx.AsyncClient(
            proxy=proxy.url,
            timeout=settings.proxy_timeout_s,
        ) as client:
            resp = await client.get(_PROBE_URL)
            resp.raise_for_status()
        return int((time.monotonic() - t0) * 1000)


# Singleton
proxy_manager = ProxyManager()
