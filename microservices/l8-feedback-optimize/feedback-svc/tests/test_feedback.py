import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_submit_feedback_success(client):
    payload = {
        "report_id": "rpt-001",
        "user_id": "usr-001",
        "channel": "WECHAT",
        "rating": 5,
        "comment": "报告非常准确，推荐使用！",
    }
    resp = await client.post("/api/v1/feedback", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["report_id"] == "rpt-001"
    assert data["rating"] == 5
    assert data["sentiment_label"] == "POSITIVE"
    assert data["sentiment_score"] is not None

@pytest.mark.asyncio
async def test_submit_feedback_negative(client):
    payload = {
        "report_id": "rpt-002",
        "user_id": "usr-002",
        "channel": "APP",
        "rating": 1,
        "comment": "报告完全错误，非常糟糕！",
    }
    resp = await client.post("/api/v1/feedback", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["sentiment_label"] == "NEGATIVE"

@pytest.mark.asyncio
async def test_submit_feedback_invalid_rating(client):
    payload = {
        "report_id": "rpt-003",
        "user_id": "usr-003",
        "channel": "WEB",
        "rating": 6,
    }
    resp = await client.post("/api/v1/feedback", json=payload)
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_get_feedback_not_found(client):
    resp = await client.get("/api/v1/feedback/nonexistent-id")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_analytics_empty(client):
    resp = await client.get("/api/v1/feedback/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 0

@pytest.mark.asyncio
async def test_analytics_with_data(client):
    for i, rating in enumerate([5, 4, 3, 2, 1], 1):
        await client.post("/api/v1/feedback", json={
            "report_id": f"rpt-{i:03d}",
            "user_id": f"usr-{i:03d}",
            "channel": "WEB",
            "rating": rating,
        })
    resp = await client.get("/api/v1/feedback/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 5
    assert data["avg_rating"] == 3.0

@pytest.mark.asyncio
async def test_health_liveness(client):
    resp = await client.get("/health/liveness")
    assert resp.status_code == 200
    assert resp.json()["status"] == "UP"
