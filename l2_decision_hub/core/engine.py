"""L2 AI Decision Hub — Core Engine.

DecisionHub is the central orchestrator:
  1. Accepts Decision submissions
  2. Manages lifecycle via StateManager
  3. Dispatches reasoning to DecisionReasoner (Claude AI)
  4. Routes results to registered handlers via DecisionRouter
  5. Emits lifecycle events via EventBus
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from l2_decision_hub.ai.client import ClaudeClient
from l2_decision_hub.ai.reasoner import DecisionReasoner
from l2_decision_hub.core.events import EventBus, EventType
from l2_decision_hub.core.router import DecisionRouter
from l2_decision_hub.core.state import StateManager
from l2_decision_hub.models.decision import Decision, DecisionState, DecisionType
from l2_decision_hub.models.priority import Priority

logger = logging.getLogger(__name__)


class DecisionHub:
    """The L2 AI Decision Hub core engine.

    Usage::

        hub = DecisionHub(api_key="sk-ant-...")
        await hub.start()

        decision_id = await hub.submit(
            title="Allocate emergency resources",
            description="...",
            decision_type=DecisionType.RESOURCE,
            priority=Priority.HIGH,
        )

        result = await hub.wait_for_result(decision_id)
        print(result.action)

        await hub.stop()
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-opus-4-6",
        max_concurrent: int = 5,
        auto_execute: bool = True,
    ) -> None:
        self._client = ClaudeClient(api_key=api_key, model=model)
        self._reasoner = DecisionReasoner(self._client)
        self._state = StateManager()
        self._events = EventBus()
        self._router = DecisionRouter(self._events)
        self._max_concurrent = max_concurrent
        self._auto_execute = auto_execute
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background decision worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        await self._events.publish(EventType.HUB_STARTED, {"hub": "L2-AI Decision Hub"})
        logger.info("DecisionHub started (max_concurrent=%d)", self._max_concurrent)

    async def stop(self) -> None:
        """Gracefully stop the hub."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        await self._events.publish(EventType.HUB_STOPPED, {"hub": "L2-AI Decision Hub"})
        logger.info("DecisionHub stopped")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def submit(
        self,
        title: str,
        description: str,
        decision_type: DecisionType = DecisionType.OPERATIONAL,
        priority: int | Priority = Priority.NORMAL,
        input_data: dict[str, Any] | None = None,
        constraints: list[str] | None = None,
        objectives: list[str] | None = None,
        tags: list[str] | None = None,
        session_id: str | None = None,
    ) -> str:
        """Submit a new decision request and return its ID.

        The decision is queued and processed asynchronously.
        """
        decision = Decision(
            title=title,
            description=description,
            type=decision_type,
            priority=int(priority),
            input_data=input_data or {},
            constraints=constraints or [],
            objectives=objectives or [],
            tags=tags or [],
        )
        decision._session_id = session_id or str(uuid.uuid4())  # type: ignore[attr-defined]

        await self._state.add_decision(decision)
        await self._events.publish(
            EventType.DECISION_CREATED,
            {"decision_id": decision.id, "title": title, "priority": decision.priority},
        )
        await self._queue.put(decision.id)
        logger.info("Decision submitted id=%s title=%r", decision.id, title)
        return decision.id

    async def get_decision(self, decision_id: str) -> Decision | None:
        """Retrieve a decision by ID."""
        return await self._state.get_decision(decision_id)

    async def list_decisions(
        self,
        state: DecisionState | None = None,
        decision_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Decision]:
        return await self._state.list_decisions(
            state=state, decision_type=decision_type, limit=limit, offset=offset
        )

    async def cancel(self, decision_id: str) -> bool:
        """Cancel a pending decision."""
        decision = await self._state.get_decision(decision_id)
        if decision is None:
            return False
        if decision.state not in (DecisionState.PENDING,):
            return False
        decision.transition(DecisionState.CANCELLED)
        await self._state.update_decision(decision)
        await self._events.publish(
            EventType.DECISION_CANCELLED, {"decision_id": decision_id}
        )
        return True

    async def wait_for_result(
        self, decision_id: str, timeout: float = 300.0
    ) -> Decision:
        """Poll until the decision reaches a terminal state or timeout.

        Returns the Decision. Check ``decision.state`` for COMPLETED/FAILED.
        """
        terminal = {DecisionState.COMPLETED, DecisionState.FAILED, DecisionState.CANCELLED}
        end_time = asyncio.get_event_loop().time() + timeout
        while True:
            decision = await self._state.get_decision(decision_id)
            if decision is None:
                raise KeyError(f"Decision {decision_id!r} not found")
            if decision.state in terminal:
                return decision
            remaining = end_time - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise TimeoutError(f"Decision {decision_id!r} did not complete within {timeout}s")
            await asyncio.sleep(min(0.5, remaining))

    # ------------------------------------------------------------------
    # Event subscriptions
    # ------------------------------------------------------------------

    @property
    def events(self) -> EventBus:
        return self._events

    @property
    def router(self) -> DecisionRouter:
        return self._router

    @property
    def state_manager(self) -> StateManager:
        return self._state

    # ------------------------------------------------------------------
    # Internal worker
    # ------------------------------------------------------------------

    async def _worker_loop(self) -> None:
        """Background loop that dequeues and processes decisions."""
        logger.debug("Worker loop started")
        while self._running:
            try:
                decision_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                asyncio.create_task(self._process_decision(decision_id))
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Worker loop encountered an unexpected error")

    async def _process_decision(self, decision_id: str) -> None:
        """Full processing pipeline for a single decision."""
        async with self._semaphore:
            decision = await self._state.get_decision(decision_id)
            if decision is None:
                logger.warning("Decision %s not found in state", decision_id)
                return
            if decision.state != DecisionState.PENDING:
                # Cancelled or already processed
                return
            await self._run_reasoning(decision)

    async def _run_reasoning(self, decision: Decision) -> None:
        decision.transition(DecisionState.REASONING)
        await self._state.update_decision(decision)
        await self._events.publish(
            EventType.DECISION_REASONING_STARTED,
            {"decision_id": decision.id, "title": decision.title},
        )

        try:
            session_id = getattr(decision, "_session_id", None)
            context = await self._state.get_or_create_context(decision, session_id)
            result = await self._reasoner.reason(decision, context)
            await self._state.save_context(context)

            decision.result = result
            decision.transition(DecisionState.DECIDED)
            await self._state.update_decision(decision)
            await self._events.publish(
                EventType.DECISION_REASONING_COMPLETED,
                {
                    "decision_id": decision.id,
                    "action": result.action,
                    "confidence": result.confidence,
                },
            )

            if self._auto_execute:
                await self._route_decision(decision)

        except Exception as exc:
            logger.exception("Reasoning failed for decision %s", decision.id)
            decision.error = str(exc)
            decision.transition(DecisionState.FAILED)
            await self._state.update_decision(decision)
            await self._events.publish(
                EventType.DECISION_FAILED,
                {"decision_id": decision.id, "error": str(exc)},
            )

    async def _route_decision(self, decision: Decision) -> None:
        decision.transition(DecisionState.EXECUTING)
        await self._state.update_decision(decision)
        await self._events.publish(
            EventType.DECISION_EXECUTING,
            {"decision_id": decision.id, "action": decision.result.action if decision.result else ""},
        )

        try:
            await self._router.dispatch(decision)
            decision.transition(DecisionState.COMPLETED)
        except Exception as exc:
            logger.exception("Handler execution failed for decision %s", decision.id)
            decision.error = str(exc)
            decision.transition(DecisionState.FAILED)
            await self._events.publish(
                EventType.DECISION_FAILED,
                {"decision_id": decision.id, "error": str(exc)},
            )

        await self._state.update_decision(decision)
        if decision.state == DecisionState.COMPLETED:
            await self._events.publish(
                EventType.DECISION_COMPLETED,
                {"decision_id": decision.id},
            )
