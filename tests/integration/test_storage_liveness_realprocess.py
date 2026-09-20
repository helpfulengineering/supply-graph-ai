"""The liveness marker, produced by a real API process (#539 D10, #544).

Unit coverage (`tests/unit/test_storage_liveness.py`) proves the read/write
logic against fabricated files with an injected clock. What that cannot see is
whether the *real* process wiring holds: does `uvicorn` actually run the
heartbeat task, does a graceful SIGTERM actually remove the marker through the
real lifespan shutdown, does a `kill -9` actually leave it behind, and does the
CLI — a separate, short-lived process with no way to authenticate to the API —
actually see the same file the API wrote.

Two different heartbeat intervals are used on purpose:

- A short one (0.3s) for tests that read the marker directly with
  `storage_liveness.read()`, in-process, so the timing assertions are not
  contaminated by the ~1-2s a fresh CLI subprocess takes just to import.
- A longer one (1.5s) for the one test that drives everything through the CLI
  subprocess end to end (#544 AC5), where correctness of the reported state
  matters and CLI startup latency must not be mistaken for staleness.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict

import pytest

from src.core.services import storage_liveness as sl
from tests.support.real_process import ApiProcess, run_cli, start_api, wait_until

pytestmark = pytest.mark.integration


def _base_env(tmp_path: Path, heartbeat_seconds: float) -> Dict[str, str]:
    old = tmp_path / "old"
    old.mkdir(parents=True, exist_ok=True)
    return {
        **os.environ,
        "STORAGE_PROVIDER": "local",
        "LOCAL_STORAGE_PATH": str(old),
        "OHM_STORAGE_CONFIG_PATH": str(tmp_path / "cfg.json"),
        "OHM_STORAGE_MARKER_PATH": str(tmp_path / "api-live.json"),
        "OHM_STORAGE_MARKER_HEARTBEAT_SECONDS": str(heartbeat_seconds),
        "OHM_FEDERATION_DATA_DIR": str(tmp_path / "fed"),
        "OHM_ENCRYPTION_SALT": "realprocess-salt",
        "OHM_ENCRYPTION_PASSWORD": "realprocess-password",
        "LLM_ENABLED": "false",
        "OHM_FEDERATION_ENABLED": "false",
        "MATCHING_EAGER_INIT": "false",
    }


def _direct_read(marker_path: Path, heartbeat_seconds: float) -> sl.LivenessInfo:
    """Read the marker the real API subprocess wrote, in this process — fast,
    so it can make tight timing assertions the CLI's own startup cost would
    swamp. Same production `read()`, just pointed at this test's marker, with
    the same heartbeat interval the subprocess was given (the stale threshold
    is derived from it, and this process never inherits the child's env dict)."""
    overrides = {
        "OHM_STORAGE_MARKER_PATH": str(marker_path),
        "OHM_STORAGE_MARKER_HEARTBEAT_SECONDS": str(heartbeat_seconds),
    }
    previous = {k: os.environ.get(k) for k in overrides}
    os.environ.update(overrides)
    try:
        return sl.read()
    finally:
        for k, v in previous.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.fixture
def api(tmp_path):
    """A real API subprocess, torn down (killed, if still alive) after the test."""
    proc: ApiProcess = None

    def _start(heartbeat_seconds: float = 0.3) -> ApiProcess:
        nonlocal proc
        env = _base_env(tmp_path, heartbeat_seconds)
        proc = start_api(env, timeout=60)
        return proc

    yield _start, tmp_path
    if proc is not None and proc.process.poll() is None:
        proc.kill()


def test_marker_appears_and_the_heartbeat_advances_then_clean_stop_removes_it(api):
    start, tmp_path = api
    proc = start(heartbeat_seconds=0.3)
    marker = tmp_path / "api-live.json"

    assert wait_until(lambda: marker.exists(), timeout=15), proc.output()

    first = _direct_read(marker, heartbeat_seconds=0.3)
    assert first.status == sl.LivenessStatus.RUNNING
    assert first.provider == "local"
    assert first.pid == proc.process.pid

    second_beat = wait_until(
        lambda: _direct_read(marker, heartbeat_seconds=0.3).heartbeat_at
        != first.heartbeat_at,
        timeout=5,
    )
    assert second_beat, "the heartbeat never advanced past its first write"

    rc = proc.stop(timeout=15)
    assert rc == 0 or rc == -15, f"unexpected exit code {rc}: {proc.output()}"
    assert not marker.exists(), "a clean stop must remove the marker (#544 AC1)"


def test_kill_minus_9_leaves_a_stale_marker_and_forget_clears_it(api):
    start, tmp_path = api
    proc = start(heartbeat_seconds=0.3)
    marker = tmp_path / "api-live.json"
    assert wait_until(lambda: marker.exists(), timeout=15), proc.output()
    assert (
        _direct_read(marker, heartbeat_seconds=0.3).status == sl.LivenessStatus.RUNNING
    )

    proc.kill()

    assert (
        _direct_read(marker, heartbeat_seconds=0.3).status == sl.LivenessStatus.RUNNING
    ), (
        "immediately after the process dies, the marker's last heartbeat is "
        "still fresh — it must not jump straight to stale"
    )

    went_stale = wait_until(
        lambda: _direct_read(marker, heartbeat_seconds=0.3).status
        == sl.LivenessStatus.STALE,
        timeout=5,
    )
    assert went_stale, "a dead process's marker never went stale (#544 AC2)"

    env = _base_env(tmp_path, heartbeat_seconds=0.3)
    result = run_cli("storage", "status", "--forget", "--yes", env=env, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not marker.exists(), "--forget did not clear a marker known to be dead"


def test_a_marker_corrupted_after_a_kill_still_reads_as_running(api):
    """Fail closed (#544 AC3): whatever killed the process could just as well
    have killed it mid-write. A malformed marker must never look safer than a
    readable one — it must look *running*, not absent or stale."""
    start, tmp_path = api
    proc = start(heartbeat_seconds=0.3)
    marker = tmp_path / "api-live.json"
    assert wait_until(lambda: marker.exists(), timeout=15), proc.output()

    proc.kill()
    marker.write_text("{not valid json", encoding="utf-8")

    info = _direct_read(marker, heartbeat_seconds=0.3)
    assert info.status == sl.LivenessStatus.RUNNING
    assert info.error is not None

    # And it stays that way — corruption does not heal into "stale" on its own.
    time.sleep(0.5)
    assert (
        _direct_read(marker, heartbeat_seconds=0.3).status == sl.LivenessStatus.RUNNING
    )


def test_ohm_storage_status_reports_all_three_states_through_the_cli(api):
    """#544 AC5, end to end. A generous heartbeat so the CLI's own ~1-2s
    startup is never mistaken for staleness."""
    start, tmp_path = api
    env = _base_env(tmp_path, heartbeat_seconds=1.5)
    marker = tmp_path / "api-live.json"

    absent = run_cli("storage", "status", "--json", env=env, timeout=30)
    assert absent.returncode == 0, absent.stdout + absent.stderr
    assert json.loads(absent.stdout)["live"]["status"] == "absent"

    proc = start(heartbeat_seconds=1.5)
    assert wait_until(lambda: marker.exists(), timeout=15), proc.output()

    running = run_cli("storage", "status", "--json", env=env, timeout=30)
    assert running.returncode == 0, running.stdout + running.stderr
    live = json.loads(running.stdout)["live"]
    assert live["status"] == "running"
    assert live["provider"] == "local"
    assert live["pid"] == proc.process.pid

    proc.kill()
    stale = wait_until(
        lambda: _direct_read(marker, heartbeat_seconds=1.5).status
        == sl.LivenessStatus.STALE,
        timeout=10,
    )
    assert stale, "marker never went stale before the CLI check"

    stale_result = run_cli("storage", "status", "--json", env=env, timeout=30)
    assert stale_result.returncode == 0, stale_result.stdout + stale_result.stderr
    assert json.loads(stale_result.stdout)["live"]["status"] == "stale"
