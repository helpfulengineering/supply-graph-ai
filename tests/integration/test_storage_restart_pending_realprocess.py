"""Restart-pending, proven with a real API subprocess and a real CLI subprocess (#545).

The unit tests (`tests/unit/test_storage_restart_pending.py`) prove
`restart_pending_info()`'s logic against a fabricated marker. The API contract
tests (`tests/api/test_storage_restart_pending_routes.py`) prove the HTTP
surface with an in-process ASGI client. Neither can show that a CLI switch run
from a genuinely separate process is what a running API's marker fails to see
— the exact shape of the incident this whole redesign started from (#543): a
process boundary an in-process test cannot cross by construction. This file
crosses it for real, the way #539 D10 asks: an actual `uvicorn` subprocess, an
actual CLI subprocess, and — new here — a real HTTP request to the running
API's own `/health` for the one assertion only a live server can answer.
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


def _env(
    tmp_path: Path, storage_dir: Path, heartbeat_seconds: float = 1.0
) -> Dict[str, str]:
    storage_dir.mkdir(parents=True, exist_ok=True)
    return {
        **os.environ,
        "STORAGE_PROVIDER": "local",
        "LOCAL_STORAGE_PATH": str(storage_dir),
        "OHM_STORAGE_CONFIG_PATH": str(tmp_path / "cfg.json"),
        "OHM_STORAGE_MARKER_PATH": str(tmp_path / "api-live.json"),
        "OHM_STORAGE_MARKER_HEARTBEAT_SECONDS": str(heartbeat_seconds),
        "OHM_FEDERATION_DATA_DIR": str(tmp_path / "fed"),
        "OHM_ENCRYPTION_SALT": "restart-pending-realprocess-salt",
        "OHM_ENCRYPTION_PASSWORD": "restart-pending-realprocess-password",
        "LLM_ENABLED": "false",
        "OHM_FEDERATION_ENABLED": "false",
        "MATCHING_EAGER_INIT": "false",
    }


def _health_ok(base_url: str) -> bool:
    """A `wait_until` predicate must never raise: before uvicorn is actually
    serving, a connection can succeed (the launcher's socket is already
    listening) with no response yet, or be refused outright — both must read
    as "not ready", not blow up the poll loop on the first attempt."""
    try:
        return httpx.get(f"{base_url}/health", timeout=1).status_code == 200
    except httpx.HTTPError:
        return False


def _cli_switch(
    tmp_path: Path, env: Dict[str, str], bucket: Path, extra: list[str] = ()
):
    return run_cli(
        "storage",
        "config",
        "set",
        "--provider",
        "local",
        "--bucket",
        str(bucket),
        "--json",
        *extra,
        env=env,
        timeout=30,
    )


@pytest.fixture
def api(tmp_path):
    proc: ApiProcess = None

    def _start(storage_dir: Path, heartbeat_seconds: float = 1.0) -> ApiProcess:
        nonlocal proc
        env = _env(tmp_path, storage_dir, heartbeat_seconds)
        proc = start_api(env, timeout=60)
        return proc

    yield _start, tmp_path
    if proc is not None and proc.process.poll() is None:
        proc.kill()


def test_a_cli_switch_against_a_running_api_is_visible_as_pending(api):
    """#545 AC1: the CLI switches a saved config a running API never sees;
    the running API's own /health (a real HTTP call to a real process) shows
    it, and so does the CLI reading the same marker locally."""
    start, tmp_path = api
    old = tmp_path / "old"
    new = tmp_path / "new"
    proc = start(old)

    assert wait_until(lambda: _health_ok(proc.base_url), timeout=20), proc.output()

    switch = _cli_switch(tmp_path, _env(tmp_path, old), new)
    assert switch.returncode == 0, switch.stdout + switch.stderr

    health = httpx.get(f"{proc.base_url}/health", timeout=5).json()
    assert health["storage"]["restart_required"] is True

    status = run_cli("storage", "status", "--json", env=_env(tmp_path, old), timeout=30)
    assert status.returncode == 0, status.stdout + status.stderr
    payload = json.loads(status.stdout)
    assert payload["runtime"]["pending"] is True
    assert payload["runtime"]["live_bucket"] == str(old)
    assert payload["runtime"]["saved_bucket"] == str(new)


def test_a_second_switch_while_pending_is_refused_and_config_is_unchanged(api):
    """#545 AC2."""
    start, tmp_path = api
    old = tmp_path / "old"
    new = tmp_path / "new"
    third = tmp_path / "third"
    proc = start(old)
    env = _env(tmp_path, old)

    assert wait_until(lambda: _health_ok(proc.base_url), timeout=20), proc.output()

    first = _cli_switch(tmp_path, env, new)
    assert first.returncode == 0, first.stdout + first.stderr

    second = _cli_switch(tmp_path, env, third)
    assert second.returncode != 0, second.stdout + second.stderr
    output = second.stdout + second.stderr
    assert "restart is already pending" in output, output

    status = run_cli("storage", "status", "--json", env=env, timeout=30)
    payload = json.loads(status.stdout)
    assert payload["saved"]["bucket"] == str(
        new
    ), "the refused switch changed the saved config"

    migrate = run_cli(
        "storage",
        "config",
        "set",
        "--provider",
        "local",
        "--bucket",
        str(third),
        "--mode",
        "migrate",
        env=env,
        timeout=30,
    )
    assert migrate.returncode != 0
    assert "restart is already pending" in migrate.stdout + migrate.stderr


def test_after_the_api_restarts_pending_clears_and_switching_works_again(api):
    """#545 AC3: restarting means a fresh process, which is exactly what
    "restart to apply" (#539 D1) has meant since slice 0 — boot, read the
    saved config, connect to it, write a marker that now agrees."""
    start, tmp_path = api
    old = tmp_path / "old"
    new = tmp_path / "new"
    newer = tmp_path / "newer"
    proc = start(old)
    env = _env(tmp_path, old)

    assert wait_until(lambda: _health_ok(proc.base_url), timeout=20), proc.output()

    switch = _cli_switch(tmp_path, env, new)
    assert switch.returncode == 0, switch.stdout + switch.stderr

    proc.stop(timeout=15)

    restarted = start(new)  # the new process boots on whatever is now saved
    assert wait_until(
        lambda: _health_ok(restarted.base_url), timeout=20
    ), restarted.output()

    status = run_cli("storage", "status", "--json", env=env, timeout=30)
    payload = json.loads(status.stdout)
    assert payload["runtime"]["pending"] is False

    again = _cli_switch(tmp_path, env, newer)
    assert again.returncode == 0, again.stdout + again.stderr


def test_with_no_running_api_nothing_is_pending_and_the_switch_says_so(tmp_path):
    """#545 AC5: an absent (or stale) marker means nothing is pending — the
    CLI switch just works, and the boxed reminder says the next start applies
    it rather than telling the operator to restart something not running."""
    old = tmp_path / "old"
    new = tmp_path / "new"
    env = _env(tmp_path, old)

    result = _cli_switch(tmp_path, env, new)
    assert result.returncode == 0, result.stdout + result.stderr

    text_result = run_cli(
        "storage",
        "config",
        "set",
        "--provider",
        "local",
        "--bucket",
        str(tmp_path / "another"),
        env=env,
        timeout=30,
    )
    assert text_result.returncode == 0, text_result.stdout + text_result.stderr
    assert (
        "next api start will apply this"
        in (text_result.stdout + text_result.stderr).lower()
    )
