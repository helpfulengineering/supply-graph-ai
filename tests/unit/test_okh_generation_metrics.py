"""Unit tests for OKH generation quality metrics."""

from __future__ import annotations

import json
from pathlib import Path

from tests.data.okh_generation.metrics import (
    heuristic_layer_comparison,
    heuristic_manifest_quality,
)

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "okh_generation" / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_presence_and_confidence_on_clean_fixture() -> None:
    q = heuristic_manifest_quality(_load("materials_clean.json"))
    assert q["has_title"] is True
    assert q["has_version"] is True
    assert q["has_function"] is True
    assert q["has_description"] is True
    assert q["generation_confidence"] == 1.0
    assert q["function_suspected_license_leak"] is False
    assert q["materials_count"] == 3
    assert q["materials_near_dup_pairs"] == 0
    assert q["materials_prose_like_count"] == 0
    assert q["materials_quality_score"] == 1.0


def test_near_dup_fixture_counts_cable_and_acrylic_pairs() -> None:
    q = heuristic_manifest_quality(_load("materials_near_dup.json"))
    assert q["materials_near_dup_pairs"] == 2  # Cable/cables + Acrylic/acrylic
    assert q["materials_prose_like_count"] == 0
    assert q["materials_quality_score"] < 1.0


def test_prose_fixture_flags_instruction_and_table_rows() -> None:
    q = heuristic_manifest_quality(_load("materials_prose.json"))
    assert q["materials_count"] == 4
    assert q["materials_prose_like_count"] == 3
    assert q["materials_near_dup_pairs"] == 0
    assert q["materials_quality_score"] < 1.0


def test_license_leak_detected_in_function() -> None:
    q = heuristic_manifest_quality(
        {
            "title": "X",
            "version": "1",
            "function": (
                "Permission is hereby granted under the MIT license; "
                "also see GPL terms for software components."
            ),
            "description": "d",
            "materials": [],
        }
    )
    assert q["function_suspected_license_leak"] is True


def test_layer_comparison_reports_deltas() -> None:
    clean = _load("materials_clean.json")
    dirty = _load("materials_near_dup.json")
    cmp_ = heuristic_layer_comparison(dirty, clean)
    assert "3L" in cmp_ and "4L" in cmp_
    assert cmp_["materials_near_dup_delta"] < 0
