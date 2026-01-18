"""
Smart File Discovery Service

This module provides a multi-strategy file discovery service that can identify
and locate files of different types (OKH, OKW, Supply Trees) using multiple
fallback strategies for maximum reliability.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from ..utils.logging import get_logger
from .manager import StorageManager

logger = get_logger(__name__)


@dataclass
class FileInfo:
    """Information about a discovered file"""

    key: str
    file_type: str
    size: int
    last_modified: datetime
    metadata: Dict[str, Any]
    content_validated: bool = False


class ContentValidator:
    """Service for validating and identifying file content"""

    def __init__(self):
        self.validators = {
            "okh": self._validate_okh_content,
            "okw": self._validate_okw_content,
            "supply-tree": self._validate_supply_tree_content,
            "rfq": self._validate_rfq_content,
            "quote": self._validate_quote_content,
        }

    def identify_file_type(self, content: bytes) -> Optional[str]:
        """Identify file type by content structure"""
        try:
            data = json.loads(content)

            for file_type, validator in self.validators.items():
                if validator(data):
                    return file_type

        except json.JSONDecodeError:
            logger.debug("Failed to parse JSON content")
        except Exception as e:
            logger.debug(f"Error identifying file type: {e}")

        return None

    def _validate_okh_content(self, data: dict) -> bool:
        """Validate OKH content structure with enhanced validation"""
        # Required fields
        required_fields = ["title", "version", "license", "function"]
        if not all(field in data for field in required_fields):
            return False

        # Enhanced validation rules
        try:
            # Check title is non-empty string
            if not isinstance(data.get("title"), str) or not data["title"].strip():
                return False

            # Check version is non-empty string
            if not isinstance(data.get("version"), str) or not data["version"].strip():
                return False

            # Check license is dict or string
            license_field = data.get("license")
            if not isinstance(license_field, (dict, str)) or not license_field:
                return False

            # Check function is non-empty string
            if (
                not isinstance(data.get("function"), str)
                or not data["function"].strip()
            ):
                return False

            return True
        except (TypeError, AttributeError):
            return False

    def _validate_okw_content(self, data: dict) -> bool:
        """Validate OKW content structure with enhanced validation"""
        # Required fields
        required_fields = ["id", "facility_status"]
        if not all(field in data for field in required_fields):
            return False

        # Enhanced validation rules
        try:
            # Check ID is non-empty string
            if not isinstance(data.get("id"), str) or not data["id"].strip():
                return False

            # Check facility_status is valid
            facility_status = data.get("facility_status")
            valid_statuses = ["active", "inactive", "maintenance", "planned"]
            if facility_status not in valid_statuses:
                return False

            # Check at least one optional field is present
            optional_fields = [
                "manufacturing_processes",
                "equipment",
                "location",
                "name",
            ]
            if not any(field in data for field in optional_fields):
                return False

            return True
        except (TypeError, AttributeError):
            return False

    def _validate_supply_tree_content(self, data: dict) -> bool:
        """Validate Supply Tree content structure with enhanced validation"""
        required_fields = ["workflows", "connections"]
        if not all(field in data for field in required_fields):
            return False

        # Enhanced validation rules
        try:
            # Check workflows is a list
            workflows = data.get("workflows")
            if not isinstance(workflows, list):
                return False

            # Check connections is a list
            connections = data.get("connections")
            if not isinstance(connections, list):
                return False

            return True
        except (TypeError, AttributeError):
            return False

    def _validate_rfq_content(self, data: dict) -> bool:
        """Validate RFQ content structure."""
        required_fields = ["project_name", "status"]
        if not all(field in data for field in required_fields):
            return False
        return True

    def _validate_quote_content(self, data: dict) -> bool:
        """Validate Quote content structure."""
        required_fields = ["rfq_id", "amount", "provider_id"]
        if not all(field in data for field in required_fields):
            return False
        return True


class SmartFileDiscovery:
    """Multi-strategy file discovery service"""

    def __init__(self, storage_manager: StorageManager):
        self.storage_manager = storage_manager
        self.content_validator = ContentValidator()
        self.discovery_strategies = [
            self._discover_by_directory_structure,
            self._discover_by_metadata,
            self._discover_by_content_validation,
            self._discover_by_filename_convention,
        ]

    async def discover_files(self, file_type: str) -> List[FileInfo]:
        """Discover files using multiple strategies with fallback"""
        logger.info(f"Starting discovery for file type: {file_type}")

        for strategy in self.discovery_strategies:
            try:
                files = await strategy(file_type)
                if files:
                    logger.info(
                        f"Found {len(files)} {file_type} files using {strategy.__name__}"
                    )
                    return files
            except Exception as e:
                logger.warning(f"Strategy {strategy.__name__} failed: {e}")
                continue

        logger.info(f"No {file_type} files found using any strategy")
        return []

    async def discover_all_files(self) -> List[FileInfo]:
        """Discover all files of all types"""
        all_files = []

        for file_type in ["okh", "okw", "supply-tree", "rfq", "quote"]:
            files = await self.discover_files(file_type)
            all_files.extend(files)

        return all_files

    async def _discover_by_directory_structure(self, file_type: str) -> List[FileInfo]:
        """Discover files by directory structure (fastest method)"""
        files = []

        # Define directory prefixes for each file type
        directory_prefixes = {
            "okh": "okh/manifests/",
            "okw": "okw/facilities/",
            "supply-tree": "supply-trees/",
            "rfq": "rfq/requests/",
            "quote": "rfq/quotes/",
        }

        prefix = directory_prefixes.get(file_type)
        if not prefix:
            return files

        try:
            async for obj in self.storage_manager.list_objects(prefix=prefix):
                file_info = FileInfo(
                    key=obj["key"],
                    file_type=file_type,
                    size=obj.get("size", 0),
                    last_modified=obj.get("last_modified", datetime.now()),
                    metadata=obj.get("metadata", {}),
                    content_validated=False,
                )
                files.append(file_info)

        except Exception as e:
            logger.debug(f"Directory structure discovery failed for {file_type}: {e}")

        return files

    async def _discover_by_metadata(self, file_type: str) -> List[FileInfo]:
        """Discover files by metadata tags"""
        files = []

        try:
            async for obj in self.storage_manager.list_objects():
                metadata = obj.get("metadata", {})

                # Check for file type in metadata
                if (
                    metadata.get("file-type") == file_type
                    or metadata.get("domain") == file_type
                    or metadata.get("type") == file_type
                ):

                    file_info = FileInfo(
                        key=obj["key"],
                        file_type=file_type,
                        size=obj.get("size", 0),
                        last_modified=obj.get("last_modified", datetime.now()),
                        metadata=metadata,
                        content_validated=False,
                    )
                    files.append(file_info)

        except Exception as e:
            logger.debug(f"Metadata discovery failed for {file_type}: {e}")

        return files

    async def _discover_by_content_validation(self, file_type: str) -> List[FileInfo]:
        """Discover files by content validation (most reliable but slowest)"""
        files = []

        try:
            async for obj in self.storage_manager.list_objects():
                try:
                    data = await self.storage_manager.get_object(obj["key"])
                    detected_type = self.content_validator.identify_file_type(data)

                    if detected_type == file_type:
                        file_info = FileInfo(
                            key=obj["key"],
                            file_type=detected_type,
                            size=obj.get("size", 0),
                            last_modified=obj.get("last_modified", datetime.now()),
                            metadata=obj.get("metadata", {}),
                            content_validated=True,
                        )
                        files.append(file_info)

                except Exception as e:
                    logger.debug(f"Failed to validate content for {obj['key']}: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Content validation discovery failed for {file_type}: {e}")

        return files

    async def _discover_by_filename_convention(self, file_type: str) -> List[FileInfo]:
        """Discover files by filename convention (fallback method)"""
        files = []

        # Define filename patterns for each file type
        filename_patterns = {
            "okh": ["-okh.json", "-okh.yaml", "-okh.yml"],
            "okw": ["-okw.json", "-okw.yaml", "-okw.yml"],
            "supply-tree": ["-supply-tree.json", "-tree.json"],
            "rfq": ["-rfq.json"],
            "quote": ["-quote.json"],
        }

        patterns = filename_patterns.get(file_type, [])
        if not patterns:
            return files

        try:
            async for obj in self.storage_manager.list_objects():
                key = obj["key"]

                # Check if filename matches any pattern
                if any(key.endswith(pattern) for pattern in patterns):
                    file_info = FileInfo(
                        key=key,
                        file_type=file_type,
                        size=obj.get("size", 0),
                        last_modified=obj.get("last_modified", datetime.now()),
                        metadata=obj.get("metadata", {}),
                        content_validated=False,
                    )
                    files.append(file_info)

        except Exception as e:
            logger.debug(f"Filename convention discovery failed for {file_type}: {e}")

        return files

    async def validate_file_content(self, file_info: FileInfo) -> bool:
        """Validate that a file's content matches its declared type"""
        try:
            data = await self.storage_manager.get_object(file_info.key)
            detected_type = self.content_validator.identify_file_type(data)
            return detected_type == file_info.file_type
        except Exception as e:
            logger.debug(f"Failed to validate content for {file_info.key}: {e}")
            return False
