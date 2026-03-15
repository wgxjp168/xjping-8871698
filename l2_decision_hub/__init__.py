"""
L2-AI 决策中枢（核心层）
L2 AI Decision Hub — Core Layer

This package provides the core decision-making engine for the L2 AI Decision Hub.
It uses Claude (claude-opus-4-6) with adaptive thinking to analyze inputs,
reason about decisions, and route them to appropriate handlers.

Architecture:
  - models/    : Pydantic data models (Decision, Context, Priority)
  - ai/        : Claude API client and reasoning modules
  - core/      : Decision engine, state manager, event bus
  - handlers/  : Handler base class and registry
  - api/       : FastAPI REST layer
"""

__version__ = "0.1.0"
__all__ = ["DecisionHub"]

from l2_decision_hub.core.engine import DecisionHub
