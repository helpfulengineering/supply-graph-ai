"""Federation API routes (catalog identify, list, record fetch)."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import Response

from src.config import settings
from src.core.api.models.federation.response import (
    CatalogListResponse,
    FederationHealthResponse,
    FederationStatusResponse,
    FederationSyncMetricsResponse,
    FollowResponse,
    IdentifyResponse,
    PackageFetchRequest,
    PackageFetchResponse,
    PeerDiscoverResponse,
    PeerListResponse,
    SignedManifestRecordResponse,
    SyncPeerResultResponse,
    SyncRunResponse,
)
from src.core.api.dependencies import get_current_user, require_write
from src.core.models.auth import AuthenticatedUser
from src.core.services.auth_service import AuthenticationService
from src.core.federation.identity import NodeIdentity
from src.core.federation.lists import (
    ListNotShareable,
    SupersedesUnknown,
    publish_curated_list,
    replace_curated_list,
)
from src.core.federation.store import FederationStore
from src.core.federation.models import (
    CuratedList,
    CuratedListWrite,
    SyncDigest,
    SyncDigestResponse,
)
from src.core.federation.package_fetch import PEER_DID_HEADER, fetch_package_from_peer
from src.core.federation.package_pointer import (
    find_package_dir_by_bundle_hash,
    package_dir_to_archive_bytes,
)
from src.core.federation.rate_limit import get_federation_rate_limiter
from src.core.federation.service import FederationService
from src.core.utils.logging import get_logger
from src.core.version import get_version
from uuid import UUID

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/federation",
    tags=["federation"],
)


async def get_federation_service() -> FederationService:
    return await FederationService.get_instance()


async def _signing_identity(
    user: AuthenticatedUser,
    publisher_did: str | None,
    service: FederationService,
) -> NodeIdentity:
    """The key that signs this list, after the caller is allowed to use it.

    A node list is signed by the node identity, and only a node admin may
    publish it. An organisation list is signed by the space key, and only the
    claimed admin may ask this node to make that signature.
    """
    if service.identity is None:
        raise RuntimeError("Federation identity not loaded")
    auth = await AuthenticationService.get_instance()
    requested = publisher_did or service.identity.did
    if requested == service.identity.did:
        if not await auth.check_permission(
            user, ["admin"], scope=auth.local_node_scope()
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This operation requires the 'admin' permission",
            )
        return service.identity
    claim = await auth.get_space_claim(requested)
    if claim is None or user.subject_did != claim.admin_did:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only that organisation's admin can publish its list.",
        )
    key = (
        auth._identity_store.load_signing_key(requested)
        if auth._identity_store is not None
        else None
    )
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No signing key held for that organisation.",
        )
    return key


def _store(service: FederationService) -> FederationStore:
    if service.store is None:
        raise RuntimeError("Federation store not loaded")
    return service.store


async def get_okh_for_lists():
    """Designs a curated list may pin. Overridable in tests."""
    from src.core.services.okh_service import OKHService

    return await OKHService.get_instance()


async def require_federation_api(
    service: FederationService = Depends(get_federation_service),
) -> FederationService:
    if not service.enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Federation is not enabled",
        )
    await service.ensure_federation_ready()
    if not service.capabilities.expose_federation_api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Federation API is not exposed for this node role",
        )
    return service


# Two kinds of caller reach this router, and they authorize differently.
#
# The PEER PROTOCOL is anonymous by necessity: a peer identifies itself with a
# DID it signs for, not with one of our API keys, so /identify, /catalog,
# /records, the CAS blob read and the digest exchanges stay open and are bounded
# by _enforce_peer_rate_limit instead.
#
# OPERATOR ACTIONS are ordinary local writes wearing federation clothing —
# following a DID, pointing the node at a URL to sync from, pulling a package.
# They mutate local trust and local storage, so they take require_write like any
# other write (see routes/okh.py). Without it, `POST /sync/run?peer_url=` is an
# unauthenticated request that makes this node fetch an arbitrary URL, auto-
# follow whatever DID it claims, and ingest its manifests.


def _enforce_peer_rate_limit(
    service: FederationService,
    peer_identifier: str,
) -> None:
    limiter = get_federation_rate_limiter()
    info = limiter.check(peer_identifier)
    if info.allowed:
        return
    service.federation_metrics.record_rate_limit_rejection()
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Federation rate limit exceeded for {peer_identifier}",
        headers={
            "X-RateLimit-Limit": str(info.limit),
            "X-RateLimit-Remaining": str(info.remaining),
            "X-RateLimit-Reset": str(info.reset_time),
        },
    )


@router.get(
    "/status",
    response_model=FederationStatusResponse,
    summary="Federation node status and sync metrics",
)
async def federation_status(
    service: FederationService = Depends(require_federation_api),
) -> FederationStatusResponse:
    snapshot = await service.get_status()
    metrics = snapshot.pop("metrics")
    return FederationStatusResponse(
        **snapshot,
        metrics=FederationSyncMetricsResponse.model_validate(asdict(metrics)),
    )


@router.get(
    "/identify",
    response_model=IdentifyResponse,
    summary="Identify this federation node",
)
async def identify(
    service: FederationService = Depends(require_federation_api),
) -> IdentifyResponse:
    record_count, root = await service.catalog_summary()
    if service.identity is None:
        raise RuntimeError("Federation identity not loaded")
    return IdentifyResponse(
        did=service.identity.did,
        display_name=service.identity.display_name,
        role=service.role.value,
        ohm_version=get_version(),
        catalog_record_count=record_count,
        merkle_root=root,
    )


@router.get(
    "/catalog",
    response_model=CatalogListResponse,
    summary="List signed catalog records for this node",
)
async def list_catalog(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    service: FederationService = Depends(require_federation_api),
) -> CatalogListResponse:
    index = await service.build_catalog_index()
    start = (page - 1) * page_size
    end = start + page_size
    page_records = index.records[start:end]
    return CatalogListResponse(
        records=page_records,
        total=index.record_count,
        page=page,
        page_size=page_size,
        merkle_root=index.merkle_root,
    )


@router.get(
    "/records/{content_hash:path}",
    response_model=SignedManifestRecordResponse,
    summary="Fetch a signed manifest by content hash",
)
async def get_record(
    content_hash: str,
    service: FederationService = Depends(require_federation_api),
) -> SignedManifestRecordResponse:
    if not content_hash.startswith("sha256:"):
        content_hash = f"sha256:{content_hash}"
    index = await service.build_catalog_index()
    signed = index.get_signed_record(content_hash)
    if signed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No record for content hash {content_hash}",
        )
    return SignedManifestRecordResponse.from_signed(signed)


@router.get(
    "/health",
    response_model=FederationHealthResponse,
    summary="Federation subsystem health",
)
async def federation_health(
    service: FederationService = Depends(require_federation_api),
) -> FederationHealthResponse:
    return FederationHealthResponse(
        status="ok",
        did=service.identity.did if service.identity else None,
        federation_enabled=settings.OHM_FEDERATION_ENABLED,
    )


@router.get(
    "/peers",
    response_model=PeerListResponse,
    summary="List known federation peers",
)
async def list_peers(
    service: FederationService = Depends(require_federation_api),
) -> PeerListResponse:
    peers = service.list_peers()
    return PeerListResponse(peers=peers, total=len(peers))


@router.post(
    "/peers/discover",
    response_model=PeerDiscoverResponse,
    summary="Discover peers (manual URLs + mDNS) and refresh local registry",
)
async def discover_peers(
    service: FederationService = Depends(require_federation_api),
    _user=Depends(require_write),
) -> PeerDiscoverResponse:
    updated = await service.refresh_peers()
    peers = service.list_peers()
    return PeerDiscoverResponse(updated=updated, peers=peers, total=len(peers))


@router.post(
    "/sync/digest",
    response_model=SyncDigestResponse,
    summary="Anti-entropy digest exchange",
)
async def sync_digest(
    digest: SyncDigest,
    service: FederationService = Depends(require_federation_api),
) -> SyncDigestResponse:
    if not service.capabilities.can_accept_inbound_sync:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This node role does not accept inbound sync",
        )
    _enforce_peer_rate_limit(service, digest.publisher_did)
    return await service.handle_sync_digest(digest)


@router.post(
    "/sync/run",
    response_model=SyncRunResponse,
    summary="Sync catalog records from followed peers",
)
async def run_sync(
    peer_url: str | None = Query(None, description="Optional single peer base URL"),
    service: FederationService = Depends(require_federation_api),
    _user=Depends(require_write),
) -> SyncRunResponse:
    if peer_url:
        result = await service.sync_with_url(peer_url)
        results = [result]
    else:
        results = await service.sync_all_followed()
    response_results = [
        SyncPeerResultResponse(
            peer_did=r.peer_did,
            base_url=r.base_url,
            pulled=r.pulled,
            skipped=r.skipped,
            errors=r.errors,
        )
        for r in results
    ]
    return SyncRunResponse(
        results=response_results,
        total_pulled=sum(r.pulled for r in results),
    )


@router.post(
    "/peers/{did:path}/follow",
    response_model=FollowResponse,
    summary="Follow a peer DID (allow manifest ingest)",
)
async def follow_peer(
    did: str,
    service: FederationService = Depends(require_federation_api),
    _user=Depends(require_write),
) -> FollowResponse:
    service.follow_peer(did)
    return FollowResponse(did=did, followed=True)


@router.delete(
    "/peers/{did:path}/follow",
    response_model=FollowResponse,
    summary="Unfollow a peer DID",
)
async def unfollow_peer(
    did: str,
    service: FederationService = Depends(require_federation_api),
    _user=Depends(require_write),
) -> FollowResponse:
    service.unfollow_peer(did)
    return FollowResponse(did=did, followed=False)


@router.get(
    "/packages/blobs/{bundle_hash:path}",
    summary="Download a package artifact by bundle hash (followed peers only)",
    responses={200: {"content": {"application/octet-stream": {}}}},
)
async def get_package_blob(
    bundle_hash: str,
    service: FederationService = Depends(require_federation_api),
    x_ohm_peer_did: str | None = Header(None, alias=PEER_DID_HEADER),
) -> Response:
    """Serve package bytes on the artifact channel. Requires a followed peer DID."""
    if not x_ohm_peer_did or not service.is_followed(x_ohm_peer_did):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Package blobs require a followed peer DID "
            f"(send {PEER_DID_HEADER})",
        )
    package_dir = find_package_dir_by_bundle_hash(bundle_hash)
    if package_dir is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No package for bundle hash {bundle_hash}",
        )
    data, filename = package_dir_to_archive_bytes(package_dir)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/packages/fetch",
    response_model=PackageFetchResponse,
    summary="On-demand fetch of a package from a peer (rebuild fallback)",
)
async def fetch_package(
    body: PackageFetchRequest,
    service: FederationService = Depends(require_federation_api),
    _user=Depends(require_write),
) -> PackageFetchResponse:
    manifest_id = UUID(body.manifest_id) if body.manifest_id else None
    result = await fetch_package_from_peer(
        service,
        peer_url=body.peer_url,
        bundle_hash=body.bundle_hash,
        manifest_id=manifest_id,
        allow_rebuild=body.allow_rebuild,
    )
    ok = result.action in ("fetched", "rebuilt", "local")
    return PackageFetchResponse(
        action=result.action,
        bundle_hash=result.bundle_hash,
        path=result.path,
        detail=result.detail,
        message=result.detail or result.action,
        status="success" if ok else "error",
    )


@router.get(
    "/okw/catalog",
    summary="List signed OKW catalog records (redacted projections)",
)
async def list_okw_catalog(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    service: FederationService = Depends(require_federation_api),
) -> dict:
    index = await service.build_okw_catalog_index()
    start = (page - 1) * page_size
    end = start + page_size
    page_records = index.records[start:end]
    return {
        "records": [r.model_dump(mode="json") for r in page_records],
        "total": index.record_count,
        "page": page,
        "page_size": page_size,
        "merkle_root": index.merkle_root,
    }


@router.get(
    "/okw/records/{content_hash:path}",
    summary="Fetch a signed OKW facility projection by content hash",
)
async def get_okw_record(
    content_hash: str,
    service: FederationService = Depends(require_federation_api),
) -> dict:
    if not content_hash.startswith("sha256:"):
        content_hash = f"sha256:{content_hash}"
    index = await service.build_okw_catalog_index()
    signed = index.get_signed_record(content_hash)
    if signed is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No OKW record for content hash {content_hash}",
        )
    return signed.model_dump(mode="json")


@router.post(
    "/okw/sync/digest",
    response_model=SyncDigestResponse,
    summary="OKW anti-entropy digest exchange",
)
async def okw_sync_digest(
    digest: SyncDigest,
    service: FederationService = Depends(require_federation_api),
) -> SyncDigestResponse:
    if not service.capabilities.can_accept_inbound_sync:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This node role does not accept inbound sync",
        )
    _enforce_peer_rate_limit(service, digest.publisher_did)
    return await service.handle_okw_sync_digest(digest)


@router.post(
    "/okw/sync/run",
    response_model=SyncRunResponse,
    summary="Sync OKW catalog records from followed peers",
)
async def run_okw_sync(
    service: FederationService = Depends(require_federation_api),
    _user=Depends(require_write),
) -> SyncRunResponse:
    results = await service.sync_okw_all_followed()
    response_results = [
        SyncPeerResultResponse(
            peer_did=r.peer_did,
            base_url=r.base_url,
            pulled=r.pulled,
            skipped=r.skipped,
            errors=r.errors,
        )
        for r in results
    ]
    return SyncRunResponse(
        results=response_results,
        total_pulled=sum(r.pulled for r in results),
    )


@router.post(
    "/lists",
    response_model=CuratedList,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    summary="Publish a curated list of pinned designs",
)
async def publish_list(
    body: CuratedListWrite,
    user: AuthenticatedUser = Depends(get_current_user),
    service: FederationService = Depends(require_federation_api),
    okh=Depends(get_okh_for_lists),
) -> CuratedList:
    """Sign the current membership with the node identity or the space key."""
    signer = await _signing_identity(user, body.publisher_did, service)
    try:
        return await publish_curated_list(signer, _store(service), okh, body)
    except ListNotShareable as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Design {exc.content_hash} is not shareable",
        ) from exc


@router.get(
    "/lists",
    response_model=list[CuratedList],
    response_model_exclude_none=True,
    summary="List published curated lists",
)
async def list_curated_lists(
    service: FederationService = Depends(require_federation_api),
) -> list[CuratedList]:
    """Every list this node publishes. Each document carries its own signature."""
    return _store(service).load_lists()


@router.get(
    "/lists/{id}",
    response_model=CuratedList,
    response_model_exclude_none=True,
    summary="Fetch a published curated list",
)
async def get_curated_list(
    id: str,
    service: FederationService = Depends(require_federation_api),
) -> CuratedList:
    """The signed document. A peer checks it offline from publisher_did."""
    document = _store(service).get_list(id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No curated list with that id",
        )
    return document


@router.put(
    "/lists/{id}",
    response_model=CuratedList,
    response_model_exclude_none=True,
    summary="Publish the next membership of a curated list",
)
async def replace_list(
    id: str,
    body: CuratedListWrite,
    user: AuthenticatedUser = Depends(get_current_user),
    service: FederationService = Depends(require_federation_api),
    okh=Depends(get_okh_for_lists),
) -> CuratedList:
    """Add, bump, or remove pins. Sequence increases by one."""
    store = _store(service)
    current = store.get_list(id)
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No curated list with that id",
        )
    signer = await _signing_identity(user, current.publisher_did, service)
    try:
        return await replace_curated_list(signer, store, okh, id, body)
    except ListNotShareable as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Design {exc.content_hash} is not shareable",
        ) from exc
    except SupersedesUnknown as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{exc.content_hash} is not a pin this edit removes",
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only that list's publisher can edit it",
        ) from exc
