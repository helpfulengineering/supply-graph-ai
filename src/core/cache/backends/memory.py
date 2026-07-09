"""In-process LRU cache backend (default for single-node / dev)."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Optional

from ...utils.logging import get_logger

logger = get_logger(__name__)


class _CacheEntry:
    def __init__(self, value: Any, ttl_seconds: int):
        self.value = value
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)

    def is_expired(self) -> bool:
        return datetime.now() >= self.expires_at


class MemoryCacheBackend:
    """Thread-safe in-memory LRU cache with TTL."""

    name = "memory"

    def __init__(self, max_size: int = 1000, cleanup_interval_seconds: int = 60):
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval_seconds
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._last_cleanup = datetime.now()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            self._cleanup_if_needed()
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return entry.value

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        with self._lock:
            self._cleanup_if_needed()
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._cache.popitem(last=False)
            self._cache[key] = _CacheEntry(value, ttl_seconds)
            self._cache.move_to_end(key)

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def _cleanup_if_needed(self) -> None:
        now = datetime.now()
        if (now - self._last_cleanup).total_seconds() < self.cleanup_interval:
            return
        expired = [k for k, e in self._cache.items() if e.is_expired()]
        for key in expired:
            del self._cache[key]
        self._last_cleanup = now
        if expired:
            logger.debug("Memory cache cleaned %s expired entries", len(expired))

    def backend_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
            }
