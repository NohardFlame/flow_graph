"""Worker job payload schema. Minimal payload for queue; do not serialize large objects."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RunJobPayload:
    """Payload for a run processing job. Used when deserializing from queue and in tests."""

    run_id: str
    document_id: str | None = None
    attempt: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "RunJobPayload":
        """Build from queue payload dict. run_id required."""
        run_id = data.get("run_id")
        if not run_id:
            raise ValueError("run_id is required in job payload")
        return cls(
            run_id=str(run_id),
            document_id=str(data["document_id"]) if data.get("document_id") is not None else None,
            attempt=int(data["attempt"]) if data.get("attempt") is not None else 0,
        )

    def to_dict(self) -> dict:
        """Serialize for queue."""
        out: dict = {"run_id": self.run_id}
        if self.document_id is not None:
            out["document_id"] = self.document_id
        if self.attempt != 0:
            out["attempt"] = self.attempt
        return out
