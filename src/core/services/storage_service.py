import logging
import json
from typing import Optional, Dict, Any, List, TypeVar, Generic, Type, Tuple
from datetime import datetime
from uuid import UUID

from ..storage.base import StorageConfig
from ..storage.manager import StorageManager
from ..models.okh import OKHManifest
from ..models.okw import ManufacturingFacility

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
