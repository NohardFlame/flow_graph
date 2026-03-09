"""Queue adapters. Fake implementation for tests and Phase 3; real queue in Phase 8."""

from app.adapters.queue.fake_queue import FakeJobQueue

__all__ = ["FakeJobQueue"]
