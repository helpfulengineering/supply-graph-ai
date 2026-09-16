"""POST /match/validate must not leak a private design (#486, #505), and must
actually validate once it gets past that gate (#507).

`validate_match` used to load an OKH manifest by id via the raw
`storage_service.get_domain_handler("okh").load()` path, bypassing
`OKHService.get()` and any visibility check entirely — the same shape
#503/#504 fixed for OKW facilities. #486 added the visibility check; #505
also fixed the loading mechanism itself, since the raw storage handler built
a filename `okh_service.create()` never wrote (a storage-key mismatch,
unrelated to auth) and always 500'd before the visibility check could ever
run against a real manifest.

The two mocked-visibility tests below exercise the gate with `OKHService.get`
mocked directly, since a real manifest load is not what is under test there.
#507 fixed what happens once a request gets past that gate: the registry
handed back a legacy sync validator stub that always crashed (or, for
manufacturing/cooking, was never wired to anything meaningful), and a second
bug coerced the real validator's domain-specific error codes into an enum
that didn't contain them. `test_validate_match_end_to_end_real_manifest`
below exercises that with no mocking at all — a real manifest, the real
`ManufacturingOKHValidator`, over one ASGI transport/event loop (a
synchronous `TestClient` making several separate calls hits the loop-affinity
singleton issue CLAUDE.md documents for `StorageService`/`BaseService`; one
`httpx.AsyncClient` making all calls from a single coroutine avoids it, same
as the tests below already do).
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.models.visibility import VisibilityLevel  # noqa: E402

pytestmark = pytest.mark.contract


def _app():
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


def _manifest():
    m = MagicMock()
    m.to_dict.return_value = {"id": "x"}
    return m


@pytest.mark.asyncio
async def test_validate_match_404s_for_anonymous_when_private(monkeypatch):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    from src.core.api.routes.match import get_okh_service

    app, api_v1 = _app()

    okh_svc = MagicMock()
    okh_svc.get = AsyncMock(return_value=_manifest())
    okh_svc.get_visibility = AsyncMock(return_value=VisibilityLevel.PRIVATE)

    api_v1.dependency_overrides[get_okh_service] = lambda: okh_svc

    import httpx

    okh_id = str(uuid4())
    payload = {"okh_id": okh_id, "supply_tree_id": okh_id}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post("/v1/api/match/validate", json=payload)

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_validate_match_reaches_matching_for_shareable(monkeypatch):
    """Calibration: without the visibility check, this would already pass —
    the point is that a *public* design must NOT 404 on visibility grounds."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    from src.core.api.routes.match import get_okh_service

    app, api_v1 = _app()

    okh_svc = MagicMock()
    okh_svc.get = AsyncMock(return_value=_manifest())
    okh_svc.get_visibility = AsyncMock(return_value=VisibilityLevel.PUBLIC)

    api_v1.dependency_overrides[get_okh_service] = lambda: okh_svc

    import httpx

    okh_id = str(uuid4())
    payload = {"okh_id": okh_id, "supply_tree_id": okh_id}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post("/v1/api/match/validate", json=payload)

    api_v1.dependency_overrides.clear()
    # Should NOT be 404-for-visibility. It may still fail downstream (a
    # separate, structural defect in the manufacturing validator — filed
    # separately — for a mocked manifest that reaches that far), but a 404
    # specifically means the visibility gate rejected it, which is wrong here.
    assert resp.status_code != 404, resp.text


@pytest.mark.asyncio
async def test_validate_match_end_to_end_real_manifest():
    """No mocks: create a real manifest, share it, validate it (#507).

    A deliberately incomplete manifest (missing several professional-level
    required fields) so the response has to carry real errors, not just a
    clean pass — that's what actually proves the real
    `ManufacturingOKHValidator` ran and its output made it back through the
    `ErrorCode` conversion without crashing, which is the whole point of
    #507. Every `errors[].code` must be a real `ErrorCode` member: that's
    the exact contract `ErrorDetail.code`'s strict typing enforces, and the
    thing that 500'd before the fix (`'required_field_missing' is not a
    valid ErrorCode`).
    """
    import httpx
    from src.core.api.models.base import ErrorCode
    from src.core.main import api_v1, app

    payload = {
        "title": "Test Widget",
        "repo": "https://github.com/example/widget",
        "version": "1.0.0",
        "license": {"hardware": "CERN-OHL-S-2.0"},
        "licensor": "Test Author",
        "function": "A widget",
        "manufacturing_processes": ["3D printing"],
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        create_resp = await client.post("/v1/api/okh/manifests/", json=payload)
        assert create_resp.status_code == 201, create_resp.text
        okh_id = create_resp.json()["id"]

        share_resp = await client.put(
            f"/v1/api/okh/{okh_id}/visibility", json={"visibility": "public"}
        )
        assert share_resp.status_code == 200, share_resp.text

        resp = await client.post(
            "/v1/api/match/validate",
            json={"okh_id": okh_id, "supply_tree_id": okh_id},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_valid"] is False
    assert len(body["errors"]) > 0
    valid_codes = {c.value for c in ErrorCode}
    for error in body["errors"]:
        assert error["code"] in valid_codes, error
        assert error["message"]
