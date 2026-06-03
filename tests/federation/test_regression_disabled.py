"""Regression: federation disabled must not affect core OHM behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


def _full_app():
    from src.core.main import app

    return app


@pytest.mark.unit
@pytest.mark.asyncio
async def test_federation_routes_404_when_disabled_by_default(monkeypatch) -> None:
    from src.config import settings

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", False)

    mock_service = MagicMock()
    mock_service.enabled = False

    async def _get_instance():
        return mock_service

    transport = httpx.ASGITransport(app=_full_app())
    with patch(
        "src.core.api.routes.federation.FederationService.get_instance",
        side_effect=_get_instance,
    ):
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            for path in (
                "/v1/api/federation/identify",
                "/v1/api/federation/catalog",
                "/v1/api/federation/status",
                "/v1/api/federation/health",
            ):
                resp = await client.get(path)
                assert resp.status_code == 404, f"{path} returned {resp.status_code}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_core_health_available_when_federation_disabled(monkeypatch) -> None:
    from src.config import settings

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", False)

    transport = httpx.ASGITransport(app=_full_app())
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json().get("status") == "ok"


@pytest.mark.unit
def test_federation_settings_default_off(monkeypatch) -> None:
    """Without OHM_FEDERATION_ENABLED in env, federation stays off."""
    monkeypatch.delenv("OHM_FEDERATION_ENABLED", raising=False)
    from src.config.settings import _get_secret_or_env

    raw = _get_secret_or_env("OHM_FEDERATION_ENABLED", "false")
    assert raw.lower() not in ("true", "1", "t")
