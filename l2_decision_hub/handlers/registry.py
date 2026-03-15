"""Handler registry — stores and selects handlers for decisions."""

from __future__ import annotations

import logging

from l2_decision_hub.handlers.base import BaseHandler, LoggingHandler
from l2_decision_hub.models.decision import Decision

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """Stores registered handlers and selects the best match for a decision.

    Selection order:
    1. Handlers are evaluated in registration order.
    2. The first handler for which ``can_handle()`` is True is used.
    3. If no specific handler matches, the LoggingHandler fallback is used.
    """

    def __init__(self) -> None:
        self._handlers: list[BaseHandler] = []
        self._fallback = LoggingHandler()

    def register(self, handler: BaseHandler) -> None:
        """Register a handler. Later registrations take lower precedence."""
        self._handlers.append(handler)
        logger.debug("Registered handler %r (types=%s)", handler.name, handler.supported_types)

    def unregister(self, handler_name: str) -> bool:
        before = len(self._handlers)
        self._handlers = [h for h in self._handlers if h.name != handler_name]
        return len(self._handlers) < before

    def select(self, decision: Decision) -> BaseHandler:
        """Return the first handler that can process this decision."""
        for handler in self._handlers:
            if handler.can_handle(decision):
                return handler
        logger.debug(
            "No specific handler matched decision %s (type=%s), using fallback",
            decision.id,
            decision.type.value,
        )
        return self._fallback

    def list_handlers(self) -> list[dict]:
        return [
            {
                "name": h.name,
                "supported_types": [t.value for t in h.supported_types],
                "min_priority": h.min_priority,
            }
            for h in self._handlers
        ]
