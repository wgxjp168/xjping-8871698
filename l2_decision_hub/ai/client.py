"""Claude API client wrapper for the L2 Decision Hub."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-opus-4-6"
_DEFAULT_MAX_TOKENS = 8192


class ClaudeClient:
    """Thin async-friendly wrapper around the Anthropic SDK.

    Uses adaptive thinking (claude-opus-4-6) for all decision reasoning.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = _DEFAULT_MODEL,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model
        self.max_tokens = max_tokens
        self._client = anthropic.Anthropic(api_key=self._api_key)
        self._async_client = anthropic.AsyncAnthropic(api_key=self._api_key)

    # ------------------------------------------------------------------
    # Async interface (preferred)
    # ------------------------------------------------------------------

    async def reason_async(
        self,
        system: str,
        messages: list[dict[str, str]],
        extra_params: dict[str, Any] | None = None,
    ) -> tuple[str, str | None]:
        """Send a reasoning request and return (text_response, thinking_text).

        Uses adaptive thinking for best results on complex decisions.
        """
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "thinking": {"type": "adaptive"},
            "system": system,
            "messages": messages,
        }
        if extra_params:
            params.update(extra_params)

        response = await self._async_client.messages.create(**params)

        text = ""
        thinking = ""
        for block in response.content:
            if block.type == "thinking":
                thinking = block.thinking
            elif block.type == "text":
                text = block.text

        logger.debug(
            "Claude response: tokens_in=%d tokens_out=%d",
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return text, thinking or None

    async def extract_json_async(
        self,
        system: str,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Reason and parse the JSON response, retrying once on parse failure."""
        text, _ = await self.reason_async(system, messages)
        try:
            return self._parse_json(text)
        except ValueError:
            # Retry with an explicit reminder to emit only JSON
            retry_messages = messages + [
                {"role": "assistant", "content": text},
                {
                    "role": "user",
                    "content": (
                        "Your previous response could not be parsed as JSON. "
                        "Please respond with ONLY the JSON object, no markdown fences, "
                        "no additional text."
                    ),
                },
            ]
            text2, _ = await self.reason_async(system, retry_messages)
            return self._parse_json(text2)

    # ------------------------------------------------------------------
    # Sync interface (for simple use / testing)
    # ------------------------------------------------------------------

    def reason(
        self,
        system: str,
        messages: list[dict[str, str]],
        extra_params: dict[str, Any] | None = None,
    ) -> tuple[str, str | None]:
        """Synchronous version of reason_async."""
        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "thinking": {"type": "adaptive"},
            "system": system,
            "messages": messages,
        }
        if extra_params:
            params.update(extra_params)

        response = self._client.messages.create(**params)

        text = ""
        thinking = ""
        for block in response.content:
            if block.type == "thinking":
                thinking = block.thinking
            elif block.type == "text":
                text = block.text

        return text, thinking or None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """Extract and parse a JSON object from raw model output."""
        text = text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.splitlines()
            # drop first and last fence line
            inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            text = "\n".join(inner).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            # Try to find a JSON object within the text
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse JSON from model output: {text[:200]}") from exc
