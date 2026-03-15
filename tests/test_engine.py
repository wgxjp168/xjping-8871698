"""Tests for DecisionHub engine (with mocked Claude API)."""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from l2_decision_hub.core.engine import DecisionHub
from l2_decision_hub.models.decision import DecisionResult, DecisionState, DecisionType
from l2_decision_hub.models.priority import Priority


def make_mock_result() -> DecisionResult:
    return DecisionResult(
        action="Proceed with option A",
        reasoning="Option A has the best risk/reward profile",
        confidence=0.87,
        alternatives=[],
        parameters={"option": "A"},
        metadata={"risk_level": "low"},
    )


@pytest.fixture
def hub():
    h = DecisionHub(api_key="test-key")
    return h


@pytest.mark.asyncio
async def test_submit_creates_decision(hub):
    with patch.object(hub, "_queue") as mock_queue:
        mock_queue.put = AsyncMock()
        decision_id = await hub.submit(
            title="Test",
            description="A test decision",
        )
        assert decision_id
        decision = await hub.state_manager.get_decision(decision_id)
        assert decision is not None
        assert decision.state == DecisionState.PENDING


@pytest.mark.asyncio
async def test_cancel_pending_decision(hub):
    with patch.object(hub, "_queue") as mock_queue:
        mock_queue.put = AsyncMock()
        decision_id = await hub.submit(title="T", description="D")
        cancelled = await hub.cancel(decision_id)
        assert cancelled is True
        decision = await hub.state_manager.get_decision(decision_id)
        assert decision.state == DecisionState.CANCELLED


@pytest.mark.asyncio
async def test_cancel_nonexistent_decision(hub):
    result = await hub.cancel("nonexistent-id")
    assert result is False


@pytest.mark.asyncio
async def test_full_pipeline_mocked():
    """Test full pipeline with mocked reasoner."""
    hub = DecisionHub(api_key="test-key")

    # Mock the reasoner to return a fixed result
    mock_result = make_mock_result()
    hub._reasoner.reason = AsyncMock(return_value=mock_result)

    await hub.start()

    decision_id = await hub.submit(
        title="Evaluate options",
        description="Pick the best option",
        decision_type=DecisionType.STRATEGIC,
        priority=Priority.HIGH,
        constraints=["Budget under $100k"],
        objectives=["Maximise ROI"],
    )

    # Wait for the pipeline to complete
    decision = await hub.wait_for_result(decision_id, timeout=10.0)

    assert decision.state == DecisionState.COMPLETED
    assert decision.result is not None
    assert decision.result.action == "Proceed with option A"
    assert decision.result.confidence == pytest.approx(0.87)

    await hub.stop()


@pytest.mark.asyncio
async def test_pipeline_failure_propagates():
    """Test that reasoner failures transition decision to FAILED."""
    hub = DecisionHub(api_key="test-key")
    hub._reasoner.reason = AsyncMock(side_effect=RuntimeError("Claude unavailable"))

    await hub.start()

    decision_id = await hub.submit(title="Fail me", description="This should fail")
    decision = await hub.wait_for_result(decision_id, timeout=10.0)

    assert decision.state == DecisionState.FAILED
    assert "Claude unavailable" in (decision.error or "")

    await hub.stop()


@pytest.mark.asyncio
async def test_list_decisions(hub):
    with patch.object(hub, "_queue") as mock_queue:
        mock_queue.put = AsyncMock()
        await hub.submit(title="D1", description="x")
        await hub.submit(title="D2", description="y")
        decisions = await hub.list_decisions()
        assert len(decisions) == 2


@pytest.mark.asyncio
async def test_wait_for_result_timeout():
    hub = DecisionHub(api_key="test-key")
    # Don't start the hub so the decision stays pending
    with patch.object(hub, "_queue") as mock_queue:
        mock_queue.put = AsyncMock()
        decision_id = await hub.submit(title="T", description="D")

    with pytest.raises(TimeoutError):
        await hub.wait_for_result(decision_id, timeout=0.1)
