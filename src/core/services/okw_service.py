from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import logging

from src.core.services.storage_service import StorageService
from ..models.okw import ManufacturingFacility

logger = logging.getLogger(__name__)

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
        
        # Store in storage
        if self.storage:
            handler = await self.storage.get_domain_handler("okw")
            await handler.save_object(facility.id, facility.to_dict())
        
        return facility
    
    async def get(self, facility_id: UUID) -> Optional[ManufacturingFacility]:
        """Get a manufacturing facility by ID"""
        await self.ensure_initialized()
        logger.info(f"Getting manufacturing facility with ID {facility_id}")
        
        if self.storage:
            handler = await self.storage.get_domain_handler("okw")
            data = await handler.load_object(facility_id)
            if data:
                return ManufacturingFacility.from_dict(data)
        
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
            handler = await self.storage.get_domain_handler("okw")
            objects, total = await handler.list_objects(
                limit=page_size,
                offset=(page - 1) * page_size
            )
            return [ManufacturingFacility.from_dict(obj) for obj in objects], total
        
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
