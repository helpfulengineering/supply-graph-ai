#!/usr/bin/env python3
"""
Auto-fix kitchen/recipe capability files in a remote storage container (e.g. newformats).

Round-trips each cooking-capability file under okw/ through the canonical
KitchenCapability model so the stored JSON gets the canonical format (including
the "domain" field). Uses the same connection pattern as verify_newformats_matching.py.

Usage:
    conda activate supply-graph-ai
    # Dry run: show what would be updated
    python scripts/auto_fix_newformats_kitchens.py --container newformats --dry-run
    # Apply fixes
    python scripts/auto_fix_newformats_kitchens.py --container newformats

Requires: .env with STORAGE_PROVIDER (e.g. azure_blob), and provider-specific
credentials (e.g. AZURE_STORAGE_ACCOUNT, AZURE_STORAGE_KEY for Azure).
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
        description="Auto-fix kitchen capability files in a storage container (canonical format + domain)"
    )
    parser.add_argument(
        "--container",
        default="newformats",
        help="Container/bucket name (default: newformats)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report what would be updated; do not write back",
    )
    args = parser.parse_args()

    import os

    from src.config.storage_config import create_storage_config
    from src.core.domains.cooking.models import KitchenCapability
    from src.core.storage.manager import StorageManager
    from src.core.storage.smart_discovery import SmartFileDiscovery
    from src.core.validation.auto_fix import auto_fix_kitchen_capability

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
    okw_files = await discovery.discover_files("okw")

    # Collect only cooking-capability files (kitchens/recipes under okw)
    to_fix = []
    for fi in okw_files:
        try:
            data = await manager.get_object(fi.key)
            raw = json.loads(data.decode("utf-8"))
            if not KitchenCapability.is_cooking_capability(raw):
                continue
            to_fix.append((fi.key, raw))
        except Exception as e:
            print(f"  Skip {fi.key}: {e}", file=sys.stderr)
            continue

    if not to_fix:
        print(
            f"No kitchen/recipe capability files found under okw/ in '{args.container}'."
        )
        await manager.disconnect()
        return 0

    print(f"Container: {args.container}")
    print(f"Kitchen/recipe capability files under okw/: {len(to_fix)}")
    if args.dry_run:
        print("(Dry run — no writes)")

    updated = 0
    errors = 0
    for key, raw in to_fix:
        try:
            fixed_content, report = auto_fix_kitchen_capability(raw, dry_run=False)
            if report.remaining_errors:
                print(f"  ❌ {key}: fix failed (e.g. parse error)", file=sys.stderr)
                errors += 1
                continue
            # Only write if content changed (e.g. domain added or normalized)
            fixed_bytes = json.dumps(
                fixed_content, indent=2, ensure_ascii=False, default=str
            ).encode("utf-8")
            if not args.dry_run:
                await manager.put_object(
                    key,
                    fixed_bytes,
                    content_type="application/json",
                )
            updated += 1
            if args.dry_run:
                print(f"  Would update: {key} (e.g. add/correct domain)")
            else:
                print(f"  Updated: {key}")
        except Exception as e:
            print(f"  ❌ {key}: {e}", file=sys.stderr)
            errors += 1

    await manager.disconnect()

    if args.dry_run:
        print(f"Would update {updated} file(s).")
    else:
        print(f"Updated {updated} file(s).")
    if errors:
        print(f"Errors: {errors}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
