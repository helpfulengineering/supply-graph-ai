"""Resolve OKH manifest file references to bytes via storage or source repo."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Optional
from uuid import UUID

import httpx

from ..packaging.repo_file_urls import resolve_repo_relative_file_url
from ..taxonomy.file_type_taxonomy import file_type_taxonomy
from ..utils.logging import get_logger
from .okh_service import OKHService

logger = get_logger(__name__)


class OkhFileNotFoundError(FileNotFoundError):
    """Manifest file ref could not be resolved to content."""


def normalize_manifest_file_path(path: str) -> str:
    """Reject traversal; return a posix-relative path segment."""
    raw = (path or "").strip().replace("\\", "/").lstrip("/")
    if not raw:
        raise ValueError("file path is required")
    parts = PurePosixPath(raw).parts
    if ".." in parts:
        raise ValueError("invalid file path")
    return "/".join(parts)


def candidate_storage_keys(
    manifest_id: UUID, manifest_key: Optional[str], relative_path: str
) -> list[str]:
    """Ordered storage object keys to try for a manifest-relative file path."""
    rel = normalize_manifest_file_path(relative_path)
    keys = [
        f"okh/{manifest_id}/{rel}",
        f"okh/files/{manifest_id}/{rel}",
        f"okh/{rel}",
    ]
    if manifest_key:
        if "/" in manifest_key:
            keys.insert(0, f"{manifest_key.rsplit('/', 1)[0]}/{rel}")
        stem = manifest_key.rsplit(".", 1)[0] if "." in manifest_key else manifest_key
        keys.insert(0, f"{stem}/{rel}")
    return list(dict.fromkeys(keys))


def guess_media_type(path: str, content: Optional[bytes] = None) -> str:
    return file_type_taxonomy.guess_mime_type(path, content)


def content_disposition(filename: str, *, inline: bool) -> str:
    safe_name = PurePosixPath(filename).name or "download"
    disposition = "inline" if inline else "attachment"
    return f'{disposition}; filename="{safe_name}"'


def is_inline_media_type(media_type: str) -> bool:
    if media_type.startswith("image/"):
        return True
    if media_type in {
        "application/pdf",
        "text/plain",
        "text/markdown",
        "text/html",
        "text/csv",
        "application/json",
    }:
        return True
    return False


async def resolve_okh_file_bytes(
    okh_service: OKHService,
    manifest_id: UUID,
    relative_path: str,
    *,
    timeout_seconds: float = 30.0,
) -> tuple[bytes, str, str]:
    """
    Load file bytes for a manifest attachment.

    Returns:
        Tuple of (content, media_type, filename basename).
    """
    await okh_service.ensure_initialized()
    rel = normalize_manifest_file_path(relative_path)
    manifest = await okh_service.get(manifest_id)
    if not manifest:
        raise OkhFileNotFoundError(f"OKH manifest {manifest_id} not found")

    if rel.startswith(("http://", "https://")):
        return await _fetch_url(
            rel, rel.split("/")[-1], timeout_seconds=timeout_seconds
        )

    storage = okh_service.storage
    if storage and storage.manager:
        manifest_key = await okh_service._find_key_for_id(manifest_id, "okh")
        for key in candidate_storage_keys(manifest_id, manifest_key, rel):
            try:
                data = await storage.manager.get_object(key)
                media_type = guess_media_type(rel, data)
                return data, media_type, PurePosixPath(rel).name
            except FileNotFoundError:
                continue
            except Exception as exc:
                logger.debug("Storage lookup failed for %s: %s", key, exc)

    if manifest.repo:
        raw_url = resolve_repo_relative_file_url(manifest.repo, rel)
        if raw_url.startswith(("http://", "https://")) and raw_url != rel:
            try:
                return await _fetch_url(
                    raw_url, PurePosixPath(rel).name, timeout_seconds=timeout_seconds
                )
            except OkhFileNotFoundError:
                logger.debug("Repo fetch failed for %s via %s", rel, raw_url)

    raise OkhFileNotFoundError(f"File not found for OKH {manifest_id}: {rel}")


async def _fetch_url(
    url: str, filename: str, *, timeout_seconds: float
) -> tuple[bytes, str, str]:
    async with httpx.AsyncClient(
        timeout=timeout_seconds, follow_redirects=True
    ) as client:
        response = await client.get(url)
        if response.status_code == 404:
            raise OkhFileNotFoundError(f"File not found at {url}")
        response.raise_for_status()
        media_type = response.headers.get("content-type", "").split(";")[0].strip()
        if not media_type:
            media_type = guess_media_type(filename, response.content)
        return response.content, media_type, filename
