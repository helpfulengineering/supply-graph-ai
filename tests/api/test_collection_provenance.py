"""Import restores the provenance an export carried, and restamps visibility."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import FastAPI

from src.core.models.provenance import organisation_verified
from src.core.packaging.collection import export_collection
from tests.federation.test_organisation_chain import _chain
from tests.unit.test_okh_collection import _manifest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


async def _client(app):
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
@pytest.mark.contract
async def test_export_writes_the_provenance_it_holds():
    from src.core.api.routes.okh import get_okh_service
    from src.core.packaging.collection import analyse_import

    manifest = _manifest("Widget")
    chain = _chain()
    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.list = AsyncMock(return_value=([manifest], 1))
    svc.get_provenance = AsyncMock(return_value=chain)
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    try:
        async with await _client(app) as client:
            resp = await client.get("/v1/api/okh/export-collection")
        assert resp.status_code == 200, resp.text
        report, _incoming = analyse_import(resp.content, [])
        restored = report.provenance[report.new[0]["content_hash"]]
        assert organisation_verified(restored)
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_import_restores_provenance_and_leaves_visibility_to_the_node():
    from src.core.api.routes.okh import get_okh_service

    manifest = _manifest("Widget")
    chain = _chain()
    archive = export_collection([manifest], {str(manifest.id): chain})

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.list = AsyncMock(return_value=([], 0))
    svc.create = AsyncMock(return_value=manifest)
    svc.set_visibility = AsyncMock()
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    try:
        async with await _client(app) as client:
            resp = await client.post(
                "/v1/api/okh/import-collection",
                files={"file": ("collection.zip", archive, "application/zip")},
            )
        assert resp.status_code == 200, resp.text
        svc.create.assert_awaited_once()
        restored = svc.create.call_args.kwargs["provenance"]
        assert organisation_verified(restored)
        svc.set_visibility.assert_not_awaited()
    finally:
        api_v1.dependency_overrides.clear()
