"""ARQ task definitions. Run worker with: arq app.workers.arq_tasks.WorkerSettings

ARQ CLI loads the given symbol and uses its __dict__. Redis and concurrency come from
get_settings() (ENVIRONMENT and REDIS_*, WORKER_* must be set when starting the worker).
"""

import asyncio
from typing import Any

from arq.connections import RedisSettings

from app.config.logging import configure_logging
from app.config.settings import get_settings
from app.workers.tasks import process_run_job as process_run_job_sync

_settings = get_settings()
configure_logging(_settings.observability.log_level)


async def process_run_job(ctx: Any, payload: dict[str, Any]) -> None:
    """ARQ task: run the sync pipeline in an executor."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: process_run_job_sync(payload))


class WorkerSettings:
    """ARQ worker settings. Run: arq app.workers.arq_tasks.WorkerSettings

    Requires: ENVIRONMENT, POSTGRES_*, REDIS_* set. Uses WORKER_CONCURRENCY for max_jobs.
    job_timeout (WORKER_JOB_TIMEOUT_SECONDS) should allow full pipeline for multifile docs.
    """
    functions = [process_run_job]
    redis_settings = RedisSettings.from_dsn(_settings.redis.url)
    max_jobs = _settings.worker.concurrency
    job_timeout = _settings.worker.job_timeout_seconds
