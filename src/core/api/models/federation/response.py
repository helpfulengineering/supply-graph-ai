"""Federation API response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.core.federation.models import CatalogRecord, PeerState, SignedManifestRecord


class FederationSyncMetricsResponse(BaseModel):
    total_records_pulled: int = 0
    total_records_skipped: int = 0
    total_sync_runs: int = 0
    total_digest_requests_inbound: int = 0
    total_digest_requests_outbound: int = 0
    total_rate_limit_rejections: int = 0
    last_sync_at: datetime | None = None
    last_background_sync_at: datetime | None = None
    per_peer_pulled: dict[str, int] = Field(default_factory=dict)


class FederationStatusResponse(BaseModel):
    did: str
    display_name: str
    role: str
    catalog_record_count: int
    merkle_root: str
    peer_count: int
    followed_peer_count: int
    sync_interval_sec: int
    rate_limit_per_min: int = 60
    mdns_enabled: bool
    background_sync_running: bool
    manual_peers: list[str] = Field(default_factory=list)
    metrics: FederationSyncMetricsResponse
    security_mode: str | None = None
    seed_peer_url: str | None = None


class IdentifyResponse(BaseModel):
    did: str
    display_name: str
    role: str
    ohm_version: str | None = None
    catalog_record_count: int = 0
    merkle_root: str | None = None


class CatalogListResponse(BaseModel):
    records: list[CatalogRecord]
    total: int
    page: int = 1
    page_size: int = 100
    merkle_root: str


class FederationHealthResponse(BaseModel):
    status: str = "ok"
    did: str | None = None
    federation_enabled: bool = True


class PeerListResponse(BaseModel):
    peers: list[PeerState]
    total: int


class PeerDiscoverResponse(BaseModel):
    updated: list[PeerState] = Field(default_factory=list)
    peers: list[PeerState]
    total: int


class SyncPeerResultResponse(BaseModel):
    peer_did: str
    base_url: str
    pulled: int = 0
    skipped: int = 0
    errors: list[str] = Field(default_factory=list)


class SyncRunResponse(BaseModel):
    results: list[SyncPeerResultResponse]
    total_pulled: int = 0


class FollowResponse(BaseModel):
    did: str
    followed: bool


class PackageFetchRequest(BaseModel):
    peer_url: str
    bundle_hash: str
    manifest_id: str | None = None
    allow_rebuild: bool = True


class PackageFetchResponse(BaseModel):
    action: str
    bundle_hash: str | None = None
    path: str | None = None
    detail: str | None = None
    message: str = ""
    status: str = "success"


class SignedManifestRecordResponse(BaseModel):
    """API wrapper for GET /records/{content_hash}."""

    catalog_record: CatalogRecord
    manifest: dict[str, Any]
    manifest_signature: str

    @classmethod
    def from_signed(cls, signed: SignedManifestRecord) -> SignedManifestRecordResponse:
        return cls(
            catalog_record=signed.catalog_record,
            manifest=signed.manifest,
            manifest_signature=signed.manifest_signature,
        )
