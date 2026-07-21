"""Contract tests for space claim + edge bootstrap routes (Slice 5)."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import FastAPI

from src.core.models.capability import CapabilityGrant, Scope
from src.core.models.space import SpaceClaim
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


@pytest.mark.asyncio
@pytest.mark.contract
async def test_claim_space_returns_201():
    from src.core.api.routes.identity import get_auth_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.claim_space = AsyncMock(
        return_value=SpaceClaim(
            space_did="did:key:zSpace",
            admin_did="did:key:zAdmin",
            signature="ab" * 32,
        )
    )
    api_v1.dependency_overrides[get_auth_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/identity/spaces/claim",
                json={
                    "space_did": "did:key:zSpace",
                    "admin_did": "did:key:zAdmin",
                },
            )
        assert resp.status_code == 201, resp.text
        assert resp.json()["admin_did"] == "did:key:zAdmin"
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_bootstrap_edge_grant_returns_201():
    from src.core.api.routes.identity import get_auth_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    now = datetime.utcnow()
    svc.bootstrap_edge_grant = AsyncMock(
        return_value=CapabilityGrant(
            issuer_did="did:key:zEdge",
            subject_did="did:key:zEdge",
            permissions=["write"],
            coarse_floor=["read", "write"],
            scope=Scope(kind="node", target="did:key:zNode"),
            issued_at=now,
            expires_at=now + timedelta(days=90),
            signature="cd" * 32,
        )
    )
    api_v1.dependency_overrides[get_auth_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/identity/grants/bootstrap-edge",
                params={"subject_did": "did:key:zEdge"},
            )
        assert resp.status_code == 201, resp.text
        assert resp.json()["issuer_did"] == "did:key:zEdge"
    finally:
        api_v1.dependency_overrides.clear()
