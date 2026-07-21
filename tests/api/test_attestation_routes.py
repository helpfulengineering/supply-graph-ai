"""Contract tests for attestation + reputation routes (Slice 6)."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import FastAPI

from src.core.models.attestation import Attestation

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


@pytest.mark.asyncio
@pytest.mark.contract
async def test_certify_returns_201():
    from src.core.api.routes.identity import get_auth_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.certify = AsyncMock(
        return_value=Attestation(
            type="certified",
            issuer_did="did:key:zIssuer",
            subject_did="did:key:zFirm",
            content_hash="sha256:bundle",
            claim={"version": "1.0.0"},
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
                "/v1/api/identity/attestations/certify",
                json={
                    "subject_did": "did:key:zFirm",
                    "bundle_hash": "sha256:bundle",
                    "version": "1.0.0",
                },
            )
        assert resp.status_code == 201, resp.text
        assert resp.json()["type"] == "certified"
        svc.certify.assert_awaited_once()
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_list_reputation_returns_200():
    from src.core.api.routes.identity import get_auth_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.list_reputation = AsyncMock(
        return_value=[
            Attestation(
                type="vouch",
                issuer_did="did:key:zA",
                subject_did="did:key:zB",
                signature="cd" * 32,
            )
        ]
    )
    api_v1.dependency_overrides[get_auth_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get("/v1/api/identity/reputation/did:key:zB")
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) == 1
    finally:
        api_v1.dependency_overrides.clear()
