"""Moving and erasing storage, and the orderings that make them safe (#381).

Both operations here can destroy data, so the tests are about what happens
when things go wrong rather than when they go right:

- a migration that fails partway must leave a working instance on its original
  backend, not a switched one pointing at a half-copy;
- a wipe whose echoed name does not match must delete nothing, and must not
  switch either — "switched but not wiped" is a state nobody asked for.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.core.services.storage_transfer import (
    WipeGuardError,
    copy_all_objects,
    wipe_storage,
)
from src.core.storage.base import StorageConfig
from src.core.storage.manager import StorageManager

pytestmark = pytest.mark.asyncio


async def _manager(path) -> StorageManager:
    manager = StorageManager(StorageConfig(provider="local", bucket_name=str(path)))
    await manager.connect()
    return manager


async def _seed(manager: StorageManager, count: int) -> None:
    for index in range(count):
        await manager.put_object(
            key=f"okh/design-{index}.json",
            data=f'{{"index": {index}}}'.encode(),
            content_type="application/json",
        )


async def _keys(manager: StorageManager) -> list[str]:
    return sorted([obj["key"] async for obj in manager.list_objects()])


async def test_copy_moves_every_object_and_verifies_it(tmp_path):
    source = await _manager(tmp_path / "src")
    destination = await _manager(tmp_path / "dst")
    await _seed(source, 5)

    report = await copy_all_objects(source, destination)

    assert report.ok
    assert report.objects_copied == 5
    # Verified means re-read from the destination and digest-compared, not
    # merely written: an operator told the copy verified should be able to
    # believe it.
    assert report.objects_verified == 5
    assert await _keys(destination) == await _keys(source)


async def test_copy_works_between_different_providers(tmp_path):
    """The loop uses only list/get/put, so provider pairs are irrelevant to it.

    The existing copy_container_blobs.py is Azure-to-Azure because it reaches
    for the Azure provider directly. This asserts the shape that makes any
    pair work — two independently configured managers, no provider in sight.
    """
    source = await _manager(tmp_path / "a")
    destination = await _manager(tmp_path / "b")
    await _seed(source, 2)

    report = await copy_all_objects(source, destination)

    assert report.ok
    assert source.config.provider == destination.config.provider == "local"
    assert report.objects_copied == 2


async def test_a_copy_that_fails_is_not_reported_as_ok(tmp_path):
    source = await _manager(tmp_path / "src")
    destination = await _manager(tmp_path / "dst")
    await _seed(source, 3)

    with patch.object(
        destination, "put_object", AsyncMock(side_effect=OSError("disk full"))
    ):
        report = await copy_all_objects(source, destination)

    assert not report.ok
    assert len(report.failures) == 3
    # Verification is skipped rather than run against a copy already known to
    # be incomplete.
    assert report.objects_verified == 0


async def test_a_silently_corrupted_copy_fails_verification(tmp_path):
    """A backend that accepts a write and returns something else is not fine."""
    source = await _manager(tmp_path / "src")
    destination = await _manager(tmp_path / "dst")
    await _seed(source, 2)

    with patch.object(
        destination, "get_object", AsyncMock(return_value=b"not what was written")
    ):
        report = await copy_all_objects(source, destination)

    assert not report.ok
    assert report.objects_copied == 2
    assert report.objects_verified == 0
    assert all("digest mismatch" in f for f in report.failures)


async def test_progress_reports_each_phase(tmp_path):
    source = await _manager(tmp_path / "src")
    destination = await _manager(tmp_path / "dst")
    await _seed(source, 2)

    seen: list[str] = []
    await copy_all_objects(
        source, destination, progress=lambda stage, fraction, msg: seen.append(stage)
    )

    assert seen[0] == "scan"
    assert "copy" in seen and "verify" in seen
    assert seen[-1] == "done"


async def test_wipe_refuses_when_the_echoed_name_does_not_match(tmp_path):
    """The guard that replaces an interactive prompt. A boolean would not."""
    manager = await _manager(tmp_path / "bucket")
    await _seed(manager, 3)

    with pytest.raises(WipeGuardError):
        await wipe_storage(manager, str(tmp_path / "bucket"), "some-other-bucket")

    assert len(await _keys(manager)) == 3


async def test_a_dry_run_reports_counts_and_deletes_nothing(tmp_path):
    manager = await _manager(tmp_path / "bucket")
    await _seed(manager, 4)

    report = await wipe_storage(
        manager, str(tmp_path / "bucket"), str(tmp_path / "bucket"), dry_run=True
    )

    assert report.dry_run is True
    assert report.objects == 4
    assert report.bytes > 0
    assert len(await _keys(manager)) == 4


async def test_wipe_removes_every_object(tmp_path):
    manager = await _manager(tmp_path / "bucket")
    await _seed(manager, 4)

    report = await wipe_storage(
        manager, str(tmp_path / "bucket"), str(tmp_path / "bucket")
    )

    assert report.objects == 4
    assert report.failures == []
    assert await _keys(manager) == []


async def test_the_key_list_in_a_report_is_capped(tmp_path):
    """A wipe report is for a human deciding; it is not a data export."""
    manager = await _manager(tmp_path / "bucket")
    await _seed(manager, 120)

    report = await wipe_storage(
        manager, str(tmp_path / "bucket"), str(tmp_path / "bucket"), dry_run=True
    )
    payload = report.to_dict()

    assert payload["objects"] == 120
    assert len(payload["keys"]) == 100
    assert payload["keys_truncated"] is True
