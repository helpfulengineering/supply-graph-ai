"""Cache key naming convention for shared backends."""

from __future__ import annotations


def namespaced_key(
    *,
    prefix: str,
    service: str,
    operation: str,
    key: str,
) -> str:
    """Build ``{prefix}:{service}:{operation}:{key}`` avoiding empty segments."""
    parts = [p.strip(":") for p in (prefix, service, operation, key) if p]
    return ":".join(parts)
