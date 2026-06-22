"""Integration tests for AssetStatus lifecycle field — GAP-3.

Run against a live OHM API:
    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_asset_status.py -v
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
    "title": "Status Test Device",
    "version": "1.0.0",
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Suite",
    "documentation_language": "en",
    "function": "Device used for AssetStatus integration tests",
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


@pytest.fixture()
def asset(client, manifest_id):
    r = client.post(
        "/api/asset/",
        json={"manifest_id": manifest_id, "asset_tag": "SN-STATUS-01"},
    )
    assert r.status_code == 201, r.text
    asset_id = r.json()["id"]
    yield r.json()
    client.delete(f"/api/asset/{asset_id}")


# ---------------------------------------------------------------------------
# TestAssetStatusCreate
# ---------------------------------------------------------------------------


class TestAssetStatusCreate:
    def test_new_asset_has_active_status(self, client, asset):
        assert asset["status"] == "active"

    def test_get_includes_status(self, client, asset):
        r = client.get(f"/api/asset/{asset['id']}")
        assert r.status_code == 200
        assert r.json()["status"] == "active"


# ---------------------------------------------------------------------------
# TestAssetStatusUpdate
# ---------------------------------------------------------------------------


class TestAssetStatusUpdate:
    def test_update_status_to_under_triage(self, client, asset):
        r = client.put(
            f"/api/asset/{asset['id']}",
            json={"status": "under_triage"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "under_triage"

    def test_status_persists_after_update(self, client, asset):
        client.put(f"/api/asset/{asset['id']}", json={"status": "under_repair"})
        r = client.get(f"/api/asset/{asset['id']}")
        assert r.status_code == 200
        assert r.json()["status"] == "under_repair"

    def test_update_all_valid_statuses(self, client, asset):
        statuses = [
            "active",
            "under_triage",
            "parts_pending",
            "under_repair",
            "restored",
            "condemned",
        ]
        for s in statuses:
            r = client.put(f"/api/asset/{asset['id']}", json={"status": s})
            assert r.status_code == 200, f"Failed to set status={s}: {r.text}"
            assert r.json()["status"] == s

    def test_invalid_status_returns_422(self, client, asset):
        r = client.put(f"/api/asset/{asset['id']}", json={"status": "not_a_status"})
        assert r.status_code == 422

    def test_other_fields_unaffected_by_status_update(self, client, manifest_id):
        r = client.post(
            "/api/asset/",
            json={
                "manifest_id": manifest_id,
                "asset_tag": "SN-STATUS-PRESERVE",
                "location": "Ward 7",
            },
        )
        assert r.status_code == 201
        asset_id = r.json()["id"]
        try:
            client.put(f"/api/asset/{asset_id}", json={"status": "condemned"})
            r = client.get(f"/api/asset/{asset_id}")
            data = r.json()
            assert data["location"] == "Ward 7"
            assert data["asset_tag"] == "SN-STATUS-PRESERVE"
            assert data["status"] == "condemned"
        finally:
            client.delete(f"/api/asset/{asset_id}")


# ---------------------------------------------------------------------------
# TestAssetStatusFilter
# ---------------------------------------------------------------------------


class TestAssetStatusFilter:
    @pytest.fixture(scope="class")
    def seeded_assets(self, client, manifest_id):
        """Three assets with distinct statuses."""
        created = []
        for tag, status in [
            ("SN-FILTER-ACTIVE", "active"),
            ("SN-FILTER-TRIAGE", "under_triage"),
            ("SN-FILTER-CONDEMNED", "condemned"),
        ]:
            r = client.post(
                "/api/asset/",
                json={"manifest_id": manifest_id, "asset_tag": tag},
            )
            assert r.status_code == 201
            aid = r.json()["id"]
            if status != "active":
                client.put(f"/api/asset/{aid}", json={"status": status})
            created.append(aid)
        yield created
        for aid in created:
            client.delete(f"/api/asset/{aid}")

    def test_filter_active(self, client, seeded_assets):
        r = client.get("/api/asset/", params={"status": "active"})
        assert r.status_code == 200
        data = r.json()
        statuses = {a["status"] for a in data["assets"]}
        assert statuses == {"active"}

    def test_filter_under_triage(self, client, seeded_assets):
        r = client.get("/api/asset/", params={"status": "under_triage"})
        assert r.status_code == 200
        data = r.json()
        assert all(a["status"] == "under_triage" for a in data["assets"])
        tags = {a["asset_tag"] for a in data["assets"]}
        assert "SN-FILTER-TRIAGE" in tags

    def test_filter_condemned(self, client, seeded_assets):
        r = client.get("/api/asset/", params={"status": "condemned"})
        assert r.status_code == 200
        assert all(a["status"] == "condemned" for a in r.json()["assets"])

    def test_invalid_status_filter_returns_422(self, client, seeded_assets):
        r = client.get("/api/asset/", params={"status": "bogus"})
        assert r.status_code == 422

    def test_no_filter_returns_all_statuses(self, client, seeded_assets):
        r = client.get("/api/asset/")
        assert r.status_code == 200
        statuses = {a["status"] for a in r.json()["assets"]}
        assert len(statuses) > 1
