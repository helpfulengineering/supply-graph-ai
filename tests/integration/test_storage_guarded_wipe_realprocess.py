"""`ohm storage wipe`, guarded against a real running API — not a fabricated marker (#547).

The unit tests (`tests/unit/test_storage_guarded_wipe.py`) prove the guard
logic against a marker file written directly. What they cannot show is that a
*real* API process — the one #543's incident actually involved — is what a
wipe attempt sees and refuses to cross. This drives the full operator
sequence D9/#547's scope describes: switch or migrate, restart, confirm
healthy, wipe — against real API and CLI subprocesses (#539 D10).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

import httpx
import pytest

from tests.support.real_process import ApiProcess, run_cli, start_api, wait_until

pytestmark = pytest.mark.integration


def _env(tmp_path: Path, storage_dir: Path) -> Dict[str, str]:
    storage_dir.mkdir(parents=True, exist_ok=True)
    return {
        **os.environ,
        "STORAGE_PROVIDER": "local",
        "LOCAL_STORAGE_PATH": str(storage_dir),
        "OHM_STORAGE_CONFIG_PATH": str(tmp_path / "cfg.json"),
        "OHM_STORAGE_MARKER_PATH": str(tmp_path / "api-live.json"),
        "OHM_STORAGE_MARKER_HEARTBEAT_SECONDS": "1",
        "OHM_FEDERATION_DATA_DIR": str(tmp_path / "fed"),
        "OHM_ENCRYPTION_SALT": "guarded-wipe-realprocess-salt",
        "OHM_ENCRYPTION_PASSWORD": "guarded-wipe-realprocess-password",
        "LLM_ENABLED": "false",
        "OHM_FEDERATION_ENABLED": "false",
        "MATCHING_EAGER_INIT": "false",
    }


def _health_ok(base_url: str) -> bool:
    try:
        return httpx.get(f"{base_url}/health", timeout=1).status_code == 200
    except httpx.HTTPError:
        return False


def _wipe(env: Dict[str, str], bucket: Path, confirm: Path, extra=()):
    return run_cli(
        "storage",
        "wipe",
        "--provider",
        "local",
        "--bucket",
        str(bucket),
        "--wipe-confirm",
        str(confirm),
        "--json",
        *extra,
        env=env,
        timeout=30,
    )


@pytest.fixture
def api(tmp_path):
    proc: ApiProcess = None

    def _start(storage_dir: Path) -> ApiProcess:
        nonlocal proc
        env = _env(tmp_path, storage_dir)
        proc = start_api(env, timeout=60)
        return proc

    yield _start, tmp_path
    if proc is not None and proc.process.poll() is None:
        proc.kill()


def test_wiping_the_backend_a_real_running_api_is_live_on_is_refused(api):
    """#547 AC1."""
    start, tmp_path = api
    old = tmp_path / "old"
    proc = start(old)
    assert wait_until(lambda: _health_ok(proc.base_url), timeout=20), proc.output()

    design = old / "okh" / "d.json"
    design.parent.mkdir(parents=True, exist_ok=True)
    design.write_text('{"title": "a real design"}')

    env = _env(tmp_path, old)
    result = _wipe(env, old, old)

    assert result.returncode != 0, result.stdout + result.stderr
    assert "a running API" in (result.stdout + result.stderr)
    assert design.exists(), "the refused wipe erased a live backend"


def test_wiping_while_a_restart_is_pending_is_refused(api):
    """#547 AC3."""
    start, tmp_path = api
    old = tmp_path / "old"
    new = tmp_path / "new"
    unrelated = tmp_path / "unrelated"
    proc = start(old)
    assert wait_until(lambda: _health_ok(proc.base_url), timeout=20), proc.output()

    env = _env(tmp_path, old)
    switch = run_cli(
        "storage",
        "config",
        "set",
        "--provider",
        "local",
        "--bucket",
        str(new),
        "--json",
        env=env,
        timeout=30,
    )
    assert switch.returncode == 0, switch.stdout + switch.stderr

    result = _wipe(env, unrelated, unrelated)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "restart is already pending" in (result.stdout + result.stderr)


def test_after_a_migrate_and_a_restart_wiping_the_old_backend_succeeds(api):
    """#547 AC4, the full documented sequence: switch or migrate, restart,
    confirm healthy, wipe. `--dry-run` first, then for real."""
    start, tmp_path = api
    old = tmp_path / "old"
    new = tmp_path / "new"
    proc = start(old)
    assert wait_until(lambda: _health_ok(proc.base_url), timeout=20), proc.output()

    design = old / "okh" / "d.json"
    design.parent.mkdir(parents=True, exist_ok=True)
    design.write_text('{"title": "migrate me"}')

    env = _env(tmp_path, old)
    migrate = run_cli(
        "storage",
        "config",
        "set",
        "--provider",
        "local",
        "--bucket",
        str(new),
        "--mode",
        "migrate",
        "--json",
        env=env,
        timeout=30,
    )
    assert migrate.returncode == 0, migrate.stdout + migrate.stderr
    assert (new / "okh" / "d.json").exists()

    # Restart: stop the old process, start a fresh one — which boots on
    # whatever is now saved (`new`), the same as a real operator restart.
    proc.stop(timeout=15)
    restarted = start(new)
    assert wait_until(
        lambda: _health_ok(restarted.base_url), timeout=20
    ), restarted.output()

    # Confirm healthy on the new backend before wiping the old one.
    health = httpx.get(f"{restarted.base_url}/health", timeout=5).json()
    assert health["storage"]["okh_count"] == 1

    dry = _wipe(_env(tmp_path, old), old, old, extra=["--dry-run"])
    assert dry.returncode == 0, dry.stdout + dry.stderr
    assert json.loads(dry.stdout)["wipe"]["dry_run"] is True
    assert design.exists()

    real = _wipe(_env(tmp_path, old), old, old)
    assert real.returncode == 0, real.stdout + real.stderr
    assert not design.exists(), "the wipe left the old design behind"
    # And the new backend, which the restarted API is actually live on, is
    # untouched.
    assert (new / "okh" / "d.json").exists()
