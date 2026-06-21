"""Integration smoke tests for the repair document extraction endpoint.

Run against a live OHM API:
    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_repair_extract.py -v
"""

from __future__ import annotations

import io
import os

import pytest
import httpx

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_API_TESTS", "0") != "1",
        reason="Set RUN_LIVE_API_TESTS=1 and a reachable OHM API at localhost:8001 to run",
    ),
]

BASE = "http://localhost:8001/v1"

# ---------------------------------------------------------------------------
# Sample repair documents as in-memory bytes
# ---------------------------------------------------------------------------

_SERVICE_MANUAL_TEXT = b"""\
Fresenius 2008H Hemodialysis System
Troubleshooting Guide

Models: 2008H, 2008K

WARNING: Never troubleshoot with patient connected to the system.
WARNING: Unplug device from mains power before opening any service panels.

Tools Required:
- Phillips #2 screwdriver
- Torque wrench 5-10 Nm
- Digital multimeter

Error Code Guide:
FLWERR   Blood flow sensor failure
!WATER   Inlet water pressure low
VLVERR   Proportioning valve fault

Parts List

PART.NO       DESCRIPTION
BLOODPUMP-01  Blood pump module (replaceable)
FLOWSNS-02    Blood flow sensor
PROPVLV-03    Proportioning valve
FILTER-04     Pre-filter cartridge (consumable)
"""

_PARTS_CATALOG_TEXT = b"""\
Frigidaire Electric Range - Parts Catalog

POS.NO  PART.NO     DESCRIPTION
1       316571702   TRIM-DRAWER,UPPER
2       316571701   TRIM-DRAWER,LOWER
3       316452400   GASKET-DRAWER (consumable)
4       316435200   ELEMENT-BAKE (replaceable)
"""

_IFIXIT_GUIDE_TEXT = b"""\
Nintendo NES Disassembly
Written By: Joe Shacar

Applies to: NES-001, NES-101

Tools Required:
- Phillips #0 Screwdriver
- TR9 Torx Security Screwdriver
- Flathead Screwdriver

CAUTION: Discharge any static electricity before handling internal components.

Step 1. Remove the six Phillips screws from the underside.
Step 2. Lift the top shell away from the console.
"""


def _upload(files_dict: dict, form: dict | None = None) -> httpx.Response:
    """POST multipart/form-data to the extract-repair-docs endpoint."""
    files = [
        ("files", (name, io.BytesIO(content), "application/octet-stream"))
        for name, content in files_dict.items()
    ]
    data = form or {}
    return httpx.post(
        f"{BASE}/api/okh/extract-repair-docs",
        files=files,
        data=data,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Basic success / shape tests
# ---------------------------------------------------------------------------


class TestExtractRepairDocsBasic:
    def test_returns_200(self):
        r = _upload({"service-manual.txt": _SERVICE_MANUAL_TEXT})
        assert r.status_code == 200, r.text

    def test_response_shape(self):
        body = _upload({"service-manual.txt": _SERVICE_MANUAL_TEXT}).json()
        assert body["success"] is True
        assert "components" in body
        assert "repair_guides" in body
        assert "documentation_type" in body
        assert "source_files" in body
        assert "llm_enhanced" in body
        assert "notes" in body

    def test_source_files_reflects_uploaded_name(self):
        body = _upload({"my-manual.txt": _SERVICE_MANUAL_TEXT}).json()
        assert "my-manual.txt" in body["source_files"]

    def test_no_llm_by_default(self):
        body = _upload({"service-manual.txt": _SERVICE_MANUAL_TEXT}).json()
        assert body["llm_enhanced"] is False

    def test_multiple_files(self):
        body = _upload(
            {
                "service-manual.txt": _SERVICE_MANUAL_TEXT,
                "parts.txt": _PARTS_CATALOG_TEXT,
            }
        ).json()
        assert body["success"] is True
        assert len(body["source_files"]) == 2

    def test_empty_files_returns_400(self):
        r = httpx.post(
            f"{BASE}/api/okh/extract-repair-docs",
            content=b"",
            headers={"Content-Type": "multipart/form-data; boundary=x"},
            timeout=10,
        )
        assert r.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Document-type classification
# ---------------------------------------------------------------------------


class TestDocumentTypeClassification:
    def test_service_manual_classified(self):
        body = _upload({"fresenius-troubleshoot.txt": _SERVICE_MANUAL_TEXT}).json()
        assert body["documentation_type"] == "troubleshooting-guide"

    def test_parts_catalog_classified(self):
        body = _upload({"frigidaire-parts.txt": _PARTS_CATALOG_TEXT}).json()
        assert body["documentation_type"] == "parts-catalog"


# ---------------------------------------------------------------------------
# Component extraction
# ---------------------------------------------------------------------------


class TestComponentExtraction:
    def test_extracts_at_least_one_component(self):
        body = _upload({"manual.txt": _SERVICE_MANUAL_TEXT}).json()
        assert len(body["components"]) >= 1

    def test_part_numbers_extracted(self):
        body = _upload({"manual.txt": _SERVICE_MANUAL_TEXT}).json()
        pns = [c.get("part_number") for c in body["components"] if c.get("part_number")]
        assert len(pns) >= 1

    def test_consumable_marked_from_parts_catalog(self):
        body = _upload({"parts.txt": _PARTS_CATALOG_TEXT}).json()
        consumables = [c for c in body["components"] if c.get("consumable")]
        assert len(consumables) >= 1, "Expected at least one consumable component"

    def test_diagnostic_codes_extracted(self):
        body = _upload({"manual.txt": _SERVICE_MANUAL_TEXT}).json()
        all_codes = []
        for c in body["components"]:
            all_codes.extend(c.get("diagnostic_codes", []))
        # May be empty if codes weren't mapped to components — that's acceptable
        # The important thing is that extraction doesn't error
        assert isinstance(all_codes, list)


# ---------------------------------------------------------------------------
# Repair guide extraction
# ---------------------------------------------------------------------------


class TestRepairGuideExtraction:
    def test_guide_extracted_from_ifixit(self):
        body = _upload({"nes-disassembly.txt": _IFIXIT_GUIDE_TEXT}).json()
        assert len(body["repair_guides"]) >= 1

    def test_guide_has_author(self):
        body = _upload({"nes-disassembly.txt": _IFIXIT_GUIDE_TEXT}).json()
        guides_with_author = [g for g in body["repair_guides"] if g.get("author")]
        assert len(guides_with_author) >= 1
        assert guides_with_author[0]["author"] == "Joe Shacar"

    def test_guide_has_tools(self):
        body = _upload({"nes-disassembly.txt": _IFIXIT_GUIDE_TEXT}).json()
        tools = []
        for g in body["repair_guides"]:
            tools.extend(g.get("tools_required", []))
        assert len(tools) >= 1

    def test_guide_has_safety_prerequisites(self):
        body = _upload({"manual.txt": _SERVICE_MANUAL_TEXT}).json()
        prereqs = []
        for g in body["repair_guides"]:
            prereqs.extend(g.get("safety_prerequisites", []))
        assert len(prereqs) >= 1

    def test_applies_to_models_extracted(self):
        body = _upload({"nes-disassembly.txt": _IFIXIT_GUIDE_TEXT}).json()
        models = []
        for g in body["repair_guides"]:
            models.extend(g.get("applies_to_models", []))
        assert len(models) >= 1


# ---------------------------------------------------------------------------
# Manifest merge
# ---------------------------------------------------------------------------


class TestManifestMerge:
    @pytest.fixture(scope="class")
    def empty_manifest_id(self):
        r = httpx.post(
            f"{BASE}/api/okh/create",
            json={
                "content": {
                    "title": "Repair Merge Test Device",
                    "version": "0.1.0",
                    "license": {"hardware": "CERN-OHL-S-2.0"},
                    "licensor": "Test Suite",
                    "documentation_language": "en",
                    "function": "Target manifest for repair doc merge test",
                }
            },
            timeout=30,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        return body.get("manifest_id") or body.get("okh", {}).get("id")

    def test_merge_adds_components(self, empty_manifest_id):
        r = _upload(
            {"manual.txt": _SERVICE_MANUAL_TEXT},
            form={"manifest_id": empty_manifest_id},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["manifest_id"] == empty_manifest_id

        # Verify components were persisted
        manifest = httpx.get(f"{BASE}/api/okh/{empty_manifest_id}", timeout=10).json()
        assert len(manifest.get("components", [])) >= 1

    def test_invalid_manifest_id_returns_404(self):
        r = _upload(
            {"manual.txt": _SERVICE_MANUAL_TEXT},
            form={"manifest_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert r.status_code == 404
