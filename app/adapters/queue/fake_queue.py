"""In-memory fake job queue for tests. Stores enqueued payloads for inspection."""

from typing import Any


class FakeJobQueue:
    """Appends payloads to a list. No network. Tests can inspect enqueued payloads."""

    def __init__(self) -> None:
        self._payloads: list[dict[str, Any]] = []

    def enqueue(self, payload: dict[str, Any]) -> None:
        self._payloads.append(payload)

    def clear(self) -> None:
        self._payloads.clear()

    def payloads(self) -> list[dict[str, Any]]:
        """Return a copy of enqueued payloads for test inspection."""
        return list(self._payloads)
