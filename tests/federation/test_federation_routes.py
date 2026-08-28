"""Contract tests for federation HTTP API (Slice 2)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI

from src.core.federation.catalog import CatalogIndex, manifest_content_hash
from src.core.federation.identity import generate_identity
from src.core.federation.merkle import merkle_root
from src.core.federation.metrics import FederationSyncMetrics
from src.core.federation.models import (
    CatalogRecord,
    SignedManifestRecord,
    SyncDigestResponse,
    utc_now,
)

MINIMAL_MANIFEST = {
    "okhv": "1.0",
    "id": "340b030e-e3c6-4869-b947-4a24c52daaf1",
    "title": "Route Test Design",
    "version": "1.0.0",
    "license": {"hardware": "MIT"},
    "licensor": "Alice",
    "documentation_language": "en",
    "function": "testing",
}


def _federation_app() -> FastAPI:
    """Minimal app with only the federation router (avoids full main import)."""
    from src.core.api.routes.federation import router as federation_router

    inner = FastAPI()
    inner.include_router(federation_router)
    outer = FastAPI()
    outer.mount("/v1", inner)
    return outer


def _sample_index() -> CatalogIndex:
    identity = generate_identity("Route Peer")
    content_hash = manifest_content_hash(MINIMAL_MANIFEST)
    payload = {
        "manifest_id": MINIMAL_MANIFEST["id"],
        "content_hash": content_hash,
        "title": MINIMAL_MANIFEST["title"],
        "version": MINIMAL_MANIFEST["version"],
        "updated_at": utc_now().isoformat(),
        "publisher_did": identity.did,
    }
    signature = identity.sign_json(payload).hex()
    record = CatalogRecord(
        manifest_id=UUID(MINIMAL_MANIFEST["id"]),
        content_hash=content_hash,
        title=MINIMAL_MANIFEST["title"],
        version=MINIMAL_MANIFEST["version"],
        updated_at=utc_now(),
        publisher_did=identity.did,
        signature=signature,
    )
    signed = SignedManifestRecord(
        catalog_record=record,
        manifest=MINIMAL_MANIFEST,
        manifest_signature=identity.sign_json(MINIMAL_MANIFEST).hex(),
    )
    return CatalogIndex(
        records=[record],
        signed_by_hash={content_hash: signed},
        merkle_root=merkle_root([content_hash]),
        record_count=1,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_federation_routes_404_when_disabled(monkeypatch) -> None:
    from src.config import settings

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", False)

    mock_service = MagicMock()
    mock_service.enabled = False

    async def _get_instance():
        return mock_service

    with patch(
        "src.core.api.routes.federation.FederationService.get_instance",
        side_effect=_get_instance,
    ):
        transport = httpx.ASGITransport(app=_federation_app())
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get("/v1/api/federation/identify")
            assert resp.status_code == 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_federation_identify_and_catalog_when_enabled(monkeypatch) -> None:
    from src.config import settings
    from src.core.federation.node_role import NodeRole

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)

    identity = generate_identity("API Peer")
    index = _sample_index()

    mock_service = MagicMock()
    mock_service.enabled = True
    mock_service.identity = identity
    mock_service.role = NodeRole.PEER
    mock_service.capabilities.expose_federation_api = True

    async def _ready() -> None:
        return None

    mock_service.ensure_federation_ready = _ready
    mock_service.build_catalog_index = AsyncMock(return_value=index)
    mock_service.catalog_summary = AsyncMock(
        return_value=(index.record_count, index.merkle_root)
    )

    async def _get_instance():
        return mock_service

    with patch(
        "src.core.api.routes.federation.FederationService.get_instance",
        side_effect=_get_instance,
    ):
        transport = httpx.ASGITransport(app=_federation_app())
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            identify = await client.get("/v1/api/federation/identify")
            assert identify.status_code == 200, identify.text
            body = identify.json()
            assert body["did"] == identity.did
            assert body["catalog_record_count"] == 1
            assert body["merkle_root"] == index.merkle_root

            catalog = await client.get("/v1/api/federation/catalog")
            assert catalog.status_code == 200, catalog.text
            items = catalog.json()["records"]
            assert len(items) == 1
            assert items[0]["content_hash"] == index.records[0].content_hash

            content_hash = index.records[0].content_hash
            record_resp = await client.get(f"/v1/api/federation/records/{content_hash}")
            assert record_resp.status_code == 200, record_resp.text
            record_body = record_resp.json()
            assert record_body["manifest"]["title"] == "Route Test Design"

            health = await client.get("/v1/api/federation/health")
            assert health.status_code == 200
            assert health.json()["status"] == "ok"

            mock_service.list_peers = MagicMock(return_value=[])
            peers = await client.get("/v1/api/federation/peers")
            assert peers.status_code == 200
            assert peers.json()["total"] == 0

            mock_service.refresh_peers = AsyncMock(return_value=[])
            discover = await client.post("/v1/api/federation/peers/discover")
            assert discover.status_code == 200
            assert discover.json()["total"] == 0

            mock_service.handle_sync_digest = AsyncMock(
                return_value=SyncDigestResponse(missing_hashes=["sha256:abc"])
            )
            digest = await client.post(
                "/v1/api/federation/sync/digest",
                json={
                    "merkle_root": "deadbeef",
                    "record_count": 0,
                    "publisher_did": "did:key:z6Mkremote",
                    "leaf_hashes": [],
                },
            )
            assert digest.status_code == 200
            assert digest.json()["missing_hashes"] == ["sha256:abc"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_record_404_for_unknown_hash(monkeypatch) -> None:
    from src.config import settings
    from src.core.federation.node_role import NodeRole

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)

    identity = generate_identity("API Peer")
    index = _sample_index()

    mock_service = MagicMock()
    mock_service.enabled = True
    mock_service.identity = identity
    mock_service.role = NodeRole.PEER
    mock_service.capabilities.expose_federation_api = True
    mock_service.ensure_federation_ready = AsyncMock(return_value=None)
    mock_service.build_catalog_index = AsyncMock(return_value=index)
    mock_service.catalog_summary = AsyncMock(
        return_value=(index.record_count, index.merkle_root)
    )

    with patch(
        "src.core.api.routes.federation.FederationService.get_instance",
        return_value=mock_service,
    ):
        transport = httpx.ASGITransport(app=_federation_app())
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            resp = await client.get(
                "/v1/api/federation/records/sha256:0000000000000000000000000000000000000000000000000000000000000000"
            )
            assert resp.status_code == 404


def _enabled_service():
    """A federation service that is on, exposed and ready."""
    from src.core.federation.node_role import NodeRole

    identity = generate_identity("Auth Peer")
    index = _sample_index()

    service = MagicMock()
    service.enabled = True
    service.identity = identity
    service.role = NodeRole.PEER
    service.capabilities.expose_federation_api = True
    service.capabilities.can_accept_inbound_sync = True
    service.ensure_federation_ready = AsyncMock(return_value=None)
    service.build_catalog_index = AsyncMock(return_value=index)
    service.catalog_summary = AsyncMock(
        return_value=(index.record_count, index.merkle_root)
    )
    service.get_status = AsyncMock(
        return_value={
            "did": identity.did,
            "display_name": identity.display_name,
            "role": "peer",
            "catalog_record_count": index.record_count,
            "merkle_root": index.merkle_root,
            "peer_count": 0,
            "followed_peer_count": 0,
            "sync_interval_sec": 60,
            "rate_limit_per_min": 60,
            "mdns_enabled": False,
            "background_sync_running": False,
            "manual_peers": [],
            "seed_peer_url": None,
            "metrics": FederationSyncMetrics(),
        }
    )
    service.list_peers = MagicMock(return_value=[])
    service.refresh_peers = AsyncMock(return_value=[])
    service.sync_with_url = AsyncMock()
    service.sync_all_followed = AsyncMock(return_value=[])
    service.sync_okw_all_followed = AsyncMock(return_value=[])
    service.follow_peer = MagicMock()
    service.unfollow_peer = MagicMock()
    return service


# (method, path) for every route that mutates local trust or storage, or makes
# this node fetch a URL a caller chose.
MUTATING_ROUTES = [
    ("POST", "/v1/api/federation/peers/discover"),
    ("POST", "/v1/api/federation/sync/run?peer_url=https://evil.example"),
    ("POST", "/v1/api/federation/peers/did:key:zAttacker/follow"),
    ("DELETE", "/v1/api/federation/peers/did:key:zAttacker/follow"),
    ("POST", "/v1/api/federation/okw/sync/run"),
]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mutating_federation_routes_reject_anonymous_when_enforced(
    monkeypatch,
) -> None:
    """Enabling federation must not open an anonymous write path.

    `POST /sync/run?peer_url=` makes this node fetch an arbitrary URL, auto-follow
    whatever DID it claims and ingest its manifests, so unauthenticated access
    would bypass the write gate that production security mode exists to apply.
    """
    from src.config import settings

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")

    service = _enabled_service()
    with patch(
        "src.core.api.routes.federation.FederationService.get_instance",
        AsyncMock(return_value=service),
    ):
        transport = httpx.ASGITransport(app=_federation_app())
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            for method, path in MUTATING_ROUTES:
                resp = await client.request(method, path)
                assert resp.status_code in (
                    401,
                    403,
                ), f"{method} {path} -> {resp.status_code}"

    service.sync_with_url.assert_not_awaited()
    service.follow_peer.assert_not_called()
    service.refresh_peers.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_peer_protocol_stays_anonymous_when_enforced(monkeypatch) -> None:
    """A peer authenticates with a DID it signs for, not one of our API keys.

    So the read side of the protocol — and the digest exchange, which is bounded
    by the per-DID rate limiter instead — must keep working unauthenticated even
    under production write enforcement.
    """
    from src.config import settings

    monkeypatch.setattr(settings, "OHM_FEDERATION_ENABLED", True)
    monkeypatch.setattr("src.config.settings.ENVIRONMENT", "production")

    service = _enabled_service()
    with patch(
        "src.core.api.routes.federation.FederationService.get_instance",
        AsyncMock(return_value=service),
    ):
        transport = httpx.ASGITransport(app=_federation_app())
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            for path in (
                "/v1/api/federation/identify",
                "/v1/api/federation/status",
                "/v1/api/federation/catalog",
                "/v1/api/federation/health",
                "/v1/api/federation/peers",
            ):
                resp = await client.get(path)
                assert resp.status_code != 401, f"{path} -> 401"
                assert resp.status_code != 403, f"{path} -> 403"
