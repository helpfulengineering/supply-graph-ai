"""Unit tests for federation manifest ingest."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uuid import UUID

from src.core.federation.catalog import manifest_content_hash
from src.core.federation.identity import generate_identity
from src.core.federation.ingest import (
    IngestError,
    verify_and_store,
    verify_signed_record,
)
from src.core.federation.models import CatalogRecord, SignedManifestRecord, utc_now
from src.core.federation.store import FederationStore
from tests.federation.test_catalog import MINIMAL_MANIFEST


def _signed_record(publisher=None) -> SignedManifestRecord:
    identity = publisher or generate_identity("Publisher")
    content_hash = manifest_content_hash(MINIMAL_MANIFEST)
    updated_at = utc_now()
    payload = {
        "manifest_id": MINIMAL_MANIFEST["id"],
        "content_hash": content_hash,
        "title": MINIMAL_MANIFEST["title"],
        "version": MINIMAL_MANIFEST["version"],
        "updated_at": updated_at.isoformat(),
        "publisher_did": identity.did,
    }
    record = CatalogRecord(
        manifest_id=UUID(MINIMAL_MANIFEST["id"]),
        content_hash=content_hash,
        title=MINIMAL_MANIFEST["title"],
        version=MINIMAL_MANIFEST["version"],
        updated_at=updated_at,
        publisher_did=identity.did,
        signature=identity.sign_json(payload).hex(),
    )
    return SignedManifestRecord(
        catalog_record=record,
        manifest=MINIMAL_MANIFEST,
        manifest_signature=identity.sign_json(MINIMAL_MANIFEST).hex(),
    )


@pytest.mark.unit
def test_verify_signed_record_accepts_valid() -> None:
    signed = _signed_record()
    verify_signed_record(signed)


@pytest.mark.unit
def test_verify_signed_record_rejects_bad_manifest_sig() -> None:
    signed = _signed_record()
    bad = signed.model_copy(update={"manifest_signature": "00" * 64})
    with pytest.raises(IngestError, match="manifest signature"):
        verify_signed_record(bad)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_and_store_rejects_unfollowed(tmp_path) -> None:
    signed = _signed_record()
    store = FederationStore(tmp_path)
    okh_service = AsyncMock()

    with pytest.raises(IngestError, match="not followed"):
        await verify_and_store(
            signed,
            publisher_did=signed.catalog_record.publisher_did,
            store=store,
            okh_service=okh_service,
            local_content_hashes=set(),
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_and_store_persists_followed_record(tmp_path) -> None:
    signed = _signed_record()
    store = FederationStore(tmp_path)
    store.set_followed(signed.catalog_record.publisher_did, True)
    okh_service = AsyncMock()
    okh_service.create = AsyncMock(return_value=MagicMock())

    with patch(
        "src.core.federation.ingest.validate_okh_manifest",
        return_value=MagicMock(valid=True, errors=[]),
    ):
        result = await verify_and_store(
            signed,
            publisher_did=signed.catalog_record.publisher_did,
            store=store,
            okh_service=okh_service,
            local_content_hashes=set(),
        )

    assert result.action == "stored"
    okh_service.create.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_and_store_skips_existing_hash(tmp_path) -> None:
    signed = _signed_record()
    store = FederationStore(tmp_path)
    store.set_followed(signed.catalog_record.publisher_did, True)
    okh_service = AsyncMock()

    result = await verify_and_store(
        signed,
        publisher_did=signed.catalog_record.publisher_did,
        store=store,
        okh_service=okh_service,
        local_content_hashes={signed.catalog_record.content_hash},
    )

    assert result.action == "skipped"
    okh_service.create.assert_not_called()
