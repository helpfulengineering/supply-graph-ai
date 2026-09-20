"""Restart-pending state: what it is, and the one-switch-at-a-time guard (#545).

A restart is "pending" precisely when a *running* API's live backend (read
from its #544 marker) disagrees with the saved configuration — nothing else.
A stale or absent marker is never pending: there is no running process whose
picture of the world could be stale, so the next boot just applies whatever is
saved. `reconfigure_storage` (and, redundantly but for speed,
`migrate_and_switch`) refuses to run while pending, so a second switch cannot
silently overwrite a first one a running API never picked up.
"""

from __future__ import annotations

import time

import pytest

from src.core.services import storage_liveness as sl
from src.core.services.storage_config_store import load_config, save_config
from src.core.services.storage_reconfigure import (
    StorageReconfigureError,
    migrate_and_switch,
    reconfigure_storage,
    restart_pending_info,
)
from src.core.services.storage_service import StorageService
from src.core.storage.base import StorageConfig


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(tmp_path / "cfg.json"))
    monkeypatch.setenv("OHM_STORAGE_MARKER_PATH", str(tmp_path / "api-live.json"))
    monkeypatch.setenv("OHM_ENCRYPTION_SALT", "restart-pending-salt")
    monkeypatch.setenv("OHM_ENCRYPTION_PASSWORD", "restart-pending-password")
    yield


def test_no_marker_is_not_pending():
    info = restart_pending_info()
    assert info.pending is False
    assert info.live_provider is None


def test_running_marker_matching_saved_is_not_pending(tmp_path):
    save_config(StorageConfig(provider="local", bucket_name=str(tmp_path / "a")))
    sl.MarkerWriter("local", str(tmp_path / "a")).beat()

    assert restart_pending_info().pending is False


def test_running_marker_differing_from_saved_is_pending(tmp_path):
    save_config(StorageConfig(provider="local", bucket_name=str(tmp_path / "b")))
    sl.MarkerWriter("local", str(tmp_path / "a")).beat()

    info = restart_pending_info()
    assert info.pending is True
    assert info.live_bucket == str(tmp_path / "a")
    assert info.saved_bucket == str(tmp_path / "b")
    assert info.since is not None


def test_a_stale_marker_is_never_pending(monkeypatch, tmp_path):
    """No running process means nothing to restart — the next boot just
    applies whatever is saved, with nothing to refuse in the meantime."""
    monkeypatch.setenv("OHM_STORAGE_MARKER_HEARTBEAT_SECONDS", "0.01")
    save_config(StorageConfig(provider="local", bucket_name=str(tmp_path / "b")))
    sl.MarkerWriter("local", str(tmp_path / "a")).beat()
    time.sleep(0.1)  # > 3 * 0.01s stale threshold

    assert restart_pending_info().pending is False


def test_no_saved_config_is_not_pending_even_with_a_running_marker(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("src.config.settings.STORAGE_CONFIG", None)
    sl.MarkerWriter("local", str(tmp_path / "a")).beat()

    assert restart_pending_info().pending is False


@pytest.mark.asyncio
async def test_reconfigure_storage_refuses_while_pending(tmp_path):
    old = tmp_path / "old"
    diverged = tmp_path / "diverged"
    attempted = tmp_path / "attempted"

    service = await StorageService.get_instance()
    await service.configure(StorageConfig(provider="local", bucket_name=str(old)))

    # A marker still saying `old` (a running API that has not restarted)
    # alongside a saved configuration that already moved on to `diverged` —
    # the shape an earlier switch from a separate process leaves behind.
    save_config(StorageConfig(provider="local", bucket_name=str(old)))
    sl.MarkerWriter("local", str(old)).beat()
    save_config(StorageConfig(provider="local", bucket_name=str(diverged)))

    with pytest.raises(StorageReconfigureError, match="restart is already pending"):
        await reconfigure_storage(service, provider="local", bucket=str(attempted))

    # Refused before anything was touched: still `diverged`, not `attempted`.
    assert load_config().bucket_name == str(diverged)


@pytest.mark.asyncio
async def test_migrate_and_switch_also_refuses_while_pending_before_copying(tmp_path):
    old = tmp_path / "old"
    diverged = tmp_path / "diverged"

    service = await StorageService.get_instance()
    await service.configure(StorageConfig(provider="local", bucket_name=str(old)))

    save_config(StorageConfig(provider="local", bucket_name=str(old)))
    sl.MarkerWriter("local", str(old)).beat()
    save_config(StorageConfig(provider="local", bucket_name=str(diverged)))

    candidate = StorageConfig(provider="local", bucket_name=str(tmp_path / "dest"))
    with pytest.raises(StorageReconfigureError, match="restart is already pending"):
        await migrate_and_switch(service, candidate)

    # Nothing was copied: the destination was never even created.
    assert not (tmp_path / "dest").exists()
