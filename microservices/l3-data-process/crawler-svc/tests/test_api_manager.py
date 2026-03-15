"""
Unit tests for APIManager — rate limiting, circuit breaker, retry logic.
"""
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.api_manager import (
    APIManager, CircuitBreaker, CBState, TokenBucket,
)
from app.models.schemas import Platform


# ── TokenBucket ───────────────────────────────────────────────────────────────

class TestTokenBucket:
    def test_initial_tokens_full(self):
        bucket = TokenBucket(rpm=60)
        assert bucket._tokens == 60.0

    @pytest.mark.asyncio
    async def test_acquire_reduces_tokens(self):
        bucket = TokenBucket(rpm=60)
        ok = await bucket.acquire(timeout=1.0)
        assert ok is True
        assert bucket._tokens < 60.0

    @pytest.mark.asyncio
    async def test_acquire_timeout_when_empty(self):
        bucket = TokenBucket(rpm=1)
        bucket._tokens = 0.0
        bucket._last_refill = time.monotonic()   # reset so no refill occurs during tiny timeout
        # With 1 rpm, refill in 0.05s = 0.05/60 ≈ 0.0008 tokens — not enough for 1 token
        ok = await bucket.acquire(timeout=0.05)
        assert ok is False

    @pytest.mark.asyncio
    async def test_tokens_refill_over_time(self):
        bucket = TokenBucket(rpm=120)
        bucket._tokens = 0.0
        bucket._last_refill = time.monotonic() - 1.0   # simulate 1s elapsed
        ok = await bucket.acquire(timeout=0.1)
        assert ok is True   # 2 tokens refilled in 1s (120/60)


# ── CircuitBreaker ────────────────────────────────────────────────────────────

class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CBState.CLOSED
        assert cb.allow_request() is True

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CBState.OPEN
        assert cb.allow_request() is False

    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0)
        cb.record_failure()
        # With recovery_timeout=0.0, the state property immediately transitions
        # OPEN → HALF_OPEN on first access (no actual waiting needed).
        # The first .state access after failure may already see HALF_OPEN.
        assert cb.state in (CBState.OPEN, CBState.HALF_OPEN)
        # After forcing at least one state check, it must be HALF_OPEN
        assert cb.state == CBState.HALF_OPEN
        assert cb.allow_request() is True

    def test_closes_after_half_open_successes(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.0, half_open_limit=2)
        cb.record_failure()
        assert cb.state == CBState.HALF_OPEN
        cb.record_success()
        cb.record_success()
        assert cb.state == CBState.CLOSED

    def test_success_decrements_failure_count(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 1


# ── APIManager ────────────────────────────────────────────────────────────────

class TestAPIManager:
    @pytest.mark.asyncio
    async def test_start_creates_client(self):
        mgr = APIManager()
        await mgr.start()
        assert mgr._client is not None
        await mgr.stop()

    @pytest.mark.asyncio
    async def test_call_raises_when_circuit_open(self):
        mgr = APIManager()
        await mgr.start()
        ctx = mgr._contexts[Platform.JD]
        ctx.breaker._state = CBState.OPEN
        ctx.breaker._last_failure = time.monotonic()  # recent failure — stays open

        with pytest.raises(RuntimeError, match="Circuit breaker OPEN"):
            await mgr.call(Platform.JD, "GET", "http://example.com")
        await mgr.stop()

    @pytest.mark.asyncio
    async def test_call_retries_on_failure(self):
        mgr = APIManager()
        await mgr.start()

        call_count = 0

        async def fake_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("network error")

        mgr._client.request = fake_request

        with pytest.raises(RuntimeError):
            await mgr.call(Platform.TAOBAO, "GET", "http://x.com", retries=2)

        assert call_count == 3   # 1 original + 2 retries
        await mgr.stop()

    def test_get_platform_rpm_empty_history(self):
        mgr = APIManager()
        assert mgr.get_platform_rpm(Platform.TAOBAO) == 0.0
