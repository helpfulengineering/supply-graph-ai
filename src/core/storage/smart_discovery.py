"""
Smart File Discovery Service

This module provides a multi-strategy file discovery service that can identify
and locate files of different types (OKH, OKW, Supply Trees) using multiple
fallback strategies for maximum reliability.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils.logging import get_logger
from .manager import StorageManager

logger = get_logger(__name__)


def is_okh_bom_sidecar_storage_key(key: str) -> bool:
    """
    True if this blob key is a BOM sidecar stored next to manifests under okh/.

    Batch upload and golden uploads write manifests as ``*.json`` and companion
    BOMs as ``*-bom.json`` under the same ``okh/`` prefix. Those files are not
    valid OKH manifests but were previously included by prefix-only discovery.
    """
    base = key.rsplit("/", 1)[-1].lower()
    # Standalone BOM exports are often named ``bom.json`` beside a manifest.
    if base == "bom.json":
        return True
    if base.endswith("-bom.json"):
        return True
    # e.g. bom_myproject.json written beside manifests
    return base.startswith("bom_") and base.endswith(".json")


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

            # Align with OKHManifest.validate() so BOM-only / stray JSON is not "okh"
            lic = data.get("licensor")
            if lic is None:
                return False
            if isinstance(lic, str):
                if not lic.strip():
                    return False
            elif isinstance(lic, dict):
                if not lic:
                    return False
            elif isinstance(lic, list):
                if not lic:
                    return False
            else:
                return False

            dl = data.get("documentation_language")
            if dl is None:
                return False
            if isinstance(dl, str):
                if not dl.strip():
                    return False
            elif isinstance(dl, list):
                if not dl or not any(
                    (isinstance(x, str) and x.strip())
                    or (isinstance(x, dict) and bool(x))
                    for x in dl
                ):
                    return False
            else:
                return False

            return True
        except (TypeError, AttributeError):
            return False

    def _validate_okw_content(self, data: dict) -> bool:
        """Validate OKW content structure — accepts both manufacturing and kitchen shapes.

        Two branches are supported:

        **Manufacturing facility** (has ``facility_status``):
        - ``facility_status`` must be a string with a value from the canonical
          ``FacilityStatus`` enum, accepted case-insensitively and with spaces
          normalised to underscores (e.g. ``"Active"`` → ``"active"``,
          ``"Temporary Closure"`` → ``"temporary_closure"``).
        - Backward-compatible with legacy lowercase values (``"active"``,
          ``"planned"``, etc.).
        - At least one optional context field must be present
          (``manufacturing_processes``, ``equipment``, ``location``, ``name``).

        **Kitchen / cooking capability** (no ``facility_status``):
        - Must have at least one cooking-specific field
          (``appliances``, ``tools``, ``ingredients``).
        - Must have a non-empty string ``name`` field.

        Both branches require a non-empty string ``id``.
        """
        try:
            # Both branches require a non-empty string ID.
            if not isinstance(data.get("id"), str) or not data["id"].strip():
                return False

            # ── Manufacturing branch ──────────────────────────────────────
            if "facility_status" in data:
                facility_status = data["facility_status"]
                if not isinstance(facility_status, str):
                    return False

                # Accept both canonical title-case values and legacy lowercase.
                # Normalise: lower + replace spaces with underscores.
                canonical_statuses = {
                    "active",
                    "inactive",
                    "maintenance",
                    "planned",
                    "temporary_closure",
                    "closed",
                }
                normalized = facility_status.lower().replace(" ", "_")
                if normalized not in canonical_statuses:
                    return False

                optional_fields = [
                    "manufacturing_processes",
                    "equipment",
                    "location",
                    "name",
                ]
                return any(f in data for f in optional_fields)

            # ── Kitchen branch ────────────────────────────────────────────
            cooking_fields = {"appliances", "tools", "ingredients"}
            if cooking_fields & data.keys():
                return isinstance(data.get("name"), str) and bool(data["name"])

            return False
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


_DEFAULT_OKH_SHAPE_CHECKER = ContentValidator()


def minimal_okh_manifest_dict(data: dict) -> bool:
    """
    True if ``data`` has the minimum top-level shape of an OKH manifest.

    Used by OKHService.list to skip BOM-only JSON and other stray files under
    ``okh/`` whose names are not caught by :func:`is_okh_bom_sidecar_storage_key`.
    """
    return _DEFAULT_OKH_SHAPE_CHECKER._validate_okh_content(data)


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
        """Discover files using multiple strategies with fallback.

        Strategies are tried in order.  A strategy that **succeeds** (no exception)
        but returns an empty list is treated as authoritative — no further strategies
        run.  The cascade only advances when a strategy raises an exception, which
        signals that the storage mechanism is unavailable or broken (e.g. the prefix
        listing failed), not that zero files exist.

        This prevents the expensive metadata-scan and content-validation strategies
        from running a full-bucket walk just because the primary prefix is empty.
        """
        logger.info(f"Starting discovery for file type: {file_type}")

        for strategy in self.discovery_strategies:
            try:
                files = await strategy(file_type)
                if files:
                    logger.info(
                        "Discovery strategy selected",
                        extra={
                            "strategy": strategy.__name__,
                            "file_type": file_type,
                            "files_found": len(files),
                        },
                    )
                else:
                    logger.debug(
                        f"Strategy {strategy.__name__} returned 0 files for {file_type!r}; "
                        "treating as authoritative (no cascade to more-expensive strategies)"
                    )
                return files
            except Exception as e:
                logger.warning(
                    f"Strategy {strategy.__name__} failed for {file_type!r}: {e}; "
                    "trying next strategy"
                )
                continue

        logger.warning(
            f"No {file_type!r} files found using any of the "
            f"{len(self.discovery_strategies)} discovery strategies"
        )
        return []

    async def discover_all_files(self) -> List[FileInfo]:
        """Discover all files of all types"""
        all_files = []

        for file_type in ["okh", "okw", "supply-tree"]:
            files = await self.discover_files(file_type)
            all_files.extend(files)

        return all_files

    async def _discover_by_directory_structure(self, file_type: str) -> List[FileInfo]:
        """Discover files by directory structure (fastest method)"""
        files = []

        # Top-level domain prefixes — search recursively from here.
        # Users may organise subdirectories however they wish; OHM does not
        # enforce any subdirectory structure beneath these roots.
        directory_prefixes = {
            "okh": "okh/",
            "okw": "okw/",
            "supply-tree": "supply-trees/",
            "asset": "asset/",
        }

        prefix = directory_prefixes.get(file_type)
        if not prefix:
            return files

        try:
            async for obj in self.storage_manager.list_objects(prefix=prefix):
                obj_key = obj["key"]
                if file_type == "okh" and is_okh_bom_sidecar_storage_key(obj_key):
                    logger.debug(
                        "Skipping OKH prefix listing entry (BOM sidecar, not a manifest)",
                        extra={"key": obj_key},
                    )
                    continue
                file_info = FileInfo(
                    key=obj_key,
                    file_type=file_type,
                    size=obj.get("size", 0),
                    last_modified=obj.get("last_modified", datetime.now()),
                    metadata=obj.get("metadata", {}),
                    content_validated=False,
                )
                files.append(file_info)

            if not files:
                logger.warning(
                    f"Directory-structure discovery found 0 files for prefix {prefix!r}. "
                    "Check that the storage provider is reachable and that objects exist "
                    "under this prefix."
                )
        except Exception as e:
            logger.warning(
                f"Directory-structure discovery failed for {file_type!r} "
                f"(prefix={prefix!r}): {e}",
                exc_info=True,
            )
            # Re-raise so discover_files can cascade to the next strategy.
            # An exception here means storage is unavailable/broken — a different
            # condition from "storage worked but found nothing" (empty files list).
            raise

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
                    else:
                        logger.debug(
                            "File skipped by content validator",
                            extra={
                                "key": obj["key"],
                                "detected_type": detected_type,
                                "requested_type": file_type,
                            },
                        )

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
