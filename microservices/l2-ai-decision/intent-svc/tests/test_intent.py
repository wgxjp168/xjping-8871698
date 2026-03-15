"""
pytest test suite for ILbuy Intent Service.

Tests cover:
- POST /intent/recognize
- POST /entity/extract
- POST /brand/detect
- GET  /health

Run with:
    pytest tests/test_intent.py -v
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.schemas import BrandStatusEnum, IntentEnum


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Async test client backed by the FastAPI ASGI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    """GET /health should return 200 with status=ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "version" in data


# ---------------------------------------------------------------------------
# Intent Recognition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intent_recognize_purchase(client: AsyncClient) -> None:
    """'我想买一台小米手机' should resolve to PURCHASE_INQUIRY."""
    response = await client.post(
        "/intent/recognize",
        json={"text": "我想买一台小米手机"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == IntentEnum.PURCHASE_INQUIRY.value
    assert 0.0 < data["confidence"] <= 1.0
    assert isinstance(data["sub_intents"], list)


@pytest.mark.asyncio
async def test_intent_recognize_recommendation(client: AsyncClient) -> None:
    """'帮我推荐一款电视' should resolve to RECOMMENDATION."""
    response = await client.post(
        "/intent/recognize",
        json={"text": "帮我推荐一款电视"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == IntentEnum.RECOMMENDATION.value
    assert data["confidence"] > 0.0


@pytest.mark.asyncio
async def test_intent_recognize_price_query(client: AsyncClient) -> None:
    """'这款手机多少钱' should resolve to PRICE_QUERY."""
    response = await client.post(
        "/intent/recognize",
        json={"text": "这款手机多少钱"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == IntentEnum.PRICE_QUERY.value


@pytest.mark.asyncio
async def test_intent_recognize_with_session_id(client: AsyncClient) -> None:
    """session_id should be echoed back in the response."""
    response = await client.post(
        "/intent/recognize",
        json={"text": "我要退货", "session_id": "sess-abc-123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "sess-abc-123"
    assert data["intent"] == IntentEnum.RETURN.value


@pytest.mark.asyncio
async def test_intent_recognize_returns_sub_intents(client: AsyncClient) -> None:
    """Response should include up to 3 sub_intents."""
    response = await client.post(
        "/intent/recognize",
        json={"text": "华为Mate60 Pro价格多少，值得买吗"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["sub_intents"]) <= 3
    for sub in data["sub_intents"]:
        assert "intent" in sub
        assert "confidence" in sub
        assert 0.0 <= sub["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_intent_recognize_returns_sub_intents(client: AsyncClient) -> None:
    """Logistics query."""
    response = await client.post(
        "/intent/recognize",
        json={"text": "我的快递什么时候到"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == IntentEnum.LOGISTICS.value


@pytest.mark.asyncio
async def test_intent_recognize_empty_text_fails(client: AsyncClient) -> None:
    """Empty text should return 422 Unprocessable Entity."""
    response = await client.post(
        "/intent/recognize",
        json={"text": ""},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Entity Extraction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_entity_extract_brand(client: AsyncClient) -> None:
    """'小米13 Pro 8+256' should extract brand=小米."""
    response = await client.post(
        "/entity/extract",
        json={"text": "小米13 Pro 8+256"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["entities"]["brand"] == "小米"


@pytest.mark.asyncio
async def test_entity_extract_budget(client: AsyncClient) -> None:
    """'预算5000元以内' should extract budget_max=5000."""
    response = await client.post(
        "/entity/extract",
        json={"text": "预算5000元以内"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["entities"]["budget_max"] == 5000.0


@pytest.mark.asyncio
async def test_entity_extract_category(client: AsyncClient) -> None:
    """'我想买一台冰箱' should extract category=冰箱."""
    response = await client.post(
        "/entity/extract",
        json={"text": "我想买一台冰箱"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["entities"]["category"] == "冰箱"


@pytest.mark.asyncio
async def test_entity_extract_specs_combo(client: AsyncClient) -> None:
    """'8+256' should extract ram=8GB and storage=256GB."""
    response = await client.post(
        "/entity/extract",
        json={"text": "我要小米13 8+256G的版本"},
    )
    assert response.status_code == 200
    data = response.json()
    specs = data["entities"].get("specs") or {}
    assert specs.get("ram") == "8GB"
    assert specs.get("storage") == "256GB"


@pytest.mark.asyncio
async def test_entity_extract_budget_range(client: AsyncClient) -> None:
    """Budget range '3000到5000元' should set both min and max."""
    response = await client.post(
        "/entity/extract",
        json={"text": "预算3000到5000元"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["entities"]["budget_min"] == 3000.0
    assert data["entities"]["budget_max"] == 5000.0


@pytest.mark.asyncio
async def test_entity_extract_quantity(client: AsyncClient) -> None:
    """'我需要3台' should extract quantity=3."""
    response = await client.post(
        "/entity/extract",
        json={"text": "我需要3台空调"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["entities"]["quantity"] == 3


@pytest.mark.asyncio
async def test_entity_extract_huawei(client: AsyncClient) -> None:
    """'华为Mate60 Pro' should extract brand=华为."""
    response = await client.post(
        "/entity/extract",
        json={"text": "我要买华为Mate60 Pro"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["entities"]["brand"] == "华为"


# ---------------------------------------------------------------------------
# Brand Detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_brand_detect_known(client: AsyncClient) -> None:
    """'我要买华为Mate60' with brand+model → KNOWN."""
    response = await client.post(
        "/brand/detect",
        json={
            "text": "我要买华为Mate60",
            "entities": {"brand": "华为", "model": "Mate60"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["brand_status"] == BrandStatusEnum.KNOWN.value
    assert data["brand_name"] == "华为"
    assert data["confidence"] > 0.5


@pytest.mark.asyncio
async def test_brand_detect_unknown(client: AsyncClient) -> None:
    """'帮我推荐一款手机' → UNKNOWN."""
    response = await client.post(
        "/brand/detect",
        json={
            "text": "帮我推荐一款手机",
            "entities": {},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["brand_status"] == BrandStatusEnum.UNKNOWN.value
    assert data["brand_name"] is None


@pytest.mark.asyncio
async def test_brand_detect_partial(client: AsyncClient) -> None:
    """'我想买小米的手机' with brand but no model → PARTIAL."""
    response = await client.post(
        "/brand/detect",
        json={
            "text": "我想买小米的手机",
            "entities": {"brand": "小米"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["brand_status"] == BrandStatusEnum.PARTIAL.value
    assert data["brand_name"] == "小米"


@pytest.mark.asyncio
async def test_brand_detect_reasoning_present(client: AsyncClient) -> None:
    """Response should always include a non-empty reasoning string."""
    response = await client.post(
        "/brand/detect",
        json={"text": "随便推荐一个", "entities": {}},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["reasoning"], str)
    assert len(data["reasoning"]) > 0


@pytest.mark.asyncio
async def test_brand_detect_no_preference(client: AsyncClient) -> None:
    """'不知道买哪个，帮我选一下' → UNKNOWN."""
    response = await client.post(
        "/brand/detect",
        json={
            "text": "不知道买哪个，帮我选一下",
            "entities": {},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["brand_status"] == BrandStatusEnum.UNKNOWN.value
