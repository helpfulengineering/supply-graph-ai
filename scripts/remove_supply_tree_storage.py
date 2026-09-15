#!/usr/bin/env python3
"""Delete the storage left behind by saved supply-tree solutions (#498).

#498 removed saved solutions. This removes what they wrote, under two prefixes:

* ``supply-tree-solutions/`` — the solutions themselves and their metadata
  sidecars. Every web match since the frontend began setting ``save_solution``
  left one: which design was matched, against which facilities, and when.
* ``supply-trees/`` — created on every boot by ``StorageOrganizer`` for a writer
  that had no callers even before #498, so this is usually just a ``.gitkeep``.

**Why delete rather than leave.** Unreferenced-but-present is the worst of the
three options: no reader, no owner, and no access-control story — true right up
until a migration, a backup, or a support export moves it somewhere it is read.
It also cannot be migrated anywhere useful, because there is no longer a concept
for it to be.

Counts are reported rather than assumed, and ``--dry-run`` is the default:
this deletes data users generated, so the operator sees the number before
anything goes.

    python scripts/remove_supply_tree_storage.py            # report only
    python scripts/remove_supply_tree_storage.py --apply    # delete
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.storage_config import get_default_storage_config  # noqa: E402
from src.core.services.storage_service import StorageService  # noqa: E402

# Spelled out here rather than imported: #498 removed the constants along with
# the feature, and a historical location is exactly the kind of thing a cleanup
# script should state rather than reach for.
PREFIXES = ("supply-tree-solutions/", "supply-trees/")


async def _keys_under(service: StorageService, prefix: str) -> list[str]:
    return [obj["key"] async for obj in service.manager.list_objects(prefix=prefix)]


async def main(apply: bool) -> int:
    service = await StorageService.get_instance()
    await service.configure(get_default_storage_config())

    total = 0
    for prefix in PREFIXES:
        try:
            keys = await _keys_under(service, prefix)
        except Exception as exc:  # noqa: BLE001 — report and continue
            print(f"  {prefix:28} could not be listed: {exc}")
            continue

        total += len(keys)
        print(f"  {prefix:28} {len(keys)} object(s)")
        if not apply:
            continue
        for key in keys:
            try:
                await service.manager.delete_object(key)
            except Exception as exc:  # noqa: BLE001
                print(f"    FAILED {key}: {exc}")

    if not total:
        print("\nNothing to remove.")
        return 0
    if apply:
        print(f"\nRemoved {total} object(s).")
    else:
        print(f"\n{total} object(s) would be removed. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete. Without it this only reports what it would remove.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.apply)))
