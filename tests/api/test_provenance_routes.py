"""Contract tests for GET /api/okh/{id}/provenance and /api/okw/{id}/provenance."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from src.core.models.provenance import Credit, RecordProvenance

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
async def test_get_okh_provenance_returns_record():
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _get_app()
    manifest_id = uuid4()
    svc = MagicMock()
    svc.get_provenance = AsyncMock(
        return_value=RecordProvenance(
            authored_by=[Credit(subject_did="did:key:zAuthor", role="author")],
            published_by="did:key:zAuthor",
        )
    )
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    try:
        async with await _client(app) as client:
            resp = await client.get(f"/v1/api/okh/{manifest_id}/provenance")
        assert resp.status_code == 200, resp.text
        assert resp.json()["published_by"] == "did:key:zAuthor"
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_get_okh_provenance_404_when_absent():
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.get_provenance = AsyncMock(return_value=None)
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    try:
        async with await _client(app) as client:
            resp = await client.get(f"/v1/api/okh/{uuid4()}/provenance")
        assert resp.status_code == 404, resp.text
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_get_okw_provenance_returns_record():
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.get_provenance = AsyncMock(
        return_value=RecordProvenance(
            published_by="did:key:zSpace", on_behalf_of="did:key:zSpace"
        )
    )
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        async with await _client(app) as client:
            resp = await client.get(f"/v1/api/okw/{uuid4()}/provenance")
        assert resp.status_code == 200, resp.text
        assert resp.json()["on_behalf_of"] == "did:key:zSpace"
    finally:
        api_v1.dependency_overrides.clear()
