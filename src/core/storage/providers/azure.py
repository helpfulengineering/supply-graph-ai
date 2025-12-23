import logging
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, List, Optional

from ..base import StorageConfig, StorageMetadata, StorageProvider

# Import Azure exceptions at module level
try:
    from azure.core.exceptions import ResourceNotFoundError
except ImportError:
    # Fallback for when Azure SDK is not available
    ResourceNotFoundError = Exception

# Type hints for Azure SDK classes (only used for type checking)
if TYPE_CHECKING:
    from azure.storage.blob import BlobServiceClient, ContainerClient
else:
    # Runtime fallback - these won't be used if Azure SDK is not installed
    BlobServiceClient = None
    ContainerClient = None

logger = logging.getLogger(__name__)


class AzureBlobProvider(StorageProvider):
    """Azure Blob Storage provider implementation"""

    def __init__(self, config: StorageConfig):
        self.config = config
        self._client: Optional["BlobServiceClient"] = None
        self._container: Optional["ContainerClient"] = None
        self._connected = False
        # Remove retry policy for now to avoid async issues
        self._retry_policy = None

    async def ensure_connected(self) -> None:
        """Ensure connection to Azure Blob Storage"""
        if not self._connected:
            await self.connect()

    async def connect(self) -> None:
        """Connect to Azure Blob Storage"""
        if not self._connected:
            try:
                # Lazy import Azure modules to avoid memory leaks
                from azure.storage.blob.aio import BlobServiceClient, ContainerClient

                # Get credentials from config
                account_name = self.config.credentials.get("account_name")
                account_key = self.config.credentials.get("account_key")

                if not account_name or not account_key:
                    raise ValueError("Azure storage account name and key are required")

                # Create connection string
                conn_str = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"

                # Create client without retry policy for now
                self._client = BlobServiceClient.from_connection_string(conn_str)

                # Get container client
                self._container = self._client.get_container_client(
                    self.config.bucket_name
                )

                # Ensure container exists
                try:
                    await self._container.get_container_properties()
                    logger.info(f"Container exists: {self.config.bucket_name}")
                except ResourceNotFoundError:
                    logger.warning(
                        f"Container {self.config.bucket_name} not found, but continuing..."
                    )
                    # Don't create container automatically for read-only testing

                self._connected = True
                logger.info(f"Connected to Azure Blob Storage: {account_name}")
            except Exception as e:
                logger.error(f"Failed to connect to Azure Blob Storage: {e}")
                raise

    async def disconnect(self) -> None:
        """Disconnect from Azure Blob Storage"""
        if self._connected or self._client or self._container:
            try:
                # Close container client first
                if self._container:
                    logger.debug("Closing Azure container client")
                    try:
                        await self._container.close()
                    except Exception as e:
                        logger.debug(f"Error closing container client: {e}")
                    finally:
                        self._container = None

                # Close blob service client (this closes underlying aiohttp session)
                if self._client:
                    logger.info(
                        "Closing Azure blob service client (this closes aiohttp session)"
                    )
                    try:
                        import asyncio
                        import aiohttp

                        # The Azure SDK's BlobServiceClient uses aiohttp internally
                        # The SDK should close the session when we call close(), but sometimes
                        # the event loop closes before the async close completes

                        # The Azure SDK's BlobServiceClient uses aiohttp internally
                        # We need to find and close the aiohttp session BEFORE closing the client
                        # This ensures the session is closed synchronously, not asynchronously
                        aiohttp_session = None
                        aiohttp_connector = None

                        try:
                            # Azure SDK structure:
                            # BlobServiceClient -> _client (AzureBlobStorage) -> _client (pipeline)
                            # -> _client (AsyncPipelineClient) -> _pipeline (AsyncPipeline)
                            # -> _transport (AioHttpTransport) -> session (aiohttp.ClientSession)
                            logger.debug(
                                "Attempting to find aiohttp session in Azure client"
                            )
                            if hasattr(self._client, "_client"):
                                pipeline = self._client._client
                                logger.debug(
                                    f"Found pipeline: {type(pipeline).__name__}"
                                )
                                if hasattr(pipeline, "_client"):
                                    http_client = pipeline._client
                                    logger.debug(
                                        f"Found HTTP client: {type(http_client).__name__}"
                                    )

                                    # Access the transport through the pipeline
                                    if hasattr(http_client, "_pipeline"):
                                        azure_pipeline = http_client._pipeline
                                        logger.debug(
                                            f"Found Azure pipeline: {type(azure_pipeline).__name__}"
                                        )
                                        if hasattr(azure_pipeline, "_transport"):
                                            transport = azure_pipeline._transport
                                            logger.debug(
                                                f"Found transport: {type(transport).__name__}"
                                            )

                                            # AioHttpTransport has a 'session' attribute (not '_session')
                                            if hasattr(transport, "session"):
                                                potential_session = transport.session
                                                logger.debug(
                                                    f"Found potential session: {type(potential_session).__name__}"
                                                )
                                                if isinstance(
                                                    potential_session,
                                                    aiohttp.ClientSession,
                                                ):
                                                    aiohttp_session = potential_session
                                                    logger.info(
                                                        f"Found aiohttp session in Azure transport: {aiohttp_session}, closed={aiohttp_session.closed}"
                                                    )

                                            # Also check for connector through the session
                                            if aiohttp_session and hasattr(
                                                aiohttp_session, "_connector"
                                            ):
                                                aiohttp_connector = (
                                                    aiohttp_session._connector
                                                )
                                                logger.info(
                                                    f"Found aiohttp connector: {aiohttp_connector}, closed={aiohttp_connector.closed if hasattr(aiohttp_connector, 'closed') else 'N/A'}"
                                                )
                                            else:
                                                logger.warning(
                                                    "aiohttp session found but no connector attribute"
                                                )
                                        else:
                                            logger.warning(
                                                "Azure pipeline has no _transport attribute"
                                            )
                                    else:
                                        logger.warning(
                                            "HTTP client has no _pipeline attribute"
                                        )
                                else:
                                    logger.warning("Pipeline has no _client attribute")
                            else:
                                logger.warning(
                                    "BlobServiceClient has no _client attribute"
                                )
                        except Exception as e:
                            logger.warning(
                                f"Could not find aiohttp session in Azure client: {e}",
                                exc_info=True,
                            )

                        # Close the transport FIRST - this is the proper way to close the aiohttp session
                        # The transport's close() method is async and will properly close the session
                        # Following the pattern from Azure SDK documentation and web search results
                        transport_to_close = None
                        try:
                            if hasattr(self._client, "_client"):
                                pipeline = self._client._client
                                if hasattr(pipeline, "_client"):
                                    http_client = pipeline._client
                                    if hasattr(http_client, "_pipeline"):
                                        azure_pipeline = http_client._pipeline
                                        if hasattr(azure_pipeline, "_transport"):
                                            transport_to_close = (
                                                azure_pipeline._transport
                                            )
                        except Exception as e:
                            logger.debug(f"Could not find transport to close: {e}")

                        if transport_to_close and hasattr(transport_to_close, "close"):
                            try:
                                logger.info(
                                    "Closing Azure transport (this will close the aiohttp session)"
                                )
                                await transport_to_close.close()
                                logger.debug("Azure transport closed successfully")
                                # Wait a bit for the session to fully close
                                await asyncio.sleep(0.1)
                            except Exception as e:
                                logger.warning(f"Error closing transport: {e}")

                        # Also try to close the session directly if we found it and transport close didn't work
                        # This is a fallback in case the transport close didn't fully close the session
                        if aiohttp_session and not aiohttp_session.closed:
                            logger.info(
                                f"Session still open after transport close, closing directly (session={aiohttp_session}, closed={aiohttp_session.closed})"
                            )
                            try:
                                # Close connector first if we found it (TCPConnector.close() is async)
                                if aiohttp_connector and not aiohttp_connector.closed:
                                    logger.debug("Closing aiohttp connector")
                                    import inspect

                                    if inspect.iscoroutinefunction(
                                        aiohttp_connector.close
                                    ):
                                        await aiohttp_connector.close()
                                    else:
                                        aiohttp_connector.close()
                                    await asyncio.sleep(0.05)

                                # Close the session (following FileResolver pattern)
                                logger.debug("Closing aiohttp session directly")
                                await aiohttp_session.close()
                                logger.debug(
                                    f"Session close() called, session.closed={aiohttp_session.closed}"
                                )

                                # Wait for the session to actually close
                                max_wait = 1.0  # 1 second max wait
                                wait_interval = 0.05
                                waited = 0.0
                                while not aiohttp_session.closed and waited < max_wait:
                                    await asyncio.sleep(wait_interval)
                                    waited += wait_interval

                                if aiohttp_session.closed:
                                    logger.info("aiohttp session closed successfully")
                                else:
                                    logger.warning(
                                        f"aiohttp session did not close within timeout (waited {waited}s, closed={aiohttp_session.closed})"
                                    )

                            except Exception as e:
                                logger.warning(
                                    f"Error closing aiohttp session: {e}", exc_info=True
                                )
                        elif aiohttp_session:
                            logger.debug(
                                f"aiohttp session already closed: {aiohttp_session}"
                            )
                        else:
                            logger.debug(
                                "No aiohttp session found - transport close should have handled it"
                            )

                        # Now close the blob service client
                        # Following the pattern from Azure OpenAI provider: ensure close() completes fully
                        # The Azure SDK's close() is async and should close the internal aiohttp session
                        # We need to ensure it completes before moving on
                        try:
                            # Use asyncio.wait_for to ensure close completes within a reasonable time
                            await asyncio.wait_for(self._client.close(), timeout=2.0)
                            logger.debug(
                                "BlobServiceClient.close() completed successfully"
                            )
                        except asyncio.TimeoutError:
                            logger.warning(
                                "BlobServiceClient.close() timed out, but continuing"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Error during BlobServiceClient.close(): {e}"
                            )

                        # Additional wait to ensure all async cleanup operations complete
                        # This is important because the Azure SDK uses aiohttp internally,
                        # and the session close is async and might need time to propagate
                        await asyncio.sleep(0.3)

                    except Exception as e:
                        logger.warning(f"Error closing blob service client: {e}")
                    finally:
                        self._client = None

                self._connected = False
                logger.info("Disconnected from Azure Blob Storage")
            except Exception as e:
                logger.warning(f"Error disconnecting from Azure Blob Storage: {e}")
                # Don't raise - try to continue cleanup
                self._connected = False
                self._container = None
                self._client = None

    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> StorageMetadata:
        """Store an object in Azure Blob Storage"""
        await self.ensure_connected()

        try:
            # Get blob client
            blob_client = self._container.get_blob_client(key)

            # Upload blob with metadata
            await blob_client.upload_blob(
                data, overwrite=True, content_type=content_type, metadata=metadata
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
                metadata=properties.metadata,
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

            # Set version if specified
            if version_id:
                blob_client = blob_client.get_blob_client(version_id=version_id)

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

            # Set version if specified
            if version_id:
                blob_client = blob_client.get_blob_client(version_id=version_id)

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
        max_keys: Optional[int] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """List objects in Azure Blob Storage"""
        await self.ensure_connected()

        try:
            # List blobs with prefix (remove delimiter for now)
            list_kwargs = {"name_starts_with": prefix}
            if delimiter:
                list_kwargs["delimiter"] = delimiter

            async for blob in self._container.list_blobs(**list_kwargs):
                yield {
                    "key": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified,
                    "etag": blob.etag,
                    "metadata": blob.metadata,
                }

                if max_keys and max_keys > 0:
                    max_keys -= 1
                    if max_keys == 0:
                        break
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            raise

    async def get_object_metadata(
        self, key: str, version_id: Optional[str] = None
    ) -> StorageMetadata:
        """Get metadata for an object"""
        await self.ensure_connected()

        try:
            # Get blob client
            blob_client = self._container.get_blob_client(key)

            # Set version if specified
            if version_id:
                blob_client = blob_client.get_blob_client(version_id=version_id)

            # Get blob properties
            properties = await blob_client.get_blob_properties()

            return StorageMetadata(
                content_type=properties.content_settings.content_type,
                size=properties.size,
                created_at=properties.creation_time,
                modified_at=properties.last_modified,
                etag=properties.etag,
                version_id=properties.version_id,
                metadata=properties.metadata,
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
        source_version_id: Optional[str] = None,
    ) -> StorageMetadata:
        """Copy an object to a new location"""
        await self.ensure_connected()

        try:
            # Get source and destination blob clients
            source_blob = self._container.get_blob_client(source_key)
            dest_blob = self._container.get_blob_client(destination_key)

            # Set source version if specified
            if source_version_id:
                source_blob = source_blob.get_blob_client(version_id=source_version_id)

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
                metadata=properties.metadata,
            )
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Source object not found: {source_key}")
        except Exception as e:
            logger.error(
                f"Failed to copy object {source_key} to {destination_key}: {e}"
            )
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
                "metadata": properties.metadata,
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

    # Azure-specific methods (not part of base interface)

    async def set_blob_tier(self, key: str, tier: str) -> None:
        """Set the tier of a blob"""
        await self.ensure_connected()

        try:
            blob_client = self._container.get_blob_client(key)
            await blob_client.set_standard_blob_tier(tier)
            logger.info(f"Set tier of blob {key} to {tier}")
        except Exception as e:
            logger.error(f"Failed to set tier of blob {key}: {e}")
            raise

    async def get_blob_tier(self, key: str) -> str:
        """Get the tier of a blob"""
        await self.ensure_connected()

        try:
            blob_client = self._container.get_blob_client(key)
            properties = await blob_client.get_blob_properties()
            return properties.blob_tier
        except Exception as e:
            logger.error(f"Failed to get tier of blob {key}: {e}")
            raise

    async def acquire_lease(
        self, key: str, duration: int = 60, proposed_lease_id: Optional[str] = None
    ) -> str:
        """Acquire a lease on a blob"""
        await self.ensure_connected()

        try:
            # Lazy import Azure modules
            from azure.storage.blob import BlobLeaseClient

            blob_client = self._container.get_blob_client(key)
            lease_client = BlobLeaseClient(blob_client)

            # Acquire lease
            lease_id = await lease_client.acquire_lease(
                duration=duration, proposed_lease_id=proposed_lease_id
            )

            logger.info(f"Acquired lease on blob {key}: {lease_id}")
            return lease_id
        except Exception as e:
            logger.error(f"Failed to acquire lease on blob {key}: {e}")
            raise

    async def release_lease(self, key: str, lease_id: str) -> None:
        """Release a lease on a blob"""
        await self.ensure_connected()

        try:
            # Lazy import Azure modules
            from azure.storage.blob import BlobLeaseClient

            blob_client = self._container.get_blob_client(key)
            lease_client = BlobLeaseClient(blob_client)

            # Release lease
            await lease_client.release_lease(lease_id)
            logger.info(f"Released lease on blob {key}: {lease_id}")
        except Exception as e:
            logger.error(f"Failed to release lease on blob {key}: {e}")
            raise

    async def create_snapshot(
        self, key: str, metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Create a snapshot of a blob"""
        await self.ensure_connected()

        try:
            blob_client = self._container.get_blob_client(key)
            snapshot = await blob_client.create_snapshot(metadata=metadata)
            logger.info(f"Created snapshot of blob {key}: {snapshot.snapshot}")
            return snapshot.snapshot
        except Exception as e:
            logger.error(f"Failed to create snapshot of blob {key}: {e}")
            raise

    async def list_snapshots(self, key: str) -> List[Dict[str, Any]]:
        """List snapshots of a blob"""
        await self.ensure_connected()

        try:
            snapshots = []
            async for blob in self._container.list_blobs(
                name_starts_with=key, include=["snapshots"]
            ):
                if blob.snapshot:
                    snapshots.append(
                        {
                            "snapshot": blob.snapshot,
                            "last_modified": blob.last_modified,
                            "size": blob.size,
                            "metadata": blob.metadata,
                        }
                    )
            return snapshots
        except Exception as e:
            logger.error(f"Failed to list snapshots of blob {key}: {e}")
            raise

    async def cleanup(self) -> None:
        """Clean up resources and close connections"""
        try:
            await self.disconnect()
            logger.info("Azure Blob Provider cleanup completed")
        except Exception as e:
            logger.error(f"Error during Azure Blob Provider cleanup: {e}")
            raise
