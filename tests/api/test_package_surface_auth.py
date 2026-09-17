"""The entire /v1/api/package surface authorizes or is correctly declared as
exempt (#478).

Unlike every other surface #479's ratchet split out, `package.py` had zero
`require_write`/`require_admin` dependencies anywhere — build, push, pull,
delete, and pin all accepted anonymous calls unconditionally, in every
security mode. All seven get `require_write`, the same policy-gated guard
used everywhere else (a no-op in dev/test, enforced in production); reads
and downloads stay public, matching the issue's own acceptance criteria.

One parametrized calibration/control pair covers all seven, since they all
gained the identical dependency. `build/{manifest_id}` gets its own
additional pair: it builds a package from a manifest loaded *by id*, the
same shape #513 fixed for `okh/from-storage` — a private manifest must not
become a publicly-downloadable package just because the caller holds any
write credential.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.models.package import BuildOptions  # noqa: E402
from src.core.models.visibility import VisibilityLevel  # noqa: E402

pytestmark = pytest.mark.contract

_MANIFEST_DATA = {
    "title": "widget",
    "version": "1.0.0",
    "license": "MIT",
    "licensor": "Test Author",
    "documentation_language": "en",
    "function": "A widget",
}

_MUTATING_ROUTES = [
    ("POST", "/v1/api/package/build", {"manifest_data": _MANIFEST_DATA}),
    ("POST", f"/v1/api/package/build/{uuid4()}", None),
    (
        "POST",
        "/v1/api/package/download-zip",
        {"items": [{"org": "o", "project": "p", "version": "1.0.0"}]},
    ),
    ("POST", "/v1/api/package/push", {"package_name": "o/p", "version": "1.0.0"}),
    ("POST", "/v1/api/package/pull", {"package_name": "o/p", "version": "1.0.0"}),
    ("DELETE", "/v1/api/package/o/p/1.0.0", None),
    ("POST", "/v1/api/package/o/p/1.0.0/pin", None),
]


def _app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,body", _MUTATING_ROUTES)
async def test_refuses_anonymous_when_enforced(monkeypatch, method, path, body):
    """Calibration: proves the test can observe enforcement at all — a check
    that has never been shown to refuse where it should is not evidence when
    it refuses."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    app, _ = _app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.request(method, path, json=body)

    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path,body", _MUTATING_ROUTES)
async def test_reachable_anonymously_when_not_enforced(monkeypatch, method, path, body):
    """The control: the same route, policy relaxed — reaches the handler
    (whatever it naturally returns) rather than 401, proving the previous
    test's 401 came from enforcement and not from something else entirely
    (a malformed request, a missing route, ...)."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    app, _ = _app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.request(method, path, json=body)

    assert resp.status_code != 401, resp.text


def _okh_service(visibility: VisibilityLevel):
    svc = MagicMock()
    svc.get_visibility = AsyncMock(return_value=visibility)
    return svc


def _package_service():
    svc = MagicMock()
    metadata = MagicMock()
    metadata.to_dict.return_value = {
        "package_name": "o/p",
        "version": "1.0.0",
        "okh_manifest_id": str(uuid4()),
        "build_timestamp": "2026-01-01T00:00:00",
        "ohm_version": "0.12.2",
        "total_files": 0,
        "total_size_bytes": 0,
        "file_inventory": [],
        "build_options": BuildOptions().to_dict(),
        "package_path": "/tmp/o/p/1.0.0",
    }
    svc.build_package_from_storage = AsyncMock(return_value=metadata)
    return svc


@pytest.mark.asyncio
async def test_build_from_storage_404s_for_anonymous_when_private():
    """A private manifest must not become a downloadable package just
    because the caller holds any write credential (#478, same shape #513
    fixed for okh/from-storage)."""
    from src.core.api.routes.package import get_okh_service, get_package_service

    app, api_v1 = _app()
    api_v1.dependency_overrides[get_okh_service] = lambda: _okh_service(
        VisibilityLevel.PRIVATE
    )
    api_v1.dependency_overrides[get_package_service] = _package_service

    manifest_id = uuid4()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(f"/v1/api/package/build/{manifest_id}")

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_build_from_storage_reaches_success_for_shareable():
    from src.core.api.routes.package import get_okh_service, get_package_service

    app, api_v1 = _app()
    api_v1.dependency_overrides[get_okh_service] = lambda: _okh_service(
        VisibilityLevel.PUBLIC
    )
    api_v1.dependency_overrides[get_package_service] = _package_service

    manifest_id = uuid4()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(f"/v1/api/package/build/{manifest_id}")

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 201, resp.text
