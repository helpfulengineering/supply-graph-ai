"""Federation API response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.core.federation.models import CatalogRecord, SignedManifestRecord


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
