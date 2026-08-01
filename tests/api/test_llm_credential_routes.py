"""Contract tests for admin LLM credential management.

Credential endpoints must reject anonymous callers even when
ENVIRONMENT=development (unlike require_admin, which relaxes in peacetime).
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
async def test_put_credential_rejects_anonymous_in_development(monkeypatch):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    app, _ = _get_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.put(
            "/v1/api/llm/credentials/anthropic",
            json={"api_key": "sk-secret", "model": "claude-test"},
        )
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
@pytest.mark.contract
async def test_put_credential_stores_and_returns_masked_status(monkeypatch):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    from src.core.api.dependencies import require_admin_strict
    from src.core.api.routes.llm import get_llm_credential_store, get_llm_service
    from src.core.models.auth import AuthenticatedUser

    admin = AuthenticatedUser(
        key_id=uuid4(), name="admin", permissions=["admin"], account_id=uuid4()
    )
    store = MagicMock()
    store.save = AsyncMock(return_value=None)
    store.list_status = AsyncMock(
        return_value=[
            {
                "provider": "anthropic",
                "model": "claude-test",
                "masked_key": "****1234",
                "configured": True,
            }
        ]
    )
    llm_svc = MagicMock()
    llm_svc.add_provider = AsyncMock(return_value=True)
    llm_svc.set_active_provider = AsyncMock(return_value=True)
    llm_svc.remove_provider = AsyncMock(return_value=True)

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[require_admin_strict] = lambda: admin
    api_v1.dependency_overrides[get_llm_credential_store] = lambda: store
    api_v1.dependency_overrides[get_llm_service] = lambda: llm_svc
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.put(
                "/v1/api/llm/credentials/anthropic",
                json={
                    "api_key": "sk-secret-1234",
                    "model": "claude-test",
                    "activate": False,
                },
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["provider"] == "anthropic"
        assert body["masked_key"] == "****1234"
        assert "sk-secret" not in resp.text
        store.save.assert_awaited()
    finally:
        api_v1.dependency_overrides.clear()
