"""OKH-LOSH v2.4 TOML -> OKH conversion field mapping."""

from __future__ import annotations

import pytest

from src.core.services.okh_losh_converter import (
    OkhLoshConversionError,
    OkhLoshConverter,
)

MINIMAL = """
okhv = "2.4"
name = "Test Widget"
repo = "https://example.com/repo"
version = "1.0.0"
license = "CC-BY-4.0"
licensor = "Jane Doe <jane@example.com>"
function = "Does a thing."
documentation-language = "en"
"""


def _write(tmp_path, content: str, name: str = "test.okh.toml"):
    path = tmp_path / name
    path.write_text(content)
    return path


def test_missing_file_raises(tmp_path):
    converter = OkhLoshConverter()
    with pytest.raises(OkhLoshConversionError, match="not found"):
        converter.okh_losh_to_okh(tmp_path / "nope.okh.toml")


def test_invalid_toml_raises(tmp_path):
    converter = OkhLoshConverter()
    path = _write(tmp_path, "not = [valid toml")
    with pytest.raises(OkhLoshConversionError, match="Invalid TOML"):
        converter.okh_losh_to_okh(path)


def test_minimal_fields_and_renames(tmp_path):
    path = _write(tmp_path, MINIMAL)
    manifest = OkhLoshConverter().okh_losh_to_okh(path)

    assert manifest.title == "Test Widget"
    assert manifest.repo == "https://example.com/repo"
    assert manifest.version == "1.0.0"
    assert manifest.license.hardware == "CC-BY-4.0"
    assert manifest.licensor.name == "Jane Doe"
    assert manifest.licensor.email == "jane@example.com"
    assert manifest.documentation_language == "en"


def test_tsdc_and_standard_compliance_wrapped_as_lists(tmp_path):
    content = (
        MINIMAL
        + """
tsdc = "ASM"
standard-compliance = "DIN EN 1335"
"""
    )
    path = _write(tmp_path, content)
    manifest = OkhLoshConverter().okh_losh_to_okh(path)

    assert manifest.tsdc == ["ASM"]
    assert [s.standard_title for s in manifest.standards_used] == ["DIN EN 1335"]


def test_manufacturing_instructions_string_and_list_become_document_refs(tmp_path):
    content = (
        MINIMAL
        + """
manufacturing-instructions = "https://example.com/manual.pdf"
user-manual = ["https://example.com/a.pdf", "https://example.com/b.pdf"]
"""
    )
    path = _write(tmp_path, content)
    manifest = OkhLoshConverter().okh_losh_to_okh(path)

    assert [d.path for d in manifest.making_instructions] == [
        "https://example.com/manual.pdf"
    ]
    assert [d.path for d in manifest.operating_instructions] == [
        "https://example.com/a.pdf",
        "https://example.com/b.pdf",
    ]


def test_software_installation_guide_kebab_case_renamed(tmp_path):
    content = (
        MINIMAL
        + """
[[software]]
release = "https://example.com/release/1.0"
installation-guide = "https://example.com/install.md"
"""
    )
    path = _write(tmp_path, content)
    manifest = OkhLoshConverter().okh_losh_to_okh(path)

    assert len(manifest.software) == 1
    assert manifest.software[0].release == "https://example.com/release/1.0"
    assert manifest.software[0].installation_guide == "https://example.com/install.md"


def test_outer_dimensions_preserved_as_is(tmp_path):
    content = (
        MINIMAL
        + """
[outer-dimensions]
width = 400
depth = 350.8
height = 150
"""
    )
    path = _write(tmp_path, content)
    manifest = OkhLoshConverter().okh_losh_to_okh(path)

    assert manifest.manufacturing_specs.outer_dimensions == {
        "width": 400,
        "depth": 350.8,
        "height": 150,
    }


def test_image_array_picks_primary_and_preserves_full_list_in_metadata(tmp_path):
    content = (
        MINIMAL
        + """
[[image]]
location = "imgs/logo.jpg"
slots = ["logo"]

[[image]]
location = "imgs/main.jpg"
slots = ["photo-thing-main"]

[[image]]
location = "imgs/other.jpg"
"""
    )
    path = _write(tmp_path, content)
    manifest = OkhLoshConverter().okh_losh_to_okh(path)

    # Primary image is the one tagged photo-thing-main, not the first entry.
    assert manifest.image == "imgs/main.jpg"
    assert manifest.metadata["images"] == [
        {"location": "imgs/logo.jpg", "slots": ["logo"]},
        {"location": "imgs/main.jpg", "slots": ["photo-thing-main"]},
        {"location": "imgs/other.jpg"},
    ]


def test_image_as_bare_string_handled(tmp_path):
    content = MINIMAL + 'image = "imgs/only.jpg"\n'
    path = _write(tmp_path, content)
    manifest = OkhLoshConverter().okh_losh_to_okh(path)

    assert manifest.image == "imgs/only.jpg"
    assert manifest.metadata["images"] == [{"location": "imgs/only.jpg"}]


def test_mass_and_release_go_to_metadata(tmp_path):
    content = (
        MINIMAL
        + """
mass = 50330.0
release = "https://example.com/releases/1.0.0"
"""
    )
    path = _write(tmp_path, content)
    manifest = OkhLoshConverter().okh_losh_to_okh(path)

    assert manifest.metadata["mass"] == 50330.0
    assert manifest.metadata["release"] == "https://example.com/releases/1.0.0"
    # No top-level manifest field is affected.
    assert not hasattr(manifest, "release")


def test_multi_value_licensor_and_organization_lists(tmp_path):
    content = (
        MINIMAL.replace(
            'licensor = "Jane Doe <jane@example.com>"',
            'licensor = ["Jane Doe <jane@example.com>", "John Roe <john@example.com>"]',
        )
        + """
organization = ["Org One", "Org Two"]
"""
    )
    path = _write(tmp_path, content)
    manifest = OkhLoshConverter().okh_losh_to_okh(path)

    assert [p.name for p in manifest.licensor] == ["Jane Doe", "John Roe"]
    assert [o.name for o in manifest.organization] == ["Org One", "Org Two"]


def test_okhv_passed_through_literally(tmp_path):
    path = _write(tmp_path, MINIMAL)
    manifest = OkhLoshConverter().okh_losh_to_okh(path)
    assert manifest.okhv == "2.4"
