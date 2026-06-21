"""Integration smoke tests for repair data model fields.

Run against a live OHM API:
    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_repair.py -v
"""

from __future__ import annotations

import os

import pytest
import httpx

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_API_TESTS", "0") != "1",
        reason="Set RUN_LIVE_API_TESTS=1 and a reachable OHM API at localhost:8001 to run",
    ),
]

BASE = "http://localhost:8001/v1"

_MANIFEST_WITH_REPAIR = {
    "title": "Repair Integration Test Device",
    "version": "0.1.0",
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Suite",
    "documentation_language": "en",
    "function": "Smoke-tests repair data model fields in the OHM API",
    "components": [
        {
            "name": "Power switch",
            "quantity": 1,
            "replaceable": True,
            "salvageable": False,
            "consumable": False,
            "part_number": "SW-SPST-2A",
            "failure_modes": ["stuck closed", "contact oxidation"],
            "diagnostic_codes": ["ERR_PWR_SW"],
            "repair_notes": "Replace with equivalent SPST switch rated ≥2A.",
        },
        {
            "name": "Activated charcoal filter",
            "quantity": 1,
            "replaceable": True,
            "salvageable": False,
            "consumable": True,
            "part_number": "P/N 10036",
            "repair_notes": "Replace when filter life indicator reads 0%.",
        },
        {
            "name": "Display module",
            "quantity": 1,
            "replaceable": True,
            "salvageable": True,
        },
    ],
    "repair_guides": [
        {
            "title": "Power Switch Replacement",
            "path": "https://www.ifixit.com/Guide/example/12345",
            "source": "ifixit",
            "author": "Joe Shacar",
            "skill_level": "easy",
            "estimated_time_minutes": 10,
            "tools_required": ["Phillips #0 Screwdriver", "Flathead Screwdriver"],
            "safety_prerequisites": ["Unplug device from mains power before opening"],
            "applies_to_components": ["Power switch"],
            "applies_to_models": ["Model A", "Model B"],
        }
    ],
    "disassembly_guides": [
        {
            "title": "Device Disassembly",
            "path": "https://www.ifixit.com/Teardown/example/99999",
        }
    ],
}

_MANIFEST_MINIMAL = {
    "title": "Minimal Repair Test",
    "version": "0.1.0",
    "license": {"hardware": "MIT"},
    "licensor": "Test Suite",
    "documentation_language": "en",
    "function": "Minimal manifest for repair field absence tests",
}


def _post_json(endpoint: str, data: dict) -> httpx.Response:
    return httpx.post(f"{BASE}{endpoint}", json=data, timeout=30)


def _get(endpoint: str) -> httpx.Response:
    return httpx.get(f"{BASE}{endpoint}", timeout=30)


def _create_and_get_id(manifest: dict) -> str:
    r = _post_json("/api/okh/create", {"content": manifest})
    assert r.status_code == 201, r.text
    body = r.json()
    manifest_id = body.get("manifest_id") or body.get("okh", {}).get("id")
    assert manifest_id, f"No manifest_id in response: {body}"
    return manifest_id


# ---------------------------------------------------------------------------
# Validate endpoint — repair fields in metadata
# ---------------------------------------------------------------------------


class TestValidateRepairMetadata:
    def test_validate_returns_repair_guide_count(self):
        r = _post_json("/api/okh/validate", {"content": _MANIFEST_WITH_REPAIR})
        assert r.status_code == 200, r.text
        meta = r.json().get("metadata", {})
        assert "repair_guide_count" in meta, f"Missing repair_guide_count: {meta}"

    def test_validate_repair_guide_count_correct(self):
        r = _post_json("/api/okh/validate", {"content": _MANIFEST_WITH_REPAIR})
        assert r.json()["metadata"]["repair_guide_count"] == 1

    def test_validate_repair_guide_count_zero_for_minimal(self):
        r = _post_json("/api/okh/validate", {"content": _MANIFEST_MINIMAL})
        assert r.status_code == 200, r.text
        assert r.json().get("metadata", {}).get("repair_guide_count", 0) == 0

    def test_validate_consumable_count(self):
        r = _post_json("/api/okh/validate", {"content": _MANIFEST_WITH_REPAIR})
        assert r.status_code == 200, r.text
        assert r.json()["metadata"]["consumable_count"] == 1

    def test_validate_consumable_count_zero_for_minimal(self):
        r = _post_json("/api/okh/validate", {"content": _MANIFEST_MINIMAL})
        assert r.status_code == 200, r.text
        assert r.json().get("metadata", {}).get("consumable_count", 0) == 0


# ---------------------------------------------------------------------------
# Create + Get roundtrip — repair fields preserved
# ---------------------------------------------------------------------------


@pytest.fixture(scope="class")
def repair_manifest_id():
    return _create_and_get_id(_MANIFEST_WITH_REPAIR)


class TestRepairFieldRoundtrip:
    def test_repair_guides_roundtrip(self, repair_manifest_id):
        body = _get(f"/api/okh/{repair_manifest_id}").json()
        guides = body.get("repair_guides", [])
        assert len(guides) == 1
        guide = guides[0]
        assert guide["title"] == "Power Switch Replacement"
        assert guide["source"] == "ifixit"
        assert guide["author"] == "Joe Shacar"
        assert guide["skill_level"] == "easy"
        assert guide["estimated_time_minutes"] == 10
        assert "Phillips #0 Screwdriver" in guide["tools_required"]
        assert (
            "Unplug device from mains power before opening"
            in guide["safety_prerequisites"]
        )
        assert "Power switch" in guide["applies_to_components"]
        assert "Model A" in guide["applies_to_models"]
        assert "Model B" in guide["applies_to_models"]

    def test_disassembly_guides_roundtrip(self, repair_manifest_id):
        body = _get(f"/api/okh/{repair_manifest_id}").json()
        guides = body.get("disassembly_guides", [])
        assert len(guides) == 1
        assert guides[0]["title"] == "Device Disassembly"

    def test_component_repair_fields_roundtrip(self, repair_manifest_id):
        components = _get(f"/api/okh/{repair_manifest_id}").json().get("components", [])
        power_switch = next(
            (c for c in components if c["name"] == "Power switch"), None
        )
        assert power_switch is not None
        assert "stuck closed" in power_switch.get("failure_modes", [])
        assert power_switch.get("repair_notes") is not None

    def test_component_part_number_roundtrip(self, repair_manifest_id):
        components = _get(f"/api/okh/{repair_manifest_id}").json().get("components", [])
        power_switch = next(
            (c for c in components if c["name"] == "Power switch"), None
        )
        assert power_switch is not None
        assert power_switch.get("part_number") == "SW-SPST-2A"

    def test_component_consumable_roundtrip(self, repair_manifest_id):
        components = _get(f"/api/okh/{repair_manifest_id}").json().get("components", [])
        filt = next(
            (c for c in components if c["name"] == "Activated charcoal filter"), None
        )
        power_switch = next(
            (c for c in components if c["name"] == "Power switch"), None
        )
        assert filt is not None
        assert filt.get("consumable") is True
        assert filt.get("part_number") == "P/N 10036"
        assert power_switch is not None
        assert power_switch.get("consumable") is False

    def test_component_diagnostic_codes_roundtrip(self, repair_manifest_id):
        components = _get(f"/api/okh/{repair_manifest_id}").json().get("components", [])
        power_switch = next(
            (c for c in components if c["name"] == "Power switch"), None
        )
        assert power_switch is not None
        assert "ERR_PWR_SW" in power_switch.get("diagnostic_codes", [])

    def test_empty_repair_fields_absent_for_minimal(self):
        manifest_id = _create_and_get_id(_MANIFEST_MINIMAL)
        body = _get(f"/api/okh/{manifest_id}").json()
        assert body.get("repair_guides", []) == []
        assert body.get("disassembly_guides", []) == []
