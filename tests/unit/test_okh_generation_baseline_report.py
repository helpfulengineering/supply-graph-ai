"""Unit tests for OKH generation baseline report builder."""

from __future__ import annotations

import json
from pathlib import Path

from tests.data.okh_generation.baseline_report import (
    build_baseline_report,
    load_repositories_dataset,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "tests" / "data" / "okh_generation"


def test_load_repositories_dataset() -> None:
    data = load_repositories_dataset(PKG / "repositories.json")
    assert len(data["repos"]) == 27
    core = [r for r in data["repos"] if r.get("core_for_regression")]
    assert len(core) >= 6


def test_baseline_skips_without_manifests(tmp_path: Path) -> None:
    report = build_baseline_report(
        REPO_ROOT,
        layer="4L",
        repositories_json=PKG / "repositories.json",
        manifests_dir=tmp_path,
    )
    assert report["summary"]["compared_count"] == 0
    assert report["summary"]["counts_by_status"]["skipped_no_ground_truth"] >= 20
    assert report["summary"]["counts_by_status"]["skipped_no_generated_manifest"] == 3


def test_baseline_compares_when_manifest_present(tmp_path: Path) -> None:
    manifest = {
        "title": "JPL Open Source Rover Project",
        "version": "1.0.0",
        "function": "Open-source rover platform for robotics education and research",
        "license": {
            "hardware": "Apache-2.0",
            "documentation": "Apache-2.0",
            "software": "Apache-2.0",
        },
        "repo": "https://github.com/nasa-jpl/open-source-rover",
        "materials": [
            {"name": "Cable"},
            {"name": "cables"},
        ],
    }
    path = tmp_path / "repo-001-4L.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")

    report = build_baseline_report(
        REPO_ROOT,
        layer="4L",
        repositories_json=PKG / "repositories.json",
        manifests_dir=tmp_path,
    )
    assert report["summary"]["compared_count"] == 1
    compared = next(r for r in report["repos"] if r["status"] == "compared")
    assert compared["id"] == "repo-001"
    assert compared["blocking_accuracy"] == 1.0
    assert compared["blocking_presence_completeness"] == 1.0
    assert compared["heuristic_quality"]["materials_near_dup_pairs"] == 1
    assert report["summary"]["materials_heuristics"]["total_near_dup_pairs"] == 1


ELECTRONICS = "frugal-iot-hw-sensor"


def _electronics_report(tmp_path: Path, manifest: dict) -> dict:
    path = tmp_path / f"{ELECTRONICS}-4L.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return build_baseline_report(
        REPO_ROOT,
        layer="4L",
        repositories_json=PKG / "repositories.json",
        manifests_dir=tmp_path,
    )


def _checks(report: dict) -> dict:
    return next(r for r in report["repos"] if r["id"] == ELECTRONICS)["checks"]


def test_open_ground_truth_checks_are_expected_failures(tmp_path: Path) -> None:
    """What #561's reporter got: a fixed defect fails, an open one is expected."""
    report = _electronics_report(
        tmp_path,
        {
            "title": "Frugal IoT",
            "version": "0.2.4",
            "manufacturing_processes": ["PCB Fabrication", "Sheet Metal Forming"],
            "bom": {"name": "BOM"},
            "design_files": [
                {"path": "SCHEMATIC.pdf"},
                {"path": "PCB-LAYOUT.pdf"},
                {"path": "frugal_iot_v02/frugal_iot_v02.kicad_sch"},
            ],
            "manufacturing_files": [{"path": "fabrication/gerbers.zip"}],
        },
    )
    assert _checks(report) == {
        "version": "fail",
        "manufacturing_processes": "expected_fail",
        "bom_external_file": "fail",
        "file_roles": "pass",
    }
    assert report["summary"]["check_outcomes"] == {
        "fail": 2,
        "expected_fail": 1,
        "pass": 1,
    }


def test_an_open_check_that_passes_is_flagged_for_its_marker(tmp_path: Path) -> None:
    report = _electronics_report(
        tmp_path,
        {
            "version": "0.2",
            "manufacturing_processes": ["PCB Fabrication"],
            "bom": {"external_file": "fabrication/BOM_JLCPCB.csv"},
            "design_files": ["SCHEMATIC.pdf"],
        },
    )
    checks = _checks(report)
    assert checks["version"] == "pass"
    assert checks["manufacturing_processes"] == "unexpected_pass"
    assert checks["bom_external_file"] == "pass"
    assert checks["file_roles"] == "fail"
