"""The CLI refuses the combined `abandon_and_wipe` mode, and its migrate still works (#543).

Run as a real subprocess, like an operator. The combined mode is the one that, run
from a separate process, erased the backend a running API was serving from; a test
that calls the service function in-process cannot see that, which is how it shipped.

`--wipe-confirm` and `--dry-run` are hidden but still accepted, so a caller who
follows the old docs gets the explanation instead of "No such option".
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

_ROOT = Path(__file__).resolve().parents[2]


def _ohm(tmp_path: Path, old: Path, *args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "STORAGE_PROVIDER": "local",
        "LOCAL_STORAGE_PATH": str(old),
        "OHM_STORAGE_CONFIG_PATH": str(tmp_path / "cfg.json"),
        "OHM_FEDERATION_DATA_DIR": str(tmp_path / "fed"),
        "OHM_ENCRYPTION_SALT": "cli-retired-salt",
        "OHM_ENCRYPTION_PASSWORD": "cli-retired-password",
        "LLM_ENABLED": "false",
    }
    return subprocess.run(
        [sys.executable, "-m", "src.cli", "storage", "config", "set", *args],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.fixture
def stores(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    (old / "okh").mkdir(parents=True)
    design = old / "okh" / "users-design-okh.json"
    design.write_text('{"title": "a user\'s data"}')
    return old, new, design


@pytest.mark.parametrize(
    "extra",
    [
        ["--wipe-confirm", "SAME_AS_OLD"],  # what the old docs told people to type
        [],  # and without it
        ["--wipe-confirm", "SAME_AS_OLD", "--dry-run"],
    ],
)
def test_the_combined_wipe_is_refused_and_nothing_is_erased(
    tmp_path, stores, extra
) -> None:
    old, new, design = stores
    extra = [str(old) if a == "SAME_AS_OLD" else a for a in extra]

    result = _ohm(
        tmp_path,
        old,
        "--provider",
        "local",
        "--bucket",
        str(new),
        "--mode",
        "abandon_and_wipe",
        *extra,
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "retired" in output, output
    assert design.exists(), f"the retired mode erased the old backend: {output}"
    assert not (tmp_path / "cfg.json").exists(), "and it persisted a configuration"


def test_a_plain_switch_still_works_and_leaves_the_old_data(tmp_path, stores) -> None:
    old, new, design = stores

    result = _ohm(tmp_path, old, "--provider", "local", "--bucket", str(new))

    assert result.returncode == 0, result.stdout + result.stderr
    assert design.exists()
    assert (tmp_path / "cfg.json").exists()


def test_migrate_from_the_cli_still_works(tmp_path, stores) -> None:
    """The one supported migrate path until slice 4 makes it honest about drift."""
    old, new, design = stores

    result = _ohm(
        tmp_path, old, "--provider", "local", "--bucket", str(new), "--mode", "migrate"
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (new / "okh" / "users-design-okh.json").exists()
    assert design.exists(), "migrate must not erase the source"
