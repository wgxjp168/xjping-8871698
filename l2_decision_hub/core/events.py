"""Async event bus for the L2 Decision Hub."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# Subscriber type: async callable that receives an event payload dict
Subscriber = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class EventType(str, Enum):
    """Well-known event types emitted by the hub."""
    DECISION_CREATED = "decision.created"
    DECISION_REASONING_STARTED = "decision.reasoning.started"
    DECISION_REASONING_COMPLETED = "decision.reasoning.completed"
    DECISION_EXECUTING = "decision.executing"
    DECISION_COMPLETED = "decision.completed"
    DECISION_FAILED = "decision.failed"
    DECISION_CANCELLED = "decision.cancelled"
    HUB_STARTED = "hub.started"
    HUB_STOPPED = "hub.stopped"


class EventBus:
    """Simple async publish-subscribe event bus.

    Subscribers are async callables; they are invoked concurrently
    via asyncio.gather for each published event.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self._wildcard: list[Subscriber] = []

    def subscribe(self, event_type: str | EventType, handler: Subscriber) -> None:
        """Register a subscriber for a specific event type."""
        key = event_type.value if isinstance(event_type, EventType) else str(event_type)
        self._subscribers[key].append(handler)

    def subscribe_all(self, handler: Subscriber) -> None:
        """Register a subscriber for ALL events (wildcard)."""
        self._wildcard.append(handler)

    def unsubscribe(self, event_type: str | EventType, handler: Subscriber) -> None:
        """Remove a subscriber."""
        key = event_type.value if isinstance(event_type, EventType) else str(event_type)
        self._subscribers[key] = [h for h in self._subscribers[key] if h is not handler]

    async def publish(self, event_type: str | EventType, payload: dict[str, Any]) -> None:
        """Publish an event to all registered subscribers.

        Each subscriber is called concurrently; exceptions are logged but not re-raised.
        """
        key = event_type.value if isinstance(event_type, EventType) else str(event_type)
        handlers = list(self._subscribers.get(key, [])) + list(self._wildcard)

        if not handlers:
            return

        full_payload = {"event_type": key, **payload}
        tasks = [self._safe_call(h, full_payload) for h in handlers]
        await asyncio.gather(*tasks)

    @staticmethod
    async def _safe_call(handler: Subscriber, payload: dict[str, Any]) -> None:
        try:
            await handler(payload)
        except Exception:
            logger.exception("EventBus subscriber raised an exception")
