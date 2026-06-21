"""Integration smoke tests for the parts-harvesting endpoint.

Run against a live OHM API:
    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_harvest_parts.py -v
"""

from __future__ import annotations

import os

import httpx
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_API_TESTS", "0") != "1",
        reason="Set RUN_LIVE_API_TESTS=1 and a reachable OHM API at localhost:8001 to run",
    ),
]

BASE = "http://localhost:8001/v1"

# ---------------------------------------------------------------------------
# Fixtures — create manifests with known component compositions
# ---------------------------------------------------------------------------

_MANIFEST_WITH_PARTS = {
    "title": "Harvest Test Device",
    "version": "1.0.0",
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Suite",
    "documentation_language": "en",
    "function": "Device used for harvest-parts integration tests",
    "components": [
        {
            "name": "Blood pump module",
            "part_number": "BLOODPUMP-01",
            "replaceable": True,
            "salvageable": False,
            "consumable": False,
        },
        {
            "name": "Pre-filter cartridge",
            "part_number": "FILTER-04",
            "replaceable": True,
            "salvageable": True,
            "consumable": True,
        },
        {
            "name": "Flow sensor",
            "part_number": None,
            "replaceable": False,
            "salvageable": False,
            "consumable": False,
        },
    ],
}

_MANIFEST_NO_PARTS = {
    "title": "Empty Device",
    "version": "1.0.0",
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Suite",
    "documentation_language": "en",
    "function": "Device with no components for harvest tests",
    "components": [],
}


def _create_manifest(content: dict) -> str:
    r = httpx.post(f"{BASE}/api/okh/create", json={"content": content}, timeout=30)
    assert r.status_code == 201, r.text
    body = r.json()
    return body.get("manifest_id") or body.get("okh", {}).get("id")


def _harvest(manifest_ids: list[str], **filters) -> httpx.Response:
    return httpx.post(
        f"{BASE}/api/okh/harvest-parts",
        json={"manifest_ids": manifest_ids, **filters},
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Basic shape / success tests
# ---------------------------------------------------------------------------


class TestHarvestPartsBasic:
    @pytest.fixture(scope="class")
    def manifest_id(self):
        return _create_manifest(_MANIFEST_WITH_PARTS)

    def test_returns_200(self, manifest_id):
        r = _harvest([manifest_id])
        assert r.status_code == 200, r.text

    def test_response_shape(self, manifest_id):
        body = _harvest([manifest_id]).json()
        assert "components" in body
        assert "total" in body
        assert "replaceable_count" in body
        assert "consumable_count" in body
        assert "salvageable_count" in body
        assert "source_manifests" in body

    def test_components_annotated_with_source(self, manifest_id):
        body = _harvest([manifest_id]).json()
        for c in body["components"]:
            assert c["source_manifest_id"] == manifest_id
            assert "source_manifest_title" in c

    def test_total_matches_component_list(self, manifest_id):
        body = _harvest([manifest_id]).json()
        assert body["total"] == len(body["components"])

    def test_source_manifests_listed(self, manifest_id):
        body = _harvest([manifest_id]).json()
        assert manifest_id in body["source_manifests"]

    def test_empty_manifest_returns_zero(self):
        mid = _create_manifest(_MANIFEST_NO_PARTS)
        body = _harvest([mid]).json()
        assert body["total"] == 0
        assert body["components"] == []

    def test_invalid_manifest_id_returns_404(self):
        r = _harvest(["00000000-0000-0000-0000-000000000000"])
        assert r.status_code == 404

    def test_malformed_manifest_id_returns_400(self):
        r = _harvest(["not-a-uuid"])
        assert r.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


class TestHarvestPartsFiltering:
    @pytest.fixture(scope="class")
    def manifest_id(self):
        return _create_manifest(_MANIFEST_WITH_PARTS)

    def test_replaceable_only(self, manifest_id):
        body = _harvest([manifest_id], replaceable_only=True).json()
        assert all(c["replaceable"] for c in body["components"])
        # Blood pump + Pre-filter are replaceable; flow sensor is not
        assert body["total"] == 2

    def test_salvageable_only(self, manifest_id):
        body = _harvest([manifest_id], salvageable_only=True).json()
        assert all(c["salvageable"] for c in body["components"])
        assert body["total"] == 1  # only Pre-filter cartridge

    def test_consumable_only(self, manifest_id):
        body = _harvest([manifest_id], consumable_only=True).json()
        assert all(c["consumable"] for c in body["components"])
        assert body["total"] == 1

    def test_has_part_number(self, manifest_id):
        body = _harvest([manifest_id], has_part_number=True).json()
        assert all(c.get("part_number") for c in body["components"])
        # Blood pump + Pre-filter have part numbers; flow sensor does not
        assert body["total"] == 2

    def test_counts_reflect_full_component_set(self, manifest_id):
        body = _harvest([manifest_id]).json()
        # 2 replaceable (blood pump, pre-filter), 1 consumable, 1 salvageable
        assert body["replaceable_count"] == 2
        assert body["consumable_count"] == 1
        assert body["salvageable_count"] == 1

    def test_combined_filters_are_anded(self, manifest_id):
        # replaceable AND consumable → only Pre-filter
        body = _harvest(
            [manifest_id], replaceable_only=True, consumable_only=True
        ).json()
        assert body["total"] == 1
        assert body["components"][0]["name"] == "Pre-filter cartridge"


# ---------------------------------------------------------------------------
# Multi-manifest harvesting
# ---------------------------------------------------------------------------


class TestHarvestPartsMultiple:
    @pytest.fixture(scope="class")
    def two_manifest_ids(self):
        id1 = _create_manifest(_MANIFEST_WITH_PARTS)
        id2 = _create_manifest(
            {
                **_MANIFEST_WITH_PARTS,
                "title": "Second Harvest Device",
                "components": [
                    {
                        "name": "Control board",
                        "part_number": "CTL-001",
                        "replaceable": True,
                        "salvageable": False,
                        "consumable": False,
                    }
                ],
            }
        )
        return [id1, id2]

    def test_components_from_all_manifests_included(self, two_manifest_ids):
        body = _harvest(two_manifest_ids).json()
        source_ids = {c["source_manifest_id"] for c in body["components"]}
        assert source_ids == set(two_manifest_ids)

    def test_source_manifests_lists_all_ids(self, two_manifest_ids):
        body = _harvest(two_manifest_ids).json()
        assert set(body["source_manifests"]) == set(two_manifest_ids)

    def test_total_is_sum_of_individual_totals(self, two_manifest_ids):
        body_combined = _harvest(two_manifest_ids).json()
        body_1 = _harvest([two_manifest_ids[0]]).json()
        body_2 = _harvest([two_manifest_ids[1]]).json()
        assert body_combined["total"] == body_1["total"] + body_2["total"]
