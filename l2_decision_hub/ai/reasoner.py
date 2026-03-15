"""Decision reasoning module — orchestrates Claude to produce DecisionResult."""

from __future__ import annotations

import json
import logging
from typing import Any

from l2_decision_hub.ai.client import ClaudeClient
from l2_decision_hub.ai.prompts import SYSTEM_PROMPT, build_decision_prompt
from l2_decision_hub.models.context import DecisionContext
from l2_decision_hub.models.decision import Decision, DecisionResult

logger = logging.getLogger(__name__)


class DecisionReasoner:
    """Wraps ClaudeClient to reason about Decision objects."""

    def __init__(self, client: ClaudeClient) -> None:
        self._client = client

    async def reason(
        self, decision: Decision, context: DecisionContext
    ) -> DecisionResult:
        """Produce a DecisionResult by reasoning with Claude.

        Args:
            decision: The decision to reason about.
            context: Contextual information (environment, history, KB).

        Returns:
            A validated DecisionResult.
        """
        prompt = build_decision_prompt(
            title=decision.title,
            decision_type=decision.type.value,
            priority=decision.priority,
            description=decision.description,
            input_data=json.dumps(decision.input_data, indent=2, ensure_ascii=False),
            constraints=decision.constraints,
            objectives=decision.objectives,
            environment=json.dumps(context.environment, indent=2, ensure_ascii=False),
            knowledge_base=context.knowledge_base,
        )

        # Build message list: existing context history + new decision request
        messages = context.to_messages() + [{"role": "user", "content": prompt}]

        logger.info(
            "Reasoning for decision id=%s type=%s priority=%d",
            decision.id,
            decision.type.value,
            decision.priority,
        )

        raw = await self._client.extract_json_async(SYSTEM_PROMPT, messages)

        result = self._parse_result(raw)

        # Update context with this exchange
        context.add_entry("user", prompt)
        context.add_entry(
            "assistant",
            json.dumps(raw, ensure_ascii=False),
            decision_id=decision.id,
        )

        return result

    # ------------------------------------------------------------------

    @staticmethod
    def _parse_result(raw: dict[str, Any]) -> DecisionResult:
        """Convert the raw JSON dict into a validated DecisionResult."""
        # Clamp confidence to [0, 1]
        confidence = float(raw.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        return DecisionResult(
            action=str(raw.get("action", "No action specified")),
            reasoning=str(raw.get("reasoning", "")),
            confidence=confidence,
            alternatives=list(raw.get("alternatives", [])),
            parameters=dict(raw.get("parameters", {})),
            metadata=dict(raw.get("metadata", {})),
        )
