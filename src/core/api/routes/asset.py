"""REST endpoints for AssetRecord — physical state of device units in the field."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel

from ...models.asset import AssetRecord, AssetStatus, ComponentState
from ...services.asset_service import AssetService
from ...utils.logging import get_logger
from ..models.asset.response import (
    AssetListResponse,
    AssetResponse,
    SalvageMatchItemResponse,
    SalvageMatchResponse,
    SalvageQueryResponse,
    TriageItemResponse,
    TriageReportResponse,
    TriageSummaryResponse,
)

logger = get_logger(__name__)

router = APIRouter(tags=["asset"])


async def get_asset_service() -> AssetService:
    return await AssetService.get_instance()


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class AssetCreateRequest(BaseModel):
    manifest_id: str
    asset_tag: str
    location: Optional[str] = None


class AssetUpdateRequest(BaseModel):
    asset_tag: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    triage_notes: Optional[str] = None


class AssetTriageRequest(BaseModel):
    component_states: List[Dict[str, Any]]
    triage_notes: Optional[str] = None


class SalvageMatchRequest(BaseModel):
    component_name: Optional[str] = None
    part_number: Optional[str] = None
    manifest_id: Optional[str] = None
    conditions: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_response(record: AssetRecord) -> AssetResponse:
    return AssetResponse(
        id=str(record.id),
        manifest_id=record.manifest_id,
        asset_tag=record.asset_tag,
        location=record.location,
        status=record.status.value,
        component_states=[cs.to_dict() for cs in record.component_states],
        last_triaged_at=(
            record.last_triaged_at.isoformat() if record.last_triaged_at else None
        ),
        triage_notes=record.triage_notes,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an asset record",
)
async def create_asset(
    body: AssetCreateRequest,
    svc: AssetService = Depends(get_asset_service),
) -> Any:
    """Register a physical unit in the field, linked to an OKH manifest."""
    record = await svc.create(
        {
            "manifest_id": body.manifest_id,
            "asset_tag": body.asset_tag,
            "location": body.location,
        }
    )
    return _to_response(record)


@router.get(
    "/{id}",
    response_model=AssetResponse,
    summary="Get an asset record",
)
async def get_asset(
    id: UUID = Path(...),
    svc: AssetService = Depends(get_asset_service),
) -> Any:
    record = await svc.get(id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {id} not found"
        )
    return _to_response(record)


@router.get(
    "/",
    response_model=AssetListResponse,
    summary="List asset records",
    description="""
    List all asset records, optionally scoped to a single design.

    Pass `?manifest_id=<uuid>` to return only assets for that OKH manifest.

    Pass `?status=<value>` to filter by lifecycle status
    (`active` | `under_triage` | `parts_pending` | `under_repair` | `restored` | `condemned`).

    Pass `?harvest_viable=true` to filter component_states on each asset down
    to only those where `harvest_viable` is True; assets with no such states
    are excluded from the response.
    """,
)
async def list_assets(
    manifest_id: Optional[str] = Query(
        None, description="Filter to this manifest UUID"
    ),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by lifecycle status"
    ),
    harvest_viable: Optional[bool] = Query(
        None, description="When true, return only assets with harvestable components"
    ),
    svc: AssetService = Depends(get_asset_service),
) -> Any:
    records = await svc.list(manifest_id=manifest_id)

    if status_filter is not None:
        try:
            wanted = AssetStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status {status_filter!r}. Valid values: "
                + ", ".join(s.value for s in AssetStatus),
            )
        records = [r for r in records if r.status == wanted]

    if harvest_viable:
        filtered = []
        for r in records:
            viable_states = [cs for cs in r.component_states if cs.harvest_viable]
            if viable_states:
                r.component_states = viable_states
                filtered.append(r)
        records = filtered

    assets = [_to_response(r) for r in records]
    return AssetListResponse(assets=assets, total=len(assets))


@router.put(
    "/{id}",
    response_model=AssetResponse,
    summary="Update an asset record",
)
async def update_asset(
    body: AssetUpdateRequest,
    id: UUID = Path(...),
    svc: AssetService = Depends(get_asset_service),
) -> Any:
    record = await svc.get(id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {id} not found"
        )
    if body.asset_tag is not None:
        record.asset_tag = body.asset_tag
    if body.location is not None:
        record.location = body.location
    if body.triage_notes is not None:
        record.triage_notes = body.triage_notes
    if body.status is not None:
        try:
            record.status = AssetStatus(body.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status {body.status!r}. Valid values: "
                + ", ".join(s.value for s in AssetStatus),
            )
    updated = await svc.update(id, record.to_dict())
    return _to_response(updated)


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an asset record",
)
async def delete_asset(
    id: UUID = Path(...),
    svc: AssetService = Depends(get_asset_service),
) -> Any:
    deleted = await svc.delete(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {id} not found"
        )
    return {"success": True, "message": f"Asset {id} deleted"}


@router.post(
    "/{id}/triage",
    response_model=AssetResponse,
    summary="Record triage results for an asset",
    description="""
    Upsert component states by `component_name`. A second call for the same
    component name replaces the prior state. `last_triaged_at` is updated to now.
    """,
)
async def record_triage(
    body: AssetTriageRequest,
    id: UUID = Path(...),
    svc: AssetService = Depends(get_asset_service),
) -> Any:
    states: list[ComponentState] = []
    for raw in body.component_states:
        try:
            states.append(ComponentState.from_dict(raw))
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid component state: {exc}",
            )
    try:
        record = await svc.record_triage(id, states, body.triage_notes)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {id} not found"
        )
    return _to_response(record)


@router.get(
    "/{id}/triage-report",
    response_model=TriageReportResponse,
    summary="Generate a repair triage report for an asset",
    description="""
    Join the AssetRecord (physical observations) with the linked OKH manifest
    (design flags) to produce a per-component repair recommendation.

    **Recommended actions:**
    - `assess` — component not yet triaged, or condition is unknown
    - `no_action` — component is intact, no work needed
    - `repair_in_place` — damaged but technician flagged as repair-feasible
    - `harvest` — damaged/missing, salvageable per design, pull for use elsewhere
    - `source_new` — damaged/missing, replaceable per design, must be sourced
    - `decommission` — damaged/missing, not replaceable or salvageable
    """,
)
async def get_triage_report(
    id: UUID = Path(...),
    svc: AssetService = Depends(get_asset_service),
) -> Any:
    try:
        report = await svc.generate_triage_report(id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {id} not found"
        )
    return TriageReportResponse(
        asset_id=report.asset_id,
        manifest_id=report.manifest_id,
        asset_tag=report.asset_tag,
        last_triaged_at=report.last_triaged_at,
        triage_notes=report.triage_notes,
        items=[TriageItemResponse(**item.to_dict()) for item in report.items],
        summary=TriageSummaryResponse(
            total_components=report.total_components,
            needs_assessment=report.needs_assessment,
            repair_in_place=report.repair_in_place_count,
            harvest=report.harvest_count,
            source_new=report.source_new_count,
            no_action=report.no_action_count,
            decommission=report.decommission_count,
        ),
    )


@router.post(
    "/salvage-match",
    response_model=SalvageMatchResponse,
    summary="Find harvestable components matching a query",
    description="""
    Search the asset fleet for components that are marked `harvest_viable=True`
    and match the supplied filters.

    At least one of `component_name` or `part_number` must be provided.

    - `component_name` — case-insensitive substring match against component names
    - `part_number` — exact match against the manifest component's part number
    - `manifest_id` — scope the search to assets linked to one design
    - `conditions` — restrict to specific observed conditions
      (`intact` | `damaged` | `missing` | `unknown`)
    """,
)
async def salvage_match(
    body: SalvageMatchRequest,
    svc: AssetService = Depends(get_asset_service),
) -> Any:
    if body.component_name is None and body.part_number is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one of 'component_name' or 'part_number' is required.",
        )
    result = await svc.salvage_match(
        component_name=body.component_name,
        part_number=body.part_number,
        manifest_id=body.manifest_id,
        conditions=body.conditions,
    )
    return SalvageMatchResponse(
        matches=[SalvageMatchItemResponse(**m.to_dict()) for m in result.matches],
        total=result.total,
        query=SalvageQueryResponse(
            component_name=result.query_component_name,
            part_number=result.query_part_number,
            manifest_id=result.query_manifest_id,
        ),
    )
