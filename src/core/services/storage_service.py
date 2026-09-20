import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar
from uuid import UUID, uuid4

from ..models.okh import OKHManifest
from ..models.okw import ManufacturingFacility
from ..matching.match_modes import MATCH_MODE_SINGLE_LEVEL
from ..storage.base import StorageConfig
from ..storage.placeholders import is_scaffold_placeholder
from ..storage.constants import (
    DEFAULT_SOLUTION_TTL_DAYS,
    STORAGE_OBJECT_TYPE_SOLUTION_METADATA,
    build_solution_key,
    build_solution_metadata_key,
)
from ..storage.manager import StorageManager

logger = logging.getLogger(__name__)

T = TypeVar("T")


class StorageRegistry:
    """Maps domain string keys to :class:`DomainStorageHandler` subclasses.

    Populated lazily via :func:`_register_handlers` and explicit ``register_handler`` calls
    so importing this module does not eagerly construct handler instances.
    """

    _handlers: Dict[str, Type["DomainStorageHandler"]] = {}

    @classmethod
    def register_handler(
        cls, domain: str, handler_class: Type["DomainStorageHandler"]
    ) -> None:
        """Associate ``domain`` with a handler class used by :meth:`StorageService.get_domain_handler`.

        Args:
            domain: Short domain id (for example ``okh``, ``okw``).
            handler_class: Concrete handler subclass (not an instance).
        """
        cls._handlers[domain] = handler_class

    @classmethod
    def get_handler(cls, domain: str) -> Type["DomainStorageHandler"]:
        """Look up the handler class for ``domain`` without instantiating it.

        Args:
            domain: Registry key previously passed to :meth:`register_handler`.

        Returns:
            The registered handler type.

        Raises:
            ValueError: If ``domain`` has not been registered.
        """
        if domain not in cls._handlers:
            raise ValueError(f"No storage handler registered for domain: {domain}")
        return cls._handlers[domain]


class StorageService:
    """Facade over ``StorageManager`` for supply trees, solutions, and domain handlers.

    Callers obtain a shared instance via :meth:`get_instance`, then :meth:`configure` with a
    ``StorageConfig`` before persisting objects. Connection failures during configure are logged
    and leave the service in a non-operational state until reconfigured.
    """

    _instance = None

    @classmethod
    async def get_instance(cls) -> "StorageService":
        """Return the process-wide ``StorageService`` singleton (constructs on first call).

        Returns:
            The shared ``StorageService`` instance. Does not open network connections by itself;
            use :meth:`configure` with application settings.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        """Create an unconfigured service; manager and handlers populate after :meth:`configure`."""
        self.manager: Optional[StorageManager] = None
        self._configured = False
        self._domain_handlers: Dict[str, "DomainStorageHandler"] = {}

    async def configure(self, config: StorageConfig) -> None:
        """Connect the underlying ``StorageManager`` from provider configuration.

        Args:
            config: Bucket/provider settings consumed by :class:`~src.core.storage.manager.StorageManager`.

        Note:
            Connection failures are **swallowed** (logged only) so the API process can start
            degraded; ``_configured`` stays false and mutating methods raise ``RuntimeError``
            until a later successful configure.
        """
        try:
            self.manager = StorageManager(config)
            await self.manager.connect()
            self._configured = True
            logger.info(f"Storage service configured with provider: {config.provider}")
        except Exception as e:
            # Log error but don't fail startup - allow app to start with degraded storage
            # Storage operations will check _configured and fail gracefully if needed
            logger.error(
                f"Failed to configure storage service: {e}. "
                f"Application will start but storage operations may fail. "
                f"This may be a temporary network issue."
            )
            # Set manager but mark as not configured
            self._configured = False
            # Don't raise - allow app to start

    async def cleanup(self) -> None:
        """Close the storage manager (if present) and clear the configured flag.

        Raises:
            Exception: Re-raised if the manager's ``cleanup`` fails after logging.
        """
        try:
            if self.manager and hasattr(self.manager, "cleanup"):
                await self.manager.cleanup()
            self._configured = False
            logger.info("Storage Service cleanup completed")
        except Exception as e:
            logger.error(f"Error during Storage Service cleanup: {e}")
            raise

    async def get_domain_handler(self, domain: str) -> "DomainStorageHandler":
        """Return a cached or newly constructed handler for ``domain``.

        Args:
            domain: Registry key (for example ``manufacturing``) with a registered
                :class:`DomainStorageHandler` subclass.

        Returns:
            Handler instance bound to this ``StorageService``.

        Raises:
            ValueError: If no handler class is registered for ``domain``.
        """
        if domain not in self._domain_handlers:
            # Register handlers lazily if not already registered
            _register_handlers()
            handler_class = StorageRegistry.get_handler(domain)
            self._domain_handlers[domain] = handler_class(self)
            logger.info(f"Created storage handler for domain: {domain}")
        return self._domain_handlers[domain]

    async def get_status(self) -> Dict[str, Any]:
        """Lightweight connectivity snapshot for health endpoints.

        Returns:
            Dict with ``configured``, ``connected``, ``provider`` (or ``None`` when down),
            and ``domains`` (registered handler keys from :class:`StorageRegistry`).
        """
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
        """Aggregate object count and byte size across the bucket (full scan).

        Returns:
            Dict with ``total_size``, ``object_count``, ``provider``, ``bucket``, and
            ``domain_stats`` (per-domain size/count from object metadata when present).

        Raises:
            RuntimeError: If storage is not configured.
        """
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

    async def get_config_fingerprint(self) -> Dict[str, Any]:
        """Resolved storage target + per-domain object counts, for drift checks.

        Reports the provider / account / container the running app is *actually*
        connected to, plus counts under ``okh/`` and ``okw/`` (metadata-only
        listing, no downloads — the full-bucket scan of
        :meth:`get_storage_stats` is avoided). Best-effort and never raises: it
        is called from the public ``/health`` endpoint, so storage being down or
        slow must not break liveness. Counts are ``None`` on error.
        """
        fingerprint: Dict[str, Any] = {
            "provider": None,
            "account": None,
            "container": None,
            "okh_count": None,
            "okw_count": None,
        }
        try:
            if not self._configured or not self.manager:
                fingerprint["error"] = "storage not configured"
                return fingerprint
            config = self.manager.config
            fingerprint["provider"] = config.provider
            fingerprint["container"] = config.bucket_name
            fingerprint["account"] = (config.credentials or {}).get("account_name")
            for prefix, field in (("okh/", "okh_count"), ("okw/", "okw_count")):
                count = 0
                async for obj in self.manager.list_objects(prefix=prefix):
                    if not is_scaffold_placeholder(obj.get("key", "")):
                        count += 1
                fingerprint[field] = count
        except Exception as e:  # never propagate to /health
            fingerprint["error"] = str(e)
        return fingerprint

    async def create_backup(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Copy every listed object under ``backups/{name}/`` (full-bucket walk; can be slow).

        Args:
            name: Folder segment under ``backups/``; defaults to a timestamped ``backup-YYYYMMDD-HHMMSS``.

        Returns:
            Summary dict: ``backup_name``, ``object_count``, ``total_size`` (bytes from put metadata),
            ``created_at`` (ISO timestamp).

        Raises:
            RuntimeError: If storage is not configured.
        """
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
        """Return backup folder markers under the ``backups/`` prefix, newest first.

        Returns:
            List of dicts with ``name`` and ``created_at`` (from listing ``last_modified``).

        Raises:
            RuntimeError: If storage is not configured.
        """
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
    """JSON CRUD under ``{domain}/{uuid}.json`` for a single model type ``T``.

    Subclasses implement :meth:`_serialize`, :meth:`_deserialize`, and id helpers.
    The high-level :class:`StorageService` must be configured before any async method runs.
    """

    def __init__(self, storage_service: StorageService) -> None:
        """Bind this handler to ``storage_service`` and derive :attr:`domain` from the class name.

        Args:
            storage_service: Parent service providing ``manager`` and ``_configured``.
        """
        self.storage_service = storage_service
        self.domain = self._get_domain()
        self.model_class: Type[T]

    def _get_domain(self) -> str:
        """Infer registry segment from the class name (strip ``StorageHandler``, lowercase)."""
        return self.__class__.__name__.replace("StorageHandler", "").lower()

    def _get_storage_key(self, obj_id: UUID) -> str:
        """Build the object key ``{domain}/{obj_id}.json``."""
        return f"{self.domain}/{obj_id}.json"

    async def save(self, obj: T) -> str:
        """Serialize ``obj``, write JSON with domain metadata, return the object ETag.

        Args:
            obj: Model instance of type ``T``.

        Returns:
            Etag/version string from ``put_object``.

        Raises:
            RuntimeError: When the parent :class:`StorageService` is not configured.
        """
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
        """Read ``{domain}/{obj_id}.json`` and deserialize via :meth:`_deserialize`.

        Raises:
            RuntimeError: When storage is not configured.
            Exception: Propagates read/JSON errors from the manager.
        """
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
        """Walk ``{domain}/`` and return index rows (id, type, last_modified), not full payloads.

        Args:
            limit: Max rows after ``offset`` (``None`` = unlimited).
            offset: Skip this many keys after prefix filtering.

        Raises:
            RuntimeError: When storage is not configured.
        """
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
        """Delete ``{domain}/{obj_id}.json`` if present.

        Raises:
            RuntimeError: When storage is not configured.
        """
        if not self.storage_service._configured:
            raise RuntimeError("Storage service not configured")

        key = self._get_storage_key(obj_id)
        return await self.storage_service.manager.delete_object(key)

    # --- Add these generic aliases for service compatibility ---
    async def save_object(self, obj_id: UUID, obj_data: Dict[str, Any]) -> str:
        """Deserialize ``obj_data`` to ``T`` then :meth:`save` (``obj_id`` must match embedded id).

        Raises:
            RuntimeError: When storage is not configured.
        """
        # Convert dict to object
        obj = self._deserialize(obj_data)
        return await self.save(obj)

    async def load_object(self, obj_id: UUID) -> Optional[Dict[str, Any]]:
        """Load by id and return :meth:`_serialize` output, or ``None`` on any failure."""
        try:
            obj = await self.load(obj_id)
            return self._serialize(obj)
        except Exception:
            return None

    async def list_objects(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Return the same index rows as :meth:`list` plus a separate total key count under prefix.

        The total is computed with an unconstrained prefix walk and may not match filtered rows.
        """
        objects = await self.list(limit=limit, offset=offset)

        # Get total count by listing all objects without limit/offset
        total_count = 0
        async for obj in self.storage_service.manager.list_objects(
            prefix=f"{self.domain}/"
        ):
            total_count += 1

        return objects, total_count

    async def delete_object(self, obj_id: UUID) -> bool:
        """Alias of :meth:`delete` for callers expecting a generic ``delete_object`` name."""
        return await self.delete(obj_id)

    def _serialize(self, obj: T) -> Dict[str, Any]:
        """Convert ``obj`` to a JSON-serializable dict (subclass contract)."""
        raise NotImplementedError

    def _deserialize(self, data: Dict[str, Any]) -> T:
        """Instantiate ``T`` from stored dict (subclass contract)."""
        raise NotImplementedError

    def _get_object_id(self, obj: T) -> UUID:
        """Stable id used in the storage key (subclass contract)."""
        raise NotImplementedError

    def _get_object_id_from_dict(self, data: Dict[str, Any]) -> UUID:
        """Parse id from a loaded dict when building list index rows (subclass contract)."""
        raise NotImplementedError

    def _get_object_type(self, obj: T) -> str:
        """Short type tag stored in object metadata (subclass contract)."""
        raise NotImplementedError


# Handler classes are now defined lazily in _register_handlers() to avoid import-time object creation


# Register handlers lazily to avoid import-time object creation
def _register_handlers() -> None:
    """Idempotently register built-in ``okh`` and ``okw`` handlers on :class:`StorageRegistry`."""
    if "okh" not in StorageRegistry._handlers:
        # Define OKH handler lazily to avoid object creation on module import
        class OKHStorageHandler(DomainStorageHandler[OKHManifest]):
            """Persist :class:`~src.core.models.okh.OKHManifest` under ``okh/{id}.json``."""

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
            """Persist :class:`~src.core.models.okw.ManufacturingFacility` under ``okw/{id}.json``."""

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
