"""Queue adapters. Fake for tests; ARQ for production when Redis is available."""

from app.adapters.queue.fake_queue import FakeJobQueue

__all__ = ["FakeJobQueue"]

# Optional: from app.adapters.queue.arq_queue import ARQJobQueue
# Use ARQJobQueue when Redis is running and worker is started: arq app.workers.arq_tasks.WorkerSettings
