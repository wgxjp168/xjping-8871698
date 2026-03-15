# ---------------------------------------------------------------------------
# Stage 1: Builder — install Python dependencies into a venv
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Install build tools needed for some native packages (e.g. numpy, torch)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy only requirements first to leverage Docker layer cache
COPY requirements.txt .

# Create isolated virtual environment and install dependencies
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip wheel && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Runtime — lean image with only the application
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Security updates
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Make venv commands available on PATH
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Tell jieba / transformers to use app-local cache dirs
    TRANSFORMERS_CACHE="/app/.cache/huggingface" \
    JIEBA_CACHE="/app/.cache/jieba"

WORKDIR /app

# Create non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Copy application source
COPY --chown=appuser:appgroup app/ ./app/

# Create cache directories owned by appuser
RUN mkdir -p /app/.cache/huggingface /app/.cache/jieba && \
    chown -R appuser:appgroup /app/.cache

# Switch to non-root user
USER appuser

EXPOSE 8010

# Healthcheck — Kubernetes will also probe via the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8010/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010", \
     "--workers", "1", "--log-level", "info"]
