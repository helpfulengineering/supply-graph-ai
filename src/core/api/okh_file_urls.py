"""Helpers for OKH manifest file proxy URLs in API responses."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote
from uuid import UUID

from src.core.taxonomy.file_type_taxonomy import file_type_taxonomy
from src.core.utils.file_path_display import enrich_path_fields

OKH_FILE_FIELDS = (
    "design_files",
    "manufacturing_files",
    "making_instructions",
    "operating_instructions",
)


def build_okh_file_proxy_url(api_base: str, okh_id: UUID, relative_path: str) -> str:
    """Absolute API URL for GET /okh/{id}/files/{path}."""
    rel = relative_path.strip().lstrip("/")
    encoded = "/".join(quote(part, safe="") for part in rel.split("/") if part)
    return f"{api_base.rstrip('/')}/okh/{okh_id}/files/{encoded}"


def api_base_from_request(request) -> str:
    """Public /v1/api origin, honoring reverse-proxy forwarded scheme."""
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("host", request.url.netloc)
    return f"{scheme}://{host}/v1/api"


def enrich_file_ref(
    item: dict[str, Any], api_base: str, okh_id: UUID
) -> dict[str, Any]:
    """Add url, display_path, directory, file_type, render_tier, mime_type."""
    path = str(item.get("path") or "").strip()
    next_item = dict(item)
    if path.startswith(("http://", "https://")):
        next_item.setdefault("url", path)
    elif path:
        next_item["url"] = build_okh_file_proxy_url(api_base, okh_id, path)

    if path:
        path_fields = enrich_path_fields(path)
        next_item.update(path_fields)
        classification = file_type_taxonomy.classify(path)
        next_item["file_type"] = classification.file_type
        next_item["file_type_display"] = classification.display_name
        next_item["render_tier"] = classification.render_tier
        next_item["mime_type"] = classification.mime_type
        next_item["okh_role"] = classification.okh_role

    return next_item


def enrich_manifest_file_urls(
    manifest_dict: dict[str, Any], api_base: str, okh_id: UUID
) -> None:
    """Add enriched fields on each file ref for clients and probes."""
    for field in OKH_FILE_FIELDS:
        items = manifest_dict.get(field) or []
        if not isinstance(items, list):
            continue
        manifest_dict[field] = [
            enrich_file_ref(item, api_base, okh_id) if isinstance(item, dict) else item
            for item in items
        ]
