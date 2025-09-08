from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import logging
import httpx
import yaml
import json

from src.core.services.storage_service import StorageService
from ..models.okh import OKHManifest, ProcessRequirement
from ..utils.logging import get_logger

logger = get_logger(__name__)

class OKHService:
    """Service for managing OKH manifests"""
    
    _instance = None
    
    @classmethod
    async def get_instance(cls, storage_service: Optional[StorageService] = None) -> 'OKHService':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance.initialize(storage_service)
        return cls._instance
    
    def __init__(self):
        """Initialize the OKH service"""
        self.storage: Optional[StorageService] = None
        self._initialized = False
    
    async def initialize(self, storage_service: Optional[StorageService] = None) -> None:
        """Initialize the service with dependencies"""
        if self._initialized:
            return
            
        self.storage = storage_service or await StorageService.get_instance()
        self._initialized = True
        logger.info("OKH service initialized")
    
    async def create(self, manifest_data: Dict[str, Any]) -> OKHManifest:
        """Create a new OKH manifest"""
        await self.ensure_initialized()
        logger.info("Creating new OKH manifest")
        
        # Create manifest object
        manifest = OKHManifest.from_dict(manifest_data)
        
        # Store in storage
        if self.storage:
            handler = await self.storage.get_domain_handler("okh")
            await handler.save_object(manifest.id, manifest.to_dict())
        
        return manifest
    
    async def get(self, manifest_id: UUID) -> Optional[OKHManifest]:
        """Get an OKH manifest by ID"""
        await self.ensure_initialized()
        logger.info(f"Getting OKH manifest with ID {manifest_id}")
        
        if self.storage:
            handler = await self.storage.get_domain_handler("okh")
            data = await handler.load_object(manifest_id)
            if data:
                return OKHManifest.from_dict(data)
        
        return None
    
    async def fetch_from_url(self, url: str) -> OKHManifest:
        """Fetch an OKH manifest from a remote URL"""
        await self.ensure_initialized()
        logger.info(f"Fetching OKH manifest from URL: {url}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Try to parse as YAML first, then JSON
                content = response.text
                try:
                    if url.endswith('.yaml') or url.endswith('.yml') or 'yaml' in response.headers.get('content-type', ''):
                        data = yaml.safe_load(content)
                    else:
                        data = json.loads(content)
                except (yaml.YAMLError, json.JSONDecodeError) as e:
                    logger.error(f"Failed to parse manifest content: {e}")
                    raise ValueError(f"Invalid manifest format: {e}")
                
                # Create manifest object
                manifest = OKHManifest.from_dict(data)
                logger.info(f"Successfully fetched OKH manifest: {manifest.id}")
                return manifest
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching manifest from {url}: {e}")
            raise ValueError(f"Failed to fetch manifest from URL: {e}")
        except Exception as e:
            logger.error(f"Error fetching manifest from {url}: {e}")
            raise ValueError(f"Error fetching manifest: {e}")
    
    async def list(
        self, 
        page: int = 1, 
        page_size: int = 100,
        filter_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[OKHManifest], int]:
        """List OKH manifests"""
        await self.ensure_initialized()
        logger.info(f"Listing OKH manifests (page={page}, page_size={page_size})")
        
        if self.storage:
            handler = await self.storage.get_domain_handler("okh")
            objects, total = await handler.list_objects(
                limit=page_size,
                offset=(page - 1) * page_size
            )
            return [OKHManifest.from_dict(obj) for obj in objects], total
        
        return [], 0
    
    async def update(self, manifest_id: UUID, manifest_data: Dict[str, Any]) -> OKHManifest:
        """Update an OKH manifest"""
        await self.ensure_initialized()
        logger.info(f"Updating OKH manifest with ID {manifest_id}")
        
        # Create manifest object
        manifest = OKHManifest.from_dict(manifest_data)
        
        # Update in storage
        if self.storage:
            handler = await self.storage.get_domain_handler("okh")
            await handler.save_object(manifest_id, manifest.to_dict())
        
        return manifest
    
    async def delete(self, manifest_id: UUID) -> bool:
        """Delete an OKH manifest"""
        await self.ensure_initialized()
        logger.info(f"Deleting OKH manifest with ID {manifest_id}")
        
        if self.storage:
            handler = await self.storage.get_domain_handler("okh")
            return await handler.delete_object(manifest_id)
        
        return True
    
    async def extract_requirements(self, manifest_id: UUID) -> List[ProcessRequirement]:
        """Extract manufacturing requirements from an OKH manifest"""
        await self.ensure_initialized()
        logger.info(f"Extracting requirements from OKH manifest {manifest_id}")
        
        manifest = await self.get(manifest_id)
        if not manifest:
            return []
            
        return manifest.extract_requirements()
    
    async def ensure_initialized(self) -> None:
        """Ensure service is initialized"""
        if not self._initialized:
            raise RuntimeError("OKH service not initialized")