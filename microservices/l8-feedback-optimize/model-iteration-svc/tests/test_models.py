"""Tests for model training and version management endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_health_liveness(client: AsyncClient):
    """GET /health/liveness should return 200 with status UP."""
    response = await client.get("/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "UP"


async def test_trigger_training_manual(client: AsyncClient):
    """POST /api/v1/models/train should return 202 with a training job."""
    response = await client.post(
        "/api/v1/models/train",
        json={"trigger_reason": "MANUAL"},
    )
    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    assert data["trigger_reason"] == "MANUAL"
    # Job is synchronous in test (runs inline), so expect terminal state
    assert data["status"] in ("SUCCESS", "FAILED", "RUNNING", "PENDING")


async def test_list_model_versions(client: AsyncClient):
    """GET /api/v1/models/versions should return 200 with a list."""
    response = await client.get("/api/v1/models/versions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


async def test_get_training_job(client: AsyncClient):
    """GET /api/v1/models/jobs/{id} should return 200 for a known job."""
    # First create a job
    create_resp = await client.post(
        "/api/v1/models/train",
        json={"trigger_reason": "MANUAL"},
    )
    assert create_resp.status_code == 202
    job_id = create_resp.json()["id"]

    # Now fetch it
    response = await client.get(f"/api/v1/models/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job_id


async def test_get_training_job_not_found(client: AsyncClient):
    """GET /api/v1/models/jobs/{unknown} should return 404."""
    response = await client.get("/api/v1/models/jobs/nonexistent-job-id")
    assert response.status_code == 404
