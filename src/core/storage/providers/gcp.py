import logging
import json
import asyncio
from typing import Optional, Dict, Any, List, AsyncIterator
from datetime import datetime

from ..base import StorageProvider, StorageConfig, StorageMetadata

logger = logging.getLogger(__name__)


class GCSProvider(StorageProvider):
    """Google Cloud Storage provider implementation"""

    def __init__(self, config: StorageConfig):
        self.config = config
        self._client: Optional[Any] = None
        self._bucket: Optional[Any] = None
        self._connected = False

    async def ensure_connected(self) -> None:
        """Ensure connection to Google Cloud Storage"""
        if not self._connected:
            await self.connect()

    def _get_credentials(self) -> Any:
        """Get GCP credentials from config"""
        try:
            from google.oauth2 import service_account

            credentials_json = self.config.credentials.get("credentials_json")
            credentials_path = self.config.credentials.get("credentials_path")
            project_id = self.config.credentials.get("project_id")

            # If credentials_json is provided as a string, parse it
            if credentials_json:
                if isinstance(credentials_json, str):
                    try:
                        # Try parsing as JSON string
                        creds_dict = json.loads(credentials_json)
                    except json.JSONDecodeError:
                        # If it's not valid JSON, treat as file path
                        credentials_path = credentials_json
                        creds_dict = None
                else:
                    creds_dict = credentials_json

                if creds_dict:
                    credentials = service_account.Credentials.from_service_account_info(
                        creds_dict
                    )
                    if not project_id:
                        project_id = creds_dict.get("project_id")
                    return credentials, project_id

            # If credentials_path is provided, load from file
            if credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                if not project_id:
                    # Try to extract project_id from credentials file
                    with open(credentials_path, "r") as f:
                        creds_dict = json.load(f)
                        project_id = creds_dict.get("project_id")
                return credentials, project_id

            # Fall back to default credentials (Application Default Credentials)
            logger.info("Using Application Default Credentials")
            return None, project_id

        except ImportError:
            raise ImportError(
                "Google Cloud Storage libraries not installed. "
                "Please install with: pip install google-cloud-storage"
            )

    async def connect(self) -> None:
        """Connect to Google Cloud Storage"""
        if not self._connected:
            try:
                from google.cloud import storage

                credentials, project_id = await asyncio.to_thread(self._get_credentials)

                # Create client (synchronous operation, but fast)
                def _create_client():
                    if credentials:
                        return storage.Client(
                            credentials=credentials, project=project_id
                        )
                    else:
                        return storage.Client(project=project_id)

                self._client = await asyncio.to_thread(_create_client)

                # Get bucket
                self._bucket = self._client.bucket(self.config.bucket_name)

                # Verify bucket exists (blocking I/O)
                def _check_bucket():
                    return self._bucket.exists()

                bucket_exists = await asyncio.to_thread(_check_bucket)
                if not bucket_exists:
                    logger.warning(
                        f"Bucket {self.config.bucket_name} does not exist, but continuing..."
                    )
                    # Don't create bucket automatically - user should create it first

                self._connected = True
                logger.info(
                    f"Connected to Google Cloud Storage: {self.config.bucket_name}"
                )
            except Exception as e:
                logger.error(f"Failed to connect to Google Cloud Storage: {e}")
                raise

    async def disconnect(self) -> None:
        """Disconnect from Google Cloud Storage"""
        if self._connected:
            try:
                self._client = None
                self._bucket = None
                self._connected = False
                logger.info("Disconnected from Google Cloud Storage")
            except Exception as e:
                logger.error(f"Error disconnecting from Google Cloud Storage: {e}")
                raise

    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> StorageMetadata:
        """Store an object in Google Cloud Storage"""
        await self.ensure_connected()

        try:
            blob = self._bucket.blob(key)

            # Set content type
            blob.content_type = content_type

            # Set metadata
            if metadata:
                blob.metadata = metadata

            # Upload data (blocking I/O)
            def _upload():
                blob.upload_from_string(data, content_type=content_type)
                blob.reload()
                return blob

            blob = await asyncio.to_thread(_upload)

            return StorageMetadata(
                content_type=blob.content_type or content_type,
                size=blob.size,
                created_at=blob.time_created,
                modified_at=blob.updated,
                etag=blob.etag,
                version_id=str(blob.generation) if blob.generation else None,
                metadata=blob.metadata or {},
            )
        except Exception as e:
            logger.error(f"Failed to store object {key}: {e}")
            raise

    async def get_object(self, key: str, version_id: Optional[str] = None) -> bytes:
        """Retrieve an object from Google Cloud Storage"""
        await self.ensure_connected()

        try:
            blob = self._bucket.blob(key)

            # Set generation (version) if specified
            if version_id:
                blob = self._bucket.blob(key, generation=int(version_id))

            # Check existence and download (blocking I/O)
            def _get():
                if not blob.exists():
                    raise FileNotFoundError(f"Object not found: {key}")
                return blob.download_as_bytes()

            return await asyncio.to_thread(_get)
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve object {key}: {e}")
            raise

    async def delete_object(self, key: str, version_id: Optional[str] = None) -> bool:
        """Delete an object from Google Cloud Storage"""
        await self.ensure_connected()

        try:
            blob = self._bucket.blob(key)

            # Set generation (version) if specified
            if version_id:
                blob = self._bucket.blob(key, generation=int(version_id))

            # Check existence and delete (blocking I/O)
            def _delete():
                if not blob.exists():
                    return False
                blob.delete()
                return True

            return await asyncio.to_thread(_delete)
        except Exception as e:
            logger.error(f"Failed to delete object {key}: {e}")
            return False

    async def list_objects(
        self,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        max_keys: Optional[int] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """List objects in Google Cloud Storage"""
        await self.ensure_connected()

        try:
            # List blobs with prefix (blocking I/O, but we'll iterate in thread)
            list_kwargs = {}
            if prefix:
                list_kwargs["prefix"] = prefix
            if delimiter:
                list_kwargs["delimiter"] = delimiter
            if max_keys:
                list_kwargs["max_results"] = max_keys

            def _list_blobs():
                return list(self._bucket.list_blobs(**list_kwargs))

            blobs = await asyncio.to_thread(_list_blobs)

            count = 0
            for blob in blobs:
                yield {
                    "key": blob.name,
                    "size": blob.size,
                    "last_modified": blob.updated,
                    "etag": blob.etag,
                    "metadata": blob.metadata or {},
                }

                count += 1
                if max_keys and count >= max_keys:
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
            blob = self._bucket.blob(key)

            # Set generation (version) if specified
            if version_id:
                blob = self._bucket.blob(key, generation=int(version_id))

            # Check existence and reload (blocking I/O)
            def _get_metadata():
                if not blob.exists():
                    raise FileNotFoundError(f"Object not found: {key}")
                blob.reload()
                return blob

            blob = await asyncio.to_thread(_get_metadata)

            return StorageMetadata(
                content_type=blob.content_type or "application/octet-stream",
                size=blob.size,
                created_at=blob.time_created,
                modified_at=blob.updated,
                etag=blob.etag,
                version_id=str(blob.generation) if blob.generation else None,
                metadata=blob.metadata or {},
            )
        except FileNotFoundError:
            raise
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
            source_blob = self._bucket.blob(source_key)

            # Set source generation (version) if specified
            if source_version_id:
                source_blob = self._bucket.blob(
                    source_key, generation=int(source_version_id)
                )

            # Create destination blob
            dest_blob = self._bucket.blob(destination_key)

            # Copy from source (blocking I/O)
            def _copy():
                if not source_blob.exists():
                    raise FileNotFoundError(f"Source object not found: {source_key}")
                dest_blob.rewrite(source_blob)
                dest_blob.reload()
                return dest_blob

            dest_blob = await asyncio.to_thread(_copy)

            return StorageMetadata(
                content_type=dest_blob.content_type or "application/octet-stream",
                size=dest_blob.size,
                created_at=dest_blob.time_created,
                modified_at=dest_blob.updated,
                etag=dest_blob.etag,
                version_id=str(dest_blob.generation) if dest_blob.generation else None,
                metadata=dest_blob.metadata or {},
            )
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to copy object {source_key} to {destination_key}: {e}"
            )
            raise

    async def create_bucket(self, bucket_name: str) -> bool:
        """Create a new bucket"""
        await self.ensure_connected()

        try:
            # Get location from config or use default
            location = self.config.region or "US"

            # Create bucket (blocking I/O)
            def _create():
                new_bucket = self._client.create_bucket(bucket_name, location=location)
                logger.info(f"Created bucket: {bucket_name} in location: {location}")
                return True

            return await asyncio.to_thread(_create)
        except Exception as e:
            logger.error(f"Failed to create bucket {bucket_name}: {e}")
            return False

    async def delete_bucket(self, bucket_name: str) -> bool:
        """Delete a bucket"""
        await self.ensure_connected()

        try:
            bucket = self._client.bucket(bucket_name)

            # Delete bucket (blocking I/O)
            def _delete():
                bucket.delete(force=True)  # force=True deletes even if not empty
                logger.info(f"Deleted bucket: {bucket_name}")
                return True

            return await asyncio.to_thread(_delete)
        except Exception as e:
            logger.error(f"Failed to delete bucket {bucket_name}: {e}")
            return False

    async def list_buckets(self) -> List[str]:
        """List all buckets"""
        await self.ensure_connected()

        try:
            # List buckets (blocking I/O)
            def _list():
                return [bucket.name for bucket in self._client.list_buckets()]

            return await asyncio.to_thread(_list)
        except Exception as e:
            logger.error(f"Failed to list buckets: {e}")
            raise

    async def get_bucket_metadata(self, bucket_name: str) -> Dict[str, Any]:
        """Get metadata for a bucket"""
        await self.ensure_connected()

        try:
            bucket = self._client.bucket(bucket_name)

            # Check existence and reload (blocking I/O)
            def _get_metadata():
                if not bucket.exists():
                    raise FileNotFoundError(f"Bucket not found: {bucket_name}")
                bucket.reload()
                return {
                    "name": bucket.name,
                    "created_at": bucket.time_created,
                    "modified_at": bucket.updated,
                    "location": bucket.location,
                    "storage_class": bucket.storage_class,
                    "metadata": bucket.labels or {},
                }

            return await asyncio.to_thread(_get_metadata)
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get metadata for bucket {bucket_name}: {e}")
            raise

    async def set_bucket_policy(self, bucket_name: str, policy: Dict[str, Any]) -> bool:
        """Set bucket policy"""
        await self.ensure_connected()

        try:
            bucket = self._client.bucket(bucket_name)

            # GCS uses IAM policies, not bucket policies like S3
            # This is a simplified implementation
            logger.warning(
                "Bucket policy setting is simplified for GCS. Use IAM policies for full control."
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set bucket policy for {bucket_name}: {e}")
            return False

    async def get_bucket_policy(self, bucket_name: str) -> Dict[str, Any]:
        """Get bucket policy"""
        await self.ensure_connected()

        try:
            bucket = self._client.bucket(bucket_name)

            # GCS uses IAM policies (blocking I/O)
            def _get_policy():
                policy = bucket.get_iam_policy()
                return {
                    "bindings": [
                        {"role": binding["role"], "members": list(binding["members"])}
                        for binding in policy.bindings
                    ]
                }

            return await asyncio.to_thread(_get_policy)
        except Exception as e:
            logger.error(f"Failed to get bucket policy for {bucket_name}: {e}")
            return {}

    async def cleanup(self) -> None:
        """Clean up resources and close connections"""
        try:
            await self.disconnect()
            logger.info("GCS Provider cleanup completed")
        except Exception as e:
            logger.error(f"Error during GCS Provider cleanup: {e}")
            raise
