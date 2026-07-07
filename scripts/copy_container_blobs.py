#!/usr/bin/env python3
"""Copy all blobs between Azure containers using OHM's storage provider.

Uses the OHM ``AzureBlobProvider`` with the account key from ``.env`` — shared-key
auth, so it works WITHOUT any ``Storage Blob Data`` RBAC role or `az` CLI access.
Every blob is streamed source → dest with its key path (``okh/…``, ``okw/…``)
preserved, so the two domains merge under one container.

Prerequisites (.env, same as seeding oshwa locally):
    STORAGE_PROVIDER=azure_blob
    AZURE_STORAGE_ACCOUNT=<account>
    AZURE_STORAGE_KEY=<key>

Usage:
    # seed production with BOTH domains (run from project root, venv active)
    python scripts/copy_container_blobs.py --source oshwa --source newformats --dest production
    python scripts/copy_container_blobs.py --source oshwa --dest production --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.config.storage_config import create_storage_config  # noqa: E402
from src.core.storage.providers.azure import AzureBlobProvider  # noqa: E402


def _content_type(key: str) -> str:
    return "application/json" if key.endswith(".json") else "application/octet-stream"


async def _copy_one(
    source_name: str, dest_name: str, prefixes: list[str], dry_run: bool
) -> int:
    # Same credentials (account key), different bucket per provider.
    source = AzureBlobProvider(
        create_storage_config("azure_blob", bucket_name=source_name)
    )
    dest = AzureBlobProvider(create_storage_config("azure_blob", bucket_name=dest_name))
    copied = 0
    try:
        await source.connect()
        if not dry_run:
            await dest.connect()
        for prefix in prefixes:
            async for obj in source.list_objects(prefix=prefix or None):
                key = obj["key"]
                if dry_run:
                    print(f"  would copy: {source_name}/{key}")
                    copied += 1
                    continue
                data = await source.get_object(key)
                await dest.put_object(key, data, content_type=_content_type(key))
                print(f"  ✅ {source_name}/{key} -> {dest_name}/{key}")
                copied += 1
    finally:
        await source.disconnect()
        await dest.disconnect()
    return copied


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        help="Source container (repeatable).",
    )
    parser.add_argument("--dest", required=True, help="Destination container.")
    parser.add_argument(
        "--prefix",
        action="append",
        help="Key prefix to copy (repeatable). Default: okh/ and okw/ — the data "
        "manifests. Pass --all to copy the entire container instead.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Copy every blob (ignores --prefix). Includes runtime outputs like "
        "supply-tree-solutions/ — usually NOT what you want for seeding.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be copied without writing.",
    )
    args = parser.parse_args()

    if args.all:
        prefixes = [""]
    else:
        prefixes = args.prefix or ["okh/", "okw/"]

    total = 0
    for source_name in args.source:
        print(f"== {source_name} -> {args.dest}  (prefixes: {prefixes}) ==")
        total += await _copy_one(source_name, args.dest, prefixes, args.dry_run)

    verb = "Would copy" if args.dry_run else "Copied"
    print(f"\n{verb} {total} blobs into '{args.dest}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
