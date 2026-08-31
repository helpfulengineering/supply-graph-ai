#!/usr/bin/env python3
"""
Standalone storage setup script for bootstrapping new environments.

This script can be run independently of the main application to set up
storage directory structure. It only requires storage credentials and
does not depend on the full application stack.

Usage:
    uv run python scripts/setup_storage.py --provider gcs --bucket my-bucket --region us-central1

The work itself lives in ``src.core.services.storage_setup.setup_storage``,
which the CLI and the app share (#372). This file is argument parsing and
printing, and deliberately has no storage behaviour of its own — the copy it
used to carry had drifted: it created three prefixes rather than four (never
``packages/``), re-stamped placeholders that already existed, and skipped the
metadata sanitisation blob backends need.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.storage_config import StorageConfig, create_storage_config
from src.core.services.storage_setup import StorageSetupError, setup_storage


async def main():
    parser = argparse.ArgumentParser(
        description="Setup storage directory structure for Supply Graph AI"
    )
    parser.add_argument(
        "--provider",
        choices=["local", "gcs", "azure_blob", "aws_s3"],
        default="local",
        help="Storage provider to use",
    )
    parser.add_argument(
        "--bucket", help="Bucket/container name (required for cloud providers)"
    )
    parser.add_argument("--region", help="Region/location for cloud providers")
    parser.add_argument(
        "--credentials-json", help="Path to credentials JSON file (for GCP)"
    )
    parser.add_argument("--project-id", help="GCP project ID (for GCS)")

    args = parser.parse_args()

    # Build credentials dict
    credentials: Dict[str, str] = {}
    if args.provider == "gcs":
        if args.credentials_json:
            if os.path.exists(args.credentials_json):
                credentials["credentials_path"] = args.credentials_json
            else:
                credentials["credentials_json"] = args.credentials_json
        if args.project_id:
            credentials["project_id"] = args.project_id

    # Create storage config
    try:
        if credentials:
            storage_config = StorageConfig(
                provider=args.provider,
                bucket_name=args.bucket or "storage",
                region=args.region,
                credentials=credentials,
            )
        else:
            storage_config = create_storage_config(
                args.provider, args.bucket, args.region
            )
    except Exception as e:
        print(f"❌ Failed to create storage config: {e}")
        sys.exit(1)

    # Connect, prove the connection with a real round trip, then establish the
    # prefixes. This used to report success on a backend it had never reached.
    try:
        result = await setup_storage(storage_config)
    except StorageSetupError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("✅ Storage is ready.")
    print(f"Provider: {result.provider}")
    print(f"Bucket: {result.bucket}")
    if result.provider == "local":
        print(f"Location: {result.location}")

    if result.prefixes_created:
        print(f"Created {len(result.prefixes_created)} prefixes:")
        for prefix in result.prefixes_created:
            print(f"  - {prefix}")
    if result.prefixes_found:
        print(f"Already present ({len(result.prefixes_found)}):")
        for prefix in result.prefixes_found:
            print(f"  - {prefix}")
    if not result.initialized:
        print("Nothing to do — storage was already set up.")


if __name__ == "__main__":
    asyncio.run(main())
