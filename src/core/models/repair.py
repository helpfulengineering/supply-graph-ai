"""Repair triage domain models — derived view joining AssetRecord + OKHManifest."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TriageAction(str, Enum):
    ASSESS = "assess"
    NO_ACTION = "no_action"
    REPAIR_IN_PLACE = "repair_in_place"
    HARVEST = "harvest"
    SOURCE_NEW = "source_new"
    DECOMMISSION = "decommission"


@dataclass
class TriageItem:
    """Per-component recommendation derived from observed condition + design flags."""

    component_name: str
    recommended_action: TriageAction
    condition: str = "not_assessed"
    repair_feasible: Optional[bool] = None
    harvest_viable: Optional[bool] = None
    source_required: Optional[bool] = None
    notes: Optional[str] = None
    # from OKH manifest
    replaceable: bool = False
    salvageable: bool = False
    consumable: bool = False
    part_number: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_name": self.component_name,
            "recommended_action": self.recommended_action.value,
            "condition": self.condition,
            "repair_feasible": self.repair_feasible,
            "harvest_viable": self.harvest_viable,
            "source_required": self.source_required,
            "notes": self.notes,
            "replaceable": self.replaceable,
            "salvageable": self.salvageable,
            "consumable": self.consumable,
            "part_number": self.part_number,
        }


@dataclass
class TriageReport:
    """Triage report for one physical unit — not stored, generated on demand."""

    asset_id: str
    manifest_id: str
    asset_tag: str
    items: List[TriageItem] = field(default_factory=list)
    last_triaged_at: Optional[str] = None
    triage_notes: Optional[str] = None

    @property
    def total_components(self) -> int:
        return len(self.items)

    @property
    def needs_assessment(self) -> int:
        return sum(1 for i in self.items if i.recommended_action == TriageAction.ASSESS)

    @property
    def repair_in_place_count(self) -> int:
        return sum(
            1
            for i in self.items
            if i.recommended_action == TriageAction.REPAIR_IN_PLACE
        )

    @property
    def harvest_count(self) -> int:
        return sum(
            1 for i in self.items if i.recommended_action == TriageAction.HARVEST
        )

    @property
    def source_new_count(self) -> int:
        return sum(
            1 for i in self.items if i.recommended_action == TriageAction.SOURCE_NEW
        )

    @property
    def no_action_count(self) -> int:
        return sum(
            1 for i in self.items if i.recommended_action == TriageAction.NO_ACTION
        )

    @property
    def decommission_count(self) -> int:
        return sum(
            1 for i in self.items if i.recommended_action == TriageAction.DECOMMISSION
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "manifest_id": self.manifest_id,
            "asset_tag": self.asset_tag,
            "last_triaged_at": self.last_triaged_at,
            "triage_notes": self.triage_notes,
            "items": [i.to_dict() for i in self.items],
            "summary": {
                "total_components": self.total_components,
                "needs_assessment": self.needs_assessment,
                "repair_in_place": self.repair_in_place_count,
                "harvest": self.harvest_count,
                "source_new": self.source_new_count,
                "no_action": self.no_action_count,
                "decommission": self.decommission_count,
            },
        }
