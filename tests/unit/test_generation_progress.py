"""Behaviour tests for generate-from-url progress reporting."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.generation.progress import ProgressEmitter, planned_stages


def test_progress_is_monotonic_and_reaches_one():
    events: list[tuple[str, float]] = []
    stages = planned_stages(include_clone=True, use_llm=True)
    emitter = ProgressEmitter(
        stages,
        callback=lambda stage, fraction, message: events.append((stage, fraction)),
    )
    for stage in stages:
        emitter.emit(stage, message=f"Running {stage}")

    fractions = [f for _, f in events]
    assert fractions == sorted(fractions)
    assert fractions[0] > 0
    assert fractions[-1] == pytest.approx(1.0)
    assert "llm" in {s for s, _ in events}


def test_progress_without_llm_skips_llm_and_still_reaches_one():
    events: list[tuple[str, float]] = []
    stages = planned_stages(include_clone=True, use_llm=False)
    emitter = ProgressEmitter(
        stages,
        callback=lambda stage, fraction, message: events.append((stage, fraction)),
    )
    for stage in stages:
        emitter.emit(stage)

    assert "llm" not in {s for s, _ in events}
    assert events[-1][1] == pytest.approx(1.0)
    with_llm = ProgressEmitter(planned_stages(use_llm=True))
    without = ProgressEmitter(planned_stages(use_llm=False))
    assert without.fraction_for("nlp") > with_llm.fraction_for("nlp")


def test_progress_emitter_writes_processing_logs():
    from src.core.generation.models import GenerationMetadata

    meta = GenerationMetadata()
    emitter = ProgressEmitter(["direct", "quality"], metadata=meta)
    emitter.emit("direct", "Direct mapping")
    emitter.emit("quality", "Quality report")
    assert len(meta.processing_logs) == 2
    assert "direct" in meta.processing_logs[0]


@pytest.mark.asyncio
async def test_generate_manifest_async_reports_monotonic_progress():
    from src.core.generation.engine import GenerationEngine
    from src.core.generation.models import LayerConfig, PlatformType, ProjectData

    events: list[tuple[str, float, str | None]] = []

    def on_progress(stage: str, fraction: float, message: str | None = None) -> None:
        events.append((stage, fraction, message))

    config = LayerConfig(
        use_direct=True,
        use_heuristic=True,
        use_nlp=False,
        use_llm=False,
        use_bom_normalization=False,
        verify_bom_github_raw=False,
        progressive_enhancement=True,
    )
    engine = GenerationEngine(config=config)
    project = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/example/demo",
        metadata={"name": "demo", "description": "A demo project"},
        files=[],
        documentation=[],
        raw_content={},
    )

    result = await engine.generate_manifest_async(project, progress=on_progress)

    assert result is not None
    assert events, "expected progress callbacks during generation"
    fractions = [f for _, f, _ in events]
    assert fractions == sorted(fractions)
    assert fractions[-1] == pytest.approx(1.0)
    stage_names = [s for s, _, _ in events]
    assert "direct" in stage_names
    assert "heuristic" in stage_names
    assert "quality" in stage_names
    assert "llm" not in stage_names
    # The run's own record of what it did. This used to be a list of formatted
    # strings on project.metadata that nothing but this assertion read; it is
    # now the structured timeline the provenance sidecar renders.
    assert result.stage_events, "expected the run to record its stages"
    assert any(event["stage"] == "direct" for event in result.stage_events)
    recorded = [event["fraction"] for event in result.stage_events]
    assert recorded == sorted(recorded)


def test_celery_task_forwards_progress_via_update_state(monkeypatch):
    monkeypatch.setenv("JOB_BROKER_URL", "memory://")
    monkeypatch.setenv("JOB_RESULT_BACKEND", "cache+memory://")
    from src.core.jobs.celery_app import celery_app
    from src.core.jobs.tasks import generate_from_url_task

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    async def fake_run(**kwargs):
        progress = kwargs.get("progress")
        assert callable(progress)
        progress("clone", 0.2, "Cloning repository")
        progress("nlp", 0.6, "Running NLP")
        return {
            "success": True,
            "message": "ok",
            "manifest": {"title": "Demo"},
            "quality_report": {},
        }

    updates: list[dict] = []

    def capture_update(state=None, meta=None, **_kwargs):
        updates.append({"state": state, "meta": meta})

    with (
        patch(
            "src.core.jobs.tasks._run_generate_from_url",
            new=AsyncMock(side_effect=fake_run),
        ),
        patch.object(generate_from_url_task, "update_state", capture_update),
    ):
        result = generate_from_url_task.run(
            "https://github.com/example/demo",
            no_llm=True,
        )

    assert result["success"] is True
    assert len(updates) >= 2
    assert updates[0]["state"] == "PROGRESS"
    assert updates[0]["meta"]["stage"] == "clone"
    assert updates[0]["meta"]["fraction"] == 0.2
    assert updates[1]["meta"]["stage"] == "nlp"


def test_get_job_status_surfaces_progress_meta():
    from src.core.jobs import generation_jobs

    fake = MagicMock()
    fake.state = "PROGRESS"
    fake.info = {
        "stage": "llm",
        "fraction": 0.72,
        "message": "Running LLM",
        "url": "https://github.com/a/b",
    }
    fake.result = None

    with patch("src.core.jobs.generation_jobs.AsyncResult", return_value=fake):
        payload = generation_jobs.get_job_status("job-xyz")

    assert payload["state"] == "PROGRESS"
    assert payload["stage"] == "llm"
    assert payload["fraction"] == 0.72
    assert payload["message"] == "Running LLM"
    assert payload["manifest"] is None


def test_revoke_job_calls_celery_control():
    from src.core.jobs import generation_jobs

    with patch.object(generation_jobs.celery_app.control, "revoke") as revoke:
        generation_jobs.revoke_job("job-xyz")
    revoke.assert_called_once_with("job-xyz", terminate=True, signal="SIGTERM")
