"""Contract test: GET /api/utility/domains surfaces default_domain.

Regression guard for the cooking-domain-instance plan: default_domain must
be "manufacturing" whenever OHM_DEFAULT_DOMAIN is unset, and must reflect the
setting when an instance opts into a different domain (e.g. cooking).
"""

from __future__ import annotations

import os
import sys
from unittest.mock import patch

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


@pytest.fixture(autouse=True)
def _isolate_cache():
    """GET /api/utility/domains is cached; isolate so tests don't see each other's response."""
    from src.core.services.cache_service import get_cache_service

    get_cache_service().clear()
    yield
    get_cache_service().clear()


async def _fetch_domains(app: FastAPI) -> dict:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.get("/v1/api/utility/domains")
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_default_domain_is_manufacturing_with_no_override():
    app, _ = _get_app()

    with patch(
        "src.core.api.routes.utility.settings.OHM_DEFAULT_DOMAIN", "manufacturing"
    ):
        body = await _fetch_domains(app)

    assert body["data"]["default_domain"] == "manufacturing"


@pytest.mark.asyncio
@pytest.mark.contract
async def test_default_domain_reflects_cooking_override():
    app, _ = _get_app()

    with patch("src.core.api.routes.utility.settings.OHM_DEFAULT_DOMAIN", "cooking"):
        body = await _fetch_domains(app)

    assert body["data"]["default_domain"] == "cooking"
