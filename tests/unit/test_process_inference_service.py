"""Unit tests for file-type → manufacturing process inference."""

from __future__ import annotations

import pytest

from src.core.generation.services.process_inference_service import (
    ProcessInferenceService,
)
from src.core.models.okh import DocumentationType, DocumentRef, License, OKHManifest


def _manifest(**kwargs) -> OKHManifest:
    defaults = dict(
        title="Test",
        version="1.0.0",
        license=License(hardware="MIT"),
        licensor="Test",
        documentation_language="en",
        function="Test part",
    )
    defaults.update(kwargs)
    return OKHManifest(**defaults)


@pytest.fixture
def service() -> ProcessInferenceService:
    return ProcessInferenceService()


def test_stl_paths_infer_3d_printing(service: ProcessInferenceService) -> None:
    result = service.infer_from_paths(["models/bracket.stl", "README.md"])
    assert "3D Printing" in result.processes
    assert result.confidence >= 0.7
    assert any("stl" in e.lower() for e in result.evidence.get("3d_printing", []))


def test_3mf_and_gcode_infer_3d_printing(service: ProcessInferenceService) -> None:
    result = service.infer_from_paths(["part.3mf", "toolpath.gcode"])
    assert result.processes == ["3D Printing"]


def test_gerber_infers_pcb_fabrication(service: ProcessInferenceService) -> None:
    result = service.infer_from_paths(["board.gbr", "board.drl"])
    assert "PCB Fabrication" in result.processes


def test_nc_infers_cnc_machining(service: ProcessInferenceService) -> None:
    result = service.infer_from_paths(["pocket.nc"])
    assert "CNC Machining" in result.processes


def test_unrelated_extensions_yield_empty(service: ProcessInferenceService) -> None:
    result = service.infer_from_paths(["main.py", "README.md", "photo.png"])
    assert result.processes == []


def test_deduplicates_across_paths(service: ProcessInferenceService) -> None:
    result = service.infer_from_paths(["a.stl", "b.STL", "c.3mf"])
    assert result.processes.count("3D Printing") == 1


def test_apply_to_manifest_only_if_empty(service: ProcessInferenceService) -> None:
    manifest = _manifest(
        manufacturing_files=[
            DocumentRef(
                title="bracket.stl",
                path="files/bracket.stl",
                type=DocumentationType.MANUFACTURING_FILES,
            )
        ],
        manufacturing_processes=[],
    )

    applied = service.apply_to_manifest(manifest, only_if_empty=True)
    assert "3D Printing" in applied.processes
    assert "3D Printing" in manifest.manufacturing_processes

    manifest.manufacturing_processes = ["Laser Cutting"]
    skipped = service.apply_to_manifest(manifest, only_if_empty=True)
    assert skipped.processes == []
    assert manifest.manufacturing_processes == ["Laser Cutting"]


def test_apply_merges_when_not_only_if_empty(service: ProcessInferenceService) -> None:
    manifest = _manifest(
        manufacturing_files=[
            DocumentRef(
                title="board.gbr",
                path="gerbers/board.gbr",
                type=DocumentationType.MANUFACTURING_FILES,
            ),
        ],
        manufacturing_processes=["Assembly"],
    )

    result = service.apply_to_manifest(manifest, only_if_empty=False)
    assert "Assembly" in manifest.manufacturing_processes
    assert "PCB Fabrication" in manifest.manufacturing_processes
    assert "PCB Fabrication" in result.processes


def test_infer_from_okh_paths_and_design_files(
    service: ProcessInferenceService,
) -> None:
    manifest = _manifest(
        design_files=[
            DocumentRef(
                title="body.stl",
                path="cad/body.stl",
                type=DocumentationType.DESIGN_FILES,
            )
        ],
        manufacturing_processes=[],
    )
    result = service.infer_from_manifest(manifest)
    assert "3D Printing" in result.processes


def test_title_3dp_prefix_infers_3d_printing(service: ProcessInferenceService) -> None:
    result = service.infer_from_text("3DP-Micropipette")
    assert "3D Printing" in result.processes
    assert any("3dp" in e.lower() for e in result.evidence.get("3d_printing", []))


def test_title_laser_cut_infers_laser_cutting(
    service: ProcessInferenceService,
) -> None:
    result = service.infer_from_text("laser-cut-origami-ear-extender")
    assert "Laser Cutting" in result.processes


def test_keywords_infer_pcb(service: ProcessInferenceService) -> None:
    result = service.infer_from_text("open hardware", keywords=["electronics", "pcb"])
    assert "PCB Fabrication" in result.processes


def test_unrelated_title_yields_empty(service: ProcessInferenceService) -> None:
    result = service.infer_from_text("Portable Hand Washing Station")
    assert result.processes == []


def test_face_in_title_does_not_infer_surface_finishing(
    service: ProcessInferenceService,
) -> None:
    """Regression: taxonomy substring match maps 'face' ⊂ 'surface_finish'."""
    result = service.infer_from_text("Badger-Shield Open-Source Face Shield")
    assert "Surface Finishing" not in result.processes
    assert result.processes == []


def test_manifest_title_used_when_no_file_types(
    service: ProcessInferenceService,
) -> None:
    manifest = _manifest(
        title="3DP-Micropipette",
        keywords=["lab", "tool"],
        manufacturing_processes=[],
    )
    result = service.infer_from_manifest(manifest)
    assert "3D Printing" in result.processes


def test_file_type_and_title_merge(service: ProcessInferenceService) -> None:
    manifest = _manifest(
        title="Laser-Cut Face Shield",
        design_files=[
            DocumentRef(
                title="bracket.stl",
                path="bracket.stl",
                type=DocumentationType.DESIGN_FILES,
            )
        ],
        manufacturing_processes=[],
    )
    result = service.infer_from_manifest(manifest)
    assert "3D Printing" in result.processes
    assert "Laser Cutting" in result.processes


@pytest.mark.asyncio
async def test_okh_service_backfill_dry_run() -> None:
    from unittest.mock import AsyncMock

    from src.core.services.okh_service import OKHService

    manifest = _manifest(
        manufacturing_files=[
            DocumentRef(
                title="part.stl",
                path="part.stl",
                type=DocumentationType.MANUFACTURING_FILES,
            )
        ],
        manufacturing_processes=[],
    )
    svc = OKHService()
    svc.ensure_initialized = AsyncMock()
    svc.get = AsyncMock(return_value=manifest)
    svc.update = AsyncMock()

    report = await svc.backfill_manufacturing_processes(
        manifest_ids=[manifest.id],
        only_if_empty=True,
        dry_run=True,
    )
    assert report["dry_run"] is True
    assert report["updated_count"] == 1
    assert "3D Printing" in report["updated"][0]["after"]
    svc.update.assert_not_called()


@pytest.mark.asyncio
async def test_heuristic_layer_infers_from_stl() -> None:
    from src.core.generation.layers.heuristic import HeuristicMatcher
    from src.core.generation.models import (
        FileInfo,
        LayerConfig,
        PlatformType,
        ProjectData,
    )

    config = LayerConfig(
        use_llm=False,
        file_categorization_config={"enable_llm_categorization": False},
    )
    matcher = HeuristicMatcher(config)
    project = ProjectData(
        platform=PlatformType.GITHUB,
        url="https://example.com/repo",
        metadata={},
        files=[
            FileInfo(
                path="models/bracket.stl",
                size=100,
                content="",
                file_type="stl",
            )
        ],
        documentation=[],
        raw_content={},
    )
    result = await matcher.process(project)
    assert result.has_field("manufacturing_processes")
    processes = result.get_field("manufacturing_processes").value
    assert "3D Printing" in processes
