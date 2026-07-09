"""Unit tests for unified cache backends and CacheService (#271)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.cache.backends.memory import MemoryCacheBackend
from src.core.cache.backends.redis_backend import RedisCacheBackend
from src.core.cache.helper import cached
from src.core.cache.keys import namespaced_key
from src.core.services.cache_service import CacheService, reset_cache_service

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_cache_service()
    yield
    reset_cache_service()


def test_namespaced_key_builds_colon_separated_path():
    assert (
        namespaced_key(prefix="ohm", service="okh", operation="list", key="p1")
        == "ohm:okh:list:p1"
    )


def test_memory_backend_lru_eviction():
    backend = MemoryCacheBackend(max_size=2, cleanup_interval_seconds=3600)
    backend.set("a", 1, ttl_seconds=300)
    backend.set("b", 2, ttl_seconds=300)
    backend.set("c", 3, ttl_seconds=300)
    assert backend.get("a") is None
    assert backend.get("b") == 2
    assert backend.get("c") == 3


def test_memory_backend_expiry():
    backend = MemoryCacheBackend(max_size=10, cleanup_interval_seconds=0)
    backend.set("k", "v", ttl_seconds=0)
    assert backend.get("k") is None


def test_redis_backend_get_set_roundtrip():
    store: dict[str, bytes] = {}

    mock_client = MagicMock()

    def setex(key, ttl, value):
        store[key] = value

    def get(key):
        return store.get(key)

    mock_client.setex = setex
    mock_client.get = get
    mock_client.delete = lambda key: store.pop(key, None)
    mock_client.flushdb = store.clear
    mock_client.info = lambda section=None: {"keyspace_hits": 1, "keyspace_misses": 0}

    backend = RedisCacheBackend.__new__(RedisCacheBackend)
    backend._client = mock_client
    backend._redis_url_host = "localhost:6379"

    backend.set("domains:x", {"status": "ok"}, ttl_seconds=60)
    assert backend.get("domains:x") == {"status": "ok"}


def test_cache_service_tracks_hits_and_misses():
    backend = MemoryCacheBackend(max_size=10)
    cache = CacheService(backend=backend, key_prefix="ohm")
    assert cache.get("missing") is None
    cache.set("k", {"v": 1}, ttl_seconds=60)
    assert cache.get("k") == {"v": 1}
    stats = cache.get_stats()
    assert stats["backend"] == "memory"
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["enabled"] is True


def test_cache_service_respects_cache_enabled_false():
    backend = MemoryCacheBackend(max_size=10)
    cache = CacheService(backend=backend, key_prefix="ohm")
    with patch("src.core.services.cache_service.CACHE_ENABLED", False):
        cache.set("k", 1, ttl_seconds=60)
        assert cache.get("k") is None
        stats = cache.get_stats()
        assert stats["enabled"] is False


def test_cached_helper_uses_shared_service():
    import asyncio

    calls = {"n": 0}

    async def loader():
        calls["n"] += 1
        return {"items": [1]}

    async def run():
        with patch("src.core.services.cache_service.get_cache_service") as mock_get:
            backend = MemoryCacheBackend(max_size=10)
            svc = CacheService(backend=backend, key_prefix="ohm")
            mock_get.return_value = svc

            first = await cached(
                service="okh",
                operation="list",
                key="page1",
                ttl_seconds=60,
                loader=loader,
            )
            second = await cached(
                service="okh",
                operation="list",
                key="page1",
                ttl_seconds=60,
                loader=loader,
            )
        assert first == {"items": [1]}
        assert second == {"items": [1]}
        assert calls["n"] == 1

    asyncio.run(run())


def test_create_cache_backend_redis_requires_url():
    from src.core.services.cache_service import create_cache_backend

    with (
        patch("src.core.services.cache_service.CACHE_BACKEND", "redis"),
        patch("src.core.services.cache_service.CACHE_REDIS_URL", None),
    ):
        with pytest.raises(ValueError, match="CACHE_REDIS_URL"):
            create_cache_backend()
