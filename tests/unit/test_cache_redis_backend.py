"""The Redis cache backend, and what switching to it must not break.

``CACHE_BACKEND=redis`` exists so the OKH catalogue cache is shared across
replicas: with the memory backend each instance warms its own copy, so a
request landing on a cold replica pays a full assembly and scaling out
re-introduces the slow path.

Switching backends changes two things that these tests pin: cached values now
make a round trip through JSON, and a cache lookup now makes a network call
from inside an async request handler.
"""

from __future__ import annotations

import json
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.core.cache.backends.redis_backend import (
    RedisCacheBackend,
    _deserialize,
    _serialize,
)


class FakeRedis:
    """Enough of redis-py to exercise the backend, with failure injection."""

    def __init__(self, *, fail: bool = False):
        self.store: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}
        self.fail = fail

    def _boom(self):
        if self.fail:
            raise ConnectionError("connection refused")

    def get(self, key):
        self._boom()
        return self.store.get(key)

    def setex(self, key, ttl, payload):
        self._boom()
        self.store[key] = payload
        self.ttls[key] = ttl

    def delete(self, key):
        self._boom()
        self.store.pop(key, None)

    def flushdb(self):
        self._boom()
        self.store.clear()


def build_backend(**kwargs) -> tuple[RedisCacheBackend, FakeRedis]:
    fake = FakeRedis(**kwargs)
    with patch("redis.from_url", return_value=fake):
        backend = RedisCacheBackend("redis://user:pw@cache.example:6379/0")
    return backend, fake


class TestRoundTrip:
    def test_stores_and_returns_the_value(self):
        backend, _ = build_backend()
        backend.set("k", {"a": [1, 2]}, ttl_seconds=60)
        assert backend.get("k") == {"a": [1, 2]}

    def test_absent_key_is_a_miss(self):
        backend, _ = build_backend()
        assert backend.get("nope") is None

    def test_the_ttl_is_applied(self):
        """Without a TTL a stale catalogue would outlive its invalidation."""
        backend, fake = build_backend()
        backend.set("k", 1, ttl_seconds=120)
        assert fake.ttls["k"] == 120

    def test_the_catalogue_entry_shape_survives_serialisation(self):
        """What list()/get() cache must come back byte-identical.

        The catalogue is cached as plain dicts precisely so this holds; caching
        OKHManifest objects would not survive the JSON round trip.
        """
        entries = [
            {
                "key": "okh/a.json",
                "manifest": {
                    "id": str(uuid4()),
                    "title": "Design",
                    "version": "1.0.0",
                    "license": {"hardware": "MIT"},
                    "licensor": {"name": "Someone"},
                    "documentation_language": "en",
                    "function": "Does a thing",
                },
            }
        ]
        assert _deserialize(_serialize(entries)) == entries


class TestDegradesInsteadOfFailing:
    """A broken cache must cost speed, not availability."""

    def test_get_returns_a_miss_when_redis_is_unreachable(self):
        backend, _ = build_backend(fail=True)
        assert backend.get("k") is None

    def test_set_swallows_the_failure(self):
        backend, _ = build_backend(fail=True)
        backend.set("k", {"a": 1}, ttl_seconds=60)  # must not raise

    def test_delete_swallows_the_failure(self):
        backend, _ = build_backend(fail=True)
        backend.delete("k")  # must not raise

    def test_corrupt_payload_is_a_miss_and_is_evicted(self):
        backend, fake = build_backend()
        fake.store["k"] = b"{not json"
        assert backend.get("k") is None
        assert "k" not in fake.store, "poisoned key would miss forever"

    def test_the_socket_timeout_is_sub_second(self):
        """The client is sync and blocks the event loop for its duration.

        redis-py defaults to 5s, which would stall a worker far longer than the
        ~1.6s assembly this cache exists to avoid.
        """
        with patch("redis.from_url") as from_url:
            RedisCacheBackend("redis://cache.example:6379/0")
        kwargs = from_url.call_args.kwargs
        assert kwargs["socket_timeout"] <= 1.0
        assert kwargs["socket_connect_timeout"] <= 1.0

    def test_stats_do_not_leak_the_credentials(self):
        backend, _ = build_backend()
        assert "pw" not in json.dumps(backend.backend_stats())


class TestBackendSelection:
    def test_redis_without_a_url_degrades_to_memory(self):
        """CACHE_BACKEND is plain config; CACHE_REDIS_URL is a secretRef.

        Different mechanisms apply them, so a deploy can land one before the
        other. That must not 500 every cached path.
        """
        from src.core.services import cache_service

        with (
            patch.object(cache_service, "CACHE_BACKEND", "redis"),
            patch.object(cache_service, "CACHE_REDIS_URL", None),
        ):
            backend = cache_service.create_cache_backend()

        assert backend.name == "memory"

    def test_redis_with_a_url_selects_redis(self):
        from src.core.services import cache_service

        with (
            patch.object(cache_service, "CACHE_BACKEND", "redis"),
            patch.object(
                cache_service, "CACHE_REDIS_URL", "redis://cache.example:6379/0"
            ),
            patch("redis.from_url", return_value=FakeRedis()),
        ):
            backend = cache_service.create_cache_backend()

        assert backend.name == "redis"

    def test_an_unknown_backend_falls_back_to_memory(self):
        from src.core.services import cache_service

        with patch.object(cache_service, "CACHE_BACKEND", "memcached"):
            assert cache_service.create_cache_backend().name == "memory"


@pytest.mark.asyncio
async def test_the_catalogue_is_shared_between_replicas():
    """The point of the change, end to end.

    Two service instances backed by one Redis: the second must answer from the
    first's assembly rather than re-reading storage.
    """
    from src.core.cache.helper import cached
    from src.core.services.cache_service import CacheService

    shared = FakeRedis()
    with patch("redis.from_url", return_value=shared):
        replica_a = CacheService(RedisCacheBackend("redis://cache.example:6379/0"))
        replica_b = CacheService(RedisCacheBackend("redis://cache.example:6379/0"))

    assemblies = 0

    async def assemble():
        nonlocal assemblies
        assemblies += 1
        return [{"key": "okh/a.json", "manifest": {"id": "x", "title": "Design"}}]

    async def read(service):
        with patch(
            "src.core.services.cache_service.get_cache_service", return_value=service
        ):
            return await cached(
                service="okh",
                operation="catalog",
                key="all",
                ttl_seconds=120,
                loader=assemble,
            )

    first = await read(replica_a)
    second = await read(replica_b)

    assert first == second
    assert assemblies == 1, "the second replica re-assembled the catalogue"
