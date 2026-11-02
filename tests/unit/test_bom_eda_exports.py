"""BOMs exported by EDA tools are found, linked and read (#564, from #561).

The header and row shapes below are those of mitra42/frugal-iot-hw-sensor: a
KiCad BOM export (quoted, ``Refs``/``Value``/``Qty``) and the JLCPCB assembly
BOM, which has no quantity column and an ``LCSC Part #`` column that is an
order code, not the part's name.
"""

from src.core.generation.bom_candidate_discovery import (
    linked_bom_file,
    list_bom_candidate_paths_from_files,
)
from src.core.generation.bom_models import BOMProcessor, BOMSource, BOMSourceType
from src.core.generation.models import FileInfo, PlatformType, ProjectData

KICAD_BOM = """\
"Refs","Value","MPN","LCSC","Footprint","Qty","DNP","Note"
"C1,C2,C4,C5,C8","10uF","10uF","C19702","Capacitor_SMD:C_0603_1608Metric","5","",""
"C7,C10","1uF","1uF","C15849","Capacitor_SMD:C_0603_1608Metric","2","",""
"""

JLCPCB_BOM = """\
Comment,Designator,Footprint,LCSC Part #
10uF,"C1,C2,C4,C5,C8",C_0603_1608Metric,C19702
1uF,"C7,C10",C_0603_1608Metric,C15849
"""


def _components(path: str, content: str) -> dict:
    source = BOMSource(
        source_type=BOMSourceType.BOM_FILE,
        raw_content=content,
        file_path=path,
        confidence=0.9,
    )
    return {c.name: c.quantity for c in BOMProcessor().process_bom_sources([source])}


def _files(*paths: str) -> list:
    return [FileInfo(path=p, content="x", size=1, file_type="text") for p in paths]


def _project(*paths: str, metadata=None) -> ProjectData:
    return ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/example/board",
        metadata=metadata or {},
        files=_files(*paths),
        documentation=[],
        raw_content={},
    )


def test_a_kicad_bom_export_is_read() -> None:
    assert _components("BOM.csv", KICAD_BOM) == {"10uF": 5, "1uF": 2}


def test_a_jlcpcb_bom_names_parts_by_value_and_counts_designators() -> None:
    assert _components("fabrication/BOM_JLCPCB.csv", JLCPCB_BOM) == {
        "10uF": 5,
        "1uF": 2,
    }


def test_a_plain_parts_list_is_still_read() -> None:
    assert _components("BOM.csv", "Item,Quantity\nM3 bolt,8\n") == {"M3 bolt": 8}


def test_a_jlcpcb_bom_is_a_candidate_ranked_below_a_plain_bom() -> None:
    files = _files(
        "fabrication/BOM_JLCPCB.csv", "fabrication/CPL_JLCPCB.csv", "BOM.csv"
    )
    assert list_bom_candidate_paths_from_files(files) == [
        "BOM.csv",
        "fabrication/BOM_JLCPCB.csv",
    ]


def test_the_top_candidate_is_linked() -> None:
    assert linked_bom_file(_project("README.md", "BOM.csv")) == "BOM.csv"


def test_nothing_is_linked_without_a_candidate() -> None:
    assert linked_bom_file(_project("README.md", "notes.csv")) is None


def test_a_path_that_failed_http_verification_is_not_linked() -> None:
    project = _project(
        "BOM.csv",
        "fabrication/BOM_JLCPCB.csv",
        metadata={
            "_bom_http_verify_summary": {"applied": True},
            "_bom_http_allowed_paths": frozenset({"fabrication/BOM_JLCPCB.csv"}),
        },
    )
    assert linked_bom_file(project) == "fabrication/BOM_JLCPCB.csv"
