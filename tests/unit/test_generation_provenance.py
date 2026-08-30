"""The generation record travels beside the manifest, never inside it.

``manifest_content_hash`` is taken over the whole manifest dict with no field
exclusions, so provenance embedded in ``metadata`` would change the design's
content address — the value that pins a package, dedups a collection and dedups
the federation catalogue. The same design generated twice would then be two
different designs, and "clean" versus "with provenance" two more.

The first test is the one that matters: producing the record must leave the
manifest byte-identical.
"""

from __future__ import annotations

import copy

from src.core.federation.catalog import manifest_content_hash
from src.core.generation.models import (
    FieldGeneration,
    GenerationLayer,
    ManifestGeneration,
    PlatformType,
    ProjectData,
    QualityReport,
)
from src.core.generation.provenance import SCHEMA, build_provenance

STAGES = [
    {"seq": 0, "stage": "clone", "fraction": 0.12, "message": "Cloning", "ts": "t0"},
    {"seq": 1, "stage": "nlp", "fraction": 0.40, "message": None, "ts": "t1"},
]


def _result() -> ManifestGeneration:
    return ManifestGeneration(
        project_data=ProjectData(
            platform=PlatformType.GITHUB,
            url="https://example.com/org/repo",
            metadata={},
            files=[],
            documentation=[],
            raw_content={},
        ),
        generated_fields={
            # Present so the manifest id is derived (uuid5 over the repo URL)
            # rather than random: without a repo, to_okh_manifest falls back to
            # uuid4 and is non-deterministic call to call, which would make the
            # hash comparison below meaningless rather than strict.
            "repo": FieldGeneration(
                value="https://example.com/org/repo",
                confidence=1.0,
                source_layer=GenerationLayer.DIRECT,
                generation_method="metadata_html_url",
                raw_source="metadata.html_url",
            ),
            "title": FieldGeneration(
                value="Open Ventilator",
                confidence=0.91,
                source_layer=GenerationLayer.DIRECT,
                generation_method="metadata_name",
                raw_source="metadata.name",
            ),
            "description": FieldGeneration(
                value="A 3D-printable valve",
                confidence=0.62,
                source_layer=GenerationLayer.NLP,
                generation_method="readme_summary",
                raw_source="README.md",
            ),
        },
        confidence_scores={"title": 0.91, "description": 0.62},
        quality_report=QualityReport(
            overall_quality=0.8,
            required_fields_complete=True,
            missing_required_fields=[],
            low_confidence_fields=["description"],
            recommendations=[],
        ),
        missing_fields=[],
        stage_events=list(STAGES),
    )


def _stable(manifest: dict) -> dict:
    """The manifest minus the one field that is a clock reading.

    ``metadata.generated_at`` is stamped per call, so two serialisations of the
    same result differ there and nowhere else. Freezing it isolates the question
    this test asks — does building the record change the manifest — from the
    passage of time.
    """
    out = copy.deepcopy(manifest)
    if isinstance(out.get("metadata"), dict):
        out["metadata"]["generated_at"] = "<frozen>"
    return out


def test_building_the_record_leaves_the_manifest_content_hash_unchanged():
    result = _result()
    before = manifest_content_hash(_stable(result.to_okh_manifest()))

    build_provenance(result, source_url="https://example.com/org/repo")

    after = manifest_content_hash(_stable(result.to_okh_manifest()))
    assert before == after, (
        "Producing provenance changed the manifest's content address. Pins, "
        "collection dedup and federation dedup all key off this hash."
    )


def test_the_manifest_carries_no_provenance():
    """Not even under another name: the hash covers every key."""
    manifest = _result().to_okh_manifest()
    serialised = str(manifest)
    assert "provenance" not in serialised
    assert "stage_events" not in serialised
    assert SCHEMA not in serialised


def test_every_generated_field_reports_layer_method_confidence_and_source():
    record = build_provenance(_result())

    assert record["fields"]["title"] == {
        "layer": GenerationLayer.DIRECT.value,
        "method": "metadata_name",
        "confidence": 0.91,
        "source": "metadata.name",
    }
    # The accuracy-checking case: which layer produced this, and from where.
    assert record["fields"]["description"]["layer"] == GenerationLayer.NLP.value
    assert record["fields"]["description"]["source"] == "README.md"


def test_the_timeline_comes_through():
    record = build_provenance(_result())
    assert [event["stage"] for event in record["stages"]] == ["clone", "nlp"]


def test_the_manifest_id_is_stable_across_serialisations():
    """Guards the premise of the hash test above, not the sidecar itself."""
    result = _result()
    assert result.to_okh_manifest()["id"] == result.to_okh_manifest()["id"]


def test_an_async_run_can_supply_its_own_timeline():
    """The job event log has the same shape, so it substitutes directly."""
    from_job = [{"seq": 0, "stage": "llm", "fraction": 0.4, "message": None, "ts": "t"}]
    record = build_provenance(_result(), stages=from_job)
    assert [event["stage"] for event in record["stages"]] == ["llm"]


def test_the_record_is_self_describing():
    record = build_provenance(_result(), source_url="https://example.com/org/repo")
    assert record["schema"] == SCHEMA
    assert record["source_url"] == "https://example.com/org/repo"
    assert record["generated_at"]


def test_a_run_with_no_fields_still_produces_a_record():
    result = _result()
    result.generated_fields = {}
    record = build_provenance(result)
    assert record["fields"] == {}
    assert record["schema"] == SCHEMA
