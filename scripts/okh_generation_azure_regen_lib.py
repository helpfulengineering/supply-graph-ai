"""Pure helpers for Azure OKH regen batching (no live storage I/O)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set


def bom_sidecar_key(manifest_key: str) -> str:
    if manifest_key.endswith(".json") and not manifest_key.endswith("-bom.json"):
        return manifest_key[: -len(".json")] + "-bom.json"
    return manifest_key + "-bom.json"


def is_bom_sidecar_key(key: str) -> bool:
    return key.endswith("-bom.json")


def is_manifest_key(key: str) -> bool:
    if not key.endswith(".json"):
        return False
    if is_bom_sidecar_key(key):
        return False
    if key.rstrip("/").endswith(".gitkeep"):
        return False
    return True


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_log_event(logfile: Path, event: Dict[str, Any]) -> None:
    """Append one JSON object as a line to an append-only JSONL logfile."""
    logfile.parent.mkdir(parents=True, exist_ok=True)
    row = dict(event)
    row.setdefault("ts", utc_now_iso())
    with logfile.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def load_ok_keys_from_logfile(logfile: Path) -> Set[str]:
    """Return keys that have a successful ``ok`` event in the JSONL logfile.

    If a key later has an ``error`` or ``start`` without a newer ``ok``, it is
    still considered ok once any prior ok exists unless the last event for that
    key is ``error`` (re-queue failed keys). Latest status wins.
    """
    if not logfile.is_file():
        return set()
    latest: Dict[str, str] = {}
    for line in logfile.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        key = row.get("key")
        event = row.get("event")
        if not key or not event:
            continue
        if event in {"ok", "error", "skip"}:
            latest[str(key)] = str(event)
    return {k for k, status in latest.items() if status == "ok"}


def classify_target(
    *,
    key: str,
    repo: Optional[str],
    skip_reason: Optional[str],
    ok_keys_from_log: Set[str],
    bom_keys: Set[str],
    force: bool = False,
) -> str:
    """Return classification: missing_repo | already_ok_in_log | bom_exists | pending."""
    if skip_reason == "missing_repo" or not (repo or "").strip():
        return "missing_repo"
    if force:
        return "pending"
    if key in ok_keys_from_log:
        return "already_ok_in_log"
    if bom_sidecar_key(key) in bom_keys:
        return "bom_exists"
    return "pending"


def summarize_classifications(statuses: Iterable[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {
        "missing_repo": 0,
        "already_ok_in_log": 0,
        "bom_exists": 0,
        "pending": 0,
    }
    for status in statuses:
        counts[status] = counts.get(status, 0) + 1
    return counts


def select_batch(
    pending: List[Dict[str, Any]], batch_size: int
) -> List[Dict[str, Any]]:
    if batch_size <= 0:
        return list(pending)
    return pending[:batch_size]
