"""Unit tests for federation catalog building."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.core.federation.catalog import (
    CatalogIndex,
    build_catalog_index,
    manifest_content_hash,
)
from src.core.federation.identity import canonical_json_bytes, generate_identity

MINIMAL_MANIFEST = {
    "okhv": "1.0",
    "id": "340b030e-e3c6-4869-b947-4a24c52daaf1",
    "title": "Test Design",
    "version": "1.0.0",
    "license": {"hardware": "MIT"},
    "licensor": "Alice",
    "documentation_language": "en",
    "function": "testing",
}


@pytest.mark.unit
def test_manifest_content_hash_is_stable() -> None:
    h1 = manifest_content_hash(MINIMAL_MANIFEST)
    h2 = manifest_content_hash(
        {
            "function": "testing",
            "documentation_language": "en",
            "licensor": "Alice",
            "license": {"hardware": "MIT"},
            "version": "1.0.0",
            "title": "Test Design",
            "id": "340b030e-e3c6-4869-b947-4a24c52daaf1",
            "okhv": "1.0",
        }
    )
    assert h1 == h2
    assert h1.startswith("sha256:")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_catalog_index_from_manifests() -> None:
    identity = generate_identity("Catalog Test")
    manifest = MagicMock()
    manifest.id = UUID("340b030e-e3c6-4869-b947-4a24c52daaf1")
    manifest.title = "Test Design"
    manifest.version = "1.0.0"
    manifest.version_date = None
    manifest.to_dict.return_value = dict(MINIMAL_MANIFEST)

    okh_service = AsyncMock()
    okh_service.list.return_value = ([manifest], 1)

    index: CatalogIndex = await build_catalog_index(okh_service, identity)

    assert index.record_count == 1
    assert index.merkle_root
    assert len(index.records) == 1
    record = index.records[0]
    assert record.publisher_did == identity.did
    assert identity.verify_bytes(
        canonical_json_bytes(record.record_payload()),
        bytes.fromhex(record.signature),
    )
    assert index.get_signed_record(record.content_hash) is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_catalog_index_empty() -> None:
    identity = generate_identity("Empty")
    okh_service = AsyncMock()
    okh_service.list.return_value = ([], 0)

    index = await build_catalog_index(okh_service, identity)
    assert index.record_count == 0
    assert index.records == []
