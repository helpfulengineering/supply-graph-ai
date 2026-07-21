"""Contract tests for GET/PUT /api/{okh,okw}/{id}/visibility."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from src.core.models.visibility import VisibilityLevel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


@pytest.mark.asyncio
@pytest.mark.contract
async def test_put_okh_visibility():
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _get_app()
    manifest_id = uuid4()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=MagicMock())
    svc.set_visibility = AsyncMock(return_value=VisibilityLevel.PUBLIC)
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.put(
                f"/v1/api/okh/{manifest_id}/visibility",
                json={"visibility": "public"},
            )
        assert resp.status_code == 200, resp.text
        assert resp.json()["visibility"] == "public"
        svc.set_visibility.assert_awaited_once()
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_get_okh_visibility_404_when_missing_record():
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=None)
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(f"/v1/api/okh/{uuid4()}/visibility")
        assert resp.status_code == 404, resp.text
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_put_okw_visibility():
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _get_app()
    facility_id = uuid4()
    svc = MagicMock()
    svc.set_visibility = AsyncMock(return_value=VisibilityLevel.FOLLOWERS)
    api_v1.dependency_overrides[get_okw_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.put(
                f"/v1/api/okw/{facility_id}/visibility",
                json={"visibility": "followers"},
            )
        assert resp.status_code == 200, resp.text
        assert resp.json()["visibility"] == "followers"
    finally:
        api_v1.dependency_overrides.clear()
