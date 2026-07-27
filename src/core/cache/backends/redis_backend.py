"""Redis-protocol cache backend (Redis, Valkey, Azure Cache for Redis, etc.)."""

from __future__ import annotations

import json
from typing import Any, Optional

from ...utils.logging import get_logger

logger = get_logger(__name__)

# The client is synchronous but is called from async request handlers, so every
# operation blocks the event loop for its duration. redis-py defaults to 5s,
# which would stall a worker far longer than the catalogue assembly this cache
# exists to avoid. A lookup slower than this has lost its reason to exist.
SOCKET_TIMEOUT_SECONDS = 0.5


def _serialize(value: Any) -> bytes:
    return json.dumps(value, default=str).encode("utf-8")


def _deserialize(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"))


class RedisCacheBackend:
    """Distributed cache using the Redis protocol (sync client).

    Every operation falls through to a miss on failure: a broken cache costs
    speed, not availability.
    """

    name = "redis"

    def __init__(self, redis_url: str):
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
            socket_timeout=SOCKET_TIMEOUT_SECONDS,
            socket_connect_timeout=SOCKET_TIMEOUT_SECONDS,
        )
        self._redis_url_host = redis_url.split("@")[-1].split("/")[0]

    def is_reachable(self) -> tuple[bool, Optional[str]]:
        """``(ok, error)`` from a single PING.

        Every other operation swallows its failure and reports a miss, which
        makes an unusable Redis indistinguishable from a cold one: it caches
        nothing, forever, while looking healthy. Production hit exactly that —
        a connection URL whose ``<key>`` placeholder was never substituted
        authenticated as the literal string, and every request paid full
        assembly with no cache at all. The factory calls this once so a broken
        Redis degrades to the memory cache instead.
        """
        try:
            self._client.ping()
            return True, None
        except Exception as exc:  # noqa: BLE001 — any failure means unusable
            return False, str(exc)

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
