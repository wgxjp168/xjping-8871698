"""Decision router — dispatches decided decisions to handlers."""

from __future__ import annotations

import logging

from l2_decision_hub.core.events import EventBus
from l2_decision_hub.handlers.registry import HandlerRegistry
from l2_decision_hub.models.decision import Decision

logger = logging.getLogger(__name__)


class DecisionRouter:
    """Routes a decided decision to the appropriate handler.

    Maintains a HandlerRegistry and delegates dispatch to it.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._registry = HandlerRegistry()
        self._events = event_bus

    @property
    def registry(self) -> HandlerRegistry:
        return self._registry

    async def dispatch(self, decision: Decision) -> None:
        """Find the right handler and execute it.

        Args:
            decision: A decision in DECIDED state with ``result`` set.

        Raises:
            RuntimeError: If the decision has no result.
        """
        if decision.result is None:
            raise RuntimeError(f"Decision {decision.id} has no result to dispatch")

        handler = self._registry.select(decision)
        logger.info(
            "Routing decision id=%s to handler=%r", decision.id, handler.name
        )

        result = await handler.handle(decision)

        if not result.success:
            raise RuntimeError(
                f"Handler {handler.name!r} reported failure: {result.message}"
            )

        logger.info(
            "Handler %r completed for decision %s: %s",
            handler.name,
            decision.id,
            result.message,
        )
