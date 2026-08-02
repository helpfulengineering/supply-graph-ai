"""Contract tests for async generate-from-url jobs."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


@pytest.mark.asyncio
@pytest.mark.contract
async def test_submit_jobs_returns_batch_and_job_ids(monkeypatch):
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("JOB_BROKER_URL", "memory://")
    monkeypatch.setenv("JOB_RESULT_BACKEND", "cache+memory://")

    fake_async = MagicMock()
    fake_async.id = "job-111"

    with patch(
        "src.core.jobs.generation_jobs.generate_from_url_task.delay",
        return_value=fake_async,
    ) as delay:
        app, _ = _get_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/okh/generate-from-url/jobs",
                json={
                    "urls": [
                        "https://github.com/a/one",
                        "https://github.com/b/two",
                    ],
                    "no_llm": True,
                },
            )

    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert "batch_id" in body
    assert len(body["jobs"]) == 2
    assert {j["url"] for j in body["jobs"]} == {
        "https://github.com/a/one",
        "https://github.com/b/two",
    }
    assert all(j["job_id"] == "job-111" for j in body["jobs"])
    assert delay.call_count == 2


@pytest.mark.asyncio
@pytest.mark.contract
async def test_get_job_status_returns_success_payload(monkeypatch):
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("JOB_BROKER_URL", "redis://redis:6379/1")

    with patch(
        "src.core.jobs.generation_jobs.get_job_status",
        return_value={
            "job_id": "job-111",
            "state": "SUCCESS",
            "stage": None,
            "fraction": 1.0,
            "message": "Manifest generated successfully",
            "url": "https://github.com/a/one",
            "error": None,
            "manifest": {"title": "One"},
            "quality_report": {"score": 0.5},
        },
    ):
        app, _ = _get_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get("/v1/api/okh/generate-from-url/jobs/job-111")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["state"] == "SUCCESS"
    assert body["manifest"]["title"] == "One"
    assert body["fraction"] == 1.0


@pytest.mark.asyncio
@pytest.mark.contract
async def test_submit_jobs_disabled_returns_503(monkeypatch):
    monkeypatch.setenv("JOBS_ENABLED", "false")
    app, _ = _get_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/v1/api/okh/generate-from-url/jobs",
            json={"urls": ["https://github.com/a/one"], "no_llm": True},
        )
    assert resp.status_code == 503, resp.text


@pytest.mark.asyncio
@pytest.mark.contract
async def test_submit_jobs_rate_limited(monkeypatch):
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("JOB_BROKER_URL", "redis://redis:6379/1")
    monkeypatch.setenv("GENERATE_FROM_URL_RATE_LIMIT_PER_MINUTE", "1")

    from src.core.services.rate_limit_service import get_rate_limit_service

    get_rate_limit_service()._request_timestamps.clear()

    fake_async = MagicMock()
    fake_async.id = "job-111"
    with (
        patch(
            "src.core.jobs.generation_jobs.generate_from_url_task.delay",
            return_value=fake_async,
        ),
        patch(
            "src.core.jobs.generation_jobs.count_inflight_jobs",
            return_value={"active": 0, "queued": 0, "total": 0},
        ),
    ):
        app, _ = _get_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            first = await client.post(
                "/v1/api/okh/generate-from-url/jobs",
                json={"urls": ["https://github.com/a/one"], "no_llm": True},
            )
            second = await client.post(
                "/v1/api/okh/generate-from-url/jobs",
                json={"urls": ["https://github.com/a/two"], "no_llm": True},
            )
    assert first.status_code == 202, first.text
    assert second.status_code == 429, second.text


@pytest.mark.asyncio
@pytest.mark.contract
async def test_llm_generation_requires_auth_when_flag_set(monkeypatch):
    monkeypatch.setenv("GENERATE_FROM_URL_REQUIRE_AUTH_FOR_LLM", "true")
    monkeypatch.setenv("JOBS_ENABLED", "true")
    monkeypatch.setenv("JOB_BROKER_URL", "redis://redis:6379/1")

    app, _ = _get_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/v1/api/okh/generate-from-url/jobs",
            json={"urls": ["https://github.com/a/one"], "no_llm": False},
        )
    assert resp.status_code == 401, resp.text
