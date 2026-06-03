"""Peer discovery sources and registry merge (manual URLs + mDNS)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from ..utils.logging import get_logger
from .discovery import DiscoveredPeer, base_url_from_service
from .models import PeerState, utc_now
from .store import FederationStore

logger = get_logger(__name__)

_IDENTIFY_PATH = "/v1/api/federation/identify"


def build_federation_base_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid peer URL: {url}")
    return f"{parsed.scheme}://{parsed.netloc}"


def merge_manual_urls(
    configured: list[str],
    extra: list[str],
) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in [*configured, *extra]:
        if not raw.strip():
            continue
        try:
            normalized = build_federation_base_url(raw)
        except ValueError:
            logger.warning(f"Skipping invalid manual peer URL: {raw}")
            continue
        if normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out


async def identify_peer(client: httpx.AsyncClient, base_url: str) -> dict[str, Any]:
    url = f"{build_federation_base_url(base_url)}{_IDENTIFY_PATH}"
    response = await client.get(url, timeout=10.0)
    response.raise_for_status()
    return response.json()


class PeerRegistry:
    """Merge discovered peers into persistent local state."""

    def __init__(self, store: FederationStore) -> None:
        self.store = store

    async def refresh(
        self,
        *,
        manual_urls: list[str],
        mdns_peers: list[DiscoveredPeer],
        local_did: str,
        extra_manual_urls: list[str] | None = None,
    ) -> list[PeerState]:
        """
        Resolve manual and mDNS peers via ``/identify``, upsert into store.

        Returns newly updated peer records (excluding self).
        """
        targets: list[tuple[str, str]] = []  # (base_url, source)

        for url in merge_manual_urls(manual_urls, extra_manual_urls or []):
            targets.append((url, "manual"))

        for peer in mdns_peers:
            targets.append((base_url_from_service(peer), "mdns"))

        updated: list[PeerState] = []
        seen_urls: set[str] = set()

        async with httpx.AsyncClient() as client:
            for base_url, source in targets:
                if base_url in seen_urls:
                    continue
                seen_urls.add(base_url)
                try:
                    info = await identify_peer(client, base_url)
                except Exception as e:
                    logger.warning(f"Could not identify peer at {base_url}: {e}")
                    continue

                did = str(info.get("did", ""))
                if not did or did == local_did:
                    continue

                existing = {p.did: p for p in self.store.load_peers()}
                prior = existing.get(did)
                peer = PeerState(
                    did=did,
                    base_url=base_url,
                    display_name=info.get("display_name"),
                    source=source,
                    followed=prior.followed if prior else False,
                    last_seen_at=utc_now(),
                    last_sync_at=prior.last_sync_at if prior else None,
                    records_synced=prior.records_synced if prior else 0,
                )
                self.store.upsert_peer(peer)
                updated.append(peer)

        return updated

    def list_peers(self) -> list[PeerState]:
        return self.store.load_peers()
