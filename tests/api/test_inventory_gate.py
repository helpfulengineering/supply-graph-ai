"""The inventory is admin-only where admin means anything (#405).

It lists every record on the node with its owner — metadata, not content, but
still a directory of who has made what. That belongs behind the same gate as
the rest of the operator surface.

Peacetime leaves admin open in development on purpose, so asserting the gate
means asserting it under the policy that actually enforces one.
"""

from __future__ import annotations

import os
import sys

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
@pytest.mark.parametrize("path", ["/v1/api/okh/inventory", "/v1/api/okw/inventory"])
async def test_inventory_refuses_an_anonymous_caller_when_enforced(monkeypatch, path):
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")

    app, _ = _get_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.get(path)

    assert resp.status_code in (401, 403), resp.text


@pytest.mark.asyncio
@pytest.mark.contract
@pytest.mark.parametrize("path", ["/v1/api/okh/inventory", "/v1/api/okw/inventory"])
async def test_inventory_is_a_literal_route_not_an_id(path):
    """A regression guard with a real story.

    FastAPI matches in declaration order, so registering /inventory after
    /{id} makes the literal path unreachable — it arrived as id="inventory"
    and 422'd on UUID parsing. A 422 here means the ordering has regressed.
    """
    app, _ = _get_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.get(path)

    assert (
        resp.status_code != 422
    ), f"{path} was matched as a path parameter, not as a literal route"
