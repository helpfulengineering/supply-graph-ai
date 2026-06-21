"""Integration tests for the salvage matching endpoint.

Run against a live OHM API:
    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_salvage_match.py -v
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

_MANIFEST_PAYLOAD = {
    "title": "Salvage Match Test Device",
    "version": "1.0.0",
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Suite",
    "documentation_language": "en",
    "function": "Device used for salvage matching integration tests",
    "components": [
        {
            "name": "Blood pump module",
            "part_number": "BLOODPUMP-01",
            "replaceable": True,
            "salvageable": True,
        },
        {
            "name": "Pre-filter cartridge",
            "part_number": "FILTER-04",
            "replaceable": True,
            "salvageable": False,
            "consumable": True,
        },
        {
            "name": "Flow sensor",
            "part_number": None,
            "replaceable": False,
            "salvageable": False,
        },
    ],
}


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        yield c


@pytest.fixture(scope="module")
def manifest_id(client):
    r = client.post("/api/okh/manifests/", json=_MANIFEST_PAYLOAD)
    assert r.status_code == 201, r.text
    mid = r.json()["id"]
    yield mid
    client.delete(f"/api/okh/manifests/{mid}")


@pytest.fixture(scope="module")
def triaged_asset(client, manifest_id):
    """Asset with known triage state for salvage queries."""
    r = client.post(
        "/api/asset/",
        json={
            "manifest_id": manifest_id,
            "asset_tag": "SN-SALVAGE-01",
            "location": "Ward 3B",
        },
    )
    assert r.status_code == 201, r.text
    asset_id = r.json()["id"]

    client.post(
        f"/api/asset/{asset_id}/triage",
        json={
            "component_states": [
                {
                    "component_name": "Blood pump module",
                    "condition": "damaged",
                    "repair_feasible": False,
                    "harvest_viable": True,
                    "notes": "Housing intact, impeller cracked",
                    "assessed_by": "J. Smith",
                },
                {
                    "component_name": "Pre-filter cartridge",
                    "condition": "intact",
                    "harvest_viable": True,
                },
                {
                    "component_name": "Flow sensor",
                    "condition": "missing",
                    "harvest_viable": False,
                },
            ]
        },
    )
    yield {"id": asset_id, "manifest_id": manifest_id}
    client.delete(f"/api/asset/{asset_id}")


# ---------------------------------------------------------------------------
# TestSalvageMatchBasic
# ---------------------------------------------------------------------------


class TestSalvageMatchBasic:
    def test_name_substring_match(self, client, triaged_asset):
        r = client.post("/api/asset/salvage-match", json={"component_name": "pump"})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        names = [m["component_name"] for m in data["matches"]]
        assert "Blood pump module" in names

    def test_name_case_insensitive(self, client, triaged_asset):
        r = client.post("/api/asset/salvage-match", json={"component_name": "BLOOD"})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert any("Blood" in m["component_name"] for m in data["matches"])

    def test_part_number_exact_match(self, client, triaged_asset):
        r = client.post(
            "/api/asset/salvage-match", json={"part_number": "BLOODPUMP-01"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert all(m["part_number"] == "BLOODPUMP-01" for m in data["matches"])

    def test_part_number_wrong_returns_empty(self, client, triaged_asset):
        r = client.post(
            "/api/asset/salvage-match", json={"part_number": "NONEXISTENT-99"}
        )
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_non_harvest_viable_excluded(self, client, triaged_asset):
        # Flow sensor is missing and harvest_viable=False — must not appear
        r = client.post(
            "/api/asset/salvage-match", json={"component_name": "Flow sensor"}
        )
        assert r.status_code == 200
        names = [m["component_name"] for m in r.json()["matches"]]
        assert "Flow sensor" not in names

    def test_response_shape(self, client, triaged_asset):
        r = client.post("/api/asset/salvage-match", json={"component_name": "pump"})
        assert r.status_code == 200
        data = r.json()
        assert "matches" in data
        assert "total" in data
        assert "query" in data
        assert data["query"]["component_name"] == "pump"
        match = data["matches"][0]
        for field in (
            "asset_id",
            "asset_tag",
            "manifest_id",
            "component_name",
            "condition",
        ):
            assert field in match

    def test_match_includes_manifest_flags(self, client, triaged_asset):
        r = client.post(
            "/api/asset/salvage-match", json={"component_name": "Blood pump"}
        )
        assert r.status_code == 200
        match = r.json()["matches"][0]
        assert match["salvageable"] is True
        assert match["part_number"] == "BLOODPUMP-01"

    def test_match_includes_asset_context(self, client, triaged_asset):
        r = client.post(
            "/api/asset/salvage-match", json={"component_name": "Blood pump"}
        )
        assert r.status_code == 200
        match = r.json()["matches"][0]
        assert match["location"] == "Ward 3B"
        assert match["assessed_by"] == "J. Smith"
        assert match["notes"] == "Housing intact, impeller cracked"

    def test_no_query_returns_422(self, client):
        r = client.post("/api/asset/salvage-match", json={})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# TestSalvageMatchFilters
# ---------------------------------------------------------------------------


class TestSalvageMatchFilters:
    def test_manifest_id_scope(self, client, triaged_asset):
        r = client.post(
            "/api/asset/salvage-match",
            json={
                "component_name": "pump",
                "manifest_id": triaged_asset["manifest_id"],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["query"]["manifest_id"] == triaged_asset["manifest_id"]
        assert all(
            m["manifest_id"] == triaged_asset["manifest_id"] for m in data["matches"]
        )

    def test_wrong_manifest_id_returns_empty(self, client, triaged_asset):
        import uuid

        r = client.post(
            "/api/asset/salvage-match",
            json={"component_name": "pump", "manifest_id": str(uuid.uuid4())},
        )
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_condition_filter_damaged_only(self, client, triaged_asset):
        r = client.post(
            "/api/asset/salvage-match",
            json={"component_name": "pump", "conditions": ["damaged"]},
        )
        assert r.status_code == 200
        assert all(m["condition"] == "damaged" for m in r.json()["matches"])

    def test_condition_filter_intact_only(self, client, triaged_asset):
        r = client.post(
            "/api/asset/salvage-match",
            json={"component_name": "filter", "conditions": ["intact"]},
        )
        assert r.status_code == 200
        data = r.json()
        assert all(m["condition"] == "intact" for m in data["matches"])

    def test_condition_filter_multiple(self, client, triaged_asset):
        r = client.post(
            "/api/asset/salvage-match",
            json={"component_name": "pump", "conditions": ["damaged", "intact"]},
        )
        assert r.status_code == 200
        conditions = {m["condition"] for m in r.json()["matches"]}
        assert conditions <= {"damaged", "intact"}

    def test_name_and_part_number_combined(self, client, triaged_asset):
        r = client.post(
            "/api/asset/salvage-match",
            json={"component_name": "pump", "part_number": "BLOODPUMP-01"},
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 1
