"""Request models for Asset endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AssetCreateRequest(BaseModel):
    manifest_id: str = Field(
        ..., description="UUID of the OKH manifest this unit instantiates"
    )
    asset_tag: str = Field(
        ..., description="Human-readable tag (e.g. serial number or location code)"
    )
    location: Optional[str] = Field(
        None, description="Physical location of the device unit"
    )


class AssetUpdateRequest(BaseModel):
    asset_tag: Optional[str] = Field(None, description="Updated asset tag")
    location: Optional[str] = Field(None, description="Updated physical location")
    status: Optional[str] = Field(
        None,
        description=(
            "Lifecycle status. One of: active, under_triage, parts_pending, "
            "under_repair, restored, condemned"
        ),
    )
    triage_notes: Optional[str] = Field(
        None, description="Free-text notes from most recent triage"
    )


class AssetTriageRequest(BaseModel):
    """Record observed component conditions for an asset.

    Each entry in component_states maps to a named component in the manifest.
    A second call for the same component_name replaces the prior state.
    """

    component_states: List[Dict[str, Any]] = Field(
        ...,
        description=(
            "List of component state objects. Each must include component_name "
            "and condition (intact | damaged | missing | unknown). "
            "Optional: harvest_viable, repair_feasible, source_required, notes, "
            "assessed_by."
        ),
    )
    triage_notes: Optional[str] = Field(
        None, description="Free-text session notes appended to the asset record"
    )


class SalvageMatchRequest(BaseModel):
    """Query for harvestable component matches across the fleet.

    At least one of component_name or part_number must be provided.
    When manifest_id is supplied, the search is scoped to that manifest and
    any manifests listed in its compatible_manifest_ids (GAP-8).
    """

    component_name: Optional[str] = Field(
        None, description="Component name to match (fuzzy, case-insensitive)"
    )
    part_number: Optional[str] = Field(None, description="Exact part number to match")
    manifest_id: Optional[str] = Field(
        None,
        description=(
            "Scope the search to a specific manifest UUID. "
            "Also searches compatible manifests declared via compatible_manifest_ids."
        ),
    )
    conditions: Optional[List[str]] = Field(
        None,
        description=(
            "Filter by component condition. "
            "Allowed values: intact, damaged, missing, unknown. "
            "Defaults to all conditions."
        ),
    )
    exclude_claimed: bool = Field(
        True,
        description=(
            "When true (default), components already claimed by a coordinator "
            "are excluded from results."
        ),
    )


class ClaimComponentRequest(BaseModel):
    """Reserve a specific component on an asset for retrieval by a coordinator."""

    component_name: str = Field(..., description="Name of the component to claim")
    claimed_by: str = Field(
        ..., description="Identifier of the coordinator claiming the component"
    )
