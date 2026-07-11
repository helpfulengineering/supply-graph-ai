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


def test_part_reference_evidence_accepts_short_list_item_outside_bom_heading() -> None:
    """Short tokens in any discrete list/table cell count; instruction mentions do not."""
    corpus = (
        "## Hardware\n"
        "- Raspberry Pi\n"
        "- acrylic sheet\n"
        "- M3 screw\n"
        "\n"
        "## Getting started\n"
        "Make sure you have an Arduino or equivalent microprocessor.\n"
        "The motor drives the stage when powered.\n"
    )
    assert has_part_reference_evidence("Raspberry Pi", corpus) is True
    assert has_part_reference_evidence("acrylic", corpus) is True
    assert has_part_reference_evidence("M3", corpus) is True
    # Instruction / narrative only — not a discrete part line
    assert has_part_reference_evidence("Arduino", corpus) is False
    assert has_part_reference_evidence("motor", corpus) is False


def test_normalize_materials_keeps_short_list_items_without_bom_heading() -> None:
    mg = _empty_manifest()
    mg.project_data.metadata["readme_content"] = (
        "## Hardware\n"
        "- Raspberry Pi\n"
        "- acrylic sheet\n"
        "\n"
        "## Notes\n"
        "Make sure you have an Arduino ready.\n"
    )
    out = mg._normalize_materials(
        [
            {"material_id": "rpi", "name": "Raspberry Pi"},
            {"material_id": "acrylic", "name": "acrylic"},
            {"material_id": "arduino", "name": "Arduino"},
        ]
    )
    names = {row["name"] for row in out}
    assert names == {"Raspberry Pi", "acrylic"}


def test_shopping_list_line_is_part_evidence() -> None:
    corpus = (
        "Tantalum Capacitor 100UF 10V - https://ali.ski/Lx9iQd (10 pcs - $1,85)\n"
        "SMD LED 0805 - https://ali.ski/wb6ZP (100 pcs - $2)\n"
        "#### SGP40: https://ali.ski/3sbUP\n"
        "#### 2. Install the latest version of the MySensors library\n"
        "Make sure you have an Arduino IDE ready.\n"
    )
    assert has_part_reference_evidence("Capacitor", corpus) is True
    assert has_part_reference_evidence("LED", corpus) is True
    assert has_part_reference_evidence("SGP40", corpus) is True
    assert has_part_reference_evidence("MySensors", corpus) is False
    assert has_part_reference_evidence("Arduino IDE", corpus) is False


def test_harvest_shopping_and_gitbuilding_parts_into_materials() -> None:
    from src.core.generation.models import FileInfo

    mg = _empty_manifest()
    mg.project_data.metadata["readme_content"] = (
        "#### SGP40: https://ali.ski/3sbUP\n"
        "BME280 - https://ali.ski/wLEIir (2 pcs - $11.5)\n"
        "#### 1. Install the Arduino IDE portable\n"
    )
    mg.project_data.files = [
        FileInfo(
            path="docs/parts/electronics.yml",
            size=80,
            content=(
                "28BYJ-48:\n"
                "  Name: 28BYJ-48 Stepper Motors\n"
                "  Description: 5V micro-geared stepper motors.\n"
            ),
            file_type="yaml",
        )
    ]
    # Start from empty extraction — harvest should supply real parts
    out = mg._normalize_materials([])
    names = {row["name"] for row in out}
    assert "SGP40" in names
    assert "BME280" in names
    assert "28BYJ-48 Stepper Motors" in names
    assert "Arduino IDE" not in names


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


def test_score_material_high_for_harvested_yaml_name() -> None:
    from src.core.generation.materials_confidence import score_material

    conf, reason = score_material(
        "28BYJ-48 Stepper Motors", source="harvest_yaml", has_evidence=True
    )
    assert conf >= 0.85
    assert reason == "harvested_part"


def test_score_material_low_for_chat_and_sales_lines() -> None:
    from src.core.generation.materials_confidence import (
        LOW_MATERIAL_CONFIDENCE,
        score_material,
    )

    for name in (
        "Телеграм чат DIY Devices",
        "Продажа DIY Устройств",
        "Нou can make your own pcb here",
    ):
        conf, reason = score_material(name, source="extracted", has_evidence=True)
        assert conf < LOW_MATERIAL_CONFIDENCE
        assert reason == "chat_or_sales_line"


def test_normalize_materials_flags_low_confidence_in_review_queue() -> None:
    from src.core.generation.models import FileInfo

    mg = _empty_manifest()
    # Shopping-line harvest keeps the chat blurb in materials; scoring flags it.
    mg.project_data.metadata["readme_content"] = (
        "Телеграм чат DIY Devices - https://t.me/example\n"
        "BME280 - https://ali.ski/wLEIir\n"
    )
    mg.project_data.files = [
        FileInfo(
            path="docs/parts/electronics.yml",
            size=40,
            content="motor:\n  Name: 28BYJ-48 Stepper Motors\n",
            file_type="yaml",
        )
    ]
    out = mg._normalize_materials([])
    names = {row["name"] for row in out}
    assert "Телеграм чат DIY Devices" in names  # kept, flagged
    assert "28BYJ-48 Stepper Motors" in names
    assert "BME280" in names
    review = mg.review_items.get("materials") or []
    review_names = {item.name for item in review}
    assert "Телеграм чат DIY Devices" in review_names
    assert "28BYJ-48 Stepper Motors" not in review_names
    assert "BME280" not in review_names

    manifest = mg.to_okh_manifest()
    gen_review = manifest["metadata"].get("generation_review", {})
    flagged = {m["name"] for m in gen_review.get("materials", [])}
    assert "Телеграм чат DIY Devices" in flagged


def test_apply_material_triage_rejects_and_renames() -> None:
    from src.core.generation.materials_confidence import MaterialReviewItem
    from src.core.generation.materials_llm_triage import (
        MaterialTriageDecision,
        apply_material_triage_decisions,
        parse_materials_triage_response,
    )

    materials = [
        {"material_id": "a", "name": "Телеграм чат DIY Devices"},
        {"material_id": "b", "name": "led"},
        {"material_id": "c", "name": "BME280"},
    ]
    review = [
        MaterialReviewItem(
            name="Телеграм чат DIY Devices",
            confidence=0.2,
            source="harvest",
            reason="chat_or_sales_line",
            needs_review=True,
            material_id="a",
        ),
        MaterialReviewItem(
            name="led",
            confidence=0.55,
            source="extracted",
            reason="generic_token_with_evidence",
            needs_review=True,
            material_id="b",
        ),
    ]
    raw = (
        '[{"name":"Телеграм чат DIY Devices","action":"reject","new_name":null},'
        '{"name":"led","action":"rename","new_name":"SMD LED 0805"}]'
    )
    decisions = parse_materials_triage_response(raw, review)
    assert {d.action for d in decisions} == {"reject", "rename"}

    out, new_review = apply_material_triage_decisions(
        materials,
        decisions,
        generate_material_id=lambda n: f"mat-{n.casefold().replace(' ', '-')}",
    )
    names = {row["name"] for row in out}
    assert "Телеграм чат DIY Devices" not in names
    assert "SMD LED 0805" in names
    assert "BME280" in names
    # renamed/accepted should leave the review queue
    assert all(item.name != "led" for item in new_review)


def test_review_interface_materials_queue_drop(monkeypatch) -> None:
    from src.core.generation.materials_confidence import MaterialReviewItem
    from src.core.generation.models import FieldGeneration, GenerationLayer
    from src.core.generation.review import ReviewInterface

    mg = _empty_manifest()
    mg.generated_fields["materials"] = FieldGeneration(
        value=[
            {"material_id": "a", "name": "Junk Chat"},
            {"material_id": "b", "name": "BME280"},
        ],
        confidence=0.5,
        source_layer=GenerationLayer.HEURISTIC,
        generation_method="test",
        raw_source="test",
    )
    mg.review_items["materials"] = [
        MaterialReviewItem(
            name="Junk Chat",
            confidence=0.2,
            source="extracted",
            reason="chat_or_sales_line",
            needs_review=True,
            material_id="a",
        )
    ]
    answers = iter(["d"])
    monkeypatch.setattr("builtins.input", lambda *_a, **_k: next(answers))
    ReviewInterface(mg).review_materials_queue()
    names = {row["name"] for row in mg.generated_fields["materials"].value}
    assert "Junk Chat" not in names
    assert "BME280" in names
    assert mg.review_items["materials"] == []


def test_rejected_keys_suppress_reharvest() -> None:
    from src.core.generation.materials_filter import normalize_material_key

    mg = _empty_manifest()
    mg.project_data.metadata["readme_content"] = (
        "Телеграм чат DIY Devices - https://t.me/example\n"
        "BME280 - https://ali.ski/wLEIir\n"
    )
    mg.materials_rejected_keys.add(normalize_material_key("Телеграм чат DIY Devices"))
    out = mg._normalize_materials([])
    names = {row["name"] for row in out}
    assert "Телеграм чат DIY Devices" not in names
    assert "BME280" in names
