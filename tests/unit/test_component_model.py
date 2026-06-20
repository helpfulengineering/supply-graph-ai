"""Unit tests for Component data model extension (issue #173)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Component dataclass
# ---------------------------------------------------------------------------


def test_component_defaults():
    from src.core.models.okh import Component

    c = Component(name="Stepper Motor")
    assert c.quantity == 1
    assert c.replaceable is False
    assert c.salvageable is False
    assert c.okh_ref is None
    assert c.product_url is None
    assert c.notes is None


def test_component_to_dict_includes_all_fields():
    from src.core.models.okh import Component

    c = Component(
        name="Raspberry Pi",
        quantity=2,
        replaceable=True,
        salvageable=True,
        okh_ref=None,
        product_url="https://example.com/rpi",
        notes="Any revision works",
    )
    d = c.to_dict()
    assert d["name"] == "Raspberry Pi"
    assert d["quantity"] == 2
    assert d["replaceable"] is True
    assert d["salvageable"] is True
    assert d["product_url"] == "https://example.com/rpi"
    assert d["notes"] == "Any revision works"
    assert d["okh_ref"] is None


def test_component_with_okh_ref():
    from src.core.models.okh import Component

    c = Component(name="Arm Segment", okh_ref="okh/arm-segment/v1.0")
    assert c.okh_ref == "okh/arm-segment/v1.0"
    assert c.to_dict()["okh_ref"] == "okh/arm-segment/v1.0"


# ---------------------------------------------------------------------------
# OKHManifest.from_dict — components parsing
# ---------------------------------------------------------------------------

_MINIMAL = {
    "title": "Test Robot",
    "version": "1.0",
    "license": {"hardware": "MIT"},
    "licensor": "Alice",
    "documentation_language": "en",
    "function": "Moves things",
}


def test_manifest_components_empty_by_default():
    from src.core.models.okh import OKHManifest

    m = OKHManifest.from_dict(_MINIMAL)
    assert m.components == []


def test_manifest_components_from_dicts():
    from src.core.models.okh import OKHManifest

    data = {
        **_MINIMAL,
        "components": [
            {"name": "Stepper Motor", "quantity": 4, "replaceable": True},
            {"name": "Raspberry Pi", "product_url": "https://example.com/rpi"},
        ],
    }
    m = OKHManifest.from_dict(data)
    assert len(m.components) == 2
    assert m.components[0].name == "Stepper Motor"
    assert m.components[0].quantity == 4
    assert m.components[0].replaceable is True
    assert m.components[1].product_url == "https://example.com/rpi"


def test_manifest_components_string_items_backward_compat():
    from src.core.models.okh import OKHManifest

    data = {**_MINIMAL, "components": ["Motor", "Wheel", "Frame"]}
    m = OKHManifest.from_dict(data)
    assert len(m.components) == 3
    assert m.components[0].name == "Motor"
    assert m.components[1].name == "Wheel"
    assert m.components[2].quantity == 1  # default


def test_manifest_components_mixed_items():
    from src.core.models.okh import OKHManifest

    data = {
        **_MINIMAL,
        "components": [
            "Generic bolt",
            {"name": "Stepper Motor", "salvageable": True},
        ],
    }
    m = OKHManifest.from_dict(data)
    assert len(m.components) == 2
    assert m.components[0].name == "Generic bolt"
    assert m.components[1].salvageable is True


def test_manifest_components_missing_optional_fields_default():
    from src.core.models.okh import OKHManifest

    data = {**_MINIMAL, "components": [{"name": "Bolt"}]}
    m = OKHManifest.from_dict(data)
    c = m.components[0]
    assert c.quantity == 1
    assert c.replaceable is False
    assert c.salvageable is False
    assert c.okh_ref is None
    assert c.product_url is None
    assert c.notes is None


# ---------------------------------------------------------------------------
# OKHManifest.to_dict — components round-trips
# ---------------------------------------------------------------------------


def test_to_dict_includes_components():
    from src.core.models.okh import OKHManifest

    data = {**_MINIMAL, "components": [{"name": "Wheel", "quantity": 4}]}
    m = OKHManifest.from_dict(data)
    d = m.to_dict()
    assert "components" in d
    assert len(d["components"]) == 1
    assert d["components"][0]["name"] == "Wheel"
    assert d["components"][0]["quantity"] == 4


def test_to_dict_empty_components_excluded():
    from src.core.models.okh import OKHManifest

    m = OKHManifest.from_dict(_MINIMAL)
    d = m.to_dict()
    components = d.get("components", [])
    assert components == []


# ---------------------------------------------------------------------------
# model_validator — component_count in details
# ---------------------------------------------------------------------------


def test_validate_includes_component_count_zero():
    from src.core.validation.model_validator import validate_okh_manifest

    result = validate_okh_manifest(_MINIMAL)
    assert "component_count" in result.details
    assert result.details["component_count"] == 0


def test_validate_includes_component_count_nonzero():
    from src.core.validation.model_validator import validate_okh_manifest

    data = {
        **_MINIMAL,
        "components": [
            {"name": "Motor"},
            {"name": "Wheel"},
        ],
    }
    result = validate_okh_manifest(data)
    assert result.details["component_count"] == 2


def test_validate_field_presence_tracks_components():
    from src.core.validation.model_validator import validate_okh_manifest

    result_without = validate_okh_manifest(_MINIMAL)
    result_with = validate_okh_manifest({**_MINIMAL, "components": [{"name": "Motor"}]})
    assert result_without.details["field_presence"]["components"] is False
    assert result_with.details["field_presence"]["components"] is True
