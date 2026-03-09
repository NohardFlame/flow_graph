"""LLM call audit persistence."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LLMCall


class LLMCallRepository:
    """Persistence for LLM call audit records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, llm_call: LLMCall) -> LLMCall:
        self._session.add(llm_call)
        self._session.flush()
        return llm_call

    def get(self, llm_call_id: str) -> LLMCall | None:
        return self._session.get(LLMCall, llm_call_id)

    def list_by_run(self, run_id: str) -> list[LLMCall]:
        result = self._session.execute(select(LLMCall).where(LLMCall.run_id == run_id).order_by(LLMCall.id))
        return list(result.scalars().all())
