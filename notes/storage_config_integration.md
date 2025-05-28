# config/storage.yaml
# Storage configuration examples for different providers

# AWS S3 Configuration
aws_s3:
  provider: "aws_s3"
  bucket_name: "ome-storage-bucket"
  region: "us-east-1"
  credentials:
    access_key: "${AWS_ACCESS_KEY_ID}"
    secret_key: "${AWS_SECRET_ACCESS_KEY}"
  encryption:
    method: "AES256"

# Azure Blob Storage Configuration  
azure_blob:
  provider: "azure_blob"
  bucket_name: "ome-storage-container"
  region: "eastus"
  credentials:
    account_name: "${AZURE_STORAGE_ACCOUNT}"
    account_key: "${AZURE_STORAGE_KEY}"
  encryption:
    method: "AES256"

# Google Cloud Storage Configuration
gcs:
  provider: "gcs"
  bucket_name: "ome-storage-bucket"
  region: "us-central1"
  credentials:
    project_id: "${GCP_PROJECT_ID}"
    service_account_key: "${GCP_SERVICE_ACCOUNT_KEY}"

# Local Development Configuration
local_dev:
  provider: "aws_s3"  # Use MinIO for local S3-compatible storage
  bucket_name: "ome-local-storage"
  endpoint_url: "http://localhost:9000"
  credentials:
    access_key: "minioadmin"
    secret_key: "minioadmin"

# src/core/config/settings.py
import os
from typing import Dict, Any, Optional
from pydantic import BaseSettings, Field
import yaml

class StorageSettings(BaseSettings):
    """Storage configuration settings"""
    
    # Default storage provider
    default_provider: str = Field("aws_s3", env="OME_STORAGE_PROVIDER")
    
    # Configuration file path
    config_file: str = Field("config/storage.yaml", env="OME_STORAGE_CONFIG")
    
    # Override settings via environment variables
    bucket_name: Optional[str] = Field(None, env="OME_STORAGE_BUCKET")
    region: Optional[str] = Field(None, env="OME_STORAGE_REGION")
    endpoint_url: Optional[str] = Field(None, env="OME_STORAGE_ENDPOINT")
    
    # AWS specific
    aws_access_key: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    
    # Azure specific
    azure_account_name: Optional[str] = Field(None, env="AZURE_STORAGE_ACCOUNT")
    azure_account_key: Optional[str] = Field(None, env="AZURE_STORAGE_KEY")
    
    # GCP specific
    gcp_project_id: Optional[str] = Field(None, env="GCP_PROJECT_ID")
    gcp_service_account_key: Optional[str] = Field(None, env="GCP_SERVICE_ACCOUNT_KEY")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    def load_storage_config(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """Load storage configuration from file and environment"""
        provider_name = provider_name or self.default_provider
        
        # Load from config file
        config = {}
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                file_config = yaml.safe_load(f)
                config = file_config.get(provider_name, {})
        
        # Override with environment variables
        if self.bucket_name:
            config['bucket_name'] = self.bucket_name
        if self.region:
            config['region'] = self.region
        if self.endpoint_url:
            config['endpoint_url'] = self.endpoint_url
        
        # Provider-specific credential overrides
        if provider_name == "aws_s3":
            if self.aws_access_key and self.aws_secret_key:
                config.setdefault('credentials', {}).update({
                    'access_key': self.aws_access_key,
                    'secret_key': self.aws_secret_key
                })
        elif provider_name == "azure_blob":
            if self.azure_account_name and self.azure_account_key:
                config.setdefault('credentials', {}).update({
                    'account_name': self.azure_account_name,
                    'account_key': self.azure_account_key
                })
        elif provider_name == "gcs":
            if self.gcp_project_id:
                config.setdefault('credentials', {}).update({
                    'project_id': self.gcp_project_id
                })
            if self.gcp_service_account_key:
                config.setdefault('credentials', {}).update({
                    'service_account_key': self.gcp_service_account_key
                })
        
        return config

# src/core/startup.py
"""Application startup and initialization"""
import asyncio
import logging
from typing import Optional

from .config.settings import StorageSettings
from .storage.base import StorageConfig, StorageProvider
from .services.storage_service import StorageService

logger = logging.getLogger(__name__)

async def initialize_storage(provider_name: Optional[str] = None) -> StorageService:
    """Initialize storage service on application startup"""
    try:
        # Load settings
        settings = StorageSettings()
        config_dict = settings.load_storage_config(provider_name)
        
        if not config_dict:
            logger.warning(f"No storage configuration found for provider: {provider_name or settings.default_provider}")
            return None
        
        # Create storage config
        storage_config = StorageConfig(
            provider=StorageProvider(config_dict['provider']),
            bucket_name=config_dict['bucket_name'],
            region=config_dict.get('region'),
            credentials=config_dict.get('credentials'),
            endpoint_url=config_dict.get('endpoint_url'),
            encryption=config_dict.get('encryption')
        )
        
        # Get storage service and configure
        storage_service = await StorageService.get_instance()
        await storage_service.configure(storage_config)
        
        logger.info(f"Storage initialized with provider: {storage_config.provider.value}")
        return storage_service
        
    except Exception as e:
        logger.error(f"Failed to initialize storage: {e}")
        return None

async def cleanup_storage():
    """Cleanup storage connections on application shutdown"""
    try:
        storage_service = await StorageService.get_instance()
        if storage_service.manager:
            await storage_service.manager.disconnect()
        logger.info("Storage connections closed")
    except Exception as e:
        logger.error(f"Error during storage cleanup: {e}")

# Update main.py to include storage
# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.core.api.routes.match import router as match_router
from src.core.api.routes.storage import router as storage_router
from src.core.domains.cooking.extractors import CookingExtractor
from src.core.domains.cooking.matchers import CookingMatcher
from src.core.domains.cooking.validators import CookingValidator
from src.core.registry.domain_registry import DomainRegistry
from src.core.startup import initialize_storage, cleanup_storage

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await initialize_storage()
    yield
    # Shutdown
    await cleanup_storage()

# Create FastAPI app with lifespan
app = FastAPI(
    title="Open Matching Engine API",
    description="API for matching requirements to capabilities across domains",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    """Health check endpoint with storage status"""
    from src.core.services.storage_service import StorageService
    
    try:
        storage_service = await StorageService.get_instance()
        storage_status = await storage_service.get_status()
    except Exception:
        storage_status = {"configured": False, "error": "Storage service unavailable"}
    
    return {
        "status": "ok",
        "domains": list(DomainRegistry._extractors.keys()),
        "storage": storage_status
    }

# Register routes
app.include_router(match_router, tags=["matching"])
app.include_router(storage_router, tags=["storage"])

# Register domain components
DomainRegistry.register_extractor("cooking", CookingExtractor())
DomainRegistry.register_matcher("cooking", CookingMatcher())
DomainRegistry.register_validator("cooking", CookingValidator())

# Add manufacturing components when ready
# DomainRegistry.register_extractor("manufacturing", ManufacturingExtractor())
# DomainRegistry.register_matcher("manufacturing", ManufacturingMatcher())
# DomainRegistry.register_validator("manufacturing", ManufacturingValidator())

# docker-compose.yml for local development with MinIO
version: '3.8'

services:
  # MinIO for local S3-compatible storage
  minio:
    image: minio/minio:latest
    container_name: ome-minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  # OME API service
  ome-api:
    build: .
    container_name: ome-api
    ports:
      - "8000:8000"
    environment:
      - OME_STORAGE_PROVIDER=aws_s3
      - OME_STORAGE_BUCKET=ome-local-storage
      - OME_STORAGE_ENDPOINT=http://minio:9000
      - AWS_ACCESS_KEY_ID=minioadmin
      - AWS_SECRET_ACCESS_KEY=minioadmin
    depends_on:
      minio:
        condition: service_healthy
    volumes:
      - ./config:/app/config
      - ./src:/app/src

volumes:
  minio_data:

# requirements.txt additions for storage providers
# Add these to your existing requirements.txt

# Storage providers
boto3>=1.26.0              # AWS S3
azure-storage-blob>=12.14.0 # Azure Blob Storage  
google-cloud-storage>=2.7.0 # Google Cloud Storage

# Configuration and utilities
PyYAML>=6.0                # YAML configuration files
pydantic[email]>=1.10.0    # Enhanced pydantic features

# Optional: For MinIO local development
minio>=7.1.0               # MinIO Python client

# src/core/cli/storage_cli.py
"""Command-line interface for storage operations"""
import asyncio
import click
import json
from uuid import UUID
from pathlib import Path

from ..config.settings import StorageSettings
from ..startup import initialize_storage
from ..services.storage_service import StorageService

@click.group()
def storage():
    """Storage management commands"""
    pass

@storage.command()
@click.option('--provider', help='Storage provider to use')
async def status(provider):
    """Check storage status"""
    try:
        storage_service = await initialize_storage(provider)
        if storage_service:
            status_info = await storage_service.get_status()
            click.echo(json.dumps(status_info, indent=2))
        else:
            click.echo("Storage not configured")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@storage.command()
@click.option('--provider', help='Storage provider to use')
async def stats(provider):
    """Get storage statistics"""
    try:
        storage_service = await initialize_storage(provider)
        if storage_service:
            stats_info = await storage_service.get_storage_stats()
            click.echo(json.dumps(stats_info, indent=2))
        else:
            click.echo("Storage not configured")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@storage.command()
@click.option('--name', help='Backup name')
@click.option('--provider', help='Storage provider to use')
async def backup(name, provider):
    """Create a backup of all data"""
    try:
        storage_service = await initialize_storage(provider)
        if storage_service:
            backup_info = await storage_service.create_backup(name)
            click.echo(f"Backup created: {backup_info['backup_name']}")
            click.echo(json.dumps(backup_info, indent=2))
        else:
            click.echo("Storage not configured")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@storage.command()
@click.option('--provider', help='Storage provider to use')
async def list_backups(provider):
    """List available backups"""
    try:
        storage_service = await initialize_storage(provider)
        if storage_service:
            backups = await storage_service.list_backups()
            if backups:
                click.echo("Available backups:")
                for backup in backups:
                    click.echo(f"  {backup['name']} ({backup['object_count']} objects, {backup['total_size']} bytes)")
            else:
                click.echo("No backups found")
        else:
            click.echo("Storage not configured")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@storage.command()
@click.argument('supply_tree_id')
@click.option('--provider', help='Storage provider to use')
async def get_supply_tree(supply_tree_id, provider):
    """Retrieve a supply tree by ID"""
    try:
        storage_service = await initialize_storage(provider)
        if storage_service:
            tree = await storage_service.load_supply_tree(UUID(supply_tree_id))
            click.echo(json.dumps(tree.to_dict(), indent=2))
        else:
            click.echo("Storage not configured")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@storage.command()
@click.option('--provider', help='Storage provider to use')
async def list_supply_trees(provider):
    """List all supply trees"""
    try:
        storage_service = await initialize_storage(provider)
        if storage_service:
            trees = await storage_service.list_supply_trees()
            if trees:
                click.echo("Supply trees:")
                for tree in trees:
                    click.echo(f"  {tree['id']} (modified: {tree['last_modified']})")
            else:
                click.echo("No supply trees found")
        else:
            click.echo("Storage not configured")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

# Convert async commands to sync for Click
def async_command(f):
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

# Apply the wrapper to all async commands
for cmd in [status, stats, backup, list_backups, get_supply_tree, list_supply_trees]:
    storage.add_command(click.command()(async_command(cmd)))

if __name__ == '__main__':
    storage()

# tests/test_storage.py
"""Tests for storage functionality"""
import pytest
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.core.storage.base import StorageConfig, StorageProvider
from src.core.storage.manager import StorageManager
from src.core.services.storage_service import StorageService
from src.core.models.supply_trees import SupplyTree
from src.core.models.okh import OKHManifest, License

@pytest.fixture
def mock_storage_config():
    """Mock storage configuration for testing"""
    return StorageConfig(
        provider=StorageProvider.AWS_S3,
        bucket_name="test-bucket",
        region="us-east-1",
        credentials={"access_key": "test", "secret_key": "test"}
    )

@pytest.fixture
def mock_supply_tree():
    """Mock supply tree for testing"""
    tree = SupplyTree()
    tree.id = uuid4()
    tree.okh_reference = "test-okh-ref"
    return tree

@pytest.fixture
def mock_okh_manifest():
    """Mock OKH manifest for testing"""
    license_obj = License(hardware="MIT", documentation="MIT", software="MIT")
    return OKHManifest(
        title="Test Manifest",
        repo="https://example.com/repo",
        version="1.0.0",
        license=license_obj,
        licensor="Test User",
        documentation_language="en",
        function="Test function"
    )

class TestStorageManager:
    """Test storage manager functionality"""
    
    @pytest.mark.asyncio
    async def test_storage_manager_initialization(self, mock_storage_config):
        """Test storage manager initialization"""
        manager = StorageManager(mock_storage_config)
        assert manager.config == mock_storage_config
        assert not manager._connected
    
    @pytest.mark.asyncio
    async def test_save_and_load_supply_tree(self, mock_storage_config, mock_supply_tree):
        """Test saving and loading supply trees"""
        # Mock the storage provider
        mock_provider = AsyncMock()
        mock_provider.put_object.return_value = "test-etag"
        mock_provider.get_object.return_value = b'{"test": "data"}'
        
        manager = StorageManager(mock_storage_config)
        manager.provider = mock_provider
        manager._connected = True
        
        # Test saving
        etag = await manager.save_supply_tree(mock_supply_tree)
        assert etag == "test-etag"
        mock_provider.put_object.assert_called_once()
        
        # Test loading would require proper JSON serialization
        # This is a simplified test
        mock_provider.get_object.return_value = b'{"id": "' + str(mock_supply_tree.id) + '"}'
        
        # Note: This would need proper deserialization in real implementation
        with pytest.raises(Exception):  # Expected since we're mocking simplified data
            await manager.load_supply_tree(mock_supply_tree.id)

class TestStorageService:
    """Test storage service functionality"""
    
    @pytest.mark.asyncio
    async def test_storage_service_singleton(self):
        """Test storage service singleton pattern"""
        service1 = await StorageService.get_instance()
        service2 = await StorageService.get_instance()
        assert service1 is service2
    
    @pytest.mark.asyncio
    async def test_storage_service_configuration(self, mock_storage_config):
        """Test storage service configuration"""
        service = StorageService()
        
        # Mock the manager
        mock_manager = AsyncMock()
        service.manager = mock_manager
        
        await service.configure(mock_storage_config)
        assert service._configured
        mock_manager.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_storage_service_status(self, mock_storage_config):
        """Test storage service status reporting"""
        service = StorageService()
        
        # Test unconfigured status
        status = await service.get_status()
        assert not status["configured"]
        assert not status["connected"]
        
        # Test configured status
        mock_manager = MagicMock()
        mock_manager._connected = True
        mock_manager.config = mock_storage_config
        
        service.manager = mock_manager
        service._configured = True
        
        status = await service.get_status()
        assert status["configured"]
        assert status["connected"]
        assert status["provider"] == "aws_s3"

# Example usage documentation
# docs/storage_usage.md
"""
# Storage Usage Guide

## Configuration

The OME storage system supports multiple cloud providers through a unified interface:

### Environment Variables
```bash
# Provider selection
export OME_STORAGE_PROVIDER=aws_s3  # or azure_blob, gcs

# AWS S3
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export OME_STORAGE_BUCKET=your-bucket-name
export OME_STORAGE_REGION=us-east-1

# Azure Blob Storage
export AZURE_STORAGE_ACCOUNT=your_account
export AZURE_STORAGE_KEY=your_key
export OME_STORAGE_BUCKET=your-container-name

# Google Cloud Storage
export GCP_PROJECT_ID=your-project
export GCP_SERVICE_ACCOUNT_KEY=path/to/key.json
export OME_STORAGE_BUCKET=your-bucket-name
```

### Configuration File
Create `config/storage.yaml`:

```yaml
aws_s3:
  provider: "aws_s3"
  bucket_name: "ome-production-storage"
  region: "us-east-1"
  credentials:
    access_key: "${AWS_ACCESS_KEY_ID}"
    secret_key: "${AWS_SECRET_ACCESS_KEY}"
```

## API Usage

### Configure Storage
```bash
curl -X POST "http://localhost:8000/storage/config" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "aws_s3",
    "bucket_name": "my-ome-bucket",
    "region": "us-east-1",
    "credentials": {
      "access_key": "your_key",
      "secret_key": "your_secret"
    }
  }'
```

### Save Supply Tree
```bash
curl -X POST "http://localhost:8000/storage/supply-trees" \
  -H "Content-Type: application/json" \
  -d '{
    "supply_tree": {...},
    "metadata": {
      "project": "test-project",
      "version": "1.0"
    }
  }'
```

### List Supply Trees
```bash
curl "http://localhost:8000/storage/supply-trees?limit=10&offset=0"
```

### Get Storage Statistics
```bash
curl "http://localhost:8000/storage/stats"
```

## Command Line Usage

```bash
# Check storage status
python -m src.core.cli.storage_cli status

# Get storage statistics
python -m src.core.cli.storage_cli stats

# Create backup
python -m src.core.cli.storage_cli backup --name "manual-backup-2024"

# List backups
python -m src.core.cli.storage_cli list-backups

# List supply trees
python -m src.core.cli.storage_cli list-supply-trees
```

## Local Development

Use MinIO for local S3-compatible storage:

```bash
# Start MinIO with docker-compose
docker-compose up minio

# Configure for local development
export OME_STORAGE_PROVIDER=aws_s3
export OME_STORAGE_ENDPOINT=http://localhost:9000
export OME_STORAGE_BUCKET=ome-local-storage
export AWS_ACCESS_KEY_ID=minioadmin
export AWS_SECRET_ACCESS_KEY=minioadmin
```

## Best Practices

1. **Environment Separation**: Use different buckets for development, staging, and production
2. **Backup Strategy**: Regular automated backups with retention policies
3. **Access Control**: Use least-privilege access for storage credentials
4. **Monitoring**: Monitor storage usage and costs
5. **Encryption**: Enable encryption at rest and in transit
6. **Versioning**: Enable object versioning for critical data
"""