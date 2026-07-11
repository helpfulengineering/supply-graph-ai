#!/usr/bin/env python3
"""
Batch OKH generation for every supported entry in tests/data/okh_generation/repositories.json.

Writes manifests to **tests/data/okh_generation/clones/** by default using the
generated OKH **title** as a kebab-case stem: ``<title-slug>-<layer>.json`` (e.g.
``open-source-rover-4L.json``), plus an optional ``-<layer>-bom.json`` sidecar.
The dataset ``id`` from ``repositories.json`` is only used for ``--only-ids``,
clone paths under ``repos/<id>/``, and report metadata—not for the manifest
filename. Override ``--output-dir`` for other layouts. Run report defaults to
**tests/data/okh_generation/last_batch_report.json**.

Typical workflow (clone + BOM normalization, same as manual ``--clone --no-review``):

    # Optional for GitLab API extractors; local git clone also works for
    # https://host/group/project when the path has namespace + project.
    export GITLAB_SELF_HOSTED_HOSTS=gitlab.waag.org   # if using Waag API fallback
    # From repo root: uv sync --extra dev

    # 3-layer baseline (default layer tag: 3L)
    uv run python scripts/okh_generation_batch.py --no-llm

    # 4-layer (LLM + chunked map-reduce) — default; layer tag 4L
    uv run python scripts/okh_generation_batch.py

    # Fast batch without LLM
    uv run python scripts/okh_generation_batch.py --no-llm

    uv run python scripts/okh_generation_baseline_report.py
    uv run python scripts/okh_generation_layer_compare.py

Options:
    --core-only      Only repos with core_for_regression: true
    --limit N        Process at most N repos (after filters)
    --only-ids a,b   Comma-separated repo ids
    --skip-existing  Skip if a manifest for the same repo URL already exists
                     in the output dir (legacy ``<id>-<layer>.json`` or title slug)
    --save-clones    Persist git clones under clones/repos/<id>/
    --no-llm         3-layer manifests only (skip LLM)
    --no-llm-chunked Single LLM request per repo (no map-reduce; may truncate)
    --llm-chunked-mode  Redundant with defaults; kept for backward compatibility
    --repo-timeout-seconds N   Per-repo wall-clock limit (default 600; 0 = none)
    --progress-interval-seconds N  Heartbeat while a repo runs (default 30; 0 = off)

Environment:
    ``GITLAB_SELF_HOSTED_HOSTS`` is read from :func:`os.environ` each time the
    router checks a URL (not cached at import). This script also loads the
    repo-root ``.env`` at startup with ``override=False`` so shell exports win
    over file values. Use ``--no-env-banner`` to hide the startup diagnostic line.
    ``OHM_GIT_CLONE_TIMEOUT`` — git clone timeout in seconds (default 300).
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
    """Load ``REPO_ROOT/.env`` without overriding variables already set in the environment."""
    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_path, override=False)


def _print_gitlab_self_hosted_banner() -> None:
    """Stderr one-liner: what this Python process sees for GitLab allowlist."""
    from src.core.generation.gitlab_instance import parse_self_hosted_gitlab_hosts

    raw = os.environ.get("GITLAB_SELF_HOSTED_HOSTS", "")
    hosts = parse_self_hosted_gitlab_hosts()
    if hosts:
        print(
            "[okh_generation_batch] GITLAB_SELF_HOSTED_HOSTS="
            f"{raw!r} → parsed: {sorted(hosts)}",
            file=sys.stderr,
        )
    else:
        print(
            "[okh_generation_batch] GITLAB_SELF_HOSTED_HOSTS unset or empty in this process "
            f"(raw={raw!r}). "
            "Use `export` in the same terminal that runs `python`, or set it in repo-root `.env`. "
            "IDE / task runners often do not inherit your interactive shell exports.",
            file=sys.stderr,
        )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--repositories-json",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/repositories.json",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/clones",
        help=(
            "Directory for <title-slug>-<layer>.json outputs "
            "(default: tests/data/okh_generation/clones)"
        ),
    )
    p.add_argument(
        "--report",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/last_batch_report.json",
        help=(
            "Write machine-readable run summary "
            "(default: tests/data/okh_generation/last_batch_report.json)"
        ),
    )
    p.add_argument(
        "--no-report",
        action="store_true",
        help="Do not write last_batch_report.json",
    )
    p.add_argument(
        "--layer",
        default=None,
        metavar="TAG",
        help="Suffix in filenames (default: 3L with --no-llm, 4L otherwise)",
    )
    p.add_argument(
        "--clone",
        action="store_true",
        help="Use local git clone when the router supports it (recommended)",
    )
    p.add_argument(
        "--no-clone",
        action="store_true",
        help="Force API extractors even when cloning is supported",
    )
    p.add_argument(
        "--save-clones",
        action="store_true",
        help="Persist clones under <output-dir>/repos/<repo-id>/",
    )
    p.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM (3-layer / 3L manifests only)",
    )
    p.add_argument(
        "--use-llm",
        action="store_true",
        help="[Deprecated] LLM is on by default; this flag is a no-op",
    )
    p.add_argument(
        "--no-llm-chunked",
        action="store_true",
        help="Disable chunked LLM map-reduce (one request per repo; may truncate)",
    )
    p.add_argument(
        "--llm-chunked-mode",
        action="store_true",
        help="[Deprecated] Chunking is on by default when LLM runs",
    )
    p.add_argument(
        "--llm-chunk-max-tokens",
        type=int,
        default=0,
        help="Override chunk max tokens when --llm-chunked-mode is enabled (0 = default)",
    )
    p.add_argument(
        "--llm-chunk-overlap-tokens",
        type=int,
        default=0,
        help="Override chunk overlap tokens when --llm-chunked-mode is enabled (0 = default)",
    )
    p.add_argument(
        "--verbose-metadata",
        action="store_true",
        help="Include per-file metadata in manifests (CLI --verbose)",
    )
    p.add_argument(
        "--include-confidence",
        action="store_true",
        help="Include per-field confidence scores in manifest metadata (development aid; off by default)",
    )
    p.add_argument(
        "--core-only",
        action="store_true",
        help="Only entries with core_for_regression: true",
    )
    p.add_argument(
        "--only-ids",
        type=str,
        default="",
        help="Comma-separated repo ids (e.g. repo-001,repo-002)",
    )
    p.add_argument(
        "--limit", type=int, default=0, help="Max repos after filters (0=all)"
    )
    p.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip if a manifest for this repo URL already exists (see module docstring)",
    )
    p.add_argument(
        "--stdout-summary",
        action="store_true",
        help="[Deprecated] Progress lines are always printed to stderr",
    )
    p.add_argument(
        "--no-env-banner",
        action="store_true",
        help="Do not print GITLAB_SELF_HOSTED_HOSTS diagnostic to stderr at startup",
    )
    p.add_argument(
        "--repo-timeout-seconds",
        type=int,
        default=600,
        help="Per-repo wall-clock timeout in seconds (default 600; 0 disables)",
    )
    p.add_argument(
        "--progress-interval-seconds",
        type=int,
        default=30,
        help="Print heartbeat every N seconds while a repo runs (default 30; 0 off)",
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


def _stderr(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _rel_to_repo(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def _write_report(
    path: Path,
    *,
    args: argparse.Namespace,
    layer_tag: str,
    use_llm: bool,
    llm_chunked: bool,
    use_clone: bool,
    selected: List[Dict[str, Any]],
    rows: List[Dict[str, Any]],
    errors: int,
) -> None:
    report: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repositories_json": str(args.repositories_json.relative_to(REPO_ROOT)),
        "layer": layer_tag,
        "layer_cli_override": args.layer,
        "use_clone": use_clone,
        "save_clones": bool(args.save_clones),
        "use_llm": bool(use_llm),
        "llm_chunked_mode": bool(use_llm and llm_chunked),
        "llm_chunk_max_tokens": (
            args.llm_chunk_max_tokens if args.llm_chunk_max_tokens > 0 else None
        ),
        "llm_chunk_overlap_tokens": (
            args.llm_chunk_overlap_tokens if args.llm_chunk_overlap_tokens > 0 else None
        ),
        "repo_timeout_seconds": args.repo_timeout_seconds,
        "selected_count": len(selected),
        "processed_count": len(rows),
        "error_count": errors,
        "repos": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
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
    if not args.no_env_banner:
        _print_gitlab_self_hosted_banner()

    use_llm = not args.no_llm
    if args.use_llm and args.no_llm:
        raise SystemExit("Cannot combine --use-llm with --no-llm")
    llm_chunked = bool(use_llm) and not args.no_llm_chunked
    if args.llm_chunked_mode and use_llm:
        llm_chunked = True
    layer_tag = args.layer if args.layer is not None else ("4L" if use_llm else "3L")
    # Default: clone unless --no-clone (--clone is redundant with the default).
    use_clone = not args.no_clone

    from tests.data.okh_generation.baseline_report import load_repositories_dataset
    from tests.data.okh_generation.manifest_discovery import (
        allocate_unique_slug,
        find_generated_manifest_path,
        title_slug_for_filename,
    )
    from tests.data.okh_generation.metrics import heuristic_manifest_quality

    from src.core.generation.dataset_generation import generate_manifest_for_repository

    args.output_dir = args.output_dir.expanduser().resolve()
    args.report = args.report.expanduser().resolve()
    args.repositories_json = args.repositories_json.expanduser().resolve()

    data = load_repositories_dataset(args.repositories_json)
    selected = _select_repos(data, args)
    total = len(selected)
    _stderr(
        f"[okh_generation_batch] selected={total} layer={layer_tag} "
        f"use_llm={use_llm} use_clone={use_clone} "
        f"repo_timeout={args.repo_timeout_seconds}s "
        f"output={args.output_dir}"
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.save_clones:
        (args.output_dir / "repos").mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    errors = 0
    used_output_stems: set[str] = set()

    def _persist_report() -> None:
        if not args.no_report:
            _write_report(
                args.report,
                args=args,
                layer_tag=layer_tag,
                use_llm=use_llm,
                llm_chunked=llm_chunked,
                use_clone=use_clone,
                selected=selected,
                rows=rows,
                errors=errors,
            )

    def _record_error(
        rid: str, url: Any, message: str, elapsed: float, index: int
    ) -> None:
        nonlocal errors
        errors += 1
        rows.append(
            {
                "id": rid,
                "url": url,
                "status": "error",
                "error": message,
                "seconds": round(elapsed, 2),
            }
        )
        _stderr(f"[{index}/{total}] {rid}\terror\t{message}\t{elapsed:.1f}s")

    for index, repo in enumerate(selected, start=1):
        rid = repo.get("id", "unknown")
        url = repo.get("url")
        t0 = time.perf_counter()
        _stderr(f"[{index}/{total}] {rid}\tstarting\t{url}")

        if args.skip_existing and url:
            existing = find_generated_manifest_path(
                args.output_dir, layer_tag, url, dataset_id=rid
            )
            if existing is not None:
                rel = _rel_to_repo(existing)
                rows.append(
                    {
                        "id": rid,
                        "url": url,
                        "status": "skipped_exists",
                        "path": rel,
                        "manifest_path": rel,
                    }
                )
                _stderr(f"[{index}/{total}] {rid}\tskipped_exists\t{rel}")
                _persist_report()
                continue

        save_clone: Optional[Path] = None
        if args.save_clones and use_clone:
            save_clone = args.output_dir / "repos" / rid

        def _batch_log(message: str, level: str = "info") -> None:
            _stderr(f"[{index}/{total}] {rid}\t{level}\t{message}")

        heartbeat: Optional[asyncio.Task] = None
        if args.progress_interval_seconds > 0:
            heartbeat = asyncio.create_task(
                _heartbeat(rid, index, total, float(args.progress_interval_seconds))
            )

        try:
            gen_coro = generate_manifest_for_repository(
                url,
                clone=use_clone,
                save_clone=save_clone,
                use_llm=use_llm,
                include_file_metadata=args.verbose_metadata,
                llm_chunked_mode_enabled=bool(use_llm and llm_chunked),
                llm_chunk_max_tokens=(
                    args.llm_chunk_max_tokens if args.llm_chunk_max_tokens > 0 else None
                ),
                llm_chunk_overlap_tokens=(
                    args.llm_chunk_overlap_tokens
                    if args.llm_chunk_overlap_tokens > 0
                    else None
                ),
                log=_batch_log,
            )
            if args.repo_timeout_seconds > 0:
                result = await asyncio.wait_for(
                    gen_coro, timeout=float(args.repo_timeout_seconds)
                )
            else:
                result = await gen_coro

            manifest = result.to_okh_manifest(
                include_field_confidence=args.include_confidence
            )
            title_raw = manifest.get("title")
            title_str = title_raw.strip() if isinstance(title_raw, str) else ""
            output_stem = allocate_unique_slug(
                title_slug_for_filename(title_str, rid), used_output_stems
            )
            manifest_path = args.output_dir / f"{output_stem}-{layer_tag}.json"
            manifest_path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            bom_path = args.output_dir / f"{output_stem}-{layer_tag}-bom.json"
            if getattr(result, "full_bom", None) is not None:
                bom = result.full_bom
                bom_dict = bom.to_dict() if hasattr(bom, "to_dict") else bom
                bom_path.write_text(
                    json.dumps(bom_dict, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )

            elapsed = time.perf_counter() - t0
            heur = heuristic_manifest_quality(manifest)
            row: Dict[str, Any] = {
                "id": rid,
                "output_stem": output_stem,
                "url": url,
                "status": "ok",
                "manifest_path": _rel_to_repo(manifest_path),
                "seconds": round(elapsed, 2),
                "heuristic_quality": heur,
            }
            if bom_path.is_file():
                row["bom_path"] = _rel_to_repo(bom_path)
            rows.append(row)
            _stderr(
                f"[{index}/{total}] {rid}\tok\t"
                f"conf={heur.get('generation_confidence')}\t"
                f"materials_prose={heur.get('materials_prose_like_count')}\t"
                f"near_dups={heur.get('materials_near_dup_pairs')}\t"
                f"{elapsed:.1f}s"
            )
        except asyncio.TimeoutError:
            _record_error(
                rid,
                url,
                f"repo timeout after {args.repo_timeout_seconds}s",
                time.perf_counter() - t0,
                index,
            )
        except Exception as e:
            _record_error(rid, url, str(e), time.perf_counter() - t0, index)
        finally:
            if heartbeat is not None:
                heartbeat.cancel()
                try:
                    await heartbeat
                except asyncio.CancelledError:
                    pass
            _persist_report()

    if not args.no_report:
        _stderr(f"Wrote {args.report}")

    _stderr(
        json.dumps(
            {"selected": len(selected), "rows": len(rows), "errors": errors},
            indent=2,
        )
    )
    return 1 if errors else 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
