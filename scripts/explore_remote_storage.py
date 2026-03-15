#!/usr/bin/env python3
"""
Explore contents of configured remote (or local) storage using the storage service.

Lists objects under the prefixes OHM expects (okh/, okw/, supply-trees/) and
optionally at container root, so you can verify that storage is populated and
that the layout matches what SmartFileDiscovery expects.

Uses the same config as the rest of the app (e.g. .env: STORAGE_PROVIDER,
AZURE_STORAGE_ACCOUNT, AZURE_STORAGE_CONTAINER). Run from project root with
conda environment active.

Usage:
    conda activate supply-graph-ai
    python scripts/explore_remote_storage.py [--max-per-prefix 50] [--show-root]
"""

import argparse
import asyncio
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


async def main():
    parser = argparse.ArgumentParser(
        description="List contents of configured storage (okh/, okw/, supply-trees/)"
    )
    parser.add_argument(
        "--max-per-prefix",
        type=int,
        default=50,
        help="Max objects to list per prefix (default 50)",
    )
    parser.add_argument(
        "--show-root",
        action="store_true",
        help="Also list blobs at container root (no prefix)",
    )
    args = parser.parse_args()

    from src.config.storage_config import get_default_storage_config
    from src.core.storage.manager import StorageManager

    config = get_default_storage_config()
    print(f"Storage provider: {config.provider}")
    print(f"Container/bucket: {config.bucket_name}")
    print()

    manager = StorageManager(config)
    try:
        await manager.connect()
    except Exception as e:
        print(f"Failed to connect: {e}")
        return 1

    prefixes = [
        ("okh/", "OKH manifests"),
        ("okw/", "OKW facilities"),
        ("supply-trees/", "Supply trees"),
    ]

    for prefix, label in prefixes:
        count = 0
        keys = []
        try:
            async for obj in manager.list_objects(
                prefix=prefix, max_keys=args.max_per_prefix
            ):
                count += 1
                keys.append(obj["key"])
            print(f"{label} (prefix '{prefix}'): {count} object(s)")
            for k in keys[:20]:
                print(f"  - {k}")
            if count > 20:
                print(f"  ... and {count - 20} more")
        except Exception as e:
            print(f"{label} (prefix '{prefix}'): error — {e}")
        print()

    # Total object count (any key) — no prefix
    total = 0
    sample_any = []
    try:
        async for obj in manager.list_objects(max_keys=args.max_per_prefix):
            total += 1
            if len(sample_any) < 15:
                sample_any.append(obj["key"])
        print(f"Total objects in container (first {args.max_per_prefix}): {total}")
        if sample_any:
            print("Sample keys (any prefix):")
            for k in sample_any:
                print(f"  - {k}")
        print()
    except Exception as e:
        print(f"Listing all objects failed: {e}\n")

    if args.show_root:
        count = 0
        keys = []
        try:
            async for obj in manager.list_objects(max_keys=args.max_per_prefix):
                k = obj["key"]
                if not k.startswith(("okh/", "okw/", "supply-trees/")):
                    count += 1
                    keys.append(k)
            print(f"Keys not under okh/|okw/|supply-trees/: {count}")
            for k in keys[:20]:
                print(f"  - {k}")
            if count > 20:
                print(f"  ... and {count - 20} more")
        except Exception as e:
            print(f"Root list error: {e}")

    await manager.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
