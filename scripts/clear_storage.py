#!/usr/bin/env python3
"""
Clear OKH and OKW files from GCS storage

This script deletes all OKH and OKW files from the configured storage,
allowing for a clean slate before generating workflow-specific demo data.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.services.storage_service import StorageService
from src.config.storage_config import create_storage_config
from src.core.utils.logging import get_logger

logger = get_logger(__name__)


async def clear_okh_files(storage_service):
    """Delete all OKH manifest files from storage."""
    logger.info("Clearing OKH files from storage...")
    deleted_count = 0
    
    async for obj in storage_service.manager.list_objects(prefix="okh/manifests/"):
        key = obj.get("key", "")
        if key.endswith(".json"):
            try:
                success = await storage_service.manager.delete_object(key)
                if success:
                    deleted_count += 1
                    logger.info(f"  ✅ Deleted: {key}")
                else:
                    logger.warning(f"  ⚠️  Failed to delete: {key}")
            except Exception as e:
                logger.error(f"  ❌ Error deleting {key}: {e}")
    
    logger.info(f"Deleted {deleted_count} OKH files")
    return deleted_count


async def clear_okw_files(storage_service):
    """Delete all OKW facility files from storage."""
    logger.info("Clearing OKW files from storage...")
    deleted_count = 0
    
    async for obj in storage_service.manager.list_objects(prefix="okw/facilities/"):
        key = obj.get("key", "")
        if key.endswith(".json"):
            try:
                success = await storage_service.manager.delete_object(key)
                if success:
                    deleted_count += 1
                    logger.info(f"  ✅ Deleted: {key}")
                else:
                    logger.warning(f"  ⚠️  Failed to delete: {key}")
            except Exception as e:
                logger.error(f"  ❌ Error deleting {key}: {e}")
    
    logger.info(f"Deleted {deleted_count} OKW files")
    return deleted_count


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clear OKH and OKW files from storage")
    parser.add_argument(
        "--provider",
        type=str,
        default="gcs",
        choices=["local", "gcs", "azure_blob", "aws_s3"],
        help="Storage provider (default: gcs)",
    )
    parser.add_argument(
        "--bucket",
        type=str,
        help="Bucket/container name (required for cloud providers)",
    )
    parser.add_argument(
        "--credentials-json",
        type=str,
        help="Path to credentials JSON file (for GCP)",
    )
    parser.add_argument(
        "--project-id",
        type=str,
        help="GCP project ID (for GCS)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be deleted without actually deleting them",
    )
    
    args = parser.parse_args()
    
    # Build credentials
    credentials = {}
    if args.credentials_json:
        if os.path.exists(args.credentials_json):
            credentials["credentials_path"] = args.credentials_json
        else:
            credentials["credentials_json"] = args.credentials_json
    if args.project_id:
        credentials["project_id"] = args.project_id
    
    # Create storage config
    if credentials:
        storage_config = create_storage_config(
            args.provider,
            args.bucket,
            None,  # region
        )
        storage_config.credentials = credentials
    else:
        storage_config = create_storage_config(args.provider, args.bucket, None)
    
    # Initialize storage service
    storage_service = await StorageService.get_instance()
    await storage_service.configure(storage_config)
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No files will be deleted")
        logger.info("")
        
        # List OKH files
        okh_files = []
        async for obj in storage_service.manager.list_objects(prefix="okh/manifests/"):
            key = obj.get("key", "")
            if key.endswith(".json"):
                okh_files.append(key)
        
        logger.info(f"Found {len(okh_files)} OKH files:")
        for key in okh_files:
            logger.info(f"  - {key}")
        
        # List OKW files
        okw_files = []
        async for obj in storage_service.manager.list_objects(prefix="okw/facilities/"):
            key = obj.get("key", "")
            if key.endswith(".json"):
                okw_files.append(key)
        
        logger.info(f"Found {len(okw_files)} OKW files:")
        for key in okw_files:
            logger.info(f"  - {key}")
        
        logger.info("")
        logger.info(f"Total: {len(okh_files)} OKH + {len(okw_files)} OKW = {len(okh_files) + len(okw_files)} files")
        logger.info("Run without --dry-run to delete these files")
    else:
        # Confirm deletion
        logger.warning("⚠️  This will delete ALL OKH and OKW files from storage!")
        logger.warning("⚠️  This action cannot be undone!")
        response = input("Type 'DELETE' to confirm: ")
        
        if response != "DELETE":
            logger.info("Cancelled.")
            return
        
        # Delete files
        okh_count = await clear_okh_files(storage_service)
        okw_count = await clear_okw_files(storage_service)
        
        logger.info("")
        logger.info(f"✅ Cleanup complete: {okh_count} OKH + {okw_count} OKW = {okh_count + okw_count} files deleted")
    
    # Cleanup
    await storage_service.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
