#!/usr/bin/env python3
"""
Populate the Azure Blob Storage container "ome" with OKH and OKW files from synthetic_data/.

Uses the same storage service and StorageOrganizer as the rest of the app so the layout
matches what the matching service expects (okh/, okw/ at top level, recursive below).

Equivalent CLI command:
    ohm storage populate --provider azure_blob --bucket ome --data-dir synthetic_data

Run from project root with conda env active. Requires .env: STORAGE_PROVIDER=azure_blob,
AZURE_STORAGE_ACCOUNT, AZURE_STORAGE_KEY.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Populate the 'ome' container from synthetic_data/ using the storage service"
    )
    parser.add_argument(
        "--container",
        default="ome",
        help="Target container name (default: ome)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=repo_root / "synthetic_data",
        help="Path to synthetic data directory (default: project synthetic_data/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be uploaded without uploading",
    )
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    if not data_dir.is_dir():
        print(f"❌ Data directory not found: {data_dir}", file=sys.stderr)
        return 1

    okh_files = sorted(data_dir.rglob("*okh*.json"))
    okw_files = sorted(data_dir.rglob("*okw*.json"))

    print(f"Source: {data_dir}")
    print(f"OKH files: {len(okh_files)}")
    print(f"OKW files: {len(okw_files)}")

    if args.dry_run:
        for p in okh_files[:5]:
            print(f"  OKH: {p.relative_to(data_dir)}")
        if len(okh_files) > 5:
            print(f"  ... and {len(okh_files) - 5} more")
        for p in okw_files[:5]:
            print(f"  OKW: {p.relative_to(data_dir)}")
        if len(okw_files) > 5:
            print(f"  ... and {len(okw_files) - 5} more")
        return 0

    from src.config.storage_config import create_storage_config
    from src.core.services.storage_service import StorageService
    from src.core.storage.organizer import StorageOrganizer

    import os

    provider = os.getenv("STORAGE_PROVIDER", "azure_blob")
    config = create_storage_config(provider, bucket_name=args.container)

    storage_service = await StorageService.get_instance()
    await storage_service.configure(config)
    organizer = StorageOrganizer(storage_service.manager)

    stored = []
    errors = []

    for file_path in okh_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            stored_path = await organizer.store_okh_manifest(
                manifest_data, blob_name=file_path.name
            )
            stored.append(("OKH", file_path.name, stored_path))
            print(f"  ✅ OKH: {file_path.name} -> {stored_path}")
        except Exception as e:
            errors.append(f"{file_path.name}: {e}")
            print(f"  ❌ OKH: {file_path.name}: {e}", file=sys.stderr)

    for file_path in okw_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                facility_data = json.load(f)
            stored_path = await organizer.store_okw_facility(
                facility_data, blob_name=file_path.name
            )
            stored.append(("OKW", file_path.name, stored_path))
            print(f"  ✅ OKW: {file_path.name} -> {stored_path}")
        except Exception as e:
            errors.append(f"{file_path.name}: {e}")
            print(f"  ❌ OKW: {file_path.name}: {e}", file=sys.stderr)

    print()
    print(
        f"✅ Uploaded {len(stored)} files to container '{args.container}' ({len([s for s in stored if s[0]=='OKH'])} OKH, {len([s for s in stored if s[0]=='OKW'])} OKW)"
    )
    if errors:
        print(f"⚠️  {len(errors)} errors", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
