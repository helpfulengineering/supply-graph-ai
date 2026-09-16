"""POST /okh/from-storage and POST /okh/harvest-parts must not leak a
private manifest (#513).

Both loaded a manifest by id and returned its content with no visibility
check at all — the same shape #486/#503/#504/#505 already fixed for
`match/validate` and the OKW routes, and the same fix here: resolve
`get_viewer`, 404 rather than return anything when the caller is anonymous
and the manifest isn't shareable. #485 had gated both with `require_write`
as a stopgap — a credential proved the caller was *someone*, not that they
were allowed to see *this* manifest — which is why an authenticated
stranger could read the same private content an anonymous one could.

`harvest_parts` takes a batch of ids; the check runs per id rather than
once for the whole request, so a shareable id cannot smuggle out results
for a private one listed alongside it in the same call.
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


def _manifest(title: str = "widget"):
    m = MagicMock()
    m.to_dict.return_value = {
        "id": str(uuid4()),
        "title": title,
        "version": "1.0.0",
        "license": {"hardware": "CERN-OHL-S-2.0"},
        "licensor": "Test Author",
        "documentation_language": "en",
        "function": "A widget",
    }
    m.title = title
    m.components = []
    return m


def _svc(visibility: VisibilityLevel):
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_manifest())
    svc.get_visibility = AsyncMock(return_value=visibility)
    return svc


@pytest.mark.asyncio
async def test_from_storage_404s_for_anonymous_when_private():
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    api_v1.dependency_overrides[get_okh_service] = lambda: _svc(VisibilityLevel.PRIVATE)

    import httpx

    okh_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/okh/from-storage", json={"manifest_id": okh_id}
        )

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_from_storage_reaches_success_for_shareable():
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    api_v1.dependency_overrides[get_okh_service] = lambda: _svc(VisibilityLevel.PUBLIC)

    import httpx

    okh_id = str(uuid4())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/okh/from-storage", json={"manifest_id": okh_id}
        )

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_harvest_parts_404s_for_anonymous_when_any_manifest_is_private():
    """A batch of two ids, only the second private — must still 404, not
    silently drop the private one and return the public one's parts."""
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=_manifest())
    svc.get_visibility = AsyncMock(
        side_effect=[VisibilityLevel.PUBLIC, VisibilityLevel.PRIVATE]
    )
    api_v1.dependency_overrides[get_okh_service] = lambda: svc

    import httpx

    ids = [str(uuid4()), str(uuid4())]
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/okh/harvest-parts", json={"manifest_ids": ids}
        )

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_harvest_parts_reaches_success_when_all_shareable():
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    api_v1.dependency_overrides[get_okh_service] = lambda: _svc(VisibilityLevel.PUBLIC)

    import httpx

    ids = [str(uuid4())]
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/okh/harvest-parts", json={"manifest_ids": ids}
        )

    api_v1.dependency_overrides.clear()
    assert resp.status_code == 200, resp.text
