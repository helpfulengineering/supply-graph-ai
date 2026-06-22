"""Salvage matching domain models — fleet query results for harvestable components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SalvageMatch:
    """One harvestable component found in the asset fleet."""

    asset_id: str
    asset_tag: str
    manifest_id: str
    component_name: str
    condition: str
    location: Optional[str] = None
    notes: Optional[str] = None
    assessed_by: Optional[str] = None
    observed_at: Optional[str] = None
    # from OKH manifest component
    part_number: Optional[str] = None
    salvageable: bool = False
    replaceable: bool = False
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_tag": self.asset_tag,
            "manifest_id": self.manifest_id,
            "location": self.location,
            "component_name": self.component_name,
            "condition": self.condition,
            "notes": self.notes,
            "assessed_by": self.assessed_by,
            "observed_at": self.observed_at,
            "part_number": self.part_number,
            "salvageable": self.salvageable,
            "replaceable": self.replaceable,
            "claimed_by": self.claimed_by,
            "claimed_at": self.claimed_at,
        }


@dataclass
class SalvageMatchResult:
    """Result of a salvage match query."""

    matches: List[SalvageMatch] = field(default_factory=list)
    query_component_name: Optional[str] = None
    query_part_number: Optional[str] = None
    query_manifest_id: Optional[str] = None

    @property
    def total(self) -> int:
        return len(self.matches)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "total": self.total,
            "query": {
                "component_name": self.query_component_name,
                "part_number": self.query_part_number,
                "manifest_id": self.query_manifest_id,
            },
        }
