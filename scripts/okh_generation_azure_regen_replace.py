#!/usr/bin/env python3
"""
Re-generate every OKH in Azure blob storage from its ``repo`` URL and overwrite
the same blob key (plus optional ``*-bom.json`` sidecar).

Uses the local generation engine (materials confidence routing included) and the
configured Azure storage credentials from ``.env``. Sequential, resumable via
tracker. Does not go through the HTTP API (avoids request timeouts on long runs).

Usage:
    export GITLAB_SELF_HOSTED_HOSTS=gitlab.waag.org
    uv run python scripts/okh_generation_azure_regen_replace.py --dry-run
    uv run python scripts/okh_generation_azure_regen_replace.py
    uv run python scripts/okh_generation_azure_regen_replace.py --force
    uv run python scripts/okh_generation_azure_regen_replace.py --only-keys okh/iris-case-4L.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


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
        "--tracker",
        type=Path,
        default=REPO_ROOT
        / "tests/data/okh_generation/azure_regen_replace_tracker.json",
    )
    p.add_argument("--local-mirror-dir", type=Path, default=None)
    p.add_argument("--only-keys", type=str, default="")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--no-llm-chunked", action="store_true")
    p.add_argument("--no-clone", action="store_true")
    p.add_argument("--repo-timeout-seconds", type=int, default=900)
    p.add_argument("--progress-interval-seconds", type=int, default=30)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List targets and exit without generating or writing",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-run keys already marked ok in the tracker",
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


def _bom_sidecar_key(manifest_key: str) -> str:
    if manifest_key.endswith(".json") and not manifest_key.endswith("-bom.json"):
        return manifest_key[: -len(".json")] + "-bom.json"
    return manifest_key + "-bom.json"


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


async def _discover_targets(mgr) -> List[Dict[str, Any]]:
    from src.core.storage.smart_discovery import SmartFileDiscovery

    discovery = SmartFileDiscovery(mgr)
    files = await discovery.discover_files("okh")
    targets: List[Dict[str, Any]] = []
    for f in files:
        if f.key.rstrip("/").endswith(".gitkeep"):
            continue
        data = await mgr.get_object(f.key)
        try:
            manifest = _unwrap_manifest(json.loads(data))
        except Exception as exc:
            targets.append(
                {
                    "key": f.key,
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
                "key": f.key,
                "repo": repo or None,
                "id": manifest.get("id"),
                "title": manifest.get("title"),
                "before": _materials_summary(manifest),
                "skip_reason": None if repo else "missing_repo",
            }
        )
    return targets


async def main() -> int:
    _load_repo_dotenv_if_present()
    args = _parse_args()
    os.environ.setdefault("GITLAB_SELF_HOSTED_HOSTS", "gitlab.waag.org")

    from src.core.generation.dataset_generation import generate_manifest_for_repository

    mgr = await _load_storage()
    targets = await _discover_targets(mgr)

    only = {x.strip() for x in args.only_keys.split(",") if x.strip()}
    if only:
        targets = [t for t in targets if t["key"] in only]
    runnable = [t for t in targets if t.get("repo") and not t.get("skip_reason")]
    skipped = [t for t in targets if t not in runnable]
    if args.limit > 0:
        runnable = runnable[: args.limit]

    _stderr(
        f"[azure_regen_replace] discovered={len(targets)} runnable={len(runnable)} "
        f"skipped={len(skipped)} dry_run={args.dry_run}"
    )
    for t in skipped:
        _stderr(f"  skip\t{t['key']}\t{t.get('skip_reason')}")
    for t in runnable:
        _stderr(f"  run\t{t['key']}\t{t['repo']}")

    if args.dry_run:
        return 0

    tracker_path: Path = args.tracker
    tracker_path.parent.mkdir(parents=True, exist_ok=True)
    if tracker_path.is_file() and not args.force:
        tracker = json.loads(tracker_path.read_text(encoding="utf-8"))
    else:
        tracker = {
            "schema_version": "1.0.0",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "repos": [],
        }
        if args.force and tracker_path.is_file():
            prev = json.loads(tracker_path.read_text(encoding="utf-8"))
            force_keys = {t["key"] for t in runnable}
            tracker["repos"] = [
                r for r in prev.get("repos", []) if r.get("key") not in force_keys
            ]
            tracker["started_at"] = prev.get("started_at", tracker["started_at"])

    done_keys = {
        r.get("key") for r in tracker.get("repos", []) if r.get("status") == "ok"
    }
    use_llm = not args.no_llm
    llm_chunked = bool(use_llm) and not args.no_llm_chunked
    use_clone = not args.no_clone
    mirror_dir = args.local_mirror_dir
    if mirror_dir:
        mirror_dir.mkdir(parents=True, exist_ok=True)

    errors = 0
    total = len(runnable)
    for index, target in enumerate(runnable, start=1):
        key = target["key"]
        url = target["repo"]
        if key in done_keys:
            _stderr(f"[{index}/{total}] {key}\tskipped_tracker_ok")
            continue

        t0 = time.perf_counter()
        _stderr(f"[{index}/{total}] {key}\tstarting\t{url}")
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
            # Keep stable identity for matching / existing references
            if target.get("id"):
                manifest["id"] = target["id"]

            bom_key = None
            bom_payload: Optional[str] = None
            if getattr(result, "full_bom", None) is not None:
                bom = result.full_bom
                bom_dict = bom.to_dict() if hasattr(bom, "to_dict") else bom
                bom_key = _bom_sidecar_key(key)
                bom_payload = (
                    json.dumps(bom_dict, indent=2, ensure_ascii=False, default=str)
                    + "\n"
                )
                # Point compressed summary at the storage sidecar (not a repo path)
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
            if bom_key and bom_payload is not None:
                try:
                    bom_obj = json.loads(bom_payload)
                    after["bom_components"] = len(bom_obj.get("components") or [])
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
                f"bom_comps={after.get('bom_components')}\t"
                f"{elapsed:.1f}s"
            )
        except asyncio.TimeoutError:
            errors += 1
            row.update(
                {
                    "status": "error",
                    "error": f"timeout after {args.repo_timeout_seconds}s",
                    "seconds": round(time.perf_counter() - t0, 2),
                }
            )
            _stderr(f"[{index}/{total}] {key}\terror\ttimeout")
        except Exception as exc:
            errors += 1
            row.update(
                {
                    "status": "error",
                    "error": str(exc),
                    "seconds": round(time.perf_counter() - t0, 2),
                }
            )
            _stderr(f"[{index}/{total}] {key}\terror\t{exc}")
        finally:
            if heartbeat is not None:
                heartbeat.cancel()
                try:
                    await heartbeat
                except asyncio.CancelledError:
                    pass

        tracker.setdefault("repos", []).append(row)
        tracker["updated_at"] = datetime.now(timezone.utc).isoformat()
        tracker["summary"] = {
            "ok": sum(1 for r in tracker["repos"] if r.get("status") == "ok"),
            "errors": sum(1 for r in tracker["repos"] if r.get("status") == "error"),
        }
        tracker_path.write_text(
            json.dumps(tracker, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        _stderr(f"[{index}/{total}] {key}\ttracker_updated\t{tracker_path}")

    summary = tracker.get("summary") or {}
    print(json.dumps(summary, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
