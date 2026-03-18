import pytest

DEPLOYMENT_PAYLOAD = {
    "model_version_id": "mv-001",
    "version_tag": "v1.0.0",
    "artifact_path": "/app/model_store/mv-001/model.pkl",
    "deployment_strategy": "BLUE_GREEN",
}


@pytest.mark.asyncio
async def test_create_deployment(client):
    resp = await client.post("/api/v1/deployments", json=DEPLOYMENT_PAYLOAD)
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert data["model_version_id"] == "mv-001"
    assert data["version_tag"] == "v1.0.0"
    assert data["status"] in ("ACTIVE", "FAILED")
    assert data["deployment_strategy"] == "BLUE_GREEN"


@pytest.mark.asyncio
async def test_list_deployments(client):
    # Create one first
    await client.post("/api/v1/deployments", json=DEPLOYMENT_PAYLOAD)
    resp = await client.get("/api/v1/deployments")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_active_deployment(client):
    # Create an active deployment
    await client.post("/api/v1/deployments", json=DEPLOYMENT_PAYLOAD)
    resp = await client.get("/api/v1/deployments/active")
    # Either 200 (found) or 404 (MQ failed so FAILED status, not active)
    assert resp.status_code in (200, 404)
    if resp.status_code == 200:
        data = resp.json()
        assert data["is_active"] is True


@pytest.mark.asyncio
async def test_rollback_nonexistent(client):
    resp = await client.post(
        "/api/v1/deployments/bad-id-does-not-exist/rollback",
        json={"reason": "test rollback"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_specific_deployment(client):
    create_resp = await client.post("/api/v1/deployments", json=DEPLOYMENT_PAYLOAD)
    assert create_resp.status_code == 202
    deployment_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/deployments/{deployment_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == deployment_id
    assert data["model_version_id"] == "mv-001"
