import pytest


@pytest.mark.asyncio
async def test_liveness(client):
    resp = await client.get("/health/liveness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness(client):
    resp = await client.get("/health/readiness")
    # 200 when DB is available (SQLite in-memory), 503 if not
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "status" in data
