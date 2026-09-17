"""POST /api/package/pull only writes inside a configured workspace (#521).

The route used to resolve a caller-supplied `output_dir` directly — nothing
constrained where it could point, so any credentialed caller (`require_write`,
#478) could still direct an arbitrary filesystem write anywhere the API
process could reach. `resolve_package_pull_path` (`remote_storage.py`) now
gates it, same shape as #512's scaffold sandbox.

These drive the real route end-to-end (no service mocking beyond the auth
dependency) against a real `tmp_path`, because "is the sandbox actually
wired into the route, and does the safe default stay ungated" is not
something a unit test of the resolver alone can answer. The sandbox check
runs before any remote lookup, so a refusal never depends on whether the
named package actually exists; the pass-through cases use a nonexistent
package deliberately, to prove the request got *past* the sandbox by
failing for an unrelated (not-found) reason instead of a permission one.
"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

pytestmark = pytest.mark.contract


def _app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


def _writer_user():
    from src.core.models.auth import AuthenticatedUser

    return AuthenticatedUser(key_id=uuid4(), name="writer", permissions=["write"])


async def _pull(app: FastAPI, body: dict) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        return await client.post("/v1/api/package/pull", json=body)


@pytest.mark.asyncio
async def test_refuses_when_no_workspace_is_configured(monkeypatch):
    from src.core.api.dependencies import require_write

    monkeypatch.delenv("PACKAGE_PULL_OUTPUT_ROOT", raising=False)
    app, api_v1 = _app()
    api_v1.dependency_overrides[require_write] = _writer_user

    resp = await _pull(
        app, {"package_name": "o/p", "version": "1.0.0", "output_dir": "/tmp/whatever"}
    )

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 422, resp.text
    assert "PACKAGE_PULL_OUTPUT_ROOT" in resp.text


@pytest.mark.asyncio
async def test_refuses_a_path_outside_the_workspace(tmp_path, monkeypatch):
    from src.core.api.dependencies import require_write

    root = tmp_path / "ohm-packages"
    root.mkdir()
    monkeypatch.setenv("PACKAGE_PULL_OUTPUT_ROOT", str(root))
    outside = tmp_path / "elsewhere"

    app, api_v1 = _app()
    api_v1.dependency_overrides[require_write] = _writer_user

    resp = await _pull(
        app, {"package_name": "o/p", "version": "1.0.0", "output_dir": str(outside)}
    )

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 422, resp.text
    assert not outside.exists(), "must not have written outside the workspace"


@pytest.mark.asyncio
async def test_a_path_inside_the_workspace_passes_the_sandbox(tmp_path, monkeypatch):
    """Proves the sandbox let the request through by failing for an
    unrelated (not-found) reason, not a permission one."""
    from src.core.api.dependencies import require_write

    root = tmp_path / "ohm-packages"
    root.mkdir()
    monkeypatch.setenv("PACKAGE_PULL_OUTPUT_ROOT", str(root))

    app, api_v1 = _app()
    api_v1.dependency_overrides[require_write] = _writer_user

    resp = await _pull(
        app,
        {
            "package_name": "nonexistent-org/nonexistent-project",
            "version": "1.0.0",
            "output_dir": str(root),
        },
    )

    api_v1.dependency_overrides.clear()
    assert resp.status_code != 422, resp.text


@pytest.mark.asyncio
async def test_omitting_output_dir_stays_ungated(monkeypatch):
    """The server's own default (packages/ in the repo root) is never
    caller-controlled, so it must not be routed through the sandbox at
    all — even with no root configured."""
    from src.core.api.dependencies import require_write

    monkeypatch.delenv("PACKAGE_PULL_OUTPUT_ROOT", raising=False)
    app, api_v1 = _app()
    api_v1.dependency_overrides[require_write] = _writer_user

    resp = await _pull(
        app, {"package_name": "nonexistent-org/nonexistent-project", "version": "1.0.0"}
    )

    api_v1.dependency_overrides.clear()
    assert resp.status_code != 422, resp.text
