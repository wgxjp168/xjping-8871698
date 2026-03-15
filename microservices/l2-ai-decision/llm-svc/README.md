# llm-svc – ILbuy L2 AI Decision Hub

Unified LLM gateway microservice for the ILbuy L2 AI Decision Hub. Provides a
single HTTP API to OpenAI, Anthropic, and Baidu Wenxin with automatic provider
fallback, structured prompt engineering, and response parsing tailored for
B2B/B2C e-commerce procurement workflows.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Provider Setup](#provider-setup)
- [Running Tests](#running-tests)
- [Docker](#docker)
- [Kubernetes](#kubernetes)

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set required environment variables (see Configuration)
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...

# 3. Start the service
uvicorn app.main:app --host 0.0.0.0 --port 8011 --reload
```

Interactive API docs: http://localhost:8011/docs

---

## Configuration

All settings are loaded from environment variables (or a `.env` file in the
working directory).

| Variable | Default | Description |
|---|---|---|
| `ENV` | `development` | Runtime environment (`development` / `staging` / `production`) |
| `PORT` | `8011` | HTTP listen port |
| `LLM_PROVIDER` | `openai` | Primary LLM provider (`openai` / `anthropic` / `wenxin`) |
| `OPENAI_API_KEY` | – | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model identifier |
| `ANTHROPIC_API_KEY` | – | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-opus-4-6` | Anthropic model identifier |
| `WENXIN_API_KEY` | – | Baidu Wenxin API key (client_id) |
| `WENXIN_SECRET_KEY` | – | Baidu Wenxin secret key (client_secret) |
| `REQUEST_TIMEOUT` | `60` | LLM API call timeout in seconds |
| `MAX_RETRIES` | `3` | Maximum retry attempts per request |

At least one provider must have its API key configured; otherwise every chat
request will return a 503.

---

## API Reference

### GET /health

Liveness probe.

**Response 200:**
```json
{"status": "ok", "service": "llm-svc"}
```

---

### GET /llm/providers

List available providers and their status.

**Response 200:**
```json
{
  "providers": {
    "openai":    {"available": true,  "model": "gpt-4o",          "api_key_configured": true},
    "anthropic": {"available": false, "model": "claude-opus-4-6", "api_key_configured": false},
    "wenxin":    {"available": false, "model": "ernie-bot-pro",   "api_key_configured": false}
  }
}
```

---

### POST /llm/chat

General multi-turn chat. Supports provider override per request.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "请帮我分析一下这款传感器的市场定位"}
  ],
  "provider": "openai",
  "max_tokens": 2048,
  "temperature": 0.7,
  "stream": false,
  "context_type": "general"
}
```

**Response 200:**
```json
{
  "content": "这款传感器定位于工业自动化领域……",
  "provider": "openai",
  "model": "gpt-4o",
  "usage": {"prompt_tokens": 45, "completion_tokens": 230, "total_tokens": 275},
  "latency_ms": 1342.5
}
```

---

### POST /llm/analyze/product

Analyse a product description against structured buyer requirements.

**Request:**
```json
{
  "product_description": "工业级压力传感器，量程0-10 bar，4-20mA输出，IP67防护",
  "user_requirements": {
    "quantity": 500,
    "certifications": ["CE", "RoHS"],
    "delivery_weeks": 8
  },
  "budget_range": {"min": 20, "max": 80, "currency": "USD"}
}
```

**Response 200:**
```json
{
  "analysis": "该产品完全满足买家的技术要求……",
  "key_features": ["IP67防水", "4-20mA输出", "量程0-10 bar"],
  "pros": ["规格匹配", "价格合理"],
  "cons": ["交货期稍长"],
  "match_score": 0.92,
  "recommendation": "建议采购，优先询价500件。"
}
```

---

### POST /llm/analyze/decision

Generate decision-support context from parsed user intent and entities.

**Request:**
```json
{
  "intent": "compare",
  "entities": {"product": "压力传感器", "brands": ["Siemens", "Honeywell"]},
  "brand_status": "authorized",
  "user_context": {"membership": "gold", "history": []}
}
```

**Response 200:**
```json
{
  "decision_context": "用户正在比较两家知名品牌……",
  "suggested_questions": [
    "您需要的最小起订量是多少？",
    "是否有特定的认证要求？"
  ],
  "confidence_factors": ["品牌授权确认", "产品规格明确"],
  "preliminary_recommendation": "建议优先考虑Honeywell，供货周期更短。"
}
```

---

### POST /llm/report/generate

Generate a comprehensive procurement decision report.

**Request:**
```json
{
  "decision_data": {
    "intent": "buy",
    "entities": {"product": "传感器"},
    "analysis": {"match_score": 0.88}
  },
  "scoring_result": {
    "overall_score": 87.5,
    "rank": 1,
    "breakdown": {"quality": 90, "price": 85, "delivery": 88}
  },
  "report_format": "detailed"
}
```

**Response 200:**
```json
{
  "report": "# 采购决策报告\n\n## 执行摘要\n……",
  "provider": "openai",
  "model": "gpt-4o",
  "latency_ms": 3210.0
}
```

---

## Provider Setup

### OpenAI

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o        # optional
```

### Anthropic

```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
export ANTHROPIC_MODEL=claude-opus-4-6  # optional
```

Adaptive thinking is automatically enabled for requests with `max_tokens >= 1024`,
which improves analysis quality for complex procurement scenarios.

### Baidu Wenxin (ERNIE-Bot Pro)

```bash
export LLM_PROVIDER=wenxin
export WENXIN_API_KEY=<client_id>
export WENXIN_SECRET_KEY=<client_secret>
```

The service fetches an OAuth2 access token automatically and caches it for
the token lifetime (~30 days). Tokens are refreshed transparently.

---

## Provider Fallback

If the primary provider fails (after `MAX_RETRIES` attempts), the service
automatically tries the next available provider. Priority order:

```
openai → anthropic → wenxin
```

---

## Running Tests

```bash
# From the llm-svc directory
pytest tests/ -v
```

All tests use mocked LLM clients – no real API keys required.

---

## Docker

```bash
# Build
docker build -t ilbuy/llm-svc:latest .

# Run
docker run -p 8011:8011 \
  -e LLM_PROVIDER=openai \
  -e OPENAI_API_KEY=sk-... \
  ilbuy/llm-svc:latest
```

---

## Kubernetes

```bash
# Create namespace (if not already present)
kubectl create namespace ilbuy-l2

# Populate the secret with real credentials
kubectl create secret generic llm-svc-secrets \
  --namespace=ilbuy-l2 \
  --from-literal=LLM_PROVIDER=openai \
  --from-literal=OPENAI_API_KEY=sk-... \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-...

# Deploy
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Verify
kubectl -n ilbuy-l2 get pods -l app=llm-svc
kubectl -n ilbuy-l2 get svc llm-svc
```

Service is exposed within the cluster at `llm-svc.ilbuy-l2.svc.cluster.local:8011`.
