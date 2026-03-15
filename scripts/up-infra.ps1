# Bring up infra (postgres, redis, minio), run migrations, then start API, worker, and generateTest UI automatically.
# Usage: from repo root, .\scripts\up-infra.ps1

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
Push-Location $repoRoot
try {
    # 1) Ensure .env exists with host variables (localhost for postgres, redis, minio)
    $envPath = Join-Path $repoRoot ".env"
    if (-not (Test-Path -LiteralPath $envPath)) {
        $exampleHost = Join-Path $repoRoot ".env.example.host"
        if (Test-Path -LiteralPath $exampleHost) {
            Copy-Item -LiteralPath $exampleHost -Destination $envPath
            Write-Host "Created .env from .env.example.host (host variables). Edit .env if needed."
        } else {
            Write-Error ".env not found. Create .env with POSTGRES_HOST=localhost, REDIS_URL=redis://localhost:6379/0, S3_ENDPOINT_URL=http://localhost:9000"
        }
    }

    # 2) Load .env into current process
    & (Join-Path $scriptDir "load-env.ps1") -Path ".env"

    # 3) Ensure .venv and install dependencies
    $venvPath = Join-Path $repoRoot ".venv"
    $venvPython = Join-Path $venvPath "Scripts\python.exe"
    $venvPip = Join-Path $venvPath "Scripts\pip.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating .venv and installing dependencies..."
        python -m venv $venvPath
        & $venvPip install -e ".[worker]"
    }

    # 4) Start infra containers
    Write-Host "Starting postgres, redis, minio..."
    docker compose -f docker-compose.infra.yml up -d
    if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

    # 5) Wait for postgres
    $maxAttempts = 30
    $attempt = 0
    while ($attempt -lt $maxAttempts) {
        $result = docker compose -f docker-compose.infra.yml exec -T postgres pg_isready -U postgres 2>$null
        if ($LASTEXITCODE -eq 0) { break }
        $attempt++
        Write-Host "Waiting for postgres... ($attempt/$maxAttempts)"
        Start-Sleep -Seconds 2
    }
    if ($attempt -ge $maxAttempts) { throw "Postgres did not become ready" }
    Write-Host "Postgres is ready."

    # 6) Create MinIO bucket (run with current env so S3_* are set)
    Write-Host "Creating S3 bucket if needed..."
    $bucketScript = @"
import boto3, os, time
from botocore.exceptions import ClientError
ep, bucket = os.environ.get('S3_ENDPOINT_URL', 'http://localhost:9000'), os.environ.get('S3_BUCKET', 'flow-graph')
for i in range(15):
    try:
        c = boto3.client('s3', endpoint_url=ep, region_name='us-east-1',
                         aws_access_key_id=os.environ.get('S3_ACCESS_KEY_ID', 'minioadmin'),
                         aws_secret_access_key=os.environ.get('S3_SECRET_ACCESS_KEY', 'minioadmin'))
        c.create_bucket(Bucket=bucket)
        print('Bucket', bucket, 'created')
        break
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') in ('BucketAlreadyOwnedByYou', 'BucketAlreadyExists'):
            print('Bucket already exists')
            break
        time.sleep(1)
    except Exception as ex:
        time.sleep(1)
else:
    raise SystemExit('MinIO not ready')
"@
    & $venvPython -c $bucketScript
    if ($LASTEXITCODE -ne 0) { Write-Warning "Bucket creation failed or MinIO not ready; continue anyway." }

    # 7) Run migrations
    Write-Host "Running Alembic migrations..."
    & $venvPython -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "alembic upgrade head failed" }

    # 8) Start API, worker, and generateTest UI (inherit env from this process)
    Write-Host "Starting API (port 8000), worker, and generateTest UI (port 8765)..."
    $apiProc = Start-Process -FilePath $venvPython -ArgumentList "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory $repoRoot -PassThru
    $workerProc = Start-Process -FilePath $venvPython -ArgumentList "-m", "arq", "app.workers.arq_tasks.WorkerSettings" -WorkingDirectory $repoRoot -PassThru
    $uiProc = $null
    $generateTestDir = Join-Path $repoRoot "generateTest"
    if (Test-Path (Join-Path $generateTestDir "run.py")) {
        $uiProc = Start-Process -FilePath $venvPython -ArgumentList "run.py", "--serve" -WorkingDirectory $generateTestDir -PassThru
    } else {
        Write-Warning "generateTest/run.py not found; skipping TestGen UI."
    }

    Write-Host "API:      http://localhost:8000"
    Write-Host "TestGen UI: http://localhost:8765"
    Write-Host "Worker and UI are running in background. Close their windows or stop processes to exit."
} finally {
    Pop-Location
}
