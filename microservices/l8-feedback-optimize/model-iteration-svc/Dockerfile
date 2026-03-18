FROM python:3.11-slim

# Non-root user
RUN groupadd -r ilbuy && useradd -r -g ilbuy -d /app -s /sbin/nologin ilbuy

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ app/

# Model store directory
RUN mkdir -p /app/model_store && chown -R ilbuy:ilbuy /app

USER ilbuy

EXPOSE 8062

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8062/health/liveness')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8062", "--workers", "1"]
