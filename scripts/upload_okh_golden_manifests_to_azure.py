#!/usr/bin/env python3
"""
Upload golden OKH manifests (e.g. tmp/oshwa/okh-manifests) to Azure Blob Storage.

Uses StorageService + StorageOrganizer so blobs land under ``okh/<filename>`` like
the rest of OHM (see scripts/populate_ome_from_synthetic_data.py).

Authentication (typical)
------------------------
Repo-root ``.env`` (or exported env) with the same variables as the rest of the app:

  - ``AZURE_STORAGE_ACCOUNT``
  - ``AZURE_STORAGE_KEY``
  - ``AZURE_STORAGE_CONTAINER`` — target container; used as the default for ``--container``

Optional: set ``AZURE_OKH_GOLDEN_CONTAINER`` to override only this script’s default
container (without changing ``AZURE_STORAGE_CONTAINER`` for other tooling).

``STORAGE_PROVIDER`` defaults to ``azure_blob`` here if unset.

Create the container
--------------------
If the container does not exist yet, pass ``--create-container`` (account key must
allow container create). No separate ``az login`` / RBAC step is required when
using account key auth from ``.env``.

Examples
--------
    conda activate supply-graph-ai
    python scripts/upload_okh_golden_manifests_to_azure.py --dry-run
    python scripts/upload_okh_golden_manifests_to_azure.py --create-container
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _collect_files(
    manifests_dir: Path, include_bom: bool
) -> Tuple[List[Path], List[Path]]:
    """Return (main_manifest_paths, bom_paths)."""
    main: List[Path] = []
    bom: List[Path] = []
    for p in sorted(manifests_dir.glob("*.json")):
        if not p.is_file():
            continue
        name = p.name
        if name.endswith("-bom.json"):
            if include_bom:
                bom.append(p)
            continue
        main.append(p)
    return main, bom


async def _run() -> int:
    # Load project .env before os.getenv() / argparse defaults (including --dry-run).
    import src.config.storage_config  # noqa: F401

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifests-dir",
        type=Path,
        default=REPO_ROOT / "tmp/oshwa/okh-manifests",
        help="Directory of *.json manifests (default: tmp/oshwa/okh-manifests)",
    )
    # Prefer dedicated golden override, then standard app container from .env.
    default_container = (
        os.getenv("AZURE_OKH_GOLDEN_CONTAINER")
        or os.getenv("AZURE_STORAGE_CONTAINER")
        or "okh-golden-dataset"
    )
    parser.add_argument(
        "--container",
        default=default_container,
        help=(
            "Blob container name (default: AZURE_OKH_GOLDEN_CONTAINER if set, "
            "else AZURE_STORAGE_CONTAINER, else 'okh-golden-dataset')"
        ),
    )
    parser.add_argument(
        "--create-container",
        action="store_true",
        help="Create the container if missing (idempotent; requires key with create permission)",
    )
    parser.add_argument(
        "--init-structure",
        action="store_true",
        help="Create okh/, okw/, supply-trees/ placeholder roots via StorageOrganizer",
    )
    parser.add_argument(
        "--include-bom",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also upload *-bom.json sidecars (default: true)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be uploaded",
    )
    args = parser.parse_args()

    manifests_dir = args.manifests_dir.expanduser().resolve()
    if not manifests_dir.is_dir():
        print(f"Manifest directory not found: {manifests_dir}", file=sys.stderr)
        return 1

    main_files, bom_files = _collect_files(manifests_dir, args.include_bom)
    print(f"Source: {manifests_dir}")
    print(f"OKH manifests: {len(main_files)}")
    print(f"BOM sidecars: {len(bom_files)}")
    print(f"Container: {args.container}")

    if args.dry_run:
        for p in main_files[:8]:
            print(f"  okh/{p.name}")
        if len(main_files) > 8:
            print(f"  ... and {len(main_files) - 8} more manifests")
        for p in bom_files[:5]:
            print(f"  okh/{p.name} (BOM)")
        if len(bom_files) > 5:
            print(f"  ... and {len(bom_files) - 5} more BOM files")
        return 0

    os.environ.setdefault("STORAGE_PROVIDER", "azure_blob")

    from src.config.storage_config import create_storage_config
    from src.core.services.storage_service import StorageService
    from src.core.storage.organizer import (
        StorageOrganizer,
        _sanitize_blob_name,
        _sanitize_metadata_for_blob,
    )

    config = create_storage_config("azure_blob", bucket_name=args.container)
    storage_service = await StorageService.get_instance()
    await storage_service.configure(config)

    if not storage_service.manager:
        print("Storage manager not available after configure()", file=sys.stderr)
        return 1

    manager = storage_service.manager

    if args.create_container:
        ok = await manager.create_bucket(args.container)
        if not ok:
            print(
                f"Failed to create container {args.container!r}. "
                "Create it in the portal or with `az storage container create` "
                "and retry without --create-container.",
                file=sys.stderr,
            )
            return 1

    organizer = StorageOrganizer(manager)

    if args.init_structure:
        await organizer.create_directory_structure()

    errors: List[str] = []
    uploaded = 0

    for file_path in main_files:
        try:
            with file_path.open(encoding="utf-8") as fh:
                manifest_data = json.load(fh)
            path = await organizer.store_okh_manifest(
                manifest_data, blob_name=file_path.name
            )
            uploaded += 1
            print(f"  okh: {file_path.name} -> {path}")
        except Exception as e:
            msg = f"{file_path.name}: {e}"
            errors.append(msg)
            print(f"  ERROR okh {file_path.name}: {e}", file=sys.stderr)

    for file_path in bom_files:
        try:
            data = file_path.read_bytes()
            segment = _sanitize_blob_name(file_path.name, ".json")
            key = f"okh/{segment}"
            await manager.put_object(
                key=key,
                data=data,
                content_type="application/json",
                metadata=_sanitize_metadata_for_blob(
                    {
                        "file-type": "golden_bom_sidecar",
                        "source_filename": file_path.name,
                    }
                ),
            )
            uploaded += 1
            print(f"  bom: {file_path.name} -> {key}")
        except Exception as e:
            msg = f"{file_path.name}: {e}"
            errors.append(msg)
            print(f"  ERROR bom {file_path.name}: {e}", file=sys.stderr)

    print()
    print(f"Uploaded {uploaded} blob(s) to container {args.container!r}.")
    if errors:
        print(f"{len(errors)} error(s).", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
