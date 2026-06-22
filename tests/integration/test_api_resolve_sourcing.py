"""Integration tests for GET /api/asset/{id}/resolve-sourcing — GAP-5.

Run against a live OHM API:
    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_resolve_sourcing.py -v
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
    "title": "Sourcing Resolution Test Device",
    "version": "1.0.0",
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Suite",
    "documentation_language": "en",
    "function": "Device used for sourcing resolution integration tests",
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
        },
        {
            "name": "Flow sensor",
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
def donor_asset(client, manifest_id):
    """A second asset with a harvestable Blood pump — fleet source for the broken asset."""
    r = client.post(
        "/api/asset/",
        json={
            "manifest_id": manifest_id,
            "asset_tag": "SN-DONOR-01",
            "location": "Storage Bay 2",
        },
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    # Blood pump is intact and available for harvest
    client.post(
        f"/api/asset/{aid}/triage",
        json={
            "component_states": [
                {
                    "component_name": "Blood pump module",
                    "condition": "intact",
                    "harvest_viable": True,
                }
            ]
        },
    )
    yield aid
    client.delete(f"/api/asset/{aid}")


@pytest.fixture(scope="module")
def broken_asset(client, manifest_id, donor_asset):
    """Asset with missing Blood pump (source_new) and missing Flow sensor (decommission)."""
    r = client.post(
        "/api/asset/",
        json={"manifest_id": manifest_id, "asset_tag": "SN-BROKEN-01"},
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    client.post(
        f"/api/asset/{aid}/triage",
        json={
            "component_states": [
                {
                    "component_name": "Blood pump module",
                    "condition": "missing",
                    # replaceable=True → source_new, harvest_viable=False → derived
                },
                {
                    "component_name": "Pre-filter cartridge",
                    "condition": "missing",
                    # replaceable=True → source_new
                },
                {
                    "component_name": "Flow sensor",
                    "condition": "missing",
                    # replaceable=False → decommission, NOT source_new
                },
            ]
        },
    )
    yield aid
    client.delete(f"/api/asset/{aid}")


# ---------------------------------------------------------------------------
# TestResolutionShape
# ---------------------------------------------------------------------------


class TestResolutionShape:
    def test_response_has_required_fields(self, client, broken_asset):
        r = client.get(f"/api/asset/{broken_asset}/resolve-sourcing")
        assert r.status_code == 200
        data = r.json()
        for field in (
            "asset_id",
            "asset_tag",
            "manifest_id",
            "items",
            "total_components",
            "fleet_available_count",
            "procure_new_count",
        ):
            assert field in data, f"Missing field: {field}"

    def test_item_has_required_fields(self, client, broken_asset):
        r = client.get(f"/api/asset/{broken_asset}/resolve-sourcing")
        assert r.status_code == 200
        item = r.json()["items"][0]
        for field in ("component_name", "verdict", "matches", "match_count"):
            assert field in item, f"Missing item field: {field}"

    def test_unknown_asset_returns_404(self, client):
        import uuid

        r = client.get(f"/api/asset/{uuid.uuid4()}/resolve-sourcing")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# TestResolutionVerdicts
# ---------------------------------------------------------------------------


class TestResolutionVerdicts:
    def test_only_source_new_components_appear(self, client, broken_asset):
        """Flow sensor is decommission, not source_new — must not appear."""
        r = client.get(f"/api/asset/{broken_asset}/resolve-sourcing")
        assert r.status_code == 200
        names = {i["component_name"] for i in r.json()["items"]}
        assert "Flow sensor" not in names

    def test_blood_pump_fleet_available(self, client, broken_asset, donor_asset):
        """Donor asset has a harvestable Blood pump — should resolve fleet_available."""
        r = client.get(f"/api/asset/{broken_asset}/resolve-sourcing")
        assert r.status_code == 200
        items = {i["component_name"]: i for i in r.json()["items"]}
        pump = items.get("Blood pump module")
        assert pump is not None
        assert pump["verdict"] == "fleet_available"
        assert pump["match_count"] >= 1

    def test_filter_fleet_available_lists_donor_location(
        self, client, broken_asset, donor_asset
    ):
        r = client.get(f"/api/asset/{broken_asset}/resolve-sourcing")
        assert r.status_code == 200
        items = {i["component_name"]: i for i in r.json()["items"]}
        pump = items["Blood pump module"]
        locations = {m.get("location") for m in pump["matches"]}
        assert "Storage Bay 2" in locations

    def test_pre_filter_procure_new(self, client, broken_asset):
        """No donor has a harvestable Pre-filter cartridge — should be procure_new."""
        r = client.get(f"/api/asset/{broken_asset}/resolve-sourcing")
        assert r.status_code == 200
        items = {i["component_name"]: i for i in r.json()["items"]}
        filt = items.get("Pre-filter cartridge")
        assert filt is not None
        assert filt["verdict"] == "procure_new"
        assert filt["match_count"] == 0

    def test_asset_excluded_from_its_own_search(self, client, manifest_id):
        """An asset should never appear as a fleet source for its own missing components."""
        r = client.post(
            "/api/asset/",
            json={"manifest_id": manifest_id, "asset_tag": "SN-SELFTEST-01"},
        )
        assert r.status_code == 201
        aid = r.json()["id"]
        try:
            # Mark Blood pump as both missing AND harvest_viable (edge case)
            client.post(
                f"/api/asset/{aid}/triage",
                json={
                    "component_states": [
                        {
                            "component_name": "Blood pump module",
                            "condition": "missing",
                            "harvest_viable": True,
                        }
                    ]
                },
            )
            r = client.get(f"/api/asset/{aid}/resolve-sourcing")
            assert r.status_code == 200
            items = {i["component_name"]: i for i in r.json()["items"]}
            pump = items.get("Blood pump module")
            if pump:
                assert all(m["asset_id"] != aid for m in pump["matches"])
        finally:
            client.delete(f"/api/asset/{aid}")

    def test_counts_match_items(self, client, broken_asset):
        r = client.get(f"/api/asset/{broken_asset}/resolve-sourcing")
        assert r.status_code == 200
        data = r.json()
        fleet_n = sum(1 for i in data["items"] if i["verdict"] == "fleet_available")
        procure_n = sum(1 for i in data["items"] if i["verdict"] == "procure_new")
        assert data["fleet_available_count"] == fleet_n
        assert data["procure_new_count"] == procure_n
        assert data["total_components"] == len(data["items"])


# ---------------------------------------------------------------------------
# TestNoSourceNewComponents
# ---------------------------------------------------------------------------


class TestNoSourceNewComponents:
    def test_empty_resolution_for_intact_asset(self, client, manifest_id):
        """An asset with all intact components has nothing to resolve."""
        r = client.post(
            "/api/asset/",
            json={"manifest_id": manifest_id, "asset_tag": "SN-INTACT-01"},
        )
        assert r.status_code == 201
        aid = r.json()["id"]
        try:
            client.post(
                f"/api/asset/{aid}/triage",
                json={
                    "component_states": [
                        {"component_name": "Blood pump module", "condition": "intact"},
                        {
                            "component_name": "Pre-filter cartridge",
                            "condition": "intact",
                        },
                    ]
                },
            )
            r = client.get(f"/api/asset/{aid}/resolve-sourcing")
            assert r.status_code == 200
            data = r.json()
            assert data["total_components"] == 0
            assert data["items"] == []
        finally:
            client.delete(f"/api/asset/{aid}")
