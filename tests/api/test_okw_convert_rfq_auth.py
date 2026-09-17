"""okw/convert/rfq routes authorize or are correctly declared as exempt
(#487, the tail of the #479 split).

Of the seven routes this issue covers, reading each handler (not the route
name) found only one real write: `okw/upload` persists via
`okw_service.create(...)` and had no auth dependency at all, unlike its
sibling `okh/upload` which already gates on `require_write`. The other six
(`convert/to-datasheet`, `convert/from-okh-losh`, `convert/from-datasheet`,
`okw/extract`, `okw/validate`, `rfq/generate`) persist nothing — verified by
reading each body — and move to `READS_EXPRESSED_AS_POST` instead, matching
the precedent `okh/extract`/`okh/validate` already set in #485.

Mirrors the shape of `tests/api/test_okh_ingest_auth.py`: a calibrated
refuse/reachable pair for the one real fix, plus "stays open" assertions for
a representative route from each reclassified shape (a content-echoing pure
function, a file-upload pure function, and a body-only pure function) rather
than one per route.
"""

from __future__ import annotations

import os
import sys

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

pytestmark = pytest.mark.contract


def _app() -> FastAPI:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app


_UPLOAD_PATH = "/v1/api/okw/upload"


@pytest.mark.asyncio
async def test_upload_refuses_anonymous_when_enforced(monkeypatch):
    """Calibration: proves the test can observe enforcement at all — a check
    that has never been shown to refuse where it should is not evidence when
    it refuses."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    app = _app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            _UPLOAD_PATH,
            files={"okw_file": ("facility.json", b'{"name": "x"}', "application/json")},
        )

    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_upload_reachable_anonymously_when_not_enforced(monkeypatch):
    """The control: the same route, policy relaxed — reaches the handler
    rather than 401, proving the previous test's 401 came from enforcement
    and not from something else entirely (a malformed request, a missing
    route, ...)."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "development")
    app = _app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            _UPLOAD_PATH,
            files={"okw_file": ("facility.json", b'{"name": "x"}', "application/json")},
        )

    assert resp.status_code != 401, resp.text


@pytest.mark.asyncio
async def test_validate_stays_open_even_when_writes_are_enforced(monkeypatch):
    """`/okw/validate` persists nothing (`okw_service` is injected but never
    called) and moved to `READS_EXPRESSED_AS_POST` rather than gaining a
    write dependency — must not 401 even under production policy."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    app = _app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/okw/validate",
            json={"content": {"name": "x"}},
        )

    assert resp.status_code != 401, resp.text


@pytest.mark.asyncio
async def test_convert_to_datasheet_stays_open_even_when_writes_are_enforced(
    monkeypatch,
):
    """`/convert/to-datasheet` builds an `OKHManifest` from the request body
    and streams back a generated file — no storage access on any path — and
    must stay open even under production policy."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    app = _app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/convert/to-datasheet",
            json={
                "title": "x",
                "version": "1.0",
                "license": "MIT",
                "function": "x",
            },
        )

    assert resp.status_code != 401, resp.text


@pytest.mark.asyncio
async def test_rfq_generate_stays_open_even_when_writes_are_enforced(monkeypatch):
    """`/rfq/generate` renders documents purely from `request.solutions` and
    other body fields — no storage access — and must stay open even under
    production policy."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    app = _app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
        resp = await client.post(
            "/v1/api/rfq/generate",
            json={"solutions": []},
        )

    assert resp.status_code != 401, resp.text
