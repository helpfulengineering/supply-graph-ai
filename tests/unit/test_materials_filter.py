"""Unit tests for Materials shape/key helpers and normalize filtering."""

from __future__ import annotations

import json
from pathlib import Path

from src.core.generation.materials_filter import (
    has_part_reference_evidence,
    is_prose_like,
    normalize_material_key,
)
from src.core.generation.models import (
    ManifestGeneration,
    PlatformType,
    ProjectData,
    QualityReport,
)

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "okh_generation" / "fixtures"


def test_is_prose_like_flags_instruction_and_table_rows() -> None:
    assert is_prose_like("Make sure you have an Arduino or equivalent microprocessor")
    assert is_prose_like(
        "|1|DC Brushless motor|[HobbyKing](https://hobbyking.com/example)|15.22"
    )
    assert is_prose_like("1")
    assert is_prose_like("(*excluding the aluminium block*)")
    assert not is_prose_like("PLA")
    assert not is_prose_like("acrylic")


def test_normalize_material_key_collapses_case_and_plural() -> None:
    assert normalize_material_key("Cable") == normalize_material_key("cables")
    assert normalize_material_key("Acrylic") == normalize_material_key("acrylic")


def _empty_manifest() -> ManifestGeneration:
    return ManifestGeneration(
        project_data=ProjectData(
            platform=PlatformType.GITHUB,
            url="https://example.com/org/repo",
            metadata={},
            files=[],
            documentation=[],
            raw_content={},
        ),
        generated_fields={},
        confidence_scores={},
        quality_report=QualityReport(
            overall_quality=1.0,
            required_fields_complete=True,
            missing_required_fields=[],
            low_confidence_fields=[],
            recommendations=[],
        ),
        missing_fields=[],
    )


def test_normalize_materials_drops_prose_like_rows() -> None:
    fixture = json.loads(
        (FIXTURES / "materials_prose.json").read_text(encoding="utf-8")
    )
    mg = _empty_manifest()
    out = mg._normalize_materials(fixture["materials"])
    names = [row["name"] for row in out]
    assert names == ["PLA"]


def test_part_reference_evidence_accepts_bom_section_item() -> None:
    corpus = (
        "## Bill of Materials\n"
        "- 2x PLA filament\n"
        "- 1 steel screw\n"
        "\n"
        "## Instructions\n"
        "Make sure you have an Arduino ready.\n"
    )
    assert has_part_reference_evidence("PLA", corpus) is True
    assert has_part_reference_evidence("steel", corpus) is True
    assert has_part_reference_evidence("Arduino", corpus) is False


def test_normalize_materials_requires_doc_evidence_when_corpus_present() -> None:
    mg = _empty_manifest()
    mg.project_data.metadata["readme_content"] = (
        "## Bill of Materials\n"
        "- PLA\n"
        "- acrylic sheet\n"
        "\n"
        "## Getting started\n"
        "Make sure you have an Arduino or equivalent microprocessor.\n"
    )
    out = mg._normalize_materials(
        [
            {"material_id": "pla", "name": "PLA"},
            {"material_id": "arduino", "name": "Arduino"},
            {"material_id": "acrylic", "name": "acrylic"},
        ]
    )
    names = {row["name"] for row in out}
    assert names == {"PLA", "acrylic"}


def test_normalize_materials_collapses_near_duplicates() -> None:
    fixture = json.loads(
        (FIXTURES / "materials_near_dup.json").read_text(encoding="utf-8")
    )
    mg = _empty_manifest()
    out = mg._normalize_materials(fixture["materials"])
    keys = {normalize_material_key(row["name"]) for row in out}
    names = [row["name"] for row in out]
    # Cable/cables and Acrylic/acrylic each collapse to one key
    assert "cable" in keys
    assert "acrylic" in keys
    assert len(names) == len(keys)
