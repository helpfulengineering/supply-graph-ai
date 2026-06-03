"""Anti-entropy sync: Merkle digest exchange and record pull."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import httpx

from ..utils.logging import get_logger
from .ingest import IngestError, verify_and_store
from .models import (
    PeerState,
    SignedManifestRecord,
    SyncDigest,
    SyncDigestResponse,
    utc_now,
)
from .peer_registry import build_federation_base_url
from .rate_limit import get_federation_rate_limiter

if TYPE_CHECKING:
    from .service import FederationService

logger = get_logger(__name__)

_SYNC_DIGEST_PATH = "/v1/api/federation/sync/digest"
_RECORDS_PATH = "/v1/api/federation/records/"


@dataclass
class SyncPeerResult:
    peer_did: str
    base_url: str
    pulled: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    rate_limited: bool = False


def compute_missing_hashes(
    our_hashes: set[str],
    requester_hashes: set[str],
) -> list[str]:
    """Hashes we have that the requester is missing."""
    return sorted(our_hashes - requester_hashes)


def build_sync_digest(
    *,
    merkle_root: str,
    record_count: int,
    publisher_did: str,
    leaf_hashes: list[str],
) -> SyncDigest:
    return SyncDigest(
        merkle_root=merkle_root,
        record_count=record_count,
        publisher_did=publisher_did,
        leaf_hashes=leaf_hashes,
    )


def respond_to_sync_digest(
    digest: SyncDigest,
    *,
    local_merkle_root: str,
    local_leaf_hashes: set[str],
) -> SyncDigestResponse:
    """Compute missing hashes for a peer's digest request."""
    if digest.merkle_root == local_merkle_root and digest.record_count == len(
        local_leaf_hashes
    ):
        return SyncDigestResponse(missing_hashes=[])
    requester = set(digest.leaf_hashes)
    return SyncDigestResponse(
        missing_hashes=compute_missing_hashes(local_leaf_hashes, requester)
    )


async def _post_digest(
    client: httpx.AsyncClient,
    base_url: str,
    digest: SyncDigest,
) -> SyncDigestResponse:
    url = f"{build_federation_base_url(base_url)}{_SYNC_DIGEST_PATH}"
    response = await client.post(url, json=digest.model_dump(mode="json"))
    response.raise_for_status()
    return SyncDigestResponse.model_validate(response.json())


async def _fetch_record(
    client: httpx.AsyncClient,
    base_url: str,
    content_hash: str,
) -> SignedManifestRecord:
    normalized = (
        content_hash if content_hash.startswith("sha256:") else f"sha256:{content_hash}"
    )
    url = f"{build_federation_base_url(base_url)}{_RECORDS_PATH}{normalized}"
    response = await client.get(url)
    response.raise_for_status()
    return SignedManifestRecord.model_validate(response.json())


async def sync_with_peer(
    service: FederationService,
    peer: PeerState,
) -> SyncPeerResult:
    """
    Pull missing catalog records from a followed peer via anti-entropy.

    Returns counts of stored and skipped records; errors are collected per hash.
    """
    from ..services.okh_service import OKHService

    assert service.identity is not None
    assert service.store is not None

    if not peer.followed and not service.store.is_followed(peer.did):
        return SyncPeerResult(
            peer_did=peer.did,
            base_url=peer.base_url,
            errors=[f"peer {peer.did} is not followed"],
        )

    result = SyncPeerResult(peer_did=peer.did, base_url=peer.base_url)
    local_index = await service.build_catalog_index()
    local_hashes = {r.content_hash for r in local_index.records}
    digest = build_sync_digest(
        merkle_root=local_index.merkle_root,
        record_count=local_index.record_count,
        publisher_did=service.identity.did,
        leaf_hashes=sorted(local_hashes),
    )

    okh_service = await OKHService.get_instance()
    limiter = get_federation_rate_limiter()
    outbound_limit = limiter.check(peer.did)
    if not outbound_limit.allowed:
        service.metrics.record_rate_limit_rejection()
        return SyncPeerResult(
            peer_did=peer.did,
            base_url=peer.base_url,
            errors=[f"outbound rate limit exceeded for {peer.did}"],
            rate_limited=True,
        )
    service.metrics.record_outbound_digest()

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            digest_response = await _post_digest(client, peer.base_url, digest)
        except Exception as e:
            result.errors.append(f"digest exchange failed: {e}")
            return result

        if not digest_response.missing_hashes:
            _update_peer_sync_state(service, peer, result)
            return result

        for content_hash in digest_response.missing_hashes:
            try:
                signed = await _fetch_record(client, peer.base_url, content_hash)
                ingest_result = await verify_and_store(
                    signed,
                    publisher_did=signed.catalog_record.publisher_did,
                    store=service.store,
                    okh_service=okh_service,
                    local_content_hashes=local_hashes,
                )
                if ingest_result.action == "stored":
                    result.pulled += 1
                    local_hashes.add(content_hash)
                else:
                    result.skipped += 1
            except (IngestError, httpx.HTTPError) as e:
                result.errors.append(f"{content_hash}: {e}")
                logger.warning(
                    f"Sync ingest failed for {content_hash} from {peer.did}: {e}"
                )

    _update_peer_sync_state(service, peer, result)
    return result


def _update_peer_sync_state(
    service: FederationService,
    peer: PeerState,
    result: SyncPeerResult,
) -> None:
    assert service.store is not None
    updated = peer.model_copy(
        update={
            "last_sync_at": utc_now(),
            "records_synced": peer.records_synced + result.pulled,
        }
    )
    service.store.upsert_peer(updated)
