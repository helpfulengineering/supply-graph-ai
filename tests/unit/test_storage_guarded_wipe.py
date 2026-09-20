"""Standalone `ohm storage wipe`, guarded against erasing anything live (#547).

#543 retired the combined switch-and-wipe: run from a separate process it
erased the backend a running API was still serving from — a live API's
design count went from 1 to 0. This restores the ability to erase an old
backend as its own explicit step, and each test here is one way that old
incident could recur if a guard were missing: wiping what is saved, what the
environment would fall back to, what a running API's marker says is live, or
wiping while a restart is pending and the node's own picture of its storage
is already out of date.
"""

from __future__ import annotations

import pytest

from src.core.services import storage_liveness as sl
from src.core.services.storage_config_store import save_config
from src.core.services.storage_reconfigure import StorageReconfigureError, guarded_wipe
from src.core.services.storage_transfer import WipeGuardError
from src.core.storage.base import StorageConfig
from src.core.storage.manager import StorageManager

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(tmp_path / "cfg.json"))
    monkeypatch.setenv("OHM_STORAGE_MARKER_PATH", str(tmp_path / "api-live.json"))
    monkeypatch.setenv("OHM_ENCRYPTION_SALT", "guarded-wipe-salt")
    monkeypatch.setenv("OHM_ENCRYPTION_PASSWORD", "guarded-wipe-password")
    monkeypatch.setattr("src.config.settings.STORAGE_CONFIG", None)


async def _seed(path, count: int = 1) -> None:
    manager = StorageManager(StorageConfig(provider="local", bucket_name=str(path)))
    await manager.connect()
    for i in range(count):
        await manager.put_object(
            f"okh/design-{i}.json",
            f'{{"i": {i}}}'.encode(),
            content_type="application/json",
        )


async def _count(path) -> int:
    manager = StorageManager(StorageConfig(provider="local", bucket_name=str(path)))
    await manager.connect()
    return len([obj async for obj in manager.list_objects()])


async def test_wiping_the_saved_configuration_is_refused(tmp_path):
    old = tmp_path / "old"
    await _seed(old)
    save_config(StorageConfig(provider="local", bucket_name=str(old)))

    with pytest.raises(StorageReconfigureError, match="saved storage configuration"):
        await guarded_wipe("local", str(old), wipe_confirm=str(old))

    assert await _count(old) == 1


async def test_wiping_the_environment_backend_is_refused_when_nothing_is_saved(
    tmp_path, monkeypatch
):
    old = tmp_path / "old"
    await _seed(old)
    monkeypatch.setattr(
        "src.config.settings.STORAGE_CONFIG",
        StorageConfig(provider="local", bucket_name=str(old)),
    )

    with pytest.raises(StorageReconfigureError, match="environment-configured backend"):
        await guarded_wipe("local", str(old), wipe_confirm=str(old))

    assert await _count(old) == 1


async def test_the_environment_backend_does_not_block_a_wipe_once_something_is_saved(
    tmp_path, monkeypatch
):
    """Saved always wins at boot (#377); once it exists, the environment is
    no longer what a fresh process would actually use, so it stops being a
    reason to refuse."""
    old = tmp_path / "old"
    new = tmp_path / "new"
    await _seed(old)
    monkeypatch.setattr(
        "src.config.settings.STORAGE_CONFIG",
        StorageConfig(provider="local", bucket_name=str(old)),
    )
    save_config(StorageConfig(provider="local", bucket_name=str(new)))

    await guarded_wipe("local", str(old), wipe_confirm=str(old))

    assert await _count(old) == 0


async def test_wiping_the_backend_a_running_api_is_live_on_is_refused(tmp_path):
    old = tmp_path / "old"
    await _seed(old)
    sl.MarkerWriter("local", str(old)).beat()

    with pytest.raises(StorageReconfigureError, match="a running API"):
        await guarded_wipe("local", str(old), wipe_confirm=str(old))

    assert await _count(old) == 1


async def test_a_running_api_on_a_different_backend_does_not_block_this_wipe(tmp_path):
    old = tmp_path / "old"
    elsewhere = tmp_path / "elsewhere"
    await _seed(old)
    sl.MarkerWriter("local", str(elsewhere)).beat()

    await guarded_wipe("local", str(old), wipe_confirm=str(old))

    assert await _count(old) == 0


async def test_an_unreadable_marker_refuses_regardless_of_the_target(tmp_path):
    """Fail closed (#544): an ambiguous marker cannot be ruled out as the
    backend in question, so it refuses every target, not just a match."""
    old = tmp_path / "old"
    await _seed(old)
    sl.marker_path().parent.mkdir(parents=True, exist_ok=True)
    sl.marker_path().write_text("{not valid json")

    with pytest.raises(StorageReconfigureError, match="unreadable"):
        await guarded_wipe("local", str(old), wipe_confirm=str(old))

    assert await _count(old) == 1


async def test_a_stale_marker_does_not_block_the_wipe(tmp_path, monkeypatch):
    """Staleness is what lets a wipe ever run without a live process to
    contradict it — the whole point of the state existing (#544)."""
    monkeypatch.setenv("OHM_STORAGE_MARKER_HEARTBEAT_SECONDS", "0.01")
    old = tmp_path / "old"
    await _seed(old)
    sl.MarkerWriter("local", str(old)).beat()
    import time

    time.sleep(0.1)  # > 3 * 0.01s stale threshold

    await guarded_wipe("local", str(old), wipe_confirm=str(old))

    assert await _count(old) == 0


async def test_wiping_while_a_restart_is_pending_is_refused(tmp_path):
    old = tmp_path / "old"
    diverged = tmp_path / "diverged"
    await _seed(old)
    # A running marker on `old`, but the saved config already moved on to
    # `diverged` — the shape an earlier switch a running API never picked up
    # leaves behind. `diverged`, not `old`, is what is pending here, but a
    # wipe of *anything* is refused until that is resolved.
    sl.MarkerWriter("local", str(old)).beat()
    save_config(StorageConfig(provider="local", bucket_name=str(diverged)))

    with pytest.raises(StorageReconfigureError, match="restart is already pending"):
        await guarded_wipe(
            "local",
            str(tmp_path / "unrelated"),
            wipe_confirm=str(tmp_path / "unrelated"),
        )

    assert await _count(old) == 1


async def test_the_echo_guard_still_applies(tmp_path):
    old = tmp_path / "old"
    await _seed(old)

    with pytest.raises(WipeGuardError):
        await guarded_wipe("local", str(old), wipe_confirm=str(tmp_path / "wrong"))

    assert await _count(old) == 1


async def test_dry_run_reports_and_deletes_nothing(tmp_path):
    old = tmp_path / "old"
    await _seed(old, count=3)

    result = await guarded_wipe("local", str(old), wipe_confirm=str(old), dry_run=True)

    assert result["wipe"]["dry_run"] is True
    assert result["wipe"]["objects"] == 3
    assert await _count(old) == 3


async def test_a_clean_wipe_with_nothing_live_succeeds(tmp_path):
    old = tmp_path / "old"
    await _seed(old, count=2)

    result = await guarded_wipe("local", str(old), wipe_confirm=str(old))

    assert result["wipe"]["objects"] == 2
    assert await _count(old) == 0
