"""Helpers for OKH manifest file proxy URLs in API responses."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote
from uuid import UUID

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


def enrich_manifest_file_urls(
    manifest_dict: dict[str, Any], api_base: str, okh_id: UUID
) -> None:
    """Add ``url`` on each file ref so clients and probes get reachable links."""
    for field in OKH_FILE_FIELDS:
        items = manifest_dict.get(field) or []
        if not isinstance(items, list):
            continue
        enriched: list[Any] = []
        for item in items:
            if not isinstance(item, dict):
                enriched.append(item)
                continue
            path = str(item.get("path") or "").strip()
            next_item = dict(item)
            if path.startswith(("http://", "https://")):
                next_item.setdefault("url", path)
            elif path:
                next_item["url"] = build_okh_file_proxy_url(api_base, okh_id, path)
            enriched.append(next_item)
        manifest_dict[field] = enriched
