"""Tests for file type taxonomy."""

from src.core.taxonomy.file_type_taxonomy import (
    DEFAULT_FILE_TYPES_PATH,
    FileTypeTaxonomy,
    file_type_taxonomy,
    load_from_yaml,
    validate_definitions,
)


def test_yaml_loads_and_validates():
    definitions = load_from_yaml(DEFAULT_FILE_TYPES_PATH)
    errors = validate_definitions(definitions)
    assert errors == []
    assert len(definitions) > 10


def test_classify_stl_grey_zone_manufacturing():
    result = file_type_taxonomy.classify("stl/part.stl")
    assert result.file_type == "mesh_stl"
    assert result.render_tier == "wasm_3d"
    assert result.okh_role == "manufacturing"


def test_classify_stl_in_design_dir():
    result = file_type_taxonomy.classify("design/part.stl")
    assert result.file_type == "mesh_stl"
    assert result.okh_role == "design"


def test_classify_pdf():
    result = file_type_taxonomy.classify("docs/manual.pdf")
    assert result.file_type == "document_pdf"
    assert result.render_tier == "native_inline"


def test_classify_markdown():
    result = file_type_taxonomy.classify("docs/README.md")
    assert result.file_type == "document_markdown"
    assert result.render_tier == "text_viewer"


def test_classify_unknown_extension():
    result = file_type_taxonomy.classify("data/weird.xyz")
    assert result.file_type == "unknown"
    assert result.render_tier == "download_only"


def test_classify_github_url():
    url = "https://github.com/o/r/raw/main/docs/assembly/README.md"
    result = file_type_taxonomy.classify(url)
    assert result.file_type == "document_markdown"
    assert result.okh_role == "documentation"


def test_reload_dry_run_smoke():
    definitions = load_from_yaml(DEFAULT_FILE_TYPES_PATH)
    taxonomy = FileTypeTaxonomy(definitions)
    assert taxonomy.get_definition("mesh_stl") is not None
