#!/usr/bin/env python3
"""
Batch re-generate OKHs in Azure blob storage (production container) from each
manifest's ``repo`` URL, writing the same blob key plus optional ``*-bom.json``.

Always runs a preflight inventory first, skips work that already exists
(successful logfile ``ok`` or existing BOM sidecar), processes at most
``--batch-size`` pending designs, and appends a JSONL process logfile.

Usage:
    uv run python scripts/okh_generation_azure_regen_batches.py --dry-run
    uv run python scripts/okh_generation_azure_regen_batches.py --batch-size 10
    uv run python scripts/okh_generation_azure_regen_batches.py --force --batch-size 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.okh_generation_azure_regen_lib import (  # noqa: E402
    append_log_event,
    bom_sidecar_key,
    classify_target,
    is_bom_sidecar_key,
    is_manifest_key,
    load_ok_keys_from_logfile,
    select_batch,
    summarize_classifications,
    utc_now_iso,
)


def _load_repo_dotenv_if_present() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_path, override=False)


def _stderr(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--logfile",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/azure_regen_batches.log.jsonl",
    )
    p.add_argument(
        "--tracker",
        type=Path,
        default=REPO_ROOT
        / "tests/data/okh_generation/azure_regen_batches_tracker.json",
    )
    p.add_argument("--local-mirror-dir", type=Path, default=None)
    p.add_argument("--only-keys", type=str, default="")
    p.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Max pending designs to process this run (0 = all pending)",
    )
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--no-llm-chunked", action="store_true")
    p.add_argument("--no-clone", action="store_true")
    p.add_argument("--repo-timeout-seconds", type=int, default=900)
    p.add_argument("--progress-interval-seconds", type=int, default=30)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Inventory + classify only; do not generate or write",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Ignore logfile ok / existing BOM sidecar skip rules",
    )
    return p.parse_args()


def _unwrap_manifest(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict) and isinstance(raw.get("okh_manifest"), dict):
        return raw["okh_manifest"]
    if isinstance(raw, dict):
        return raw
    raise ValueError("manifest payload is not a JSON object")


def _materials_summary(manifest: Dict[str, Any]) -> Dict[str, Any]:
    mats = manifest.get("materials") or []
    names = []
    for row in mats:
        if isinstance(row, dict):
            names.append(str(row.get("name") or ""))
        else:
            names.append(str(row))
    review = (manifest.get("metadata") or {}).get("generation_review") or {}
    flagged = review.get("materials") or []
    return {
        "materials_count": len(names),
        "review_flagged_count": len(flagged),
    }


async def _heartbeat(key: str, index: int, total: int, interval: float) -> None:
    start = time.perf_counter()
    while True:
        await asyncio.sleep(interval)
        _stderr(
            f"[{index}/{total}] {key}\tstill running\t"
            f"{time.perf_counter() - start:.0f}s"
        )


async def _load_storage():
    from src.config.settings import STORAGE_CONFIG
    from src.core.services.storage_service import StorageService

    storage = await StorageService.get_instance()
    if not storage._configured:
        await storage.configure(STORAGE_CONFIG)
    return storage.manager


async def _inventory(mgr) -> Dict[str, Any]:
    from src.core.storage.smart_discovery import SmartFileDiscovery

    discovery = SmartFileDiscovery(mgr)
    files = await discovery.discover_files("okh")
    bom_keys: Set[str] = set()
    targets: List[Dict[str, Any]] = []

    for f in files:
        key = f.key
        if is_bom_sidecar_key(key):
            bom_keys.add(key)
            continue
        if not is_manifest_key(key):
            continue
        data = await mgr.get_object(key)
        try:
            manifest = _unwrap_manifest(json.loads(data))
        except Exception as exc:
            targets.append(
                {
                    "key": key,
                    "repo": None,
                    "id": None,
                    "title": None,
                    "skip_reason": f"parse_error: {exc}",
                }
            )
            continue
        repo = str(manifest.get("repo") or "").strip()
        targets.append(
            {
                "key": key,
                "repo": repo or None,
                "id": manifest.get("id"),
                "title": manifest.get("title"),
                "before": _materials_summary(manifest),
                "skip_reason": None if repo else "missing_repo",
            }
        )

    return {"targets": targets, "bom_keys": bom_keys}


async def main() -> int:
    _load_repo_dotenv_if_present()
    args = _parse_args()
    os.environ.setdefault("GITLAB_SELF_HOSTED_HOSTS", "gitlab.waag.org")

    batch_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    logfile: Path = args.logfile

    from src.core.generation.dataset_generation import generate_manifest_for_repository

    mgr = await _load_storage()
    inventory = await _inventory(mgr)
    targets: List[Dict[str, Any]] = inventory["targets"]
    bom_keys: Set[str] = inventory["bom_keys"]

    only = {x.strip() for x in args.only_keys.split(",") if x.strip()}
    if only:
        targets = [t for t in targets if t["key"] in only]

    ok_keys = load_ok_keys_from_logfile(logfile)
    classified: List[Dict[str, Any]] = []
    for t in targets:
        status = classify_target(
            key=t["key"],
            repo=t.get("repo"),
            skip_reason=t.get("skip_reason"),
            ok_keys_from_log=ok_keys,
            bom_keys=bom_keys,
            force=args.force,
        )
        row = {**t, "class": status}
        classified.append(row)

    summary = summarize_classifications(r["class"] for r in classified)
    _stderr(
        f"[azure_regen_batches] batch_id={batch_id} "
        f"container inventory manifests={len(targets)} boms={len(bom_keys)} "
        f"force={args.force} dry_run={args.dry_run}"
    )
    _stderr(
        "[azure_regen_batches] preflight "
        + " ".join(f"{k}={v}" for k, v in summary.items())
    )

    append_log_event(
        logfile,
        {
            "event": "preflight",
            "batch_id": batch_id,
            "summary": summary,
            "manifest_count": len(targets),
            "bom_count": len(bom_keys),
            "force": args.force,
            "dry_run": args.dry_run,
        },
    )

    pending = [r for r in classified if r["class"] == "pending"]
    skipped = [r for r in classified if r["class"] != "pending"]
    for t in skipped:
        _stderr(f"  skip\t{t['key']}\t{t['class']}\t{t.get('skip_reason') or ''}")
        append_log_event(
            logfile,
            {
                "event": "skip",
                "batch_id": batch_id,
                "key": t["key"],
                "repo": t.get("repo"),
                "reason": t["class"],
            },
        )

    batch = select_batch(pending, args.batch_size)
    remaining_after = max(0, len(pending) - len(batch))
    _stderr(
        f"[azure_regen_batches] selected={len(batch)} "
        f"pending_total={len(pending)} remaining_after={remaining_after}"
    )
    for t in batch:
        _stderr(f"  run\t{t['key']}\t{t.get('repo')}")

    if args.dry_run:
        print(
            json.dumps(
                {
                    "batch_id": batch_id,
                    "preflight": summary,
                    "selected": len(batch),
                    "remaining_after": remaining_after,
                    "dry_run": True,
                },
                indent=2,
            )
        )
        return 0

    use_llm = not args.no_llm
    llm_chunked = bool(use_llm) and not args.no_llm_chunked
    use_clone = not args.no_clone
    mirror_dir = args.local_mirror_dir
    if mirror_dir:
        mirror_dir.mkdir(parents=True, exist_ok=True)

    tracker_path: Path = args.tracker
    tracker_path.parent.mkdir(parents=True, exist_ok=True)
    if tracker_path.is_file():
        tracker = json.loads(tracker_path.read_text(encoding="utf-8"))
    else:
        tracker = {
            "schema_version": "1.0.0",
            "started_at": utc_now_iso(),
            "repos": [],
        }

    errors = 0
    total = len(batch)
    for index, target in enumerate(batch, start=1):
        key = target["key"]
        url = target["repo"]
        t0 = time.perf_counter()
        _stderr(f"[{index}/{total}] {key}\tstarting\t{url}")
        append_log_event(
            logfile,
            {
                "event": "start",
                "batch_id": batch_id,
                "key": key,
                "repo": url,
            },
        )

        heartbeat: Optional[asyncio.Task] = None
        if args.progress_interval_seconds > 0:
            heartbeat = asyncio.create_task(
                _heartbeat(key, index, total, float(args.progress_interval_seconds))
            )

        row: Dict[str, Any] = {
            "key": key,
            "url": url,
            "id": target.get("id"),
            "title": target.get("title"),
            "before": target.get("before"),
            "batch_id": batch_id,
        }
        try:

            def _log(message: str, level: str = "info") -> None:
                _stderr(f"[{index}/{total}] {key}\t{level}\t{message}")

            gen_coro = generate_manifest_for_repository(
                url,
                clone=use_clone,
                use_llm=use_llm,
                llm_chunked_mode_enabled=bool(use_llm and llm_chunked),
                log=_log,
            )
            if args.repo_timeout_seconds > 0:
                result = await asyncio.wait_for(
                    gen_coro, timeout=float(args.repo_timeout_seconds)
                )
            else:
                result = await gen_coro

            manifest = result.to_okh_manifest(include_field_confidence=False)
            if target.get("id"):
                manifest["id"] = target["id"]

            bom_key = None
            bom_payload: Optional[str] = None
            if getattr(result, "full_bom", None) is not None:
                bom = result.full_bom
                bom_dict = bom.to_dict() if hasattr(bom, "to_dict") else bom
                bom_key = bom_sidecar_key(key)
                bom_payload = (
                    json.dumps(bom_dict, indent=2, ensure_ascii=False, default=str)
                    + "\n"
                )
                if isinstance(manifest.get("bom"), dict):
                    manifest["bom"]["external_file"] = bom_key

            payload = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
            await mgr.put_object(
                key, payload.encode("utf-8"), content_type="application/json"
            )
            if bom_key and bom_payload is not None:
                await mgr.put_object(
                    bom_key,
                    bom_payload.encode("utf-8"),
                    content_type="application/json",
                )

            if mirror_dir is not None:
                out = mirror_dir / Path(key).name
                out.write_text(payload, encoding="utf-8")
                if bom_key and bom_payload is not None:
                    (mirror_dir / Path(bom_key).name).write_text(
                        bom_payload, encoding="utf-8"
                    )

            after = _materials_summary(manifest)
            bom_components = None
            if bom_key and bom_payload is not None:
                try:
                    bom_obj = json.loads(bom_payload)
                    bom_components = len(bom_obj.get("components") or [])
                    after["bom_components"] = bom_components
                except Exception:
                    after["bom_components"] = None
            elapsed = time.perf_counter() - t0
            row.update(
                {
                    "status": "ok",
                    "after": after,
                    "bom_key": bom_key,
                    "seconds": round(elapsed, 2),
                }
            )
            _stderr(
                f"[{index}/{total}] {key}\tok\t"
                f"materials={after['materials_count']}\t"
                f"flagged={after['review_flagged_count']}\t"
                f"bom_comps={bom_components}\t"
                f"{elapsed:.1f}s"
            )
            append_log_event(
                logfile,
                {
                    "event": "ok",
                    "batch_id": batch_id,
                    "key": key,
                    "repo": url,
                    "materials_count": after["materials_count"],
                    "bom_components": bom_components,
                    "bom_key": bom_key,
                    "seconds": round(elapsed, 2),
                },
            )
        except asyncio.TimeoutError:
            errors += 1
            elapsed = round(time.perf_counter() - t0, 2)
            err = f"timeout after {args.repo_timeout_seconds}s"
            row.update({"status": "error", "error": err, "seconds": elapsed})
            _stderr(f"[{index}/{total}] {key}\terror\ttimeout")
            append_log_event(
                logfile,
                {
                    "event": "error",
                    "batch_id": batch_id,
                    "key": key,
                    "repo": url,
                    "error": err,
                    "seconds": elapsed,
                },
            )
        except Exception as exc:
            errors += 1
            elapsed = round(time.perf_counter() - t0, 2)
            row.update({"status": "error", "error": str(exc), "seconds": elapsed})
            _stderr(f"[{index}/{total}] {key}\terror\t{exc}")
            append_log_event(
                logfile,
                {
                    "event": "error",
                    "batch_id": batch_id,
                    "key": key,
                    "repo": url,
                    "error": str(exc),
                    "seconds": elapsed,
                },
            )
        finally:
            if heartbeat is not None:
                heartbeat.cancel()
                try:
                    await heartbeat
                except asyncio.CancelledError:
                    pass

        tracker.setdefault("repos", []).append(row)
        tracker["updated_at"] = utc_now_iso()
        tracker["summary"] = {
            "ok": sum(1 for r in tracker["repos"] if r.get("status") == "ok"),
            "errors": sum(1 for r in tracker["repos"] if r.get("status") == "error"),
        }
        tracker_path.write_text(
            json.dumps(tracker, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    out = {
        "batch_id": batch_id,
        "preflight": summary,
        "processed": total,
        "errors": errors,
        "remaining_after": remaining_after,
        "logfile": str(logfile),
        "tracker": str(tracker_path),
    }
    print(json.dumps(out, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
