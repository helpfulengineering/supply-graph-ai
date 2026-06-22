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


# ---------------------------------------------------------------------------
# TestGap1FlagWriteback — verifies GAP-1 fix: harvest_viable auto-populated
# ---------------------------------------------------------------------------


class TestGap1FlagWriteback:
    """record_triage() now derives harvest_viable/source_required/repair_feasible
    from condition + manifest flags when the caller leaves them None.
    These tests verify the closed loop: triage with no flags → salvage-match finds it.
    """

    def test_salvageable_component_findable_without_explicit_harvest_viable(
        self, client, manifest_id
    ):
        """The critical GAP-1 scenario: technician records condition only,
        system fills harvest_viable=True from manifest salvageable flag."""
        r = client.post(
            "/api/asset/",
            json={"manifest_id": manifest_id, "asset_tag": "SN-GAP1-01"},
        )
        assert r.status_code == 201
        asset_id = r.json()["id"]

        try:
            # Triage with condition only — no harvest_viable supplied
            triage_r = client.post(
                f"/api/asset/{asset_id}/triage",
                json={
                    "component_states": [
                        {
                            "component_name": "Blood pump module",
                            "condition": "damaged",
                            "repair_feasible": False,
                            # harvest_viable intentionally omitted
                        }
                    ]
                },
            )
            assert triage_r.status_code == 200
            states = {
                cs["component_name"]: cs for cs in triage_r.json()["component_states"]
            }
            # System should have derived harvest_viable=True (manifest: salvageable=True)
            assert states["Blood pump module"]["harvest_viable"] is True
            assert states["Blood pump module"]["source_required"] is False

            # The component now appears in salvage-match without the caller having set the flag
            match_r = client.post(
                "/api/asset/salvage-match",
                json={"component_name": "Blood pump", "manifest_id": manifest_id},
            )
            assert match_r.status_code == 200
            assert match_r.json()["total"] >= 1
        finally:
            client.delete(f"/api/asset/{asset_id}")

    def test_replaceable_missing_component_gets_source_required(
        self, client, manifest_id
    ):
        r = client.post(
            "/api/asset/",
            json={"manifest_id": manifest_id, "asset_tag": "SN-GAP1-02"},
        )
        assert r.status_code == 201
        asset_id = r.json()["id"]

        try:
            triage_r = client.post(
                f"/api/asset/{asset_id}/triage",
                json={
                    "component_states": [
                        {
                            "component_name": "Pre-filter cartridge",
                            "condition": "missing",
                            # source_required intentionally omitted
                        }
                    ]
                },
            )
            assert triage_r.status_code == 200
            states = {
                cs["component_name"]: cs for cs in triage_r.json()["component_states"]
            }
            # manifest: replaceable=True → source_required derived True
            assert states["Pre-filter cartridge"]["source_required"] is True
            assert states["Pre-filter cartridge"]["harvest_viable"] is False
        finally:
            client.delete(f"/api/asset/{asset_id}")

    def test_explicit_caller_value_wins_over_derived(self, client, manifest_id):
        """Caller sets harvest_viable=False even though manifest says salvageable.
        The caller's judgment must be preserved."""
        r = client.post(
            "/api/asset/",
            json={"manifest_id": manifest_id, "asset_tag": "SN-GAP1-03"},
        )
        assert r.status_code == 201
        asset_id = r.json()["id"]

        try:
            triage_r = client.post(
                f"/api/asset/{asset_id}/triage",
                json={
                    "component_states": [
                        {
                            "component_name": "Blood pump module",
                            "condition": "damaged",
                            "repair_feasible": False,
                            "harvest_viable": False,  # explicit override
                        }
                    ]
                },
            )
            assert triage_r.status_code == 200
            states = {
                cs["component_name"]: cs for cs in triage_r.json()["component_states"]
            }
            # Caller said False; derived would say True — caller wins
            assert states["Blood pump module"]["harvest_viable"] is False

            # Should NOT appear in salvage-match
            match_r = client.post(
                "/api/asset/salvage-match",
                json={"component_name": "Blood pump", "manifest_id": manifest_id},
            )
            blood_pump_matches = [
                m for m in match_r.json()["matches"] if m["asset_id"] == asset_id
            ]
            assert blood_pump_matches == []
        finally:
            client.delete(f"/api/asset/{asset_id}")

    def test_intact_component_harvest_viable_not_set_by_default(
        self, client, manifest_id
    ):
        """NO_ACTION (intact) does not auto-set harvest_viable — that stays None
        so a decommission scenario can still mark it harvestable explicitly."""
        r = client.post(
            "/api/asset/",
            json={"manifest_id": manifest_id, "asset_tag": "SN-GAP1-04"},
        )
        assert r.status_code == 201
        asset_id = r.json()["id"]

        try:
            triage_r = client.post(
                f"/api/asset/{asset_id}/triage",
                json={
                    "component_states": [
                        {"component_name": "Flow sensor", "condition": "intact"}
                    ]
                },
            )
            assert triage_r.status_code == 200
            states = {
                cs["component_name"]: cs for cs in triage_r.json()["component_states"]
            }
            # harvest_viable should remain None (not forced False for intact components)
            assert states["Flow sensor"]["harvest_viable"] is None
            # source_required should be False (intact = nothing to replace)
            assert states["Flow sensor"]["source_required"] is False
        finally:
            client.delete(f"/api/asset/{asset_id}")
