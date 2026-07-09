"""Service-level cache helper using the shared CacheService backend."""

from __future__ import annotations

from typing import Awaitable, Callable, TypeVar

from .keys import namespaced_key

T = TypeVar("T")


async def cached(
    *,
    service: str,
    operation: str,
    key: str,
    ttl_seconds: int,
    loader: Callable[[], Awaitable[T]],
) -> T:
    """Load ``loader`` once per TTL, sharing the configured cache backend.

    Example::

        manifest = await cached(
            service="okh",
            operation="get",
            key=str(okh_id),
            ttl_seconds=300,
            loader=lambda: self._load_manifest(okh_id),
        )
    """
    from ..services.cache_service import get_cache_service

    cache = get_cache_service()
    cache_key = namespaced_key(
        prefix=cache.key_prefix,
        service=service,
        operation=operation,
        key=key,
    )
    hit = cache.get(cache_key)
    if hit is not None:
        return hit
    result = await loader()
    cache.set(cache_key, result, ttl_seconds=ttl_seconds)
    return result
