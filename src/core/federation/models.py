"""Pydantic models for federation catalog and peer state."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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


class CatalogRecord(BaseModel):
    """Signed index entry for one OKH manifest."""

    manifest_id: UUID
    content_hash: str
    title: str
    version: str
    updated_at: datetime
    publisher_did: str
    signature: str = Field(
        description="Hex-encoded Ed25519 signature over canonical record"
    )

    def record_payload(self) -> dict[str, Any]:
        """Fields included in the signed payload (excludes signature)."""
        return {
            "manifest_id": str(self.manifest_id),
            "content_hash": self.content_hash,
            "title": self.title,
            "version": self.version,
            "updated_at": self.updated_at.isoformat(),
            "publisher_did": self.publisher_did,
        }


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


class SignedManifestRecord(BaseModel):
    """Full manifest payload transferred between peers."""

    catalog_record: CatalogRecord
    manifest: dict[str, Any]
    manifest_signature: str = Field(
        description="Hex signature over canonical manifest JSON"
    )
