import pytest

@pytest.mark.asyncio
async def test_track_single_event(client):
    payload = {
        "event_type": "REPORT_VIEW",
        "user_id": "usr-001",
        "session_id": "sess-001",
        "channel": "APP",
        "report_id": "rpt-001",
    }
    resp = await client.post("/api/v1/track/event", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert "event_id" in data
    assert data["status"] == "ACCEPTED"

@pytest.mark.asyncio
async def test_track_batch_events(client):
    events = [
        {"event_type": "CLICK", "user_id": f"usr-{i}", "session_id": f"sess-{i}", "channel": "WEB"}
        for i in range(5)
    ]
    resp = await client.post("/api/v1/track/batch", json={"events": events})
    assert resp.status_code == 202
    assert resp.json()["total"] == 5

@pytest.mark.asyncio
async def test_track_empty_batch_rejected(client):
    resp = await client.post("/api/v1/track/batch", json={"events": []})
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_get_funnel_empty(client):
    resp = await client.get("/api/v1/track/funnel/rpt-nonexistent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["view_count"] == 0
    assert data["conversion_rate"] == 0.0

@pytest.mark.asyncio
async def test_conversion_funnel_tracking(client):
    # Track report view
    await client.post("/api/v1/track/event", json={
        "event_type": "REPORT_VIEW",
        "user_id": "usr-funnel",
        "session_id": "sess-funnel",
        "channel": "WEB",
        "report_id": "rpt-funnel",
    })
    # Track conversion
    await client.post("/api/v1/track/event", json={
        "event_type": "CONVERSION",
        "user_id": "usr-funnel",
        "session_id": "sess-funnel",
        "channel": "WEB",
        "report_id": "rpt-funnel",
    })
    resp = await client.get("/api/v1/track/funnel/rpt-funnel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["view_count"] >= 1

@pytest.mark.asyncio
async def test_health_liveness(client):
    resp = await client.get("/health/liveness")
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_get_metrics(client):
    resp = await client.get("/api/v1/track/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_sessions" in data
