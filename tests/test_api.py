"""Tests for the FastAPI REST layer."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport

from l2_decision_hub.api.app import create_app
from l2_decision_hub.api.routes import set_hub
from l2_decision_hub.core.engine import DecisionHub
from l2_decision_hub.models.decision import DecisionResult, DecisionState


def make_hub() -> DecisionHub:
    h = DecisionHub(api_key="test-key")
    h._reasoner.reason = AsyncMock(
        return_value=DecisionResult(
            action="Do it",
            reasoning="Makes sense",
            confidence=0.9,
        )
    )
    return h


@pytest.fixture
async def client():
    hub = make_hub()
    # Start the hub and inject it before creating the app
    await hub.start()
    set_hub(hub)
    app = create_app(hub=hub)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    await hub.stop()


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_submit_decision(client):
    payload = {
        "title": "Cloud migration",
        "description": "Should we move to the cloud?",
        "priority": 3,
        "decision_type": "strategic",
    }
    r = await client.post("/api/v1/decisions", json=payload)
    assert r.status_code == 202
    data = r.json()
    assert "decision_id" in data


@pytest.mark.asyncio
async def test_get_decision(client):
    payload = {"title": "T", "description": "D"}
    post = await client.post("/api/v1/decisions", json=payload)
    decision_id = post.json()["decision_id"]

    r = await client.get(f"/api/v1/decisions/{decision_id}")
    assert r.status_code == 200
    assert r.json()["id"] == decision_id


@pytest.mark.asyncio
async def test_get_decision_not_found(client):
    r = await client.get("/api/v1/decisions/nonexistent-id")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_decisions(client):
    for i in range(3):
        await client.post("/api/v1/decisions", json={"title": f"D{i}", "description": "x"})

    r = await client.get("/api/v1/decisions")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 3
    assert isinstance(data["decisions"], list)


@pytest.mark.asyncio
async def test_hub_status(client):
    r = await client.get("/api/v1/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "running"
    assert "total_decisions" in data


@pytest.mark.asyncio
async def test_cancel_decision(client):
    post = await client.post("/api/v1/decisions", json={"title": "T", "description": "D"})
    decision_id = post.json()["decision_id"]

    # Cancel immediately (decision should still be pending)
    r = await client.delete(f"/api/v1/decisions/{decision_id}")
    # 204 if cancelled, 409 if already processed
    assert r.status_code in (204, 409)
