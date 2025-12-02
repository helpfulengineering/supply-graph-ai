"""
Storage Organization Service

This module provides services for organizing files in storage containers
using a structured directory hierarchy and proper metadata tagging.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID, uuid4

from .manager import StorageManager
from .smart_discovery import SmartFileDiscovery, FileInfo
from ..utils.logging import get_logger

logger = get_logger(__name__)


class StorageOrganizer:
    """Service for organizing storage container structure"""

    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        self.discovery = SmartFileDiscovery(storage_manager)

    async def create_directory_structure(self) -> Dict[str, Any]:
        """Create the organized directory structure in storage"""
        logger.info("Creating organized directory structure")

        # Create placeholder files to establish directory structure
        # Simplified structure: only top-level directories
        directories = {
            "okh/manifests/": ".gitkeep",
            "okw/facilities/": ".gitkeep",
            "supply-trees/": ".gitkeep",
        }

        created_dirs = []

        for directory, placeholder_file in directories.items():
            try:
                # Ensure directory ends with /
                if not directory.endswith("/"):
                    directory = directory + "/"

                # Create a placeholder file to establish the directory
                placeholder_content = {
                    "type": "directory_placeholder",
                    "directory": directory,
                    "created_at": datetime.now().isoformat(),
                    "purpose": "Establishes directory structure in blob storage",
                }

                placeholder_key = f"{directory}{placeholder_file}"
                data = json.dumps(placeholder_content).encode("utf-8")

                await self.storage_manager.put_object(
                    key=placeholder_key,
                    data=data,
                    content_type="application/json",
                    metadata={
                        "file-type": "directory_placeholder",
                        "directory": directory,
                        "created_at": datetime.now().isoformat(),
                    },
                )

                created_dirs.append(directory)
                logger.info(f"Created directory: {directory}")

            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {e}")

        return {
            "created_directories": created_dirs,
            "total_created": len(created_dirs),
            "timestamp": datetime.now().isoformat(),
        }

    async def store_okh_manifest(
        self, manifest_data: Dict[str, Any], manifest_id: Optional[str] = None
    ) -> str:
        """Store an OKH manifest in the organized structure"""
        if not manifest_id:
            manifest_id = manifest_data.get("id", str(uuid4()))

        # Generate organized path (simplified structure: no subdirectories)
        path = f"okh/manifests/{manifest_id}.json"

        # Store with metadata
        data = json.dumps(manifest_data).encode("utf-8")
        metadata = await self.storage_manager.put_object(
            key=path,
            data=data,
            content_type="application/json",
            metadata={
                "file-type": "okh",
                "domain": "okh",
                "id": manifest_id,
                "title": manifest_data.get("title", "Unknown"),
                "version": manifest_data.get("version", "1.0.0"),
                "created_at": datetime.now().isoformat(),
            },
        )

        logger.info(f"Stored OKH manifest at: {path}")
        return path

    async def store_okw_facility(
        self, facility_data: Dict[str, Any], facility_id: Optional[str] = None
    ) -> str:
        """Store an OKW facility in the organized structure"""
        if not facility_id:
            facility_id = facility_data.get("id", str(uuid4()))

        # Generate organized path (simplified structure: no subdirectories)
        path = f"okw/facilities/{facility_id}.json"

        # Store with metadata
        data = json.dumps(facility_data).encode("utf-8")
        metadata = await self.storage_manager.put_object(
            key=path,
            data=data,
            content_type="application/json",
            metadata={
                "file-type": "okw",
                "domain": "okw",
                "id": facility_id,
                "name": facility_data.get("name", "Unknown Facility"),
                "facility_status": facility_data.get("facility_status", "Unknown"),
                "created_at": datetime.now().isoformat(),
            },
        )

        logger.info(f"Stored OKW facility at: {path}")
        return path

    async def store_supply_tree(
        self, tree_data: Dict[str, Any], tree_id: Optional[str] = None
    ) -> str:
        """Store a supply tree in the organized structure"""
        if not tree_id:
            tree_id = tree_data.get("id", str(uuid4()))

        # Generate organized path (simplified structure: no subdirectories)
        path = f"supply-trees/{tree_id}.json"

        # Store with metadata
        data = json.dumps(tree_data).encode("utf-8")
        status = tree_data.get("status", "generated")
        metadata = await self.storage_manager.put_object(
            key=path,
            data=data,
            content_type="application/json",
            metadata={
                "file-type": "supply-tree",
                "domain": "supply-tree",
                "id": tree_id,
                "status": status,
                "created_at": datetime.now().isoformat(),
            },
        )

        logger.info(f"Stored supply tree at: {path}")
        return path

    # Note: Subdirectory helper methods removed - using simplified structure
    # Files are stored directly in okh/manifests/, okw/facilities/, and supply-trees/

    async def get_storage_structure(self) -> Dict[str, Any]:
        """Get the current storage structure"""
        # Simplified structure: no subdirectories
        structure = {
            "okh": {"manifests": []},
            "okw": {"facilities": []},
            "supply-trees": [],
        }

        try:
            # Get all files and organize them by structure
            all_files = await self.discovery.discover_all_files()

            for file_info in all_files:
                path_parts = file_info.key.split("/")

                if len(path_parts) >= 2:
                    domain = path_parts[0]
                    category = path_parts[1]

                    if domain in structure and category in structure[domain]:
                        # Files are stored directly in category directories (no subdirectories)
                        if isinstance(structure[domain][category], list):
                            structure[domain][category].append(
                                {
                                    "key": file_info.key,
                                    "file_type": file_info.file_type,
                                    "size": file_info.size,
                                    "last_modified": file_info.last_modified.isoformat(),
                                }
                            )

        except Exception as e:
            logger.error(f"Failed to get storage structure: {e}")

        return structure
