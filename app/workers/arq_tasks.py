"""ARQ task definitions. Run worker with: arq app.workers.arq_tasks.WorkerSettings

ARQ CLI loads the given symbol and uses its __dict__ (it does not call a function).
We use defaults at class definition time so the module imports without requiring ENVIRONMENT
(which would run get_settings()). Set ENVIRONMENT and POSTGRES_* when starting the worker
so job execution can load config.
"""

import asyncio
from typing import Any

from arq.connections import RedisSettings

from app.workers.tasks import process_run_job as process_run_job_sync


async def process_run_job(ctx: Any, payload: dict[str, Any]) -> None:
    """ARQ task: run the sync pipeline in an executor."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: process_run_job_sync(payload))


# Defaults at import time so module loads without get_settings() (which requires ENVIRONMENT).
# Override via env: REDIS_URL, and set ENVIRONMENT, POSTGRES_* before starting worker for job execution.
class WorkerSettings:
    """ARQ worker settings. Run: arq app.workers.arq_tasks.WorkerSettings

    Requires: Redis running. Before starting the worker, set ENVIRONMENT and POSTGRES_*
    (and optionally REDIS_URL) so job execution can load config and connect to DB.
    """
    functions = [process_run_job]
    redis_settings = RedisSettings.from_dsn("redis://localhost:6379/0")
    max_jobs = 4
