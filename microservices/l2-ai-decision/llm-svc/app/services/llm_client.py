"""
UnifiedLLMClient – single async interface to OpenAI, Anthropic, and Wenxin.

Provider precedence:
  1. Provider explicitly requested in LLMChatRequest.provider
  2. Default from settings.llm_provider
  3. Automatic fallback order: openai → anthropic → wenxin

Retry logic is handled via tenacity with exponential back-off.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.models.schemas import ChatMessage, LLMChatRequest, LLMChatResponse, LLMProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry decorator factory
# ---------------------------------------------------------------------------

def _build_retry():
    return retry(
        reraise=True,
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=lambda rs: logger.warning(
            "LLM call failed (attempt %d), retrying…", rs.attempt_number
        ),
    )


# ---------------------------------------------------------------------------
# Wenxin access-token cache (module-level so it persists across requests)
# ---------------------------------------------------------------------------

_wenxin_token: Optional[str] = None
_wenxin_token_expires_at: float = 0.0


class UnifiedLLMClient:
    """Async LLM client that unifies OpenAI, Anthropic, and Wenxin."""

    def __init__(self) -> None:
        self._openai_client = None
        self._anthropic_client = None

        if settings.openai_available:
            try:
                from openai import AsyncOpenAI  # type: ignore

                self._openai_client = AsyncOpenAI(
                    api_key=settings.openai_api_key,
                    timeout=settings.request_timeout,
                )
                logger.info("OpenAI client initialised (model=%s)", settings.openai_model)
            except ImportError:
                logger.warning("openai package not installed – OpenAI provider unavailable")

        if settings.anthropic_available:
            try:
                import anthropic  # type: ignore

                self._anthropic_client = anthropic.AsyncAnthropic(
                    api_key=settings.anthropic_api_key,
                    timeout=settings.request_timeout,
                )
                logger.info(
                    "Anthropic client initialised (model=%s)", settings.anthropic_model
                )
            except ImportError:
                logger.warning(
                    "anthropic package not installed – Anthropic provider unavailable"
                )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chat(self, request: LLMChatRequest) -> LLMChatResponse:
        """
        Route the request to the appropriate provider with automatic
        fallback if the primary provider fails.
        """
        primary = (
            request.provider.value if request.provider else settings.llm_provider
        )
        fallback_order = self._build_fallback_order(primary)

        last_error: Optional[Exception] = None
        for provider_name in fallback_order:
            try:
                return await self._dispatch(provider_name, request)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Provider '%s' failed: %s – trying next provider",
                    provider_name,
                    exc,
                )
                last_error = exc

        raise RuntimeError(
            f"All LLM providers failed. Last error: {last_error}"
        ) from last_error

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    async def _dispatch(
        self, provider: str, request: LLMChatRequest
    ) -> LLMChatResponse:
        start = time.monotonic()
        messages = request.messages
        max_tokens = request.max_tokens
        temperature = request.temperature

        if provider == LLMProvider.openai.value:
            content, model, usage = await self._call_openai(
                messages, max_tokens, temperature
            )
        elif provider == LLMProvider.anthropic.value:
            content, model, usage = await self._call_anthropic(
                messages, max_tokens, temperature
            )
        elif provider == LLMProvider.wenxin.value:
            content, model, usage = await self._call_wenxin(messages, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {provider!r}")

        latency_ms = (time.monotonic() - start) * 1000
        return LLMChatResponse(
            content=content,
            provider=provider,
            model=model,
            usage=usage,
            latency_ms=round(latency_ms, 2),
        )

    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------

    async def _call_openai(
        self,
        messages: List[ChatMessage],
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, str, Dict[str, Any]]:
        if not self._openai_client:
            raise RuntimeError("OpenAI client is not initialised")

        @_build_retry()
        async def _inner():
            response = await self._openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = response.choices[0].message.content or ""
            usage: Dict[str, Any] = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            return content, response.model, usage

        return await _inner()

    # ------------------------------------------------------------------
    # Anthropic
    # ------------------------------------------------------------------

    async def _call_anthropic(
        self,
        messages: List[ChatMessage],
        max_tokens: int,
        temperature: float,
    ) -> tuple[str, str, Dict[str, Any]]:
        if not self._anthropic_client:
            raise RuntimeError("Anthropic client is not initialised")

        # Separate system prompt from the conversation turns
        system_prompt = ""
        conversation: List[Dict[str, str]] = []
        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                conversation.append({"role": msg.role, "content": msg.content})

        # Determine if this is a complex request that benefits from extended
        # thinking (budget_tokens enables adaptive thinking in Claude models).
        use_thinking = max_tokens >= 1024

        @_build_retry()
        async def _inner():
            kwargs: Dict[str, Any] = dict(
                model=settings.anthropic_model,
                max_tokens=max_tokens,
                messages=conversation,
            )
            if system_prompt:
                kwargs["system"] = system_prompt
            if not (0.0 <= temperature <= 1.0):
                # Anthropic accepts 0-1; clamp silently
                kwargs["temperature"] = max(0.0, min(1.0, temperature))
            else:
                kwargs["temperature"] = temperature

            if use_thinking:
                # Enable extended thinking for complex analysis tasks.
                # budget_tokens must be < max_tokens.
                thinking_budget = min(max_tokens - 1, 8000)
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": thinking_budget,
                }
                # temperature must be 1 when thinking is enabled
                kwargs["temperature"] = 1

            response = await self._anthropic_client.messages.create(**kwargs)

            # Collect text blocks (skip thinking blocks)
            text_parts = [
                block.text
                for block in response.content
                if hasattr(block, "text")
            ]
            content = "\n".join(text_parts)

            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
            return content, response.model, usage

        return await _inner()

    # ------------------------------------------------------------------
    # Wenxin (Baidu ERNIE-Bot)
    # ------------------------------------------------------------------

    async def _call_wenxin(
        self,
        messages: List[ChatMessage],
        max_tokens: int,
    ) -> tuple[str, str, Dict[str, Any]]:
        if not settings.wenxin_available:
            raise RuntimeError("Wenxin credentials are not configured")

        access_token = await self.get_wenxin_access_token()

        # Wenxin does not support system role – prepend as first user message
        conversation: List[Dict[str, str]] = []
        system_text = ""
        for msg in messages:
            if msg.role == "system":
                system_text = msg.content
            else:
                conversation.append({"role": msg.role, "content": msg.content})

        if system_text and conversation:
            # Inject system context into the first user message
            conversation[0]["content"] = (
                f"[系统说明] {system_text}\n\n{conversation[0]['content']}"
            )

        # Wenxin requires alternating user/assistant turns starting with user
        if not conversation or conversation[0]["role"] != "user":
            conversation.insert(
                0, {"role": "user", "content": "请开始对话"}
            )

        @_build_retry()
        async def _inner():
            url = f"{settings.wenxin_model_url}?access_token={access_token}"
            payload = {
                "messages": conversation,
                "max_output_tokens": max_tokens,
            }
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            if "error_code" in data:
                raise RuntimeError(
                    f"Wenxin API error {data['error_code']}: {data.get('error_msg')}"
                )

            content = data.get("result", "")
            usage_raw = data.get("usage", {})
            usage = {
                "prompt_tokens": usage_raw.get("prompt_tokens", 0),
                "completion_tokens": usage_raw.get("completion_tokens", 0),
                "total_tokens": usage_raw.get("total_tokens", 0),
            }
            model_name = "ernie-bot-pro"
            return content, model_name, usage

        return await _inner()

    # ------------------------------------------------------------------
    # Wenxin access token
    # ------------------------------------------------------------------

    async def get_wenxin_access_token(self) -> str:
        """
        Fetch (or return cached) a Baidu OAuth2 access token.
        Tokens are valid for 30 days; we refresh 60 s before expiry.
        """
        global _wenxin_token, _wenxin_token_expires_at

        now = time.monotonic()
        if _wenxin_token and now < _wenxin_token_expires_at - 60:
            return _wenxin_token

        params = {
            "grant_type": "client_credentials",
            "client_id": settings.wenxin_api_key,
            "client_secret": settings.wenxin_secret_key,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.wenxin_token_url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if "error" in data:
            raise RuntimeError(
                f"Wenxin token error: {data['error']} – {data.get('error_description')}"
            )

        _wenxin_token = data["access_token"]
        # expires_in is in seconds; store as absolute monotonic time
        _wenxin_token_expires_at = now + int(data.get("expires_in", 2592000))
        logger.info("Wenxin access token refreshed (expires_in=%s s)", data.get("expires_in"))
        return _wenxin_token  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_fallback_order(self, primary: str) -> List[str]:
        """
        Return provider names in the order to try, starting with *primary*
        and continuing with any other configured provider.
        """
        all_providers = [p.value for p in LLMProvider]
        available = [
            p
            for p in all_providers
            if self._provider_is_available(p)
        ]
        # Put primary first
        if primary in available:
            available.remove(primary)
            return [primary] + available
        return available or [primary]

    def _provider_is_available(self, provider: str) -> bool:
        if provider == LLMProvider.openai.value:
            return self._openai_client is not None
        if provider == LLMProvider.anthropic.value:
            return self._anthropic_client is not None
        if provider == LLMProvider.wenxin.value:
            return settings.wenxin_available
        return False

    def get_provider_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Return availability and model info for each provider."""
        return {
            LLMProvider.openai.value: {
                "available": self._openai_client is not None,
                "model": settings.openai_model,
                "api_key_configured": settings.openai_available,
            },
            LLMProvider.anthropic.value: {
                "available": self._anthropic_client is not None,
                "model": settings.anthropic_model,
                "api_key_configured": settings.anthropic_available,
            },
            LLMProvider.wenxin.value: {
                "available": settings.wenxin_available,
                "model": "ernie-bot-pro",
                "api_key_configured": settings.wenxin_available,
            },
        }


# Module-level singleton – instantiated once at import time so that
# API clients are reused across all requests.
llm_client = UnifiedLLMClient()
