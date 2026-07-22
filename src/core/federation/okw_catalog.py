"""Signed OKW federation catalog (separate Merkle tree from OKH)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, Field

from ..models.visibility import is_shareable
from .catalog import manifest_content_hash
from .identity import NodeIdentity
from .merkle import merkle_root
from .models import utc_now

if TYPE_CHECKING:
    from ..services.okw_service import OKWService


class OkwCatalogRecord(BaseModel):
    """Signed index entry for one redacted OKW facility projection."""

    facility_id: UUID
    content_hash: str
    name: str
    updated_at: datetime
    publisher_did: str
    visibility: str
    signature: str = Field(
        description="Hex-encoded Ed25519 signature over canonical record"
    )

    def record_payload(self) -> dict[str, Any]:
        return {
            "facility_id": str(self.facility_id),
            "content_hash": self.content_hash,
            "name": self.name,
            "updated_at": self.updated_at.isoformat(),
            "publisher_did": self.publisher_did,
            "visibility": self.visibility,
        }


class SignedOkwRecord(BaseModel):
    catalog_record: OkwCatalogRecord
    facility: dict[str, Any]
    facility_signature: str


@dataclass
class OkwCatalogIndex:
    records: list[OkwCatalogRecord]
    signed_by_hash: dict[str, SignedOkwRecord] = field(default_factory=dict)
    merkle_root: str = ""
    record_count: int = 0

    def get_signed_record(self, content_hash: str) -> SignedOkwRecord | None:
        return self.signed_by_hash.get(content_hash)


def _sign_okw_record(
    identity: NodeIdentity, record: OkwCatalogRecord
) -> OkwCatalogRecord:
    signature = identity.sign_json(record.record_payload()).hex()
    return record.model_copy(update={"signature": signature})


async def build_okw_catalog_index(
    okw_service: OKWService,
    identity: NodeIdentity,
    *,
    page_size: int = 10_000,
) -> OkwCatalogIndex:
    """Build signed OKW catalog from shareable facilities (redacted projections)."""
    facilities, _total = await okw_service.list(page=1, page_size=page_size)
    records: list[OkwCatalogRecord] = []
    signed_by_hash: dict[str, SignedOkwRecord] = {}

    for facility in facilities:
        visibility = await okw_service.get_visibility(facility.id)
        if not is_shareable(visibility):
            continue

        projection = await okw_service.project_for_visibility(facility)
        if not projection:
            continue

        content_hash = manifest_content_hash(projection)
        record = OkwCatalogRecord(
            facility_id=facility.id,
            content_hash=content_hash,
            name=projection.get("name") or facility.name,
            updated_at=utc_now(),
            publisher_did=identity.did,
            visibility=visibility.value,
            signature="",
        )
        signed = _sign_okw_record(identity, record)
        facility_sig = identity.sign_json(projection).hex()
        records.append(signed)
        signed_by_hash[content_hash] = SignedOkwRecord(
            catalog_record=signed,
            facility=projection,
            facility_signature=facility_sig,
        )

    leaf_hashes = [r.content_hash for r in records]
    return OkwCatalogIndex(
        records=records,
        signed_by_hash=signed_by_hash,
        merkle_root=merkle_root(leaf_hashes),
        record_count=len(records),
    )
