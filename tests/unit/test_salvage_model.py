"""Unit tests for salvage matching predicate and result model."""

from __future__ import annotations

import pytest

from src.core.models.asset import ComponentCondition, ComponentState
from src.core.models.salvage import SalvageMatch, SalvageMatchResult
from src.core.services.asset_service import _is_salvage_match


class _C:
    """Lightweight stand-in for OKH Component."""

    def __init__(self, part_number=None, salvageable=False, replaceable=False):
        self.part_number = part_number
        self.salvageable = salvageable
        self.replaceable = replaceable


def _cs(name="Blood pump", condition=ComponentCondition.DAMAGED, harvest_viable=True):
    return ComponentState(
        component_name=name,
        condition=condition,
        harvest_viable=harvest_viable,
    )


# ---------------------------------------------------------------------------
# _is_salvage_match
# ---------------------------------------------------------------------------


class TestIsSalvageMatch:
    def test_not_harvest_viable_excluded(self):
        cs = _cs(harvest_viable=False)
        assert not _is_salvage_match(cs, None, "Blood pump", None, None)

    def test_name_substring_match(self):
        cs = _cs("Blood pump module")
        assert _is_salvage_match(cs, None, "pump", None, None)

    def test_name_case_insensitive(self):
        cs = _cs("Blood pump module")
        assert _is_salvage_match(cs, None, "BLOOD", None, None)

    def test_name_no_match(self):
        cs = _cs("Blood pump module")
        assert not _is_salvage_match(cs, None, "filter", None, None)

    def test_no_name_filter_accepts_all(self):
        cs = _cs("Anything")
        assert _is_salvage_match(cs, None, None, None, None)

    def test_part_number_exact_match(self):
        cs = _cs()
        comp = _C(part_number="BLOODPUMP-01")
        assert _is_salvage_match(cs, comp, None, "BLOODPUMP-01", None)

    def test_part_number_no_match(self):
        cs = _cs()
        comp = _C(part_number="FILTER-04")
        assert not _is_salvage_match(cs, comp, None, "BLOODPUMP-01", None)

    def test_part_number_comp_none(self):
        cs = _cs()
        assert not _is_salvage_match(cs, None, None, "BLOODPUMP-01", None)

    def test_conditions_filter_match(self):
        cs = _cs(condition=ComponentCondition.DAMAGED)
        assert _is_salvage_match(cs, None, "pump", None, ["damaged", "intact"])

    def test_conditions_filter_no_match(self):
        cs = _cs(condition=ComponentCondition.MISSING)
        assert not _is_salvage_match(cs, None, "pump", None, ["intact"])

    def test_name_and_part_number_both_required(self):
        cs = _cs("Blood pump")
        comp = _C(part_number="BLOODPUMP-01")
        assert _is_salvage_match(cs, comp, "pump", "BLOODPUMP-01", None)

    def test_name_matches_part_number_misses(self):
        cs = _cs("Blood pump")
        comp = _C(part_number="WRONG")
        assert not _is_salvage_match(cs, comp, "pump", "BLOODPUMP-01", None)

    def test_intact_component_included(self):
        cs = _cs(condition=ComponentCondition.INTACT, harvest_viable=True)
        assert _is_salvage_match(cs, None, None, None, None)


# ---------------------------------------------------------------------------
# SalvageMatchResult
# ---------------------------------------------------------------------------


class TestSalvageMatchResult:
    def _match(self, name="Blood pump"):
        return SalvageMatch(
            asset_id="a1",
            asset_tag="SN-01",
            manifest_id="m1",
            component_name=name,
            condition="damaged",
        )

    def test_total_property(self):
        result = SalvageMatchResult(matches=[self._match(), self._match("Filter")])
        assert result.total == 2

    def test_empty_result(self):
        result = SalvageMatchResult()
        assert result.total == 0
        d = result.to_dict()
        assert d["matches"] == []
        assert d["total"] == 0

    def test_to_dict_shape(self):
        result = SalvageMatchResult(
            matches=[self._match()],
            query_component_name="pump",
            query_manifest_id="m1",
        )
        d = result.to_dict()
        assert d["total"] == 1
        assert d["query"]["component_name"] == "pump"
        assert d["query"]["manifest_id"] == "m1"
        assert d["query"]["part_number"] is None
        assert d["matches"][0]["component_name"] == "Blood pump"
