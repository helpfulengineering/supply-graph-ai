"""Pydantic models for federation catalog and peer state."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ..models.attestation import Attestation
from ..models.provenance import RecordProvenance


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NodeInfo(BaseModel):
    """Local node metadata exposed via GET /federation/identify."""

    did: str
    display_name: str
    role: str
    ohm_version: str | None = None
    catalog_record_count: int = 0
    merkle_root: str | None = None


class PackagePointer(BaseModel):
    """Content-addressed package artifact advertised on a catalog record.

    Out of the OKH design content hash; included in the node-signed payload.
    """

    bundle_hash: str
    byte_size: int
    filename: str | None = None


class CatalogRecord(BaseModel):
    """Signed index entry for one OKH manifest."""

    manifest_id: UUID
    content_hash: str
    title: str
    version: str
    updated_at: datetime
    publisher_did: str
    # Record-level authorship, distinct from publisher_did (the relaying node).
    # Rides the node-signed payload so it is tamper-evident in transit.
    provenance: RecordProvenance | None = None
    # Durable attestations about this design / its releases (Slice 6).
    attestations: list[Attestation] | None = None
    # Optional package artifact pointer (separate transport channel).
    package: PackagePointer | None = None
    signature: str = Field(
        description="Hex-encoded Ed25519 signature over canonical record"
    )

    def record_payload(self) -> dict[str, Any]:
        """Fields included in the signed payload (excludes signature)."""
        payload: dict[str, Any] = {
            "manifest_id": str(self.manifest_id),
            "content_hash": self.content_hash,
            "title": self.title,
            "version": self.version,
            "updated_at": self.updated_at.isoformat(),
            "publisher_did": self.publisher_did,
        }
        # Only present when a record carries provenance, so existing unsigned-
        # provenance records keep their exact payload (and signatures stay valid).
        if self.provenance is not None:
            payload["provenance"] = self.provenance.model_dump(mode="json")
        if self.attestations:
            payload["attestations"] = [
                a.model_dump(mode="json") for a in self.attestations
            ]
        if self.package is not None:
            payload["package"] = self.package.model_dump(mode="json")
        return payload


class SyncDigest(BaseModel):
    """Anti-entropy digest exchange."""

    merkle_root: str
    record_count: int
    publisher_did: str
    leaf_hashes: list[str] = Field(default_factory=list)


class SyncDigestResponse(BaseModel):
    """Peer response listing hashes the requester is missing."""

    missing_hashes: list[str] = Field(default_factory=list)


class PeerState(BaseModel):
    """Known remote peer and sync metadata."""

    did: str
    base_url: str
    display_name: str | None = None
    source: str = "manual"
    followed: bool = False
    last_seen_at: datetime | None = None
    last_sync_at: datetime | None = None
    records_synced: int = 0


class CuratedListEntry(BaseModel):
    """One pinned design on a curated list."""

    content_hash: str
    supersedes: str | None = None

    def signing_dict(self) -> dict[str, str]:
        item = {"content_hash": self.content_hash}
        if self.supersedes:
            item["supersedes"] = self.supersedes
        return item


class CuratedListWrite(BaseModel):
    """What a publisher sends to create or replace a list."""

    name: str
    entries: list[CuratedListEntry]
    publisher_did: str | None = None


class ListSubscriptionWrite(BaseModel):
    """Where to fetch the list a node wants to follow."""

    peer_url: str
    list_id: str


class ListSubscription(BaseModel):
    """A follow scoped to one list on one node."""

    peer_url: str
    list_id: str
    name: str
    publisher_did: str
    sequence: int


class CuratedList(BaseModel):
    """The signed current membership of a curated list."""

    list_id: str
    name: str
    publisher_did: str
    sequence: int
    entries: list[CuratedListEntry]
    signature: str = ""

    def record_payload(self) -> dict[str, Any]:
        """Fields covered by the signature. The signature itself is excluded."""
        entries = sorted(self.entries, key=lambda entry: entry.content_hash)
        return {
            "list_id": self.list_id,
            "name": self.name,
            "publisher_did": self.publisher_did,
            "sequence": self.sequence,
            "entries": [entry.signing_dict() for entry in entries],
        }


class SignedManifestRecord(BaseModel):
    """Full manifest payload transferred between peers."""

    catalog_record: CatalogRecord
    manifest: dict[str, Any]
    manifest_signature: str = Field(
        description="Hex signature over canonical manifest JSON"
    )
