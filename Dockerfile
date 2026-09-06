# ── Stage 1: base ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# Don't write .pyc files, don't buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (layer cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# ── Runtime config ──────────────────────────────────────────────────────────
# These are defaults — override in docker-compose.yml or K8s deployment.yaml
ENV APP_VERSION=v1 \
    BUILD_NUMBER=0 \
    ENVIRONMENT=production \
    PORT=8000 \
    WORKERS=2

EXPOSE 8000

# Use gunicorn with uvicorn workers in production
# --bind 0.0.0.0:8000   listen on all interfaces (required in container)
# --workers 2           2 worker processes
# --worker-class        uvicorn async workers
# --timeout 120         allow /load endpoint to run up to 2 minutes
CMD ["gunicorn", "run:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120", \
     "--log-level", "info", \
     "--access-logfile", "-"]
