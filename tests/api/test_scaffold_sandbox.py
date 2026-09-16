"""POST /okh/scaffold and /okh/scaffold/cleanup only write inside a
configured workspace (#512).

Both routes used to resolve a caller-supplied path (`output_path` /
`project_path`) directly against the filesystem, unsandboxed — an
anonymous caller (until #485) or any authenticated one (after) could write
a file anywhere the API process could write, or delete any empty-or-stub-
matching file/directory anywhere it could reach.

These drive the real routes end-to-end (no service mocking) against a real
`tmp_path`, because "is the sandbox actually wired into both routes" is not
something a unit test of `resolve_scaffold_path` alone can answer.
"""

from __future__ import annotations

import os
import sys

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

pytestmark = pytest.mark.contract


def _app() -> FastAPI:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app


async def _post(path: str, body: dict) -> httpx.Response:
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        return await client.post(path, json=body)


@pytest.mark.asyncio
async def test_scaffold_refuses_when_no_workspace_is_configured(monkeypatch):
    monkeypatch.delenv("SCAFFOLD_OUTPUT_ROOT", raising=False)

    resp = await _post(
        "/v1/api/okh/scaffold",
        {
            "project_name": "widget",
            "output_format": "filesystem",
            "output_path": "/tmp/whatever",
        },
    )

    assert resp.status_code == 422, resp.text
    assert "SCAFFOLD_OUTPUT_ROOT" in resp.text


@pytest.mark.asyncio
async def test_scaffold_refuses_a_path_outside_the_workspace(tmp_path, monkeypatch):
    root = tmp_path / "ohm-scaffolds"
    root.mkdir()
    monkeypatch.setenv("SCAFFOLD_OUTPUT_ROOT", str(root))

    outside = tmp_path / "elsewhere"
    resp = await _post(
        "/v1/api/okh/scaffold",
        {
            "project_name": "widget",
            "output_format": "filesystem",
            "output_path": str(outside),
        },
    )

    assert resp.status_code == 422, resp.text
    assert not outside.exists(), "must not have written outside the workspace"


@pytest.mark.asyncio
async def test_scaffold_writes_inside_a_configured_workspace(tmp_path, monkeypatch):
    root = tmp_path / "ohm-scaffolds"
    root.mkdir()
    monkeypatch.setenv("SCAFFOLD_OUTPUT_ROOT", str(root))

    resp = await _post(
        "/v1/api/okh/scaffold",
        {
            "project_name": "widget",
            "output_format": "filesystem",
            "output_path": str(root),
        },
    )

    assert resp.status_code == 200, resp.text
    assert (root / "widget").is_dir()


@pytest.mark.asyncio
async def test_cleanup_refuses_when_no_workspace_is_configured(monkeypatch):
    monkeypatch.delenv("SCAFFOLD_OUTPUT_ROOT", raising=False)

    resp = await _post(
        "/v1/api/okh/scaffold/cleanup",
        {"project_path": "/tmp/whatever", "dry_run": True},
    )

    assert resp.status_code == 422, resp.text
    assert "SCAFFOLD_OUTPUT_ROOT" in resp.text


@pytest.mark.asyncio
async def test_cleanup_refuses_a_path_outside_the_workspace(tmp_path, monkeypatch):
    root = tmp_path / "ohm-scaffolds"
    root.mkdir()
    monkeypatch.setenv("SCAFFOLD_OUTPUT_ROOT", str(root))

    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "canary.txt").write_text("do not touch")

    resp = await _post(
        "/v1/api/okh/scaffold/cleanup",
        {"project_path": str(outside), "dry_run": False},
    )

    assert resp.status_code == 422, resp.text
    assert (outside / "canary.txt").exists(), "must not have touched the outside path"
