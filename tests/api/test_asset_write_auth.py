"""The asset surface writes, so it authorizes (#483).

`AssetRecord` is the third top-level domain object — design (OKH), capability
(OKW), physical state (asset) — persisted at `asset/{id}.json`. Create, update,
delete, triage and claim-component all reached their handlers with no
`Authorization` header, in every security mode.

`salvage-match` is deliberately *not* in this file. It persists nothing and reads
the same records `GET /v1/api/asset` already serves publicly, so a write
permission on it would be theatre. It is declared in
`tests/parity/test_auth_ratchet.py` under `READS_EXPRESSED_AS_POST`, which names
the read it is equivalent to.

The first test is a **calibration control**: it proves this file can observe
enforcement, so the refusals below mean something.
"""

from __future__ import annotations

import os
import sys
from uuid import uuid4

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


async def _call(method: str, path: str, **kw) -> httpx.Response:
    transport = httpx.ASGITransport(app=_app())
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        return await client.request(method, path, **kw)


@pytest.mark.asyncio
async def test_calibration_a_guarded_route_refuses(monkeypatch):
    """Control: a route known to be guarded refuses, so a refusal is detectable."""
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    resp = await _call("DELETE", f"/v1/api/okh/manifests/{uuid4()}")
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    [
        ("POST", "/v1/api/asset/", {"manifest_id": str(uuid4())}),
        ("PUT", f"/v1/api/asset/{uuid4()}", {"location": "bench 3"}),
        ("DELETE", f"/v1/api/asset/{uuid4()}", None),
        ("POST", f"/v1/api/asset/{uuid4()}/triage", {"component_states": []}),
        (
            "POST",
            f"/v1/api/asset/{uuid4()}/claim-component",
            {"component_name": "pump", "claimed_by": "someone"},
        ),
    ],
)
async def test_asset_writes_require_auth(monkeypatch, method, path, body):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    kw = {"json": body} if body is not None else {}
    resp = await _call(method, path, **kw)
    assert resp.status_code == 401, f"{method} {path} -> {resp.status_code}"


@pytest.mark.asyncio
async def test_salvage_match_stays_open(monkeypatch):
    """The read is not swept up with the writes.

    Asserting the boundary, not just the guards: a blanket `require_write` across
    the router would pass every test above and quietly break this.
    """
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    resp = await _call(
        "POST", "/v1/api/asset/salvage-match", json={"component_name": "pump"}
    )
    assert resp.status_code != 401, resp.text
