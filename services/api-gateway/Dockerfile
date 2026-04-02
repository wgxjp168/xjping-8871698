FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY index.html .
COPY architecture.html .
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8080", "--timeout", "60", "app:app"]
HEALTHCHECK --interval=10s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/actuator/health')"
