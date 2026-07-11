#!/usr/bin/env python3
"""
Sequential OKH regen with before/after Materials metrics tracker.

For each selected repo (default: core_for_regression):
  1. Score the existing Phase-4 manifest under --before-dir (if present)
  2. Re-generate from the source URL into --after-dir (one repo at a time)
  3. Score the new manifest and append a comparison row to --tracker

Does not write to cloud storage. Review the tracker before any upload.

Usage:
    export GITLAB_SELF_HOSTED_HOSTS=gitlab.waag.org
    uv run python scripts/okh_generation_materials_regen_compare.py --core-only
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
        "--repositories-json",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/repositories.json",
    )
    p.add_argument(
        "--before-dir",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/clones",
        help="Existing manifests to score as baseline (Phase 4 canary)",
    )
    p.add_argument(
        "--after-dir",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/clones-regen",
        help="Directory for freshly generated manifests",
    )
    p.add_argument(
        "--tracker",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/materials_regen_tracker.json",
        help="Incremental before/after comparison JSON (rewritten after each repo)",
    )
    p.add_argument("--layer", default="4L")
    p.add_argument("--core-only", action="store_true")
    p.add_argument("--only-ids", type=str, default="")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--no-llm-chunked", action="store_true")
    p.add_argument("--repo-timeout-seconds", type=int, default=600)
    p.add_argument("--progress-interval-seconds", type=int, default=30)
    p.add_argument("--no-clone", action="store_true")
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if tracker already has status=ok for a repo",
    )
    return p.parse_args()


def _select_repos(
    data: Dict[str, Any], args: argparse.Namespace
) -> List[Dict[str, Any]]:
    only = {x.strip() for x in args.only_ids.split(",") if x.strip()}
    out: List[Dict[str, Any]] = []
    for repo in data.get("repos", []):
        if not repo.get("platform_supported"):
            continue
        if args.core_only and not repo.get("core_for_regression"):
            continue
        rid = repo.get("id", "")
        if only and rid not in only:
            continue
        out.append(repo)
        if args.limit and len(out) >= args.limit:
            break
    return out


def _materials_slice(heur: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "materials_count": heur.get("materials_count"),
        "materials_near_dup_pairs": heur.get("materials_near_dup_pairs"),
        "materials_prose_like_count": heur.get("materials_prose_like_count"),
        "materials_quality_score": heur.get("materials_quality_score"),
    }


def _delta(
    before: Optional[Dict[str, Any]], after: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    if not before or not after:
        return {}
    return {
        "near_dup_delta": int(after["materials_near_dup_pairs"])
        - int(before["materials_near_dup_pairs"]),
        "prose_delta": int(after["materials_prose_like_count"])
        - int(before["materials_prose_like_count"]),
        "quality_delta": round(
            float(after["materials_quality_score"])
            - float(before["materials_quality_score"]),
            4,
        ),
        "count_delta": int(after["materials_count"]) - int(before["materials_count"]),
        "improved": (
            int(after["materials_near_dup_pairs"])
            <= int(before["materials_near_dup_pairs"])
            and int(after["materials_prose_like_count"])
            <= int(before["materials_prose_like_count"])
            and float(after["materials_quality_score"])
            >= float(before["materials_quality_score"])
        ),
    }


def _load_tracker(path: Path) -> Dict[str, Any]:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema_version": "1.0.0",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "repos": [],
    }


def _write_tracker(path: Path, tracker: Dict[str, Any]) -> None:
    tracker["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(tracker, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


async def _heartbeat(rid: str, index: int, total: int, interval: float) -> None:
    started = time.perf_counter()
    while True:
        await asyncio.sleep(interval)
        _stderr(
            f"[{index}/{total}] {rid}\tstill running\t"
            f"{time.perf_counter() - started:.0f}s"
        )


async def _run() -> int:
    args = _parse_args()
    _load_repo_dotenv_if_present()

    use_llm = not args.no_llm
    llm_chunked = bool(use_llm) and not args.no_llm_chunked
    use_clone = not args.no_clone
    layer_tag = args.layer if args.layer else ("4L" if use_llm else "3L")

    from tests.data.okh_generation.baseline_report import load_repositories_dataset
    from tests.data.okh_generation.manifest_discovery import (
        allocate_unique_slug,
        find_generated_manifest_path,
        title_slug_for_filename,
    )
    from tests.data.okh_generation.metrics import heuristic_manifest_quality
    from src.core.generation.dataset_generation import generate_manifest_for_repository

    before_dir = args.before_dir.expanduser().resolve()
    after_dir = args.after_dir.expanduser().resolve()
    tracker_path = args.tracker.expanduser().resolve()
    after_dir.mkdir(parents=True, exist_ok=True)

    data = load_repositories_dataset(args.repositories_json.expanduser().resolve())
    selected = _select_repos(data, args)
    total = len(selected)
    tracker = _load_tracker(tracker_path)
    tracker["before_dir"] = str(before_dir.relative_to(REPO_ROOT))
    tracker["after_dir"] = str(after_dir.relative_to(REPO_ROOT))
    tracker["layer"] = layer_tag
    if args.force:
        selected_ids = {str(r.get("id") or "") for r in selected}
        tracker["repos"] = [
            r for r in tracker.get("repos", []) if r.get("id") not in selected_ids
        ]
        done_ids = set()
    else:
        done_ids = {
            r.get("id") for r in tracker.get("repos", []) if r.get("status") == "ok"
        }

    _stderr(
        f"[materials_regen_compare] selected={total} layer={layer_tag} "
        f"before={before_dir} after={after_dir} tracker={tracker_path}"
    )

    used_stems: set[str] = set()
    for existing in after_dir.glob(f"*-{layer_tag}.json"):
        stem = existing.name[: -len(f"-{layer_tag}.json")]
        used_stems.add(stem)

    errors = 0
    for index, repo in enumerate(selected, start=1):
        rid = str(repo.get("id") or "unknown")
        url = repo.get("url")
        if rid in done_ids:
            _stderr(f"[{index}/{total}] {rid}\tskipped_tracker_ok")
            continue

        before_path = (
            find_generated_manifest_path(before_dir, layer_tag, url, dataset_id=rid)
            if url
            else None
        )
        before_heur = None
        if before_path and before_path.is_file():
            before_manifest = json.loads(before_path.read_text(encoding="utf-8"))
            before_heur = _materials_slice(heuristic_manifest_quality(before_manifest))

        t0 = time.perf_counter()
        _stderr(f"[{index}/{total}] {rid}\tstarting\t{url}")
        heartbeat: Optional[asyncio.Task] = None
        if args.progress_interval_seconds > 0:
            heartbeat = asyncio.create_task(
                _heartbeat(rid, index, total, float(args.progress_interval_seconds))
            )

        row: Dict[str, Any] = {
            "id": rid,
            "url": url,
            "before_path": (
                str(before_path.relative_to(REPO_ROOT))
                if before_path and before_path.is_file()
                else None
            ),
            "before": before_heur,
        }

        try:

            def _log(message: str, level: str = "info") -> None:
                _stderr(f"[{index}/{total}] {rid}\t{level}\t{message}")

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
            title_raw = manifest.get("title")
            title_str = title_raw.strip() if isinstance(title_raw, str) else ""
            stem = allocate_unique_slug(
                title_slug_for_filename(title_str, rid), used_stems
            )
            after_path = after_dir / f"{stem}-{layer_tag}.json"
            after_path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            after_heur = _materials_slice(heuristic_manifest_quality(manifest))
            elapsed = time.perf_counter() - t0
            delta = _delta(before_heur, after_heur)
            row.update(
                {
                    "status": "ok",
                    "after_path": str(after_path.relative_to(REPO_ROOT)),
                    "after": after_heur,
                    "delta": delta,
                    "seconds": round(elapsed, 2),
                }
            )
            _stderr(
                f"[{index}/{total}] {rid}\tok\t"
                f"before_prose={before_heur and before_heur.get('materials_prose_like_count')}\t"
                f"after_prose={after_heur.get('materials_prose_like_count')}\t"
                f"before_dups={before_heur and before_heur.get('materials_near_dup_pairs')}\t"
                f"after_dups={after_heur.get('materials_near_dup_pairs')}\t"
                f"improved={delta.get('improved')}\t"
                f"{elapsed:.1f}s"
            )
        except asyncio.TimeoutError:
            errors += 1
            row.update(
                {
                    "status": "error",
                    "error": f"repo timeout after {args.repo_timeout_seconds}s",
                    "seconds": round(time.perf_counter() - t0, 2),
                }
            )
            _stderr(f"[{index}/{total}] {rid}\terror\ttimeout")
        except Exception as exc:
            errors += 1
            row.update(
                {
                    "status": "error",
                    "error": str(exc),
                    "seconds": round(time.perf_counter() - t0, 2),
                }
            )
            _stderr(f"[{index}/{total}] {rid}\terror\t{exc}")
        finally:
            if heartbeat is not None:
                heartbeat.cancel()
                try:
                    await heartbeat
                except asyncio.CancelledError:
                    pass
            # Replace any prior row for this id, then append
            tracker["repos"] = [
                r for r in tracker.get("repos", []) if r.get("id") != rid
            ]
            tracker["repos"].append(row)
            ok_rows = [r for r in tracker["repos"] if r.get("status") == "ok"]
            tracker["summary"] = {
                "ok": len(ok_rows),
                "errors": sum(
                    1 for r in tracker["repos"] if r.get("status") == "error"
                ),
                "improved_count": sum(
                    1 for r in ok_rows if (r.get("delta") or {}).get("improved")
                ),
                "not_improved_count": sum(
                    1
                    for r in ok_rows
                    if r.get("delta") and not r["delta"].get("improved")
                ),
            }
            _write_tracker(tracker_path, tracker)
            _stderr(f"[{index}/{total}] {rid}\ttracker_updated\t{tracker_path}")

    _stderr(json.dumps(tracker.get("summary", {}), indent=2))
    return 1 if errors else 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
