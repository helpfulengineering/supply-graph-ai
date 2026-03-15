#!/usr/bin/env python3
"""
Compare match operations between two Azure Blob Storage containers.

For each container (e.g. "ome" and "newformats"), this script:
1. Connects to the container using the same account as configured in .env
2. Discovers OKH files (requirements) and OKW files (capabilities) under okh/ and okw/
3. Loads all OKH manifests and manufacturing OKW facilities (kitchens are skipped)
4. Runs matching: for each OKH, finds matching facilities via MatchingService.find_matches_with_manifest
5. Reports counts, errors, and per-OKH match counts for comparison

Use this to investigate why one container (e.g. newformats) fails while another (e.g. ome) works.

Usage:
    conda activate supply-graph-ai
    # Compare default containers "ome" and "newformats"
    python scripts/compare_storage_containers.py

    # Compare specific containers
    python scripts/compare_storage_containers.py --containers ome newformats

    # Single container (quick check)
    python scripts/compare_storage_containers.py --containers ome

Requires: .env with STORAGE_PROVIDER=azure_blob, AZURE_STORAGE_ACCOUNT, AZURE_STORAGE_KEY.
Container names are passed as arguments; AZURE_STORAGE_CONTAINER in .env is ignored for this script.

Run from project root so PYTHONPATH picks up src (or set PYTHONPATH to project root).
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


async def run_for_container(
    container: str,
    provider: str,
    verbose: bool,
) -> Dict[str, Any]:
    """Discover okh/okw in the given container, load them, run matching; return stats."""
    from src.config.storage_config import create_storage_config
    from src.core.models.okh import OKHManifest
    from src.core.models.okw import ManufacturingFacility
    from src.core.services.matching_service import MatchingService
    from src.core.storage.manager import StorageManager
    from src.core.storage.smart_discovery import SmartFileDiscovery
    from src.core.validation.uuid_validator import UUIDValidator
    from src.core.domains.cooking.models import KitchenCapability

    config = create_storage_config(provider, bucket_name=container)
    manager = StorageManager(config)
    try:
        await manager.connect()
    except Exception as e:
        return {
            "container": container,
            "error": f"Failed to connect: {e}",
            "okh_count": 0,
            "okw_count": 0,
            "match_requests": 0,
            "match_success": 0,
            "match_errors": 0,
            "per_okh": [],
        }

    discovery = SmartFileDiscovery(manager)
    okh_files = await discovery.discover_files("okh")
    okw_files = await discovery.discover_files("okw")

    # Load OKH manifests (with UUID fix)
    manifests: List[OKHManifest] = []
    for fi in okh_files:
        try:
            data = await manager.get_object(fi.key)
            raw = json.loads(data.decode("utf-8"))
            fixed = UUIDValidator.validate_and_fix_okh_data(raw)
            manifest = OKHManifest.from_dict(fixed)
            manifests.append(manifest)
        except Exception as e:
            if verbose:
                print(f"  [{container}] Skip OKH {fi.key}: {e}", file=sys.stderr)
            continue

    # Load OKW facilities (manufacturing only; skip kitchen-shaped), dedupe by ID (keep most recent)
    facilities_by_id: Dict[str, Any] = {}
    file_modified_by_id: Dict[str, Any] = {}
    for fi in okw_files:
        try:
            data = await manager.get_object(fi.key)
            raw = json.loads(data.decode("utf-8"))
            if KitchenCapability.is_kitchen_data(raw):
                continue
            fixed = UUIDValidator.validate_and_fix_okw_data(raw)
            fac = ManufacturingFacility.from_dict(fixed)
            fid = str(fac.id)
            current_m = getattr(fi, "last_modified", None)
            if fid not in facilities_by_id:
                facilities_by_id[fid] = fac
                file_modified_by_id[fid] = current_m
            else:
                existing_m = file_modified_by_id.get(fid)
                if current_m and (not existing_m or current_m > existing_m):
                    facilities_by_id[fid] = fac
                    file_modified_by_id[fid] = current_m
        except Exception as e:
            if verbose:
                print(f"  [{container}] Skip OKW {fi.key}: {e}", file=sys.stderr)
            continue

    facilities = list(facilities_by_id.values())

    await manager.disconnect()

    # Matching (no storage needed; we pass in-memory manifest + facilities)
    matching_service = await MatchingService.get_instance(
        okh_service=None, okw_service=None
    )
    match_success = 0
    match_errors = 0
    per_okh: List[Dict[str, Any]] = []

    for manifest in manifests:
        okh_id = str(manifest.id)
        title = getattr(manifest, "title", "") or ""
        try:
            solutions = await matching_service.find_matches_with_manifest(
                manifest, facilities, explicit_domain="manufacturing"
            )
            count = len(solutions) if solutions is not None else 0
            match_success += 1
            per_okh.append(
                {"okh_id": okh_id, "title": title[:60], "solution_count": count}
            )
        except Exception as e:
            match_errors += 1
            per_okh.append({"okh_id": okh_id, "title": title[:60], "error": str(e)})

    return {
        "container": container,
        "error": None,
        "okh_count": len(manifests),
        "okw_count": len(facilities),
        "okh_file_count": len(okh_files),
        "okw_file_count": len(okw_files),
        "match_requests": len(manifests),
        "match_success": match_success,
        "match_errors": match_errors,
        "per_okh": per_okh,
    }


def print_report(results: List[Dict[str, Any]], verbose: bool) -> None:
    """Print a side-by-side comparison and any per-OKH details if verbose."""
    print("\n" + "=" * 60)
    print("CONTAINER COMPARISON (OKH requirements vs OKW capabilities)")
    print("=" * 60)

    for r in results:
        err = r.get("error")
        if err:
            print(f"\n{r['container']}: ERROR — {err}")
            continue
        print(f"\n{r['container']}:")
        print(
            f"  OKH files discovered: {r['okh_file_count']}  →  manifests loaded: {r['okh_count']}"
        )
        print(
            f"  OKW files discovered: {r['okw_file_count']}  →  facilities (mfg) loaded: {r['okw_count']}"
        )
        print(
            f"  Match requests: {r['match_requests']}  →  success: {r['match_success']}, errors: {r['match_errors']}"
        )

    print("\n" + "-" * 60)
    if len(results) >= 2:
        a, b = results[0], results[1]
        if not a.get("error") and not b.get("error"):
            print("Summary:")
            print(
                f"  OKH load: {a['container']} has {a['okh_count']} manifests, {b['container']} has {b['okh_count']} manifests"
            )
            print(
                f"  OKW load: {a['container']} has {a['okw_count']} facilities, {b['container']} has {b['okw_count']} facilities"
            )
            print(
                f"  Match errors: {a['container']} = {a['match_errors']}, {b['container']} = {b['match_errors']}"
            )

    if verbose:
        for r in results:
            if r.get("error") or not r.get("per_okh"):
                continue
            print(f"\nPer-OKH results for {r['container']}:")
            for p in r["per_okh"]:
                if "error" in p:
                    print(
                        f"  {p['okh_id']} ({p.get('title','')}): ERROR — {p['error']}"
                    )
                else:
                    print(
                        f"  {p['okh_id']} ({p.get('title','')}): {p.get('solution_count', 0)} solution(s)"
                    )


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare match operations between storage containers (e.g. ome vs newformats)"
    )
    parser.add_argument(
        "--containers",
        nargs="+",
        default=["ome", "newformats"],
        help="Container names to compare (default: ome newformats)",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Storage provider (default: from STORAGE_PROVIDER env, else azure_blob)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print per-OKH match counts and errors",
    )
    args = parser.parse_args()

    import os

    provider = args.provider or os.getenv("STORAGE_PROVIDER", "azure_blob")

    results: List[Dict[str, Any]] = []
    for container in args.containers:
        results.append(await run_for_container(container, provider, args.verbose))

    print_report(results, args.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
