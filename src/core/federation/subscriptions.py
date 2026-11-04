"""Subscribe to a curated list served by another node."""

from __future__ import annotations

import httpx

from .identity import verify_payload
from .ingest import verify_and_store
from .models import CuratedList, ListMark, ListSubscription, SignedManifestRecord
from .peer_registry import build_federation_base_url
from .store import FederationStore
from .sync import SyncPeerResult


class ListSignatureInvalid(Exception):
    """The fetched document is not signed by its publisher_did."""


async def fetch_remote_list(peer_url: str, list_id: str) -> CuratedList:
    url = f"{build_federation_base_url(peer_url)}/v1/api/federation/lists/{list_id}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
    return CuratedList.model_validate(response.json())


async def subscribe(
    store: FederationStore, peer_url: str, list_id: str
) -> ListSubscription:
    """Remember a peer's list after its signature verifies."""
    document = await fetch_remote_list(peer_url, list_id)
    if not verify_payload(
        document.publisher_did, document.record_payload(), document.signature
    ):
        raise ListSignatureInvalid(document.publisher_did)
    subscription = ListSubscription(
        peer_url=build_federation_base_url(peer_url),
        list_id=document.list_id,
        name=document.name,
        publisher_did=document.publisher_did,
        sequence=document.sequence,
    )
    store.save_subscription(subscription)
    return subscription


def unsubscribe(
    store: FederationStore, peer_url: str, list_id: str
) -> ListSubscription | None:
    return store.delete_subscription(build_federation_base_url(peer_url), list_id)


def _label_list_changes(
    store: FederationStore, subscription: ListSubscription, document: CuratedList
) -> None:
    """Label pins a verified list replaced or dropped. The designs stay."""
    current = {entry.content_hash for entry in document.entries}
    replaced = {entry.supersedes for entry in document.entries if entry.supersedes}
    previous = store.load_seen_pins(subscription.peer_url, document.list_id)
    for content_hash in sorted(previous - current - replaced):
        store.save_mark(
            ListMark(
                peer_url=subscription.peer_url,
                list_id=document.list_id,
                list_name=document.name,
                content_hash=content_hash,
                status="removed",
            )
        )
    for entry in document.entries:
        if not entry.supersedes:
            continue
        store.save_mark(
            ListMark(
                peer_url=subscription.peer_url,
                list_id=document.list_id,
                list_name=document.name,
                content_hash=entry.supersedes,
                status="superseded",
                superseded_by=entry.content_hash,
            )
        )
    store.save_seen_pins(subscription.peer_url, document.list_id, current)


async def _fetch_record(peer_url: str, content_hash: str) -> SignedManifestRecord:
    url = (
        f"{build_federation_base_url(peer_url)}"
        f"/v1/api/federation/records/{content_hash}"
    )
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
    return SignedManifestRecord.model_validate(response.json())


async def sync_subscribed_lists(
    store: FederationStore,
    okh,
    local_hashes: set[str],
) -> list[SyncPeerResult]:
    """Pull the designs named on each subscribed list, and nothing else."""
    results: list[SyncPeerResult] = []
    for subscription in store.load_subscriptions():
        result = SyncPeerResult(
            peer_did=subscription.publisher_did,
            base_url=subscription.peer_url,
        )
        try:
            document = await fetch_remote_list(
                subscription.peer_url, subscription.list_id
            )
        except Exception as exc:
            result.errors.append(f"list fetch failed: {exc}")
            results.append(result)
            continue
        if not verify_payload(
            document.publisher_did, document.record_payload(), document.signature
        ):
            result.errors.append("The list signature does not verify")
            results.append(result)
            continue
        _label_list_changes(store, subscription, document)
        for entry in document.entries:
            if entry.content_hash in local_hashes:
                result.skipped += 1
                continue
            try:
                signed = await _fetch_record(subscription.peer_url, entry.content_hash)
                ingest_result = await verify_and_store(
                    signed,
                    publisher_did=signed.catalog_record.publisher_did,
                    store=store,
                    okh_service=okh,
                    local_content_hashes=local_hashes,
                    require_follow=False,
                )
            except Exception as exc:
                result.errors.append(f"{entry.content_hash}: {exc}")
                continue
            if ingest_result.action == "stored":
                result.pulled += 1
                local_hashes.add(entry.content_hash)
            else:
                result.skipped += 1
        results.append(result)
    return results
