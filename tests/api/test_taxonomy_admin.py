"""Reloading the taxonomy is an operator action, not a public one (#487).

``POST /v1/api/taxonomy/reload`` answered **200** to an anonymous caller on a
production-configured node, replacing the process taxonomy that every match
depends on. It resolved no auth dependency at all — see
``tests/parity/test_auth_ratchet.py`` for the gate that now prevents the class.

The first test is a **calibration control**: it proves this file can observe
enforcement, so the refusal asserted by the second means something. A check never
shown to PASS where it should is not evidence when it fails.
"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

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
async def test_calibration_a_guarded_route_refuses(monkeypatch):
    """Control: a route known to be guarded refuses, so a refusal is detectable."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    transport = httpx.ASGITransport(app=_get_app())
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.delete(f"/v1/api/okh/manifests/{uuid4()}")
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
@pytest.mark.contract
async def test_reload_requires_auth_when_enforced(monkeypatch):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    transport = httpx.ASGITransport(app=_get_app())
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.post("/v1/api/taxonomy/reload")
    assert resp.status_code == 401, resp.text
