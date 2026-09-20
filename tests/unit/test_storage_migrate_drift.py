"""Migrate detects drift and refuses to commit rather than trust a moving source (#546).

`copy_all_objects` verifies by re-reading the *destination* and comparing it
to what it copied — that proves the copy is faithful to what it read, not
that what it read is still what the source holds. A writer that adds,
changes, or deletes an object during the copy is invisible to that
verification: the deletion is never carried over (the copy has no concept of
"this used to exist"), and a change read mid-copy either lands as a stale
version or, if a later read wins the race, differs from what "verified" was
promising the operator.

`detect_drift` is the pure comparison (unit-testable against fabricated
snapshots, #546 AC4); `test_storage_switch_modes.py` already proves the quiet
case, so this file is specifically about the two things that are new here:
a drift refusal, and that re-running after one converges once the source
holds still.
"""

from __future__ import annotations

import pytest

from src.core.services.storage_reconfigure import (
    StorageReconfigureError,
    build_candidate,
    migrate_and_switch,
)
from src.core.services.storage_service import StorageService
from src.core.services.storage_transfer import CopyReport, detect_drift, snapshot_source
from src.core.storage.base import StorageConfig
from src.core.storage.manager import StorageManager


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    """Without this, `save_config()` inside `migrate_and_switch` writes to
    the real default `~/.ohm/storage-config.json` on whatever machine runs
    the test — this file was missing it, and did exactly that."""
    monkeypatch.setenv("OHM_STORAGE_CONFIG_PATH", str(tmp_path / "cfg.json"))
    monkeypatch.setenv("OHM_ENCRYPTION_SALT", "migrate-drift-salt")
    monkeypatch.setenv("OHM_ENCRYPTION_PASSWORD", "migrate-drift-password")


# ---------------------------------------------------------------------------
# detect_drift: pure, no I/O (#546 AC4)
# ---------------------------------------------------------------------------


def _entry(size=10, last_modified="2026-01-01T00:00:00+00:00", etag=None):
    return {"size": size, "last_modified": last_modified, "etag": etag}


def test_identical_snapshots_are_clean():
    snap = {"a": _entry(), "b": _entry(size=20)}
    drift = detect_drift(snap, dict(snap))
    assert drift.clean
    assert drift.to_dict() == {"clean": True, "added": [], "removed": [], "changed": []}


def test_a_new_key_is_added():
    before = {"a": _entry()}
    after = {"a": _entry(), "b": _entry()}
    drift = detect_drift(before, after)
    assert drift.added == ["b"]
    assert not drift.clean


def test_a_missing_key_is_removed():
    before = {"a": _entry(), "b": _entry()}
    after = {"a": _entry()}
    drift = detect_drift(before, after)
    assert drift.removed == ["b"]
    assert not drift.clean


def test_a_changed_size_or_mtime_is_changed_when_there_is_no_etag():
    before = {"a": _entry(size=10, last_modified="t1")}
    after = {"a": _entry(size=20, last_modified="t1")}
    assert detect_drift(before, after).changed == ["a"]

    before2 = {"a": _entry(size=10, last_modified="t1")}
    after2 = {"a": _entry(size=10, last_modified="t2")}
    assert detect_drift(before2, after2).changed == ["a"]


def test_etag_is_trusted_over_size_and_mtime_when_both_sides_have_one():
    # Same etag, different size/mtime metadata (e.g. a provider that reports
    # slightly different precision) — not drift, because the bytes agree.
    before = {"a": _entry(size=10, last_modified="t1", etag="abc")}
    after = {"a": _entry(size=999, last_modified="t2", etag="abc")}
    assert detect_drift(before, after).clean

    # Different etag, identical size/mtime — still drift; the etag wins.
    before2 = {"a": _entry(size=10, last_modified="t1", etag="abc")}
    after2 = {"a": _entry(size=10, last_modified="t1", etag="xyz")}
    assert detect_drift(before2, after2).changed == ["a"]


def test_describe_reads_like_a_sentence():
    drift = detect_drift(
        {"a": _entry(), "b": _entry()},
        {"a": _entry(size=999), "c": _entry()},
    )
    assert drift.describe() == "1 added, 1 changed, 1 removed"
    assert detect_drift({}, {}).describe() == "no drift"


# ---------------------------------------------------------------------------
# snapshot_source: shape, against a real local store
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_snapshot_source_captures_size_and_modified_time(tmp_path):
    manager = StorageManager(StorageConfig(provider="local", bucket_name=str(tmp_path)))
    await manager.connect()
    await manager.put_object("okh/a.json", b'{"v": 1}', content_type="application/json")

    snapshot = await snapshot_source(manager)

    assert set(snapshot) == {"okh/a.json"}
    entry = snapshot["okh/a.json"]
    assert entry["size"] == len(b'{"v": 1}')
    assert entry["last_modified"] is not None


# ---------------------------------------------------------------------------
# migrate_and_switch: drift refuses; a quiet re-run converges (#546 AC1, AC3)
# ---------------------------------------------------------------------------


async def _seeded_service(path, count=2):
    manager = StorageManager(StorageConfig(provider="local", bucket_name=str(path)))
    await manager.connect()
    for i in range(count):
        await manager.put_object(
            f"okh/design-{i}.json",
            f'{{"i": {i}}}'.encode(),
            content_type="application/json",
        )
    service = await StorageService.get_instance()
    await service.configure(StorageConfig(provider="local", bucket_name=str(path)))
    return service


@pytest.mark.asyncio
async def test_a_write_during_the_copy_refuses_the_switch(tmp_path, monkeypatch):
    old = tmp_path / "old"
    new = tmp_path / "new"
    service = await _seeded_service(old)

    async def copy_that_races_a_writer(source, destination, progress=None):
        # Stands in for a concurrent writer landing mid-copy: by the time this
        # returns, the source no longer matches what snapshot_source saw
        # before the copy started.
        await source.put_object(
            "okh/design-0.json", b'{"i": "changed"}', content_type="application/json"
        )
        return CopyReport(objects_copied=2, objects_verified=2)

    monkeypatch.setattr(
        "src.core.services.storage_transfer.copy_all_objects", copy_that_races_a_writer
    )

    with pytest.raises(StorageReconfigureError, match="changed while the copy"):
        await migrate_and_switch(service, build_candidate("local", str(new)))

    # Refused before anything was touched: still serving the old backend.
    assert service.manager.config.bucket_name == str(old)


@pytest.mark.asyncio
async def test_a_drift_refusal_converges_once_the_source_is_quiet(tmp_path):
    """#546 AC3: re-running the identical call, once the source has stopped
    moving, just works — migrate keeps no retry state that a refusal could
    get stuck in."""
    old = tmp_path / "old"
    new = tmp_path / "new"
    service = await _seeded_service(old)

    async def copy_that_races_a_writer(source, destination, progress=None):
        await source.put_object(
            "okh/design-0.json", b'{"i": "changed"}', content_type="application/json"
        )
        return CopyReport(objects_copied=2, objects_verified=2)

    # A separate, scoped MonkeyPatch rather than the function's own fixture:
    # `.undo()` below must restore only this one patch. Undoing the shared
    # fixture would also roll back the autouse `isolated` fixture's env vars
    # (they use the same underlying instance), and the second, real
    # `migrate_and_switch` call below would then persist to whatever
    # `OHM_STORAGE_CONFIG_PATH` resolves to outside the test — this test
    # caught that exact bug once already.
    patcher = pytest.MonkeyPatch()
    patcher.setattr(
        "src.core.services.storage_transfer.copy_all_objects", copy_that_races_a_writer
    )
    with pytest.raises(StorageReconfigureError, match="changed while the copy"):
        await migrate_and_switch(service, build_candidate("local", str(new)))
    assert service.manager.config.bucket_name == str(old)

    # The writer has stopped now — re-run the identical call with the real
    # (unpatched) copy and nothing else touching the source in between.
    patcher.undo()
    result = await migrate_and_switch(service, build_candidate("local", str(new)))

    assert result["drift"]["clean"] is True
    assert service.manager.config.bucket_name == str(new)
