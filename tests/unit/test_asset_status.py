"""Unit tests for AssetStatus lifecycle field on AssetRecord."""

from __future__ import annotations

import pytest

from src.core.models.asset import AssetRecord, AssetStatus


def _minimal_record(**kwargs) -> AssetRecord:
    base = {"manifest_id": "m-1", "asset_tag": "SN-001"}
    base.update(kwargs)
    return AssetRecord.from_dict(base)


class TestAssetStatusEnum:
    def test_all_values_are_lowercase_strings(self):
        expected = {
            "active",
            "under_triage",
            "parts_pending",
            "under_repair",
            "restored",
            "condemned",
        }
        assert {s.value for s in AssetStatus} == expected

    def test_construction_from_value(self):
        assert AssetStatus("under_triage") == AssetStatus.UNDER_TRIAGE

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            AssetStatus("not_a_status")


class TestAssetRecordStatusRoundTrip:
    def test_default_status_is_active(self):
        record = _minimal_record()
        assert record.status == AssetStatus.ACTIVE

    def test_to_dict_includes_status(self):
        record = _minimal_record()
        assert record.to_dict()["status"] == "active"

    def test_from_dict_restores_non_default_status(self):
        record = _minimal_record()
        record.status = AssetStatus.UNDER_TRIAGE
        restored = AssetRecord.from_dict(record.to_dict())
        assert restored.status == AssetStatus.UNDER_TRIAGE

    def test_round_trip_all_statuses(self):
        for s in AssetStatus:
            record = _minimal_record()
            record.status = s
            restored = AssetRecord.from_dict(record.to_dict())
            assert restored.status == s


class TestAssetStatusMigrationSafety:
    def test_missing_status_key_defaults_to_active(self):
        data = {"manifest_id": "m-1", "asset_tag": "SN-OLD"}
        record = AssetRecord.from_dict(data)
        assert record.status == AssetStatus.ACTIVE

    def test_null_status_defaults_to_active(self):
        data = {"manifest_id": "m-1", "asset_tag": "SN-NULL", "status": None}
        record = AssetRecord.from_dict(data)
        assert record.status == AssetStatus.ACTIVE

    def test_empty_string_status_defaults_to_active(self):
        data = {"manifest_id": "m-1", "asset_tag": "SN-EMPTY", "status": ""}
        record = AssetRecord.from_dict(data)
        assert record.status == AssetStatus.ACTIVE

    def test_unknown_string_defaults_to_active(self):
        data = {"manifest_id": "m-1", "asset_tag": "SN-BAD", "status": "legacy_value"}
        record = AssetRecord.from_dict(data)
        assert record.status == AssetStatus.ACTIVE
