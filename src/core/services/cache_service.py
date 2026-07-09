"""
Cache service facade — unified API over pluggable backends.

Backends: ``memory`` (default, self-host single-node) and ``redis`` (multi-replica).
Configure via CACHE_BACKEND, CACHE_REDIS_URL, CACHE_KEY_PREFIX in settings.
"""

from __future__ import annotations

from typing import Any, Optional

from src.config.settings import (
    CACHE_BACKEND,
    CACHE_CLEANUP_INTERVAL,
    CACHE_ENABLED,
    CACHE_KEY_PREFIX,
    CACHE_MAX_SIZE,
    CACHE_REDIS_URL,
)

from ..cache.backends.memory import MemoryCacheBackend
from ..cache.backends.redis_backend import RedisCacheBackend
from ..utils.logging import get_logger

logger = get_logger(__name__)


def create_cache_backend():
    """Factory: select backend from settings."""
    backend_name = (CACHE_BACKEND or "memory").lower()
    if backend_name == "redis":
        if not CACHE_REDIS_URL:
            raise ValueError("CACHE_REDIS_URL is required when CACHE_BACKEND=redis")
        logger.info(
            "Initializing Redis cache backend (%s)",
            CACHE_REDIS_URL.split("@")[-1],
        )
        return RedisCacheBackend(CACHE_REDIS_URL)
    if backend_name != "memory":
        logger.warning("Unknown CACHE_BACKEND=%r; falling back to memory", backend_name)
    return MemoryCacheBackend(
        max_size=CACHE_MAX_SIZE,
        cleanup_interval_seconds=CACHE_CLEANUP_INTERVAL,
    )


class CacheService:
    """Application cache with hit/miss metrics and namespaced keys."""

    def __init__(self, backend=None, *, key_prefix: str = CACHE_KEY_PREFIX):
        self._backend = backend or create_cache_backend()
        self.key_prefix = key_prefix.strip(":")
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._deletes = 0

    @property
    def backend_name(self) -> str:
        return getattr(self._backend, "name", type(self._backend).__name__)

    def _full_key(self, key: str) -> str:
        if self.key_prefix and not key.startswith(f"{self.key_prefix}:"):
            return f"{self.key_prefix}:{key}"
        return key

    def get(self, key: str) -> Optional[Any]:
        if not CACHE_ENABLED:
            return None
        full_key = self._full_key(key)
        value = self._backend.get(full_key)
        if value is not None:
            self._hits += 1
        else:
            self._misses += 1
        return value

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        if not CACHE_ENABLED:
            return
        self._backend.set(self._full_key(key), value, ttl_seconds=ttl_seconds)
        self._sets += 1

    def delete(self, key: str) -> None:
        if not CACHE_ENABLED:
            return
        self._backend.delete(self._full_key(key))
        self._deletes += 1

    def clear(self) -> None:
        self._backend.clear()

    def get_stats(self) -> dict[str, Any]:
        extra = {}
        if hasattr(self._backend, "backend_stats"):
            extra = self._backend.backend_stats()
        return {
            "backend": self.backend_name,
            "enabled": CACHE_ENABLED,
            "hits": self._hits,
            "misses": self._misses,
            "sets": self._sets,
            "deletes": self._deletes,
            "key_prefix": self.key_prefix,
            "hit_rate": (
                round(self._hits / (self._hits + self._misses), 4)
                if (self._hits + self._misses)
                else None
            ),
            **extra,
        }


_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Return the process-wide cache service singleton."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


def reset_cache_service() -> None:
    """Reset singleton (tests only)."""
    global _cache_service
    _cache_service = None
