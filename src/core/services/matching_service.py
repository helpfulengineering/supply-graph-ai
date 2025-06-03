from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import logging

from ..models.okh import OKHManifest
from ..models.okw import ManufacturingFacility
from ..models.supply_trees import SupplyTree, SupplyTreeSolution
from .okh_service import OKHService
from .okw_service import OKWService

logger = logging.getLogger(__name__)

class MatchingService:
    """Service for matching OKH requirements to OKW capabilities"""
    
    _instance = None
    
    @classmethod
    async def get_instance(
        cls,
        okh_service: Optional[OKHService] = None,
        okw_service: Optional[OKWService] = None
    ) -> 'MatchingService':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance.initialize(okh_service, okw_service)
        return cls._instance
    
    def __init__(self):
        """Initialize the matching service"""
        self.okh_service: Optional[OKHService] = None
        self.okw_service: Optional[OKWService] = None
        self._initialized = False
    
    async def initialize(
        self,
        okh_service: Optional[OKHService] = None,
        okw_service: Optional[OKWService] = None
    ) -> None:
        """Initialize the service with dependencies"""
        if self._initialized:
            return
            
        self.okh_service = okh_service or await OKHService.get_instance()
        self.okw_service = okw_service or await OKWService.get_instance()
        self._initialized = True
        logger.info("Matching service initialized")
    
    async def find_matches(self, okh_id: UUID) -> List[SupplyTreeSolution]:
        """Find matching facilities for an OKH manifest"""
        await self.ensure_initialized()
        logger.info(f"Finding matches for OKH manifest {okh_id}")
        
        # Get OKH manifest
        manifest = await self.okh_service.get(okh_id)
        if not manifest:
            logger.error(f"OKH manifest {okh_id} not found")
            return []
        
        # Get all facilities
        facilities, _ = await self.okw_service.list()
        if not facilities:
            logger.warning("No facilities found")
            return []
        
        # Generate supply tree
        supply_tree = SupplyTree.generate_from_requirements(manifest, facilities)
        
        # Calculate confidence score
        confidence = supply_tree.calculate_confidence()
        
        # Create solution
        solution = SupplyTreeSolution(
            tree=supply_tree,
            score=confidence,
            metrics={
                "facility_count": len(facilities),
                "process_count": len(manifest.extract_requirements()),
                "confidence": confidence
            }
        )
        
        return [solution]
    
    async def ensure_initialized(self) -> None:
        """Ensure service is initialized"""
        if not self._initialized:
            raise RuntimeError("Matching service not initialized")