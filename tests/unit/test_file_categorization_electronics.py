"""Electronics files are categorised, not defaulted (#563, from #561).

Paths are from mitra42/frugal-iot-hw-sensor, the repository #561 reported:
every one of these fell through to "No clear pattern matched, defaulting to
design_files" at confidence 0.3.
"""

from pathlib import Path

import pytest

from src.core.generation.utils.file_categorization import FileCategorizationRules
from src.core.models.okh import DocumentationType

DEFAULT_CONFIDENCE = 0.3


def _categorise(path: str):
    return FileCategorizationRules().categorize_file(Path(path).name, path)


@pytest.mark.parametrize(
    "path",
    [
        "SCHEMATIC.pdf",
        "claude-tools/schematic/out/schematic.pdf",
        "docs/power-supply-schematic.png",
        "hardware/Schematics.pdf",
        "fabrication/SCHEMATIC.pdf",
    ],
)
def test_a_schematic_is_a_design_file_wherever_it_is(path):
    result = _categorise(path)

    assert result.documentation_type == DocumentationType.DESIGN_FILES
    assert result.confidence > DEFAULT_CONFIDENCE
    assert "schematic" in result.reason.lower()


@pytest.mark.parametrize("path", ["PCB-LAYOUT.pdf", "pcb_layout.pdf", "PCB Layout.pdf"])
def test_a_pcb_layout_drawing_is_a_design_file(path):
    result = _categorise(path)

    assert result.documentation_type == DocumentationType.DESIGN_FILES
    assert result.confidence > DEFAULT_CONFIDENCE


def test_a_kicad_schematic_is_a_design_file_by_its_extension():
    """It matched before only because "kicad" happens to contain "cad"."""
    result = _categorise("frugal_iot_v02/frugal_iot_v02.kicad_sch")

    assert result.documentation_type == DocumentationType.DESIGN_FILES
    assert result.confidence >= 0.9
    assert ".kicad_sch" in result.reason


@pytest.mark.parametrize(
    "path",
    ["fabrication/README.md", "fabrication/gerbers.zip", "fabrication/assembly.pdf"],
)
def test_files_under_fabrication_are_manufacturing_files(path):
    result = _categorise(path)

    assert result.documentation_type == DocumentationType.MANUFACTURING_FILES
    assert result.confidence > DEFAULT_CONFIDENCE


def test_a_layout_word_alone_does_not_make_a_design_file():
    """'layout' is too common to mean a PCB on its own (page layout, room layout)."""
    result = _categorise("docs/page-layout-notes.md")

    assert "layout" not in result.reason.lower()
