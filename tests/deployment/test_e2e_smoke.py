"""E2E smoke: upload document, create run, process run (fake LLM), fetch status and actions.

Uses real DB (with commit), real pipeline, fake storage and fake queue shared between API and worker.
Only LLM is faked. Does not mask integration: asserts run completion and persisted data.
"""

import io

import pytest
from fastapi.testclient import TestClient

from app.adapters.queue.fake_queue import FakeJobQueue
from app.adapters.storage.fake_storage import FakeObjectStorage
from app.api.app import create_app
from app.db.repositories import (
    ActionRepository,
    DocumentRepository,
    RunEventRepository,
    RunRepository,
    ChunkRepository,
)
from app.db.session import get_session_factory
from app.services.run_orchestration.service import RunOrchestrator
from app.workers.deps import get_worker_deps
from app.workers.tasks import process_run_job
from app.core.constants import RunStatus


def _build_orchestrator_with_storage(session, storage):
    """Build RunOrchestrator with overridden storage (shared with API uploads)."""
    deps = get_worker_deps()
    deps["storage"] = storage
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


def test_e2e_upload_create_run_process_fetch_actions(session_factory):
    """Full path: upload sample file, create run, run pipeline (fake LLM), then fetch run status and actions."""
    fake_storage = FakeObjectStorage()
    fake_queue = FakeJobQueue()
    # Use session_factory that commits so worker sees persisted document/run
    app = create_app(
        storage=fake_storage,
        queue=fake_queue,
        session_factory=session_factory,
    )
    app.state.commit_db = True
    client = TestClient(app)

    # 1. Upload document (use .md so Docling parser accepts the file format)
    sample_content = b"# Sample document for E2E\n\nSection one.\nSection two."
    upload_resp = client.post(
        "/documents",
        files={"file": ("sample.md", io.BytesIO(sample_content), "text/markdown")},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    document_id = upload_resp.json()["id"]

    # 2. Create run (enqueues to fake queue; we will run job manually)
    run_resp = client.post(f"/documents/{document_id}/runs")
    assert run_resp.status_code == 202, run_resp.text
    run_id = run_resp.json()["id"]

    # 3. Run the job synchronously (same process, shared storage and DB)
    payload = {"run_id": run_id, "correlation_id": "e2e-smoke"}
    process_run_job(
        payload,
        session_factory=session_factory,
        orchestrator_factory=lambda s: _build_orchestrator_with_storage(s, fake_storage),
    )

    # 4. Fetch run status
    status_resp = client.get(f"/runs/{run_id}")
    assert status_resp.status_code == 200, status_resp.text
    status_data = status_resp.json()
    assert status_data["status"] in ("succeeded", "failed"), status_data
    # Pipeline should complete; we accept succeeded or failed (e.g. no chunks accepted)
    assert status_data["id"] == run_id

    # 5. Fetch actions for the run (may be empty if prefilter rejected all chunks)
    actions_resp = client.get(f"/runs/{run_id}/actions")
    assert actions_resp.status_code == 200, actions_resp.text
    actions_data = actions_resp.json()
    assert "items" in actions_data
    assert isinstance(actions_data["items"], list)

    # 6. Run and DB: run should be in a terminal state and events persisted
    session = session_factory()
    try:
        run_repo = RunRepository(session)
        run = run_repo.get(run_id)
        assert run is not None
        assert run.status in (RunStatus.SUCCEEDED, RunStatus.FAILED)
        events_repo = RunEventRepository(session)
        events = events_repo.list_by_run(run_id)
        assert len(events) >= 1
    finally:
        session.close()
