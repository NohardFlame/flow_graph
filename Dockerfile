# syntax=docker/dockerfile:1
# Deps-only image: Python + system deps + pip deps. No app code in the image.
# Compose mounts the project (.:/app) and runs app services; rebuild only when pyproject.toml changes.
# Build with BuildKit for pip cache: DOCKER_BUILDKIT=1 docker compose build

FROM python:3.12-slim

WORKDIR /app

# System deps: libpq for psycopg, curl for healthcheck
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install runtime deps from pinned list (no pytest/pytest-cov). Cached when requirements-docker.txt unchanged.
COPY requirements-docker.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefer-binary -r requirements-docker.txt

# Register the app package (editable, no deps). Stub only; real code is mounted at runtime.
COPY pyproject.toml README.md ./
RUN mkdir -p app && touch app/__init__.py && \
    pip install -e . --no-deps

# Non-root user (mount at runtime must be writable by this user for pip install -e . --no-deps)
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
