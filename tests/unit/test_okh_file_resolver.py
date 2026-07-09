"""Unit tests for OKH manifest file resolution (#272)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.core.api.okh_file_urls import (
    build_okh_file_proxy_url,
    enrich_manifest_file_urls,
)
from src.core.services.okh_file_resolver import (
    OkhFileNotFoundError,
    candidate_storage_keys,
    content_disposition,
    is_inline_media_type,
    normalize_manifest_file_path,
    resolve_okh_file_bytes,
)


def test_normalize_manifest_file_path_rejects_traversal():
    with pytest.raises(ValueError):
        normalize_manifest_file_path("../secret.pdf")


def test_candidate_storage_keys_includes_manifest_parent():
    mid = UUID("123e4567-e89b-12d3-a456-426614174000")
    keys = candidate_storage_keys(mid, "okh/widget-123e4567-okh.json", "docs/plan.pdf")
    assert "okh/widget-123e4567-okh/docs/plan.pdf" in keys
    assert "okh/123e4567-e89b-12d3-a456-426614174000/docs/plan.pdf" in keys


def test_build_okh_file_proxy_url_encodes_segments():
    mid = UUID("123e4567-e89b-12d3-a456-426614174000")
    url = build_okh_file_proxy_url(
        "https://example.com/v1/api", mid, "images/a file.pdf"
    )
    assert url == (
        "https://example.com/v1/api/okh/"
        "123e4567-e89b-12d3-a456-426614174000/files/images/a%20file.pdf"
    )


def test_enrich_manifest_file_urls_adds_proxy_links():
    mid = UUID("123e4567-e89b-12d3-a456-426614174000")
    manifest = {
        "design_files": [{"title": "Plan", "path": "docs/plan.pdf", "type": "design"}],
        "manufacturing_files": [
            {"title": "Remote", "path": "https://example.com/x.pdf", "type": "mfg"}
        ],
    }
    enrich_manifest_file_urls(manifest, "https://host/v1/api", mid)
    assert manifest["design_files"][0]["url"].endswith("/files/docs/plan.pdf")
    assert manifest["manufacturing_files"][0]["url"] == "https://example.com/x.pdf"


def test_content_disposition_inline_vs_attachment():
    assert "inline" in content_disposition("a.pdf", inline=True)
    assert "attachment" in content_disposition("part.stl", inline=False)


def test_is_inline_media_type():
    assert is_inline_media_type("image/png")
    assert is_inline_media_type("application/pdf")
    assert not is_inline_media_type("model/stl")


@pytest.mark.asyncio
async def test_resolve_okh_file_bytes_from_storage():
    mid = UUID("123e4567-e89b-12d3-a456-426614174000")
    manifest = MagicMock()
    manifest.repo = None
    okh_service = MagicMock()
    okh_service.ensure_initialized = AsyncMock()
    okh_service.get = AsyncMock(return_value=manifest)
    okh_service._find_key_for_id = AsyncMock(return_value="okh/test-okh.json")
    okh_service.storage.manager.get_object = AsyncMock(
        side_effect=[FileNotFoundError(), b"%PDF-1.4"]
    )

    data, media_type, name = await resolve_okh_file_bytes(
        okh_service, mid, "docs/plan.pdf"
    )
    assert data.startswith(b"%PDF")
    assert media_type == "application/pdf"
    assert name == "plan.pdf"


@pytest.mark.asyncio
async def test_resolve_okh_file_bytes_missing_raises():
    mid = UUID("123e4567-e89b-12d3-a456-426614174000")
    manifest = MagicMock()
    manifest.repo = "https://github.com/org/repo"
    okh_service = MagicMock()
    okh_service.ensure_initialized = AsyncMock()
    okh_service.get = AsyncMock(return_value=manifest)
    okh_service._find_key_for_id = AsyncMock(return_value=None)
    okh_service.storage.manager.get_object = AsyncMock(side_effect=FileNotFoundError())

    with patch(
        "src.core.services.okh_file_resolver.resolve_repo_relative_file_url",
        return_value="docs/plan.pdf",
    ):
        with pytest.raises(OkhFileNotFoundError):
            await resolve_okh_file_bytes(okh_service, mid, "docs/plan.pdf")
