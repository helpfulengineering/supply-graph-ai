"""The liveness marker fails closed, and its heartbeat drives running/stale (#544).

Fast, deterministic tests with an injected clock — no real process, no real
sleeping. The real-process acceptance tests (an actual API and an actual CLI
subprocess) live in tests/integration/test_storage_liveness_realprocess.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from src.core.services import storage_liveness as sl


@pytest.fixture(autouse=True)
def isolated_marker(monkeypatch, tmp_path):
    monkeypatch.setenv("OHM_STORAGE_MARKER_PATH", str(tmp_path / "api-live.json"))
    monkeypatch.setenv("OHM_STORAGE_MARKER_HEARTBEAT_SECONDS", "15")
    yield tmp_path


def _clock(at: datetime):
    return lambda: at


def test_no_file_is_absent():
    info = sl.read()
    assert info.status == sl.LivenessStatus.ABSENT
    assert info.age_seconds is None


def test_a_fresh_heartbeat_is_running():
    writer = sl.MarkerWriter("local", "bucket-a")
    writer.beat()

    info = sl.read(now_fn=_clock(datetime.now(timezone.utc)))
    assert info.status == sl.LivenessStatus.RUNNING
    assert info.provider == "local"
    assert info.bucket == "bucket-a"
    assert info.pid == writer._pid
    assert info.age_seconds is not None and info.age_seconds < 1


def test_heartbeat_older_than_three_intervals_is_stale():
    writer = sl.MarkerWriter("local", "bucket-a")
    writer.beat()

    future = datetime.now(timezone.utc) + timedelta(seconds=45.1)
    info = sl.read(now_fn=_clock(future))
    assert info.status == sl.LivenessStatus.STALE


def test_heartbeat_just_under_three_intervals_is_still_running():
    writer = sl.MarkerWriter("local", "bucket-a")
    writer.beat()

    future = datetime.now(timezone.utc) + timedelta(seconds=44.9)
    info = sl.read(now_fn=_clock(future))
    assert info.status == sl.LivenessStatus.RUNNING


@pytest.mark.parametrize(
    "contents",
    [
        "not json at all",
        "{}",  # valid json, missing heartbeat_at
        json.dumps({"heartbeat_at": "not-a-timestamp"}),
    ],
)
def test_an_unreadable_or_malformed_marker_reads_as_running(isolated_marker, contents):
    path = sl.marker_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")

    info = sl.read()
    assert info.status == sl.LivenessStatus.RUNNING
    assert info.error is not None


def test_update_backend_changes_provider_and_bucket_and_beats():
    writer = sl.MarkerWriter("local", "old-bucket")
    writer.beat()

    writer.update_backend("azure_blob", "new-container")

    info = sl.read()
    assert info.provider == "azure_blob"
    assert info.bucket == "new-container"


def test_started_at_survives_repeated_beats():
    writer = sl.MarkerWriter("local", "bucket-a")
    writer.beat()
    first = sl.read()

    writer.beat()
    second = sl.read()

    assert first.started_at == second.started_at
    assert first.heartbeat_at is not None


def test_forget_removes_a_present_marker_and_is_idempotent():
    writer = sl.MarkerWriter("local", "bucket-a")
    writer.beat()
    assert sl.read().status != sl.LivenessStatus.ABSENT

    assert sl.forget() is True
    assert sl.read().status == sl.LivenessStatus.ABSENT
    assert sl.forget() is False


def test_default_heartbeat_seconds_when_env_unset(monkeypatch):
    monkeypatch.delenv("OHM_STORAGE_MARKER_HEARTBEAT_SECONDS", raising=False)
    assert sl.heartbeat_seconds() == sl.DEFAULT_HEARTBEAT_SECONDS


def test_invalid_heartbeat_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("OHM_STORAGE_MARKER_HEARTBEAT_SECONDS", "not-a-number")
    assert sl.heartbeat_seconds() == sl.DEFAULT_HEARTBEAT_SECONDS


@pytest.mark.asyncio
async def test_start_stop_writes_and_then_removes_the_marker():
    writer = sl.start("local", "bucket-a")
    try:
        assert sl.read().status == sl.LivenessStatus.RUNNING
    finally:
        await sl.stop()
    assert sl.read().status == sl.LivenessStatus.ABSENT
    assert writer is not None


@pytest.mark.asyncio
async def test_refresh_backend_is_a_noop_with_no_active_writer():
    # No sl.start() call in this test — mirrors the CLI process, which never
    # starts a marker. Must not raise.
    sl.refresh_backend("gcs", "some-bucket")
    assert sl.read().status == sl.LivenessStatus.ABSENT
