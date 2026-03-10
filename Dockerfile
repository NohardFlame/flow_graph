# Shared image for API and worker. Use different CMD for each role.
# API:  uvicorn app.api.main:app --host 0.0.0.0 --port 8000
# Worker: arq app.workers.arq_tasks.WorkerSettings

FROM python:3.12-slim

WORKDIR /app

# System deps: libpq for psycopg, curl for healthcheck
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install app and worker extra (ARQ)
COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY data ./data

RUN pip install --no-cache-dir -e ".[worker]"

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Default: API. Override in compose: command: ["arq", "app.workers.arq_tasks.WorkerSettings"]
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
