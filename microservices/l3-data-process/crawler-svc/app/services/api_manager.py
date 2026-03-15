"""
API Call Manager
================
Provides per-platform:
  - Token-bucket rate limiting (requests per minute)
  - Exponential-backoff retry with jitter
  - Circuit breaker (open → half-open → closed)
  - Per-platform HTTP session management
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

import httpx

from app.core.config import get_settings
from app.models.schemas import Platform

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Token-bucket rate limiter
# ---------------------------------------------------------------------------

class TokenBucket:
    """Thread-safe async token bucket (capacity = rpm, refill every 60 s)."""

    def __init__(self, rpm: int) -> None:
        self._rpm         = rpm
        self._tokens      = float(rpm)
        self._max_tokens  = float(rpm)
        self._refill_rate = rpm / 60.0   # tokens / second
        self._last_refill = time.monotonic()
        self._lock        = asyncio.Lock()

    async def acquire(self, timeout: float = 30.0) -> bool:
        deadline = time.monotonic() + timeout
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self._last_refill
                self._tokens = min(
                    self._max_tokens,
                    self._tokens + elapsed * self._refill_rate,
                )
                self._last_refill = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            wait = min(1.0 / self._refill_rate, remaining)
            await asyncio.sleep(wait + random.uniform(0, min(0.05, wait)))

    @property
    def current_rpm(self) -> float:
        return self._tokens * (60.0 / 1.0)


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

class CBState(Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int   = 5
    recovery_timeout:  float = 60.0   # seconds
    half_open_limit:   int   = 2

    _state:          CBState  = field(default=CBState.CLOSED, init=False)
    _failure_count:  int      = field(default=0, init=False)
    _last_failure:   float    = field(default=0.0, init=False)
    _half_open_pass: int      = field(default=0, init=False)

    @property
    def state(self) -> CBState:
        if self._state == CBState.OPEN:
            if time.monotonic() - self._last_failure >= self.recovery_timeout:
                self._state = CBState.HALF_OPEN
                self._half_open_pass = 0
        return self._state

    def allow_request(self) -> bool:
        s = self.state
        if s == CBState.CLOSED:
            return True
        if s == CBState.HALF_OPEN:
            return self._half_open_pass < self.half_open_limit
        return False

    def record_success(self) -> None:
        if self._state == CBState.HALF_OPEN:
            self._half_open_pass += 1
            if self._half_open_pass >= self.half_open_limit:
                self._state = CBState.CLOSED
                self._failure_count = 0
        else:
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CBState.OPEN
            logger.warning("Circuit breaker OPEN")


# ---------------------------------------------------------------------------
# Per-platform context
# ---------------------------------------------------------------------------

_RPM_MAP: Dict[Platform, int] = {
    Platform.TAOBAO:  settings.taobao_rpm,
    Platform.JD:      settings.jd_rpm,
    Platform.ALI1688: settings.ali1688_rpm,
    Platform.PDD:     settings.pdd_rpm,
    Platform.VIPSHOP: settings.vipshop_rpm,
    Platform.SUNING:  settings.suning_rpm,
    Platform.DOUYIN:  settings.douyin_rpm,
}


@dataclass
class PlatformContext:
    platform:        Platform
    bucket:          TokenBucket
    breaker:         CircuitBreaker = field(default_factory=CircuitBreaker)
    request_history: deque          = field(default_factory=lambda: deque(maxlen=200))
    total_requests:  int            = 0
    total_errors:    int            = 0


# ---------------------------------------------------------------------------
# API Manager
# ---------------------------------------------------------------------------

class APIManager:
    """Central manager for all outbound HTTP calls to e-commerce platforms."""

    def __init__(self) -> None:
        self._contexts: Dict[Platform, PlatformContext] = {
            p: PlatformContext(
                platform=p,
                bucket=TokenBucket(rpm=_RPM_MAP.get(p, 30)),
            )
            for p in Platform
        }
        self._client: Optional[httpx.AsyncClient] = None
        self._start_time = time.monotonic()

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.http_timeout_s),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            follow_redirects=True,
        )
        logger.info('"API manager started"')

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
        logger.info('"API manager stopped"')

    # ── Public call interface ─────────────────────────────────────────────

    async def call(
        self,
        platform: Platform,
        method: str,
        url: str,
        *,
        params: Optional[Dict] = None,
        json: Optional[Dict]   = None,
        headers: Optional[Dict] = None,
        proxy: Optional[str]   = None,
        retries: int           = settings.http_max_retries,
    ) -> httpx.Response:
        ctx = self._contexts[platform]

        if not ctx.breaker.allow_request():
            raise RuntimeError(f"Circuit breaker OPEN for {platform.value}")

        acquired = await ctx.bucket.acquire(timeout=30.0)
        if not acquired:
            raise TimeoutError(f"Rate limit timeout for {platform.value}")

        last_exc: Optional[Exception] = None
        for attempt in range(1, retries + 2):
            try:
                t0 = time.monotonic()
                resp = await self._client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                    proxy=proxy,
                )
                latency_ms = int((time.monotonic() - t0) * 1000)

                ctx.total_requests += 1
                ctx.request_history.append(
                    {"ts": time.monotonic(), "latency_ms": latency_ms, "status": resp.status_code}
                )

                if resp.status_code in (429, 503):
                    # Respect Retry-After header if present
                    retry_after = float(resp.headers.get("Retry-After", 5 * attempt))
                    logger.warning(
                        '"platform %s rate-limited (attempt %d), wait %.1fs"',
                        platform.value, attempt, retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                resp.raise_for_status()
                ctx.breaker.record_success()
                return resp

            except (httpx.HTTPStatusError, httpx.RequestError, Exception) as exc:
                last_exc = exc
                ctx.total_errors += 1
                ctx.breaker.record_failure()

                if attempt > retries:
                    break

                delay = settings.http_retry_delay_s * (settings.http_backoff_factor ** (attempt - 1))
                jitter = random.uniform(0, delay * 0.3)
                logger.warning(
                    '"platform %s request failed (attempt %d/%d): %s — retry in %.1fs"',
                    platform.value, attempt, retries + 1, exc, delay + jitter,
                )
                await asyncio.sleep(delay + jitter)

        raise RuntimeError(f"{platform.value} call failed after {retries+1} attempts: {last_exc}") from last_exc

    # ── Status ────────────────────────────────────────────────────────────

    def get_platform_rpm(self, platform: Platform) -> float:
        ctx = self._contexts[platform]
        now = time.monotonic()
        recent = [r for r in ctx.request_history if now - r["ts"] <= 60]
        return float(len(recent))

    def get_breaker_state(self, platform: Platform) -> str:
        return self._contexts[platform].breaker.state.value

    def uptime_s(self) -> float:
        return time.monotonic() - self._start_time


# Singleton
api_manager = APIManager()
