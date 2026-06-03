"""Unit tests for federation peer registry and manual discovery."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.core.federation.models import PeerState, utc_now
from src.core.federation.peer_registry import (
    PeerRegistry,
    build_federation_base_url,
    identify_peer,
    merge_manual_urls,
)
from src.core.federation.store import FederationStore


@pytest.mark.unit
def test_build_federation_base_url_normalizes() -> None:
    assert (
        build_federation_base_url("http://ohm-peer-b:8001/") == "http://ohm-peer-b:8001"
    )


@pytest.mark.unit
def test_merge_manual_urls_dedupes() -> None:
    urls = merge_manual_urls(
        ["http://a:8001", "http://a:8001/", "http://b:8001"],
        [],
    )
    assert urls == ["http://a:8001", "http://b:8001"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_identify_peer_parses_response() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "did": "did:key:z6Mkpeer",
                "display_name": "Peer B",
                "role": "peer",
                "ohm_version": "1.0.0",
                "catalog_record_count": 3,
                "merkle_root": "abc",
            },
        )
    )
    async with httpx.AsyncClient(transport=transport) as client:
        info = await identify_peer(client, "http://peer-b:8001")
    assert info["did"] == "did:key:z6Mkpeer"
    assert info["display_name"] == "Peer B"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_peer_registry_refresh_manual(tmp_path) -> None:
    store = FederationStore(tmp_path)
    registry = PeerRegistry(store)

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "did": "did:key:z6Mkremote",
                "display_name": "Remote",
                "role": "peer",
                "catalog_record_count": 0,
                "merkle_root": "deadbeef",
            },
        )
    )

    with patch(
        "src.core.federation.peer_registry.httpx.AsyncClient",
        return_value=httpx.AsyncClient(transport=transport),
    ):
        peers = await registry.refresh(
            manual_urls=["http://remote:8001"],
            mdns_peers=[],
            local_did="did:key:z6Mklocal",
        )

    assert len(peers) == 1
    assert peers[0].did == "did:key:z6Mkremote"
    assert peers[0].base_url == "http://remote:8001"
    assert peers[0].source == "manual"
    saved = store.load_peers()
    assert len(saved) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_peer_registry_skips_local_did(tmp_path) -> None:
    store = FederationStore(tmp_path)
    registry = PeerRegistry(store)

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "did": "did:key:z6Mklocal",
                "display_name": "Self",
                "role": "peer",
                "catalog_record_count": 0,
                "merkle_root": "x",
            },
        )
    )

    with patch(
        "src.core.federation.peer_registry.httpx.AsyncClient",
        return_value=httpx.AsyncClient(transport=transport),
    ):
        peers = await registry.refresh(
            manual_urls=["http://localhost:8001"],
            mdns_peers=[],
            local_did="did:key:z6Mklocal",
        )

    assert peers == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_peer_registry_merges_mdns_peers(tmp_path) -> None:
    from src.core.federation.discovery import DiscoveredPeer

    store = FederationStore(tmp_path)
    registry = PeerRegistry(store)

    mdns_peer = DiscoveredPeer(
        name="ohm-api._ohm._tcp.local.",
        host="192.168.1.50",
        port=8001,
        did="did:key:z6Mkmdns",
        properties={},
    )

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "did": "did:key:z6Mkmdns",
                "display_name": "mDNS Peer",
                "role": "peer",
                "catalog_record_count": 1,
                "merkle_root": "y",
            },
        )
    )

    with patch(
        "src.core.federation.peer_registry.httpx.AsyncClient",
        return_value=httpx.AsyncClient(transport=transport),
    ):
        peers = await registry.refresh(
            manual_urls=[],
            mdns_peers=[mdns_peer],
            local_did="did:key:z6Mklocal",
        )

    assert len(peers) == 1
    assert peers[0].source == "mdns"
    assert peers[0].base_url == "http://192.168.1.50:8001"
