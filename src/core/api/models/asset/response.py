from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AssetResponse(BaseModel):
    id: str
    manifest_id: str
    asset_tag: str
    location: Optional[str] = None
    status: str = "active"
    component_states: List[Dict[str, Any]] = []
    last_triaged_at: Optional[str] = None
    triage_notes: Optional[str] = None


class AssetListResponse(BaseModel):
    assets: List[AssetResponse]
    total: int


class TriageItemResponse(BaseModel):
    component_name: str
    recommended_action: str
    condition: str
    repair_feasible: Optional[bool] = None
    harvest_viable: Optional[bool] = None
    source_required: Optional[bool] = None
    notes: Optional[str] = None
    replaceable: bool = False
    salvageable: bool = False
    consumable: bool = False
    part_number: Optional[str] = None


class TriageSummaryResponse(BaseModel):
    total_components: int
    needs_assessment: int
    repair_in_place: int
    harvest: int
    source_new: int
    no_action: int
    decommission: int


class TriageReportResponse(BaseModel):
    asset_id: str
    manifest_id: str
    asset_tag: str
    last_triaged_at: Optional[str] = None
    triage_notes: Optional[str] = None
    items: List[TriageItemResponse]
    summary: TriageSummaryResponse


class ChecklistItemResponse(BaseModel):
    component_name: str
    assessed: bool
    replaceable: bool = False
    salvageable: bool = False
    consumable: bool = False
    part_number: Optional[str] = None
    current_condition: Optional[str] = None
    current_state: Optional[Dict[str, Any]] = None


class ChecklistResponse(BaseModel):
    asset_id: str
    manifest_id: str
    asset_tag: str
    status: str
    last_triaged_at: Optional[str] = None
    items: List[ChecklistItemResponse]
    total_components: int
    assessed_count: int
    pending_count: int


class SourcingResolutionItemResponse(BaseModel):
    component_name: str
    verdict: str
    part_number: Optional[str] = None
    matches: List[Dict[str, Any]] = []
    match_count: int = 0


class SourcingResolutionResponse(BaseModel):
    asset_id: str
    asset_tag: str
    manifest_id: str
    items: List[SourcingResolutionItemResponse]
    total_components: int
    fleet_available_count: int
    procure_new_count: int


class SalvageMatchItemResponse(BaseModel):
    asset_id: str
    asset_tag: str
    manifest_id: str
    location: Optional[str] = None
    component_name: str
    condition: str
    notes: Optional[str] = None
    assessed_by: Optional[str] = None
    observed_at: Optional[str] = None
    part_number: Optional[str] = None
    salvageable: bool = False
    replaceable: bool = False


class SalvageQueryResponse(BaseModel):
    component_name: Optional[str] = None
    part_number: Optional[str] = None
    manifest_id: Optional[str] = None


class SalvageMatchResponse(BaseModel):
    matches: List[SalvageMatchItemResponse]
    total: int
    query: SalvageQueryResponse
