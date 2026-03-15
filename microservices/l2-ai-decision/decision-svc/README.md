# ILbuy L2 AI Decision Hub — decision-svc

**Port:** `8012`  
**Language:** Python 3.11 / FastAPI  
**Role:** Core purchase-decision microservice providing 8-step AI analysis, Drools-inspired rule evaluation, and multi-context scoring models.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [API Reference](#api-reference)
3. [8-Step Decision Flow](#8-step-decision-flow)
4. [Scoring Models](#scoring-models)
5. [Rule Engine](#rule-engine)
6. [Explainability Engine](#explainability-engine)
7. [Configuration](#configuration)
8. [Testing](#testing)
9. [Deployment](#deployment)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run in development mode
uvicorn app.main:app --host 0.0.0.0 --port 8012 --reload

# Swagger UI
open http://localhost:8012/docs
```

---

## API Reference

### POST `/decision/analyze`

Full 8-step AI decision analysis.

**Request:**
```json
{
  "session_id": "sess-abc123",
  "intent": "企业采购笔记本电脑",
  "entities": {
    "product_price": 8999.0,
    "budget": 10000.0,
    "brand": "Lenovo",
    "category": "laptop",
    "org_type": "enterprise",
    "order_quantity": 20,
    "min_order_quantity": 10
  },
  "brand_status": "KNOWN",
  "user_context": {
    "org_type": "enterprise",
    "approved_brands": ["Lenovo", "Dell", "HP"]
  }
}
```

**Response:** `DecisionAnalyzeResponse`
```json
{
  "decision_id": "DEC-A1B2C3D4E5F6",
  "scoring_context": "B2B",
  "score_result": {
    "total_score": 82.4,
    "grade": "B",
    "confidence": 0.91,
    "dimension_scores": { ... },
    "factors": [ ... ]
  },
  "rule_result": {
    "passed": true,
    "violations": [],
    "warnings": [],
    "applied_rules": ["RULE_001", "RULE_002", ...]
  },
  "recommendation": "该产品综合评分良好，推荐采购。",
  "next_steps": [ ... ],
  "requires_human_review": false,
  "explanation": { ... }
}
```

---

### POST `/decision/score`

Score-only endpoint. Skips rule engine and explanation generation.

**Request:** Same as `/decision/analyze`, optionally add `"scoring_context": "B2B"`.

**Response:** `ScoreResult`

---

### POST `/decision/rules`

Rules-only compliance check.

**Request:** Same as `/decision/analyze`.

**Response:**
```json
{
  "passed": false,
  "violations": ["[RULE_001] 产品价格 ¥1500.00 超出预算 ¥1000.00（超出 50.0%）"],
  "warnings": [],
  "applied_rules": ["RULE_001", ..., "RULE_008"]
}
```

---

### GET `/decision/report/{decision_id}?format=markdown`

Retrieve a report for a previously analyzed decision.

- `format=json` (default) — structured JSON report
- `format=markdown` — rich Markdown with tables and sections

---

### POST `/decision/report/generate`

Generate a report from a cached decision.

**Request:**
```json
{
  "decision_id": "DEC-A1B2C3D4E5F6",
  "include_explanation": true,
  "format": "markdown"
}
```

---

### GET `/health` · GET `/decision/health`

```json
{ "status": "ok", "service": "decision-svc", "version": "1.0.0" }
```

---

## 8-Step Decision Flow

Each step is independently logged and the flow is fully async.

| Step | Name | Description |
|------|------|-------------|
| 1 | `validate_input` | Validates required fields (session_id, intent) |
| 2 | `determine_scoring_context` | Detects B2B vs B2C_KNOWN vs B2C_UNKNOWN from intent keywords and entity signals |
| 3 | `enrich_context` | Calls L3 product service + L3 market data service; falls back to mock data when services are unavailable |
| 4 | `apply_rules` | Evaluates all 8 business rules via the Drools-inspired rule engine |
| 5 | `calculate_scores` | Runs the appropriate scorer (B2B / B2C_KNOWN / B2C_UNKNOWN) |
| 6 | `get_llm_insights` | Optional async call to llm-svc for supplementary analysis; safely skipped if unavailable |
| 7 | `generate_explanation` | SHAP-inspired feature importance, top positive/negative drivers, counterfactual reasoning |
| 8 | `compile_decision` | Assembles recommendation, next-steps, human-review flag, and the full `DecisionAnalyzeResponse` |

### Context Determination Logic

```
B2B       ← intent contains "企业/采购/批量" OR org_type is "enterprise/corporate"
B2C_KNOWN ← brand_status == "KNOWN"
B2C_UNKNOWN ← brand_status == "UNKNOWN" or "PARTIAL" (default)
```

---

## Scoring Models

### B2B Scorer (`ScoringContext.B2B`)

| Dimension | Weight | Key Signals |
|-----------|--------|-------------|
| price_competitiveness | 25% | `market_price_ratio`, `bulk_discount_available` |
| supplier_reliability | 20% | `brand_tier` (A/B/C), `certification_count`, `years_in_market` |
| delivery_capability | 20% | `lead_time_days`, `stock_availability` |
| quality_compliance | 15% | `has_quality_cert`, `return_rate` |
| after_service | 10% | `warranty_months`, `support_response_hours` |
| min_order_qty_fit | 10% | `order_quantity` vs `min_order_quantity` |

### B2C Known-Brand Scorer (`ScoringContext.B2C_KNOWN`)

| Dimension | Weight | Key Signals |
|-----------|--------|-------------|
| price_value | 30% | `product_price / budget`, `promotion_available` |
| brand_match | 25% | exact/partial brand match, `is_authorized_dealer` |
| spec_match | 25% | overlap of `required_specs` vs `product_specs` |
| availability | 10% | `in_stock`, `delivery_time_days` |
| review_score | 10% | `average_rating / 5 × 100`, weighted by `review_count` |

### B2C Unknown-Brand Scorer (`ScoringContext.B2C_UNKNOWN`)

| Dimension | Weight | Key Signals |
|-----------|--------|-------------|
| category_fit | 25% | `user_need_category` vs `product_category`, tag overlap |
| budget_match | 30% | `product_price` within `[budget_min, budget_max]` |
| feature_richness | 20% | `product_spec_count / category_avg_spec_count` |
| popularity | 15% | `sales_rank`, `review_count`, `average_rating` |
| value_for_money | 10% | features-per-yuan ratio |

### Grade Thresholds

| Grade | Score Range | Description |
|-------|-------------|-------------|
| A | ≥ 85 | 优秀 — 强烈推荐 |
| B | 70–84 | 良好 — 推荐采购 |
| C | 55–69 | 一般 — 谨慎评估 |
| D | < 55 | 较差 — 不建议采购 |

---

## Rule Engine

Drools-inspired Python rule engine. All 8 rules are evaluated in priority order (no short-circuit).

| Rule ID | Name | Category | Severity | Trigger Condition |
|---------|------|----------|----------|-------------------|
| RULE_001 | budget_check | budget | violation | `product_price > budget` |
| RULE_002 | min_order_quantity | logistics | violation | B2B `order_quantity < min_order_quantity` |
| RULE_003 | brand_compliance | compliance | warning | B2B brand not in `approved_brands` |
| RULE_004 | delivery_feasibility | logistics | warning | `delivery_time_days > max_delivery_days` |
| RULE_005 | category_restriction | compliance | violation | product category in `restricted_categories` |
| RULE_006 | duplicate_order | risk | warning | similar order within last 24 hours |
| RULE_007 | price_reasonableness | budget | warning | `product_price > 3 × market_reference_price` |
| RULE_008 | spec_compatibility | compliance | violation | required spec values not met by product specs |

Custom rules can be registered via `rule_engine.register_rule(Rule(...))`.

---

## Explainability Engine

SHAP-inspired feature importance analysis:

- **Feature Importance** — Each factor's actual weighted contribution vs. baseline (50 × weight). Positive delta = driving score up.
- **Top Positive Factors** — Top-3 dimensions contributing most positively.
- **Top Negative Factors** — Top-3 dimensions dragging the score down.
- **Natural Language Summary** — Auto-generated Chinese explanation.
- **Counterfactual** — "如果X改变，分数将提升Y点" format guidance.

Example counterfactual output:
```
当前评分 62.5 分（一般），距良好（B级）还差 7.5 分。
建议重点改善「交付能力」维度（当前 35.0 分），
若该项提升至满分可带来约 7.0 分的总分增益。
```

---

## Configuration

Environment variables (can be set in `.env` or K8s ConfigMap):

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | `development` | Deployment environment |
| `PORT` | `8012` | Service listen port |
| `INTENT_SVC_URL` | `http://intent-svc:8011` | Intent service URL |
| `LLM_SVC_URL` | `http://llm-svc:8013` | LLM service URL |
| `L3_DATA_SVC_URL` | `http://l3-data-svc:8031` | L3 data service URL |
| `L3_PRODUCT_SVC_URL` | `http://l3-product-svc:8032` | L3 product service URL |
| `HTTP_TIMEOUT` | `5.0` | HTTP client timeout (seconds) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DECISION_CACHE_TTL` | `3600` | In-memory cache TTL (seconds) |

---

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run specific test class
pytest tests/test_decision.py::TestB2BScoring -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

Test coverage includes:
- B2B scoring (7 cases)
- B2C Known scoring (6 cases)
- B2C Unknown scoring (5 cases)
- Rule engine (7 cases)
- Full 8-step decision flow (4 integration cases)
- Markdown report generation (5 cases)
- Explainability engine (6 cases)
- Health endpoints (2 cases)

---

## Deployment

### Docker

```bash
docker build -t ilbuy/decision-svc:latest .
docker run -p 8012:8012 --env-file .env ilbuy/decision-svc:latest
```

### Kubernetes

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Verify
kubectl get pods -n ilbuy-l2 -l app=decision-svc
kubectl get svc -n ilbuy-l2 decision-svc
```

K8s resources:
- **Deployment**: 2 replicas, rolling update, non-root securityContext
- **Resources**: 250m/256Mi requests, 500m/512Mi limits
- **Service**: ClusterIP on port 8012
- **Health checks**: liveness + readiness on `/health`
- **Anti-affinity**: TopologySpreadConstraints for HA across nodes

---

## Service Dependencies

```
decision-svc (8012)
├── intent-svc (8011)       ← optional upstream
├── llm-svc (8013)          ← optional, step 6
├── l3-data-svc (8031)      ← enrichment, mock fallback
└── l3-product-svc (8032)   ← enrichment, mock fallback
```

All downstream service calls include graceful fallback to mock data, ensuring the decision flow completes even when dependencies are unavailable.

---

*ILbuy L2 AI Decision Hub — decision-svc v1.0.0*
