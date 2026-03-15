"""In-memory state manager for decisions and sessions."""

from __future__ import annotations

import asyncio
import logging
from typing import Iterator

from l2_decision_hub.models.context import DecisionContext
from l2_decision_hub.models.decision import Decision, DecisionState

logger = logging.getLogger(__name__)


class StateManager:
    """Thread-safe (asyncio-safe) store for active decisions and their contexts.

    Uses asyncio.Lock to serialise concurrent writes.
    Decisions are kept in memory; for persistence, swap this with a DB-backed store.
    """

    def __init__(self) -> None:
        self._decisions: dict[str, Decision] = {}
        self._contexts: dict[str, DecisionContext] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Decision CRUD
    # ------------------------------------------------------------------

    async def add_decision(self, decision: Decision) -> None:
        async with self._lock:
            self._decisions[decision.id] = decision
            logger.debug("StateManager: added decision id=%s", decision.id)

    async def get_decision(self, decision_id: str) -> Decision | None:
        return self._decisions.get(decision_id)

    async def update_decision(self, decision: Decision) -> None:
        async with self._lock:
            if decision.id not in self._decisions:
                raise KeyError(f"Decision {decision.id!r} not found")
            self._decisions[decision.id] = decision

    async def delete_decision(self, decision_id: str) -> bool:
        async with self._lock:
            if decision_id in self._decisions:
                del self._decisions[decision_id]
                self._contexts.pop(decision_id, None)
                return True
            return False

    async def list_decisions(
        self,
        state: DecisionState | None = None,
        decision_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Decision]:
        decisions = list(self._decisions.values())
        if state:
            decisions = [d for d in decisions if d.state == state]
        if decision_type:
            decisions = [d for d in decisions if d.type.value == decision_type]
        # Sort by priority desc, then created_at asc
        decisions.sort(key=lambda d: (-d.priority, d.created_at))
        return decisions[offset : offset + limit]

    async def count_decisions(self, state: DecisionState | None = None) -> int:
        decisions = self._decisions.values()
        if state:
            return sum(1 for d in decisions if d.state == state)
        return len(self._decisions)

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------

    async def get_or_create_context(
        self, decision: Decision, session_id: str | None = None
    ) -> DecisionContext:
        async with self._lock:
            ctx = self._contexts.get(decision.id)
            if ctx is None:
                ctx = DecisionContext(
                    session_id=session_id or decision.id,
                    decision_id=decision.id,
                )
                self._contexts[decision.id] = ctx
            return ctx

    async def save_context(self, context: DecisionContext) -> None:
        async with self._lock:
            self._contexts[context.decision_id] = context

    # ------------------------------------------------------------------
    # Iteration helpers
    # ------------------------------------------------------------------

    def iter_pending(self) -> Iterator[Decision]:
        """Yield decisions in PENDING state, ordered by priority (highest first)."""
        pending = sorted(
            (d for d in self._decisions.values() if d.state == DecisionState.PENDING),
            key=lambda d: -d.priority,
        )
        yield from pending
