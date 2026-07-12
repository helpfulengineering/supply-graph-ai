"""Unit tests for Azure OKH regen batch helpers (no live Azure)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.okh_generation_azure_regen_lib import (
    append_log_event,
    bom_sidecar_key,
    classify_target,
    is_bom_sidecar_key,
    is_manifest_key,
    load_ok_keys_from_logfile,
    select_batch,
    summarize_classifications,
)


def test_bom_sidecar_key():
    assert bom_sidecar_key("okh/foo.json") == "okh/foo-bom.json"
    assert bom_sidecar_key("okh/foo-bom.json") == "okh/foo-bom.json-bom.json"


def test_manifest_vs_bom_key_filters():
    assert is_manifest_key("okh/design.json")
    assert not is_manifest_key("okh/design-bom.json")
    assert is_bom_sidecar_key("okh/design-bom.json")
    assert not is_bom_sidecar_key("okh/design.json")


def test_classify_missing_repo():
    assert (
        classify_target(
            key="okh/a.json",
            repo=None,
            skip_reason="missing_repo",
            ok_keys_from_log=set(),
            bom_keys=set(),
        )
        == "missing_repo"
    )


def test_classify_already_ok_in_log():
    assert (
        classify_target(
            key="okh/a.json",
            repo="https://github.com/x/y",
            skip_reason=None,
            ok_keys_from_log={"okh/a.json"},
            bom_keys=set(),
        )
        == "already_ok_in_log"
    )


def test_classify_bom_exists():
    assert (
        classify_target(
            key="okh/a.json",
            repo="https://github.com/x/y",
            skip_reason=None,
            ok_keys_from_log=set(),
            bom_keys={"okh/a-bom.json"},
        )
        == "bom_exists"
    )


def test_classify_pending_and_force():
    assert (
        classify_target(
            key="okh/a.json",
            repo="https://github.com/x/y",
            skip_reason=None,
            ok_keys_from_log={"okh/a.json"},
            bom_keys={"okh/a-bom.json"},
            force=False,
        )
        == "already_ok_in_log"
    )
    assert (
        classify_target(
            key="okh/a.json",
            repo="https://github.com/x/y",
            skip_reason=None,
            ok_keys_from_log={"okh/a.json"},
            bom_keys={"okh/a-bom.json"},
            force=True,
        )
        == "pending"
    )


def test_select_batch_and_summary():
    pending = [{"key": f"okh/{i}.json"} for i in range(5)]
    assert len(select_batch(pending, 2)) == 2
    assert len(select_batch(pending, 0)) == 5
    assert summarize_classifications(
        ["pending", "pending", "bom_exists", "missing_repo"]
    ) == {
        "missing_repo": 1,
        "already_ok_in_log": 0,
        "bom_exists": 1,
        "pending": 2,
    }


def test_logfile_ok_keys_latest_wins(tmp_path: Path):
    log = tmp_path / "batch.log.jsonl"
    append_log_event(log, {"event": "ok", "key": "okh/a.json"})
    append_log_event(log, {"event": "ok", "key": "okh/b.json"})
    append_log_event(log, {"event": "error", "key": "okh/b.json", "error": "boom"})
    append_log_event(log, {"event": "preflight", "summary": {}})

    ok_keys = load_ok_keys_from_logfile(log)
    assert ok_keys == {"okh/a.json"}

    # lines are valid JSONL
    lines = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x]
    assert all("ts" in row for row in lines)
    assert lines[0]["event"] == "ok"
