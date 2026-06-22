"""Integration tests for POST /api/asset/{id}/claim-component and
exclude_claimed in salvage-match — GAP-7.

Run against a live OHM API:
    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_claim_component.py -v
"""

from __future__ import annotations

import os
import uuid

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_API_TESTS", "0") != "1",
        reason="Set RUN_LIVE_API_TESTS=1 to run integration tests",
    ),
]


@pytest.fixture()
def manifest_id(client):
    """Minimal manifest with a salvageable component."""
    r = client.post(
        "/api/okh/manifests/",
        json={
            "title": "Claim Test Device",
            "version": "1.0.0",
            "license": {"hardware": "CERN-OHL-S-2.0"},
            "licensor": "Test Suite",
            "documentation_language": "en",
            "function": "Device for claim-component integration tests",
            "components": [
                {
                    "name": "Claim Pump",
                    "part_number": "CP-01",
                    "replaceable": True,
                    "salvageable": True,
                }
            ],
        },
    )
    assert r.status_code == 201, r.text
    mid = r.json()["id"]
    yield mid
    client.delete(f"/api/okh/manifests/{mid}")


@pytest.fixture()
def asset_with_triage(client, manifest_id):
    """Asset with a harvest-viable component state for claim tests."""
    r = client.post(
        "/api/asset/",
        json={
            "manifest_id": manifest_id,
            "asset_tag": "CLAIM-TEST-001",
            "location": "Bay 1",
        },
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]

    # Record triage so the component is harvest_viable
    t = client.post(
        f"/api/asset/{aid}/triage",
        json={
            "component_states": [
                {
                    "component_name": "Claim Pump",
                    "condition": "intact",
                    "harvest_viable": True,
                }
            ]
        },
    )
    assert t.status_code == 200, t.text

    yield aid
    client.delete(f"/api/asset/{aid}")


# ---------------------------------------------------------------------------
# POST /{id}/claim-component
# ---------------------------------------------------------------------------


class TestClaimComponent:
    def test_claim_succeeds_on_unclaimed_component(self, client, asset_with_triage):
        r = client.post(
            f"/api/asset/{asset_with_triage}/claim-component",
            json={"component_name": "Claim Pump", "claimed_by": "coord-1"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] is True
        assert data["claimed_by"] == "coord-1"
        assert data["claimed_at"]

    def test_claim_returns_409_when_already_claimed(self, client, asset_with_triage):
        # First claim
        client.post(
            f"/api/asset/{asset_with_triage}/claim-component",
            json={"component_name": "Claim Pump", "claimed_by": "coord-1"},
        )
        # Second claim — must conflict
        r = client.post(
            f"/api/asset/{asset_with_triage}/claim-component",
            json={"component_name": "Claim Pump", "claimed_by": "coord-2"},
        )
        assert r.status_code == 409

    def test_claim_unknown_asset_returns_404(self, client):
        r = client.post(
            f"/api/asset/{uuid.uuid4()}/claim-component",
            json={"component_name": "Claim Pump", "claimed_by": "coord-1"},
        )
        assert r.status_code == 404

    def test_claim_unknown_component_returns_404(self, client, asset_with_triage):
        r = client.post(
            f"/api/asset/{asset_with_triage}/claim-component",
            json={"component_name": "Nonexistent Part", "claimed_by": "coord-1"},
        )
        assert r.status_code == 404

    def test_claim_response_shape(self, client, asset_with_triage):
        r = client.post(
            f"/api/asset/{asset_with_triage}/claim-component",
            json={"component_name": "Claim Pump", "claimed_by": "coord-shape"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        for field in (
            "success",
            "asset_id",
            "component_name",
            "claimed_by",
            "claimed_at",
        ):
            assert field in data, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# salvage-match exclude_claimed
# ---------------------------------------------------------------------------


class TestSalvageMatchExcludeClaimed:
    def test_claimed_component_excluded_by_default(
        self, client, asset_with_triage, manifest_id
    ):
        # Claim the component
        client.post(
            f"/api/asset/{asset_with_triage}/claim-component",
            json={"component_name": "Claim Pump", "claimed_by": "coord-excl"},
        )
        # Default salvage-match should not return claimed components
        r = client.post(
            "/api/asset/salvage-match",
            json={"component_name": "Claim Pump", "manifest_id": manifest_id},
        )
        assert r.status_code == 200, r.text
        asset_ids = [m["asset_id"] for m in r.json()["matches"]]
        assert asset_with_triage not in asset_ids

    def test_include_claimed_shows_claimed_components(
        self, client, asset_with_triage, manifest_id
    ):
        # Claim the component
        client.post(
            f"/api/asset/{asset_with_triage}/claim-component",
            json={"component_name": "Claim Pump", "claimed_by": "coord-incl"},
        )
        # exclude_claimed=False must return claimed components
        r = client.post(
            "/api/asset/salvage-match",
            json={
                "component_name": "Claim Pump",
                "manifest_id": manifest_id,
                "exclude_claimed": False,
            },
        )
        assert r.status_code == 200, r.text
        matches = {m["asset_id"]: m for m in r.json()["matches"]}
        assert asset_with_triage in matches
        assert matches[asset_with_triage]["claimed_by"] == "coord-incl"

    def test_exclude_claimed_true_explicit(
        self, client, asset_with_triage, manifest_id
    ):
        client.post(
            f"/api/asset/{asset_with_triage}/claim-component",
            json={"component_name": "Claim Pump", "claimed_by": "coord-expl"},
        )
        r = client.post(
            "/api/asset/salvage-match",
            json={
                "component_name": "Claim Pump",
                "manifest_id": manifest_id,
                "exclude_claimed": True,
            },
        )
        assert r.status_code == 200, r.text
        asset_ids = [m["asset_id"] for m in r.json()["matches"]]
        assert asset_with_triage not in asset_ids
