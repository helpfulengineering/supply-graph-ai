import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from .base import StorageConfig, StorageMetadata, StorageProvider

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages storage provider lifecycle and provides unified interface"""

    def __init__(self, config: StorageConfig):
        self.config = config
        self._provider: Optional[StorageProvider] = None
        self._connected = False

    @property
    def provider(self) -> StorageProvider:
        """Get the current storage provider"""
        if not self._provider:
            self._provider = self._create_provider()
        return self._provider

    def _create_provider(self) -> StorageProvider:
        """Create appropriate storage provider based on config"""
        # Import providers dynamically to avoid dependency issues
        if self.config.provider == "local":
            from .providers.local import LocalStorageProvider

            return LocalStorageProvider(self.config)
        elif self.config.provider == "azure_blob":
            from .providers.azure import AzureBlobProvider

            return AzureBlobProvider(self.config)
        elif self.config.provider == "aws_s3":
            from .providers.aws import AWSS3Provider

            return AWSS3Provider(self.config)
        elif self.config.provider == "gcs":
            from .providers.gcp import GCSProvider

            return GCSProvider(self.config)
        else:
            raise ValueError(f"Unsupported storage provider: {self.config.provider}")

    async def connect(self) -> None:
        """Connect to the storage provider"""
        if not self._connected:
            try:
                await self.provider.connect()
                self._connected = True
                logger.info(f"Connected to storage provider: {self.config.provider}")
            except Exception as e:
                logger.error(f"Failed to connect to storage provider: {e}")
                raise

    async def disconnect(self) -> None:
        """Disconnect from the storage provider"""
        if self._connected and self._provider:
            try:
                await self._provider.disconnect()
                self._connected = False
                logger.info("Disconnected from storage provider")
            except Exception as e:
                logger.error(f"Error disconnecting from storage provider: {e}")
                raise

    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> StorageMetadata:
        """Store an object"""
        await self.ensure_connected()
        return await self.provider.put_object(key, data, content_type, metadata)

    async def get_object(self, key: str, version_id: Optional[str] = None) -> bytes:
        """Retrieve an object"""
        await self.ensure_connected()
        return await self.provider.get_object(key, version_id)

    async def delete_object(self, key: str, version_id: Optional[str] = None) -> bool:
        """Delete an object"""
        await self.ensure_connected()
        return await self.provider.delete_object(key, version_id)

    async def list_objects(
        self,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        max_keys: Optional[int] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """List objects"""
        await self.ensure_connected()
        async for obj in self.provider.list_objects(prefix, delimiter, max_keys):
            yield obj

    async def get_object_metadata(
        self, key: str, version_id: Optional[str] = None
    ) -> StorageMetadata:
        """Get object metadata"""
        await self.ensure_connected()
        return await self.provider.get_object_metadata(key, version_id)

    async def copy_object(
        self,
        source_key: str,
        destination_key: str,
        source_version_id: Optional[str] = None,
    ) -> StorageMetadata:
        """Copy an object"""
        await self.ensure_connected()
        return await self.provider.copy_object(
            source_key, destination_key, source_version_id
        )

    async def create_bucket(self, bucket_name: str) -> bool:
        """Create a bucket"""
        await self.ensure_connected()
        return await self.provider.create_bucket(bucket_name)

    async def delete_bucket(self, bucket_name: str) -> bool:
        """Delete a bucket"""
        await self.ensure_connected()
        return await self.provider.delete_bucket(bucket_name)

    async def list_buckets(self) -> List[str]:
        """List buckets"""
        await self.ensure_connected()
        return await self.provider.list_buckets()

    async def get_bucket_metadata(self, bucket_name: str) -> Dict[str, Any]:
        """Get bucket metadata"""
        await self.ensure_connected()
        return await self.provider.get_bucket_metadata(bucket_name)

    async def set_bucket_policy(self, bucket_name: str, policy: Dict[str, Any]) -> bool:
        """Set bucket policy"""
        await self.ensure_connected()
        return await self.provider.set_bucket_policy(bucket_name, policy)

    async def get_bucket_policy(self, bucket_name: str) -> Dict[str, Any]:
        """Get bucket policy"""
        await self.ensure_connected()
        return await self.provider.get_bucket_policy(bucket_name)

    async def ensure_connected(self) -> None:
        """Ensure connection to storage provider"""
        if not self._connected:
            await self.connect()

    async def cleanup(self) -> None:
        """Clean up resources and close connections"""
        try:
            if self._provider:
                logger.info(f"Cleaning up storage provider: {self.config.provider}")
                # Try cleanup() first, then disconnect() as fallback
                if hasattr(self._provider, "cleanup"):
                    logger.debug("Calling provider.cleanup()")
                    await self._provider.cleanup()
                elif hasattr(self._provider, "disconnect"):
                    logger.debug("Calling provider.disconnect()")
                    await self._provider.disconnect()

                # Give extra time for Azure provider to close aiohttp sessions
                if self.config.provider == "azure_blob":
                    import asyncio

                    logger.debug("Waiting for Azure provider cleanup to complete...")
                    await asyncio.sleep(0.5)  # Extra wait for Azure aiohttp sessions

            self._connected = False
            logger.info("Storage Manager cleanup completed")
        except Exception as e:
            logger.warning(f"Error during Storage Manager cleanup: {e}")
            # Don't raise - continue with cleanup
            self._connected = False
