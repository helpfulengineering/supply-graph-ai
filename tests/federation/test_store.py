"""Unit tests for federation local store."""

from __future__ import annotations

import pytest

from src.core.federation.models import PeerState
from src.core.federation.store import FederationStore


@pytest.mark.unit
def test_follow_and_peer_round_trip(tmp_path) -> None:
    store = FederationStore(tmp_path)
    peer = PeerState(
        did="did:key:z6Mktest",
        base_url="http://ohm-peer-b:8001",
        display_name="Peer B",
        source="manual",
    )
    store.upsert_peer(peer)
    store.set_followed(peer.did, True)

    assert store.is_followed(peer.did)
    peers = store.load_peers()
    assert len(peers) == 1
    assert peers[0].followed is True

    store.set_followed(peer.did, False)
    assert not store.is_followed(peer.did)
