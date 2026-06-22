"""Integration tests for harvest-parts fleet enrichment — GAP-6.

Run against a live OHM API:
    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_harvest_enrich.py -v
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
def manifest_with_salvageable_component(client):
    """Manifest with one salvageable component for harvesting."""
    r = client.post(
        "/api/okh/manifests/",
        json={
            "title": "Harvest Enrich Test Device",
            "version": "1.0.0",
            "license": {"hardware": "CERN-OHL-S-2.0"},
            "licensor": "Test Suite",
            "documentation_language": "en",
            "function": "Device for harvest-enrich integration tests",
            "components": [
                {
                    "name": "Test Pump Module",
                    "part_number": "TPM-01",
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


# ---------------------------------------------------------------------------
# Without enrich_fleet (baseline)
# ---------------------------------------------------------------------------


class TestHarvestWithoutEnrichment:
    def test_baseline_response_shape(self, client, manifest_with_salvageable_component):
        r = client.post(
            "/api/okh/harvest-parts",
            json={"manifest_ids": [manifest_with_salvageable_component]},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "components" in data
        assert "total" in data

    def test_no_fleet_fields_without_flag(
        self, client, manifest_with_salvageable_component
    ):
        r = client.post(
            "/api/okh/harvest-parts",
            json={
                "manifest_ids": [manifest_with_salvageable_component],
                "enrich_fleet": False,
            },
        )
        assert r.status_code == 200, r.text
        for c in r.json()["components"]:
            assert "fleet_available_count" not in c
            assert "fleet_asset_ids" not in c


# ---------------------------------------------------------------------------
# With enrich_fleet=True
# ---------------------------------------------------------------------------


class TestHarvestWithEnrichment:
    def test_enrich_fleet_returns_fleet_fields(
        self, client, manifest_with_salvageable_component
    ):
        r = client.post(
            "/api/okh/harvest-parts",
            json={
                "manifest_ids": [manifest_with_salvageable_component],
                "enrich_fleet": True,
            },
        )
        assert r.status_code == 200, r.text
        for c in r.json()["components"]:
            assert (
                "fleet_available_count" in c
            ), f"Missing fleet_available_count on {c['name']}"
            assert "fleet_asset_ids" in c, f"Missing fleet_asset_ids on {c['name']}"

    def test_fleet_available_count_is_integer(
        self, client, manifest_with_salvageable_component
    ):
        r = client.post(
            "/api/okh/harvest-parts",
            json={
                "manifest_ids": [manifest_with_salvageable_component],
                "enrich_fleet": True,
            },
        )
        assert r.status_code == 200, r.text
        for c in r.json()["components"]:
            assert isinstance(c["fleet_available_count"], int)
            assert isinstance(c["fleet_asset_ids"], list)

    def test_enrich_fleet_combines_with_filter(
        self, client, manifest_with_salvageable_component
    ):
        """enrich_fleet works together with replaceable_only filter."""
        r = client.post(
            "/api/okh/harvest-parts",
            json={
                "manifest_ids": [manifest_with_salvageable_component],
                "replaceable_only": True,
                "enrich_fleet": True,
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        # All returned components must be replaceable and have fleet fields
        for c in data["components"]:
            assert c.get("replaceable") is True
            assert "fleet_available_count" in c

    def test_unknown_manifest_still_404(self, client):
        r = client.post(
            "/api/okh/harvest-parts",
            json={
                "manifest_ids": [str(uuid.uuid4())],
                "enrich_fleet": True,
            },
        )
        assert r.status_code == 404
