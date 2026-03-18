"""Tests for A/B experiment management endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EXPERIMENT_PAYLOAD = {
    "name": "Test Experiment Alpha",
    "description": "A/B test between control and variant model",
    "experiment_type": "MODEL_AB",
    "traffic_percentage": 50.0,
    "target_metric": "conversion_rate",
}


async def test_create_experiment(client: AsyncClient):
    """POST /api/v1/experiments should return 201 with the created experiment."""
    response = await client.post("/api/v1/experiments", json=EXPERIMENT_PAYLOAD)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == EXPERIMENT_PAYLOAD["name"]
    assert data["status"] == "DRAFT"
    assert "id" in data


async def test_start_experiment(client: AsyncClient):
    """POST /api/v1/experiments/{id}/start should move status to RUNNING."""
    # Create first
    create_resp = await client.post("/api/v1/experiments", json=EXPERIMENT_PAYLOAD)
    assert create_resp.status_code == 201
    exp_id = create_resp.json()["id"]

    # Start
    response = await client.post(f"/api/v1/experiments/{exp_id}/start")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RUNNING"
    assert data["id"] == exp_id


async def test_list_experiments(client: AsyncClient):
    """GET /api/v1/experiments should return 200 with a list."""
    response = await client.get("/api/v1/experiments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


async def test_complete_experiment_inconclusive(client: AsyncClient):
    """POST /api/v1/experiments/{id}/complete should return 200.

    With zero observations the winner should be INCONCLUSIVE.
    """
    # Create and start
    create_resp = await client.post("/api/v1/experiments", json=EXPERIMENT_PAYLOAD)
    assert create_resp.status_code == 201
    exp_id = create_resp.json()["id"]

    await client.post(f"/api/v1/experiments/{exp_id}/start")

    # Complete without any recorded outcomes → INCONCLUSIVE
    response = await client.post(f"/api/v1/experiments/{exp_id}/complete")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["winner"] == "INCONCLUSIVE"


async def test_get_experiment_results(client: AsyncClient):
    """GET /api/v1/experiments/{id}/results should return analysis dict."""
    create_resp = await client.post("/api/v1/experiments", json=EXPERIMENT_PAYLOAD)
    assert create_resp.status_code == 201
    exp_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/experiments/{exp_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["experiment_id"] == exp_id
    assert "winner" in data
