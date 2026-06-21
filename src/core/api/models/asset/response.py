from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AssetResponse(BaseModel):
    id: str
    manifest_id: str
    asset_tag: str
    location: Optional[str] = None
    component_states: List[Dict[str, Any]] = []
    last_triaged_at: Optional[str] = None
    triage_notes: Optional[str] = None


class AssetListResponse(BaseModel):
    assets: List[AssetResponse]
    total: int
