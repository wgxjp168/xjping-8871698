"""Tests for the StateManager."""

import pytest

from l2_decision_hub.core.state import StateManager
from l2_decision_hub.models.decision import Decision, DecisionState, DecisionType


@pytest.fixture
def decision():
    return Decision(
        title="Test Decision",
        description="A decision for testing",
        type=DecisionType.OPERATIONAL,
        priority=3,
    )


@pytest.mark.asyncio
async def test_add_and_get(decision):
    sm = StateManager()
    await sm.add_decision(decision)
    fetched = await sm.get_decision(decision.id)
    assert fetched is not None
    assert fetched.id == decision.id


@pytest.mark.asyncio
async def test_update_decision(decision):
    sm = StateManager()
    await sm.add_decision(decision)
    decision.transition(DecisionState.REASONING)
    await sm.update_decision(decision)
    updated = await sm.get_decision(decision.id)
    assert updated.state == DecisionState.REASONING


@pytest.mark.asyncio
async def test_delete_decision(decision):
    sm = StateManager()
    await sm.add_decision(decision)
    deleted = await sm.delete_decision(decision.id)
    assert deleted is True
    assert await sm.get_decision(decision.id) is None


@pytest.mark.asyncio
async def test_list_decisions_filter_by_state():
    sm = StateManager()
    d1 = Decision(title="D1", description="x")
    d2 = Decision(title="D2", description="y")
    d2.transition(DecisionState.COMPLETED)
    await sm.add_decision(d1)
    await sm.add_decision(d2)

    pending = await sm.list_decisions(state=DecisionState.PENDING)
    assert len(pending) == 1
    assert pending[0].id == d1.id


@pytest.mark.asyncio
async def test_count_decisions():
    sm = StateManager()
    for i in range(3):
        await sm.add_decision(Decision(title=f"D{i}", description="x"))
    assert await sm.count_decisions() == 3
    assert await sm.count_decisions(DecisionState.PENDING) == 3


@pytest.mark.asyncio
async def test_get_or_create_context(decision):
    sm = StateManager()
    await sm.add_decision(decision)
    ctx = await sm.get_or_create_context(decision)
    assert ctx.decision_id == decision.id
    # Calling again returns same context
    ctx2 = await sm.get_or_create_context(decision)
    assert ctx2.decision_id == ctx.decision_id


@pytest.mark.asyncio
async def test_iter_pending():
    sm = StateManager()
    low = Decision(title="low", description="x", priority=1)
    high = Decision(title="high", description="x", priority=5)
    await sm.add_decision(low)
    await sm.add_decision(high)
    pending = list(sm.iter_pending())
    # High priority first
    assert pending[0].priority == 5
