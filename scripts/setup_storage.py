#!/usr/bin/env python3
"""
Standalone storage setup script for bootstrapping new environments.

This script can be run independently of the main application to set up
storage directory structure. It only requires storage credentials and
does not depend on the full application stack.

Usage:
    python scripts/setup_storage.py --provider gcs --bucket my-bucket --region us-central1
"""

import asyncio
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.storage_config import StorageConfig, create_storage_config
from src.core.storage.manager import StorageManager


async def create_simple_directory_structure(
    storage_manager: StorageManager,
    directories: list[str]
) -> Dict[str, Any]:
    """Create a simple directory structure using placeholder files.
    
    Args:
        storage_manager: Configured storage manager
        directories: List of directory paths to create (e.g., ['okh/manifests/', 'okw/facilities/'])
    
    Returns:
        Dictionary with creation results
    """
    from datetime import datetime
    
    created_dirs = []
    errors = []
    
    for directory in directories:
        try:
            # Ensure directory ends with /
            if not directory.endswith('/'):
                directory = directory + '/'
            
            # Create a placeholder file to establish the directory
            placeholder_file = f"{directory}.gitkeep"
            placeholder_content = {
                "type": "directory_placeholder",
                "directory": directory,
                "created_at": datetime.now().isoformat(),
                "purpose": "Establishes directory structure in blob storage"
            }
            
            data = json.dumps(placeholder_content).encode('utf-8')
            
            await storage_manager.put_object(
                key=placeholder_file,
                data=data,
                content_type="application/json",
                metadata={
                    "file-type": "directory_placeholder",
                    "directory": directory,
                    "created_at": datetime.now().isoformat()
                }
            )
            
            created_dirs.append(directory)
            print(f"✅ Created directory: {directory}")
            
        except Exception as e:
            error_msg = f"Failed to create directory {directory}: {e}"
            errors.append(error_msg)
            print(f"❌ {error_msg}")
    
    return {
        "created_directories": created_dirs,
        "total_created": len(created_dirs),
        "errors": errors
    }


async def main():
    parser = argparse.ArgumentParser(
        description="Setup storage directory structure for Supply Graph AI"
    )
    parser.add_argument(
        "--provider",
        choices=["local", "gcs", "azure_blob", "aws_s3"],
        default="local",
        help="Storage provider to use"
    )
    parser.add_argument(
        "--bucket",
        help="Bucket/container name (required for cloud providers)"
    )
    parser.add_argument(
        "--region",
        help="Region/location for cloud providers"
    )
    parser.add_argument(
        "--credentials-json",
        help="Path to credentials JSON file (for GCP)"
    )
    parser.add_argument(
        "--project-id",
        help="GCP project ID (for GCS)"
    )
    
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
                credentials=credentials
            )
        else:
            storage_config = create_storage_config(args.provider, args.bucket, args.region)
    except Exception as e:
        print(f"❌ Failed to create storage config: {e}")
        sys.exit(1)
    
    # Create storage manager and connect
    try:
        storage_manager = StorageManager(storage_config)
        await storage_manager.connect()
        print(f"✅ Connected to {args.provider} storage: {storage_config.bucket_name}")
    except Exception as e:
        print(f"❌ Failed to connect to storage: {e}")
        sys.exit(1)
    
    # Define simple directory structure
    directories = [
        "okh/manifests/",
        "okw/facilities/",
        "supply-trees/"
    ]
    
    # Create directory structure
    try:
        result = await create_simple_directory_structure(storage_manager, directories)
        
        print("\n" + "=" * 50)
        print("✅ Storage directory structure created successfully!")
        print(f"Provider: {args.provider}")
        print(f"Bucket: {storage_config.bucket_name}")
        print(f"Created {result['total_created']} directories:")
        for directory in result['created_directories']:
            print(f"  - {directory}")
        
        if result['errors']:
            print(f"\n⚠️  {len(result['errors'])} errors occurred:")
            for error in result['errors']:
                print(f"  - {error}")
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Failed to create directory structure: {e}")
        sys.exit(1)
    finally:
        await storage_manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

