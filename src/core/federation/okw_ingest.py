"""Validate and persist redacted OKW projections from followed peers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..utils.logging import get_logger
from .catalog import manifest_content_hash
from .identity import canonical_json_bytes, did_to_public_key
from .okw_catalog import SignedOkwRecord

if TYPE_CHECKING:
    from ..services.okw_service import OKWService
    from .store import FederationStore

logger = get_logger(__name__)


class OkwIngestError(Exception):
    """OKW federation ingest failed."""


@dataclass
class OkwIngestResult:
    action: str  # stored | skipped
    content_hash: str | None = None
    reason: str | None = None


def verify_signed_okw_record(record: SignedOkwRecord) -> None:
    publisher_key = did_to_public_key(record.catalog_record.publisher_did)
    catalog_sig = bytes.fromhex(record.catalog_record.signature)
    catalog_payload = canonical_json_bytes(record.catalog_record.record_payload())
    try:
        publisher_key.verify(catalog_sig, catalog_payload)
    except Exception as exc:
        raise OkwIngestError("invalid OKW catalog signature") from exc

    facility_sig = bytes.fromhex(record.facility_signature)
    try:
        publisher_key.verify(facility_sig, canonical_json_bytes(record.facility))
    except Exception as exc:
        raise OkwIngestError("invalid OKW facility signature") from exc

    if manifest_content_hash(record.facility) != record.catalog_record.content_hash:
        raise OkwIngestError("OKW content hash mismatch")


async def verify_and_store_okw(
    record: SignedOkwRecord,
    *,
    publisher_did: str,
    store: FederationStore,
    okw_service: OKWService,
    local_content_hashes: set[str],
) -> OkwIngestResult:
    if not store.is_followed(publisher_did):
        raise OkwIngestError(f"publisher {publisher_did} is not followed")

    verify_signed_okw_record(record)
    content_hash = record.catalog_record.content_hash
    if content_hash in local_content_hashes:
        return OkwIngestResult(
            action="skipped",
            content_hash=content_hash,
            reason="already_present",
        )

    facility_id = record.catalog_record.facility_id
    existing = await okw_service.get(facility_id)
    if existing is not None:
        existing_proj = await okw_service.project_for_visibility(existing)
        local_hash = manifest_content_hash(
            existing_proj if existing_proj else existing.to_dict()
        )
        reason = "already_present" if local_hash == content_hash else "id_conflict"
        return OkwIngestResult(
            action="skipped",
            content_hash=content_hash,
            reason=reason,
        )

    # create() stamps private visibility by default
    await okw_service.create(record.facility)
    logger.info(f"Ingested federated OKW {facility_id} from {publisher_did}")
    return OkwIngestResult(action="stored", content_hash=content_hash)
