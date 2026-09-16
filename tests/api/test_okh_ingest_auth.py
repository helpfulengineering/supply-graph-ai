"""OKH ingest/generation routes authorize or are correctly declared as
exempt (#485).

Fourteen routes resolved no auth dependency at all — every one of them a row
in `UNAUTHENTICATED_DEBT` (`tests/parity/test_auth_ratchet.py`). The ratchet
proves each route now resolves *some* dependency or has moved to
`READS_EXPRESSED_AS_POST`; it cannot prove the dependency actually refuses
when it should, or that a genuinely-exempt route stays open. These tests do
that, on a representative route from each of the three shapes #485 produced:

- `require_write` (e.g. `/okh/from-storage`) — must 401 an anonymous
  caller once `SecurityPolicy.require_auth_for_writes` is enforced
  (production), calibrated against a control proving the same route is
  reachable at all when it is not enforced.
- `require_auth_for_llm_spend` — covered exhaustively in
  `tests/unit/test_llm_auth_gate.py`; not repeated here.
- `READS_EXPRESSED_AS_POST` (`/okh/validate`) — must stay open even in
  production, since it persists nothing and has no visibility to scope.
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

pytestmark = pytest.mark.contract


def _app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


@pytest.mark.asyncio
async def test_from_storage_refuses_anonymous_when_enforced(monkeypatch):
    """Calibration: proves the test can observe enforcement at all — a
    check that has never been shown to refuse where it should is not
    evidence when it refuses."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    app, _ = _app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/okh/from-storage", json={"manifest_id": str(uuid4())}
        )

    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_from_storage_reachable_anonymously_when_not_enforced(monkeypatch):
    """The control: the same route, same payload, policy relaxed — reaches
    the handler (404 for a manifest that doesn't exist) rather than 401,
    proving the previous test's 401 came from enforcement and not from
    something else entirely (a malformed request, a missing route, ...)."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=None)
    api_v1.dependency_overrides[get_okh_service] = lambda: svc

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://t"
        ) as client:
            resp = await client.post(
                "/v1/api/okh/from-storage", json={"manifest_id": str(uuid4())}
            )
    finally:
        api_v1.dependency_overrides.clear()

    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_validate_stays_open_even_when_writes_are_enforced(monkeypatch):
    """`/okh/validate` persists nothing (`okh_service` is injected but never
    called) and moved to `READS_EXPRESSED_AS_POST` rather than gaining a
    write dependency (#485) — must not 401 even under production policy."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    app, _ = _app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/okh/validate",
            json={"content": {"title": "x"}},
        )

    assert resp.status_code != 401, resp.text
