"""Contract tests for OKH manifest file proxy routes (#272)."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

_MANIFEST_ID = UUID("123e4567-e89b-12d3-a456-426614174000")


def _get_app() -> tuple[FastAPI, FastAPI]:
    from src.core.main import api_v1

    app = FastAPI()
    app.mount("/v1", api_v1)
    return app, api_v1


@pytest.mark.asyncio
@pytest.mark.contract
async def test_get_okh_enriches_design_file_urls():
    from src.core.api.routes.okh import get_okh_service
    from src.core.models.okh import (
        DocumentationType,
        DocumentRef,
        License,
        OKHManifest,
    )

    manifest = OKHManifest(
        id=_MANIFEST_ID,
        title="Test",
        version="0.0.1",
        license=License(hardware="CERN-OHL-S-2.0"),
        licensor="Test",
        documentation_language="en",
        function="test",
        design_files=[
            DocumentRef(
                title="Plan",
                path="attachments/plan.pdf",
                type=DocumentationType.DESIGN_FILES,
            )
        ],
    )

    app, api_v1 = _get_app()
    svc = MagicMock()
    svc.get = AsyncMock(return_value=manifest)
    api_v1.dependency_overrides[get_okh_service] = lambda: svc

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(f"/v1/api/okh/{_MANIFEST_ID}")

        assert resp.status_code == 200, resp.text
        design = resp.json().get("design_files") or []
        assert design[0]["url"].endswith(
            f"/okh/{_MANIFEST_ID}/files/attachments/plan.pdf"
        )
    finally:
        api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_get_okh_file_returns_bytes():
    from src.core.api.routes.okh import get_okh_service

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_okh_service] = lambda: MagicMock()

    with patch(
        "src.core.api.routes.okh.resolve_okh_file_bytes",
        new=AsyncMock(return_value=(b"%PDF-1.4", "application/pdf", "plan.pdf")),
    ):
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                resp = await client.get(
                    f"/v1/api/okh/{_MANIFEST_ID}/files/attachments/plan.pdf"
                )

            assert resp.status_code == 200
            assert resp.content.startswith(b"%PDF")
            assert "inline" in resp.headers.get("content-disposition", "")
        finally:
            api_v1.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.contract
async def test_get_okh_file_missing_returns_404():
    from src.core.api.routes.okh import get_okh_service
    from src.core.services.okh_file_resolver import OkhFileNotFoundError

    app, api_v1 = _get_app()
    api_v1.dependency_overrides[get_okh_service] = lambda: MagicMock()

    with patch(
        "src.core.api.routes.okh.resolve_okh_file_bytes",
        new=AsyncMock(side_effect=OkhFileNotFoundError("missing")),
    ):
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                resp = await client.get(f"/v1/api/okh/{_MANIFEST_ID}/files/missing.pdf")

            assert resp.status_code == 404
        finally:
            api_v1.dependency_overrides.clear()
