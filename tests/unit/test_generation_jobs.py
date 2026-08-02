"""Unit tests for generate-from-url job enqueue helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.jobs import generation_jobs


def test_enforce_job_capacity_rejects_when_active_cap_exceeded(monkeypatch):
    monkeypatch.setenv("GENERATE_FROM_URL_MAX_CONCURRENT", "1")
    with patch(
        "src.core.jobs.generation_jobs.count_inflight_jobs",
        return_value={"active": 1, "queued": 0, "total": 1},
    ):
        with pytest.raises(ValueError, match="concurrent"):
            generation_jobs.enforce_job_capacity(additional=1)


def test_enqueue_deduplicates_urls(monkeypatch):
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("JOB_BROKER_URL", "redis://redis:6379/1")
    fake = MagicMock()
    fake.id = "j1"
    with (
        patch(
            "src.core.jobs.generation_jobs.count_inflight_jobs",
            return_value={"active": 0, "queued": 0, "total": 0},
        ),
        patch(
            "src.core.jobs.generation_jobs.generate_from_url_task.delay",
            return_value=fake,
        ) as delay,
    ):
        result = generation_jobs.enqueue_generate_jobs(
            [
                "https://github.com/a/one",
                "https://github.com/a/one",
                " https://github.com/b/two ",
            ],
            no_llm=True,
        )
    assert len(result["jobs"]) == 2
    assert delay.call_count == 2
