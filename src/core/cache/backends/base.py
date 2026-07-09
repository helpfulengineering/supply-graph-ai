"""Cache backend protocol — shared by memory and Redis implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


@dataclass
class CacheStats:
    """Aggregate cache statistics (hits/misses tracked by CacheService)."""

    backend: str
    enabled: bool
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    key_prefix: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "backend": self.backend,
            "enabled": self.enabled,
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "key_prefix": self.key_prefix,
            "hit_rate": (
                round(self.hits / (self.hits + self.misses), 4)
                if (self.hits + self.misses)
                else None
            ),
        }
        payload.update(self.extra)
        return payload


class CacheBackend(Protocol):
    """Pluggable cache store (memory, Redis/Valkey, etc.)."""

    @property
    def name(self) -> str:
        """Backend identifier, e.g. ``memory`` or ``redis``."""
        ...

    def get(self, key: str) -> Optional[Any]:
        """Return cached value or ``None`` on miss/expiry."""
        ...

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Store a value with TTL."""
        ...

    def delete(self, key: str) -> None:
        """Remove one key."""
        ...

    def clear(self) -> None:
        """Clear all keys for this backend/prefix."""
        ...

    def backend_stats(self) -> dict[str, Any]:
        """Backend-specific stats (size, connection, etc.)."""
        ...
