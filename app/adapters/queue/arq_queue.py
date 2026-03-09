"""ARQ-based job queue adapter. Requires Redis and optional dependency: pip install arq."""

from typing import Any

from app.core.protocols import JobQueueProtocol


# Task name that the ARQ worker will run (must match worker_settings)
RUN_JOB_TASK_NAME = "process_run_job"


class ARQJobQueue:
    """Enqueue run jobs to Redis via ARQ. Use when Redis is available and worker process runs ARQ."""

    def __init__(self, redis_settings: Any = None) -> None:
        """redis_settings: arq.connections.RedisSettings or None to use app config."""
        self._redis_settings = redis_settings

    def enqueue(self, payload: dict[str, Any]) -> None:
        """Serialize payload and enqueue via ARQ. Runs async enqueue in a new event loop."""
        try:
            import asyncio
            from arq import create_pool
            from arq.connections import RedisSettings
        except ImportError as e:
            raise RuntimeError(
                "ARQ queue requires: pip install arq. Then ensure Redis is running."
            ) from e
        redis_settings = self._redis_settings
        if redis_settings is None:
            from app.config.settings import get_settings
            url = get_settings().redis.url
            redis_settings = RedisSettings.from_dsn(url)

        # Payload must have run_id; pass through as-is for worker

        async def _enqueue() -> None:
            redis = await create_pool(redis_settings)
            try:
                await redis.enqueue_job(RUN_JOB_TASK_NAME, payload)
            finally:
                await redis.close()

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if loop.is_running():
            # Caller is already async; cannot block
            raise RuntimeError(
                "ARQJobQueue.enqueue is synchronous; call from sync context or use enqueue_async."
            )
        loop.run_until_complete(_enqueue())

    def ping(self) -> bool:
        """Health check: verify Redis is reachable. Returns True if PING succeeds."""
        try:
            import asyncio
            import redis.asyncio as redis
        except ImportError:
            return False
        from app.config.settings import get_settings
        url = get_settings().redis.url

        async def _ping() -> bool:
            r = redis.from_url(url)
            try:
                await r.ping()
                return True
            except Exception:
                return False
            finally:
                await r.aclose()

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        if loop.is_running():
            return False
        return loop.run_until_complete(_ping())
