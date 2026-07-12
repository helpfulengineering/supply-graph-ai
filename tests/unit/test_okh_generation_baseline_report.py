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
    assert len(data["repos"]) == 26
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
    assert report["summary"]["counts_by_status"]["skipped_no_generated_manifest"] == 2


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
