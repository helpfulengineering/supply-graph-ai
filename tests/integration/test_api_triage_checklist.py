"""Integration tests for GET /api/asset/{id}/triage-checklist — GAP-2.

Run against a live OHM API:
    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_triage_checklist.py -v
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
    "title": "Checklist Test Device",
    "version": "1.0.0",
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Suite",
    "documentation_language": "en",
    "function": "Device used for triage checklist integration tests",
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
def fresh_asset(client, manifest_id):
    """Asset with no triage recorded — all components pending."""
    r = client.post(
        "/api/asset/",
        json={"manifest_id": manifest_id, "asset_tag": "SN-CHKLIST-FRESH"},
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    yield aid
    client.delete(f"/api/asset/{aid}")


@pytest.fixture(scope="module")
def partial_asset(client, manifest_id):
    """Asset with one component triaged, two pending."""
    r = client.post(
        "/api/asset/",
        json={"manifest_id": manifest_id, "asset_tag": "SN-CHKLIST-PARTIAL"},
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    client.post(
        f"/api/asset/{aid}/triage",
        json={
            "component_states": [
                {
                    "component_name": "Blood pump module",
                    "condition": "damaged",
                    "notes": "Impeller cracked",
                    "assessed_by": "J. Smith",
                }
            ]
        },
    )
    yield aid
    client.delete(f"/api/asset/{aid}")


# ---------------------------------------------------------------------------
# TestChecklistShape
# ---------------------------------------------------------------------------


class TestChecklistShape:
    def test_response_has_required_fields(self, client, fresh_asset):
        r = client.get(f"/api/asset/{fresh_asset}/triage-checklist")
        assert r.status_code == 200
        data = r.json()
        for field in (
            "asset_id",
            "manifest_id",
            "asset_tag",
            "status",
            "items",
            "total_components",
            "assessed_count",
            "pending_count",
        ):
            assert field in data, f"Missing field: {field}"

    def test_item_has_required_fields(self, client, fresh_asset):
        r = client.get(f"/api/asset/{fresh_asset}/triage-checklist")
        assert r.status_code == 200
        item = r.json()["items"][0]
        for field in (
            "component_name",
            "assessed",
            "replaceable",
            "salvageable",
            "consumable",
            "current_condition",
            "current_state",
        ):
            assert field in item, f"Missing item field: {field}"

    def test_unknown_asset_returns_404(self, client):
        import uuid

        r = client.get(f"/api/asset/{uuid.uuid4()}/triage-checklist")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# TestFreshAsset — no triage recorded
# ---------------------------------------------------------------------------


class TestFreshAsset:
    def test_all_components_pending(self, client, fresh_asset):
        r = client.get(f"/api/asset/{fresh_asset}/triage-checklist")
        assert r.status_code == 200
        data = r.json()
        assert data["total_components"] == 3
        assert data["assessed_count"] == 0
        assert data["pending_count"] == 3

    def test_all_items_unassessed(self, client, fresh_asset):
        r = client.get(f"/api/asset/{fresh_asset}/triage-checklist")
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["assessed"] is False
            assert item["current_condition"] is None
            assert item["current_state"] is None

    def test_manifest_components_all_present(self, client, fresh_asset):
        r = client.get(f"/api/asset/{fresh_asset}/triage-checklist")
        assert r.status_code == 200
        names = {i["component_name"] for i in r.json()["items"]}
        assert names == {"Blood pump module", "Pre-filter cartridge", "Flow sensor"}

    def test_manifest_flags_surfaced(self, client, fresh_asset):
        r = client.get(f"/api/asset/{fresh_asset}/triage-checklist")
        assert r.status_code == 200
        items = {i["component_name"]: i for i in r.json()["items"]}
        pump = items["Blood pump module"]
        assert pump["replaceable"] is True
        assert pump["salvageable"] is True
        assert pump["part_number"] == "BLOODPUMP-01"
        filt = items["Pre-filter cartridge"]
        assert filt["consumable"] is True
        assert filt["salvageable"] is False

    def test_default_status_is_active(self, client, fresh_asset):
        r = client.get(f"/api/asset/{fresh_asset}/triage-checklist")
        assert r.status_code == 200
        assert r.json()["status"] == "active"


# ---------------------------------------------------------------------------
# TestPartialAsset — one component assessed
# ---------------------------------------------------------------------------


class TestPartialAsset:
    def test_one_assessed_two_pending(self, client, partial_asset):
        r = client.get(f"/api/asset/{partial_asset}/triage-checklist")
        assert r.status_code == 200
        data = r.json()
        assert data["assessed_count"] == 1
        assert data["pending_count"] == 2

    def test_assessed_item_has_current_state(self, client, partial_asset):
        r = client.get(f"/api/asset/{partial_asset}/triage-checklist")
        assert r.status_code == 200
        items = {i["component_name"]: i for i in r.json()["items"]}
        pump = items["Blood pump module"]
        assert pump["assessed"] is True
        assert pump["current_condition"] == "damaged"
        assert pump["current_state"] is not None
        assert pump["current_state"]["notes"] == "Impeller cracked"

    def test_unassessed_items_have_null_state(self, client, partial_asset):
        r = client.get(f"/api/asset/{partial_asset}/triage-checklist")
        assert r.status_code == 200
        items = {i["component_name"]: i for i in r.json()["items"]}
        for name in ("Pre-filter cartridge", "Flow sensor"):
            assert items[name]["assessed"] is False
            assert items[name]["current_condition"] is None

    def test_checklist_reflects_status_after_update(self, client, manifest_id):
        r = client.post(
            "/api/asset/",
            json={"manifest_id": manifest_id, "asset_tag": "SN-CHKLIST-STATUS"},
        )
        assert r.status_code == 201
        aid = r.json()["id"]
        try:
            client.put(f"/api/asset/{aid}", json={"status": "under_triage"})
            r = client.get(f"/api/asset/{aid}/triage-checklist")
            assert r.status_code == 200
            assert r.json()["status"] == "under_triage"
        finally:
            client.delete(f"/api/asset/{aid}")
