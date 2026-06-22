"""Unit tests for SourcingResolution domain model."""

from __future__ import annotations

from src.core.models.sourcing import (
    SourcingResolution,
    SourcingResolutionItem,
    SourcingVerdict,
)


def _item(verdict: SourcingVerdict, matches=None) -> SourcingResolutionItem:
    return SourcingResolutionItem(
        component_name="X",
        verdict=verdict,
        matches=matches or [],
    )


class TestSourcingVerdict:
    def test_values(self):
        assert SourcingVerdict.FLEET_AVAILABLE.value == "fleet_available"
        assert SourcingVerdict.PROCURE_NEW.value == "procure_new"


class TestSourcingResolutionItem:
    def test_to_dict_fleet_available(self):
        match = {"asset_id": "a", "component_name": "X"}
        item = SourcingResolutionItem(
            component_name="Pump",
            verdict=SourcingVerdict.FLEET_AVAILABLE,
            part_number="PN-01",
            matches=[match],
        )
        d = item.to_dict()
        assert d["verdict"] == "fleet_available"
        assert d["match_count"] == 1
        assert d["matches"] == [match]
        assert d["part_number"] == "PN-01"

    def test_to_dict_procure_new(self):
        item = SourcingResolutionItem(
            component_name="Filter", verdict=SourcingVerdict.PROCURE_NEW
        )
        d = item.to_dict()
        assert d["verdict"] == "procure_new"
        assert d["match_count"] == 0
        assert d["matches"] == []


class TestSourcingResolution:
    def test_counts(self):
        resolution = SourcingResolution(
            asset_id="a",
            asset_tag="SN-1",
            manifest_id="m",
            items=[
                _item(SourcingVerdict.FLEET_AVAILABLE),
                _item(SourcingVerdict.FLEET_AVAILABLE),
                _item(SourcingVerdict.PROCURE_NEW),
            ],
        )
        assert resolution.fleet_available_count == 2
        assert resolution.procure_new_count == 1

    def test_empty_resolution(self):
        resolution = SourcingResolution(asset_id="a", asset_tag="SN-0", manifest_id="m")
        assert resolution.fleet_available_count == 0
        assert resolution.procure_new_count == 0

    def test_to_dict_shape(self):
        resolution = SourcingResolution(
            asset_id="a",
            asset_tag="SN-1",
            manifest_id="m",
            items=[_item(SourcingVerdict.PROCURE_NEW)],
        )
        d = resolution.to_dict()
        assert d["asset_id"] == "a"
        assert d["total_components"] == 1
        assert d["fleet_available_count"] == 0
        assert d["procure_new_count"] == 1
        assert len(d["items"]) == 1
