from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncIterator
from datetime import datetime


class StorageConfig:
    """Configuration for storage provider"""

    def __init__(
        self,
        provider: str,
        bucket_name: str,
        region: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None,
        endpoint_url: Optional[str] = None,
        encryption: Optional[Dict[str, str]] = None,
    ):
        self.provider = provider
        self.bucket_name = bucket_name
        self.region = region
        self.credentials = credentials or {}
        self.endpoint_url = endpoint_url
        self.encryption = encryption or {}


class StorageMetadata:
    """Metadata for stored objects"""

    def __init__(
        self,
        content_type: str,
        size: int,
        created_at: datetime,
        modified_at: datetime,
        etag: str,
        version_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ):
        self.content_type = content_type
        self.size = size
        self.created_at = created_at
        self.modified_at = modified_at
        self.etag = etag
        self.version_id = version_id
        self.metadata = metadata or {}


class StorageProvider(ABC):
    """Base class for storage providers"""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the storage provider"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the storage provider"""
        pass

    @abstractmethod
    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> StorageMetadata:
        """Store an object in the storage provider"""
        pass

    @abstractmethod
    async def get_object(self, key: str, version_id: Optional[str] = None) -> bytes:
        """Retrieve an object from the storage provider"""
        pass

    @abstractmethod
    async def delete_object(self, key: str, version_id: Optional[str] = None) -> bool:
        """Delete an object from the storage provider"""
        pass

    @abstractmethod
    async def list_objects(
        self,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        max_keys: Optional[int] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """List objects in the storage provider"""
        pass

    @abstractmethod
    async def get_object_metadata(
        self, key: str, version_id: Optional[str] = None
    ) -> StorageMetadata:
        """Get metadata for an object"""
        pass

    @abstractmethod
    async def copy_object(
        self,
        source_key: str,
        destination_key: str,
        source_version_id: Optional[str] = None,
    ) -> StorageMetadata:
        """Copy an object to a new location"""
        pass

    @abstractmethod
    async def create_bucket(self, bucket_name: str) -> bool:
        """Create a new bucket"""
        pass

    @abstractmethod
    async def delete_bucket(self, bucket_name: str) -> bool:
        """Delete a bucket"""
        pass

    @abstractmethod
    async def list_buckets(self) -> List[str]:
        """List all buckets"""
        pass

    @abstractmethod
    async def get_bucket_metadata(self, bucket_name: str) -> Dict[str, Any]:
        """Get metadata for a bucket"""
        pass

    @abstractmethod
    async def set_bucket_policy(self, bucket_name: str, policy: Dict[str, Any]) -> bool:
        """Set bucket policy"""
        pass

    @abstractmethod
    async def get_bucket_policy(self, bucket_name: str) -> Dict[str, Any]:
        """Get bucket policy"""
        pass
