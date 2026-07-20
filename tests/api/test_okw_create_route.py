"""
Contract test for POST /api/okw/create.

Regression guard: the handler previously built ``OKWUploadResponse`` with the
wrong field names (``facility=``/``facility_id=``) while the model requires
``okw=``, so every successful create raised a 500 when serializing the response.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


def _facility_content() -> dict:
    data_dir = Path(__file__).resolve().parents[2] / "synthetic_data"
    facility_file = sorted(data_dir.glob("*okw*.json"))[0]
    return json.loads(facility_file.read_text(encoding="utf-8"))


@pytest.mark.asyncio
@pytest.mark.contract
async def test_create_okw_returns_201_with_okw_field():
    from src.core.api.routes.okw import get_okw_service

    app, api_v1 = _get_app()
    svc = MagicMock()
    # Service echoes the parsed facility back (create returns the stored record).
    svc.create = AsyncMock(
        side_effect=lambda facility, created_by=None, provenance=None: facility
    )
    api_v1.dependency_overrides[get_okw_service] = lambda: svc

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/v1/api/okw/create", json={"content": _facility_content()}
            )

        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["success"] is True
        assert body.get("okw") is not None
    finally:
        api_v1.dependency_overrides.clear()
