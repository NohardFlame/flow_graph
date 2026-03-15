#!/usr/bin/env bash
# Bring up infra (postgres, redis, minio), run migrations, then start API, worker, and generateTest UI automatically.
# Usage: from repo root, ./scripts/up-infra.sh
#        (on first use: chmod +x scripts/up-infra.sh)
# Requires: bash, docker compose, python3

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# 1) Ensure .env exists with host variables (localhost for postgres, redis, minio)
ENV_PATH="$REPO_ROOT/.env"
if [ ! -f "$ENV_PATH" ]; then
  EXAMPLE_HOST="$REPO_ROOT/.env.example.host"
  if [ -f "$EXAMPLE_HOST" ]; then
    cp "$EXAMPLE_HOST" "$ENV_PATH"
    echo "Created .env from .env.example.host (host variables). Edit .env if needed."
  else
    echo ".env not found. Create .env with POSTGRES_HOST=localhost, REDIS_URL=redis://localhost:6379/0, S3_ENDPOINT_URL=http://localhost:9000" >&2
    exit 1
  fi
fi

# 2) Load .env into current process
# shellcheck source=scripts/load-env.sh
source "$SCRIPT_DIR/load-env.sh" ".env"

# 3) Ensure .venv and install dependencies
VENV_PATH="$REPO_ROOT/.venv"
VENV_PYTHON="$VENV_PATH/bin/python"
VENV_PIP="$VENV_PATH/bin/pip"
if [ ! -f "$VENV_PYTHON" ]; then
  echo "Creating .venv and installing dependencies..."
  python3 -m venv "$VENV_PATH"
  "$VENV_PIP" install -e ".[worker]"
fi

# 4) Start infra containers
echo "Starting postgres, redis, minio..."
docker compose -f docker-compose.infra.yml up -d

# 5) Wait for postgres
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  if docker compose -f docker-compose.infra.yml exec -T postgres pg_isready -U postgres 2>/dev/null; then
    break
  fi
  ATTEMPT=$((ATTEMPT + 1))
  echo "Waiting for postgres... ($ATTEMPT/$MAX_ATTEMPTS)"
  sleep 2
done
if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
  echo "Postgres did not become ready" >&2
  exit 1
fi
echo "Postgres is ready."

# 6) Create MinIO bucket (run with current env so S3_* are set)
echo "Creating S3 bucket if needed..."
"$VENV_PYTHON" -c '
import os, sys, time
try:
  import boto3
  from botocore.exceptions import ClientError
except ImportError:
  sys.exit(0)
ep = os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000")
bucket = os.environ.get("S3_BUCKET", "flow-graph")
for i in range(15):
  try:
    c = boto3.client(
      "s3",
      endpoint_url=ep,
      region_name="us-east-1",
      aws_access_key_id=os.environ.get("S3_ACCESS_KEY_ID", "minioadmin"),
      aws_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY", "minioadmin"),
    )
    c.create_bucket(Bucket=bucket)
    print("Bucket", bucket, "created")
    break
  except ClientError as e:
    if e.response.get("Error", {}).get("Code") in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
      print("Bucket already exists")
      break
    time.sleep(1)
  except Exception:
    time.sleep(1)
else:
  sys.exit(1)
' || echo "Bucket creation failed or MinIO not ready; continue anyway."

# 7) Run migrations
echo "Running Alembic migrations..."
"$VENV_PYTHON" -m alembic upgrade head

# 8) Start API, worker, and generateTest UI (inherit env from this process)
echo "Starting API (port 8000), worker, and generateTest UI (port 8765)..."
mkdir -p "$REPO_ROOT/logs"
nohup "$VENV_PYTHON" -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 </dev/null >> "$REPO_ROOT/logs/api.log" 2>&1 &
nohup "$VENV_PYTHON" -m arq app.workers.arq_tasks.WorkerSettings </dev/null >> "$REPO_ROOT/logs/worker.log" 2>&1 &

GENERATE_TEST_DIR="$REPO_ROOT/generateTest"
if [ -f "$GENERATE_TEST_DIR/run.py" ]; then
  (cd "$GENERATE_TEST_DIR" && nohup "$VENV_PYTHON" run.py --serve </dev/null >> "$REPO_ROOT/logs/generateTest-ui.log" 2>&1 &)
else
  echo "generateTest/run.py not found; skipping TestGen UI."
fi

echo "API:        http://localhost:8000"
echo "ingest_UI:  http://localhost:8000/ui"
echo "TestGen UI: http://localhost:8765"
echo "Worker and UI are running in background. Stop with: pkill -f 'uvicorn app.api.main' ; pkill -f 'arq app.workers' ; pkill -f 'run.py --serve'"
echo "Logs: $REPO_ROOT/logs/"
