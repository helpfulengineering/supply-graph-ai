"""A freshly scaffolded store is empty, and every reader must agree.

Scaffolding writes a `.gitkeep` placeholder under each top-level prefix so the
directory exists in blob storage, and labels it: `file-type: directory_placeholder`.
Most readers then ignored the label. On a node with nothing in it, `/health`
reported `okh_count: 1, okw_count: 1`, the OKW listing returned one record with
a UUID and an empty name, and the OKH listing said 0 — the same placeholder
counted as an object by three of four readers. The federation catalogue builder
found it too (`Found 1 OKH files using smart discovery`), so an empty node
advertised a design it did not have.

The README advertises `/health`'s counts as a feature, and dashboards rely on
them.

`OKHService.list` is the control: it already reported 0 (it rejects anything
without an OKH manifest's shape), so it passes before and after, and shows the
test's "empty" is really empty.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from src.core.services.base import ServiceStatus
from src.core.services.okh_service import OKHService
from src.core.services.okw_service import OKWService
from src.core.services.storage_service import StorageService
from src.core.storage.base import StorageConfig
from src.core.storage.manager import StorageManager
from src.core.storage.organizer import StorageOrganizer
from src.core.storage.placeholders import is_scaffold_placeholder
from src.core.storage.smart_discovery import SmartFileDiscovery

pytestmark = pytest.mark.unit


@pytest_asyncio.fixture
async def fresh_node(tmp_path):
    """A storage service over a store scaffolded the way a new node scaffolds it."""
    config = StorageConfig(provider="local", bucket_name=str(tmp_path))
    service = StorageService()
    await service.configure(config)
    assert service._configured, "the local store did not connect"
    await StorageOrganizer(service.manager).create_directory_structure()
    return service


def _service_over(service_class, storage: StorageService):
    """A domain service that reads `storage` and nothing else.

    `ensure_initialized()` looks at `status`, and when it is UNINITIALIZED it
    replaces `.storage` with the process-wide `StorageService` singleton, which
    points at the default `storage/` directory. Setting `.storage` alone therefore
    tests whatever that directory has accumulated, not the store built here; the
    control below fails for exactly that reason if this is left out.
    """
    service = service_class()
    service.storage = storage
    service.status = ServiceStatus.ACTIVE
    return service


@pytest.mark.parametrize(
    "key,expected",
    [
        ("okh/.gitkeep", True),
        ("okw/.gitkeep", True),
        ("packages/.gitkeep", True),
        ("okw/some/nested/.gitkeep", True),
        # A real file that merely mentions it, or ends like it, is not one.
        ("okw/.gitkeep-notes.json", False),
        ("okw/my.gitkeep", False),
        ("okw/facility.json", False),
        ("okh/design-okh.json", False),
    ],
)
def test_the_predicate_recognises_only_the_scaffold_placeholder(
    key: str, expected: bool
) -> None:
    assert is_scaffold_placeholder(key) is expected


@pytest.mark.asyncio
async def test_the_scaffold_actually_wrote_placeholders(fresh_node) -> None:
    """Guards the rest of this file: 'empty' below must not mean 'nothing was written'."""
    keys = [o["key"] async for o in fresh_node.manager.list_objects()]
    assert {"okh/.gitkeep", "okw/.gitkeep"} <= set(keys), keys


@pytest.mark.asyncio
async def test_discovery_finds_nothing_on_a_fresh_node(fresh_node) -> None:
    discovery = SmartFileDiscovery(fresh_node.manager)
    assert await discovery.discover_files("okh") == []
    assert await discovery.discover_files("okw") == []


@pytest.mark.asyncio
async def test_health_counts_are_zero_on_a_fresh_node(fresh_node) -> None:
    fingerprint = await fresh_node.get_config_fingerprint()
    assert (fingerprint["okh_count"], fingerprint["okw_count"]) == (0, 0), (
        "/health counts scaffold placeholders as objects: "
        f"{fingerprint['okh_count']} designs, {fingerprint['okw_count']} facilities"
    )


@pytest.mark.asyncio
async def test_the_okw_listing_is_empty_on_a_fresh_node(fresh_node) -> None:
    service = _service_over(OKWService, fresh_node)

    facilities, total = await service.list(viewer=None)

    assert (
        total == 0 and facilities == []
    ), f"a fresh node lists {total} facilities: {[f.name for f in facilities]!r}"


@pytest.mark.asyncio
async def test_the_okh_listing_is_empty_on_a_fresh_node(fresh_node) -> None:
    """The control: this reader already got it right."""
    service = _service_over(OKHService, fresh_node)

    manifests, total = await service.list(viewer=None)

    assert total == 0 and manifests == []


@pytest.mark.asyncio
async def test_an_empty_node_does_not_fall_through_to_a_bucket_scan(
    fresh_node, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Filtering the placeholder must not make an empty node expensive.

    The placeholder used to make the primary strategy return something, so the
    slower strategies (which download every object to identify it) never ran on a
    fresh node. Now that the primary result is honestly empty, "empty" must stay
    an authoritative answer — a fix that removes work-that-was-being-skipped is
    how a repair reads as a slowdown.
    """

    # Recorded, not raised: discover_files wraps every strategy in
    # `except Exception` to cascade on failure, so an assertion raised inside one
    # is swallowed and the test would pass while the cascade ran.
    scanned: list[str] = []

    async def record(self, file_type):
        scanned.append(file_type)
        return []

    monkeypatch.setattr(SmartFileDiscovery, "_discover_by_metadata", record)
    monkeypatch.setattr(SmartFileDiscovery, "_discover_by_content_validation", record)

    discovery = SmartFileDiscovery(fresh_node.manager)
    assert await discovery.discover_files("okh") == []
    assert await discovery.discover_files("okw") == []
    assert not scanned, f"fell through to a full-bucket strategy for {scanned}"


@pytest.mark.asyncio
async def test_the_catalogue_builder_does_not_trip_over_the_placeholder(
    fresh_node, caplog: pytest.LogCaptureFixture
) -> None:
    """Federation serves this catalogue; an empty node must advertise nothing.

    The placeholder was counted ("Found 1 OKH files") and then rejected with a
    warning on every build, which is noise an operator learns to ignore.
    """
    service = _service_over(OKHService, fresh_node)

    with caplog.at_level("INFO"):
        catalogue = await service._assemble_okh_catalog()

    assert catalogue == []
    noise = [r.getMessage() for r in caplog.records if ".gitkeep" in r.getMessage()]
    assert not noise, noise
    assert any("Found 0 OKH files" in r.getMessage() for r in caplog.records)
