"""
Authentication storage layer.

This module provides storage operations for API keys using the StorageService.
"""

import json
import logging
from typing import List, Optional
from uuid import UUID

from ..models.auth import APIKey
from ..services.storage_service import StorageService
from .constants import (
    AUTH_API_KEY_INDEX_PREFIX,
    AUTH_API_KEYS_PREFIX,
    STORAGE_OBJECT_TYPE_API_KEY,
)

logger = logging.getLogger(__name__)


class AuthStorage:
    """Storage layer for API key persistence."""

    def __init__(self, storage_service: StorageService):
        """
        Initialize AuthStorage.

        Args:
            storage_service: StorageService instance for persistence
        """
        self.storage_service = storage_service
        self._storage_prefix = AUTH_API_KEYS_PREFIX

    async def save_key(self, key: APIKey) -> None:
        """
        Save API key to storage.

        Args:
            key: APIKey instance to save
        """
        # Serialize key to JSON
        key_data = key.model_dump(mode="json")
        # Convert datetime objects to ISO format strings
        if key_data.get("created_at"):
            key_data["created_at"] = key.created_at.isoformat()
        if key_data.get("last_used_at"):
            key_data["last_used_at"] = key.last_used_at.isoformat()
        if key_data.get("expires_at"):
            key_data["expires_at"] = key.expires_at.isoformat()
        # Convert UUID to string
        key_data["key_id"] = str(key.key_id)

        data = json.dumps(key_data).encode("utf-8")

        # Generate storage key
        storage_key = self._get_storage_key(key.key_id)

        # Save with metadata
        await self.storage_service.manager.put_object(
            key=storage_key,
            data=data,
            content_type="application/json",
            metadata={
                "type": STORAGE_OBJECT_TYPE_API_KEY,
                "key_id": str(key.key_id),
                "name": key.name,
            },
        )

        # The digest pointer is what keeps authentication from scanning (#409).
        # Written after the key itself so a crash between the two leaves a key
        # that still authenticates by the legacy path, rather than a pointer to
        # a key that does not exist.
        if key.token_digest:
            await self.storage_service.manager.put_object(
                key=self._get_index_key(key.token_digest),
                data=json.dumps({"key_id": str(key.key_id)}).encode("utf-8"),
                content_type="application/json",
                metadata={
                    "type": STORAGE_OBJECT_TYPE_API_KEY,
                    "key_id": str(key.key_id),
                },
            )

    async def load_key(self, key_id: UUID) -> Optional[APIKey]:
        """
        Load API key from storage.

        Args:
            key_id: UUID of the key to load

        Returns:
            APIKey instance if found, None otherwise
        """
        storage_key = self._get_storage_key(key_id)

        try:
            data = await self.storage_service.manager.get_object(storage_key)
            key_data = json.loads(data.decode("utf-8"))

            # Convert ISO format strings back to datetime objects
            from datetime import datetime

            if key_data.get("created_at"):
                key_data["created_at"] = datetime.fromisoformat(key_data["created_at"])
            if key_data.get("last_used_at"):
                key_data["last_used_at"] = datetime.fromisoformat(
                    key_data["last_used_at"]
                )
            if key_data.get("expires_at"):
                key_data["expires_at"] = datetime.fromisoformat(key_data["expires_at"])

            # Convert string UUID back to UUID object
            key_data["key_id"] = UUID(key_data["key_id"])

            return APIKey(**key_data)
        except Exception as e:
            logger.debug(f"Failed to load API key {key_id}: {e}")
            return None

    async def find_by_digest(self, token_digest: str) -> Optional[APIKey]:
        """Resolve a token digest to its key in constant work, or ``None``.

        Two point reads rather than a listing: the pointer object, then the key
        it names. Returns ``None`` for a digest nothing was issued against,
        which is the common case for a bogus token and costs no bcrypt at all.
        """
        try:
            data = await self.storage_service.manager.get_object(
                self._get_index_key(token_digest)
            )
            key_id = json.loads(data.decode("utf-8"))["key_id"]
        except Exception:
            return None
        return await self.load_key(UUID(key_id))

    async def list_keys(self) -> List[APIKey]:
        """
        List all API keys from storage.

        Returns:
            List of APIKey instances
        """
        keys = []
        prefix = f"{self._storage_prefix}/"

        try:
            async for obj in self.storage_service.manager.list_objects(prefix=prefix):
                if "data" in obj:
                    # If data is already loaded
                    data = obj["data"]
                else:
                    # Load the object data
                    data = await self.storage_service.manager.get_object(obj["key"])

                try:
                    key_data = json.loads(data.decode("utf-8"))

                    # Convert ISO format strings back to datetime objects
                    from datetime import datetime

                    if key_data.get("created_at"):
                        key_data["created_at"] = datetime.fromisoformat(
                            key_data["created_at"]
                        )
                    if key_data.get("last_used_at"):
                        key_data["last_used_at"] = datetime.fromisoformat(
                            key_data["last_used_at"]
                        )
                    if key_data.get("expires_at"):
                        key_data["expires_at"] = datetime.fromisoformat(
                            key_data["expires_at"]
                        )

                    # Convert string UUID back to UUID object
                    key_data["key_id"] = UUID(key_data["key_id"])

                    keys.append(APIKey(**key_data))
                except Exception as e:
                    logger.warning(
                        f"Failed to parse API key from {obj.get('key', 'unknown')}: {e}"
                    )
                    continue
        except Exception as e:
            logger.error(f"Failed to list API keys: {e}")
            raise

        return keys

    async def delete_key(self, key_id: UUID) -> None:
        """
        Delete API key from storage.

        Args:
            key_id: UUID of the key to delete
        """
        storage_key = self._get_storage_key(key_id)
        await self.storage_service.manager.delete_object(storage_key)

    def _get_storage_key(self, key_id: UUID) -> str:
        """
        Get storage path for key.

        Args:
            key_id: UUID of the key

        Returns:
            Storage key path
        """
        return f"{self._storage_prefix}/{key_id}.json"

    @staticmethod
    def _get_index_key(token_digest: str) -> str:
        """Storage key for a digest pointer. The digest is hex, so it is safe
        to interpolate into a path without further escaping."""
        return f"{AUTH_API_KEY_INDEX_PREFIX}/{token_digest}.json"
