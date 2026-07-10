"""Tests for OKH file URL enrichment."""

from uuid import UUID

from src.core.api.okh_file_urls import enrich_file_ref


def test_enrich_file_ref_adds_display_and_classification():
    item = {
        "title": "Guide",
        "path": "docs/assembly/README.md",
        "type": "design-files",
        "metadata": {},
    }
    okh_id = UUID("3f531231-bf67-4c8d-bd5f-a7ac1a86812f")
    enriched = enrich_file_ref(item, "http://localhost:8001/v1/api", okh_id)

    assert enriched["display_path"] == "docs/assembly/README.md"
    assert enriched["directory"] == "docs/assembly"
    assert enriched["file_type"] == "document_markdown"
    assert enriched["render_tier"] == "text_viewer"
    assert enriched["url"].endswith(
        "/okh/3f531231-bf67-4c8d-bd5f-a7ac1a86812f/files/docs/assembly/README.md"
    )


def test_enrich_github_url_display_path():
    item = {
        "title": "STL",
        "path": "https://github.com/o/r/raw/main/stl/part.stl",
        "type": "manufacturing-files",
        "metadata": {},
    }
    okh_id = UUID("3f531231-bf67-4c8d-bd5f-a7ac1a86812f")
    enriched = enrich_file_ref(item, "http://localhost:8001/v1/api", okh_id)

    assert enriched["display_path"] == "stl/part.stl"
    assert enriched["file_type"] == "mesh_stl"
    assert enriched["render_tier"] == "wasm_3d"
    assert enriched["url"] == item["path"]
