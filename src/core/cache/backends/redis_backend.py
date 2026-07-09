"""Redis-protocol cache backend (Redis, Valkey, Azure Cache for Redis, etc.)."""

from __future__ import annotations

import json
from typing import Any, Optional

from ...utils.logging import get_logger

logger = get_logger(__name__)


def _serialize(value: Any) -> bytes:
    return json.dumps(value, default=str).encode("utf-8")


def _deserialize(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"))


class RedisCacheBackend:
    """Distributed cache using the Redis protocol (sync client)."""

    name = "redis"

    def __init__(self, redis_url: str, *, socket_timeout: float = 5.0):
        try:
            import redis
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "redis package is required when CACHE_BACKEND=redis. "
                "Install with: uv sync"
            ) from exc

        self._client = redis.from_url(
            redis_url,
            decode_responses=False,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_timeout,
        )
        self._redis_url_host = redis_url.split("@")[-1].split("/")[0]

    def get(self, key: str) -> Optional[Any]:
        try:
            raw = self._client.get(key)
        except Exception as exc:
            logger.warning("Redis cache get failed for %s: %s", key, exc)
            return None
        if raw is None:
            return None
        try:
            return _deserialize(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("Redis cache deserialize failed for %s: %s", key, exc)
            self.delete(key)
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        try:
            payload = _serialize(value)
            self._client.setex(key, ttl_seconds, payload)
        except Exception as exc:
            logger.warning("Redis cache set failed for %s: %s", key, exc)

    def delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except Exception as exc:
            logger.warning("Redis cache delete failed for %s: %s", key, exc)

    def clear(self) -> None:
        try:
            self._client.flushdb()
        except Exception as exc:
            logger.warning("Redis cache clear failed: %s", exc)

    def backend_stats(self) -> dict[str, Any]:
        try:
            info = self._client.info("stats")
            keyspace = self._client.info("keyspace")
            db_keys = 0
            for _db, meta in (keyspace or {}).items():
                if isinstance(meta, dict):
                    db_keys += int(meta.get("keys", 0))
            return {
                "redis_host": self._redis_url_host,
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "keys": db_keys,
            }
        except Exception as exc:
            return {"redis_host": self._redis_url_host, "error": str(exc)}
