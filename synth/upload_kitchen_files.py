#!/usr/bin/env python3
"""
Script to upload kitchen files directly to storage.

This script uploads kitchen JSON files to storage so they can be used
for matching with recipes.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.services.storage_service import StorageService
from src.config.storage_config import get_default_storage_config, create_storage_config


async def upload_kitchen_file(file_path: str, storage_service: StorageService) -> str:
    """Upload a kitchen file to storage"""
    # Read the kitchen file
    with open(file_path, 'r') as f:
        kitchen_data = json.load(f)
    
    # Generate a storage key (similar to OKW format)
    kitchen_name = kitchen_data.get("name", "unknown")
    safe_name = "".join(c for c in kitchen_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_name = safe_name.replace(' ', '-').lower()
    
    # Generate a short ID for the kitchen
    kitchen_id = str(uuid4())[:8]
    filename = f"{safe_name}-{kitchen_id}-kitchen.json"
    
    # Convert to JSON
    kitchen_json = json.dumps(kitchen_data, indent=2, ensure_ascii=False, default=str)
    
    # Upload to storage
    metadata = await storage_service.manager.put_object(
        key=filename,
        data=kitchen_json.encode('utf-8'),
        content_type="application/json",
        metadata={
            "domain": "cooking",
            "type": "kitchen",
            "name": kitchen_name
        }
    )
    
    print(f"Uploaded: {filename} (etag: {metadata.etag})")
    return filename


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload kitchen files to storage")
    parser.add_argument("files", nargs="+", help="Kitchen JSON files to upload")
    parser.add_argument("--storage-provider", default="local", help="Storage provider (local, azure_blob, aws_s3)")
    
    args = parser.parse_args()
    
    # Initialize storage service
    if args.storage_provider == "local":
        storage_config = get_default_storage_config()
    else:
        storage_config = create_storage_config(provider=args.storage_provider)
    
    storage_service = StorageService()
    await storage_service.configure(storage_config)
    
    try:
        uploaded_files = []
        for file_path in args.files:
            if not os.path.exists(file_path):
                print(f"Error: File not found: {file_path}")
                continue
            
            try:
                filename = await upload_kitchen_file(file_path, storage_service)
                uploaded_files.append(filename)
            except Exception as e:
                print(f"Error uploading {file_path}: {e}")
        
        print(f"\nUpload complete!")
        print(f"Successfully uploaded: {len(uploaded_files)} files")
        for filename in uploaded_files:
            print(f"  - {filename}")
    
    finally:
        await storage_service.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

