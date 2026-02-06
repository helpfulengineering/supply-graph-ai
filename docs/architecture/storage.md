 # Storage Architecture

## Overview

The storage system in Supply Graph AI provides a flexible, extensible, and domain-specific storage solution for managing OKH manifests, OKW facilities, and supply trees. The architecture follows a provider-based pattern with a unified interface that supports multiple storage backends including local filesystem, Azure Blob Storage, AWS S3, and Google Cloud Storage.

## Getting Started with Local Storage

### Quick Start (Recommended for New Users)

Local storage is the easiest way to get started with OHM. It requires no cloud accounts, no credentials, and works immediately on your local machine or network-attached storage.

**1. Configure Local Storage**

Edit your `.env` file (or create one from `env.template`):

```bash
# Storage Configuration
STORAGE_PROVIDER=local
LOCAL_STORAGE_PATH=./storage
```

**2. Set Up Storage Structure**

```bash
# Create the directory structure
ohm storage setup --provider local
```

This creates:
```
./storage/
├── okh/
│   └── manifests/
├── okw/
│   └── facilities/
└── supply-trees/
    ├── generated/
    └── validated/
```

**3. Start Using Storage**

You're done! OHM will now store all data in the `./storage` directory.

### Local Storage Path Options

Local storage supports multiple path formats:

```bash
# Relative to project root (default)
LOCAL_STORAGE_PATH=./storage

# Home directory expansion
LOCAL_STORAGE_PATH=~/ohm-data
LOCAL_STORAGE_PATH=~/Documents/ohm-storage

# Absolute paths
LOCAL_STORAGE_PATH=/var/lib/ohm/storage
LOCAL_STORAGE_PATH=/opt/ohm-data

# Network-attached storage
LOCAL_STORAGE_PATH=/mnt/nas/ohm-storage
LOCAL_STORAGE_PATH=/Volumes/shared/ohm-data  # macOS network drive
```

### When to Use Local Storage

**✅ Perfect for:**
- Getting started and learning OHM
- Development and testing
- Self-hosted single-server deployments
- Network-attached storage (NAS) setups
- Air-gapped or offline environments
- Privacy-sensitive data that must stay on-premises

**⚠️ Consider Cloud Storage for:**
- Multi-server production deployments
- Automatic backup and disaster recovery
- Team collaboration across locations
- Global content delivery
- Automatic scaling and high availability

### Local Storage Features

The local storage provider offers full feature parity with cloud providers:

- ✅ **All storage operations**: Create, read, update, delete, list
- ✅ **Metadata tracking**: Content type, size, timestamps, custom metadata
- ✅ **Domain organization**: Automatic organization by OKH, OKW, supply-trees
- ✅ **Async operations**: High-performance async file I/O
- ✅ **Cross-platform**: Works on Windows, macOS, Linux
- ✅ **ETag generation**: MD5 hashing for data integrity

### Troubleshooting Local Storage

**Directory not found error:**
```bash
# Ensure parent directory exists or use absolute path
mkdir -p ~/ohm-data
LOCAL_STORAGE_PATH=~/ohm-data ohm storage setup
```

**Permission denied error:**
```bash
# Check and fix permissions
ls -ld ./storage
chmod 755 ./storage  # On Unix-like systems
```

**Storage not found after setup:**
```bash
# Verify configuration
cat .env | grep STORAGE
# Should show: STORAGE_PROVIDER=local

# Verify path exists
ls -la ./storage
```

## Core Components

### Storage Service

The `StorageService` is the central component that manages storage operations and coordinates between different domain handlers. It implements the singleton pattern and provides a unified interface for all storage operations.

```python
class StorageService:
    _instance = None
    
    @classmethod
    async def get_instance(cls) -> 'StorageService':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def configure(self, config: StorageConfig) -> None:
        """Configure storage service with provider settings"""
        self.manager = StorageManager(config)
        await self.manager.connect()
        self._configured = True
```

### Storage Manager

The `StorageManager` manages the lifecycle of storage providers and provides a unified interface for storage operations. It handles provider creation, connection management, and operation delegation.

```python
class StorageManager:
    def __init__(self, config: StorageConfig):
        self.config = config
        self._provider: Optional[StorageProvider] = None
        self._connected = False
    
    def _create_provider(self) -> StorageProvider:
        """Create appropriate storage provider based on config"""
        provider_map = {
            "aws_s3": AWSS3Provider,
            "azure_blob": AzureBlobProvider,
            "gcs": GCSProvider,
            "local": LocalStorageProvider
        }
        return provider_map[self.config.provider](self.config)
```

### Storage Provider Interface

The `StorageProvider` interface defines the contract that all storage implementations must follow. It provides methods for object operations, bucket management, and metadata handling.

```python
class StorageProvider(ABC):
    @abstractmethod
    async def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None
    ) -> StorageMetadata:
        """Store an object in the storage provider"""
        pass

    @abstractmethod
    async def get_object(self, key: str, version_id: Optional[str] = None) -> bytes:
        """Retrieve an object from the storage provider"""
        pass

    @abstractmethod
    async def list_objects(
        self,
        prefix: Optional[str] = None,
        delimiter: Optional[str] = None,
        max_keys: Optional[int] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """List objects in the storage provider"""
        pass

    @abstractmethod
    async def delete_object(self, key: str, version_id: Optional[str] = None) -> bool:
        """Delete an object from the storage provider"""
        pass
```

### Domain Storage Handlers

Domain handlers are specialized components that handle storage operations for specific domains (OKH, OKW, Supply Trees). They extend the `DomainStorageHandler` base class and provide domain-specific serialization and deserialization.

```python
class DomainStorageHandler(Generic[T]):
    """Base class for domain-specific storage handlers"""
    
    def __init__(self, storage_service: StorageService):
        self.storage_service = storage_service
        self.domain = self._get_domain()
    
    async def save(self, obj: T) -> str:
        """Save a domain object to storage"""
        obj_data = self._serialize(obj)
        data = json.dumps(obj_data).encode('utf-8')
        key = self._get_storage_key(self._get_object_id(obj))
        metadata = await self.storage_service.manager.put_object(
            key=key,
            data=data,
            content_type="application/json",
            metadata={"domain": self.domain, "type": self._get_object_type(obj)}
        )
        return metadata.etag
```

## Storage Flow

1. **Initialization**
   - The `StorageService` singleton is created via `get_instance()`
   - Storage configuration is loaded from environment variables
   - `StorageManager` creates the appropriate provider (Azure, AWS, GCS, or Local)
   - Provider connects to the storage backend

2. **Object Storage**
   - Domain services request storage operations through `StorageService`
   - `StorageService` delegates to `StorageManager`
   - `StorageManager` uses the configured provider to store objects
   - Objects are serialized to JSON and stored with metadata

3. **Object Retrieval**
   - Domain services request objects by ID or list operations
   - `StorageService` routes requests through `StorageManager`
   - Provider retrieves objects and returns raw bytes
   - Objects are deserialized from JSON back to domain models

4. **Real-time Processing**
   - The `/v1/match` endpoint automatically loads OKW facilities from storage
   - Files are parsed in real-time (YAML/JSON) and converted to domain objects
   - Invalid files are logged and skipped to ensure robust operation

## Configuration

Storage configuration is managed through environment variables and the `StorageConfig` class:

### Environment Variables

**Local Storage (Recommended for getting started):**
```bash
STORAGE_PROVIDER=local
LOCAL_STORAGE_PATH=./storage

# Alternative paths:
# LOCAL_STORAGE_PATH=~/ohm-data           # Home directory
# LOCAL_STORAGE_PATH=/var/lib/ohm         # System directory
# LOCAL_STORAGE_PATH=/mnt/nas/ohm-storage # Network storage
```

**Azure Blob Storage:**
```bash
STORAGE_PROVIDER=azure_blob
AZURE_STORAGE_ACCOUNT=your_account_name
AZURE_STORAGE_KEY=your_account_key
AZURE_STORAGE_CONTAINER=your_container_name
```

**AWS S3:**
```bash
STORAGE_PROVIDER=aws_s3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
AWS_S3_BUCKET=your_bucket_name
```

**Google Cloud Storage:**
```bash
STORAGE_PROVIDER=gcs
GCP_PROJECT_ID=your_project_id
GCP_CREDENTIALS_JSON=your_credentials_json
GCP_STORAGE_BUCKET=your_bucket_name
```

### Configuration Creation

```python
from src.config.storage_config import create_storage_config

# Create config for specific provider
config = create_storage_config(
    provider="azure_blob",
    bucket_name="okw-facilities"
)

# Or get default config from environment
config = get_default_storage_config()
```

## Error Handling

The storage system implements comprehensive error handling with custom exceptions:

- **StorageConfigError**: Base exception for storage configuration errors
- **MissingCredentialsError**: Raised when required credentials are missing
- **StorageConnectionError**: Raised when storage connection fails
- **ObjectNotFoundError**: Raised when an object cannot be found
- **ValidationError**: Raised when object validation fails

### Error Handling Examples

```python
try:
    config = create_storage_config("azure_blob")
except MissingCredentialsError as e:
    logger.error(f"Configuration error: {e}")
    # Handle missing credentials

try:
    await storage_service.save_object(obj_id, data)
except StorageConnectionError as e:
    logger.error(f"Storage connection failed: {e}")
    # Handle connection issues
```

## Logging

The storage system uses structured logging to track operations and provide debugging information:

```python
logger.info(
    "Connected to storage provider",
    extra={
        "provider": config.provider,
        "bucket": config.bucket_name
    }
)

logger.info(
    "Saving object to storage",
    extra={
        "key": key,
        "domain": domain,
        "size": len(data),
        "content_type": content_type
    }
)
```

## Current Implementation Status

### ✅ Implemented Features

**Storage Providers:**
- **Azure Blob Storage**: Full implementation with async support
- **AWS S3**: Complete implementation with boto3 integration
- **Google Cloud Storage**: Full implementation with GCS client
- **Local Storage**: Filesystem-based storage with metadata support

**Core Functionality:**
- **Object Operations**: Put, get, delete, list with full async support
- **Metadata Management**: Content type, size, timestamps, custom metadata
- **Bucket Management**: Create, delete, list buckets/containers
- **Versioning Support**: Object versioning where supported by provider
- **Connection Management**: Automatic connection/disconnection handling

**Domain Integration:**
- **OKH Storage**: Specialized handlers for OKH manifest storage
- **OKW Storage**: Specialized handlers for OKW facility storage
- **Supply Tree Storage**: Specialized handlers for supply tree storage
- **Real-time Processing**: Automatic loading and parsing of storage files

**Configuration:**
- **Environment-based**: Automatic configuration from environment variables
- **Multi-provider**: Support for switching between storage providers
- **Credential Management**: Secure credential handling for all providers
- **Validation**: Comprehensive configuration validation

### 🚧 In Progress

**Advanced Features:**
- **Caching Layer**: Planned implementation for frequently accessed objects
- **Batch Operations**: Support for bulk storage operations
- **Encryption**: Object-level encryption at rest
- **Replication**: Cross-region replication for high availability

## Best Practices

1. **Use StorageService Singleton**: Always access storage through `StorageService.get_instance()`
2. **Configure Before Use**: Ensure storage service is configured before performing operations
3. **Handle Errors Gracefully**: Use try-catch blocks for storage operations
4. **Use Domain Handlers**: Leverage domain-specific handlers for type-safe operations
5. **Validate Configuration**: Check environment variables and credentials before initialization
6. **Use Structured Logging**: Include relevant context in log messages
7. **Implement Proper Cleanup**: Disconnect from storage providers when done

### Example Usage

```python
# Initialize storage service
storage_service = await StorageService.get_instance()
config = create_storage_config("azure_blob")
await storage_service.configure(config)

# Use domain handlers
okh_handler = storage_service.get_domain_handler("okh")
await okh_handler.save(okh_manifest)

# Handle errors appropriately
try:
    manifest = await okh_handler.load(manifest_id)
except Exception as e:
    logger.error(f"Failed to load OKH manifest: {e}")
    raise
```

## Extending the System

### Adding a New Storage Provider

1. **Create Provider Class**: Implement `StorageProvider` interface
2. **Add Configuration**: Update `create_storage_config()` function
3. **Register Provider**: Add to provider map in `StorageManager`
4. **Add Credentials**: Implement credential retrieval function

```python
class CustomStorageProvider(StorageProvider):
    def __init__(self, config: StorageConfig):
        self.config = config
        self.client = self._create_client()
    
    async def connect(self) -> None:
        """Connect to custom storage"""
        await self.client.connect()
    
    async def put_object(self, key: str, data: bytes, 
                        content_type: str, metadata: Dict[str, str]) -> StorageMetadata:
        """Store object in custom storage"""
        # Implementation
        pass
```

### Adding a New Domain Handler

1. **Create Handler Class**: Extend `DomainStorageHandler`
2. **Implement Serialization**: Define `_serialize()` and `_deserialize()` methods
3. **Register Handler**: Add to `StorageRegistry`

```python
class CustomDomainStorageHandler(DomainStorageHandler[CustomModel]):
    def _serialize(self, obj: CustomModel) -> Dict[str, Any]:
        """Convert custom model to dictionary"""
        return obj.to_dict()
    
    def _deserialize(self, data: Dict[str, Any]) -> CustomModel:
        """Convert dictionary to custom model"""
        return CustomModel.from_dict(data)
    
    def _get_object_id(self, obj: CustomModel) -> UUID:
        """Get object ID from custom model"""
        return obj.id
```

## Future Considerations

### Planned Enhancements

1. **Caching Layer**: Redis-based caching for frequently accessed objects
2. **Batch Operations**: Bulk upload/download operations for efficiency
3. **Object Versioning**: Full versioning support across all providers
4. **Cross-Region Replication**: Automatic replication for high availability
5. **Encryption at Rest**: Object-level encryption with key management
6. **Performance Monitoring**: Metrics and monitoring for storage operations
7. **Backup and Recovery**: Automated backup and disaster recovery
8. **Multi-tenant Support**: Tenant isolation and resource quotas

### Integration Opportunities

1. **CDN Integration**: Content delivery network for global access
2. **Search Integration**: Full-text search across stored objects
3. **Analytics Integration**: Storage usage analytics and reporting
4. **Workflow Integration**: Event-driven storage operations
5. **API Gateway Integration**: Rate limiting and access control