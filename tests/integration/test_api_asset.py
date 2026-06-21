"""Integration tests for the AssetRecord API endpoints.

Run against a live OHM API:
    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_asset.py -v
"""

from __future__ import annotations

import os
import uuid

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
# Fixtures
# ---------------------------------------------------------------------------

_MANIFEST_PAYLOAD = {
    "title": "Asset Integration Test Device",
    "version": "1.0.0",
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Suite",
    "documentation_language": "en",
    "function": "Device used for AssetRecord integration tests",
    "components": [
        {"name": "Blood pump", "replaceable": True, "salvageable": True},
        {
            "name": "Filter cartridge",
            "replaceable": True,
            "salvageable": False,
            "consumable": True,
        },
        {"name": "Flow sensor", "replaceable": False},
    ],
}


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        yield c


@pytest.fixture(scope="module")
def manifest_id(client):
    """Create a test OKH manifest and return its ID. Deleted after the module."""
    r = client.post("/api/okh/manifests/", json=_MANIFEST_PAYLOAD)
    assert r.status_code == 201, r.text
    mid = r.json()["id"]
    yield mid
    client.delete(f"/api/okh/manifests/{mid}")


@pytest.fixture()
def asset(client, manifest_id):
    """Create one asset and delete it after the test."""
    r = client.post(
        "/api/asset/",
        json={
            "manifest_id": manifest_id,
            "asset_tag": "SN-TEST-001",
            "location": "Ward 1",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    yield data
    client.delete(f"/api/asset/{data['id']}")


# ---------------------------------------------------------------------------
# TestAssetCRUD
# ---------------------------------------------------------------------------


class TestAssetCRUD:
    def test_create_returns_201(self, client, manifest_id):
        r = client.post(
            "/api/asset/",
            json={"manifest_id": manifest_id, "asset_tag": "SN-CRUD-01"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["manifest_id"] == manifest_id
        assert data["asset_tag"] == "SN-CRUD-01"
        assert "id" in data
        client.delete(f"/api/asset/{data['id']}")

    def test_create_with_location(self, client, manifest_id):
        r = client.post(
            "/api/asset/",
            json={
                "manifest_id": manifest_id,
                "asset_tag": "SN-LOC-01",
                "location": "ICU Bay 3",
            },
        )
        assert r.status_code == 201
        assert r.json()["location"] == "ICU Bay 3"
        client.delete(f"/api/asset/{r.json()['id']}")

    def test_get_by_id(self, client, asset):
        r = client.get(f"/api/asset/{asset['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == asset["id"]
        assert r.json()["asset_tag"] == asset["asset_tag"]

    def test_get_nonexistent_returns_404(self, client):
        r = client.get(f"/api/asset/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_update_location(self, client, asset):
        r = client.put(f"/api/asset/{asset['id']}", json={"location": "Ward 4B"})
        assert r.status_code == 200
        assert r.json()["location"] == "Ward 4B"

    def test_update_triage_notes(self, client, asset):
        r = client.put(
            f"/api/asset/{asset['id']}", json={"triage_notes": "Cleared for reuse"}
        )
        assert r.status_code == 200
        assert r.json()["triage_notes"] == "Cleared for reuse"

    def test_delete(self, client, manifest_id):
        r = client.post(
            "/api/asset/",
            json={"manifest_id": manifest_id, "asset_tag": "SN-DEL-01"},
        )
        assert r.status_code == 201
        asset_id = r.json()["id"]

        del_r = client.delete(f"/api/asset/{asset_id}")
        assert del_r.status_code == 200

        get_r = client.get(f"/api/asset/{asset_id}")
        assert get_r.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        r = client.delete(f"/api/asset/{uuid.uuid4()}")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# TestAssetListFiltering
# ---------------------------------------------------------------------------


class TestAssetListFiltering:
    def test_list_all(self, client, asset):
        r = client.get("/api/asset/")
        assert r.status_code == 200
        data = r.json()
        assert "assets" in data
        assert "total" in data
        ids = [a["id"] for a in data["assets"]]
        assert asset["id"] in ids

    def test_list_by_manifest_id(self, client, manifest_id, asset):
        r = client.get("/api/asset/", params={"manifest_id": manifest_id})
        assert r.status_code == 200
        data = r.json()
        assert all(a["manifest_id"] == manifest_id for a in data["assets"])
        ids = [a["id"] for a in data["assets"]]
        assert asset["id"] in ids

    def test_list_by_wrong_manifest_id_returns_empty(self, client):
        r = client.get("/api/asset/", params={"manifest_id": str(uuid.uuid4())})
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_list_harvest_viable_empty_before_triage(self, client, asset):
        r = client.get("/api/asset/", params={"harvest_viable": "true"})
        assert r.status_code == 200
        ids = [a["id"] for a in r.json()["assets"]]
        # asset has no component states yet — must not appear
        assert asset["id"] not in ids


# ---------------------------------------------------------------------------
# TestTriageRecording
# ---------------------------------------------------------------------------


class TestTriageRecording:
    def test_triage_single_component(self, client, asset):
        payload = {
            "component_states": [
                {
                    "component_name": "Blood pump",
                    "condition": "damaged",
                    "repair_feasible": False,
                    "harvest_viable": True,
                }
            ]
        }
        r = client.post(f"/api/asset/{asset['id']}/triage", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["last_triaged_at"] is not None
        states = {cs["component_name"]: cs for cs in data["component_states"]}
        assert "Blood pump" in states
        assert states["Blood pump"]["condition"] == "damaged"
        assert states["Blood pump"]["harvest_viable"] is True

    def test_triage_multiple_components(self, client, asset):
        payload = {
            "component_states": [
                {
                    "component_name": "Blood pump",
                    "condition": "intact",
                    "harvest_viable": False,
                },
                {
                    "component_name": "Filter cartridge",
                    "condition": "missing",
                    "source_required": True,
                },
            ],
            "triage_notes": "Initial triage pass",
        }
        r = client.post(f"/api/asset/{asset['id']}/triage", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["triage_notes"] == "Initial triage pass"
        names = [cs["component_name"] for cs in data["component_states"]]
        assert "Blood pump" in names
        assert "Filter cartridge" in names

    def test_triage_upserts_by_name(self, client, asset):
        # First triage
        r1 = client.post(
            f"/api/asset/{asset['id']}/triage",
            json={
                "component_states": [
                    {"component_name": "Flow sensor", "condition": "intact"}
                ]
            },
        )
        assert r1.status_code == 200

        # Second triage — same component name, different condition
        r2 = client.post(
            f"/api/asset/{asset['id']}/triage",
            json={
                "component_states": [
                    {"component_name": "Flow sensor", "condition": "damaged"}
                ]
            },
        )
        assert r2.status_code == 200
        states = {cs["component_name"]: cs for cs in r2.json()["component_states"]}
        assert states["Flow sensor"]["condition"] == "damaged"
        # Only one entry for "Flow sensor"
        flow_entries = [
            cs
            for cs in r2.json()["component_states"]
            if cs["component_name"] == "Flow sensor"
        ]
        assert len(flow_entries) == 1

    def test_triage_nonexistent_asset_returns_404(self, client):
        r = client.post(
            f"/api/asset/{uuid.uuid4()}/triage",
            json={"component_states": [{"component_name": "X", "condition": "intact"}]},
        )
        assert r.status_code == 404

    def test_triage_invalid_condition_returns_422(self, client, asset):
        r = client.post(
            f"/api/asset/{asset['id']}/triage",
            json={
                "component_states": [{"component_name": "Y", "condition": "destroyed"}]
            },
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# TestHarvestableFilter
# ---------------------------------------------------------------------------


class TestHarvestableFilter:
    def test_harvest_viable_filter(self, client, manifest_id):
        # Create asset
        r = client.post(
            "/api/asset/",
            json={"manifest_id": manifest_id, "asset_tag": "SN-HARVEST-01"},
        )
        assert r.status_code == 201
        asset_id = r.json()["id"]

        try:
            # Triage with one harvestable and one non-harvestable component
            client.post(
                f"/api/asset/{asset_id}/triage",
                json={
                    "component_states": [
                        {
                            "component_name": "Blood pump",
                            "condition": "damaged",
                            "harvest_viable": True,
                        },
                        {
                            "component_name": "Filter cartridge",
                            "condition": "missing",
                            "harvest_viable": False,
                        },
                    ]
                },
            )

            r = client.get("/api/asset/", params={"harvest_viable": "true"})
            assert r.status_code == 200
            data = r.json()
            matching = [a for a in data["assets"] if a["id"] == asset_id]
            assert len(matching) == 1

            # Only harvest_viable=True components returned
            component_names = [
                cs["component_name"] for cs in matching[0]["component_states"]
            ]
            assert "Blood pump" in component_names
            assert "Filter cartridge" not in component_names
        finally:
            client.delete(f"/api/asset/{asset_id}")

    def test_harvest_viable_excludes_assets_with_none(self, client, manifest_id):
        # Create asset and triage it with no harvest-viable components
        r = client.post(
            "/api/asset/",
            json={"manifest_id": manifest_id, "asset_tag": "SN-HARVEST-NONE"},
        )
        assert r.status_code == 201
        asset_id = r.json()["id"]

        try:
            client.post(
                f"/api/asset/{asset_id}/triage",
                json={
                    "component_states": [
                        {
                            "component_name": "Blood pump",
                            "condition": "intact",
                            "harvest_viable": False,
                        },
                    ]
                },
            )

            r = client.get("/api/asset/", params={"harvest_viable": "true"})
            assert r.status_code == 200
            ids = [a["id"] for a in r.json()["assets"]]
            assert asset_id not in ids
        finally:
            client.delete(f"/api/asset/{asset_id}")
