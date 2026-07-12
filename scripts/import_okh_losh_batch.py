#!/usr/bin/env python3
"""
Bulk-import OKH-LOSH v2.4 TOML manifests into OHM.

Recursively finds *.okh.toml files under --data-dir, converts each via
OkhLoshConverter, validates + auto-fixes it, and persists it through
OKHService.create() -- the canonical validation-aware pipeline (unlike
`ohm storage populate`, which stores raw dicts with no validation at all).

Default --quality-level is "hobby": community-contributed legacy designs
are not expected to declare OHM-specific fields like manufacturing_processes
(only "recommended", not required, at hobby level). A missing top-level
`version` is not auto-fixable (not an array/object field) and is not
invented -- files missing it are still imported, flagged in the report, and
expected to be finished off by hand via `ohm okh fix`.

Equivalent single-file conversion (no persistence):
    ohm convert from-okh-losh <file> -o <out>.okh.json

Run from project root with the project venv active.
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
        description="Bulk-import OKH-LOSH v2.4 TOML manifests into OHM storage"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Directory to recursively search for *.okh.toml files",
    )
    parser.add_argument(
        "--container",
        default=None,
        help=(
            "Target storage container/bucket name. If omitted, falls back to "
            "whatever STORAGE_CONFIG resolves to from the environment -- pass "
            "this explicitly to avoid landing in the wrong container."
        ),
    )
    parser.add_argument(
        "--quality-level",
        default="hobby",
        choices=["hobby", "professional", "medical"],
        help="Validation quality level (default: hobby)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Convert and validate only; do not persist anything",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional path to write a JSON report of per-file results",
    )
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    if not data_dir.is_dir():
        print(f"Data directory not found: {data_dir}", file=sys.stderr)
        return 1

    files = sorted(data_dir.rglob("*.okh.toml"))
    print(f"Source: {data_dir}")
    print(f"Found {len(files)} OKH-LOSH TOML file(s)")
    if not files:
        return 0

    from src.core.services.okh_losh_converter import (
        OkhLoshConversionError,
        OkhLoshConverter,
    )
    from src.core.validation.auto_fix import auto_fix_okh_manifest
    from src.core.validation.model_validator import validate_okh_manifest

    converter = OkhLoshConverter()

    okh_service = None
    if not args.dry_run:
        import os

        from src.config.storage_config import create_storage_config
        from src.core.services.okh_service import OKHService
        from src.core.services.storage_service import StorageService

        if args.container:
            provider = os.getenv("STORAGE_PROVIDER", "azure_blob")
            config = create_storage_config(provider, bucket_name=args.container)
            storage_service = await StorageService.get_instance()
            await storage_service.configure(config)
            print(f"Target container: {args.container} (provider={provider})")
        else:
            print(
                "Target container: <from environment STORAGE_CONFIG> "
                "(pass --container to be explicit)"
            )

        okh_service = OKHService()
        await okh_service.ensure_initialized()

    results = []
    created = 0
    conversion_errors = 0
    validation_clean = 0
    validation_issues = 0

    for file_path in files:
        rel = str(file_path.relative_to(data_dir))
        entry = {"file": rel}

        try:
            manifest = converter.okh_losh_to_okh(file_path)
        except OkhLoshConversionError as exc:
            conversion_errors += 1
            entry.update(status="conversion_error", error=str(exc))
            results.append(entry)
            print(f"  CONVERT-FAIL  {rel}: {exc}")
            continue

        content = manifest.to_dict()
        validation = validate_okh_manifest(content, quality_level=args.quality_level)

        if not validation.valid:
            content, fix_report = auto_fix_okh_manifest(
                content, validation, quality_level=args.quality_level
            )
            entry["fixes_applied"] = len(fix_report.fixes_applied)
            validation = validate_okh_manifest(
                content, quality_level=args.quality_level
            )

        if validation.valid:
            validation_clean += 1
        else:
            validation_issues += 1

        entry["title"] = manifest.title
        entry["valid"] = validation.valid
        entry["errors"] = validation.errors
        entry["warnings"] = validation.warnings

        if args.dry_run:
            entry["status"] = "dry_run"
        else:
            try:
                created_manifest = await okh_service.create(content)
                created += 1
                entry["status"] = "created"
                entry["id"] = str(created_manifest.id)
            except Exception as exc:
                entry["status"] = "create_error"
                entry["error"] = str(exc)
                print(f"  CREATE-FAIL  {rel}: {exc}")

        results.append(entry)
        marker = "OK" if validation.valid else "ISSUES"
        print(f"  {marker:7s} {rel}  ({manifest.title})")

    print()
    print(f"Converted: {len(files) - conversion_errors}/{len(files)}")
    print(f"Conversion errors: {conversion_errors}")
    print(f"Validation clean: {validation_clean}")
    print(
        f"Validation issues (imported anyway, review with `ohm okh fix`): "
        f"{validation_issues}"
    )
    if not args.dry_run:
        print(f"Created: {created}")

    if args.report:
        args.report.write_text(json.dumps(results, indent=2, default=str))
        print(f"Report written to {args.report}")

    if okh_service is not None:
        await okh_service.shutdown()

    return 1 if conversion_errors else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
