"""A version is read from where the author declared it, or left blank (#564)."""

from src.core.generation.models import FileInfo, PlatformType, ProjectData
from src.core.generation.version_sources import (
    declared_version,
    missing_version_warning,
)

KICAD_SCH = (
    '(kicad_sch\n  (title_block\n    (title "Board")\n    (rev "{rev}")\n  )\n)\n'
)


def _project(files=None, metadata=None) -> ProjectData:
    return ProjectData(
        platform=PlatformType.GITHUB,
        url="https://github.com/example/board",
        metadata=metadata or {},
        files=[
            FileInfo(path=path, content=content, size=len(content), file_type="text")
            for path, content in (files or {}).items()
        ],
        documentation=[],
        raw_content={},
    )


def _kicad_project(rev: str, stem: str = "board/board") -> dict:
    return {f"{stem}.kicad_pro": "{}", f"{stem}.kicad_sch": KICAD_SCH.format(rev=rev)}


def test_a_release_tag_is_the_version() -> None:
    assert declared_version(_project(metadata={"tag_name": "v0.3.1"})) == (
        "0.3.1",
        "release tag v0.3.1",
    )


def test_a_root_version_file_is_the_version() -> None:
    assert declared_version(_project({"VERSION": "2.1\n"})) == ("2.1", "VERSION")


def test_a_root_package_manifest_is_the_version() -> None:
    project = _project({"package.json": '{"name": "board", "version": "1.4.0"}'})
    assert declared_version(project) == ("1.4.0", "package.json: version")


def test_a_nested_package_manifest_is_firmware_not_the_design() -> None:
    project = _project({"firmware/package.json": '{"version": "5.1.2"}'})
    assert declared_version(project) is None


def test_the_kicad_title_block_revision_is_the_version() -> None:
    project = _project(_kicad_project("0.2", "frugal_iot_v02/frugal_iot_v02"))
    assert declared_version(project) == (
        "0.2",
        "frugal_iot_v02/frugal_iot_v02.kicad_sch: title_block rev",
    )


def test_a_schematic_outside_a_kicad_project_is_not_read() -> None:
    project = _project({"tools/out/scratch.kicad_sch": KICAD_SCH.format(rev="9")})
    assert declared_version(project) is None


def test_kicad_projects_that_disagree_declare_nothing() -> None:
    project = _project({**_kicad_project("1"), **_kicad_project("2", "other/other")})
    assert declared_version(project) is None


def test_a_release_outranks_a_design_file() -> None:
    project = _project(_kicad_project("0.2"), metadata={"tag_name": "1.0"})
    assert declared_version(project) == ("1.0", "release tag 1.0")


def test_prose_never_declares_a_version() -> None:
    """'V0.2' and 'revision 4' in a README is how 0.2.4 was invented."""
    project = _project({"README.md": "# Board V0.2\n\nStatus: revision 4.\n"})
    assert declared_version(project) is None


def test_the_warning_names_the_hints_it_saw() -> None:
    project = _project(
        {
            "README.md": "# Frugal IoT V0.2\n\nStatus: revision 4.\n",
            "fabrication/frugal_iot_v02-F_Cu.gbr": "",
        }
    )
    warning = missing_version_warning(project)
    assert "v02" in warning
    assert "V0.2" in warning


def test_the_warning_without_hints_says_where_to_declare_one() -> None:
    warning = missing_version_warning(_project({"README.md": "# Board\n"}))
    assert "release" in warning and "VERSION" in warning
