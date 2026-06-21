"""Sourcing resolution domain models — per-component procurement decision."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SourcingVerdict(str, Enum):
    FLEET_AVAILABLE = "fleet_available"  # harvestable match found in fleet
    PROCURE_NEW = "procure_new"  # no fleet match, must order


@dataclass
class SourcingResolutionItem:
    """Per-component sourcing verdict with available fleet matches."""

    component_name: str
    verdict: SourcingVerdict
    part_number: Optional[str] = None
    matches: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_name": self.component_name,
            "verdict": self.verdict.value,
            "part_number": self.part_number,
            "matches": self.matches,
            "match_count": len(self.matches),
        }


@dataclass
class SourcingResolution:
    """Resolution plan for all source_new components on one asset."""

    asset_id: str
    asset_tag: str
    manifest_id: str
    items: List[SourcingResolutionItem] = field(default_factory=list)

    @property
    def fleet_available_count(self) -> int:
        return sum(
            1 for i in self.items if i.verdict == SourcingVerdict.FLEET_AVAILABLE
        )

    @property
    def procure_new_count(self) -> int:
        return sum(1 for i in self.items if i.verdict == SourcingVerdict.PROCURE_NEW)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_tag": self.asset_tag,
            "manifest_id": self.manifest_id,
            "items": [i.to_dict() for i in self.items],
            "total_components": len(self.items),
            "fleet_available_count": self.fleet_available_count,
            "procure_new_count": self.procure_new_count,
        }
