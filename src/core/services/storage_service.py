import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar
from uuid import UUID, uuid4

from ..models.okh import OKHManifest
from ..models.okw import ManufacturingFacility
from ..storage.base import StorageConfig
from ..storage.manager import StorageManager

logger = logging.getLogger(__name__)

T = TypeVar("T")


class StorageRegistry:
    """Registry for domain-specific storage handlers"""

    _handlers: Dict[str, Type["DomainStorageHandler"]] = {}

    @classmethod
    def register_handler(
        cls, domain: str, handler_class: Type["DomainStorageHandler"]
    ) -> None:
        """Register a storage handler for a specific domain"""
        cls._handlers[domain] = handler_class

    @classmethod
    def get_handler(cls, domain: str) -> Type["DomainStorageHandler"]:
        """Get registered handler for domain"""
        if domain not in cls._handlers:
            raise ValueError(f"No storage handler registered for domain: {domain}")
        return cls._handlers[domain]


class StorageService:
    """Service for managing storage operations"""

    _instance = None

    @classmethod
    async def get_instance(cls) -> "StorageService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """Initialize storage service"""
        self.manager: Optional[StorageManager] = None
        self._configured = False
        self._domain_handlers: Dict[str, "DomainStorageHandler"] = {}

    async def configure(self, config: StorageConfig) -> None:
        """Configure storage service with provider settings"""
        try:
            self.manager = StorageManager(config)
            await self.manager.connect()
            self._configured = True
            logger.info(f"Storage service configured with provider: {config.provider}")
        except Exception as e:
            logger.error(f"Failed to configure storage service: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up resources and close connections"""
        try:
            if self.manager and hasattr(self.manager, "cleanup"):
                await self.manager.cleanup()
            self._configured = False
            logger.info("Storage Service cleanup completed")
        except Exception as e:
            logger.error(f"Error during Storage Service cleanup: {e}")
            raise

    async def get_domain_handler(self, domain: str) -> "DomainStorageHandler":
        """Get or create the storage handler for a specific domain"""
        if domain not in self._domain_handlers:
            # Register handlers lazily if not already registered
            _register_handlers()
            handler_class = StorageRegistry.get_handler(domain)
            self._domain_handlers[domain] = handler_class(self)
            logger.info(f"Created storage handler for domain: {domain}")
        return self._domain_handlers[domain]

    async def get_status(self) -> Dict[str, Any]:
        """Get storage service status"""
        if not self._configured or not self.manager:
            return {
                "configured": False,
                "connected": False,
                "provider": None,
                "domains": list(StorageRegistry._handlers.keys()),
            }

        return {
            "configured": True,
            "connected": self.manager._connected,
            "provider": self.manager.config.provider,
            "domains": list(StorageRegistry._handlers.keys()),
        }

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        total_size = 0
        object_count = 0
        domain_stats = {}

        async for obj in self.manager.list_objects():
            total_size += obj.get("size", 0)
            object_count += 1

            # Track domain-specific stats
            domain = obj.get("metadata", {}).get("domain")
            if domain:
                if domain not in domain_stats:
                    domain_stats[domain] = {"size": 0, "count": 0}
                domain_stats[domain]["size"] += obj.get("size", 0)
                domain_stats[domain]["count"] += 1

        return {
            "total_size": total_size,
            "object_count": object_count,
            "provider": self.manager.config.provider,
            "bucket": self.manager.config.bucket_name,
            "domain_stats": domain_stats,
        }

    async def save_supply_tree(self, tree) -> str:
        """Save a supply tree to storage"""
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        # Convert tree to JSON
        tree_data = tree.to_dict()
        data = json.dumps(tree_data).encode("utf-8")

        # Generate storage key
        key = f"supply-trees/{tree.id}.json"

        # Save with metadata
        metadata = await self.manager.put_object(
            key=key,
            data=data,
            content_type="application/json",
            metadata={
                "type": "supply_tree",
                "id": str(tree.id),
                "okh_reference": tree.okh_reference,
            },
        )

        return metadata.etag

    async def load_supply_tree(self, tree_id: UUID):
        """Load a supply tree from storage"""
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        key = f"supply-trees/{tree_id}.json"

        try:
            data = await self.manager.get_object(key)
            from ..models.supply_trees import SupplyTree

            tree_dict = json.loads(data.decode("utf-8"))
            return SupplyTree.from_dict(tree_dict)
        except Exception as e:
            logger.error(f"Failed to load supply tree {tree_id}: {e}")
            raise

    async def list_supply_trees(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List all supply trees"""
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        trees = []
        count = 0

        try:
            async for obj in self.manager.list_objects(prefix="supply-trees/"):
                # Skip .gitkeep and other non-JSON files
                if not obj["key"].endswith(".json"):
                    continue

                if offset and count < offset:
                    count += 1
                    continue

                if limit and len(trees) >= limit:
                    break

                try:
                    data = await self.manager.get_object(obj["key"])
                    tree_dict = json.loads(data.decode("utf-8"))
                    trees.append(
                        {
                            "id": tree_dict["id"],
                            "okh_reference": tree_dict.get("okh_reference"),
                            "last_modified": obj["last_modified"],
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to load supply tree from {obj['key']}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error iterating over supply trees: {e}", exc_info=True)
            raise

        return trees

    async def delete_supply_tree(self, tree_id: UUID) -> bool:
        """Delete a supply tree"""
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        key = f"supply-trees/{tree_id}.json"
        return await self.manager.delete_object(key)

    async def save_supply_tree_solution(
        self,
        solution,
        solution_id: Optional[UUID] = None,
        ttl_days: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> UUID:
        """Save a supply tree solution to storage"""
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        # Generate UUID if not provided
        if solution_id is None:
            solution_id = uuid4()

        # Convert solution to JSON
        solution_data = solution.to_dict()
        data = json.dumps(solution_data).encode("utf-8")

        # Generate storage key
        key = f"supply-tree-solutions/{solution_id}.json"

        # Prepare metadata for object storage
        object_metadata = {
            "type": "supply_tree_solution",
            "id": str(solution_id),
            "matching_mode": solution.metadata.get("matching_mode", "single-level"),
            "tree_count": str(len(solution.all_trees)),
            "component_count": str(
                len(solution.component_mapping) if solution.component_mapping else 0
            ),
        }

        # Save solution data
        await self.manager.put_object(
            key=key,
            data=data,
            content_type="application/json",
            metadata=object_metadata,
        )

        # Create metadata file
        now = datetime.now()
        ttl = ttl_days if ttl_days is not None else 30
        expires_at = now + timedelta(days=ttl)

        metadata = {
            "id": str(solution_id),
            "okh_id": solution.metadata.get("okh_id"),
            "okh_title": solution.metadata.get("okh_title"),
            "matching_mode": solution.metadata.get("matching_mode", "single-level"),
            "tree_count": len(solution.all_trees),
            "component_count": (
                len(solution.component_mapping) if solution.component_mapping else 0
            ),
            "facility_count": len(
                set(tree.facility_name for tree in solution.all_trees)
            ),
            "score": solution.score,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "ttl_days": ttl,
            "tags": tags or [],
        }

        metadata_key = f"supply-tree-solutions/metadata/{solution_id}.json"
        metadata_data = json.dumps(metadata).encode("utf-8")

        await self.manager.put_object(
            key=metadata_key,
            data=metadata_data,
            content_type="application/json",
            metadata={"type": "solution_metadata", "id": str(solution_id)},
        )

        return solution_id

    async def load_supply_tree_solution(self, solution_id: UUID):
        """Load a supply tree solution from storage"""
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        key = f"supply-tree-solutions/{solution_id}.json"

        try:
            data = await self.manager.get_object(key)
            from ..models.supply_trees import SupplyTreeSolution

            solution_dict = json.loads(data.decode("utf-8"))
            return SupplyTreeSolution.from_dict(solution_dict)
        except Exception as e:
            logger.error(f"Failed to load supply tree solution {solution_id}: {e}")
            raise

    async def list_supply_tree_solutions(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        okh_id: Optional[UUID] = None,
        matching_mode: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        min_age_days: Optional[int] = None,
        max_age_days: Optional[int] = None,
        include_stale: bool = True,
        only_stale: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        List supply tree solutions with optional filtering and sorting.

        Args:
            limit: Maximum number of solutions to return
            offset: Number of solutions to skip
            okh_id: Filter by OKH ID
            matching_mode: Filter by matching mode (nested/single-level)
            sort_by: Field to sort by (created_at, updated_at, expires_at, score, age_days)
            sort_order: Sort order (asc, desc)
            min_age_days: Filter by minimum age in days
            max_age_days: Filter by maximum age in days
            include_stale: Include stale solutions (default: True)
            only_stale: Only return stale solutions (default: False)

        Returns:
            List of solution metadata dictionaries
        """
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        solutions = []
        count = 0
        now = datetime.now()

        try:
            async for obj in self.manager.list_objects(
                prefix="supply-tree-solutions/metadata/"
            ):
                # Skip .gitkeep and other non-JSON files
                if not obj["key"].endswith(".json"):
                    continue

                try:
                    data = await self.manager.get_object(obj["key"])
                    metadata_dict = json.loads(data.decode("utf-8"))

                    # Apply basic filters
                    if okh_id and metadata_dict.get("okh_id") != str(okh_id):
                        continue

                    if (
                        matching_mode
                        and metadata_dict.get("matching_mode") != matching_mode
                    ):
                        continue

                    # Calculate age for filtering
                    created_at_str = metadata_dict.get("created_at")
                    if created_at_str:
                        created_at = datetime.fromisoformat(created_at_str)
                        age_days = (now - created_at).days
                    else:
                        age_days = 0

                    # Apply age filters
                    if min_age_days is not None and age_days < min_age_days:
                        continue
                    if max_age_days is not None and age_days > max_age_days:
                        continue

                    # Apply staleness filters
                    if only_stale or not include_stale:
                        solution_id = UUID(metadata_dict.get("id"))
                        is_stale, _ = await self.is_solution_stale(solution_id)

                        if only_stale and not is_stale:
                            continue
                        if not include_stale and is_stale:
                            continue

                    # Return required metadata fields
                    solution_data = {
                        "id": metadata_dict.get("id"),
                        "okh_id": metadata_dict.get("okh_id"),
                        "okh_title": metadata_dict.get("okh_title"),
                        "matching_mode": metadata_dict.get("matching_mode"),
                        "tree_count": metadata_dict.get("tree_count"),
                        "component_count": metadata_dict.get("component_count"),
                        "facility_count": metadata_dict.get("facility_count"),
                        "score": metadata_dict.get("score"),
                        "created_at": metadata_dict.get("created_at"),
                        "updated_at": metadata_dict.get("updated_at"),
                        "expires_at": metadata_dict.get("expires_at"),
                        "ttl_days": metadata_dict.get("ttl_days"),
                        "tags": metadata_dict.get("tags", []),
                        "last_modified": obj.get("last_modified"),
                        "age_days": age_days,
                    }
                    solutions.append(solution_data)

                except Exception as e:
                    logger.error(
                        f"Failed to load solution metadata from {obj['key']}: {e}"
                    )
                    continue

            # Apply sorting
            reverse = sort_order.lower() == "desc"
            if sort_by == "created_at":
                solutions.sort(
                    key=lambda x: (
                        datetime.fromisoformat(x.get("created_at", ""))
                        if x.get("created_at")
                        else datetime.min
                    ),
                    reverse=reverse,
                )
            elif sort_by == "updated_at":
                solutions.sort(
                    key=lambda x: (
                        datetime.fromisoformat(x.get("updated_at", ""))
                        if x.get("updated_at")
                        else datetime.min
                    ),
                    reverse=reverse,
                )
            elif sort_by == "expires_at":
                solutions.sort(
                    key=lambda x: (
                        datetime.fromisoformat(x.get("expires_at", ""))
                        if x.get("expires_at")
                        else datetime.max
                    ),
                    reverse=reverse,
                )
            elif sort_by == "score":
                solutions.sort(key=lambda x: x.get("score", 0.0), reverse=reverse)
            elif sort_by == "age_days":
                solutions.sort(key=lambda x: x.get("age_days", 0), reverse=reverse)

            # Apply pagination after sorting
            if offset:
                solutions = solutions[offset:]
            if limit:
                solutions = solutions[:limit]

        except Exception as e:
            logger.error(
                f"Error iterating over supply tree solutions: {e}", exc_info=True
            )
            raise

        return solutions

    async def delete_supply_tree_solution(self, solution_id: UUID) -> bool:
        """Delete a supply tree solution from storage"""
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        # Delete both solution file and metadata file
        solution_key = f"supply-tree-solutions/{solution_id}.json"
        metadata_key = f"supply-tree-solutions/metadata/{solution_id}.json"

        # Delete both files, return True if at least one was deleted
        solution_deleted = await self.manager.delete_object(solution_key)
        metadata_deleted = await self.manager.delete_object(metadata_key)

        # Return True if either file was deleted (handles partial deletion)
        return solution_deleted or metadata_deleted

    async def is_solution_stale(
        self, solution_id: UUID, max_age_days: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if solution is stale.

        Args:
            solution_id: The solution ID to check
            max_age_days: Optional maximum age in days (overrides default TTL check)

        Returns:
            Tuple of (is_stale: bool, reason: Optional[str])
            Reasons: "expired", "too_old_{age}_days", "exceeded_ttl_{ttl}_days", "check_failed"
        """
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        metadata_key = f"supply-tree-solutions/metadata/{solution_id}.json"

        try:
            data = await self.manager.get_object(metadata_key)
            metadata = json.loads(data.decode("utf-8"))

            now = datetime.now()
            created_at = datetime.fromisoformat(metadata.get("created_at"))
            expires_at_str = metadata.get("expires_at")

            # Check explicit expiration
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if now > expires_at:
                    return (True, "expired")

            # Check age-based staleness
            age_days = (now - created_at).days

            # Check max_age_days if provided
            if max_age_days and age_days > max_age_days:
                return (True, f"too_old_{age_days}_days")

            # Check default TTL
            ttl_days = metadata.get("ttl_days", 30)
            if age_days > ttl_days:
                return (True, f"exceeded_ttl_{ttl_days}_days")

            return (False, None)

        except Exception as e:
            logger.error(f"Failed to check staleness for solution {solution_id}: {e}")
            return (True, "check_failed")

    async def get_solution_age(self, solution_id: UUID) -> timedelta:
        """
        Get age of solution.

        Args:
            solution_id: The solution ID to check

        Returns:
            timedelta representing the age of the solution
        """
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        metadata_key = f"supply-tree-solutions/metadata/{solution_id}.json"

        try:
            data = await self.manager.get_object(metadata_key)
            metadata = json.loads(data.decode("utf-8"))
            created_at = datetime.fromisoformat(metadata.get("created_at"))
            return datetime.now() - created_at
        except Exception as e:
            logger.error(f"Failed to get age for solution {solution_id}: {e}")
            raise

    async def get_stale_solutions(
        self, max_age_days: Optional[int] = None, before_date: Optional[datetime] = None
    ) -> List[UUID]:
        """
        Get list of stale solution IDs.

        Args:
            max_age_days: Optional maximum age in days for staleness check
            before_date: Optional date filter - only return solutions created before this date

        Returns:
            List of UUIDs for stale solutions
        """
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        stale_solutions = []

        try:
            async for obj in self.manager.list_objects(
                prefix="supply-tree-solutions/metadata/"
            ):
                if not obj["key"].endswith(".json"):
                    continue

                try:
                    # Extract solution ID from key
                    key = obj["key"]
                    solution_id_str = key.split("/")[-1].replace(".json", "")
                    solution_id = UUID(solution_id_str)

                    # Check if solution is stale
                    is_stale, _ = await self.is_solution_stale(
                        solution_id, max_age_days
                    )

                    if is_stale:
                        # Check before_date filter if provided
                        if before_date:
                            data = await self.manager.get_object(key)
                            metadata = json.loads(data.decode("utf-8"))
                            created_at = datetime.fromisoformat(
                                metadata.get("created_at")
                            )
                            if created_at >= before_date:
                                continue

                        stale_solutions.append(solution_id)

                except Exception as e:
                    logger.error(f"Failed to check staleness for {obj['key']}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error iterating over solutions: {e}", exc_info=True)
            raise

        return stale_solutions

    async def cleanup_stale_solutions(
        self,
        max_age_days: Optional[int] = None,
        before_date: Optional[datetime] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Remove stale solutions from storage.

        Args:
            max_age_days: Optional maximum age in days for staleness check
            before_date: Optional date filter - only delete solutions created before this date
            dry_run: If True, return preview without deleting (default: True)

        Returns:
            Dict with:
            - deleted_count: Number of solutions deleted (or would be deleted in dry_run)
            - freed_space: Bytes freed (0 in dry_run)
            - deleted_ids: List of solution IDs deleted (or would be deleted)
            - dry_run: Whether this was a dry run
        """
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        stale_ids = await self.get_stale_solutions(max_age_days, before_date)

        deleted_count = 0
        freed_space = 0
        deleted_ids = []

        for solution_id in stale_ids:
            if not dry_run:
                # Get size before deletion
                solution_key = f"supply-tree-solutions/{solution_id}.json"
                try:
                    data = await self.manager.get_object(solution_key)
                    freed_space += len(data)
                except Exception:
                    # If we can't get the size, continue anyway
                    pass

                # Delete solution
                if await self.delete_supply_tree_solution(solution_id):
                    deleted_count += 1
                    deleted_ids.append(str(solution_id))
            else:
                # Dry run - just add to list
                deleted_ids.append(str(solution_id))

        return {
            "deleted_count": deleted_count if not dry_run else len(deleted_ids),
            "freed_space": freed_space,
            "deleted_ids": deleted_ids,
            "dry_run": dry_run,
        }

    async def extend_solution_ttl(
        self, solution_id: UUID, additional_days: int = 30
    ) -> bool:
        """
        Extend solution expiration time.

        Args:
            solution_id: The solution ID to extend
            additional_days: Number of days to add to expiration (default: 30)

        Returns:
            True if successful, False otherwise
        """
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        metadata_key = f"supply-tree-solutions/metadata/{solution_id}.json"

        try:
            data = await self.manager.get_object(metadata_key)
            metadata = json.loads(data.decode("utf-8"))

            # Update expiration
            expires_at_str = metadata.get("expires_at")
            if expires_at_str:
                current_expires = datetime.fromisoformat(expires_at_str)
                new_expires = current_expires + timedelta(days=additional_days)
            else:
                # Calculate from created_at if expires_at is missing
                created_at = datetime.fromisoformat(metadata.get("created_at"))
                current_ttl = metadata.get("ttl_days", 30)
                new_expires = created_at + timedelta(days=current_ttl + additional_days)

            metadata["expires_at"] = new_expires.isoformat()
            metadata["updated_at"] = datetime.now().isoformat()
            metadata["ttl_days"] = metadata.get("ttl_days", 30) + additional_days

            # Save updated metadata
            await self.manager.put_object(
                key=metadata_key,
                data=json.dumps(metadata).encode("utf-8"),
                content_type="application/json",
            )

            return True

        except Exception as e:
            logger.error(f"Failed to extend TTL for solution {solution_id}: {e}")
            return False

    async def archive_stale_solutions(
        self, max_age_days: Optional[int] = None, archive_prefix: str = "archived/"
    ) -> Dict[str, Any]:
        """
        Move stale solutions to archive instead of deleting.

        Args:
            max_age_days: Optional maximum age in days for staleness check
            archive_prefix: Prefix for archived solutions (default: "archived/")

        Returns:
            Dict with:
            - archived_count: Number of solutions archived
            - archived_ids: List of solution IDs archived
        """
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        stale_ids = await self.get_stale_solutions(max_age_days)

        archived_count = 0
        archived_ids = []

        for solution_id in stale_ids:
            try:
                solution_key = f"supply-tree-solutions/{solution_id}.json"
                metadata_key = f"supply-tree-solutions/metadata/{solution_id}.json"

                # Archive solution file
                archived_solution_key = (
                    f"{archive_prefix}supply-tree-solutions/{solution_id}.json"
                )
                await self.manager.copy_object(solution_key, archived_solution_key)

                # Archive metadata file
                archived_metadata_key = (
                    f"{archive_prefix}supply-tree-solutions/metadata/{solution_id}.json"
                )
                await self.manager.copy_object(metadata_key, archived_metadata_key)

                # Delete original files
                await self.manager.delete_object(solution_key)
                await self.manager.delete_object(metadata_key)

                archived_count += 1
                archived_ids.append(str(solution_id))

            except Exception as e:
                logger.error(f"Failed to archive solution {solution_id}: {e}")
                continue

        return {"archived_count": archived_count, "archived_ids": archived_ids}

    async def load_supply_tree_solution_with_metadata(
        self,
        solution_id: UUID,
        validate_freshness: bool = True,
        auto_refresh: bool = False,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Load solution with optional freshness validation.

        Args:
            solution_id: The solution ID to load
            validate_freshness: If True, check staleness and include metadata (default: True)
            auto_refresh: If True, automatically extend TTL if stale (default: False)

        Returns:
            Tuple of (solution: SupplyTreeSolution, metadata: Dict[str, Any])
            Metadata includes: is_stale, staleness_reason, age_days, expires_at, refresh_recommended
        """
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        # Load the solution
        solution = await self.load_supply_tree_solution(solution_id)

        metadata = {}

        if validate_freshness:
            try:
                is_stale, reason = await self.is_solution_stale(solution_id)
                age = await self.get_solution_age(solution_id)

                # Load metadata for expiration info
                metadata_key = f"supply-tree-solutions/metadata/{solution_id}.json"
                try:
                    data = await self.manager.get_object(metadata_key)
                    meta = json.loads(data.decode("utf-8"))

                    metadata = {
                        "is_stale": is_stale,
                        "staleness_reason": reason,
                        "age_days": age.days,
                        "expires_at": meta.get("expires_at"),
                        "refresh_recommended": is_stale,
                    }

                    # Auto-refresh if requested and stale
                    if auto_refresh and is_stale:
                        await self.extend_solution_ttl(solution_id)
                        metadata["auto_refreshed"] = True
                        metadata["is_stale"] = False
                        metadata["refresh_recommended"] = False

                except Exception as e:
                    logger.warning(f"Failed to load metadata for staleness check: {e}")
                    metadata = {
                        "is_stale": is_stale,
                        "staleness_reason": reason,
                        "age_days": age.days,
                        "refresh_recommended": is_stale,
                    }

            except Exception as e:
                logger.warning(
                    f"Failed to validate freshness for solution {solution_id}: {e}"
                )
                # Return solution anyway, with empty metadata

        return (solution, metadata)

    async def create_backup(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a backup of all data"""
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        backup_name = name or f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        backup_prefix = f"backups/{backup_name}/"

        # Copy all objects to backup location
        object_count = 0
        total_size = 0

        async for obj in self.manager.list_objects():
            try:
                data = await self.manager.get_object(obj["key"])
                backup_key = f"{backup_prefix}{obj['key']}"

                metadata = await self.manager.put_object(
                    key=backup_key,
                    data=data,
                    content_type=obj.get("content_type", "application/octet-stream"),
                    metadata=obj.get("metadata"),
                )

                object_count += 1
                total_size += metadata.size
            except Exception as e:
                logger.error(f"Failed to backup object {obj['key']}: {e}")
                continue

        return {
            "backup_name": backup_name,
            "object_count": object_count,
            "total_size": total_size,
            "created_at": datetime.now().isoformat(),
        }

    async def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups"""
        if not self._configured or not self.manager:
            raise RuntimeError("Storage service not configured")

        backups = []
        async for obj in self.manager.list_objects(prefix="backups/"):
            if obj["key"].endswith("/"):
                backup_name = obj["key"].split("/")[1]
                backups.append(
                    {
                        "name": backup_name,
                        "created_at": obj["last_modified"].isoformat(),
                    }
                )

        return sorted(backups, key=lambda x: x["created_at"], reverse=True)


class DomainStorageHandler(Generic[T]):
    """Base class for domain-specific storage handlers"""

    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self.domain = self._get_domain()
        self.model_class: Type[T]

    def _get_domain(self) -> str:
        """Get domain name from handler class"""
        return self.__class__.__name__.replace("StorageHandler", "").lower()

    def _get_storage_key(self, obj_id: UUID) -> str:
        """Get storage key for an object"""
        return f"{self.domain}/{obj_id}.json"

    async def save(self, obj: T) -> str:
        """Save a domain object to storage"""
        if not self.storage_service._configured:
            raise RuntimeError("Storage service not configured")

        # Convert object to JSON
        obj_data = self._serialize(obj)
        data = json.dumps(obj_data).encode("utf-8")

        # Generate storage key
        key = self._get_storage_key(self._get_object_id(obj))

        # Save with metadata
        metadata = await self.storage_service.manager.put_object(
            key=key,
            data=data,
            content_type="application/json",
            metadata={
                "domain": self.domain,
                "type": self._get_object_type(obj),
                "id": str(self._get_object_id(obj)),
            },
        )

        return metadata.etag

    async def load(self, obj_id: UUID) -> T:
        """Load a domain object from storage"""
        if not self.storage_service._configured:
            raise RuntimeError("Storage service not configured")

        key = self._get_storage_key(obj_id)

        try:
            data = await self.storage_service.manager.get_object(key)
            obj_dict = json.loads(data.decode("utf-8"))
            return self._deserialize(obj_dict)
        except Exception as e:
            logger.error(f"Failed to load {self.domain} object {obj_id}: {e}")
            raise

    async def list(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """List all domain objects"""
        if not self.storage_service._configured:
            raise RuntimeError("Storage service not configured")

        objects = []
        count = 0

        async for obj in self.storage_service.manager.list_objects(
            prefix=f"{self.domain}/"
        ):
            if offset and count < offset:
                count += 1
                continue

            if limit and len(objects) >= limit:
                break

            try:
                data = await self.storage_service.manager.get_object(obj["key"])
                obj_dict = json.loads(data.decode("utf-8"))
                objects.append(
                    {
                        "id": self._get_object_id_from_dict(obj_dict),
                        "type": obj_dict.get("type"),
                        "last_modified": obj["last_modified"],
                    }
                )
            except Exception as e:
                logger.error(
                    f"Failed to load {self.domain} object from {obj['key']}: {e}"
                )
                continue

        return objects

    async def delete(self, obj_id: UUID) -> bool:
        """Delete a domain object"""
        if not self.storage_service._configured:
            raise RuntimeError("Storage service not configured")

        key = self._get_storage_key(obj_id)
        return await self.storage_service.manager.delete_object(key)

    # --- Add these generic aliases for service compatibility ---
    async def save_object(self, obj_id: UUID, obj_data: dict) -> str:
        """Save a domain object by ID and dict (for service compatibility)"""
        # Convert dict to object
        obj = self._deserialize(obj_data)
        return await self.save(obj)

    async def load_object(self, obj_id: UUID) -> Optional[dict]:
        """Load a domain object by ID and return as dict (for service compatibility)"""
        try:
            obj = await self.load(obj_id)
            return self._serialize(obj)
        except Exception:
            return None

    async def list_objects(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> Tuple[List[dict], int]:
        """List all domain objects as dicts (for service compatibility)"""
        objects = await self.list(limit=limit, offset=offset)

        # Get total count by listing all objects without limit/offset
        total_count = 0
        async for obj in self.storage_service.manager.list_objects(
            prefix=f"{self.domain}/"
        ):
            total_count += 1

        return objects, total_count

    async def delete_object(self, obj_id: UUID) -> bool:
        """Delete a domain object by ID (for service compatibility)"""
        return await self.delete(obj_id)

    def _serialize(self, obj: T) -> Dict[str, Any]:
        """Serialize object to dictionary"""
        raise NotImplementedError

    def _deserialize(self, data: Dict[str, Any]) -> T:
        """Deserialize dictionary to object"""
        raise NotImplementedError

    def _get_object_id(self, obj: T) -> UUID:
        """Get object ID"""
        raise NotImplementedError

    def _get_object_id_from_dict(self, data: Dict[str, Any]) -> UUID:
        """Get object ID from dictionary"""
        raise NotImplementedError

    def _get_object_type(self, obj: T) -> str:
        """Get object type"""
        raise NotImplementedError


# Handler classes are now defined lazily in _register_handlers() to avoid import-time object creation


# Register handlers lazily to avoid import-time object creation
def _register_handlers():
    """Register handlers lazily to avoid import-time object creation"""
    if "okh" not in StorageRegistry._handlers:
        # Define OKH handler lazily to avoid object creation on module import
        class OKHStorageHandler(DomainStorageHandler[OKHManifest]):
            def _serialize(self, obj: OKHManifest) -> dict:
                return obj.to_dict()

            def _deserialize(self, data: dict) -> OKHManifest:
                return OKHManifest.from_dict(data)

            def _get_object_id(self, obj: OKHManifest) -> UUID:
                return obj.id

            def _get_object_id_from_dict(self, data: dict) -> UUID:
                return UUID(data["id"])

            def _get_object_type(self, obj: OKHManifest) -> str:
                return "okh_manifest"

        StorageRegistry.register_handler("okh", OKHStorageHandler)

    if "okw" not in StorageRegistry._handlers:
        # Define OKW handler lazily to avoid object creation on module import
        class OKWStorageHandler(DomainStorageHandler[ManufacturingFacility]):
            def _serialize(self, obj: ManufacturingFacility) -> dict:
                return obj.to_dict()

            def _deserialize(self, data: dict) -> ManufacturingFacility:
                return ManufacturingFacility.from_dict(data)

            def _get_object_id(self, obj: ManufacturingFacility) -> UUID:
                return obj.id

            def _get_object_id_from_dict(self, data: dict) -> UUID:
                return UUID(data["id"])

            def _get_object_type(self, obj: ManufacturingFacility) -> str:
                return "okw_facility"

        StorageRegistry.register_handler("okw", OKWStorageHandler)


# Register handlers when first needed - done lazily in get_domain_handler method
