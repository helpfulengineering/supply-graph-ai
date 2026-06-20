"""Integration smoke tests for API endpoints added in issues #171-176.

Run against a live OHM API:
    pytest tests/integration/test_api_171_176.py -v
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
import httpx

BASE = "http://localhost:8001/v1"

# ---------------------------------------------------------------------------
# Minimal valid OKH manifest used across all tests
# ---------------------------------------------------------------------------

_MANIFEST = {
    "title": "Integration Test Widget",
    "version": "0.1.0",
    "license": {"hardware": "MIT"},
    "licensor": "Test Suite",
    "documentation_language": "en",
    "function": "Smoke-tests the OHM API",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post_json(endpoint: str, data: dict) -> httpx.Response:
    return httpx.post(f"{BASE}{endpoint}", json=data, timeout=30)


def _get(endpoint: str, params: dict | None = None) -> httpx.Response:
    return httpx.get(f"{BASE}{endpoint}", params=params or {}, timeout=30)


# ---------------------------------------------------------------------------
# #171 — OKH completeness metadata in validate response
# ---------------------------------------------------------------------------


class TestValidateCompleteness:
    def test_validate_returns_metadata(self):
        r = _post_json("/api/okh/validate", {"content": _MANIFEST})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "metadata" in body, f"No metadata key in: {body.keys()}"

    def test_validate_metadata_has_coverage_fields(self):
        r = _post_json("/api/okh/validate", {"content": _MANIFEST})
        meta = r.json().get("metadata", {})
        assert "required_coverage" in meta, f"Missing required_coverage: {meta}"
        assert "optional_coverage" in meta, f"Missing optional_coverage: {meta}"

    def test_validate_coverage_values_are_floats_0_to_1(self):
        r = _post_json("/api/okh/validate", {"content": _MANIFEST})
        meta = r.json()["metadata"]
        assert 0.0 <= meta["required_coverage"] <= 1.0
        assert 0.0 <= meta["optional_coverage"] <= 1.0

    def test_validate_field_presence_map_present(self):
        r = _post_json("/api/okh/validate", {"content": _MANIFEST})
        meta = r.json()["metadata"]
        assert "field_presence" in meta
        assert isinstance(meta["field_presence"], dict)


# ---------------------------------------------------------------------------
# #173 — Component field in OKH response
# ---------------------------------------------------------------------------


class TestComponentsField:
    def _first_manifest_id(self) -> str | None:
        r = _get("/api/okh", params={"limit": 1})
        if r.status_code != 200:
            return None
        items = r.json().get("items", [])
        return items[0]["id"] if items else None

    def test_get_manifest_includes_components_field(self):
        manifest_id = self._first_manifest_id()
        if not manifest_id:
            pytest.skip("No manifests stored — store one first")
        r = _get(f"/api/okh/{manifest_id}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert (
            "components" in body
        ), f"components field missing from GET response: {list(body.keys())}"

    def test_validate_includes_component_count_in_metadata(self):
        """Validate a manifest with components; metadata should include component_count."""
        payload = dict(_MANIFEST)
        payload["components"] = [{"name": "Frame", "quantity": 1}]
        r = _post_json("/api/okh/validate", {"content": payload})
        assert r.status_code == 200, r.text
        meta = r.json().get("metadata", {})
        assert "component_count" in meta, f"component_count missing: {meta}"
        assert meta["component_count"] == 1


# ---------------------------------------------------------------------------
# #174 — Package pin / verify-pin
# Requires a built package on disk — skip if none found.
# ---------------------------------------------------------------------------


def _first_built_package() -> tuple[str, str] | None:
    """Return (org/project, version) for the first local package, or None."""
    packages_dir = Path(__file__).resolve().parents[2] / "packages"
    if not packages_dir.exists():
        return None
    for org_dir in packages_dir.iterdir():
        if not org_dir.is_dir():
            continue
        for proj_dir in org_dir.iterdir():
            if not proj_dir.is_dir():
                continue
            for ver_dir in proj_dir.iterdir():
                if ver_dir.is_dir():
                    return f"{org_dir.name}/{proj_dir.name}", ver_dir.name
    return None


@pytest.fixture(scope="module")
def built_package():
    pkg = _first_built_package()
    if pkg is None:
        pytest.skip(
            "No built packages found — build one with 'ohm package build' first"
        )
    return pkg


class TestPackagePin:
    def test_pin_returns_200(self, built_package):
        org_proj, version = built_package
        org, proj = org_proj.split("/", 1)
        r = httpx.post(
            f"{BASE}/api/package/{org}/{proj}/{version}/pin",
            params={"pinned_by": "integration-test"},
            timeout=30,
        )
        assert r.status_code == 200, r.text

    def test_pin_response_has_pin_record(self, built_package):
        org_proj, version = built_package
        org, proj = org_proj.split("/", 1)
        r = httpx.post(
            f"{BASE}/api/package/{org}/{proj}/{version}/pin",
            params={"pinned_by": "integration-test"},
            timeout=30,
        )
        body = r.json()
        data = body.get("data", body)
        assert "pin_record" in data, f"No pin_record in: {data.keys()}"
        assert "manifest_content_hash" in data["pin_record"]

    def test_verify_pin_returns_verified_true(self, built_package):
        org_proj, version = built_package
        org, proj = org_proj.split("/", 1)
        # Ensure pinned first
        httpx.post(
            f"{BASE}/api/package/{org}/{proj}/{version}/pin",
            params={"pinned_by": "integration-test"},
            timeout=30,
        )
        r = _get(f"/api/package/{org}/{proj}/{version}/verify-pin")
        assert r.status_code == 200, r.text
        data = r.json().get("data", r.json())
        assert data.get("verified") is True

    def test_verify_pin_404_without_pin(self):
        r = _get("/api/package/nonexistent/pkg/9.9.9/verify-pin")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# #175 — Package verify-signature
# ---------------------------------------------------------------------------


class TestPackageSignature:
    def test_verify_signature_404_for_missing_package(self):
        r = _get("/api/package/nonexistent/pkg/9.9.9/verify-signature")
        assert r.status_code == 404

    def test_verify_signature_404_without_signature(self, built_package):
        org_proj, version = built_package
        org, proj = org_proj.split("/", 1)
        r = _get(f"/api/package/{org}/{proj}/{version}/verify-signature")
        # Either 404 (no sig) or 200 (signed during build) — never 500
        assert r.status_code in (200, 404), r.text


# ---------------------------------------------------------------------------
# #176 — OKH collection export / import / diff
# ---------------------------------------------------------------------------


class TestCollectionExport:
    def test_export_collection_returns_zip(self):
        r = _get("/api/okh/export-collection")
        # 404 = empty collection, 200 = has data
        if r.status_code == 404:
            pytest.skip("Collection is empty — store a manifest first")
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "application/zip"
        assert zipfile.is_zipfile(io.BytesIO(r.content))

    def test_export_collection_zip_has_index(self):
        r = _get("/api/okh/export-collection")
        if r.status_code == 404:
            pytest.skip("Collection is empty")
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            assert "collection-index.json" in zf.namelist()

    def test_export_collection_index_entries_valid(self):
        r = _get("/api/okh/export-collection")
        if r.status_code == 404:
            pytest.skip("Collection is empty")
        with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
            index = json.loads(zf.read("collection-index.json"))
        assert isinstance(index, list)
        for entry in index:
            assert "content_hash" in entry
            assert entry["content_hash"].startswith("sha256:")
            assert "title" in entry
            assert "version" in entry


class TestCollectionImport:
    @pytest.fixture
    def collection_archive(self) -> bytes:
        """Export the current collection for use in import/diff tests."""
        r = _get("/api/okh/export-collection")
        if r.status_code == 404:
            pytest.skip("Collection is empty — cannot test import/diff")
        return r.content

    def test_import_dry_run_returns_report(self, collection_archive):
        r = httpx.post(
            f"{BASE}/api/okh/import-collection",
            files={"file": ("collection.zip", collection_archive, "application/zip")},
            params={"dry_run": "true"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "new" in body
        assert "duplicate" in body
        assert "conflict" in body
        assert body.get("dry_run") is True

    def test_import_dry_run_all_are_duplicates(self, collection_archive):
        """Re-importing the same export must classify everything as duplicate."""
        r = httpx.post(
            f"{BASE}/api/okh/import-collection",
            files={"file": ("collection.zip", collection_archive, "application/zip")},
            params={"dry_run": "true"},
            timeout=30,
        )
        body = r.json()
        assert len(body["new"]) == 0
        assert len(body["conflict"]) == 0
        assert len(body["duplicate"]) > 0

    def test_import_dry_run_does_not_write(self, collection_archive):
        """imported count must be 0 in dry-run mode."""
        r = httpx.post(
            f"{BASE}/api/okh/import-collection",
            files={"file": ("collection.zip", collection_archive, "application/zip")},
            params={"dry_run": "true"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        assert r.json().get("imported", 0) == 0


class TestCollectionDiff:
    @pytest.fixture
    def collection_archive(self) -> bytes:
        r = _get("/api/okh/export-collection")
        if r.status_code == 404:
            pytest.skip("Collection is empty — cannot test diff")
        return r.content

    def test_diff_identical_archive_is_empty(self, collection_archive):
        r = httpx.post(
            f"{BASE}/api/okh/diff-collection",
            files={"file": ("collection.zip", collection_archive, "application/zip")},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "only_in_archive" in body
        assert "only_local" in body
        # Diffing a fresh export against itself should show nothing
        assert body["only_in_archive"] == []
        assert body["only_local"] == []
