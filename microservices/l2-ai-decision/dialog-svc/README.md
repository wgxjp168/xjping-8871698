# dialog-svc

**ILbuy L2 AI Decision Hub — Dialog Service**

`dialog-svc` is a Node.js/Express microservice that manages multi-turn conversational
sessions for the ILbuy AI Decision Hub. It orchestrates the state machine that drives
users through the product-search dialog flow, calling `intent-svc` for NLU and
`decision-svc` to trigger the 8-step AI decision analysis.

---

## Architecture

```
Client ──► dialog-svc:8013 ──► intent-svc:8010  (NLU / entity / brand)
                           └──► decision-svc:8012 (8-step AI decision flow)
                           └──► Redis             (session storage)
```

### Dialog State Machine

```
INIT → COLLECTING → BRAND_DETECTION → DECISION → COMPLETED
                                               └──► ERROR
```

| State            | Description                                               |
|------------------|-----------------------------------------------------------|
| `INIT`           | Session created, awaiting first message                   |
| `COLLECTING`     | Gathering product requirements from the user              |
| `BRAND_DETECTION`| Enough entities collected; detecting brand preferences    |
| `DECISION`       | All params ready; running AI decision flow                |
| `COMPLETED`      | Decision report generated; session complete               |
| `ERROR`          | An unrecoverable error occurred during processing         |

---

## API Endpoints

| Method   | Path                           | Auth     | Description                              |
|----------|--------------------------------|----------|------------------------------------------|
| `GET`    | `/health`                      | None     | Liveness / readiness probe               |
| `POST`   | `/dialog/session`              | None     | Start a new dialog session               |
| `POST`   | `/dialog/message`              | Bearer   | Send a message to an existing session    |
| `GET`    | `/dialog/session/:sessionId`   | None     | Get current session state                |
| `DELETE` | `/dialog/session/:sessionId`   | None     | End (delete) a session                   |
| `GET`    | `/dialog/history/:sessionId`   | None     | Get full message history of a session    |

### POST /dialog/session

**Request body:**
```json
{
  "userId": "optional-user-id",
  "message": "I am looking for a gaming laptop under $1500"
}
```

**Response (201):**
```json
{
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "message": "I understand you are looking for something related to \"search_product\"...",
  "state": "COLLECTING",
  "suggestions": ["Tell me the product category...", "What is your approximate budget?"],
  "requiresMoreInfo": true
}
```

### POST /dialog/message

**Headers:** `Authorization: Bearer <JWT>`

**Request body:**
```json
{
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Budget is around $1200, prefer ASUS or Dell"
}
```

**Response (200):** Same shape as `/dialog/session`.

---

## Environment Variables

| Variable          | Required | Default                            | Description                             |
|-------------------|----------|------------------------------------|-----------------------------------------|
| `PORT`            | No       | `8013`                             | HTTP port to listen on                  |
| `REDIS_URL`       | Yes      | `redis://localhost:6379`           | Redis connection URL                    |
| `JWT_SECRET`      | Yes      | `ilbuy-dialog-svc-dev-secret`      | Secret used to sign/verify JWTs         |
| `AUTH_SVC_URL`    | No       | _(empty)_                          | If set, forward JWT verification here   |
| `INTENT_SVC_URL`  | No       | `http://localhost:8010`            | Base URL for intent-svc                 |
| `DECISION_SVC_URL`| No       | `http://localhost:8012`            | Base URL for decision-svc               |
| `SESSION_TTL`     | No       | `3600`                             | Session expiry in seconds               |
| `LOG_LEVEL`       | No       | `info`                             | Winston log level                       |
| `NODE_ENV`        | No       | `development`                      | Set to `production` in production       |

---

## Local Development

### Prerequisites

- Node.js >= 20
- Redis (local or Docker)

### 1. Install dependencies

```bash
npm install
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your local values
```

Minimum `.env` for local development:

```
PORT=8013
REDIS_URL=redis://localhost:6379
JWT_SECRET=my-local-dev-secret
INTENT_SVC_URL=http://localhost:8010
DECISION_SVC_URL=http://localhost:8012
```

### 3. Start Redis (Docker)

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 4. Start the service

```bash
# Development (auto-reload on file changes)
npm run dev

# Production
npm start
```

### 5. Run tests

```bash
npm test
```

---

## Docker

### Build

```bash
docker build -t ilbuy/dialog-svc:latest .
```

### Run

```bash
docker run -d \
  -p 8013:8013 \
  -e REDIS_URL=redis://host.docker.internal:6379 \
  -e JWT_SECRET=my-secret \
  --name dialog-svc \
  ilbuy/dialog-svc:latest
```

---

## Kubernetes

Apply the manifests in the `k8s/` directory:

```bash
# Create namespace (if not already present)
kubectl create namespace ilbuy

# Create ConfigMap and Secret (adjust values first)
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# Deploy service
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

Expected ConfigMap keys: `REDIS_URL`, `INTENT_SVC_URL`, `DECISION_SVC_URL`,
`AUTH_SVC_URL`, `SESSION_TTL`, `LOG_LEVEL`.

Expected Secret key: `JWT_SECRET`.
