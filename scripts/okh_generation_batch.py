#!/usr/bin/env python3
"""
Batch OKH generation for every supported entry in tests/data/okh_generation/repositories.json.

Writes manifests to tests/data/okh_generation/clones/<repo-id>-<layer>.json (same layout as
the baseline report expects). Optional BOM sidecar and a JSON run report for iteration.

Typical workflow (clone + BOM normalization, same as manual ``--clone --no-review``):

    export GITLAB_SELF_HOSTED_HOSTS=gitlab.waag.org   # if using Waag
    conda activate supply-graph-ai

    # 3-layer baseline (default layer tag: 3L)
    python scripts/okh_generation_batch.py --stdout-summary

    # 4-layer (LLM) — default layer tag: 4L so 3L outputs are not overwritten
    python scripts/okh_generation_batch.py --use-llm --stdout-summary

    python scripts/okh_generation_baseline_report.py
    python scripts/okh_generation_layer_compare.py

Options:
    --core-only      Only repos with core_for_regression: true
    --limit N        Process at most N repos (after filters)
    --only-ids a,b   Comma-separated repo ids
    --skip-existing  Skip if output manifest already exists
    --save-clones    Persist git clones under clones/repos/<id>/
    --llm-chunked-mode  Enable chunked LLM path (feature-flag; requires --use-llm)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


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
        help="Directory for <id>-<layer>.json outputs",
    )
    p.add_argument(
        "--report",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/last_batch_report.json",
        help="Write machine-readable run summary",
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
        help="Suffix in filenames (default: 3L without --use-llm, 4L with --use-llm)",
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
        "--use-llm",
        action="store_true",
        help="Enable 4-layer generation (LLM)",
    )
    p.add_argument(
        "--llm-chunked-mode",
        action="store_true",
        help="Enable chunked LLM mode in generation layer (feature flag; requires --use-llm)",
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
    p.add_argument("--limit", type=int, default=0, help="Max repos after filters (0=all)")
    p.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip generation if <id>-<layer>.json already exists",
    )
    p.add_argument(
        "--stdout-summary",
        action="store_true",
        help="Print one-line summary per repo to stdout",
    )
    return p.parse_args()


def _select_repos(data: Dict[str, Any], args: argparse.Namespace) -> List[Dict[str, Any]]:
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


async def _run() -> int:
    args = _parse_args()
    if args.llm_chunked_mode and not args.use_llm:
        raise SystemExit("--llm-chunked-mode requires --use-llm")
    layer_tag = args.layer if args.layer is not None else (
        "4L" if args.use_llm else "3L"
    )
    use_clone = bool(args.clone) and not args.no_clone
    if not args.clone and not args.no_clone:
        # Default: clone when user runs batch without explicit flags (safest for GitLab)
        use_clone = True

    from tests.data.okh_generation.baseline_report import load_repositories_dataset
    from tests.data.okh_generation.metrics import heuristic_manifest_quality

    from src.core.generation.dataset_generation import generate_manifest_for_repository

    data = load_repositories_dataset(args.repositories_json)
    selected = _select_repos(data, args)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.save_clones:
        (args.output_dir / "repos").mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    errors = 0

    for repo in selected:
        rid = repo.get("id", "unknown")
        url = repo.get("url")
        manifest_path = args.output_dir / f"{rid}-{layer_tag}.json"
        t0 = time.perf_counter()

        if args.skip_existing and manifest_path.is_file():
            rows.append(
                {
                    "id": rid,
                    "url": url,
                    "status": "skipped_exists",
                    "path": str(manifest_path.relative_to(REPO_ROOT)),
                }
            )
            if args.stdout_summary:
                print(f"{rid}\tskipped_exists\t{url}", file=sys.stderr)
            continue

        save_clone: Optional[Path] = None
        if args.save_clones and use_clone:
            save_clone = args.output_dir / "repos" / rid

        try:
            result = await generate_manifest_for_repository(
                url,
                clone=use_clone,
                save_clone=save_clone,
                use_llm=args.use_llm,
                include_file_metadata=args.verbose_metadata,
                llm_chunked_mode_enabled=bool(args.use_llm and args.llm_chunked_mode),
                llm_chunk_max_tokens=(
                    args.llm_chunk_max_tokens if args.llm_chunk_max_tokens > 0 else None
                ),
                llm_chunk_overlap_tokens=(
                    args.llm_chunk_overlap_tokens
                    if args.llm_chunk_overlap_tokens > 0
                    else None
                ),
            )
            manifest = result.to_okh_manifest()
            manifest_path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            bom_path = args.output_dir / f"{rid}-{layer_tag}-bom.json"
            if getattr(result, "full_bom", None) is not None:
                bom = result.full_bom
                bom_dict = bom.to_dict() if hasattr(bom, "to_dict") else bom
                bom_path.write_text(
                    json.dumps(bom_dict, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )

            elapsed = time.perf_counter() - t0
            heur = heuristic_manifest_quality(manifest)
            row = {
                "id": rid,
                "url": url,
                "status": "ok",
                "manifest_path": str(manifest_path.relative_to(REPO_ROOT)),
                "seconds": round(elapsed, 2),
                "heuristic_quality": heur,
            }
            if bom_path.is_file():
                row["bom_path"] = str(bom_path.relative_to(REPO_ROOT))
            rows.append(row)
            if args.stdout_summary:
                conf = heur.get("generation_confidence")
                leak = heur.get("function_suspected_license_leak")
                print(
                    f"{rid}\tok\tconf={conf}\tlicense_leak={leak}\t{elapsed:.1f}s",
                    file=sys.stderr,
                )
        except Exception as e:
            errors += 1
            elapsed = time.perf_counter() - t0
            rows.append(
                {
                    "id": rid,
                    "url": url,
                    "status": "error",
                    "error": str(e),
                    "seconds": round(elapsed, 2),
                }
            )
            if args.stdout_summary:
                print(f"{rid}\terror\t{e}\t{elapsed:.1f}s", file=sys.stderr)

    report: Dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repositories_json": str(args.repositories_json.relative_to(REPO_ROOT)),
        "layer": layer_tag,
        "layer_cli_override": args.layer,
        "use_clone": use_clone,
        "save_clones": bool(args.save_clones),
        "use_llm": bool(args.use_llm),
        "llm_chunked_mode": bool(args.use_llm and args.llm_chunked_mode),
        "llm_chunk_max_tokens": (
            args.llm_chunk_max_tokens if args.llm_chunk_max_tokens > 0 else None
        ),
        "llm_chunk_overlap_tokens": (
            args.llm_chunk_overlap_tokens if args.llm_chunk_overlap_tokens > 0 else None
        ),
        "selected_count": len(selected),
        "processed_count": len(rows),
        "error_count": errors,
        "repos": rows,
    }

    if not args.no_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {args.report}", file=sys.stderr)

    print(
        json.dumps(
            {
                "selected": len(selected),
                "rows": len(rows),
                "errors": errors,
            },
            indent=2,
        ),
        file=sys.stderr,
    )
    return 1 if errors else 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
