"""Integration tests for POST /api/okh/import-repair-doc — GAP-4.

Run against a live OHM API:
    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_import_repair_doc.py -v
"""

from __future__ import annotations

import io
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

# Minimal plain-text repair document — no PDF reader needed, works with the
# programmatic extractor's text path.
_REPAIR_DOC = b"""
Service Manual - Blood Dialysis System

PARTS LIST

BP-01  Blood pump module
FILTER-04  Pre-filter cartridge
FLOWSNS  Flow sensor assembly

TOOLS REQUIRED
- Torque screwdriver
- Calibration kit

WARNING: Disconnect power before opening the device chassis.
"""


def _doc_files(content=_REPAIR_DOC, filename="manual.txt"):
    return [("files", (filename, io.BytesIO(content), "text/plain"))]


@pytest.fixture(scope="module")
def client():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        yield c


@pytest.fixture()
def pre_existing_manifest(client):
    """A manifest with one component already annotated."""
    r = client.post(
        "/api/okh/manifests/",
        json={
            "title": "Import Test Device",
            "version": "1.0.0",
            "license": {"hardware": "CERN-OHL-S-2.0"},
            "licensor": "Test Suite",
            "documentation_language": "en",
            "function": "Device for import-repair-doc integration tests",
            "components": [
                {
                    "name": "Blood pump module",
                    "part_number": "BP-01",
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
# TestCreateMode — no manifest_id, creates new manifest
# ---------------------------------------------------------------------------


class TestCreateMode:
    def test_creates_manifest_from_doc(self, client):
        r = client.post(
            "/api/okh/import-repair-doc",
            files=_doc_files(),
            data={"title": "Dialysis System From Import"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] is True
        assert data["manifest_id"]
        # Clean up
        client.delete(f"/api/okh/manifests/{data['manifest_id']}")

    def test_response_has_annotation_reminder(self, client):
        r = client.post(
            "/api/okh/import-repair-doc",
            files=_doc_files(),
            data={"title": "Reminder Test Device"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "replaceable=False" in data["annotation_reminder"]
        assert "salvageable=False" in data["annotation_reminder"]
        client.delete(f"/api/okh/manifests/{data['manifest_id']}")

    def test_new_components_have_conservative_defaults(self, client):
        r = client.post(
            "/api/okh/import-repair-doc",
            files=_doc_files(),
            data={"title": "Conservative Test Device"},
        )
        assert r.status_code == 200, r.text
        mid = r.json()["manifest_id"]
        try:
            manifest_r = client.get(f"/api/okh/manifests/{mid}")
            assert manifest_r.status_code == 200
            comps = {c["name"]: c for c in manifest_r.json().get("components", [])}
            for comp in comps.values():
                assert (
                    comp.get("replaceable") is False
                ), f"{comp['name']} should have replaceable=False after import"
                assert (
                    comp.get("salvageable") is False
                ), f"{comp['name']} should have salvageable=False after import"
        finally:
            client.delete(f"/api/okh/manifests/{mid}")

    def test_missing_title_returns_422(self, client):
        r = client.post(
            "/api/okh/import-repair-doc",
            files=_doc_files(),
            data={},
        )
        assert r.status_code == 422

    def test_response_shape(self, client):
        r = client.post(
            "/api/okh/import-repair-doc",
            files=_doc_files(),
            data={"title": "Shape Test"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        mid = data["manifest_id"]
        try:
            for field in (
                "success",
                "message",
                "manifest_id",
                "components_added",
                "components_updated",
                "guides_added",
                "source_files",
                "annotation_reminder",
            ):
                assert field in data, f"Missing field: {field}"
        finally:
            client.delete(f"/api/okh/manifests/{mid}")


# ---------------------------------------------------------------------------
# TestPatchMode — manifest_id provided, merges into existing
# ---------------------------------------------------------------------------


class TestPatchMode:
    def test_merges_into_existing_manifest(self, client, pre_existing_manifest):
        r = client.post(
            "/api/okh/import-repair-doc",
            files=_doc_files(),
            data={"manifest_id": pre_existing_manifest},
        )
        assert r.status_code == 200, r.text
        assert r.json()["manifest_id"] == pre_existing_manifest

    def test_existing_flags_preserved_after_merge(self, client, pre_existing_manifest):
        client.post(
            "/api/okh/import-repair-doc",
            files=_doc_files(),
            data={"manifest_id": pre_existing_manifest},
        )
        manifest_r = client.get(f"/api/okh/manifests/{pre_existing_manifest}")
        assert manifest_r.status_code == 200
        comps = {c["name"]: c for c in manifest_r.json().get("components", [])}
        pump = comps.get("Blood pump module")
        assert pump is not None, "Blood pump module must remain in manifest"
        # Was annotated as True before import — must be preserved
        assert pump["replaceable"] is True
        assert pump["salvageable"] is True

    def test_new_components_get_conservative_defaults(
        self, client, pre_existing_manifest
    ):
        client.post(
            "/api/okh/import-repair-doc",
            files=_doc_files(),
            data={"manifest_id": pre_existing_manifest},
        )
        manifest_r = client.get(f"/api/okh/manifests/{pre_existing_manifest}")
        assert manifest_r.status_code == 200
        comps = {c["name"]: c for c in manifest_r.json().get("components", [])}
        # These are new — must be conservative
        for name in ("Pre-filter cartridge", "Flow sensor assembly"):
            comp = comps.get(name)
            if comp:
                assert comp.get("replaceable") is False
                assert comp.get("salvageable") is False

    def test_unknown_manifest_returns_404(self, client):
        import uuid

        r = client.post(
            "/api/okh/import-repair-doc",
            files=_doc_files(),
            data={"manifest_id": str(uuid.uuid4())},
        )
        assert r.status_code == 404
