# ---- Build/base ----
FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system ilbuy && adduser --system --group ilbuy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN chown -R ilbuy:ilbuy /app
USER ilbuy

EXPOSE 8060

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8060/health/liveness || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8060", "--workers", "2"]
