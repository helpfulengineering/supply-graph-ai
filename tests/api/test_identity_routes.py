"""Contract tests for the identity API surface (Slice 1).

Confirms the router is mounted under /api/identity and that key/account
operations delegate to AuthenticationService. The service itself is mocked so
these stay hermetic; service behavior is covered in tests/unit.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
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
async def test_create_key_returns_token_once(monkeypatch):
    """Minting a key now requires a caller (#413).

    It used to be admin-gated, which the dev policy left open — so an
    unauthenticated request could mint a credential, which is the same shape as
    the anonymous-write hole. The operation is now scoped to the account making
    it, and an account is exactly what an anonymous caller does not have. The
    unauthenticated bootstrap path is POST /identity/register.
    """
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    from src.core.api.dependencies import get_current_user
    from src.core.api.routes.identity import get_auth_service
    from src.core.models.auth import APIKeyResponse, AuthenticatedUser

    account_id = uuid4()
    captured = {}

    async def _create(payload):
        captured["payload"] = payload
        return APIKeyResponse(
            key_id=uuid4(),
            name=payload.name,
            permissions=payload.permissions,
            created_at=datetime.utcnow(),
            token="secret-token",
        )

    svc = MagicMock()
    svc.create_api_key = AsyncMock(side_effect=_create)
    caller = AuthenticatedUser(
        key_id=uuid4(), name="ada", permissions=["read", "write"], account_id=account_id
    )

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_auth_service] = lambda: svc
    api_v1.dependency_overrides[get_current_user] = lambda: caller
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/identity/keys",
                # Asking for admin on someone else's account: both are ignored.
                json={
                    "name": "k",
                    "permissions": ["read", "admin"],
                    "account_id": str(uuid4()),
                },
            )
        assert resp.status_code == 201, resp.text
        assert resp.json()["token"] == "secret-token"
        assert captured["payload"].account_id == account_id
        assert "admin" not in captured["payload"].permissions
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_account(monkeypatch):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    from src.core.api.routes.identity import get_auth_service
    from src.core.models.account import Account, AccountKind

    account = Account(display_name="MIT FabLab", kind=AccountKind.SPACE)
    svc = MagicMock()
    svc.create_account = AsyncMock(return_value=account)

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_auth_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/identity/accounts",
                json={"display_name": "MIT FabLab", "kind": "space"},
            )
        assert resp.status_code == 201, resp.text
        assert resp.json()["display_name"] == "MIT FabLab"
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_mint_identity(monkeypatch):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    from src.core.api.routes.identity import get_auth_service
    from src.core.models.identity import Identity, IdentityKind

    account_id = uuid4()
    identity = Identity(
        did="did:key:zMinted",
        kind=IdentityKind.PERSON,
        display_name="Ada",
        account_id=str(account_id),
    )
    svc = MagicMock()
    svc.create_identity = AsyncMock(return_value=identity)

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_auth_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/identity/identities",
                json={"account_id": str(account_id), "display_name": "Ada"},
            )
        assert resp.status_code == 201, resp.text
        assert resp.json()["did"] == "did:key:zMinted"
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_issue_grant(monkeypatch):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    from datetime import timedelta

    from src.core.api.routes.identity import get_auth_service
    from src.core.models.capability import CapabilityGrant, Scope

    grant = CapabilityGrant(
        issuer_did="did:key:zNode",
        subject_did="did:key:zSubject",
        permissions=["write"],
        coarse_floor=["read"],
        scope=Scope(kind="node", target="did:key:zNode"),
        expires_at=datetime.utcnow() + timedelta(days=90),
    )
    svc = MagicMock()
    svc.issue_grant = AsyncMock(return_value=grant)

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_auth_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/identity/grants",
                json={
                    "issuer_did": "did:key:zNode",
                    "subject_did": "did:key:zSubject",
                    "permissions": ["write"],
                    "scope": {"kind": "node", "target": "did:key:zNode"},
                },
            )
        assert resp.status_code == 201, resp.text
        assert resp.json()["subject_did"] == "did:key:zSubject"
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_register_is_unauthenticated_and_returns_the_token_once(monkeypatch):
    """Registration must not require a credential — that is the whole point."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    from src.core.api.routes.identity import get_auth_service
    from src.core.models.auth import APIKeyResponse, RegistrationResponse

    account_id = uuid4()
    svc = MagicMock()
    svc.register = AsyncMock(
        return_value=RegistrationResponse(
            account_id=account_id,
            display_name="Ada",
            did="did:key:zTest",
            key=APIKeyResponse(
                key_id=uuid4(),
                name="Ada (first key)",
                permissions=["read", "write"],
                created_at=datetime.utcnow(),
                token="one-time-token",
            ),
        )
    )

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_auth_service] = lambda: svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            # No Authorization header, and production environment: still allowed.
            resp = await client.post(
                "/v1/api/identity/register", json={"display_name": "Ada"}
            )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["did"] == "did:key:zTest"
        assert body["key"]["token"] == "one-time-token"
        assert "admin" not in body["key"]["permissions"]
    finally:
        api_v1.dependency_overrides.clear()
