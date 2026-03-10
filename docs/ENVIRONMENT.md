# Environment contract

All configuration is driven by environment variables. No secrets are baked into the image.

## Quick setup (local)

1. Copy the example env file and edit it:  
   `copy .env.example .env`  
   (`.env` is in `.gitignore` and will not be committed.)
2. Load variables into your shell (PowerShell, from repo root):  
   `. .\scripts\load-env.ps1`
3. Run migrations, then start the API and worker (see below).

## Tiers

- `local` — local development (Compose or bare metal)
- `test` — pytest and CI (use test DB; can set `USE_FAKE_ADAPTERS=1` to avoid S3/Redis)
- `staging` — pre-production
- `prod` — production

Optional modules (e.g. Qdrant) are disabled by default in all tiers.

---

## Required

| Variable | Description |
|----------|-------------|
| `ENVIRONMENT` | One of: `local`, `test`, `staging`, `prod`. Required; missing value causes API and worker to exit non-zero. |
| `POSTGRES_HOST` | PostgreSQL host (default: `localhost`) |
| `POSTGRES_PORT` | PostgreSQL port (default: `5432`) |
| `POSTGRES_USER` | PostgreSQL user (default: `postgres`) |
| `POSTGRES_PASSWORD` | PostgreSQL password (default: empty) |
| `POSTGRES_DB` | Database name (default: `app`) |

For production-like runs (API and worker with real queue):

| Variable | Description |
|----------|-------------|
| `REDIS_URL` | Redis DSN (default: `redis://localhost:6379/0`) |

---

## Optional (by group)

### API and adapters

| Variable | Description |
|----------|-------------|
| `USE_FAKE_ADAPTERS` | Set to `1` or `true` to use in-memory storage and queue instead of S3/Redis. Use for local dev without MinIO/Redis. |
| `API_HOST` | Bind host (default: `0.0.0.0`) |
| `API_PORT` | Bind port (default: `8000`) |
| `S3_ENDPOINT_URL` | S3-compatible endpoint (default: `http://localhost:9000`) |
| `S3_BUCKET` | Bucket name (default: `flow-graph`) |
| `S3_KEY_PREFIX` | Optional key prefix |
| `S3_ACCESS_KEY_ID` | Access key for S3/MinIO (or set `AWS_ACCESS_KEY_ID`) |
| `S3_SECRET_ACCESS_KEY` | Secret key for S3/MinIO (or set `AWS_SECRET_ACCESS_KEY`) |

### Worker

| Variable | Description |
|----------|-------------|
| `WORKER_CONCURRENCY` | Max concurrent jobs (default: `2`) |
| `WORKER_QUEUE_NAME` | Queue name (default: `default`) |

### LLM and features

| Variable | Description |
|----------|-------------|
| `LITELLM_API_KEY` | **Required for API-key providers.** OpenAI, Anthropic, or Google AI Studio (Gemini) API key. If unset, worker uses a fake LLM (empty extractions). Not used for Vertex AI — see below. |
| `LITELLM_MODEL` | Model name (default: `gpt-4o-mini`). Use `openai/...`, `anthropic/...`, or **`gemini/gemini-...`** for Google AI Studio (API key); use `vertex_ai/...` only when ADC is set up. **For Gemini you must use the `gemini/` prefix and the API model ID** (e.g. `gemini/gemini-2.5-flash`, `gemini/gemini-3.1-flash-lite-preview`), not the display name (e.g. "Gemini 3.1 Flash Lite" causes 400 "unexpected model name format"). |
| `LITELLM_BASE_URL` | Optional base URL for compatible API (e.g. OpenAI-compatible proxy). |
| `LITELLM_*` | Also: `fallback_model`, `max_retries`, `request_timeout`, `repair_max_attempts`, `extraction_delay_seconds` (default `2.0` — seconds between chunk LLM calls to avoid 429 on free tier). |

**Vertex AI** (models `vertex_ai/...`) does **not** use `LITELLM_API_KEY`. It uses [Google Application Default Credentials (ADC)](https://cloud.google.com/docs/authentication/external/set-up-adc). Either:

- Set `GOOGLE_APPLICATION_CREDENTIALS` to the path of a service account JSON key file, or  
- Run `gcloud auth application-default login` (for local dev with your user account).

If you have a **Google AI Studio API key**, use model **`gemini/gemini-2.5-pro`** (or e.g. `gemini/gemini-2.5-flash`) and set `LITELLM_API_KEY` to that key. The `gemini/` prefix is required so LiteLLM uses the API key; without it, LiteLLM treats the model as Vertex AI and requires ADC.

**429 with "limit: 0":** If the error says **`limit: 0`** for `gemini-2.5-pro` free-tier metrics, your project has **no free-tier quota** for that model (e.g. region or account not eligible). Use a model that has quota: **`gemini/gemini-2.5-flash`** or **`gemini/gemini-2.0-flash`** (both have free tier in more regions). Delays and retries will not help when limit is 0.

**429 with rate limit (non-zero limit):** If you exceed requests per minute, the worker waits between chunks (`LITELLM_EXTRACTION_DELAY_SECONDS`, default 2) and retries on 429 with a 15s backoff. Increase the delay if you still hit 429.

**Multiple requests at once:** The worker runs up to **`WORKER_CONCURRENCY`** jobs in parallel (default **2**). So two runs can be in the extraction step at the same time and send LLM requests simultaneously. For rate-limited APIs (e.g. Gemini free tier), set **`WORKER_CONCURRENCY=1`** so only one job runs at a time and the per-chunk delay is effective.

| `PREFILTER_*` | Prefilter weights and thresholds |
| `NORMALIZATION_*` | Config dir, version |
| `ENABLE_QDRANT` | Enable Qdrant indexing (default: off) |
| `ENABLE_LLM_CACHE` | Enable LLM response caching |
| `ENABLE_PREFILTER_DEBUG_FIELDS` | Include debug fields in prefilter output |
| `OBS_*` | Log level, `OBS_ENABLE_DEBUG_ARTIFACTS`, timeouts |

### Qdrant (optional module)

| Variable | Description |
|----------|-------------|
| `QDRANT_ENABLED` | Enable Qdrant (default: off) |
| `QDRANT_URL` | Qdrant URL (default: `http://localhost:6333`) |

---

## Migration startup plan

1. Ensure PostgreSQL is running and the target database exists (e.g. `createdb app` or create via Compose).
2. Set `ENVIRONMENT` and all `POSTGRES_*` variables for the target environment.
3. Run migrations:  
   `python -m alembic upgrade head`  
   (or inside the API image:  
   `docker compose run --rm api python -m alembic upgrade head`.)
4. Start the API and worker after migrations have been applied.

In Docker Compose, you can add a one-off migration service that runs `alembic upgrade head` and exits; make `api` and `worker` depend on it so migrations run before app processes start.

---

## Worker startup plan

1. Set `ENVIRONMENT`, `POSTGRES_*`, and `REDIS_*` (and optionally `S3_*` if not using fakes).
2. Start the worker:  
   `arq app.workers.arq_tasks.WorkerSettings`  
   (or with Python module:  
   `python -m arq app.workers.arq_tasks.WorkerSettings`.)
3. Optional: set `WORKER_CONCURRENCY` to control max concurrent jobs.

The worker loads settings at import time; invalid or missing required config causes non-zero exit.

---

## Run full pipeline from console (no container)

To run the full pipeline on your machine without Docker for the app (you can still use Docker for Postgres/Redis only):

1. **Prerequisites**
   - Python 3.12+ with project deps installed (e.g. `pip install -e ".[dev]"`).
   - PostgreSQL running; database created (e.g. `createdb app`).
   - Redis running (required so the API can enqueue jobs and the worker can consume them).
   - **S3-compatible storage** (e.g. MinIO). Without it you get "Unable to locate credentials". Run MinIO (e.g. `docker run -p 9000:9000 minio/minio server /data`), create a bucket named `flow-graph`, and set credentials (see below).

2. **Environment (PowerShell example)**

   ```powershell
   $env:ENVIRONMENT = "local"
   $env:POSTGRES_HOST = "localhost"
   $env:POSTGRES_PORT = "5432"
   $env:POSTGRES_USER = "postgres"
   $env:POSTGRES_PASSWORD = "your_db_password"
   $env:POSTGRES_DB = "app"
   $env:REDIS_URL = "redis://localhost:6379/0"
   # S3/MinIO (required for uploads unless using fake adapters in single-process tests)
   $env:S3_ENDPOINT_URL = "http://localhost:9000"
   $env:S3_ACCESS_KEY_ID = "minioadmin"
   $env:S3_SECRET_ACCESS_KEY = "minioadmin"
   # Optional: use in-memory storage/queue only (no S3/MinIO) — then API and worker must share the same process; see note below.
   # $env:USE_FAKE_ADAPTERS = "1"
   ```

   For **real LLM** extraction (otherwise the worker uses a fake LLM and returns no actions):

   - **OpenAI / Anthropic / Gemini API (Google AI Studio):** set `LITELLM_API_KEY` and optionally `LITELLM_MODEL`:

   ```powershell
   $env:LITELLM_API_KEY = "sk-..."   # OpenAI, Anthropic, or Google AI Studio key
   $env:LITELLM_MODEL = "gpt-4o-mini"   # or anthropic/claude-..., or gemini/gemini-2.5-pro for AI Studio
   # $env:LITELLM_BASE_URL = "https://..."   # optional, for custom endpoint
   ```
   For **Google AI Studio (Gemini)** with an API key, use the **`gemini/`** prefix: `gemini/gemini-2.5-pro`. Without the prefix, LiteLLM uses Vertex AI and will ask for GCP credentials instead of the key.

   - **Vertex AI** (e.g. `vertex_ai/gemini-...`): do **not** rely on `LITELLM_API_KEY`. Set up [Application Default Credentials](https://cloud.google.com/docs/authentication/external/set-up-adc), e.g.:

   ```powershell
   $env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\service-account-key.json"
   $env:LITELLM_MODEL = "vertex_ai/gemini-1.5-flash-001"
   ```
   Or run `gcloud auth application-default login` and set `LITELLM_MODEL` to your Vertex model.

3. **Migrations**

   ```powershell
   python -m alembic upgrade head
   ```

4. **Start API and worker in two terminals** (same env in both).

   Terminal 1 — API:

   ```powershell
   uvicorn app.api.main:app --host 0.0.0.0 --port 8000
   ```

   Terminal 2 — Worker:

   ```powershell
   python -m arq app.workers.arq_tasks.WorkerSettings
   ```

5. **Run the pipeline**

   - Upload a document: `POST /documents` with a `file` (e.g. PDF or `.md`).
   - Create a run: `POST /documents/{document_id}/runs` → returns `run_id` and enqueues the job.
   - The worker picks the job and runs the pipeline (parse → chunks → prefilter → LLM extraction → actions).
   - Poll run status: `GET /runs/{run_id}`; fetch actions: `GET /runs/{run_id}/actions`.

   Example (after starting API and worker):

   ```powershell
   # Upload (adjust path as needed)
   curl -X POST http://localhost:8000/documents -F "file=@sample.pdf"
   # Create run (use document_id from response)
   curl -X POST http://localhost:8000/documents/{document_id}/runs
   # Status and actions
   curl http://localhost:8000/runs/{run_id}
   curl http://localhost:8000/runs/{run_id}/actions
   ```

   **Note:** With `USE_FAKE_ADAPTERS=1`, storage and queue are in-memory and not shared across processes. Use it only for single-process tests (e.g. pytest). For a full console run, use real Redis (and optionally S3 or MinIO) so the API and worker communicate via the queue and storage.

---

## Secrets strategy

- **Secrets** (DB password, Redis URL, S3 credentials, LLM API key) are **never** baked into the image.
- Provide them at runtime via:
  - **Compose**: `environment` or `env_file` (e.g. `.env` not committed).
  - **Production**: Orchestrator secret injection (e.g. Kubernetes secrets, AWS Secrets Manager) mapped to the same env var names.
- Use least-privilege access for DB, Redis, and buckets; prefer private network placement.
