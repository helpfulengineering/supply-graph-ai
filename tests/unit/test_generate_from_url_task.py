"""Celery generate-from-url task — behaviour through the public task API (eager)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def eager_celery(monkeypatch):
    """Run Celery tasks in-process without a broker."""
    monkeypatch.setenv("JOB_BROKER_URL", "memory://")
    monkeypatch.setenv("JOB_RESULT_BACKEND", "cache+memory://")
    from src.core.jobs.celery_app import celery_app

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    return celery_app


def test_generate_from_url_task_returns_success_payload(eager_celery):
    from src.core.jobs.tasks import generate_from_url_task

    fake_result = {
        "success": True,
        "message": "Manifest generated successfully",
        "manifest": {"title": "Demo"},
        "quality_report": {"score": 0.9},
    }
    with patch(
        "src.core.jobs.tasks._run_generate_from_url",
        new=AsyncMock(return_value=fake_result),
    ):
        async_result = generate_from_url_task.delay(
            url="https://github.com/example/demo",
            skip_review=True,
            verbose=False,
            clone=True,
            no_llm=True,
        )
    assert async_result.successful()
    payload = async_result.result
    assert payload["success"] is True
    assert payload["manifest"]["title"] == "Demo"
    assert payload["url"] == "https://github.com/example/demo"


def test_generate_from_url_task_failure_is_marked_failed(eager_celery):
    from src.core.jobs.tasks import generate_from_url_task

    eager_celery.conf.task_eager_propagates = False
    with patch(
        "src.core.jobs.tasks._run_generate_from_url",
        new=AsyncMock(side_effect=ValueError("unsupported platform")),
    ):
        async_result = generate_from_url_task.delay(
            url="https://example.com/not-a-repo",
            no_llm=True,
        )
    assert async_result.failed()
    assert isinstance(async_result.result, ValueError)
    assert "unsupported platform" in str(async_result.result)


def test_celery_app_expires_results(eager_celery):
    assert eager_celery.conf.result_expires == 24 * 60 * 60


def test_job_settings_read_from_env(monkeypatch):
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("JOB_BROKER_URL", "redis://broker:6379/1")
    monkeypatch.setenv("JOB_RESULT_BACKEND", "redis://broker:6379/2")
    from src.config.schema import get_settings

    settings = get_settings()
    assert settings.jobs_enabled is True
    assert settings.job_broker_url == "redis://broker:6379/1"
    assert settings.job_result_backend == "redis://broker:6379/2"
