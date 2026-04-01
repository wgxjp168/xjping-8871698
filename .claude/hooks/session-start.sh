#!/bin/bash
# ILbuy SessionStart Hook
# Installs Python deps and starts all 6 microservices for web sessions.
set -euo pipefail

# Only run in remote (Claude Code on the web) environment
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

REPO="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
LOG_DIR="/tmp/ilbuy-logs"
PID_FILE="/tmp/ilbuy.pids"

mkdir -p "$LOG_DIR"

# ── 1. Install Python dependencies ──────────────────────────────────────────
echo "[setup] Installing Python dependencies..."
pip install -q \
  flask==3.1.3 \
  flask-limiter==4.1.1 \
  gunicorn==23.0.0 \
  requests==2.32.3 \
  redis==7.3.0 \
  2>/dev/null
echo "[setup] Dependencies installed."

# ── 2. Persist env vars for the session ─────────────────────────────────────
cat >> "${CLAUDE_ENV_FILE:-/dev/null}" << 'ENVEOF'
export RATELIMIT_STORAGE_URI=memory://
export JWT_SECRET="ILbuy@JWT@SecretKey@2024@Production"
export USER_SERVICE_URL="http://localhost:8001"
export PROCUREMENT_SERVICE_URL="http://localhost:8002"
export AI_SERVICE_URL="http://localhost:8003"
export ORDER_SERVICE_URL="http://localhost:8004"
export DATA_SERVICE_URL="http://localhost:8005"
ENVEOF

# ── 3. Stop any leftover services from a previous session ───────────────────
if [ -f "$PID_FILE" ]; then
  while read -r pid _name; do
    kill "$pid" 2>/dev/null || true
  done < "$PID_FILE"
  rm -f "$PID_FILE"
  sleep 1
fi

# ── 4. Start each microservice ───────────────────────────────────────────────
start_svc() {
  local name="$1" dir="$2"
  RATELIMIT_STORAGE_URI=memory:// \
  JWT_SECRET="ILbuy@JWT@SecretKey@2024@Production" \
  USER_SERVICE_URL="http://localhost:8001" \
  PROCUREMENT_SERVICE_URL="http://localhost:8002" \
  AI_SERVICE_URL="http://localhost:8003" \
  ORDER_SERVICE_URL="http://localhost:8004" \
  DATA_SERVICE_URL="http://localhost:8005" \
  python3 "$dir/app.py" >> "$LOG_DIR/$name.log" 2>&1 &
  echo "$! $name" >> "$PID_FILE"
}

wait_healthy() {
  local url="$1" name="$2"
  for i in $(seq 1 30); do
    if curl -sf "$url" >/dev/null 2>&1; then
      echo "[ok] $name ready"
      return 0
    fi
    sleep 1
  done
  echo "[warn] $name not ready after 30s — continuing anyway"
}

> "$PID_FILE"

echo "[setup] Starting microservices..."
start_svc user-service            "$REPO/services/user-service"
wait_healthy http://localhost:8001/health "user-service"

start_svc procurement-service     "$REPO/services/procurement-service"
wait_healthy http://localhost:8002/health "procurement-service"

start_svc ai-matching-service     "$REPO/services/ai-matching-service"
wait_healthy http://localhost:8003/health "ai-matching-service"

start_svc order-service           "$REPO/services/order-service"
wait_healthy http://localhost:8004/health "order-service"

start_svc data-collector-service  "$REPO/services/data-collector-service"
wait_healthy http://localhost:8005/health "data-collector-service"

start_svc api-gateway             "$REPO/services/api-gateway"
wait_healthy http://localhost:8080/actuator/health "api-gateway"

echo "[setup] All 6 ILbuy services are running. Ready to test!"
