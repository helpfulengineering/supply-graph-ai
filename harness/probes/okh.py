"""OKH list/detail helpers for production probes."""

from __future__ import annotations

from typing import Any


def first_okh_id_from_list_body(body: Any) -> str | None:
    """Extract the first OKH id from a paginated list response."""
    if not isinstance(body, dict):
        return None

    items = body.get("items")
    if not isinstance(items, list):
        data = body.get("data")
        if isinstance(data, dict):
            items = data.get("items") or data.get("manifests") or data.get("results")

    if not isinstance(items, list) or not items:
        return None

    first = items[0]
    if not isinstance(first, dict):
        return None
    okh_id = first.get("id") or first.get("okh_id")
    return str(okh_id) if okh_id else None
