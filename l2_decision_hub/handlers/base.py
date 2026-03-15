"""Base handler interface for executing decisions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from l2_decision_hub.models.decision import Decision, DecisionType


class HandlerResult(BaseModel):
    """Result returned by a handler after executing a decision."""
    success: bool
    message: str = ""
    output: dict[str, Any] = {}


class BaseHandler(ABC):
    """Abstract base class for decision handlers.

    Subclass this to implement custom execution logic.

    Example::

        class AlertHandler(BaseHandler):
            name = "alert"
            supported_types = [DecisionType.RISK, DecisionType.ESCALATION]

            async def handle(self, decision: Decision) -> HandlerResult:
                # Send alert based on decision.result
                return HandlerResult(success=True, message="Alert sent")
    """

    #: Unique handler name used for routing and logging
    name: str = "base"

    #: Decision types this handler can process (empty = all types)
    supported_types: list[DecisionType] = []

    #: Minimum priority level for this handler (1-5)
    min_priority: int = 1

    def can_handle(self, decision: Decision) -> bool:
        """Return True if this handler accepts the given decision."""
        if self.supported_types and decision.type not in self.supported_types:
            return False
        if decision.priority < self.min_priority:
            return False
        return True

    @abstractmethod
    async def handle(self, decision: Decision) -> HandlerResult:
        """Execute the decision and return a result.

        Args:
            decision: The decided decision (decision.result is set).

        Returns:
            HandlerResult describing the execution outcome.
        """
        ...


class LoggingHandler(BaseHandler):
    """Built-in handler that logs every decision (catch-all fallback)."""

    name = "logging"
    supported_types = []  # handles all types

    async def handle(self, decision: Decision) -> HandlerResult:
        import logging
        logger = logging.getLogger(__name__)
        result = decision.result
        logger.info(
            "[LoggingHandler] decision_id=%s action=%r confidence=%.2f",
            decision.id,
            result.action if result else "N/A",
            result.confidence if result else 0.0,
        )
        return HandlerResult(
            success=True,
            message=f"Logged decision {decision.id}",
            output={"action": result.action if result else ""},
        )
