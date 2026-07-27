"""The OKH catalogue is assembled concurrently and cached.

Rendering the Designs page cost ~15s because ``OKHService.list`` fetched every
OKH object from blob storage one at a time — 287 objects in production — and
applied pagination only afterwards, so each page repeated the whole scan.

These tests pin the two properties that fix it, and the dedup semantics that
must survive the change.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from src.core.services.okh_service import CATALOG_FETCH_CONCURRENCY, OKHService
from src.core.storage.smart_discovery import FileInfo


def manifest_dict(manifest_id: str, title: str = "Design") -> dict:
    """The minimum shape OKHService.list accepts as a manifest."""
    return {
        "id": manifest_id,
        "title": title,
        "version": "1.0.0",
        "license": {"hardware": "MIT"},
        "licensor": {"name": "Someone"},
        "documentation_language": "en",
        "function": "Does a thing",
    }


class FakeStorageManager:
    """Records concurrency and can simulate per-object latency."""

    def __init__(self, objects: dict[str, dict], latency: float = 0.0):
        self.objects = objects
        self.latency = latency
        self.in_flight = 0
        self.max_in_flight = 0
        self.get_calls = 0

    async def get_object(self, key: str) -> bytes:
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        self.get_calls += 1
        try:
            if self.latency:
                await asyncio.sleep(self.latency)
            return json.dumps(self.objects[key]).encode("utf-8")
        finally:
            self.in_flight -= 1


class FakeStorage:
    def __init__(self, manager):
        self.manager = manager


def file_info(key: str, minutes_old: int = 0) -> FileInfo:
    return FileInfo(
        key=key,
        file_type="okh",
        size=100,
        last_modified=datetime(2026, 1, 1) - timedelta(minutes=minutes_old),
        metadata={},
    )


def build_service(objects, latency=0.0):
    service = OKHService()
    manager = FakeStorageManager(objects, latency=latency)
    service.storage = FakeStorage(manager)
    service._initialized = True
    return service, manager


async def run_list(service, keys, **kwargs):
    """Call list() with discovery stubbed to the given keys."""

    async def fake_discover(_prefix):
        return keys

    with (
        patch("src.core.services.okh_service.SmartFileDiscovery") as Discovery,
        patch.object(service, "ensure_initialized", return_value=None),
    ):
        Discovery.return_value.discover_files = fake_discover
        return await service.list(**kwargs)


@pytest.fixture(autouse=True)
def _isolate_cache():
    """Each test starts with an empty catalogue cache."""
    from src.core.services.cache_service import get_cache_service

    get_cache_service().clear()
    yield
    get_cache_service().clear()


@pytest.mark.asyncio
class TestConcurrency:
    async def test_objects_are_fetched_concurrently(self):
        ids = [str(uuid4()) for _ in range(40)]
        objects = {f"okh/{i}.json": manifest_dict(i) for i in ids}
        service, manager = build_service(objects, latency=0.01)

        await run_list(service, [file_info(k) for k in objects])

        assert manager.get_calls == 40
        # The point of the change: reads overlap instead of queueing one deep.
        assert manager.max_in_flight > 1

    async def test_concurrency_is_bounded(self):
        """Unbounded fan-out would exhaust the storage client's connections."""
        ids = [str(uuid4()) for _ in range(60)]
        objects = {f"okh/{i}.json": manifest_dict(i) for i in ids}
        service, manager = build_service(objects, latency=0.01)

        await run_list(service, [file_info(k) for k in objects])

        assert manager.max_in_flight <= CATALOG_FETCH_CONCURRENCY


@pytest.mark.asyncio
class TestCaching:
    async def test_second_page_does_not_rescan_storage(self):
        """Pagination happens after assembly, so page 2 used to repeat it all."""
        ids = [str(uuid4()) for _ in range(30)]
        objects = {f"okh/{i}.json": manifest_dict(i) for i in ids}
        service, manager = build_service(objects)
        keys = [file_info(k) for k in objects]

        await run_list(service, keys, page=1, page_size=10)
        after_first = manager.get_calls
        await run_list(service, keys, page=2, page_size=10)

        assert after_first == 30
        assert manager.get_calls == 30, "second page refetched every object"

    async def test_a_write_invalidates_the_catalogue(self):
        ids = [str(uuid4()) for _ in range(5)]
        objects = {f"okh/{i}.json": manifest_dict(i) for i in ids}
        service, manager = build_service(objects)
        keys = [file_info(k) for k in objects]

        await run_list(service, keys)
        service._invalidate_catalog_cache()
        await run_list(service, keys)

        # Otherwise a design someone just created stays invisible until the TTL.
        assert manager.get_calls == 10


@pytest.mark.asyncio
class TestSemanticsPreserved:
    async def test_paginates_and_totals_correctly(self):
        ids = [str(uuid4()) for _ in range(25)]
        objects = {f"okh/{i}.json": manifest_dict(i) for i in ids}
        service, _ = build_service(objects)

        page, total = await run_list(
            service, [file_info(k) for k in objects], page=2, page_size=10
        )

        assert total == 25
        assert len(page) == 10

    async def test_duplicate_ids_keep_the_newest_file(self):
        shared = str(uuid4())
        objects = {
            "okh/old.json": manifest_dict(shared, title="Old"),
            "okh/new.json": manifest_dict(shared, title="New"),
        }
        service, _ = build_service(objects)

        page, total = await run_list(
            service,
            [file_info("okh/old.json", minutes_old=60), file_info("okh/new.json")],
        )

        assert total == 1
        assert page[0].title == "New"

    async def test_unusable_objects_are_skipped_not_fatal(self):
        good = str(uuid4())
        objects = {
            "okh/good.json": manifest_dict(good),
            "okh/bom.json": {"components": []},  # a BOM sidecar, not a manifest
        }
        service, _ = build_service(objects)

        page, total = await run_list(
            service, [file_info("okh/good.json"), file_info("okh/bom.json")]
        )

        assert total == 1
        assert str(page[0].id) == good


@pytest.mark.asyncio
class TestSingleFetch:
    """get() and _find_key_for_id answered from the catalogue, not a scan.

    Both previously read objects one at a time until the id matched, so cost
    grew with the record's position in storage — ~3.3s in production for a 3KB
    manifest.
    """

    async def test_get_is_answered_from_the_cached_catalogue(self):
        ids = [str(uuid4()) for _ in range(30)]
        objects = {f"okh/{i}.json": manifest_dict(i) for i in ids}
        service, manager = build_service(objects)
        keys = [file_info(k) for k in objects]

        await run_list(service, keys)  # warms the catalogue
        reads_after_list = manager.get_calls

        async def fake_discover(_prefix):
            return keys

        with (
            patch("src.core.services.okh_service.SmartFileDiscovery") as Discovery,
            patch.object(service, "ensure_initialized", return_value=None),
        ):
            Discovery.return_value.discover_files = fake_discover
            # The last id is the worst case for a positional scan.
            found = await service.get(UUID(ids[-1]))

        assert found is not None
        assert str(found.id) == ids[-1]
        assert manager.get_calls == reads_after_list, "get() re-read storage"

    async def test_find_key_is_answered_from_the_cached_catalogue(self):
        target = str(uuid4())
        objects = {
            "okh/other.json": manifest_dict(str(uuid4())),
            "okh/target.json": manifest_dict(target),
        }
        service, manager = build_service(objects)
        keys = [file_info(k) for k in objects]

        await run_list(service, keys)
        reads_after_list = manager.get_calls

        with (
            patch("src.core.services.okh_service.SmartFileDiscovery") as Discovery,
            patch.object(service, "ensure_initialized", return_value=None),
        ):
            Discovery.return_value.discover_files = lambda _p: _aslist(keys)
            key = await service._find_key_for_id(UUID(target), "okh")

        assert key == "okh/target.json"
        assert manager.get_calls == reads_after_list

    async def test_get_falls_back_to_scanning_for_uncatalogued_objects(self):
        """The catalogue skips non-minimal manifests; get() never did."""
        catalogued = str(uuid4())
        objects = {"okh/good.json": manifest_dict(catalogued)}
        service, manager = build_service(objects)

        # A record that exists in storage but is absent from the catalogue.
        missing = str(uuid4())
        objects["okh/extra.json"] = manifest_dict(missing)
        keys = [file_info("okh/good.json"), file_info("okh/extra.json")]

        async def fake_discover(_prefix):
            return keys

        with (
            patch("src.core.services.okh_service.SmartFileDiscovery") as Discovery,
            patch.object(service, "ensure_initialized", return_value=None),
        ):
            Discovery.return_value.discover_files = fake_discover
            found = await service.get(UUID(missing))

        assert found is not None, "fallback scan should still find it"
        assert str(found.id) == missing


async def _aslist(values):
    return values
