"""Contract test for GET /identity/security-policy (Slice 8)."""

from __future__ import annotations

import os
import sys

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _get_app() -> FastAPI:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app


@pytest.mark.asyncio
@pytest.mark.contract
async def test_security_policy_returns_200():
    app = _get_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.get("/v1/api/identity/security-policy")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mode"] in ("peacetime", "crisis", "shielded")
    assert "grant_ttl_days" in body
    assert "mdns_advertise" in body
