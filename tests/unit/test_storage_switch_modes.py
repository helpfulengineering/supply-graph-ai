"""The three switch modes, and the orderings they depend on (#381).

Switching points an instance at an empty backend and leaves the old data where
it is, invisible. These are the other two answers, and both have an ordering
that is a safety property rather than an implementation detail:

- **migrate**: validate, copy, verify, *then* swap. A failure at any point
  before the swap leaves a working instance on its original backend and a
  partial copy on the destination — recoverable. The reverse is not.
- **abandon_and_wipe**: swap, *then* erase. Erasing first would open a window
  in which the old data is gone and the new backend is unproven.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.core.services.storage_reconfigure import (
    StorageReconfigureError,
    build_candidate,
    migrate_and_switch,
    switch_and_wipe,
)
from src.core.services.storage_service import StorageService
from src.core.storage.base import StorageConfig
from src.core.storage.manager import StorageManager

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(tmp_path / "cfg.json"))
    monkeypatch.setenv("OHM_ENCRYPTION_SALT", "switch-modes-salt")
    monkeypatch.setenv("OHM_ENCRYPTION_PASSWORD", "switch-modes-password")


async def _seed(path, count: int) -> None:
    manager = StorageManager(StorageConfig(provider="local", bucket_name=str(path)))
    await manager.connect()
    for index in range(count):
        await manager.put_object(
            key=f"okh/design-{index}.json",
            data=f'{{"index": {index}}}'.encode(),
            content_type="application/json",
        )
    await manager.disconnect()


async def _object_count(path) -> int:
    manager = StorageManager(StorageConfig(provider="local", bucket_name=str(path)))
    await manager.connect()
    count = len([obj async for obj in manager.list_objects()])
    await manager.disconnect()
    return count


async def _service_on(path) -> StorageService:
    service = await StorageService.get_instance()
    await service.configure(StorageConfig(provider="local", bucket_name=str(path)))
    return service


async def test_migration_copies_verifies_then_switches(tmp_path):
    await _seed(tmp_path / "old", 3)
    service = await _service_on(tmp_path / "old")

    result = await migrate_and_switch(
        service, build_candidate("local", str(tmp_path / "new"))
    )

    assert result["migration"]["objects_verified"] == 3
    assert service.manager.config.bucket_name == str(tmp_path / "new")
    # Migration copies; it does not erase. The old backend is untouched, which
    # is what makes a migration reversible by hand if it turns out wrong.
    assert await _object_count(tmp_path / "old") == 3


async def test_a_migration_to_an_unusable_destination_does_not_switch(tmp_path):
    await _seed(tmp_path / "old", 2)
    service = await _service_on(tmp_path / "old")

    with pytest.raises(StorageReconfigureError):
        await migrate_and_switch(
            service, build_candidate("local", "/dev/null/not-a-directory")
        )

    assert service.manager.config.bucket_name == str(tmp_path / "old")
    assert service._configured is True


async def test_a_migration_that_fails_partway_leaves_the_instance_working(tmp_path):
    """The criterion that matters most: a half-copy must not become live."""
    await _seed(tmp_path / "old", 3)
    service = await _service_on(tmp_path / "old")

    with patch(
        "src.core.services.storage_transfer.copy_all_objects",
        AsyncMock(
            return_value=type(
                "R",
                (),
                {
                    "ok": False,
                    "failures": ["okh/design-1.json: connection reset"],
                    "to_dict": lambda self: {},
                },
            )()
        ),
    ):
        with pytest.raises(StorageReconfigureError) as excinfo:
            await migrate_and_switch(
                service, build_candidate("local", str(tmp_path / "new"))
            )

    assert "still serving" in str(excinfo.value)
    assert service.manager.config.bucket_name == str(tmp_path / "old")
    assert await _object_count(tmp_path / "old") == 3


async def test_wipe_with_a_mismatched_echo_neither_switches_nor_deletes(tmp_path):
    """ "Switched but not wiped" is a state nobody asked for, so fail first."""
    await _seed(tmp_path / "old", 3)
    service = await _service_on(tmp_path / "old")

    with pytest.raises(StorageReconfigureError) as excinfo:
        await switch_and_wipe(
            service,
            build_candidate("local", str(tmp_path / "new")),
            wipe_confirm="a-different-bucket",
        )

    assert "Nothing was deleted" in str(excinfo.value)
    assert service.manager.config.bucket_name == str(tmp_path / "old")
    assert await _object_count(tmp_path / "old") == 3


async def test_a_wipe_dry_run_switches_nothing_and_deletes_nothing(tmp_path):
    await _seed(tmp_path / "old", 4)
    service = await _service_on(tmp_path / "old")

    result = await switch_and_wipe(
        service,
        build_candidate("local", str(tmp_path / "new")),
        wipe_confirm=str(tmp_path / "old"),
        dry_run=True,
    )

    assert result["dry_run"] is True
    assert result["switched"] is False
    assert result["wipe"]["objects"] == 4
    assert service.manager.config.bucket_name == str(tmp_path / "old")
    assert await _object_count(tmp_path / "old") == 4


async def test_wipe_happens_only_after_the_switch_succeeds(tmp_path):
    await _seed(tmp_path / "old", 4)
    service = await _service_on(tmp_path / "old")

    result = await switch_and_wipe(
        service,
        build_candidate("local", str(tmp_path / "new")),
        wipe_confirm=str(tmp_path / "old"),
    )

    assert result["switched"] is True
    assert result["wipe"]["objects"] == 4
    assert service.manager.config.bucket_name == str(tmp_path / "new")
    assert await _object_count(tmp_path / "old") == 0
    # The new backend is set up and serving, not merely selected.
    assert service._configured is True
    assert await _object_count(tmp_path / "new") > 0
