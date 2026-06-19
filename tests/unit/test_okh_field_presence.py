"""Unit tests for OKH field presence and coverage reporting (issue #171)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# _field_is_present
# ---------------------------------------------------------------------------


def _fp(value):
    from src.core.validation.model_validator import _field_is_present

    return _field_is_present(value)


def test_none_is_absent():
    assert _fp(None) is False


def test_empty_string_is_absent():
    assert _fp("") is False
    assert _fp("   ") is False


def test_nonempty_string_is_present():
    assert _fp("hello") is True


def test_empty_list_is_absent():
    assert _fp([]) is False


def test_nonempty_list_is_present():
    assert _fp(["item"]) is True


def test_empty_dict_is_absent():
    assert _fp({}) is False


def test_nonempty_dict_is_present():
    assert _fp({"key": "val"}) is True


def test_zero_int_is_present():
    assert _fp(0) is True


def test_false_bool_is_present():
    assert _fp(False) is True


# ---------------------------------------------------------------------------
# _compute_okh_field_presence
# ---------------------------------------------------------------------------


def _make_manifest(**kwargs):
    from src.core.models.okh import OKHManifest

    defaults = {
        "title": "Test Project",
        "version": "1.0",
        "license": {"hardware": "MIT"},
        "licensor": "Alice",
        "documentation_language": "en",
        "function": "Test function",
    }
    defaults.update(kwargs)
    return OKHManifest.from_dict(defaults)


def test_all_required_present_gives_required_coverage_1():
    from src.core.validation.model_validator import _compute_okh_field_presence

    manifest = _make_manifest()
    result = _compute_okh_field_presence(manifest)
    assert result["required_coverage"] == 1.0


def test_missing_required_field_lowers_required_coverage():
    from src.core.validation.model_validator import _compute_okh_field_presence

    manifest = _make_manifest(function="")
    result = _compute_okh_field_presence(manifest)
    assert result["required_coverage"] < 1.0


def test_no_optional_fields_gives_optional_coverage_0():
    from src.core.validation.model_validator import _compute_okh_field_presence

    manifest = _make_manifest()
    result = _compute_okh_field_presence(manifest)
    assert result["optional_coverage"] == 0.0


def test_optional_field_raises_optional_coverage():
    from src.core.validation.model_validator import _compute_okh_field_presence

    manifest = _make_manifest(description="A useful device", bom=[{"name": "bolt"}])
    result = _compute_okh_field_presence(manifest)
    assert result["optional_coverage"] > 0.0


def test_field_presence_map_contains_required_keys():
    from src.core.validation.model_validator import (
        _OKH_REQUIRED_FIELDS,
        _compute_okh_field_presence,
    )

    manifest = _make_manifest()
    result = _compute_okh_field_presence(manifest)
    for field in _OKH_REQUIRED_FIELDS:
        assert field in result["field_presence"]


def test_field_presence_map_contains_optional_keys():
    from src.core.validation.model_validator import (
        _OKH_OPTIONAL_FIELDS,
        _compute_okh_field_presence,
    )

    manifest = _make_manifest()
    result = _compute_okh_field_presence(manifest)
    for field in _OKH_OPTIONAL_FIELDS:
        assert field in result["field_presence"]


def test_field_presence_bools_are_accurate():
    from src.core.validation.model_validator import _compute_okh_field_presence

    manifest = _make_manifest(description="filled", bom=[])
    result = _compute_okh_field_presence(manifest)
    assert result["field_presence"]["description"] is True
    assert result["field_presence"]["bom"] is False


# ---------------------------------------------------------------------------
# validate_okh_manifest wires in field_presence data
# ---------------------------------------------------------------------------


def test_validate_okh_manifest_details_include_field_presence():
    from src.core.validation.model_validator import validate_okh_manifest

    manifest_dict = {
        "title": "Test",
        "version": "1.0",
        "license": {"hardware": "MIT"},
        "licensor": "Alice",
        "documentation_language": "en",
        "function": "Does stuff",
    }
    result = validate_okh_manifest(manifest_dict)
    assert "field_presence" in result.details
    assert "required_coverage" in result.details
    assert "optional_coverage" in result.details


def test_validate_okh_manifest_required_coverage_is_float():
    from src.core.validation.model_validator import validate_okh_manifest

    manifest_dict = {
        "title": "Test",
        "version": "1.0",
        "license": {"hardware": "MIT"},
        "licensor": "Alice",
        "documentation_language": "en",
        "function": "Does stuff",
    }
    result = validate_okh_manifest(manifest_dict)
    assert isinstance(result.details["required_coverage"], float)
    assert 0.0 <= result.details["required_coverage"] <= 1.0


# ---------------------------------------------------------------------------
# ValidationResult Pydantic model carries metadata field
# ---------------------------------------------------------------------------


def test_validation_result_metadata_field_exists():
    from src.core.api.models.base import ValidationResult

    vr = ValidationResult(
        is_valid=True,
        score=1.0,
        metadata={"required_coverage": 1.0, "optional_coverage": 0.2},
    )
    assert vr.metadata["required_coverage"] == 1.0


def test_validation_result_metadata_optional():
    from src.core.api.models.base import ValidationResult

    vr = ValidationResult(is_valid=True, score=1.0)
    assert vr.metadata is None


def test_model_validation_result_to_api_format_passes_metadata():
    from src.core.validation.model_validator import ModelValidationResult

    mvr = ModelValidationResult(valid=True)
    mvr.details["field_presence"] = {"title": True, "bom": False}
    mvr.details["required_coverage"] = 1.0
    mvr.details["optional_coverage"] = 0.0

    api = mvr.to_api_format()
    assert api["metadata"]["required_coverage"] == 1.0
    assert api["metadata"]["field_presence"]["title"] is True
