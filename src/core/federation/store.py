"""Persistent federation state (peers, follows) on local disk."""

from __future__ import annotations

import json
from pathlib import Path

from .models import PeerState


class FederationStore:
    """JSON-file backed store for federation peer/follow state."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._peers_path = self.data_dir / "peers.json"
        self._follows_path = self.data_dir / "follows.json"

    def load_peers(self) -> list[PeerState]:
        if not self._peers_path.is_file():
            return []
        raw = json.loads(self._peers_path.read_text(encoding="utf-8"))
        return [PeerState.model_validate(item) for item in raw]

    def save_peers(self, peers: list[PeerState]) -> None:
        payload = [p.model_dump(mode="json") for p in peers]
        self._peers_path.write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    def load_followed_dids(self) -> set[str]:
        if not self._follows_path.is_file():
            return set()
        raw = json.loads(self._follows_path.read_text(encoding="utf-8"))
        return set(raw)

    def save_followed_dids(self, dids: set[str]) -> None:
        self._follows_path.write_text(
            json.dumps(sorted(dids), indent=2),
            encoding="utf-8",
        )

    def upsert_peer(self, peer: PeerState) -> None:
        peers = self.load_peers()
        by_did = {p.did: p for p in peers}
        by_did[peer.did] = peer
        self.save_peers(list(by_did.values()))

    def set_followed(self, did: str, followed: bool = True) -> None:
        followed_dids = self.load_followed_dids()
        if followed:
            followed_dids.add(did)
        else:
            followed_dids.discard(did)
        self.save_followed_dids(followed_dids)
        peers = self.load_peers()
        for peer in peers:
            if peer.did == did:
                peer.followed = followed
        self.save_peers(peers)

    def is_followed(self, did: str) -> bool:
        return did in self.load_followed_dids()
