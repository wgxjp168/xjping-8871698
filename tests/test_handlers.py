"""Tests for handler registry and base handler."""

import pytest

from l2_decision_hub.handlers.base import BaseHandler, HandlerResult, LoggingHandler
from l2_decision_hub.handlers.registry import HandlerRegistry
from l2_decision_hub.models.decision import Decision, DecisionResult, DecisionType


class EchoHandler(BaseHandler):
    name = "echo"
    supported_types = [DecisionType.OPERATIONAL]

    async def handle(self, decision: Decision) -> HandlerResult:
        return HandlerResult(success=True, message="echo", output={"id": decision.id})


class FailHandler(BaseHandler):
    name = "fail"
    supported_types = [DecisionType.RISK]

    async def handle(self, decision: Decision) -> HandlerResult:
        return HandlerResult(success=False, message="intentional failure")


def make_decision(dtype: DecisionType = DecisionType.OPERATIONAL, priority: int = 2) -> Decision:
    d = Decision(title="T", description="D", type=dtype, priority=priority)
    d.result = DecisionResult(action="do it", reasoning="because", confidence=0.8)
    return d


@pytest.mark.asyncio
async def test_echo_handler():
    d = make_decision()
    h = EchoHandler()
    result = await h.handle(d)
    assert result.success is True
    assert result.message == "echo"


def test_can_handle_type_filter():
    h = EchoHandler()
    assert h.can_handle(make_decision(DecisionType.OPERATIONAL))
    assert not h.can_handle(make_decision(DecisionType.STRATEGIC))


def test_can_handle_priority_filter():
    h = EchoHandler()
    h.min_priority = 3
    assert h.can_handle(make_decision(priority=3))
    assert not h.can_handle(make_decision(priority=2))


def test_registry_selects_specific_handler():
    reg = HandlerRegistry()
    reg.register(EchoHandler())
    handler = reg.select(make_decision(DecisionType.OPERATIONAL))
    assert handler.name == "echo"


def test_registry_fallback_to_logging():
    reg = HandlerRegistry()
    reg.register(EchoHandler())  # only handles OPERATIONAL
    handler = reg.select(make_decision(DecisionType.STRATEGIC))
    assert handler.name == "logging"


def test_registry_unregister():
    reg = HandlerRegistry()
    reg.register(EchoHandler())
    removed = reg.unregister("echo")
    assert removed is True
    assert len(reg._handlers) == 0


@pytest.mark.asyncio
async def test_logging_handler():
    d = make_decision()
    h = LoggingHandler()
    result = await h.handle(d)
    assert result.success is True
