"""Migrate's drift refusal, proven against a real writer racing a real CLI (#546).

The unit tests (`tests/unit/test_storage_migrate_drift.py`) prove
`detect_drift` and the refusal logic with a *mocked* copy step standing in
for a concurrent writer. What that cannot show is that a genuinely separate
process touching the source while a real CLI subprocess is mid-copy is what
the refusal actually catches — this crosses that process boundary for real
(#539 D10), the same way #543's original incident did.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict

import pytest

from tests.support.real_process import run_cli, wait_until

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _env(tmp_path: Path) -> Dict[str, str]:
    return {
        **os.environ,
        "STORAGE_PROVIDER": "local",
        "LOCAL_STORAGE_PATH": str(tmp_path / "old"),
        "OHM_STORAGE_CONFIG_PATH": str(tmp_path / "cfg.json"),
        "OHM_STORAGE_MARKER_PATH": str(tmp_path / "api-live.json"),
        "OHM_FEDERATION_DATA_DIR": str(tmp_path / "fed"),
        "OHM_ENCRYPTION_SALT": "migrate-drift-realprocess-salt",
        "OHM_ENCRYPTION_PASSWORD": "migrate-drift-realprocess-password",
        "LLM_ENABLED": "false",
    }


def _seed(old: Path, count: int, padded: bool = False) -> None:
    (old / "okh").mkdir(parents=True, exist_ok=True)
    pad = "x" * 2000 if padded else ""
    for i in range(count):
        (old / "okh" / f"design-{i}.json").write_text(f'{{"i": {i}, "pad": "{pad}"}}')


def test_a_real_concurrent_writer_is_caught_and_the_switch_is_refused(tmp_path):
    old = tmp_path / "old"
    new = tmp_path / "new"
    # Calibrated: 300 padded objects give the copy a real, measured ~0.8s
    # window between the first object landing at the destination and the
    # whole migrate completing — plenty of room for this test process's own
    # write to land inside it. 40 tiny objects copy too fast locally to
    # reliably race at all.
    _seed(old, 300, padded=True)
    env = _env(tmp_path)

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "src.cli",
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
        ],
        cwd=_REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Wait for the copy to actually start moving objects (not just the
        # destination's initial directory-structure setup), then write to the
        # source from THIS process — a real, separate writer.
        assert wait_until(
            lambda: new.exists() and any(new.rglob("design-*.json")), timeout=20
        ), "the destination never received a copied object"
        (old / "okh" / "design-0.json").write_text('{"i": "changed-by-a-real-writer"}')

        stdout, stderr = proc.communicate(timeout=30)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate(timeout=10)

    output = stdout + stderr
    assert proc.returncode != 0, output
    assert "changed while the copy" in output, output
    assert not (
        tmp_path / "cfg.json"
    ).exists(), f"the refused migrate persisted a configuration anyway: {output}"


def test_a_quiet_source_migrates_successfully_end_to_end(tmp_path):
    old = tmp_path / "old"
    new = tmp_path / "new"
    _seed(old, 3)
    env = _env(tmp_path)

    result = run_cli(
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

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["drift"]["clean"] is True
    assert payload["cutoff_at"] is not None
    assert (tmp_path / "cfg.json").exists()
