"""Integration tests for the repair triage report endpoint.

Run against a live OHM API:
    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_repair_triage.py -v
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

_MANIFEST_PAYLOAD = {
    "title": "Triage Report Test Device",
    "version": "1.0.0",
    "license": {"hardware": "CERN-OHL-S-2.0"},
    "licensor": "Test Suite",
    "documentation_language": "en",
    "function": "Device used for repair triage report integration tests",
    "components": [
        {"name": "Blood pump", "replaceable": True, "salvageable": True},
        {
            "name": "Filter cartridge",
            "replaceable": True,
            "salvageable": False,
            "consumable": True,
        },
        {"name": "Flow sensor", "replaceable": False, "salvageable": False},
        {"name": "Display panel", "replaceable": True, "salvageable": False},
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


@pytest.fixture()
def asset(client, manifest_id):
    r = client.post(
        "/api/asset/",
        json={"manifest_id": manifest_id, "asset_tag": "SN-TRIAGE-01"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    yield data
    client.delete(f"/api/asset/{data['id']}")


class TestTriageReportUntriaged:
    def test_report_before_triage_all_assess(self, client, asset):
        r = client.get(f"/api/asset/{asset['id']}/triage-report")
        assert r.status_code == 200
        data = r.json()
        assert data["asset_id"] == asset["id"]
        assert data["asset_tag"] == asset["asset_tag"]
        assert data["summary"]["total_components"] == 4
        assert data["summary"]["needs_assessment"] == 4
        assert all(i["recommended_action"] == "assess" for i in data["items"])

    def test_report_shape(self, client, asset):
        r = client.get(f"/api/asset/{asset['id']}/triage-report")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "summary" in data
        summary = data["summary"]
        for key in (
            "total_components",
            "needs_assessment",
            "repair_in_place",
            "harvest",
            "source_new",
            "no_action",
            "decommission",
        ):
            assert key in summary

    def test_report_nonexistent_asset_returns_404(self, client):
        r = client.get(f"/api/asset/{uuid.uuid4()}/triage-report")
        assert r.status_code == 404


class TestTriageReportActions:
    def test_intact_component_no_action(self, client, asset):
        client.post(
            f"/api/asset/{asset['id']}/triage",
            json={
                "component_states": [
                    {"component_name": "Blood pump", "condition": "intact"}
                ]
            },
        )
        r = client.get(f"/api/asset/{asset['id']}/triage-report")
        items = {i["component_name"]: i for i in r.json()["items"]}
        assert items["Blood pump"]["recommended_action"] == "no_action"

    def test_damaged_repair_feasible_repair_in_place(self, client, asset):
        client.post(
            f"/api/asset/{asset['id']}/triage",
            json={
                "component_states": [
                    {
                        "component_name": "Display panel",
                        "condition": "damaged",
                        "repair_feasible": True,
                    }
                ]
            },
        )
        r = client.get(f"/api/asset/{asset['id']}/triage-report")
        items = {i["component_name"]: i for i in r.json()["items"]}
        assert items["Display panel"]["recommended_action"] == "repair_in_place"

    def test_damaged_salvageable_harvest(self, client, asset):
        client.post(
            f"/api/asset/{asset['id']}/triage",
            json={
                "component_states": [
                    {
                        "component_name": "Blood pump",
                        "condition": "damaged",
                        "repair_feasible": False,
                        "harvest_viable": True,
                    }
                ]
            },
        )
        r = client.get(f"/api/asset/{asset['id']}/triage-report")
        items = {i["component_name"]: i for i in r.json()["items"]}
        assert items["Blood pump"]["recommended_action"] == "harvest"
        # manifest flags carried through
        assert items["Blood pump"]["salvageable"] is True

    def test_missing_replaceable_source_new(self, client, asset):
        client.post(
            f"/api/asset/{asset['id']}/triage",
            json={
                "component_states": [
                    {"component_name": "Filter cartridge", "condition": "missing"}
                ]
            },
        )
        r = client.get(f"/api/asset/{asset['id']}/triage-report")
        items = {i["component_name"]: i for i in r.json()["items"]}
        assert items["Filter cartridge"]["recommended_action"] == "source_new"

    def test_missing_not_replaceable_decommission(self, client, asset):
        client.post(
            f"/api/asset/{asset['id']}/triage",
            json={
                "component_states": [
                    {"component_name": "Flow sensor", "condition": "missing"}
                ]
            },
        )
        r = client.get(f"/api/asset/{asset['id']}/triage-report")
        items = {i["component_name"]: i for i in r.json()["items"]}
        assert items["Flow sensor"]["recommended_action"] == "decommission"

    def test_summary_counts_after_full_triage(self, client, manifest_id):
        # Fresh asset with all four components triaged
        r = client.post(
            "/api/asset/",
            json={"manifest_id": manifest_id, "asset_tag": "SN-SUMMARY-01"},
        )
        assert r.status_code == 201
        asset_id = r.json()["id"]
        try:
            client.post(
                f"/api/asset/{asset_id}/triage",
                json={
                    "component_states": [
                        {"component_name": "Blood pump", "condition": "intact"},
                        {
                            "component_name": "Filter cartridge",
                            "condition": "missing",
                        },
                        {
                            "component_name": "Flow sensor",
                            "condition": "damaged",
                            "repair_feasible": True,
                        },
                        {
                            "component_name": "Display panel",
                            "condition": "damaged",
                            "repair_feasible": False,
                        },
                    ]
                },
            )
            r = client.get(f"/api/asset/{asset_id}/triage-report")
            assert r.status_code == 200
            s = r.json()["summary"]
            assert s["total_components"] == 4
            assert s["no_action"] == 1
            assert s["source_new"] == 1
            assert s["repair_in_place"] == 1
            # Display panel: damaged, repair_feasible=False, replaceable=True → source_new
            assert s["source_new"] >= 1
            assert s["needs_assessment"] == 0
        finally:
            client.delete(f"/api/asset/{asset_id}")
