"""On-demand package artifact fetch from followed peers (CAS channel)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

import httpx

from ..utils.logging import get_logger
from .package_pointer import find_package_dir_by_bundle_hash, write_fetched_package
from .peer_registry import build_federation_base_url

if TYPE_CHECKING:
    from .service import FederationService

logger = get_logger(__name__)

_BLOB_PATH = "/v1/api/federation/packages/blobs/"
PEER_DID_HEADER = "X-OHM-Peer-DID"


@dataclass
class PackageFetchResult:
    action: str  # fetched | rebuilt | local | failed
    bundle_hash: str | None = None
    path: str | None = None
    detail: str | None = None


async def fetch_package_from_peer(
    service: FederationService,
    *,
    peer_url: str,
    bundle_hash: str,
    manifest_id: UUID | None = None,
    allow_rebuild: bool = True,
) -> PackageFetchResult:
    """Fetch package bytes from a peer; optionally rebuild from OKH on failure."""
    if service.identity is None:
        raise RuntimeError("Federation identity not loaded")

    local = find_package_dir_by_bundle_hash(bundle_hash)
    if local is not None:
        return PackageFetchResult(
            action="local",
            bundle_hash=bundle_hash,
            path=str(local),
            detail="already present",
        )

    base = build_federation_base_url(peer_url)
    normalized = (
        bundle_hash if bundle_hash.startswith("sha256:") else f"sha256:{bundle_hash}"
    )
    url = f"{base}{_BLOB_PATH}{normalized}"
    headers = {PEER_DID_HEADER: service.identity.did}

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.content
        path = write_fetched_package(data, expected_hash=normalized)
        return PackageFetchResult(
            action="fetched",
            bundle_hash=normalized,
            path=str(path),
        )
    except Exception as e:
        logger.warning(f"Package fetch from {base} failed: {e}")
        if not allow_rebuild or manifest_id is None:
            return PackageFetchResult(
                action="failed",
                bundle_hash=normalized,
                detail=str(e),
            )
        return await _rebuild_fallback(manifest_id, normalized, str(e))


async def _rebuild_fallback(
    manifest_id: UUID,
    bundle_hash: str,
    fetch_error: str,
) -> PackageFetchResult:
    try:
        from ..services.okh_service import OKHService
        from ..services.package_service import PackageService

        okh = await OKHService.get_instance()
        manifest = await okh.get(manifest_id)
        if manifest is None:
            return PackageFetchResult(
                action="failed",
                bundle_hash=bundle_hash,
                detail=f"fetch failed ({fetch_error}); manifest {manifest_id} missing for rebuild",
            )
        pkg = await PackageService.get_instance()
        meta = await pkg.build_package_from_manifest(manifest)
        return PackageFetchResult(
            action="rebuilt",
            bundle_hash=bundle_hash,
            path=getattr(meta, "package_path", None) or str(meta),
            detail=f"fetch failed ({fetch_error}); rebuilt from OKH URLs",
        )
    except Exception as e:
        return PackageFetchResult(
            action="failed",
            bundle_hash=bundle_hash,
            detail=f"fetch failed ({fetch_error}); rebuild failed ({e})",
        )
