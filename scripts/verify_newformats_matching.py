#!/usr/bin/env python3
"""
Verify that matching in the 'newformats' container produces valid matches.

Loads OKH and OKW from the newformats container only, runs the same matching
flow as the compare script, and reports for each OKH:
  - Whether matching succeeded (no exception)
  - Number of solutions (matched facility sets)
  - Facility names in those solutions

Exit code: 0 if every OKH has at least one solution; 1 if any error or zero matches.
Use this to confirm that newformats data produces valid matches (e.g. for a colleague
who reports "no valid matches" — run this to verify expected behavior).

Usage:
    conda activate supply-graph-ai
    python scripts/verify_newformats_matching.py

    # Newformats is recipe + kitchen (cooking): verify with explicit cooking domain
    python scripts/verify_newformats_matching.py --domain cooking

    # Verify that domain auto-detect picks cooking when given recipes + kitchens
    python scripts/verify_newformats_matching.py --domain auto

Requires: .env with STORAGE_PROVIDER=azure_blob, AZURE_STORAGE_ACCOUNT, AZURE_STORAGE_KEY.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify matching in the newformats container produces valid matches"
    )
    parser.add_argument(
        "--container",
        default="newformats",
        help="Container to verify (default: newformats)",
    )
    parser.add_argument(
        "--domain",
        default="manufacturing",
        choices=["manufacturing", "cooking", "auto"],
        help="Domain: manufacturing (OKH vs OKW facilities), cooking (recipe vs kitchens), auto (detect from content).",
    )
    args = parser.parse_args()

    from src.config.storage_config import create_storage_config
    from src.core.models.okh import OKHManifest
    from src.core.models.okw import ManufacturingFacility
    from src.core.services.matching_service import MatchingService
    from src.core.storage.manager import StorageManager
    from src.core.storage.smart_discovery import SmartFileDiscovery
    from src.core.validation.uuid_validator import UUIDValidator
    from src.core.domains.cooking.models import KitchenCapability

    import os

    provider = os.getenv("STORAGE_PROVIDER", "azure_blob")
    config = create_storage_config(provider, bucket_name=args.container)
    manager = StorageManager(config)
    try:
        await manager.connect()
    except Exception as e:
        print(
            f"ERROR: Failed to connect to container '{args.container}': {e}",
            file=sys.stderr,
        )
        return 1

    discovery = SmartFileDiscovery(manager)
    okh_files = await discovery.discover_files("okh")
    okw_files = await discovery.discover_files("okw")

    manifests: List[OKHManifest] = []
    for fi in okh_files:
        try:
            data = await manager.get_object(fi.key)
            raw = json.loads(data.decode("utf-8"))
            fixed = UUIDValidator.validate_and_fix_okh_data(raw)
            manifest = OKHManifest.from_dict(fixed)
            manifests.append(manifest)
        except Exception as e:
            print(f"  Skip OKH {fi.key}: {e}", file=sys.stderr)
            continue

    use_cooking = args.domain in ("cooking", "auto")
    capabilities: List[Any] = []
    capabilities_label = "kitchens" if use_cooking else "facilities (manufacturing)"

    if use_cooking:
        kitchens_by_id: Dict[str, Any] = {}
        file_modified_by_id: Dict[str, Any] = {}
        for fi in okw_files:
            try:
                data = await manager.get_object(fi.key)
                raw = json.loads(data.decode("utf-8"))
                if not KitchenCapability.is_kitchen_data(raw):
                    continue
                kitchen = KitchenCapability.from_dict(raw)
                kid = str(kitchen.id)
                current_m = getattr(fi, "last_modified", None)
                if kid not in kitchens_by_id:
                    kitchens_by_id[kid] = kitchen
                    file_modified_by_id[kid] = current_m
                else:
                    existing_m = file_modified_by_id.get(kid)
                    if current_m and (not existing_m or current_m > existing_m):
                        kitchens_by_id[kid] = kitchen
                        file_modified_by_id[kid] = current_m
            except Exception as e:
                print(f"  Skip OKW (kitchen) {fi.key}: {e}", file=sys.stderr)
                continue
        capabilities = list(kitchens_by_id.values())
    else:
        facilities_by_id = {}
        file_modified_by_id = {}
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
                print(f"  Skip OKW {fi.key}: {e}", file=sys.stderr)
                continue
        capabilities = list(facilities_by_id.values())

    await manager.disconnect()

    print(f"Container: {args.container}")
    print(f"  Domain: {args.domain}")
    print(f"  OKH manifests: {len(manifests)}")
    print(f"  OKW {capabilities_label}: {len(capabilities)}")
    if not manifests:
        print("  No OKH manifests — nothing to match.", file=sys.stderr)
        return 1
    if not capabilities:
        print(
            f"  No {capabilities_label} — matching will return no solutions.",
            file=sys.stderr,
        )
        if use_cooking:
            print(
                "  Tip: For cooking, OKW files must be kitchen-shaped: no 'facility_status'; include 'appliances', 'tools', or 'ingredients'.",
                file=sys.stderr,
            )

    matching_service = await MatchingService.get_instance(
        okh_service=None, okw_service=None
    )
    explicit_domain = None if args.domain == "auto" else args.domain

    all_valid = True
    for manifest in manifests:
        okh_id = str(manifest.id)
        title = getattr(manifest, "title", "") or "(no title)"
        try:
            solutions = await matching_service.find_matches_with_manifest(
                manifest, capabilities, explicit_domain=explicit_domain
            )
            count = len(solutions) if solutions is not None else 0
            facility_names: Set[str] = set()
            if solutions:
                for sol in solutions:
                    for tree in sol.all_trees:
                        facility_names.add(tree.facility_name)
            names_str = (
                ", ".join(sorted(facility_names)) if facility_names else "(none)"
            )
            if count == 0:
                all_valid = False
                print(f"  ❌ {title[:50]} ({okh_id[:8]}...): 0 solutions — NO MATCHES")
            else:
                print(
                    f"  ✅ {title[:50]} ({okh_id[:8]}...): {count} solution(s) — facilities: {names_str}"
                )
        except Exception as e:
            all_valid = False
            print(f"  ❌ {title[:50]} ({okh_id[:8]}...): ERROR — {e}", file=sys.stderr)

    print()
    if all_valid and manifests and capabilities:
        print("Result: All OKH manifests have at least one valid match.")
        return 0
    if not manifests or not capabilities:
        print("Result: Cannot verify (missing OKH or OKW data).", file=sys.stderr)
        return 1
    print("Result: At least one OKH has no matches or an error.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
