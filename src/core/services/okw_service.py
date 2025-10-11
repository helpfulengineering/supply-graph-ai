from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import logging
import json

from src.core.services.storage_service import StorageService
from ..models.okw import ManufacturingFacility
from ..utils.logging import get_logger

logger = get_logger(__name__)

class OKWService:
    """Service for managing OKW manufacturing facilities"""
    
    _instance = None
    
    @classmethod
    async def get_instance(cls, storage_service: Optional[StorageService] = None) -> 'OKWService':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance.initialize(storage_service)
        return cls._instance
    
    def __init__(self):
        """Initialize the OKW service"""
        self.storage: Optional[StorageService] = None
        self._initialized = False
    
    async def initialize(self, storage_service: Optional[StorageService] = None) -> None:
        """Initialize the service with dependencies"""
        if self._initialized:
            return
            
        self.storage = storage_service or await StorageService.get_instance()
        self._initialized = True
        logger.info("OKW service initialized")
    
    async def create(self, facility_data: Dict[str, Any]) -> ManufacturingFacility:
        """Create a new manufacturing facility"""
        await self.ensure_initialized()
        logger.info("Creating new manufacturing facility")
        
        # Create facility object
        facility = ManufacturingFacility.from_dict(facility_data)
        
        # Store in storage with proper naming convention
        if self.storage:
            # Generate filename based on facility name and ID (similar to synthetic data)
            safe_name = "".join(c for c in facility.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '-').lower()
            filename = f"{safe_name}-{str(facility.id)[:8]}-okw.json"
            
            # Save directly to storage root
            facility_json = json.dumps(facility.to_dict(), indent=2, ensure_ascii=False, default=str)
            await self.storage.manager.put_object(filename, facility_json.encode('utf-8'))
            logger.info(f"Saved OKW facility to {filename}")
        
        return facility
    
    async def get(self, facility_id: UUID) -> Optional[ManufacturingFacility]:
        """Get a manufacturing facility by ID"""
        await self.ensure_initialized()
        logger.info(f"Getting manufacturing facility with ID {facility_id}")
        
        if self.storage:
            # Search through all OKW files to find the one with matching ID
            async for obj in self.storage.manager.list_objects():
                if obj["key"].endswith("-okw.json"):
                    try:
                        data = await self.storage.manager.get_object(obj["key"])
                        content = data.decode('utf-8')
                        okw_data = json.loads(content)
                        facility = ManufacturingFacility.from_dict(okw_data)
                        if facility.id == facility_id:
                            return facility
                    except Exception as e:
                        logger.error(f"Failed to load OKW file {obj['key']}: {e}")
                        continue
        
        return None
    
    async def list(
        self, 
        page: int = 1, 
        page_size: int = 100,
        filter_params: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[ManufacturingFacility], int]:
        """List manufacturing facilities"""
        await self.ensure_initialized()
        logger.info(f"Listing manufacturing facilities (page={page}, page_size={page_size})")
        
        if self.storage:
            # For now, load OKW files directly from storage root (they have -okw.json suffix)
            objects = []
            total_count = 0
            
            async for obj in self.storage.manager.list_objects():
                if obj["key"].endswith("-okw.json"):
                    total_count += 1
                    if len(objects) < page_size and len(objects) >= (page - 1) * page_size:
                        try:
                            data = await self.storage.manager.get_object(obj["key"])
                            content = data.decode('utf-8')
                            okw_data = json.loads(content)
                            objects.append(ManufacturingFacility.from_dict(okw_data))
                        except Exception as e:
                            logger.error(f"Failed to load OKW file {obj['key']}: {e}")
                            continue
            
            return objects, total_count
        
        return [], 0
    
    async def update(self, facility_id: UUID, facility_data: Dict[str, Any]) -> ManufacturingFacility:
        """Update a manufacturing facility"""
        await self.ensure_initialized()
        logger.info(f"Updating manufacturing facility with ID {facility_id}")
        
        # Create facility object
        facility = ManufacturingFacility.from_dict(facility_data)
        
        # Update in storage
        if self.storage:
            handler = await self.storage.get_domain_handler("okw")
            await handler.save_object(facility_id, facility.to_dict())
        
        return facility
    
    async def delete(self, facility_id: UUID) -> bool:
        """Delete a manufacturing facility"""
        await self.ensure_initialized()
        logger.info(f"Deleting manufacturing facility with ID {facility_id}")
        
        if self.storage:
            handler = await self.storage.get_domain_handler("okw")
            return await handler.delete_object(facility_id)
        
        return True
    
    async def ensure_initialized(self) -> None:
        """Ensure service is initialized"""
        if not self._initialized:
            raise RuntimeError("OKW service not initialized")
