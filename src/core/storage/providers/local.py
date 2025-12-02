import asyncio
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

import aiofiles

from ..base import StorageConfig, StorageMetadata, StorageProvider


class LocalStorageProvider(StorageProvider):
    """Local filesystem-based storage provider"""

    def __init__(self, config: StorageConfig):
        self.config = config
        self.base_path = Path(config.bucket_name)
        self._connected = False

    async def connect(self) -> None:
        """Create base directory if it doesn't exist"""
        if not self._connected:
            os.makedirs(self.base_path, exist_ok=True)
            self._connected = True

    async def disconnect(self) -> None:
        """No cleanup needed for local storage"""
        self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure connection to local storage"""
        if not self._connected:
            await self.connect()

    def _get_object_path(self, key: str) -> Path:
        """Get filesystem path for an object"""
        return self.base_path / key

    def _get_metadata_path(self, key: str) -> Path:
        """Get filesystem path for object metadata"""
        return self.base_path / f"{key}.meta"

    async def _save_metadata(self, key: str, metadata: StorageMetadata) -> None:
        """Save object metadata to filesystem"""
        metadata_path = self._get_metadata_path(key)
        metadata_dict = {
            "content_type": metadata.content_type,
            "size": metadata.size,
            "created_at": metadata.created_at.isoformat(),
            "modified_at": metadata.modified_at.isoformat(),
            "etag": metadata.etag,
            "version_id": metadata.version_id,
            "metadata": metadata.metadata,
        }
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(metadata_dict))

    async def _load_metadata(self, key: str) -> Optional[StorageMetadata]:
        """Load object metadata from filesystem"""
        metadata_path = self._get_metadata_path(key)
        if not os.path.exists(metadata_path):
            return None

        async with aiofiles.open(metadata_path, "r") as f:
            metadata_dict = json.loads(await f.read())

        return StorageMetadata(
            content_type=metadata_dict["content_type"],
            size=metadata_dict["size"],
            created_at=datetime.fromisoformat(metadata_dict["created_at"]),
            modified_at=datetime.fromisoformat(metadata_dict["modified_at"]),
            etag=metadata_dict["etag"],
            version_id=metadata_dict.get("version_id"),
            metadata=metadata_dict.get("metadata"),
        )

    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> StorageMetadata:
        """Store an object in the filesystem"""
        await self.ensure_connected()

        # Create directory structure if needed
        object_path = self._get_object_path(key)
        os.makedirs(object_path.parent, exist_ok=True)

        # Write object data
        async with aiofiles.open(object_path, "wb") as f:
            await f.write(data)

        # Generate metadata
        etag = hashlib.md5(data).hexdigest()
        now = datetime.now()
        storage_metadata = StorageMetadata(
            content_type=content_type,
            size=len(data),
            created_at=now,
            modified_at=now,
            etag=etag,
            metadata=metadata,
        )

        # Save metadata
        await self._save_metadata(key, storage_metadata)

        return storage_metadata

    async def get_object(self, key: str, version_id: Optional[str] = None) -> bytes:
        """Retrieve an object from the filesystem"""
        await self.ensure_connected()

        object_path = self._get_object_path(key)
        if not os.path.exists(object_path):
            raise FileNotFoundError(f"Object not found: {key}")

        async with aiofiles.open(object_path, "rb") as f:
            return await f.read()

    async def delete_object(self, key: str, version_id: Optional[str] = None) -> bool:
        """Delete an object from the filesystem"""
        await self.ensure_connected()

        object_path = self._get_object_path(key)
        metadata_path = self._get_metadata_path(key)

        try:
            if os.path.exists(object_path):
                os.remove(object_path)
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            return True
        except Exception as e:
            print(f"Error deleting object {key}: {e}")
            return False

    async def list_objects(
        self,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        max_keys: Optional[int] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """List objects in the filesystem"""
        await self.ensure_connected()

        count = 0
        for root, _, files in os.walk(self.base_path):
            for file in files:
                if file.endswith(".meta"):
                    continue

                rel_path = os.path.relpath(os.path.join(root, file), self.base_path)
                if prefix and not rel_path.startswith(prefix):
                    continue

                metadata = await self._load_metadata(rel_path)
                if metadata:
                    yield {
                        "key": rel_path,
                        "size": metadata.size,
                        "last_modified": metadata.modified_at,
                        "etag": metadata.etag,
                        "metadata": metadata.metadata,
                    }

                count += 1
                if max_keys and count >= max_keys:
                    return

    async def get_object_metadata(
        self, key: str, version_id: Optional[str] = None
    ) -> StorageMetadata:
        """Get metadata for an object"""
        await self.ensure_connected()

        metadata = await self._load_metadata(key)
        if not metadata:
            raise FileNotFoundError(f"Object not found: {key}")

        return metadata

    async def copy_object(
        self,
        source_key: str,
        destination_key: str,
        source_version_id: Optional[str] = None,
    ) -> StorageMetadata:
        """Copy an object to a new location"""
        await self.ensure_connected()

        # Read source object
        data = await self.get_object(source_key, source_version_id)
        metadata = await self.get_object_metadata(source_key, source_version_id)

        # Write to destination
        return await self.put_object(
            destination_key, data, metadata.content_type, metadata.metadata
        )

    async def create_bucket(self, bucket_name: str) -> bool:
        """Create a new bucket (directory)"""
        try:
            os.makedirs(self.base_path / bucket_name, exist_ok=True)
            return True
        except Exception:
            return False

    async def delete_bucket(self, bucket_name: str) -> bool:
        """Delete a bucket (directory)"""
        try:
            os.rmdir(self.base_path / bucket_name)
            return True
        except Exception:
            return False

    async def list_buckets(self) -> List[str]:
        """List all buckets (directories)"""
        await self.ensure_connected()

        buckets = []
        for root, dirs, _ in os.walk(self.base_path):
            for dir_name in dirs:
                rel_path = os.path.relpath(os.path.join(root, dir_name), self.base_path)
                buckets.append(rel_path)
        return buckets

    async def get_bucket_metadata(self, bucket_name: str) -> Dict[str, Any]:
        """Get metadata for a bucket"""
        await self.ensure_connected()

        bucket_path = self.base_path / bucket_name
        if not os.path.exists(bucket_path):
            raise FileNotFoundError(f"Bucket not found: {bucket_name}")

        # Get basic bucket info
        stats = os.stat(bucket_path)
        return {
            "name": bucket_name,
            "created_at": datetime.fromtimestamp(stats.st_ctime),
            "modified_at": datetime.fromtimestamp(stats.st_mtime),
        }

    async def set_bucket_policy(self, bucket_name: str, policy: Dict[str, Any]) -> bool:
        """Set bucket policy (not implemented for local storage)"""
        return True

    async def get_bucket_policy(self, bucket_name: str) -> Dict[str, Any]:
        """Get bucket policy (not implemented for local storage)"""
        return {}
