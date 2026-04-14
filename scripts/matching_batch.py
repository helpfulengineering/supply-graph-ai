#!/usr/bin/env python3
"""
Batch matching test: run ``ohm match requirements`` against every generated OKH manifest
in tests/data/okh_generation/clones/ and produce a JSON report.

Matching is performed using the Python service API directly (no HTTP server needed).
Facilities are loaded once from storage and reused across all manifests.

Typical usage:
    conda activate supply-graph-ai

    # Match all 4L manifests (default)
    python scripts/matching_batch.py --stdout-summary

    # Match a specific layer
    python scripts/matching_batch.py --layer 3L --stdout-summary

    # Match only core repos
    python scripts/matching_batch.py --core-only --stdout-summary

    # Limit to N repos for a quick sanity check
    python scripts/matching_batch.py --limit 5 --stdout-summary

Options:
    --manifests-dir   Directory containing <title-slug>-<layer>.json (or legacy <id>-<layer>.json)
                      (default: tests/data/okh_generation/clones/)
    --layer TAG       Layer suffix to match (default: 4L). Use "all" to match every layer.
    --min-confidence  Minimum confidence threshold for solutions (default: 0.3)
    --max-results     Max solutions per manifest (default: 10)
    --report          Path to write JSON report
                      (default: tests/data/matching/last_batch_report.json)
    --no-report       Skip writing the report file
    --stdout-summary  Print a human-readable summary after completion
    --core-only       Only repos present in repositories.json with core_for_regression: true
    --only-ids a,b    Comma-separated repo ids to include
    --limit N         Process at most N manifests (after filters; 0 = all)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--manifests-dir",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/clones",
        help="Directory containing generated OKH manifests",
    )
    p.add_argument(
        "--repositories-json",
        type=Path,
        default=REPO_ROOT / "tests/data/okh_generation/repositories.json",
        help="Repository list used for --core-only and repo metadata",
    )
    p.add_argument(
        "--layer",
        default="4L",
        metavar="TAG",
        help='Layer suffix to select (e.g. "3L", "4L", "4L-chunked"). Use "all" for every layer.',
    )
    p.add_argument(
        "--min-confidence",
        type=float,
        default=0.3,
        help="Minimum confidence threshold for match solutions (default: 0.3)",
    )
    p.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Max solutions per manifest (default: 10)",
    )
    p.add_argument(
        "--report",
        type=Path,
        default=REPO_ROOT / "tests/data/matching/last_batch_report.json",
        help="Output report path",
    )
    p.add_argument("--no-report", action="store_true", help="Do not write the report")
    p.add_argument(
        "--stdout-summary", action="store_true", help="Print summary to stdout"
    )
    p.add_argument(
        "--core-only",
        action="store_true",
        help="Limit to entries with core_for_regression: true in repositories.json",
    )
    p.add_argument(
        "--only-ids",
        default="",
        help="Comma-separated repo ids to include (e.g. bha-centrifuge,bha-bioreactor)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max manifests to process (0 = all)",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Manifest discovery
# ---------------------------------------------------------------------------


def _discover_manifests(
    manifests_dir: Path,
    layer: str,
    core_ids: Optional[set],
    only_ids: Optional[set],
    repo_meta: Dict[str, Any],
) -> List[Tuple[str, str, Path]]:
    """Return list of (dataset_repo_id, layer_tag, manifest_path) tuples.

    Filenames may be ``<title-slug>-<layer>.json`` or legacy ``<id>-<layer>.json``.
    Dataset id is resolved from the manifest's ``repo`` URL via *repo_meta*.
    """
    from tests.data.okh_generation.manifest_discovery import canonical_repo_url

    results: List[Tuple[str, str, Path]] = []
    url_to_id: Dict[str, str] = {}
    for rid, meta in repo_meta.items():
        u = canonical_repo_url(meta.get("url") or "")
        if u:
            url_to_id[u] = rid

    for f in sorted(manifests_dir.glob("*.json")):
        name = f.stem  # e.g. "bha-centrifuge-4L" or "open-source-rover-4L"
        if name.endswith("-bom"):
            continue

        layer_tag: Optional[str] = None
        stem_without_layer: Optional[str] = None

        for candidate_suffix in ["4L-chunked", "4L", "3L"]:
            suffix = f"-{candidate_suffix}"
            if name.endswith(suffix):
                layer_tag = candidate_suffix
                stem_without_layer = name[: -len(suffix)]
                break

        if layer_tag is None or stem_without_layer is None:
            continue

        if layer != "all" and layer_tag != layer:
            continue

        try:
            with f.open(encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue

        mu = canonical_repo_url(data.get("repo") or "")
        repo_id = url_to_id.get(mu)
        if repo_id is None and stem_without_layer in repo_meta:
            repo_id = stem_without_layer
        if repo_id is None:
            continue

        if core_ids is not None and repo_id not in core_ids:
            continue

        if only_ids is not None and repo_id not in only_ids:
            continue

        results.append((repo_id, layer_tag, f))

    return results


# ---------------------------------------------------------------------------
# Matching core (Python service API)
# ---------------------------------------------------------------------------


async def _run_one(
    manifest_path: Path,
    facilities,
    matching_service,
    min_confidence: float,
    max_results: int,
) -> Dict[str, Any]:
    """Run matching for a single manifest; return a result record."""
    import json

    from src.core.models.okh import OKHManifest

    t0 = time.monotonic()
    record: Dict[str, Any] = {
        "manifest_path": str(manifest_path.relative_to(REPO_ROOT)),
        "status": "error",
        "error": None,
        "solution_count": 0,
        "top_confidence": None,
        "top_facility_name": None,
        "process_requirements": [],
        "solutions": [],
        "elapsed_s": None,
    }

    try:
        with open(manifest_path) as fh:
            raw = json.load(fh)

        manifest = OKHManifest.from_dict(raw)
        record["okh_title"] = getattr(manifest, "title", None) or raw.get("title", "")

        # Extract requirements for diagnostic purposes
        from src.core.registry.domain_registry import DomainRegistry

        domain_services = DomainRegistry.get_domain_services("manufacturing")
        extraction = domain_services.extractor.extract_requirements(raw)
        reqs = (
            extraction.data.content.get("process_requirements", [])
            if extraction.data
            else []
        )
        record["process_requirements"] = [
            (r.get("process_name", str(r)) if isinstance(r, dict) else str(r))
            for r in reqs
        ]

        solutions = await matching_service.find_matches_with_manifest(
            okh_manifest=manifest,
            facilities=facilities,
            explicit_domain="manufacturing",
        )

        # Sort by confidence score descending
        sorted_solutions = sorted(
            solutions,
            key=lambda s: s.score if hasattr(s, "score") else 0.0,
            reverse=True,
        )[:max_results]

        # Filter by confidence
        filtered = [
            s
            for s in sorted_solutions
            if (s.score if hasattr(s, "score") else 0.0) >= min_confidence
        ]

        record["status"] = "ok"
        record["solution_count"] = len(filtered)
        if filtered:
            best = filtered[0]
            record["top_confidence"] = best.score if hasattr(best, "score") else None
            record["top_facility_name"] = (
                best.tree.facility_name
                if (hasattr(best, "tree") and best.tree)
                else None
            )

        # Compact solution summaries
        for sol in filtered:
            entry: Dict[str, Any] = {}
            if hasattr(sol, "score"):
                entry["confidence"] = sol.score
            if hasattr(sol, "tree") and sol.tree:
                entry["facility_name"] = sol.tree.facility_name
                entry["facility_id"] = (
                    str(sol.tree.okw_reference) if sol.tree.okw_reference else None
                )
                entry["match_type"] = getattr(sol.tree, "match_type", None)
                entry["capabilities_used"] = getattr(sol.tree, "capabilities_used", [])
            record["solutions"].append(entry)

    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"

    record["elapsed_s"] = round(time.monotonic() - t0, 2)
    return record


async def _run_batch(args: argparse.Namespace) -> None:
    # ------------------------------------------------------------------
    # Load repository metadata for filtering
    # ------------------------------------------------------------------
    repo_meta: Dict[str, Any] = {}
    if args.repositories_json.exists():
        with open(args.repositories_json) as fh:
            repos_data = json.load(fh)
        repos_list = (
            repos_data if isinstance(repos_data, list) else repos_data.get("repos", [])
        )
        for repo in repos_list:
            repo_meta[repo["id"]] = repo

    core_ids: Optional[set] = None
    if args.core_only:
        core_ids = {
            rid for rid, meta in repo_meta.items() if meta.get("core_for_regression")
        }

    only_ids: Optional[set] = None
    if args.only_ids.strip():
        only_ids = {s.strip() for s in args.only_ids.split(",")}

    # ------------------------------------------------------------------
    # Discover manifests
    # ------------------------------------------------------------------
    manifests = _discover_manifests(
        args.manifests_dir,
        layer=args.layer,
        core_ids=core_ids,
        only_ids=only_ids,
        repo_meta=repo_meta,
    )

    if args.limit > 0:
        manifests = manifests[: args.limit]

    if not manifests:
        print(
            "No manifests found matching the given filters. Exiting.", file=sys.stderr
        )
        sys.exit(1)

    print(
        f"Found {len(manifests)} manifest(s) to process (layer={args.layer})",
        flush=True,
    )

    # ------------------------------------------------------------------
    # Initialise storage + services (once)
    # ------------------------------------------------------------------
    print("Initialising storage and matching service...", flush=True)

    from src.core.services.okw_service import OKWService
    from src.core.services.matching_service import MatchingService

    # Reset singletons so we get a fresh connection (important when running
    # this script multiple times in the same Python process during dev)
    MatchingService._instance = None
    OKWService._instance = None

    okw_service = await OKWService.get_instance()
    matching_service = await MatchingService.get_instance()

    # Load all facilities from storage once
    facilities, _ = await okw_service.list()
    print(f"Loaded {len(facilities)} facility(ies) from storage", flush=True)

    if not facilities:
        print(
            "WARNING: No facilities found in storage. Match results will be empty.\n"
            "Run scripts/generate_synthetic_data.py and upload OKW files first.",
            file=sys.stderr,
        )

    # ------------------------------------------------------------------
    # Process each manifest
    # ------------------------------------------------------------------
    run_start = datetime.now(timezone.utc)
    batch_t0 = time.monotonic()

    results: List[Dict[str, Any]] = []

    for idx, (repo_id, layer_tag, manifest_path) in enumerate(manifests, 1):
        label = f"[{idx}/{len(manifests)}] {repo_id} ({layer_tag})"
        print(f"  {label}...", end="", flush=True)

        record = await _run_one(
            manifest_path=manifest_path,
            facilities=facilities,
            matching_service=matching_service,
            min_confidence=args.min_confidence,
            max_results=args.max_results,
        )
        record["repo_id"] = repo_id
        record["layer"] = layer_tag

        status_icon = (
            "✅"
            if record["status"] == "ok" and record["solution_count"] > 0
            else (
                "⚠️ "
                if record["status"] == "ok" and record["solution_count"] == 0
                else "❌"
            )
        )
        solutions_str = (
            f"{record['solution_count']} solution(s), best={record['top_confidence']:.2f} ({record['top_facility_name']})"
            if record["solution_count"] > 0
            else "no matches"
        )
        print(f" {status_icon}  {solutions_str}  [{record['elapsed_s']}s]", flush=True)

        results.append(record)

    total_elapsed = round(time.monotonic() - batch_t0, 1)

    # ------------------------------------------------------------------
    # Build report
    # ------------------------------------------------------------------
    ok_count = sum(1 for r in results if r["status"] == "ok")
    matched_count = sum(
        1 for r in results if r["status"] == "ok" and r["solution_count"] > 0
    )
    error_count = sum(1 for r in results if r["status"] == "error")
    no_match_count = ok_count - matched_count
    avg_solutions = (
        sum(r["solution_count"] for r in results) / len(results) if results else 0.0
    )
    avg_confidence = None
    conf_values = [
        r["top_confidence"] for r in results if r["top_confidence"] is not None
    ]
    if conf_values:
        avg_confidence = round(sum(conf_values) / len(conf_values), 3)

    report: Dict[str, Any] = {
        "run_at": run_start.isoformat(),
        "layer": args.layer,
        "facility_count": len(facilities),
        "manifest_count": len(results),
        "summary": {
            "matched": matched_count,
            "no_match": no_match_count,
            "error": error_count,
            "match_rate_pct": (
                round(matched_count / len(results) * 100, 1) if results else 0.0
            ),
            "avg_solutions_per_manifest": round(avg_solutions, 2),
            "avg_top_confidence": avg_confidence,
        },
        "total_elapsed_s": total_elapsed,
        "results": results,
    }

    # ------------------------------------------------------------------
    # Write report
    # ------------------------------------------------------------------
    if not args.no_report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with open(args.report, "w") as fh:
            json.dump(report, fh, indent=2, default=str)
        print(f"\nReport written to: {args.report.relative_to(REPO_ROOT)}", flush=True)

    # ------------------------------------------------------------------
    # Stdout summary
    # ------------------------------------------------------------------
    if args.stdout_summary:
        summary = report["summary"]
        print("\n" + "=" * 60)
        print("BATCH MATCHING SUMMARY")
        print("=" * 60)
        print(f"  Layer:           {args.layer}")
        print(f"  Manifests:       {len(results)}")
        print(f"  Facilities:      {len(facilities)}")
        print(f"  Matched:         {matched_count}  ({summary['match_rate_pct']}%)")
        print(f"  No match:        {no_match_count}")
        print(f"  Errors:          {error_count}")
        print(f"  Avg solutions:   {summary['avg_solutions_per_manifest']}")
        print(f"  Avg confidence:  {avg_confidence}")
        print(f"  Total time:      {total_elapsed}s")
        print("=" * 60)

        if error_count:
            print("\nErrors:")
            for r in results:
                if r["status"] == "error":
                    print(f"  {r['repo_id']} ({r['layer']}): {r['error']}")

        if no_match_count:
            print("\nNo matches found for:")
            for r in results:
                if r["status"] == "ok" and r["solution_count"] == 0:
                    reqs = (
                        ", ".join(r["process_requirements"])
                        or "(no process requirements extracted)"
                    )
                    print(f"  {r['repo_id']} ({r['layer']}): {reqs}")


def main() -> None:
    args = _parse_args()
    asyncio.run(_run_batch(args))


if __name__ == "__main__":
    main()
