"""Tests for ClaudeClient (with mocked Anthropic SDK)."""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from l2_decision_hub.ai.client import ClaudeClient


def make_mock_response(text: str, thinking: str = ""):
    """Build a mock Anthropic Messages response."""
    blocks = []
    if thinking:
        t_block = MagicMock()
        t_block.type = "thinking"
        t_block.thinking = thinking
        blocks.append(t_block)
    txt_block = MagicMock()
    txt_block.type = "text"
    txt_block.text = text
    blocks.append(txt_block)

    resp = MagicMock()
    resp.content = blocks
    resp.usage = MagicMock(input_tokens=100, output_tokens=50)
    return resp


@pytest.mark.asyncio
async def test_reason_async_returns_text_and_thinking():
    client = ClaudeClient(api_key="sk-test")
    mock_resp = make_mock_response("Hello world", thinking="Let me think...")

    with patch.object(client._async_client.messages, "create", new=AsyncMock(return_value=mock_resp)):
        text, thinking = await client.reason_async("System", [{"role": "user", "content": "Hi"}])

    assert text == "Hello world"
    assert thinking == "Let me think..."


@pytest.mark.asyncio
async def test_extract_json_async_valid():
    client = ClaudeClient(api_key="sk-test")
    payload = {"action": "do it", "confidence": 0.9}
    mock_resp = make_mock_response(json.dumps(payload))

    with patch.object(client._async_client.messages, "create", new=AsyncMock(return_value=mock_resp)):
        result = await client.extract_json_async("System", [{"role": "user", "content": "Decide"}])

    assert result["action"] == "do it"
    assert result["confidence"] == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_extract_json_async_with_markdown_fences():
    client = ClaudeClient(api_key="sk-test")
    payload = {"action": "test"}
    fenced = f"```json\n{json.dumps(payload)}\n```"
    mock_resp = make_mock_response(fenced)

    with patch.object(client._async_client.messages, "create", new=AsyncMock(return_value=mock_resp)):
        result = await client.extract_json_async("System", [{"role": "user", "content": "Go"}])

    assert result["action"] == "test"


def test_parse_json_plain():
    data = ClaudeClient._parse_json('{"key": "value"}')
    assert data["key"] == "value"


def test_parse_json_embedded():
    text = 'Here is the result: {"key": "value"} — done.'
    data = ClaudeClient._parse_json(text)
    assert data["key"] == "value"


def test_parse_json_invalid_raises():
    with pytest.raises(ValueError):
        ClaudeClient._parse_json("not json at all!!!")
