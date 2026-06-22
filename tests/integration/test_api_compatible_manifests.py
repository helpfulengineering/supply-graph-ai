"""Integration tests for compatible_manifest_ids cross-manifest salvage-match — GAP-8.

Run against a live OHM API:
    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_compatible_manifests.py -v
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
def primary_manifest(client):
    """Manifest that will declare a compatible manifest."""
    r = client.post(
        "/api/okh/manifests/",
        json={
            "title": "Compat Primary Device",
            "version": "1.0.0",
            "license": {"hardware": "CERN-OHL-S-2.0"},
            "licensor": "Test Suite",
            "documentation_language": "en",
            "function": "Primary device for GAP-8 tests",
            "components": [
                {"name": "Compat Pump", "part_number": "CP-X", "salvageable": True}
            ],
        },
    )
    assert r.status_code == 201, r.text
    mid = r.json()["id"]
    yield mid
    client.delete(f"/api/okh/manifests/{mid}")


@pytest.fixture()
def compat_manifest(client):
    """Manifest that is physically compatible with the primary."""
    r = client.post(
        "/api/okh/manifests/",
        json={
            "title": "Compat Secondary Device",
            "version": "1.0.0",
            "license": {"hardware": "CERN-OHL-S-2.0"},
            "licensor": "Test Suite",
            "documentation_language": "en",
            "function": "Secondary device for GAP-8 tests",
            "components": [
                {"name": "Compat Pump", "part_number": "CP-X", "salvageable": True}
            ],
        },
    )
    assert r.status_code == 201, r.text
    mid = r.json()["id"]
    yield mid
    client.delete(f"/api/okh/manifests/{mid}")


@pytest.fixture()
def asset_on_compat_manifest(client, compat_manifest):
    """Asset linked to the compatible manifest with a harvest-viable component."""
    r = client.post(
        "/api/asset/",
        json={
            "manifest_id": compat_manifest,
            "asset_tag": "COMPAT-ASSET-001",
            "location": "Bay 2",
        },
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]

    t = client.post(
        f"/api/asset/{aid}/triage",
        json={
            "component_states": [
                {
                    "component_name": "Compat Pump",
                    "condition": "intact",
                    "harvest_viable": True,
                }
            ]
        },
    )
    assert t.status_code == 200, t.text
    yield aid
    client.delete(f"/api/asset/{aid}")


def _link_compat(client, primary_id, compat_id):
    """Patch the primary manifest to declare the compat manifest as compatible."""
    r = client.get(f"/api/okh/{primary_id}")
    assert r.status_code == 200, r.text
    data = r.json()
    data["compatible_manifest_ids"] = [compat_id]
    return client.put(f"/api/okh/{primary_id}", json=data)


# ---------------------------------------------------------------------------
# Model-level: GET/PUT round-trip of compatible_manifest_ids
# ---------------------------------------------------------------------------


class TestCompatibleManifestIdsField:
    def test_manifest_returns_empty_compatible_ids_by_default(
        self, client, primary_manifest
    ):
        r = client.get(f"/api/okh/{primary_manifest}")
        assert r.status_code == 200, r.text
        assert r.json().get("compatible_manifest_ids", []) == []

    def test_put_sets_compatible_manifest_ids(
        self, client, primary_manifest, compat_manifest
    ):
        patch_r = _link_compat(client, primary_manifest, compat_manifest)
        assert patch_r.status_code == 200, patch_r.text

        r = client.get(f"/api/okh/{primary_manifest}")
        assert r.status_code == 200, r.text
        assert compat_manifest in r.json().get("compatible_manifest_ids", [])


# ---------------------------------------------------------------------------
# salvage-match expansion
# ---------------------------------------------------------------------------


class TestSalvageMatchExpansion:
    def test_compat_asset_absent_without_link(
        self, client, primary_manifest, asset_on_compat_manifest
    ):
        """Without compatible_manifest_ids, scoped search misses the compat asset."""
        r = client.post(
            "/api/asset/salvage-match",
            json={"component_name": "Compat Pump", "manifest_id": primary_manifest},
        )
        assert r.status_code == 200, r.text
        asset_ids = [m["asset_id"] for m in r.json()["matches"]]
        assert asset_on_compat_manifest not in asset_ids

    def test_compat_asset_present_after_link(
        self, client, primary_manifest, compat_manifest, asset_on_compat_manifest
    ):
        """After linking, scoped search includes assets from the compatible manifest."""
        _link_compat(client, primary_manifest, compat_manifest)

        r = client.post(
            "/api/asset/salvage-match",
            json={"component_name": "Compat Pump", "manifest_id": primary_manifest},
        )
        assert r.status_code == 200, r.text
        asset_ids = [m["asset_id"] for m in r.json()["matches"]]
        assert asset_on_compat_manifest in asset_ids

    def test_unscoped_search_always_finds_all(self, client, asset_on_compat_manifest):
        """Part-number search without manifest_id crosses all manifests."""
        r = client.post(
            "/api/asset/salvage-match",
            json={"part_number": "CP-X"},
        )
        assert r.status_code == 200, r.text
        asset_ids = [m["asset_id"] for m in r.json()["matches"]]
        assert asset_on_compat_manifest in asset_ids
