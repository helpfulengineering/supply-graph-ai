"""Anti-entropy sync for the OKW catalog (separate from OKH)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import httpx

from ..utils.logging import get_logger
from .models import PeerState, SyncDigestResponse, utc_now
from .okw_catalog import SignedOkwRecord
from .okw_ingest import OkwIngestError, verify_and_store_okw
from .peer_registry import build_federation_base_url
from .rate_limit import get_federation_rate_limiter
from .sync import build_sync_digest

if TYPE_CHECKING:
    from .service import FederationService

logger = get_logger(__name__)

_OKW_DIGEST_PATH = "/v1/api/federation/okw/sync/digest"
_OKW_RECORDS_PATH = "/v1/api/federation/okw/records/"


@dataclass
class OkwSyncPeerResult:
    peer_did: str
    base_url: str
    pulled: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


async def sync_okw_with_peer(
    service: FederationService,
    peer: PeerState,
) -> OkwSyncPeerResult:
    from ..services.okw_service import OKWService

    if service.identity is None or service.store is None:
        raise RuntimeError("Federation identity or store not loaded")
    store = service.store
    identity = service.identity

    if not peer.followed and not store.is_followed(peer.did):
        return OkwSyncPeerResult(
            peer_did=peer.did,
            base_url=peer.base_url,
            errors=[f"peer {peer.did} is not followed"],
        )

    result = OkwSyncPeerResult(peer_did=peer.did, base_url=peer.base_url)
    local_index = await service.build_okw_catalog_index()
    local_hashes = {r.content_hash for r in local_index.records}
    digest = build_sync_digest(
        merkle_root=local_index.merkle_root,
        record_count=local_index.record_count,
        publisher_did=identity.did,
        leaf_hashes=sorted(local_hashes),
    )

    limiter = get_federation_rate_limiter()
    if not limiter.check(peer.did).allowed:
        result.errors.append(f"outbound rate limit exceeded for {peer.did}")
        return result

    okw_service = await OKWService.get_instance()
    peer_base = build_federation_base_url(peer.base_url)
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{peer_base}{_OKW_DIGEST_PATH}",
                json=digest.model_dump(mode="json"),
            )
            response.raise_for_status()
            digest_response = SyncDigestResponse.model_validate(response.json())
        except Exception as e:
            result.errors.append(f"OKW digest exchange failed: {e}")
            return result

        for content_hash in digest_response.missing_hashes:
            try:
                rec_resp = await client.get(
                    f"{peer_base}{_OKW_RECORDS_PATH}{content_hash}"
                )
                rec_resp.raise_for_status()
                signed = SignedOkwRecord.model_validate(rec_resp.json())
                ingest = await verify_and_store_okw(
                    signed,
                    publisher_did=signed.catalog_record.publisher_did,
                    store=store,
                    okw_service=okw_service,
                    local_content_hashes=local_hashes,
                )
                if ingest.action == "stored":
                    result.pulled += 1
                    local_hashes.add(content_hash)
                else:
                    result.skipped += 1
            except (OkwIngestError, httpx.HTTPError) as e:
                result.errors.append(f"{content_hash}: {e}")
                logger.warning(f"OKW sync ingest failed: {e}")

    store.upsert_peer(peer.model_copy(update={"last_sync_at": utc_now()}))
    return result
