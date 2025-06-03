 # Storage Architecture

## Overview

The storage system in Supply Graph AI is designed to provide a flexible, extensible, and domain-specific storage solution for managing OKH manifests, OKW facilities, and supply trees. The architecture follows a provider-based pattern that allows for easy integration of different storage backends while maintaining a consistent interface for the application.

## Core Components

### Storage Service

The `StorageService` is the central component that manages storage operations and coordinates between different domain handlers. It implements the singleton pattern to ensure a single instance manages all storage operations.

```python
class StorageService:
    _instance = None
    
    @classmethod
    async def get_instance(cls) -> 'StorageService':
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance.initialize()
        return cls._instance
```

### Storage Provider

The `StorageProvider` interface defines the contract that all storage implementations must follow. It provides methods for basic CRUD operations and domain-specific functionality.

```python
class StorageProvider(ABC):
    @abstractmethod
    async def save_object(self, object_id: UUID, data: Dict[str, Any]) -> bool:
        """Save an object to storage"""
        pass

    @abstractmethod
    async def load_object(self, object_id: UUID) -> Optional[Dict[str, Any]]:
        """Load an object from storage"""
        pass

    @abstractmethod
    async def delete_object(self, object_id: UUID) -> bool:
        """Delete an object from storage"""
        pass

    @abstractmethod
    async def list_objects(
        self,
        limit: int = 100,
        offset: int = 0,
        filter_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List objects with pagination and filtering"""
        pass
```

### Domain Handlers

Domain handlers are specialized components that handle storage operations for specific domains (OKH, OKW, etc.). They implement the `StorageProvider` interface and provide domain-specific functionality.

```python
class OKHStorageHandler(StorageProvider):
    """Handler for OKH manifest storage operations"""
    pass

class OKWStorageHandler(StorageProvider):
    """Handler for OKW facility storage operations"""
    pass

class SupplyTreeStorageHandler(StorageProvider):
    """Handler for supply tree storage operations"""
    pass
```

## Storage Flow

1. **Initialization**
   - The `StorageService` is initialized with configuration settings
   - Domain handlers are registered with the service
   - Storage providers are configured and connected

2. **Object Storage**
   - Domain services (OKH, OKW) request storage operations
   - `StorageService` routes requests to appropriate domain handlers
   - Domain handlers use storage providers to perform operations

3. **Object Retrieval**
   - Domain services request objects by ID
   - `StorageService` locates the appropriate handler
   - Handler retrieves and returns the object

## Configuration

Storage configuration is managed through environment variables and configuration files:

```yaml
storage:
  provider: "local"  # or "s3", "azure", etc.
  base_path: "./data"
  okh:
    path: "okh"
  okw:
    path: "okw"
  supply_trees:
    path: "supply_trees"
```

## Error Handling

The storage system implements custom errors for error handling:

- **StorageError**: Base exception for storage-related errors
- **ObjectNotFoundError**: Raised when an object cannot be found
- **StorageConnectionError**: Raised when storage connection fails
- **ValidationError**: Raised when object validation fails

## Logging

The storage system uses structured logging to track operations:

```python
logger.info(
    "Saving object to storage",
    extra={
        "object_id": str(object_id),
        "domain": domain,
        "size": len(data)
    }
)
```

## Best Practices

1. **Always use domain handlers** for storage operations
2. **Validate objects** before storage
3. **Handle errors appropriately** at each level
4. **Use structured logging** for debugging
5. **Implement proper cleanup** in storage providers

## Extending the System

To add a new storage provider:

1. Create a new class implementing `StorageProvider`
2. Implement all required methods
3. Add provider-specific configuration
4. Register the provider with `StorageService`

Example:

```python
class S3StorageProvider(StorageProvider):
    def __init__(self, config: Dict[str, Any]):
        self.bucket = config["bucket"]
        self.client = boto3.client("s3")

    async def save_object(self, object_id: UUID, data: Dict[str, Any]) -> bool:
        # Implementation
        pass
```

## Future Considerations

1. **Caching Layer**: Implement caching for frequently accessed objects
2. **Batch Operations**: Add support for batch storage operations
3. **Versioning**: Add support for object versioning
4. **Replication**: Implement storage replication for high availability
5. **Encryption**: Add support for object encryption at rest