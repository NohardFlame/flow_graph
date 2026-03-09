"""Build run orchestrator and worker deps from settings. Used by worker entrypoint."""

from pathlib import Path
from typing import Any

from app.adapters.parser.docling_adapter import DoclingParserAdapter
from app.adapters.storage.fake_storage import FakeObjectStorage
from app.config.settings import get_settings
from app.core.normalization_config import load_normalization_config
from app.services.chunk_assembler import ChunkAssembler
from app.services.prefilter.service import PrefilterService
from app.services.run_orchestration.service import RunOrchestrator

# Lazy imports for optional/LLM deps. Default returns empty drafts so pipeline completes without real LLM.
def _default_llm_adapter() -> Any:
    from app.adapters.llm.fake_llm_adapter import FakeLLMAdapter
    # Return empty drafts so multiple chunks don't exhaust the queue
    return FakeLLMAdapter(extraction_responses=["[]"] * 1000)


def _default_id_generator() -> Any:
    import uuid
    class _IdGen:
        def generate(self) -> str:
            return str(uuid.uuid4())
    return _IdGen()


def _default_clock() -> Any:
    from datetime import datetime, timezone
    class _Clock:
        def now(self):
            return datetime.now(timezone.utc)
    return _Clock()


def get_worker_deps() -> dict[str, Any]:
    """Return non-session deps for RunOrchestrator. Uses get_settings()."""
    settings = get_settings()
    base = Path(settings.normalization.config_dir)
    if not base.is_absolute():
        base = Path.cwd() / base
    norm_config = load_normalization_config(base, require_dir=False)

    prefilter_base = Path(settings.prefilter.lexicon_dir)
    if not prefilter_base.is_absolute():
        prefilter_base = Path.cwd() / prefilter_base

    return {
        "storage": FakeObjectStorage(),
        "parser_factory": lambda document_id, run_id: DoclingParserAdapter(document_id=document_id, run_id=run_id),
        "chunk_assembler": ChunkAssembler(),
        "prefilter_service": PrefilterService(lexicon_dir=str(prefilter_base)),
        "llm_adapter": _default_llm_adapter(),
        "normalization_config": norm_config,
        "id_generator": _default_id_generator(),
        "clock": _default_clock(),
        "max_extract_retries": settings.litellm.max_retries,
        "extraction_prompt_cfg": {"prompt_version": "v1", "schema_version": "v1"},
    }


def build_orchestrator(session: Any) -> RunOrchestrator:
    """Build RunOrchestrator with repos from session and other deps from get_worker_deps()."""
    from app.db.repositories import (
        ActionRepository,
        ChunkRepository,
        DocumentRepository,
        RunEventRepository,
        RunRepository,
    )
    deps = get_worker_deps()
    return RunOrchestrator(
        run_repo=RunRepository(session),
        document_repo=DocumentRepository(session),
        chunk_repo=ChunkRepository(session),
        action_repo=ActionRepository(session),
        run_event_repo=RunEventRepository(session),
        storage=deps["storage"],
        parser_factory=deps["parser_factory"],
        chunk_assembler=deps["chunk_assembler"],
        prefilter_service=deps["prefilter_service"],
        llm_adapter=deps["llm_adapter"],
        normalization_config=deps["normalization_config"],
        id_generator=deps["id_generator"],
        clock=deps["clock"],
        max_extract_retries=deps["max_extract_retries"],
        extraction_prompt_cfg=deps["extraction_prompt_cfg"],
    )
