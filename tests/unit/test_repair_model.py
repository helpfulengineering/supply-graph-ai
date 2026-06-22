"""Unit tests for TriageAction derivation logic and TriageReport model."""

from __future__ import annotations

import pytest

from src.core.models.asset import ComponentCondition, ComponentState
from src.core.models.repair import TriageAction, TriageItem, TriageReport
from src.core.services.asset_service import _derive_action, _derive_flags

# ---------------------------------------------------------------------------
# Minimal stand-in for a manifest Component
# ---------------------------------------------------------------------------


class _C:
    """Lightweight stand-in for OKH Component."""

    def __init__(self, replaceable=False, salvageable=False, consumable=False):
        self.replaceable = replaceable
        self.salvageable = salvageable
        self.consumable = consumable


# ---------------------------------------------------------------------------
# _derive_action
# ---------------------------------------------------------------------------


class TestDeriveAction:
    def _cs(
        self, condition, repair_feasible=None, harvest_viable=None, source_required=None
    ):
        return ComponentState(
            component_name="Test",
            condition=condition,
            repair_feasible=repair_feasible,
            harvest_viable=harvest_viable,
            source_required=source_required,
        )

    def test_none_state_returns_assess(self):
        assert _derive_action(None, _C()) == TriageAction.ASSESS

    def test_unknown_condition_returns_assess(self):
        cs = self._cs(ComponentCondition.UNKNOWN)
        assert _derive_action(cs, _C()) == TriageAction.ASSESS

    def test_intact_returns_no_action(self):
        cs = self._cs(ComponentCondition.INTACT)
        assert _derive_action(cs, _C(replaceable=True)) == TriageAction.NO_ACTION

    def test_damaged_repair_feasible_returns_repair_in_place(self):
        cs = self._cs(ComponentCondition.DAMAGED, repair_feasible=True)
        assert _derive_action(cs, _C()) == TriageAction.REPAIR_IN_PLACE

    def test_damaged_not_feasible_salvageable_returns_harvest(self):
        cs = self._cs(ComponentCondition.DAMAGED, repair_feasible=False)
        assert _derive_action(cs, _C(salvageable=True)) == TriageAction.HARVEST

    def test_damaged_not_feasible_replaceable_returns_source_new(self):
        cs = self._cs(ComponentCondition.DAMAGED, repair_feasible=False)
        assert _derive_action(cs, _C(replaceable=True)) == TriageAction.SOURCE_NEW

    def test_damaged_neither_returns_decommission(self):
        cs = self._cs(ComponentCondition.DAMAGED, repair_feasible=False)
        assert _derive_action(cs, _C()) == TriageAction.DECOMMISSION

    def test_missing_replaceable_returns_source_new(self):
        cs = self._cs(ComponentCondition.MISSING)
        assert _derive_action(cs, _C(replaceable=True)) == TriageAction.SOURCE_NEW

    def test_missing_not_replaceable_returns_decommission(self):
        cs = self._cs(ComponentCondition.MISSING)
        assert _derive_action(cs, _C()) == TriageAction.DECOMMISSION

    def test_damaged_repair_feasible_none_salvageable_prefers_harvest(self):
        # repair_feasible=None is not True, so check salvageable path
        cs = self._cs(ComponentCondition.DAMAGED, repair_feasible=None)
        assert _derive_action(cs, _C(salvageable=True)) == TriageAction.HARVEST

    def test_derive_with_no_comp_context(self):
        # When no manifest component is available, damaged → decommission
        cs = self._cs(ComponentCondition.DAMAGED)
        assert _derive_action(cs, None) == TriageAction.DECOMMISSION


# ---------------------------------------------------------------------------
# _derive_flags — flag write-back for record_triage (GAP-1)
# ---------------------------------------------------------------------------


class TestDeriveFlags:
    def test_harvest_sets_harvest_viable_true(self):
        flags = _derive_flags(TriageAction.HARVEST)
        assert flags["harvest_viable"] is True
        assert flags["repair_feasible"] is False
        assert flags["source_required"] is False

    def test_source_new_sets_source_required_true(self):
        flags = _derive_flags(TriageAction.SOURCE_NEW)
        assert flags["source_required"] is True
        assert flags["harvest_viable"] is False
        assert flags["repair_feasible"] is False

    def test_repair_in_place_sets_repair_feasible_true(self):
        flags = _derive_flags(TriageAction.REPAIR_IN_PLACE)
        assert flags["repair_feasible"] is True
        assert flags["harvest_viable"] is False
        assert flags["source_required"] is False

    def test_decommission_sets_all_false(self):
        flags = _derive_flags(TriageAction.DECOMMISSION)
        assert flags["harvest_viable"] is False
        assert flags["repair_feasible"] is False
        assert flags["source_required"] is False

    def test_no_action_sets_only_source_required_false(self):
        flags = _derive_flags(TriageAction.NO_ACTION)
        assert flags["source_required"] is False
        assert "harvest_viable" not in flags
        assert "repair_feasible" not in flags

    def test_assess_returns_empty(self):
        assert _derive_flags(TriageAction.ASSESS) == {}

    def test_caller_value_wins_over_derived(self):
        """Simulate what record_triage does: only fill None fields."""
        cs = ComponentState(
            component_name="X",
            condition=ComponentCondition.DAMAGED,
            harvest_viable=True,  # caller explicitly set True
        )
        flags = _derive_flags(TriageAction.HARVEST)
        # harvest_viable is not None, so it should not be overwritten
        for flag, value in flags.items():
            if getattr(cs, flag) is None:
                setattr(cs, flag, value)
        assert cs.harvest_viable is True  # unchanged

    def test_none_fields_are_filled(self):
        """Simulate what record_triage does for a component with no flags set."""
        cs = ComponentState(
            component_name="Blood pump",
            condition=ComponentCondition.DAMAGED,
            # harvest_viable, repair_feasible, source_required all None
        )
        flags = _derive_flags(TriageAction.HARVEST)
        for flag, value in flags.items():
            if getattr(cs, flag) is None:
                setattr(cs, flag, value)
        assert cs.harvest_viable is True
        assert cs.repair_feasible is False
        assert cs.source_required is False


# ---------------------------------------------------------------------------
# TriageReport — summary properties
# ---------------------------------------------------------------------------


class TestTriageReport:
    def _item(self, action: TriageAction) -> TriageItem:
        return TriageItem(component_name="X", recommended_action=action)

    def test_summary_counts(self):
        report = TriageReport(
            asset_id="a",
            manifest_id="m",
            asset_tag="SN-1",
            items=[
                self._item(TriageAction.ASSESS),
                self._item(TriageAction.ASSESS),
                self._item(TriageAction.NO_ACTION),
                self._item(TriageAction.REPAIR_IN_PLACE),
                self._item(TriageAction.HARVEST),
                self._item(TriageAction.SOURCE_NEW),
                self._item(TriageAction.DECOMMISSION),
            ],
        )
        assert report.total_components == 7
        assert report.needs_assessment == 2
        assert report.no_action_count == 1
        assert report.repair_in_place_count == 1
        assert report.harvest_count == 1
        assert report.source_new_count == 1
        assert report.decommission_count == 1

    def test_to_dict_shape(self):
        report = TriageReport(
            asset_id="a",
            manifest_id="m",
            asset_tag="SN-1",
            items=[self._item(TriageAction.NO_ACTION)],
        )
        d = report.to_dict()
        assert d["asset_id"] == "a"
        assert d["manifest_id"] == "m"
        assert len(d["items"]) == 1
        assert d["items"][0]["recommended_action"] == "no_action"
        assert "summary" in d
        assert d["summary"]["total_components"] == 1
        assert d["summary"]["no_action"] == 1

    def test_empty_report(self):
        report = TriageReport(asset_id="a", manifest_id="m", asset_tag="SN-0")
        assert report.total_components == 0
        assert report.needs_assessment == 0
        d = report.to_dict()
        assert d["items"] == []
        assert d["summary"]["total_components"] == 0
