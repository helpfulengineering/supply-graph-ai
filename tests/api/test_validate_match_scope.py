"""POST /match/validate must not leak a private design (#486, #505).

`validate_match` used to load an OKH manifest by id via the raw
`storage_service.get_domain_handler("okh").load()` path, bypassing
`OKHService.get()` and any visibility check entirely — the same shape
#503/#504 fixed for OKW facilities. #486 added the visibility check; #505
also fixed the loading mechanism itself, since the raw storage handler built
a filename `okh_service.create()` never wrote (a storage-key mismatch,
unrelated to auth) and always 500'd before the visibility check could ever
run against a real manifest.

This exercises the fix with `OKHService.get` mocked directly, since a real
manifest load is not what is under test here — the visibility gate is.
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
