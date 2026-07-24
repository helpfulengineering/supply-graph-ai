"""Unit tests for remote file filename probing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

from src.core.api.okh_file_urls import enrich_file_ref
from src.core.utils.remote_file_hint import (
    clear_remote_filename_cache,
    filename_from_content_disposition,
    filename_from_url_path,
    probe_remote_filename,
)


def setup_function() -> None:
    clear_remote_filename_cache()


def test_filename_from_content_disposition() -> None:
    assert (
        filename_from_content_disposition(
            'attachment; filename="3.5cm_BiasTape_minimalistic_Q2.stl"'
        )
        == "3.5cm_BiasTape_minimalistic_Q2.stl"
    )
    assert (
        filename_from_content_disposition("attachment; filename*=UTF-8''part%20a.stl")
        == "part a.stl"
    )


def test_filename_from_url_path_strips_query() -> None:
    assert (
        filename_from_url_path(
            "https://cdn.thingiverse.com/assets/x/3.5cm_BiasTape.stl?ofn=abc"
        )
        == "3.5cm_BiasTape.stl"
    )


def test_probe_remote_filename_uses_redirect_location() -> None:
    mock_resp = MagicMock()
    mock_resp.headers = {
        "location": "https://cdn.example.com/files/bracket.stl?x=1",
    }
    mock_resp.url = "https://www.thingiverse.com/download:1"
    mock_resp.status_code = 302

    with patch("src.core.utils.remote_file_hint.httpx.Client") as client_cls:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        client.get.return_value = mock_resp
        client_cls.return_value = client

        assert (
            probe_remote_filename("https://www.thingiverse.com/download:1")
            == "bracket.stl"
        )


def test_enrich_resolves_thingiverse_download_to_stl() -> None:
    item = {
        "title": "Design Files 1",
        "path": "https://www.thingiverse.com/download:7851122",
        "type": "design-files",
        "metadata": {},
    }
    okh_id = UUID("4148beb6-0b55-4ba8-8dfd-9480f6523f26")

    with patch(
        "src.core.api.okh_file_urls.probe_remote_filename",
        return_value="3.5cm_BiasTape_minimalistic_Q2.stl",
    ):
        enriched = enrich_file_ref(item, "http://localhost:8001/v1/api", okh_id)

    assert enriched["file_type"] == "mesh_stl"
    assert enriched["file_type_display"] == "STL Mesh"
    assert enriched["display_path"] == "3.5cm_BiasTape_minimalistic_Q2.stl"
    assert enriched["url"] == item["path"]
