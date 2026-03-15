"""
UnifiedLLMClient – single async interface to OpenAI, Anthropic, and Wenxin.

Provider precedence:
  1. Provider explicitly requested in LLMChatRequest.provider
  2. Default from settings.llm_provider
  3. Automatic fallback order: openai → anthropic → wenxin

Key features:
  - Adaptive thinking for claude-opus-4-6 / claude-sonnet-4-6 (replaces
    deprecated budget_tokens / extended-thinking).
  - Thinking traces returned in LLMChatResponse.thinking.
  - analyze_structured() enforces JSON Schema via output_config (Anthropic)
    or prompt-augmented parsing (other providers).
  - stream_chat() yields text tokens via AsyncIterator.
  - Wenxin OAuth2 token with 30-day expiry + 60 s pre-expiry refresh.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

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

# Models that support adaptive thinking (must NOT use budget_tokens).
_ADAPTIVE_THINKING_MODELS = frozenset({
    "claude-opus-4-6",
    "claude-sonnet-4-6",
})

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
        """Route request to the appropriate provider with automatic fallback."""
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

    async def analyze_structured(
        self,
        request: LLMChatRequest,
        json_schema: Dict[str, Any],
    ) -> Tuple[Any, LLMChatResponse]:
        """
        Call the LLM and enforce a JSON Schema on the response.

        - Anthropic (claude-opus-4-6/sonnet-4-6): uses output_config with
          json_schema format for guaranteed valid JSON.
        - Other providers: prompt-based JSON enforcement + post-call parsing.

        Returns:
            (parsed_object, raw_llm_response)
        """
        provider = (
            request.provider.value if request.provider else settings.llm_provider
        )
        start = time.monotonic()

        if provider == LLMProvider.anthropic.value and self._anthropic_client:
            content, thinking, model, usage = await self._call_anthropic_structured(
                messages=request.messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                json_schema=json_schema,
                enable_thinking=request.enable_thinking,
            )
        else:
            # Fallback: augment last user message with schema hint
            augmented_messages = list(request.messages)
            schema_hint = (
                "\n\n请严格按照以下JSON Schema格式输出，不要包含任何额外文字：\n"
                + json.dumps(json_schema, ensure_ascii=False, indent=2)
            )
            if augmented_messages and augmented_messages[-1].role == "user":
                last = augmented_messages[-1]
                augmented_messages[-1] = ChatMessage(
                    role="user", content=last.content + schema_hint
                )
            augmented_req = request.model_copy(update={"messages": augmented_messages})
            resp = await self.chat(augmented_req)
            content, thinking, model, usage = (
                resp.content, resp.thinking, resp.model, resp.usage
            )

        latency_ms = round((time.monotonic() - start) * 1000, 2)
        resp = LLMChatResponse(
            content=content,
            thinking=thinking,
            provider=provider,
            model=model,
            usage=usage,
            latency_ms=latency_ms,
        )

        # Parse JSON from response
        raw = content.strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if match:
                parsed = json.loads(match.group(1))
            else:
                raise ValueError(f"LLM response is not valid JSON: {raw[:200]}")

        return parsed, resp

    async def stream_chat(self, request: LLMChatRequest) -> AsyncIterator[str]:
        """
        Stream text tokens. Anthropic yields real deltas; other providers
        yield the full content as a single chunk.
        """
        provider = (
            request.provider.value if request.provider else settings.llm_provider
        )
        if provider == LLMProvider.anthropic.value and self._anthropic_client:
            async for token in self._stream_anthropic(request):
                yield token
        else:
            resp = await self.chat(request)
            yield resp.content

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    async def _dispatch(self, provider: str, request: LLMChatRequest) -> LLMChatResponse:
        start = time.monotonic()
        thinking: Optional[str] = None

        if provider == LLMProvider.openai.value:
            content, model, usage = await self._call_openai(
                request.messages, request.max_tokens, request.temperature
            )
        elif provider == LLMProvider.anthropic.value:
            content, thinking, model, usage = await self._call_anthropic(
                request.messages, request.max_tokens, request.temperature,
                request.enable_thinking,
            )
        elif provider == LLMProvider.wenxin.value:
            content, model, usage = await self._call_wenxin(
                request.messages, request.max_tokens
            )
        else:
            raise ValueError(f"Unknown provider: {provider!r}")

        latency_ms = (time.monotonic() - start) * 1000
        return LLMChatResponse(
            content=content,
            thinking=thinking,
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
    ) -> Tuple[str, str, Dict[str, Any]]:
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
    # Anthropic — standard (non-streaming)
    # ------------------------------------------------------------------

    async def _call_anthropic(
        self,
        messages: List[ChatMessage],
        max_tokens: int,
        temperature: float,
        enable_thinking: bool = False,
    ) -> Tuple[str, Optional[str], str, Dict[str, Any]]:
        if not self._anthropic_client:
            raise RuntimeError("Anthropic client is not initialised")

        system_prompt, conversation = self._split_system(messages)
        use_adaptive = enable_thinking and self._supports_adaptive_thinking()

        @_build_retry()
        async def _inner():
            kwargs: Dict[str, Any] = dict(
                model=settings.anthropic_model,
                max_tokens=max_tokens,
                messages=conversation,
            )
            if system_prompt:
                kwargs["system"] = system_prompt

            if use_adaptive:
                # Adaptive thinking for claude-opus-4-6 / claude-sonnet-4-6.
                # temperature MUST NOT be set when adaptive thinking is enabled.
                kwargs["thinking"] = {"type": "adaptive"}
            else:
                kwargs["temperature"] = max(0.0, min(1.0, temperature))

            response = await self._anthropic_client.messages.create(**kwargs)

            text_parts: List[str] = []
            thinking_parts: List[str] = []
            for block in response.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
                elif hasattr(block, "thinking"):
                    thinking_parts.append(block.thinking)

            content = "\n".join(text_parts)
            thinking = "\n".join(thinking_parts) if thinking_parts else None
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
            return content, thinking, response.model, usage

        return await _inner()

    # ------------------------------------------------------------------
    # Anthropic — structured JSON output (output_config json_schema)
    # ------------------------------------------------------------------

    async def _call_anthropic_structured(
        self,
        messages: List[ChatMessage],
        max_tokens: int,
        temperature: float,
        json_schema: Dict[str, Any],
        enable_thinking: bool = False,
    ) -> Tuple[str, Optional[str], str, Dict[str, Any]]:
        if not self._anthropic_client:
            raise RuntimeError("Anthropic client is not initialised")

        system_prompt, conversation = self._split_system(messages)
        use_adaptive = enable_thinking and self._supports_adaptive_thinking()

        @_build_retry()
        async def _inner():
            kwargs: Dict[str, Any] = dict(
                model=settings.anthropic_model,
                max_tokens=max_tokens,
                messages=conversation,
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": json_schema,
                    }
                },
            )
            if system_prompt:
                kwargs["system"] = system_prompt
            if use_adaptive:
                kwargs["thinking"] = {"type": "adaptive"}
            else:
                kwargs["temperature"] = max(0.0, min(1.0, temperature))

            response = await self._anthropic_client.messages.create(**kwargs)

            text_parts: List[str] = []
            thinking_parts: List[str] = []
            for block in response.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
                elif hasattr(block, "thinking"):
                    thinking_parts.append(block.thinking)

            content = "\n".join(text_parts)
            thinking = "\n".join(thinking_parts) if thinking_parts else None
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
            return content, thinking, response.model, usage

        return await _inner()

    # ------------------------------------------------------------------
    # Anthropic — streaming
    # ------------------------------------------------------------------

    async def _stream_anthropic(self, request: LLMChatRequest) -> AsyncIterator[str]:
        if not self._anthropic_client:
            raise RuntimeError("Anthropic client is not initialised")

        system_prompt, conversation = self._split_system(request.messages)
        use_adaptive = request.enable_thinking and self._supports_adaptive_thinking()

        kwargs: Dict[str, Any] = dict(
            model=settings.anthropic_model,
            max_tokens=request.max_tokens,
            messages=conversation,
        )
        if system_prompt:
            kwargs["system"] = system_prompt
        if use_adaptive:
            kwargs["thinking"] = {"type": "adaptive"}
        else:
            kwargs["temperature"] = max(0.0, min(1.0, request.temperature))

        async with self._anthropic_client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    # ------------------------------------------------------------------
    # Wenxin (Baidu ERNIE-Bot)
    # ------------------------------------------------------------------

    async def _call_wenxin(
        self,
        messages: List[ChatMessage],
        max_tokens: int,
    ) -> Tuple[str, str, Dict[str, Any]]:
        if not settings.wenxin_available:
            raise RuntimeError("Wenxin credentials are not configured")

        access_token = await self.get_wenxin_access_token()

        conversation: List[Dict[str, str]] = []
        system_text = ""
        for msg in messages:
            if msg.role == "system":
                system_text = msg.content
            else:
                conversation.append({"role": msg.role, "content": msg.content})

        if system_text and conversation:
            conversation[0]["content"] = (
                f"[系统说明] {system_text}\n\n{conversation[0]['content']}"
            )

        if not conversation or conversation[0]["role"] != "user":
            conversation.insert(0, {"role": "user", "content": "请开始对话"})

        @_build_retry()
        async def _inner():
            url = f"{settings.wenxin_model_url}?access_token={access_token}"
            payload = {"messages": conversation, "max_output_tokens": max_tokens}
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
            return content, "ernie-bot-pro", usage

        return await _inner()

    # ------------------------------------------------------------------
    # Wenxin access token
    # ------------------------------------------------------------------

    async def get_wenxin_access_token(self) -> str:
        """Return a cached Baidu OAuth2 access token, refreshing if near expiry."""
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
        _wenxin_token_expires_at = now + int(data.get("expires_in", 2592000))
        logger.info("Wenxin access token refreshed (expires_in=%s s)", data.get("expires_in"))
        return _wenxin_token  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _supports_adaptive_thinking(self) -> bool:
        """True when the configured Anthropic model supports adaptive thinking."""
        return settings.anthropic_model in _ADAPTIVE_THINKING_MODELS

    @staticmethod
    def _split_system(
        messages: List[ChatMessage],
    ) -> Tuple[str, List[Dict[str, str]]]:
        """Separate system prompt from conversation turns for Anthropic API."""
        system_prompt = ""
        conversation: List[Dict[str, str]] = []
        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                conversation.append({"role": msg.role, "content": msg.content})
        return system_prompt, conversation

    def _build_fallback_order(self, primary: str) -> List[str]:
        all_providers = [p.value for p in LLMProvider]
        available = [p for p in all_providers if self._provider_is_available(p)]
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
        return {
            LLMProvider.openai.value: {
                "available": self._openai_client is not None,
                "model": settings.openai_model,
                "api_key_configured": settings.openai_available,
                "supports_thinking": False,
            },
            LLMProvider.anthropic.value: {
                "available": self._anthropic_client is not None,
                "model": settings.anthropic_model,
                "api_key_configured": settings.anthropic_available,
                "supports_thinking": (
                    self._anthropic_client is not None
                    and self._supports_adaptive_thinking()
                ),
            },
            LLMProvider.wenxin.value: {
                "available": settings.wenxin_available,
                "model": "ernie-bot-pro",
                "api_key_configured": settings.wenxin_available,
                "supports_thinking": False,
            },
        }


# Module-level singleton – instantiated once at import time.
llm_client = UnifiedLLMClient()
