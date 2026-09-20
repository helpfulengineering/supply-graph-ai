"""The migrate switch mode and the orderings it depends on (#381, #543).

Switching points an instance at an empty backend and leaves the old data where
it is, invisible. **migrate** is the other answer, and its ordering is a safety
property rather than an implementation detail: validate, copy, verify, *then*
swap. A failure at any point before the swap leaves a working instance on its
original backend and a partial copy on the destination — recoverable. The
reverse is not.

The third mode, `abandon_and_wipe`, is retired (#543): run from a separate
process it erased the backend a running API was still serving from. Its
replacement is a standalone, guarded wipe (#547); `wipe_storage` and its echo
guard are covered in `test_storage_transfer.py`, and the refusals in
`tests/api/test_storage_retired_modes.py` and
`tests/cli/test_storage_config_set_retired_modes.py`.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.core.services.storage_reconfigure import (
    StorageReconfigureError,
    build_candidate,
    migrate_and_switch,
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
    # A quiet source (#546): nothing drifted between the two snapshots.
    assert result["drift"] == {"clean": True, "added": [], "removed": [], "changed": []}
    assert result["cutoff_at"] is not None


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


async def test_a_fresh_process_adopts_the_instance_configuration(tmp_path):
    """The gap that made migrate and wipe unusable from the CLI (#381).

    A long-running API process configures storage at boot. A CLI process does
    not: it starts, configures nothing, and both modes here act on the
    *current* backend — so they reported that there was no storage to migrate
    from, describing the process rather than the instance.
    """
    from src.core.services.storage_config_store import save_config
    from src.core.services.storage_reconfigure import ensure_configured

    await _seed(tmp_path / "persisted", 2)
    save_config(
        StorageConfig(provider="local", bucket_name=str(tmp_path / "persisted"))
    )

    # A service that has never been configured, as a fresh process has.
    service = StorageService.__new__(StorageService)
    service.manager = None
    service._configured = False

    await ensure_configured(service)

    assert service.manager is not None
    assert service.manager.config.bucket_name == str(tmp_path / "persisted")


async def test_ensure_configured_leaves_a_configured_service_alone(tmp_path):
    """It must not re-point a process that already connected at boot."""
    from src.core.services.storage_config_store import save_config
    from src.core.services.storage_reconfigure import ensure_configured

    save_config(StorageConfig(provider="local", bucket_name=str(tmp_path / "other")))
    service = await _service_on(tmp_path / "live")

    await ensure_configured(service)

    assert service.manager.config.bucket_name == str(tmp_path / "live")
