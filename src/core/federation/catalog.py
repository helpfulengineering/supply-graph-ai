"""Build signed federation catalog from local OKH manifests."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Any

from .identity import NodeIdentity, canonical_json_bytes
from .merkle import merkle_root
from .models import CatalogRecord, SignedManifestRecord, utc_now

if TYPE_CHECKING:
    from ..services.okh_service import OKHService


@dataclass
class CatalogIndex:
    """In-memory catalog snapshot for API responses."""

    records: list[CatalogRecord]
    signed_by_hash: dict[str, SignedManifestRecord] = field(default_factory=dict)
    merkle_root: str = ""
    record_count: int = 0

    def get_signed_record(self, content_hash: str) -> SignedManifestRecord | None:
        return self.signed_by_hash.get(content_hash)


def manifest_content_hash(manifest: dict[str, Any]) -> str:
    """Stable content address for a manifest dict."""
    digest = hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()
    return f"sha256:{digest}"


def _manifest_updated_at(manifest_dict: dict[str, Any]) -> datetime:
    raw = manifest_dict.get("version_date")
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return datetime.combine(raw, datetime.min.time(), tzinfo=timezone.utc)
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass
    return utc_now()


def _sign_catalog_record(
    identity: NodeIdentity, record: CatalogRecord
) -> CatalogRecord:
    signature = identity.sign_json(record.record_payload()).hex()
    return record.model_copy(update={"signature": signature})


async def build_catalog_index(
    okh_service: OKHService,
    identity: NodeIdentity,
    *,
    page_size: int = 10_000,
) -> CatalogIndex:
    """List OKH manifests from storage and build signed catalog entries."""
    manifests, total = await okh_service.list(page=1, page_size=page_size)
    records: list[CatalogRecord] = []
    signed_by_hash: dict[str, SignedManifestRecord] = {}

    for manifest in manifests:
        manifest_dict = manifest.to_dict()
        content_hash = manifest_content_hash(manifest_dict)
        record = CatalogRecord(
            manifest_id=manifest.id,
            content_hash=content_hash,
            title=manifest.title,
            version=manifest.version,
            updated_at=_manifest_updated_at(manifest_dict),
            publisher_did=identity.did,
            signature="",
        )
        signed_record = _sign_catalog_record(identity, record)
        manifest_sig = identity.sign_json(manifest_dict).hex()
        records.append(signed_record)
        signed_by_hash[content_hash] = SignedManifestRecord(
            catalog_record=signed_record,
            manifest=manifest_dict,
            manifest_signature=manifest_sig,
        )

    leaf_hashes = [r.content_hash for r in records]
    root = merkle_root(leaf_hashes)
    return CatalogIndex(
        records=records,
        signed_by_hash=signed_by_hash,
        merkle_root=root,
        record_count=total,
    )
