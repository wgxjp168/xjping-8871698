"""Tests for data models."""

import pytest
from datetime import datetime

from l2_decision_hub.models.decision import (
    Decision,
    DecisionState,
    DecisionType,
    DecisionResult,
)
from l2_decision_hub.models.context import DecisionContext, ContextEntry
from l2_decision_hub.models.priority import Priority


class TestPriority:
    def test_values(self):
        assert Priority.LOW < Priority.NORMAL < Priority.HIGH < Priority.CRITICAL < Priority.EMERGENCY

    def test_from_string(self):
        assert Priority.from_string("high") == Priority.HIGH
        assert Priority.from_string("EMERGENCY") == Priority.EMERGENCY
        assert Priority.from_string("unknown") == Priority.NORMAL


class TestDecision:
    def test_defaults(self):
        d = Decision(title="Test", description="A test decision")
        assert d.state == DecisionState.PENDING
        assert d.type == DecisionType.OPERATIONAL
        assert d.priority == 2
        assert d.result is None
        assert d.id  # uuid generated

    def test_transition(self):
        d = Decision(title="T", description="D")
        d.transition(DecisionState.REASONING)
        assert d.state == DecisionState.REASONING
        assert d.completed_at is None

        d.transition(DecisionState.COMPLETED)
        assert d.state == DecisionState.COMPLETED
        assert d.completed_at is not None

    def test_constraints_and_objectives(self):
        d = Decision(
            title="T",
            description="D",
            constraints=["No downtime"],
            objectives=["Minimise cost"],
        )
        assert "No downtime" in d.constraints
        assert "Minimise cost" in d.objectives


class TestDecisionResult:
    def test_confidence_bounds(self):
        r = DecisionResult(
            action="Do X",
            reasoning="Because Y",
            confidence=0.85,
        )
        assert r.confidence == 0.85

    def test_full_result(self):
        r = DecisionResult(
            action="Migrate to AWS",
            reasoning="Cost and scalability benefits",
            confidence=0.9,
            alternatives=[{"action": "GCP", "pros": ["ML"], "cons": ["Cost"]}],
            parameters={"timeline_months": 12},
            metadata={"risk_level": "medium"},
        )
        assert r.alternatives[0]["action"] == "GCP"
        assert r.parameters["timeline_months"] == 12


class TestDecisionContext:
    def test_add_entry(self):
        ctx = DecisionContext(session_id="s1", decision_id="d1")
        ctx.add_entry("user", "Hello")
        assert len(ctx.history) == 1
        assert ctx.history[0].role == "user"

    def test_max_history_trim(self):
        ctx = DecisionContext(session_id="s1", decision_id="d1", max_history=5)
        for i in range(10):
            ctx.add_entry("user" if i % 2 == 0 else "assistant", f"Message {i}")
        assert len(ctx.history) <= 5

    def test_to_messages(self):
        ctx = DecisionContext(session_id="s1", decision_id="d1")
        ctx.add_entry("user", "What should I do?")
        ctx.add_entry("assistant", "Do X")
        messages = ctx.to_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_system_entries_not_in_messages(self):
        ctx = DecisionContext(session_id="s1", decision_id="d1")
        ctx.add_entry("system", "You are helpful")
        ctx.add_entry("user", "Hello")
        messages = ctx.to_messages()
        # system entries are filtered out
        assert all(m["role"] != "system" for m in messages)
