"""Persistent federation state (peers, follows) on local disk."""

from __future__ import annotations

import json
from pathlib import Path

from .models import CuratedList, ListSubscription, PeerState


class FederationStore:
    """JSON-file backed store for federation peer/follow state."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._peers_path = self.data_dir / "peers.json"
        self._follows_path = self.data_dir / "follows.json"
        self._lists_path = self.data_dir / "lists.json"
        self._subscriptions_path = self.data_dir / "subscriptions.json"

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

    def load_lists(self) -> list[CuratedList]:
        if not self._lists_path.is_file():
            return []
        raw = json.loads(self._lists_path.read_text(encoding="utf-8"))
        return [CuratedList.model_validate(item) for item in raw]

    def get_list(self, list_id: str) -> CuratedList | None:
        for document in self.load_lists():
            if document.list_id == list_id:
                return document
        return None

    def save_list(self, document: CuratedList) -> None:
        by_id = {item.list_id: item for item in self.load_lists()}
        by_id[document.list_id] = document
        payload = [
            item.model_dump(mode="json", exclude_none=True) for item in by_id.values()
        ]
        self._lists_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_subscriptions(self) -> list[ListSubscription]:
        if not self._subscriptions_path.is_file():
            return []
        raw = json.loads(self._subscriptions_path.read_text(encoding="utf-8"))
        return [ListSubscription.model_validate(item) for item in raw]

    def save_subscription(self, subscription: ListSubscription) -> None:
        kept = [
            item
            for item in self.load_subscriptions()
            if not (
                item.peer_url == subscription.peer_url
                and item.list_id == subscription.list_id
            )
        ]
        kept.append(subscription)
        payload = [item.model_dump(mode="json") for item in kept]
        self._subscriptions_path.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    def delete_subscription(
        self, peer_url: str, list_id: str
    ) -> ListSubscription | None:
        current = self.load_subscriptions()
        removed = next(
            (
                item
                for item in current
                if item.peer_url == peer_url and item.list_id == list_id
            ),
            None,
        )
        if removed is None:
            return None
        kept = [item for item in current if item is not removed]
        payload = [item.model_dump(mode="json") for item in kept]
        self._subscriptions_path.write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        return removed
