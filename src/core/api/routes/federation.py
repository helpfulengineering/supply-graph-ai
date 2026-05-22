"""Federation API routes (catalog identify, list, record fetch)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.config import settings
from src.core.api.models.federation.response import (
    CatalogListResponse,
    FederationHealthResponse,
    IdentifyResponse,
    SignedManifestRecordResponse,
)
from src.core.federation.service import FederationService
from src.core.utils.logging import get_logger
from src.core.version import get_version

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/federation",
    tags=["federation"],
)


async def get_federation_service() -> FederationService:
    return await FederationService.get_instance()


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


@router.get(
    "/identify",
    response_model=IdentifyResponse,
    summary="Identify this federation node",
)
async def identify(
    service: FederationService = Depends(require_federation_api),
) -> IdentifyResponse:
    index = await service.build_catalog_index()
    assert service.identity is not None
    return IdentifyResponse(
        did=service.identity.did,
        display_name=service.identity.display_name,
        role=service.role.value,
        ohm_version=get_version(),
        catalog_record_count=index.record_count,
        merkle_root=index.merkle_root,
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
