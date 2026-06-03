"""Tests for federation status endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.core.federation.metrics import FederationSyncMetrics
from tests.federation.test_federation_routes import _federation_app, _sample_index


@pytest.mark.unit
@pytest.mark.asyncio
async def test_federation_status_endpoint(monkeypatch) -> None:
    from src.config import settings
    from src.core.federation.identity import generate_identity
    from src.core.federation.node_role import NodeRole

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)

    identity = generate_identity("Status Peer")
    index = _sample_index()

    mock_service = MagicMock()
    mock_service.enabled = True
    mock_service.identity = identity
    mock_service.role = NodeRole.PEER
    mock_service.capabilities.expose_federation_api = True
    mock_service.ensure_federation_ready = AsyncMock(return_value=None)
    mock_service.build_catalog_index = AsyncMock(return_value=index)
    mock_service.get_status = AsyncMock(
        return_value={
            "did": identity.did,
            "display_name": identity.display_name,
            "role": "peer",
            "catalog_record_count": 1,
            "merkle_root": index.merkle_root,
            "peer_count": 0,
            "followed_peer_count": 0,
            "sync_interval_sec": 60,
            "mdns_enabled": False,
            "background_sync_running": True,
            "manual_peers": [],
            "metrics": FederationSyncMetrics(),
        }
    )

    with patch(
        "src.core.api.routes.federation.FederationService.get_instance",
        AsyncMock(return_value=mock_service),
    ):
        transport = httpx.ASGITransport(app=_federation_app())
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get("/v1/api/federation/status")
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["did"] == identity.did
            assert body["catalog_record_count"] == 1
            assert body["background_sync_running"] is True
            assert "metrics" in body
