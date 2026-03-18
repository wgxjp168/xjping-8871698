# model-iteration-svc

**ILbuy 我来购 Platform — Layer 8 (反馈优化层)**

XGBoost recommendation model training, evaluation and A/B experiment management service.

## Features

- Consumes `l8.behavior.aggregated` events from behavior-track-svc via RabbitMQ
- Trains XGBoost classifiers on behavior features (conversion_rate, avg_satisfaction, click_count, view_count, session_duration)
- Evaluates models against configurable AUC/F1 thresholds
- Publishes `l8.model.ready` to RabbitMQ when a model is approved for deployment
- Manages A/B experiments between model versions with proportion z-test analysis
- Exposes REST API on port **8062**

## Data Flow

```
behavior-track-svc
    └─ RabbitMQ: l8.behavior.aggregated
            │
    model-iteration-svc (port 8062)
            │  ├─ train XGBoost model
            │  ├─ evaluate (AUC ≥ 0.65, F1 ≥ 0.60)
            │  └─ run A/B experiments
            │
    RabbitMQ: l8.model.ready
            │
    model-deploy-svc
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health/liveness | Liveness probe |
| GET | /health/readiness | Readiness probe (checks DB) |
| POST | /api/v1/models/train | Trigger a training job |
| GET | /api/v1/models/jobs/{job_id} | Get training job status |
| GET | /api/v1/models/versions | List model versions |
| POST | /api/v1/models/versions/{id}/approve | Approve a model version |
| POST | /api/v1/experiments | Create A/B experiment |
| GET | /api/v1/experiments | List experiments |
| POST | /api/v1/experiments/{id}/start | Start an experiment |
| POST | /api/v1/experiments/{id}/complete | Complete & analyze experiment |
| GET | /api/v1/experiments/{id}/results | Get experiment results |

## Local Startup

```bash
# Prerequisites: PostgreSQL, RabbitMQ running locally

# Install dependencies
pip install -r requirements.txt

# Configure environment (optional — defaults work for local dev)
export DB_URL="postgresql+asyncpg://ilbuy:ilbuy@localhost:5432/ilbuy_l8"
export RABBITMQ_URL="amqp://guest:guest@localhost:5672/"

# Run
uvicorn app.main:app --host 0.0.0.0 --port 8062 --reload
```

## Configuration

All settings are loaded via `app/config.py` (pydantic-settings, supports `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| DB_URL | postgresql+asyncpg://... | PostgreSQL async URL |
| RABBITMQ_URL | amqp://guest:guest@localhost:5672/ | RabbitMQ URL |
| RABBITMQ_EXCHANGE | ilbuy.l8 | Topic exchange name |
| MODEL_STORE_PATH | /app/model_store | Model artifact directory |
| MIN_TRAINING_SAMPLES | 100 | Minimum samples before auto-training |
| MIN_AUC | 0.65 | Minimum AUC-ROC to pass evaluation |
| MIN_F1 | 0.60 | Minimum F1 to pass evaluation |
| AB_TEST_MIN_SAMPLE_SIZE | 200 | Minimum users per variant for significance |
| AB_TEST_CONFIDENCE_LEVEL | 0.95 | Confidence level for z-test |

## Running Tests

```bash
# Install test dependencies (included in requirements.txt)
pip install pytest pytest-asyncio aiosqlite httpx

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_models.py -v
pytest tests/test_experiments.py -v
```

## Docker

```bash
docker build -t ilbuy/model-iteration-svc:latest .
docker run -p 8062:8062 \
  -e DB_URL="postgresql+asyncpg://ilbuy:ilbuy@host.docker.internal:5432/ilbuy_l8" \
  -e RABBITMQ_URL="amqp://guest:guest@host.docker.internal:5672/" \
  ilbuy/model-iteration-svc:latest
```

## Kubernetes Deployment

```bash
# Apply all k8s manifests
kubectl apply -f k8s/deployment.yaml

# Check status
kubectl get pods -n ilbuy-l8 -l app=model-iteration-svc
kubectl logs -n ilbuy-l8 -l app=model-iteration-svc --tail=50
```
