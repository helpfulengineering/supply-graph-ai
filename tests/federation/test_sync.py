"""Unit tests for anti-entropy sync helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.core.federation.models import SyncDigest, SyncDigestResponse
from src.core.federation.sync import (
    compute_missing_hashes,
    sync_with_peer,
)


@pytest.mark.unit
def test_compute_missing_hashes() -> None:
    ours = {"sha256:aaa", "sha256:bbb", "sha256:ccc"}
    theirs = {"sha256:aaa", "sha256:ccc"}
    assert compute_missing_hashes(ours, theirs) == ["sha256:bbb"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_with_peer_pulls_missing_records() -> None:
    from src.core.federation.catalog import manifest_content_hash
    from src.core.federation.identity import generate_identity
    from src.core.federation.models import (
        CatalogRecord,
        PeerState,
        SignedManifestRecord,
        utc_now,
    )
    from tests.federation.test_catalog import MINIMAL_MANIFEST
    from uuid import UUID

    identity = generate_identity("Remote")
    content_hash = manifest_content_hash(MINIMAL_MANIFEST)
    record = CatalogRecord(
        manifest_id=UUID(MINIMAL_MANIFEST["id"]),
        content_hash=content_hash,
        title=MINIMAL_MANIFEST["title"],
        version=MINIMAL_MANIFEST["version"],
        updated_at=utc_now(),
        publisher_did=identity.did,
        signature="00" * 64,
    )
    signed = SignedManifestRecord(
        catalog_record=record,
        manifest=MINIMAL_MANIFEST,
        manifest_signature="00" * 64,
    )

    peer = PeerState(
        did=identity.did,
        base_url="http://peer-b:8001",
        followed=True,
    )

    mock_service = MagicMock()
    mock_service.identity = MagicMock(did="did:key:z6Mklocal")
    mock_index = MagicMock()
    mock_index.merkle_root = "root-a"
    mock_index.record_count = 0
    mock_index.records = []
    mock_service.build_catalog_index = AsyncMock(return_value=mock_index)
    mock_service.store = MagicMock()
    mock_service.store.is_followed.return_value = True

    digest_response = SyncDigestResponse(missing_hashes=[content_hash])

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path.endswith("/sync/digest"):
            return httpx.Response(200, json=digest_response.model_dump())
        if request.method == "GET" and content_hash in str(request.url):
            return httpx.Response(
                200,
                json={
                    "catalog_record": record.model_dump(mode="json"),
                    "manifest": MINIMAL_MANIFEST,
                    "manifest_signature": signed.manifest_signature,
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    with (
        patch(
            "src.core.federation.sync.verify_and_store",
            new_callable=AsyncMock,
            return_value=MagicMock(action="stored"),
        ) as mock_ingest,
        patch(
            "src.core.services.okh_service.OKHService.get_instance",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ),
        patch(
            "src.core.federation.sync.httpx.AsyncClient",
            return_value=httpx.AsyncClient(transport=transport),
        ),
    ):
        result = await sync_with_peer(mock_service, peer)

    assert result.pulled == 1
    assert result.skipped == 0
    mock_ingest.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sync_with_peer_skips_when_roots_match() -> None:
    from src.core.federation.models import PeerState

    peer = PeerState(
        did="did:key:z6Mkremote",
        base_url="http://peer-b:8001",
        followed=True,
    )

    mock_service = MagicMock()
    mock_service.identity = MagicMock(did="did:key:z6Mklocal")
    mock_index = MagicMock()
    mock_index.merkle_root = "same-root"
    mock_index.record_count = 2
    mock_index.records = []
    mock_service.build_catalog_index = AsyncMock(return_value=mock_index)
    mock_service.store = MagicMock()
    mock_service.store.is_followed.return_value = True

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(
                200,
                json=SyncDigestResponse(missing_hashes=[]).model_dump(),
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    with (
        patch(
            "src.core.services.okh_service.OKHService.get_instance",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        ),
        patch(
            "src.core.federation.sync.httpx.AsyncClient",
            return_value=httpx.AsyncClient(transport=transport),
        ),
    ):
        result = await sync_with_peer(mock_service, peer)

    assert result.pulled == 0
