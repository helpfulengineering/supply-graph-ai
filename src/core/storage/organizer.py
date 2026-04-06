"""
Storage Organization Service

This module provides services for organizing files in storage containers
using a structured directory hierarchy and proper metadata tagging.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from ..utils.logging import get_logger
from .manager import StorageManager
from .smart_discovery import SmartFileDiscovery

logger = get_logger(__name__)


def _sanitize_metadata_for_blob(
    metadata: Optional[Dict[str, Any]],
) -> Optional[Dict[str, str]]:
    """Sanitize metadata for Azure Blob Storage (and similar) compatibility.

    Azure allows only C# identifier characters in keys (letters, digits, underscore)
    and ASCII-only values. Other providers may accept more; this keeps metadata safe.
    """
    if not metadata:
        return None
    out: Dict[str, str] = {}
    key_pat = re.compile(r"[^a-zA-Z0-9_]")
    for k, v in metadata.items():
        key_safe = re.sub(key_pat, "_", str(k)).strip("_") or "key"
        if key_safe[0].isdigit():
            key_safe = "k_" + key_safe
        val_str = str(v) if v is not None else ""
        val_ascii = val_str.encode("ascii", "replace").decode("ascii")
        out[key_safe] = val_ascii
    return out


def _sanitize_blob_name(name: str, default_suffix: str = ".json") -> str:
    """Sanitize a filename for use as a blob name (path segment).

    Azure allows most characters; we remove control chars and backslash, and avoid
    trailing period or slash. Result is safe for okh/ and okw/ prefixes.
    """
    if not name or not name.strip():
        return f"unnamed{default_suffix}"
    # Strip path components (use basename)
    base = name.replace("\\", "/").split("/")[-1].strip()
    if not base:
        return f"unnamed{default_suffix}"
    # Remove control characters and other problematic code points
    safe = re.sub(r"[\x00-\x1f\x7f\u0081\uE000-\uF8FF]", "", base)
    safe = safe.rstrip("./")
    if not safe:
        return f"unnamed{default_suffix}"
    if not safe.lower().endswith(".json"):
        safe = (
            f"{safe}{default_suffix}"
            if default_suffix.startswith(".")
            else f"{safe}.{default_suffix}"
        )
    return safe


class StorageOrganizer:
    """Service for organizing storage container structure"""

    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        self.discovery = SmartFileDiscovery(storage_manager)

    async def create_directory_structure(self) -> Dict[str, Any]:
        """Create the organized directory structure in storage"""
        logger.info("Creating organized directory structure")

        # Create placeholder files to establish top-level domain directories.
        # No subdirectory structure is enforced; users may organise freely beneath
        # these roots. OHM searches recursively from each top-level prefix.
        directories = {
            "okh/": ".gitkeep",
            "okw/": ".gitkeep",
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
                    metadata=_sanitize_metadata_for_blob(
                        {
                            "file-type": "directory_placeholder",
                            "directory": directory,
                            "created_at": datetime.now().isoformat(),
                        }
                    ),
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
        self,
        manifest_data: Dict[str, Any],
        manifest_id: Optional[str] = None,
        blob_name: Optional[str] = None,
    ) -> str:
        """Store an OKH manifest in the organized structure.

        Args:
            manifest_data: The manifest payload.
            manifest_id: Optional ID (defaults to manifest_data["id"] or new UUID).
            blob_name: Optional human-readable blob name (e.g. original filename).
                When set, the file is stored as okh/<sanitized_blob_name> for easier
                manual use in storage; otherwise okh/<manifest_id>.json is used.
        """
        if not manifest_id:
            manifest_id = manifest_data.get("id", str(uuid4()))
        if isinstance(manifest_id, UUID):
            manifest_id = str(manifest_id)

        # Use human-readable name when provided, else UUID-based key
        if blob_name:
            segment = _sanitize_blob_name(blob_name, ".json")
            path = f"okh/{segment}"
        else:
            path = f"okh/{manifest_id}.json"

        # Store with metadata
        data = json.dumps(manifest_data).encode("utf-8")
        metadata = await self.storage_manager.put_object(
            key=path,
            data=data,
            content_type="application/json",
            metadata=_sanitize_metadata_for_blob(
                {
                    "file-type": "okh",
                    "domain": "okh",
                    "id": manifest_id,
                    "title": manifest_data.get("title", "Unknown"),
                    "version": manifest_data.get("version", "1.0.0"),
                    "created_at": datetime.now().isoformat(),
                }
            ),
        )

        logger.info(f"Stored OKH manifest at: {path}")
        return path

    async def store_okw_facility(
        self,
        facility_data: Dict[str, Any],
        facility_id: Optional[str] = None,
        blob_name: Optional[str] = None,
    ) -> str:
        """Store an OKW facility in the organized structure.

        Args:
            facility_data: The facility payload.
            facility_id: Optional ID (defaults to facility_data["id"] or new UUID).
            blob_name: Optional human-readable blob name (e.g. original filename).
                When set, the file is stored as okw/<sanitized_blob_name> for easier
                manual use in storage; otherwise okw/<facility_id>.json is used.
        """
        if not facility_id:
            facility_id = facility_data.get("id", str(uuid4()))
        if isinstance(facility_id, UUID):
            facility_id = str(facility_id)

        # Use human-readable name when provided, else UUID-based key
        if blob_name:
            segment = _sanitize_blob_name(blob_name, ".json")
            path = f"okw/{segment}"
        else:
            path = f"okw/{facility_id}.json"

        # Store with metadata
        data = json.dumps(facility_data).encode("utf-8")
        metadata = await self.storage_manager.put_object(
            key=path,
            data=data,
            content_type="application/json",
            metadata=_sanitize_metadata_for_blob(
                {
                    "file-type": "okw",
                    "domain": "okw",
                    "id": facility_id,
                    "name": facility_data.get("name", "Unknown Facility"),
                    "facility_status": facility_data.get("facility_status", "Unknown"),
                    "created_at": datetime.now().isoformat(),
                }
            ),
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
            metadata=_sanitize_metadata_for_blob(
                {
                    "file-type": "supply-tree",
                    "domain": "supply-tree",
                    "id": tree_id,
                    "status": status,
                    "created_at": datetime.now().isoformat(),
                }
            ),
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
