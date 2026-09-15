"""Supply-tree routes that persist must authorize (#484).

Seven routes on this surface wrote to storage with no `Authorization` header, in
every security mode: creating and updating trees, deleting them, and saving,
extending, deleting or bulk-cleaning saved solutions.

Three POST-shaped routes deliberately stay open, because they persist nothing —
`solution/load`, `{id}/validate` and `{id}/optimize`. They are declared in
`READS_EXPRESSED_AS_POST`, and `test_reads_stay_open` asserts that boundary: a
blanket guard across the router would satisfy every refusal below and quietly
break them.

Those three are provisional. Their `GET` twins are themselves unscoped (#496),
so when that lands they must be scoped here in the same change.

The first test is a **calibration control** proving this file can observe
enforcement, so the refusals mean something.
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

TREE = uuid4()
SOLUTION = "sol-abc"


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
    "method,path",
    [
        ("POST", "/v1/api/supply-tree/create"),
        ("PUT", f"/v1/api/supply-tree/{TREE}"),
        ("DELETE", f"/v1/api/supply-tree/{TREE}"),
        ("POST", f"/v1/api/supply-tree/solution/{SOLUTION}/save"),
        ("POST", f"/v1/api/supply-tree/solution/{SOLUTION}/extend"),
        ("DELETE", f"/v1/api/supply-tree/solution/{SOLUTION}"),
        ("POST", "/v1/api/supply-tree/solutions/cleanup"),
    ],
)
async def test_writes_require_auth(monkeypatch, method, path):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    resp = await _call(method, path, json={})
    assert resp.status_code == 401, f"{method} {path} -> {resp.status_code}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/v1/api/supply-tree/solution/load",
        f"/v1/api/supply-tree/{TREE}/validate",
        f"/v1/api/supply-tree/{TREE}/optimize",
    ],
)
async def test_reads_stay_open(monkeypatch, path):
    """The boundary, not just the guards.

    These persist nothing, so a write permission on them would be theatre. A
    blanket guard on the router would pass every refusal above and break these.
    """
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")
    resp = await _call("POST", path, json={})
    assert resp.status_code != 401, f"{path} -> {resp.status_code}"
