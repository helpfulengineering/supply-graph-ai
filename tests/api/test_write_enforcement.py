"""Contract tests for OKH write auth enforcement + attribution (Slice 1).

The policy knob ``require_auth_for_writes`` (peacetime: on in production, off in
dev/test) gates the OKH/OKW create/update/delete endpoints. These tests exercise
both postures on a representative OKH endpoint and verify writes are attributed to
the authenticated account.
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


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


@pytest.mark.asyncio
@pytest.mark.contract
async def test_write_requires_auth_when_enforced(monkeypatch):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    app, _ = _get_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.delete(f"/v1/api/okh/manifests/{uuid4()}")
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
@pytest.mark.contract
async def test_write_allowed_anonymously_when_not_enforced(monkeypatch):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=object())
    svc.delete = AsyncMock(return_value=True)
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.delete(f"/v1/api/okh/manifests/{uuid4()}")
        assert resp.status_code == 200, resp.text
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_attributed_to_account(monkeypatch):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    from src.core.api.dependencies import require_write
    from src.core.api.routes.okh import get_okh_service
    from src.core.models.auth import AuthenticatedUser

    account_id = uuid4()
    user = AuthenticatedUser(
        key_id=uuid4(), name="k", permissions=["write"], account_id=account_id
    )
    manifest = MagicMock()
    manifest.to_dict.return_value = {
        "id": str(uuid4()),
        "title": "T",
        "version": "1.0",
        "license": {"hardware": "MIT"},
        "licensor": "me",
        "documentation_language": "en",
        "function": "f",
    }
    svc = MagicMock()
    svc.create = AsyncMock(return_value=manifest)

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_okh_service] = lambda: svc
    api_v1.dependency_overrides[require_write] = lambda: user
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post("/v1/api/okh/manifests/", json={"title": "T"})
        assert resp.status_code == 201, resp.text
        svc.create.assert_awaited_once()
        assert svc.create.call_args.kwargs["created_by"] == str(account_id)
    finally:
        api_v1.dependency_overrides.clear()
