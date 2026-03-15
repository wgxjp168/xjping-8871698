"""Decision context models — carries history and environment state."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ContextEntry(BaseModel):
    """A single entry in the decision context history."""
    role: str = Field(description="'system', 'user', or 'assistant'")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionContext(BaseModel):
    """Carries all context needed to reason about a decision.

    This is passed to the AI reasoning engine and updated with the result.
    """
    session_id: str = Field(description="Session identifier for multi-turn reasoning")
    decision_id: str = Field(description="Associated decision ID")
    history: list[ContextEntry] = Field(
        default_factory=list,
        description="Conversation history for multi-turn reasoning",
    )
    environment: dict[str, Any] = Field(
        default_factory=dict,
        description="Current environment / system state snapshot",
    )
    knowledge_base: list[str] = Field(
        default_factory=list,
        description="Relevant facts or rules loaded for this decision",
    )
    max_history: int = Field(
        default=20,
        description="Maximum number of history entries to retain",
    )

    def add_entry(self, role: str, content: str, **metadata: Any) -> None:
        """Append an entry and trim to max_history."""
        self.history.append(
            ContextEntry(role=role, content=content, metadata=metadata)
        )
        if len(self.history) > self.max_history:
            # Keep the first system entry if present, trim oldest non-system entries
            system_entries = [e for e in self.history if e.role == "system"]
            other_entries = [e for e in self.history if e.role != "system"]
            trimmed = other_entries[-(self.max_history - len(system_entries)):]
            self.history = system_entries + trimmed

    def to_messages(self) -> list[dict[str, str]]:
        """Convert history to Claude API message format."""
        return [
            {"role": entry.role if entry.role != "system" else "user", "content": entry.content}
            for entry in self.history
            if entry.role in ("user", "assistant")
        ]
