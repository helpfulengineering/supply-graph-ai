"""Tests for FederationService peer discovery helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.core.federation.discovery import DiscoveredPeer
from src.core.federation.service import FederationService
from src.core.federation.store import FederationStore


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_peers_merges_manual_and_mdns(tmp_path, monkeypatch) -> None:
    from src.config import settings

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    monkeypatch.setattr(settings, "OHM_FEDERATION_MDNS_ENABLED", True)
    monkeypatch.setattr(settings, "OHM_FEDERATION_MANUAL_PEERS", ["http://manual:8001"])
    monkeypatch.setattr(settings, "OHM_FEDERATION_DATA_DIR", str(tmp_path))

    service = FederationService()
    service.store = FederationStore(tmp_path)
    from src.core.federation.identity import generate_identity

    from src.core.federation.node_role import NodeRole, capabilities_for_role

    service.identity = generate_identity("Local")
    service.capabilities = capabilities_for_role(NodeRole.PEER)

    mdns_peer = DiscoveredPeer(
        name="remote._ohm._tcp.local.",
        host="10.0.0.2",
        port=8001,
        did="did:key:z6Mkremote",
        properties={},
    )

    with (
        patch(
            "src.core.federation.service.browse_mdns_peers",
            return_value=[mdns_peer],
        ),
        patch(
            "src.core.federation.peer_registry.identify_peer",
            new_callable=AsyncMock,
            side_effect=[
                {
                    "did": "did:key:z6Mkmanual",
                    "display_name": "Manual",
                    "role": "peer",
                    "catalog_record_count": 0,
                    "merkle_root": "a",
                },
                {
                    "did": "did:key:z6Mkremote",
                    "display_name": "Remote",
                    "role": "peer",
                    "catalog_record_count": 0,
                    "merkle_root": "b",
                },
            ],
        ),
        patch.object(service, "ensure_federation_ready", AsyncMock()),
    ):
        updated = await service.refresh_peers()

    assert len(updated) == 2
    saved = {p.did for p in service.list_peers()}
    assert "did:key:z6Mkmanual" in saved
    assert "did:key:z6Mkremote" in saved
