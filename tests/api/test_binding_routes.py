"""Contract tests for binding + directory routes (Slice 7)."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import FastAPI

from src.core.models.binding import DirectoryEntry, IdentityBinding

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


@pytest.mark.asyncio
@pytest.mark.contract
async def test_start_domain_binding_returns_201():
    from src.core.api.routes.identity import get_auth_service

    app, api_v1 = _get_app()
    binding = IdentityBinding(
        subject_did="did:key:zSpace",
        kind="domain",
        external_id="domain:example.org",
        challenge="abc",
        signature="ab" * 32,
    )
    svc = MagicMock()
    svc.start_domain_binding = AsyncMock(
        return_value={
            "binding": binding,
            "well_known_url": "https://example.org/.well-known/ohm-did.json",
            "well_known_document": {
                "did": "did:key:zSpace",
                "challenge": "abc",
                "method": "ohm-domain-bind-v1",
            },
        }
    )
    api_v1.dependency_overrides[get_auth_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/identity/bindings/domain",
                json={"subject_did": "did:key:zSpace", "domain": "example.org"},
            )
        assert resp.status_code == 201, resp.text
        assert resp.json()["well_known_url"].endswith("ohm-did.json")
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_list_directory_returns_200():
    from src.core.api.routes.identity import get_auth_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.list_directory = AsyncMock(
        return_value=[
            DirectoryEntry(did="did:key:zA", display_name="Ada", domain="a.example")
        ]
    )
    api_v1.dependency_overrides[get_auth_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get("/v1/api/identity/directory")
        assert resp.status_code == 200, resp.text
        assert resp.json()[0]["domain"] == "a.example"
    finally:
        api_v1.dependency_overrides.clear()
