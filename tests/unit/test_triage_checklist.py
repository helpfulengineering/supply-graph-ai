"""Unit tests for TriageChecklist model."""

from __future__ import annotations

from src.core.models.repair import ChecklistItem, TriageChecklist


class TestChecklistItem:
    def test_assessed_false_has_null_state(self):
        item = ChecklistItem(component_name="Pump", assessed=False)
        d = item.to_dict()
        assert d["assessed"] is False
        assert d["current_condition"] is None
        assert d["current_state"] is None

    def test_assessed_true_carries_state(self):
        state = {"component_name": "Pump", "condition": "damaged"}
        item = ChecklistItem(
            component_name="Pump",
            assessed=True,
            current_condition="damaged",
            current_state=state,
        )
        d = item.to_dict()
        assert d["assessed"] is True
        assert d["current_condition"] == "damaged"
        assert d["current_state"] == state

    def test_manifest_flags_included(self):
        item = ChecklistItem(
            component_name="Filter",
            assessed=False,
            replaceable=True,
            salvageable=False,
            consumable=True,
            part_number="FILTER-04",
        )
        d = item.to_dict()
        assert d["replaceable"] is True
        assert d["salvageable"] is False
        assert d["consumable"] is True
        assert d["part_number"] == "FILTER-04"


class TestTriageChecklist:
    def _item(self, assessed: bool) -> ChecklistItem:
        return ChecklistItem(component_name="X", assessed=assessed)

    def test_counts(self):
        checklist = TriageChecklist(
            asset_id="a",
            manifest_id="m",
            asset_tag="SN-1",
            status="under_triage",
            items=[self._item(True), self._item(True), self._item(False)],
        )
        assert checklist.total_components == 3
        assert checklist.assessed_count == 2
        assert checklist.pending_count == 1

    def test_empty_checklist(self):
        checklist = TriageChecklist(
            asset_id="a", manifest_id="m", asset_tag="SN-0", status="active"
        )
        assert checklist.total_components == 0
        assert checklist.assessed_count == 0
        assert checklist.pending_count == 0

    def test_to_dict_shape(self):
        checklist = TriageChecklist(
            asset_id="a",
            manifest_id="m",
            asset_tag="SN-1",
            status="active",
            items=[self._item(False)],
        )
        d = checklist.to_dict()
        assert d["asset_id"] == "a"
        assert d["status"] == "active"
        assert d["total_components"] == 1
        assert d["assessed_count"] == 0
        assert d["pending_count"] == 1
        assert len(d["items"]) == 1
        assert d["items"][0]["assessed"] is False
