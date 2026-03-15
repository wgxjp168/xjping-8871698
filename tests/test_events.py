"""Tests for the EventBus."""

import asyncio
import pytest

from l2_decision_hub.core.events import EventBus, EventType


@pytest.mark.asyncio
async def test_subscribe_and_publish():
    bus = EventBus()
    received = []

    async def handler(payload):
        received.append(payload)

    bus.subscribe(EventType.DECISION_CREATED, handler)
    await bus.publish(EventType.DECISION_CREATED, {"decision_id": "abc"})

    assert len(received) == 1
    assert received[0]["decision_id"] == "abc"
    assert received[0]["event_type"] == "decision.created"


@pytest.mark.asyncio
async def test_wildcard_subscriber():
    bus = EventBus()
    received = []

    async def handler(payload):
        received.append(payload["event_type"])

    bus.subscribe_all(handler)
    await bus.publish(EventType.HUB_STARTED, {})
    await bus.publish(EventType.DECISION_CREATED, {})

    assert len(received) == 2
    assert "hub.started" in received or EventType.HUB_STARTED.value in received


@pytest.mark.asyncio
async def test_unsubscribe():
    bus = EventBus()
    received = []

    async def handler(payload):
        received.append(1)

    bus.subscribe(EventType.DECISION_COMPLETED, handler)
    bus.unsubscribe(EventType.DECISION_COMPLETED, handler)
    await bus.publish(EventType.DECISION_COMPLETED, {})

    assert received == []


@pytest.mark.asyncio
async def test_subscriber_exception_is_swallowed():
    bus = EventBus()

    async def bad_handler(payload):
        raise RuntimeError("boom")

    bus.subscribe(EventType.DECISION_FAILED, bad_handler)
    # Should not raise
    await bus.publish(EventType.DECISION_FAILED, {})
