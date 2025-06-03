import logging
from typing import Optional, Dict, Any, List, AsyncIterator
from datetime import datetime
import asyncio
from azure.storage.blob.aio import BlobServiceClient, ContainerClient, BlobClient
from azure.core.exceptions import ResourceNotFoundError

from ..base import StorageProvider, StorageConfig, StorageMetadata

logger = logging.getLogger(__name__)

class AzureBlobProvider(StorageProvider):
    """Azure Blob Storage provider implementation"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self._client: Optional[BlobServiceClient] = None
        self._container: Optional[ContainerClient] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Connect to Azure Blob Storage"""
        if not self._connected:
            try:
                # Get credentials from config
                account_name = self.config.credentials.get("account_name")
                account_key = self.config.credentials.get("account_key")
                
                if not account_name or not account_key:
                    raise ValueError("Azure storage account name and key are required")
                
                # Create connection string
                conn_str = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
                
                # Create client
                self._client = BlobServiceClient.from_connection_string(conn_str)
                
                # Get container client
                self._container = self._client.get_container_client(self.config.bucket_name)
                
                # Ensure container exists
                try:
                    await self._container.get_container_properties()
                except ResourceNotFoundError:
                    await self._container.create_container()
                    logger.info(f"Created container: {self.config.bucket_name}")
                
                self._connected = True
                logger.info(f"Connected to Azure Blob Storage: {account_name}")
            except Exception as e:
                logger.error(f"Failed to connect to Azure Blob Storage: {e}")
                raise
    
    async def disconnect(self) -> None:
        """Disconnect from Azure Blob Storage"""
        if self._connected:
            try:
                if self._client:
                    await self._client.close()
                self._connected = False
                logger.info("Disconnected from Azure Blob Storage")
            except Exception as e:
                logger.error(f"Error disconnecting from Azure Blob Storage: {e}")
                raise
    
    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageMetadata:
        """Store an object in Azure Blob Storage"""
        await self.ensure_connected()
        
        try:
            # Get blob client
            blob_client = self._container.get_blob_client(key)
            
            # Upload blob with metadata
            await blob_client.upload_blob(
                data,
                overwrite=True,
                content_type=content_type,
                metadata=metadata
            )
            
            # Get blob properties
            properties = await blob_client.get_blob_properties()
            
            return StorageMetadata(
                content_type=properties.content_settings.content_type,
                size=properties.size,
                created_at=properties.creation_time,
                modified_at=properties.last_modified,
                etag=properties.etag,
                version_id=properties.version_id,
                metadata=properties.metadata
            )
        except Exception as e:
            logger.error(f"Failed to store object {key}: {e}")
            raise
    
    async def get_object(self, key: str, version_id: Optional[str] = None) -> bytes:
        """Retrieve an object from Azure Blob Storage"""
        await self.ensure_connected()
        
        try:
            # Get blob client
            blob_client = self._container.get_blob_client(key)
            
            # Download blob
            download = await blob_client.download_blob()
            return await download.readall()
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Object not found: {key}")
        except Exception as e:
            logger.error(f"Failed to retrieve object {key}: {e}")
            raise
    
    async def delete_object(self, key: str, version_id: Optional[str] = None) -> bool:
        """Delete an object from Azure Blob Storage"""
        await self.ensure_connected()
        
        try:
            # Get blob client
            blob_client = self._container.get_blob_client(key)
            
            # Delete blob
            await blob_client.delete_blob()
            return True
        except ResourceNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Failed to delete object {key}: {e}")
            return False
    
    async def list_objects(
        self,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        max_keys: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """List objects in Azure Blob Storage"""
        await self.ensure_connected()
        
        try:
            # List blobs with prefix
            async for blob in self._container.list_blobs(
                name_starts_with=prefix,
                delimiter=delimiter
            ):
                yield {
                    "key": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified,
                    "etag": blob.etag,
                    "metadata": blob.metadata
                }
                
                if max_keys and max_keys > 0:
                    max_keys -= 1
                    if max_keys == 0:
                        break
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            raise
    
    async def get_object_metadata(
        self,
        key: str,
        version_id: Optional[str] = None
    ) -> StorageMetadata:
        """Get metadata for an object"""
        await self.ensure_connected()
        
        try:
            # Get blob client
            blob_client = self._container.get_blob_client(key)
            
            # Get blob properties
            properties = await blob_client.get_blob_properties()
            
            return StorageMetadata(
                content_type=properties.content_settings.content_type,
                size=properties.size,
                created_at=properties.creation_time,
                modified_at=properties.last_modified,
                etag=properties.etag,
                version_id=properties.version_id,
                metadata=properties.metadata
            )
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Object not found: {key}")
        except Exception as e:
            logger.error(f"Failed to get metadata for object {key}: {e}")
            raise
    
    async def copy_object(
        self,
        source_key: str,
        destination_key: str,
        source_version_id: Optional[str] = None
    ) -> StorageMetadata:
        """Copy an object to a new location"""
        await self.ensure_connected()
        
        try:
            # Get source and destination blob clients
            source_blob = self._container.get_blob_client(source_key)
            dest_blob = self._container.get_blob_client(destination_key)
            
            # Start copy operation
            await dest_blob.start_copy_from_url(source_blob.url)
            
            # Get destination blob properties
            properties = await dest_blob.get_blob_properties()
            
            return StorageMetadata(
                content_type=properties.content_settings.content_type,
                size=properties.size,
                created_at=properties.creation_time,
                modified_at=properties.last_modified,
                etag=properties.etag,
                version_id=properties.version_id,
                metadata=properties.metadata
            )
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Source object not found: {source_key}")
        except Exception as e:
            logger.error(f"Failed to copy object {source_key} to {destination_key}: {e}")
            raise
    
    async def create_bucket(self, bucket_name: str) -> bool:
        """Create a new container"""
        await self.ensure_connected()
        
        try:
            container_client = self._client.get_container_client(bucket_name)
            await container_client.create_container()
            return True
        except Exception as e:
            logger.error(f"Failed to create container {bucket_name}: {e}")
            return False
    
    async def delete_bucket(self, bucket_name: str) -> bool:
        """Delete a container"""
        await self.ensure_connected()
        
        try:
            container_client = self._client.get_container_client(bucket_name)
            await container_client.delete_container()
            return True
        except Exception as e:
            logger.error(f"Failed to delete container {bucket_name}: {e}")
            return False
    
    async def list_buckets(self) -> List[str]:
        """List all containers"""
        await self.ensure_connected()
        
        try:
            containers = []
            async for container in self._client.list_containers():
                containers.append(container.name)
            return containers
        except Exception as e:
            logger.error(f"Failed to list containers: {e}")
            raise
    
    async def get_bucket_metadata(self, bucket_name: str) -> Dict[str, Any]:
        """Get metadata for a container"""
        await self.ensure_connected()
        
        try:
            container_client = self._client.get_container_client(bucket_name)
            properties = await container_client.get_container_properties()
            
            return {
                "name": properties.name,
                "created_at": properties.creation_time,
                "modified_at": properties.last_modified,
                "metadata": properties.metadata
            }
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Container not found: {bucket_name}")
        except Exception as e:
            logger.error(f"Failed to get metadata for container {bucket_name}: {e}")
            raise
    
    async def set_bucket_policy(self, bucket_name: str, policy: Dict[str, Any]) -> bool:
        """Set container policy (not implemented for Azure)"""
        logger.warning("Container policies not implemented for Azure Blob Storage")
        return True
    
    async def get_bucket_policy(self, bucket_name: str) -> Dict[str, Any]:
        """Get container policy (not implemented for Azure)"""
        logger.warning("Container policies not implemented for Azure Blob Storage")
        return {}
