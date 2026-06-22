"""Unit tests for the AssetRecord domain model."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from src.core.models.asset import AssetRecord, ComponentCondition, ComponentState

# ---------------------------------------------------------------------------
# ComponentCondition
# ---------------------------------------------------------------------------


def test_condition_values():
    assert ComponentCondition.INTACT.value == "intact"
    assert ComponentCondition.DAMAGED.value == "damaged"
    assert ComponentCondition.MISSING.value == "missing"
    assert ComponentCondition.UNKNOWN.value == "unknown"


# ---------------------------------------------------------------------------
# ComponentState round-trip
# ---------------------------------------------------------------------------


def test_component_state_to_dict_minimal():
    cs = ComponentState(component_name="Blood pump")
    d = cs.to_dict()
    assert d["component_name"] == "Blood pump"
    assert d["condition"] == "unknown"
    assert d["repair_feasible"] is None
    assert d["harvest_viable"] is None
    assert d["observed_at"] is None


def test_component_state_to_dict_full():
    ts = datetime(2026, 6, 20, 12, 0, 0, tzinfo=timezone.utc)
    cs = ComponentState(
        component_name="Pre-filter cartridge",
        condition=ComponentCondition.INTACT,
        repair_feasible=False,
        harvest_viable=True,
        source_required=False,
        notes="Housing intact, element depleted",
        observed_at=ts,
        assessed_by="J. Smith",
    )
    d = cs.to_dict()
    assert d["condition"] == "intact"
    assert d["harvest_viable"] is True
    assert d["assessed_by"] == "J. Smith"
    assert "2026-06-20" in d["observed_at"]


def test_component_state_from_dict_round_trip():
    ts = datetime(2026, 6, 20, 12, 0, 0)
    cs = ComponentState(
        component_name="Flow sensor",
        condition=ComponentCondition.DAMAGED,
        harvest_viable=False,
        source_required=True,
        observed_at=ts,
        assessed_by="Tech A",
    )
    restored = ComponentState.from_dict(cs.to_dict())
    assert restored.component_name == cs.component_name
    assert restored.condition == ComponentCondition.DAMAGED
    assert restored.harvest_viable is False
    assert restored.source_required is True
    assert restored.assessed_by == "Tech A"
    assert restored.observed_at is not None


def test_component_state_from_dict_unknown_condition_fallback():
    cs = ComponentState.from_dict({"component_name": "Widget", "condition": "exploded"})
    assert cs.condition == ComponentCondition.UNKNOWN


def test_component_state_from_dict_missing_observed_at():
    cs = ComponentState.from_dict({"component_name": "X", "observed_at": "bad-date"})
    assert cs.observed_at is None


# ---------------------------------------------------------------------------
# AssetRecord round-trip
# ---------------------------------------------------------------------------


def test_asset_record_defaults():
    ar = AssetRecord(manifest_id="abc-123", asset_tag="SN-001")
    assert isinstance(ar.id, UUID)
    assert ar.location is None
    assert ar.component_states == []
    assert ar.last_triaged_at is None


def test_asset_record_to_dict():
    ar = AssetRecord(manifest_id="m1", asset_tag="T1", location="ICU Bay 3")
    d = ar.to_dict()
    assert d["manifest_id"] == "m1"
    assert d["asset_tag"] == "T1"
    assert d["location"] == "ICU Bay 3"
    assert d["component_states"] == []
    assert isinstance(d["id"], str)


def test_asset_record_from_dict_round_trip():
    ts = datetime(2026, 6, 20, 9, 0, 0)
    ar = AssetRecord(
        manifest_id="manifest-uuid",
        asset_tag="ASSET-007",
        location="Storage Room B",
        component_states=[
            ComponentState(
                component_name="Pump",
                condition=ComponentCondition.DAMAGED,
                harvest_viable=False,
            )
        ],
        last_triaged_at=ts,
        triage_notes="Annual inspection",
    )
    restored = AssetRecord.from_dict(ar.to_dict())
    assert restored.manifest_id == "manifest-uuid"
    assert restored.asset_tag == "ASSET-007"
    assert restored.location == "Storage Room B"
    assert restored.triage_notes == "Annual inspection"
    assert len(restored.component_states) == 1
    assert restored.component_states[0].component_name == "Pump"
    assert restored.component_states[0].condition == ComponentCondition.DAMAGED
    assert restored.last_triaged_at is not None


def test_asset_record_from_dict_bad_id_gets_new_uuid():
    ar = AssetRecord.from_dict(
        {"id": "not-a-uuid", "manifest_id": "m", "asset_tag": "t"}
    )
    assert isinstance(ar.id, UUID)


def test_asset_record_from_dict_missing_id_gets_new_uuid():
    ar = AssetRecord.from_dict({"manifest_id": "m", "asset_tag": "t"})
    assert isinstance(ar.id, UUID)


def test_asset_record_from_dict_skips_bad_component_states():
    d = {
        "manifest_id": "m",
        "asset_tag": "t",
        "component_states": [
            {"component_name": "Good"},
            {"missing_required_field": True},  # no component_name → KeyError
        ],
    }
    ar = AssetRecord.from_dict(d)
    assert len(ar.component_states) == 1
    assert ar.component_states[0].component_name == "Good"
