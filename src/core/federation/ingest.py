"""Validate and persist signed manifests from followed federation peers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..utils.logging import get_logger
from ..validation.model_validator import validate_okh_manifest
from .catalog import manifest_content_hash
from .identity import canonical_json_bytes, did_to_public_key
from .models import SignedManifestRecord

if TYPE_CHECKING:
    from ..services.okh_service import OKHService
    from .store import FederationStore

logger = get_logger(__name__)


class IngestError(Exception):
    """Manifest failed verification, validation, or policy checks."""


@dataclass
class IngestResult:
    action: str  # "stored" | "skipped"
    content_hash: str | None = None
    reason: str | None = None


def verify_signed_record(record: SignedManifestRecord) -> None:
    """Verify catalog and manifest signatures and content hash."""
    publisher_key = did_to_public_key(record.catalog_record.publisher_did)
    catalog_sig = bytes.fromhex(record.catalog_record.signature)
    catalog_payload = canonical_json_bytes(record.catalog_record.record_payload())
    try:
        publisher_key.verify(catalog_sig, catalog_payload)
    except Exception as exc:
        raise IngestError("invalid catalog record signature") from exc

    manifest_sig = bytes.fromhex(record.manifest_signature)
    manifest_payload = canonical_json_bytes(record.manifest)
    try:
        publisher_key.verify(manifest_sig, manifest_payload)
    except Exception as exc:
        raise IngestError("invalid manifest signature") from exc

    computed = manifest_content_hash(record.manifest)
    if computed != record.catalog_record.content_hash:
        raise IngestError("content hash mismatch")


async def verify_and_store(
    record: SignedManifestRecord,
    *,
    publisher_did: str,
    store: FederationStore,
    okh_service: OKHService,
    local_content_hashes: set[str],
) -> IngestResult:
    """
    Verify a remote signed record and persist if allowed.

    Requires ``publisher_did`` to be on the local follow allowlist.
    """
    if not store.is_followed(publisher_did):
        raise IngestError(f"publisher {publisher_did} is not followed")

    verify_signed_record(record)

    content_hash = record.catalog_record.content_hash
    if content_hash in local_content_hashes:
        return IngestResult(
            action="skipped",
            content_hash=content_hash,
            reason="already_present",
        )

    validation = validate_okh_manifest(record.manifest)
    if not validation.valid:
        msg = "; ".join(validation.errors[:3]) or "validation failed"
        raise IngestError(f"OKH validation failed: {msg}")

    await okh_service.create(record.manifest)
    logger.info(
        f"Ingested federated manifest {record.catalog_record.manifest_id} "
        f"from {publisher_did}"
    )
    return IngestResult(action="stored", content_hash=content_hash)
