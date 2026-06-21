"""Asset record domain model — physical state of a specific device unit in the field."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class ComponentCondition(Enum):
    INTACT = "intact"
    DAMAGED = "damaged"
    MISSING = "missing"
    UNKNOWN = "unknown"


@dataclass
class ComponentState:
    """Observed condition of one component on a specific physical unit."""

    component_name: str  # matches Component.name in the referenced OKHManifest
    condition: ComponentCondition = ComponentCondition.UNKNOWN
    repair_feasible: Optional[bool] = None
    harvest_viable: Optional[bool] = None
    source_required: Optional[bool] = None
    notes: Optional[str] = None
    observed_at: Optional[datetime] = None
    assessed_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_name": self.component_name,
            "condition": self.condition.value,
            "repair_feasible": self.repair_feasible,
            "harvest_viable": self.harvest_viable,
            "source_required": self.source_required,
            "notes": self.notes,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "assessed_by": self.assessed_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ComponentState:
        try:
            condition = ComponentCondition(data.get("condition", "unknown"))
        except ValueError:
            condition = ComponentCondition.UNKNOWN

        observed_at = None
        if data.get("observed_at"):
            try:
                observed_at = datetime.fromisoformat(data["observed_at"])
            except (ValueError, TypeError):
                pass

        return cls(
            component_name=data["component_name"],
            condition=condition,
            repair_feasible=data.get("repair_feasible"),
            harvest_viable=data.get("harvest_viable"),
            source_required=data.get("source_required"),
            notes=data.get("notes"),
            observed_at=observed_at,
            assessed_by=data.get("assessed_by"),
        )


@dataclass
class AssetRecord:
    """Physical state of one unit of a device in the field.

    Links to its design via ``manifest_id`` (an OKHManifest UUID) and is
    identified in the real world by ``asset_tag`` (barcode, serial number,
    facility asset number, etc.).

    Stored at ``asset/{id}.json``.
    """

    manifest_id: str  # UUID of the OKHManifest this unit is an instance of
    asset_tag: str  # facility-assigned identifier
    id: UUID = field(default_factory=uuid4)
    location: Optional[str] = None
    component_states: List[ComponentState] = field(default_factory=list)
    last_triaged_at: Optional[datetime] = None
    triage_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "manifest_id": self.manifest_id,
            "asset_tag": self.asset_tag,
            "location": self.location,
            "component_states": [cs.to_dict() for cs in self.component_states],
            "last_triaged_at": (
                self.last_triaged_at.isoformat() if self.last_triaged_at else None
            ),
            "triage_notes": self.triage_notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AssetRecord:
        try:
            parsed_id = UUID(str(data["id"])) if data.get("id") else uuid4()
        except (ValueError, AttributeError):
            parsed_id = uuid4()

        last_triaged_at = None
        if data.get("last_triaged_at"):
            try:
                last_triaged_at = datetime.fromisoformat(data["last_triaged_at"])
            except (ValueError, TypeError):
                pass

        component_states = []
        for cs in data.get("component_states", []):
            try:
                component_states.append(ComponentState.from_dict(cs))
            except Exception:
                continue

        return cls(
            id=parsed_id,
            manifest_id=str(data["manifest_id"]),
            asset_tag=str(data["asset_tag"]),
            location=data.get("location"),
            component_states=component_states,
            last_triaged_at=last_triaged_at,
            triage_notes=data.get("triage_notes"),
        )
