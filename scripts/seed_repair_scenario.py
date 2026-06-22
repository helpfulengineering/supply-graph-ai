#!/usr/bin/env python3
"""
Seed a local OHM storage directory with a realistic repair-workflow scenario.

Creates four device types (ventilator, oxygen concentrator, pulse oximeter, CPAP)
in varying states of disrepair, then writes OKH manifests and AssetRecords to
the correct local-storage layout so the OHM service can read them directly.

Storage layout written:
    <storage_dir>/okh/{manifest_uuid}.json
    <storage_dir>/asset/{asset_uuid}.json

Usage:
    # Use a temp dir (default)
    python scripts/seed_repair_scenario.py

    # Specify an existing directory
    python scripts/seed_repair_scenario.py --storage-dir /tmp/my-repair-test

    # Set the same dir and start the server (STORAGE_PROVIDER=local overrides .env)
    STORAGE_PROVIDER=local LOCAL_STORAGE_PATH=/tmp/ohm-repair-test uvicorn src.core.main:app --port 8001

    # Then run the integration tests
    RUN_LIVE_API_TESTS=1 pytest tests/integration/ -v
"""

import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

# Resolve project root so imports work from any cwd
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from core.models.asset import AssetRecord, AssetStatus  # noqa: E402
from core.models.okh import OKHManifest  # noqa: E402

# Import generators from generate_synthetic_data
sys.path.insert(0, str(_ROOT / "scripts"))
from generate_synthetic_data import AssetGenerator  # noqa: E402


# ---------------------------------------------------------------------------
# Scenario distribution — controls how many assets per scenario per device type.
# Deliberately uneven to exercise all branches of the repair workflow.
# ---------------------------------------------------------------------------
SCENARIO_DISTRIBUTION = {
    "active": 4,  # healthy pool in service
    "under_triage": 3,  # damage assessment in progress
    "parts_pending": 2,  # sourcing step
    "under_repair": 1,  # repair in progress
    "restored": 1,  # successfully repaired
    "condemned": 3,  # harvest pool (harvest_viable=True on intact components)
}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def seed(storage_dir: Path) -> dict:
    """Populate *storage_dir* with manifests and assets; return a summary dict."""
    okh_dir = storage_dir / "okh"
    asset_dir = storage_dir / "asset"
    okh_dir.mkdir(parents=True, exist_ok=True)
    asset_dir.mkdir(parents=True, exist_ok=True)

    gen = AssetGenerator(complexity="mixed")
    manifests: dict[str, OKHManifest] = {}
    assets_by_type: dict[str, list[AssetRecord]] = {}

    # 1. Generate one manifest per device template
    for tmpl in AssetGenerator.DEVICE_TEMPLATES:
        manifest = gen.generate_device_manifest(tmpl)
        manifests[tmpl["type"]] = manifest
        manifest_path = okh_dir / f"{manifest.id}.json"
        _write_json(manifest_path, manifest.to_dict())
        print(
            f"  [manifest] {tmpl['type']:20s}  id={manifest.id}  → {manifest_path.relative_to(storage_dir)}"
        )

    # 2. Wire compatible_manifest_ids between the ventilator and CPAP manifests
    #    (they share blower/motor components — exercises GAP-8 cross-manifest search)
    vent = manifests.get("ventilator")
    cpap = manifests.get("cpap")
    if vent and cpap:
        vent.compatible_manifest_ids = [str(cpap.id)]
        cpap.compatible_manifest_ids = [str(vent.id)]
        _write_json(okh_dir / f"{vent.id}.json", vent.to_dict())
        _write_json(okh_dir / f"{cpap.id}.json", cpap.to_dict())
        print(f"  [compat]   ventilator ↔ cpap  (GAP-8 cross-manifest salvage-match)")

    # 3. Generate the asset fleet for each device type
    for tmpl in AssetGenerator.DEVICE_TEMPLATES:
        dtype = tmpl["type"]
        manifest = manifests[dtype]
        fleet = gen.generate_fleet(
            manifest,
            tag_prefix=tmpl["tag_prefix"],
            scenario_distribution=SCENARIO_DISTRIBUTION,
        )
        assets_by_type[dtype] = fleet
        for asset in fleet:
            _write_json(asset_dir / f"{asset.id}.json", asset.to_dict())

    return {"manifests": manifests, "assets_by_type": assets_by_type}


def print_summary(storage_dir: Path, result: dict) -> None:
    manifests = result["manifests"]
    assets_by_type = result["assets_by_type"]

    total_assets = sum(len(v) for v in assets_by_type.values())
    all_assets = [a for fleet in assets_by_type.values() for a in fleet]
    status_counts: Counter = Counter(a.status.value for a in all_assets)

    harvest_count = sum(
        1 for a in all_assets if any(cs.harvest_viable for cs in a.component_states)
    )

    print()
    print("=" * 66)
    print("  OHM Repair Scenario — Seed Complete")
    print("=" * 66)
    print(f"  Storage dir   : {storage_dir}")
    print(f"  Manifests     : {len(manifests)}")
    print(f"  Total assets  : {total_assets}")
    print()
    print("  Asset status breakdown:")
    for status, count in sorted(status_counts.items()):
        print(f"    {status:<20s}  {count:>3d}")
    print()
    print(f"  Assets with harvest-viable components: {harvest_count}")
    print()

    print("  Manifest IDs:")
    for dtype, manifest in manifests.items():
        n = len(assets_by_type.get(dtype, []))
        compat = (
            " [compat↔cpap]"
            if dtype == "ventilator"
            else (" [compat↔ventilator]" if dtype == "cpap" else "")
        )
        print(f"    {dtype:<22s}  {manifest.id}{compat}  ({n} assets)")
    print()

    # Pick one condemned asset per device type for the harvest example
    condemned = [a for a in all_assets if a.status == AssetStatus.CONDEMNED]
    if condemned:
        ex = condemned[0]
        harvestable_names = [
            cs.component_name for cs in ex.component_states if cs.harvest_viable
        ]
        print("  Example: harvest from a condemned asset")
        print(f"    asset_id     : {ex.id}")
        print(f"    manifest_id  : {ex.manifest_id}")
        if harvestable_names:
            print(f"    harvest-viable components: {', '.join(harvestable_names)}")
        print()

    print("  Quick-start commands:")
    print()
    print(f"    # 1. Start OHM with this storage directory:")
    print(
        f"    STORAGE_PROVIDER=local LOCAL_STORAGE_PATH={storage_dir} uvicorn src.core.main:app --port 8001 --reload"
    )
    print()
    print(f"    # 2. Run all integration tests:")
    print(f"    RUN_LIVE_API_TESTS=1 pytest tests/integration/ -v")
    print()
    print(f"    # 3. Run repair-specific integration tests:")
    print(
        f"    RUN_LIVE_API_TESTS=1 pytest tests/integration/test_api_claim_component.py tests/integration/test_api_harvest_enrich.py tests/integration/test_api_compatible_manifests.py -v"
    )
    print()

    if manifests:
        first_manifest_id = next(iter(manifests.values())).id
        print(f"    # 4. Try the harvest-parts CLI (works without a server):")
        print(
            f"    LOCAL_STORAGE_PATH={storage_dir} ohm okh harvest-parts --manifest-id {first_manifest_id} --enrich-fleet"
        )
        print()
        print(f"    # 5. Salvage-match example:")
        print(
            f"    LOCAL_STORAGE_PATH={storage_dir} ohm asset salvage-match --component-name 'Blower Motor' --manifest-id {manifests.get('ventilator', next(iter(manifests.values()))).id}"
        )
        print()

    print("=" * 66)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--storage-dir",
        default=None,
        help="Path to write the seeded data. Defaults to a new temp directory.",
    )
    args = parser.parse_args()

    if args.storage_dir:
        storage_dir = Path(args.storage_dir).expanduser().resolve()
        storage_dir.mkdir(parents=True, exist_ok=True)
    else:
        storage_dir = Path(tempfile.mkdtemp(prefix="ohm-repair-test-"))

    print(f"Seeding repair scenario into: {storage_dir}")
    print()

    result = seed(storage_dir)
    print_summary(storage_dir, result)


if __name__ == "__main__":
    main()
