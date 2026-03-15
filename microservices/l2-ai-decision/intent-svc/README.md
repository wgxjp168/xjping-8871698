# ILbuy Intent Service (`intent-svc`)

Microservice in the **ILbuy L2 AI Decision Hub** responsible for:

- **Intent recognition** — classify Chinese e-commerce user text into one of 15 intents
- **Entity extraction** — extract structured product/shopping entities (brand, model, budget, specs, …)
- **Brand detection** — classify the user's brand preference as KNOWN / PARTIAL / UNKNOWN

| Property | Value |
|---|---|
| Language | Python 3.11 |
| Framework | FastAPI |
| Default port | **8010** |
| NLP libraries | jieba, scikit-learn, transformers |

---

## Quick Start

### Local development

```bash
# Clone and enter the service directory
cd microservices/l2-ai-decision/intent-svc

# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --host 0.0.0.0 --port 8010 --reload
```

### Docker

```bash
docker build -t ilbuy/intent-svc:1.0.0 .
docker run -p 8010:8010 ilbuy/intent-svc:1.0.0
```

### Kubernetes

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ENV` | `development` | Runtime environment (`development` / `staging` / `production`) |
| `PORT` | `8010` | Listening port |
| `LOG_LEVEL` | `INFO` | Log level (`DEBUG` / `INFO` / `WARNING` / `ERROR`) |
| `LLM_SVC_URL` | `http://llm-svc:8020` | URL of the downstream LLM service |
| `HF_MODEL_NAME` | `hfl/chinese-roberta-wwm-ext` | Hugging Face model identifier |
| `NLP_DEVICE` | `cpu` | Torch device (`cpu` or `cuda`) |

---

## API Reference

Interactive docs are available at `http://localhost:8010/docs` (Swagger UI) and `/redoc`.

### `GET /health`

Liveness / readiness probe.

**Response `200`**

```json
{
  "status": "ok",
  "service": "intent-svc",
  "version": "1.0.0",
  "env": "development"
}
```

---

### `POST /intent/recognize`

Classify user intent from Chinese text.

**Request body**

```json
{
  "text": "我想买一台小米手机，预算3000元以内",
  "context": { "previous_intent": "CATEGORY_BROWSE" },
  "session_id": "sess-abc-123"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | string | Yes | User utterance (1–2000 chars) |
| `context` | object | No | Conversation context dict |
| `session_id` | string | No | Opaque session ID echoed in response |

**Response `200`**

```json
{
  "intent": "PURCHASE_INQUIRY",
  "confidence": 0.8741,
  "sub_intents": [
    { "intent": "BUDGET_INQUIRY", "confidence": 0.0632 },
    { "intent": "RECOMMENDATION", "confidence": 0.0412 },
    { "intent": "PRICE_QUERY",    "confidence": 0.0215 }
  ],
  "session_id": "sess-abc-123"
}
```

**Supported intents**

| Intent | Description |
|---|---|
| `PURCHASE_INQUIRY` | User wants to buy a product |
| `PRICE_QUERY` | User asking about price |
| `SPEC_QUERY` | User asking about specifications |
| `COMPARISON` | Comparing two or more products |
| `RECOMMENDATION` | User wants a recommendation |
| `COMPLAINT` | User filing a complaint |
| `AFTER_SALES` | After-sales / repair request |
| `LOGISTICS` | Shipping / delivery enquiry |
| `RETURN` | Returning a product |
| `EXCHANGE` | Exchanging a product |
| `BUDGET_INQUIRY` | Budget-related query |
| `BRAND_QUERY` | Brand comparison / enquiry |
| `CATEGORY_BROWSE` | Browsing a product category |
| `CUSTOM_ORDER` | Custom / bulk order |
| `OTHER` | Everything else |

---

### `POST /entity/extract`

Extract structured entities from Chinese shopping text.

**Request body**

```json
{
  "text": "我要买小米13 Pro 8+256，预算5000元以内，要黑色的",
  "intent": "PURCHASE_INQUIRY"
}
```

**Response `200`**

```json
{
  "entities": {
    "brand": "小米",
    "model": "13 Pro",
    "budget_min": null,
    "budget_max": 5000.0,
    "category": "手机",
    "specs": {
      "ram": "8GB",
      "storage": "256GB",
      "color": "黑色"
    },
    "quantity": null,
    "delivery_time": null
  },
  "raw_entities": [
    { "entity_type": "brand",       "value": "小米",   "start": 3,  "end": 5,  "confidence": 0.95 },
    { "entity_type": "specs_combo", "value": "8+256",  "start": 10, "end": 15, "confidence": 0.93 },
    { "entity_type": "budget_max",  "value": "预算5000元以内", "start": 17, "end": 24, "confidence": 0.88 }
  ]
}
```

---

### `POST /brand/detect`

Classify the user's brand preference status.

**Request body**

```json
{
  "text": "我要买华为Mate60 Pro",
  "entities": { "brand": "华为", "model": "Mate60 Pro" }
}
```

**Response `200`**

```json
{
  "brand_status": "KNOWN",
  "brand_name": "华为",
  "confidence": 0.9400,
  "reasoning": "Brand '华为' identified with model 'Mate60 Pro'. Combined known signal: 0.80."
}
```

| `brand_status` | Meaning |
|---|---|
| `KNOWN` | User named a brand and model |
| `PARTIAL` | Brand mentioned but no specific model |
| `UNKNOWN` | No brand preference; user seeks a recommendation |

**Example — UNKNOWN**

```bash
curl -s -X POST http://localhost:8010/brand/detect \
  -H 'Content-Type: application/json' \
  -d '{"text": "帮我推荐一款手机", "entities": {}}' | jq .
```

```json
{
  "brand_status": "UNKNOWN",
  "brand_name": null,
  "confidence": 0.7200,
  "reasoning": "Detected 0.67 UNKNOWN signal strength (recommendation/no-preference phrases found). Known signal was low (0.00)."
}
```

---

## Running Tests

```bash
pytest tests/test_intent.py -v
```

Expected output (all tests pass):

```
tests/test_intent.py::test_health_endpoint                    PASSED
tests/test_intent.py::test_intent_recognize_purchase          PASSED
tests/test_intent.py::test_intent_recognize_recommendation    PASSED
tests/test_intent.py::test_intent_recognize_price_query       PASSED
tests/test_intent.py::test_intent_recognize_with_session_id   PASSED
tests/test_intent.py::test_entity_extract_brand               PASSED
tests/test_intent.py::test_entity_extract_budget              PASSED
tests/test_intent.py::test_entity_extract_category            PASSED
tests/test_intent.py::test_entity_extract_specs_combo         PASSED
tests/test_intent.py::test_entity_extract_budget_range        PASSED
tests/test_intent.py::test_entity_extract_quantity            PASSED
tests/test_intent.py::test_entity_extract_huawei              PASSED
tests/test_intent.py::test_brand_detect_known                 PASSED
tests/test_intent.py::test_brand_detect_unknown               PASSED
tests/test_intent.py::test_brand_detect_partial               PASSED
tests/test_intent.py::test_brand_detect_reasoning_present     PASSED
tests/test_intent.py::test_brand_detect_no_preference         PASSED
```

---

## Architecture

```
intent-svc (port 8010)
│
├── app/
│   ├── main.py               FastAPI app + lifespan + CORS + logging
│   ├── core/
│   │   └── config.py         Pydantic Settings
│   ├── models/
│   │   └── schemas.py        Request/Response Pydantic models
│   ├── api/
│   │   ├── deps.py           Singleton dependency providers (lru_cache)
│   │   └── routes.py         POST /intent/recognize, /entity/extract, /brand/detect; GET /health
│   └── services/
│       ├── intent_recognizer.py   Jieba + TF-IDF + regex intent classifier
│       ├── entity_extractor.py    Rule-based entity extractor
│       └── brand_detector.py      Signal-based brand status classifier
│
├── tests/
│   └── test_intent.py        Async pytest test suite (17 tests)
│
├── k8s/
│   ├── deployment.yaml       2 replicas, 512Mi/500m, rolling update, HPA
│   └── service.yaml          ClusterIP on port 8010
│
├── Dockerfile                Multi-stage, non-root user, python:3.11-slim
└── requirements.txt
```

---

## License

Proprietary — ILbuy Technology Co., Ltd.
