#!/usr/bin/env python3
"""
Validate all OKW facilities in configured storage (local or remote).

Uses the same validation as the CLI (validate_okw_facility) and reports
per-facility pass/fail plus a summary. Run from project root with the
supply-graph-ai conda environment active.

Usage:
    conda activate supply-graph-ai
    python scripts/validate_okw_in_storage.py [--quality-level professional]
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Project root in path for src imports
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


async def main():
    parser = argparse.ArgumentParser(description="Validate OKW facilities in storage")
    parser.add_argument(
        "--quality-level",
        choices=["hobby", "professional", "medical"],
        default="professional",
        help="Validation quality level (default: professional)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Use strict validation mode",
    )
    args = parser.parse_args()

    from src.config.storage_config import get_default_storage_config
    from src.core.services.okw_service import OKWService
    from src.core.services.storage_service import StorageService
    from src.core.validation.model_validator import validate_okw_facility

    # Configure storage and list OKW
    config = get_default_storage_config()
    storage = await StorageService.get_instance()
    await storage.configure(config)

    okw_service = await OKWService.get_instance()
    facilities, total = await okw_service.list(page=1, page_size=10_000)

    if not facilities:
        print("No OKW facilities found in storage.")
        print(f"Storage provider: {config.provider}, bucket/path: {config.bucket_name}")
        return 0

    print(
        f"Validating {len(facilities)} OKW facilities (quality={args.quality_level}, strict={args.strict})"
    )
    print()

    valid_count = 0
    invalid_count = 0
    errors_summary = []

    for fac in facilities:
        name = getattr(fac, "name", str(fac.id))
        try:
            content = fac.to_dict()
        except Exception as e:
            invalid_count += 1
            errors_summary.append((name, [f"to_dict failed: {e}"]))
            print(f"  ✗ {name}: to_dict failed — {e}")
            continue

        result = validate_okw_facility(
            content,
            quality_level=args.quality_level,
            strict_mode=args.strict,
        )

        if result.valid:
            valid_count += 1
            if result.warnings:
                print(f"  ✓ {name}: valid (warnings: {len(result.warnings)})")
            else:
                print(f"  ✓ {name}: valid")
        else:
            invalid_count += 1
            errors_summary.append((name, result.errors))
            print(f"  ✗ {name}: invalid — {'; '.join(result.errors[:3])}")

    print()
    print(
        f"Summary: {valid_count} valid, {invalid_count} invalid (total {len(facilities)})"
    )
    if errors_summary:
        print("\nErrors by facility:")
        for name, errs in errors_summary:
            for e in errs[:5]:
                print(f"  - {name}: {e}")
    return 0 if invalid_count == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
