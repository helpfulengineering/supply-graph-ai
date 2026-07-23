"""Contract: POST /v1/api/okh/create must return 201 with OKHUploadResponse.

Regression: OKHResponse subclasses SuccessResponse (requires ``message``/``status``).
Building ``OKHResponse(**manifest.to_dict())`` raised ValidationError → HTTP 500
after the manifest was already persisted (federation matrix noise on Azure 0.10.0).
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

MINIMAL = {
    "okhv": "1.0",
    "id": str(uuid4()),
    "title": "Create Contract Seed",
    "version": "1.0.0",
    "license": {"hardware": "MIT"},
    "licensor": "OHM Test",
    "documentation_language": "en",
    "function": "Contract test manifest",
    "manufacturing_processes": ["Assembly"],
}


def _get_app() -> FastAPI:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_okh_returns_201_upload_response():
    from src.core.api.routes.okh import get_okh_service
    from src.core.models.okh import OKHManifest

    app = _get_app()
    api_v1 = app.routes[0].app  # mounted /v1
    # Prefer dependency override on the mounted app's routes module
    from src.core.main import api_v1 as v1

    manifest = OKHManifest.from_dict(dict(MINIMAL))
    svc = MagicMock()
    svc.create = AsyncMock(return_value=manifest)
    v1.dependency_overrides[get_okh_service] = lambda: svc

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/okh/create",
                json={"content": MINIMAL},
            )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["success"] is True
        assert "message" in body
        assert body["okh"]["id"] == str(manifest.id)
        assert body["okh"]["title"] == manifest.title
        svc.create.assert_awaited_once()
    finally:
        v1.dependency_overrides.pop(get_okh_service, None)
