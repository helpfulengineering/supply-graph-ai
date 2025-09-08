from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import logging

from ..models.okh import OKHManifest
from ..models.okw import ManufacturingFacility
from ..models.supply_trees import SupplyTree, SupplyTreeSolution
from .okh_service import OKHService
from .okw_service import OKWService
from ..registry.domain_registry import DomainRegistry
from ..utils.logging import get_logger

logger = get_logger(__name__)

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
    
    async def find_matches(
        self,
        okh_id: UUID,
        optimization_criteria: Optional[Dict[str, float]] = None
    ) -> List[SupplyTreeSolution]:
        """Find matching facilities for an OKH manifest by ID (loads manifest and facilities, then delegates)."""
        await self.ensure_initialized()
        logger.info(
            "Finding matches for OKH manifest",
            extra={
                "okh_id": str(okh_id),
                "optimization_criteria": optimization_criteria
            }
        )
        try:
            # Load manifest and facilities using services
            manifest = await self.okh_service.get(okh_id)
            if not manifest:
                logger.warning("OKH manifest not found", extra={"okh_id": str(okh_id)})
                return []
            facilities, total = await self.okw_service.list()
            logger.info(
                "Retrieved manufacturing facilities",
                extra={"facility_count": len(facilities), "total_facilities": total}
            )
            # Delegate to the core logic
            return await self.find_matches_with_manifest(
                okh_manifest=manifest,
                facilities=facilities,
                optimization_criteria=optimization_criteria
            )
        except Exception as e:
            logger.error(
                "Error finding matches",
                extra={"okh_id": str(okh_id), "error": str(e)},
                exc_info=True
            )
            raise
    
    async def find_matches_with_manifest(
        self,
        okh_manifest: OKHManifest,
        facilities: List[ManufacturingFacility],
        optimization_criteria: Optional[Dict[str, float]] = None
    ) -> List[SupplyTreeSolution]:
        """Find matching facilities for an in-memory OKH manifest and provided facilities."""
        await self.ensure_initialized()

        logger.info(
            "Finding matches for in-memory OKH manifest",
            extra={
                "manifest_id": str(getattr(okh_manifest, 'id', None)),
                "optimization_criteria": optimization_criteria
            }
        )

        try:
            # Get the manufacturing domain extractor
            extractor = DomainRegistry.get_extractor("manufacturing")
            
            # Extract requirements using the domain extractor
            manifest_data = okh_manifest.to_dict()
            extraction_result = extractor.extract_requirements(manifest_data)
            requirements = extraction_result.data.content.get('requirements', []) if extraction_result.data else []
            
            logger.info(
                "Extracted requirements from OKH manifest",
                extra={
                    "requirement_count": len(requirements)
                }
            )

            solutions = []
            
            for facility in facilities:
                logger.debug(
                    "Checking facility for matches",
                    extra={
                        "facility_id": str(facility.id),
                        "facility_name": facility.name
                    }
                )
                # Extract capabilities using the domain extractor
                facility_data = facility.to_dict()
                extraction_result = extractor.extract_capabilities(facility_data)
                capabilities = extraction_result.data.content.get('capabilities', []) if extraction_result.data else []
                
                if self._can_satisfy_requirements(requirements, capabilities):
                    tree = self._generate_supply_tree(okh_manifest, facility)
                    score = self._calculate_confidence_score(
                        requirements,
                        capabilities,
                        optimization_criteria
                    )
                    solution = SupplyTreeSolution(
                        tree=tree,
                        score=score,
                        metrics={
                            "facility_count": 1,
                            "requirement_count": len(requirements),
                            "capability_count": len(capabilities)
                        }
                    )
                    solutions.append(solution)
                    logger.info(
                        "Found matching facility",
                        extra={
                            "facility_id": str(facility.id),
                            "confidence_score": score
                        }
                    )
            logger.info(
                "Match finding completed",
                extra={
                    "solution_count": len(solutions)
                }
            )
            return solutions

        except Exception as e:
            logger.error(
                "Error finding matches (in-memory manifest)",
                extra={
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    def _can_satisfy_requirements(
        self,
        requirements: List[Dict[str, Any]],
        capabilities: List[Dict[str, Any]]
    ) -> bool:
        """Check if capabilities can satisfy requirements"""
        try:
            # TODO: Implement actual matching logic
            # For now, return True if any capability matches any requirement
            for req in requirements:
                for cap in capabilities:
                    if req["process_name"] == cap["process_name"]:
                        return True
            return False
            
        except Exception as e:
            logger.error(
                "Error checking requirement satisfaction",
                extra={
                    "requirement_count": len(requirements),
                    "capability_count": len(capabilities),
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    def _generate_supply_tree(
        self,
        manifest: OKHManifest,
        facility: ManufacturingFacility
    ) -> SupplyTree:
        """Generate a supply tree for a manifest and facility"""
        try:
            # TODO: Implement actual tree generation logic
            # For now, return a simple tree
            return SupplyTree(
                root_node={
                    "type": "facility",
                    "id": str(facility.id),
                    "name": facility.name
                },
                edges=[],
                metadata={
                    "okh_id": str(manifest.id),
                    "facility_id": str(facility.id)
                }
            )
            
        except Exception as e:
            logger.error(
                "Error generating supply tree",
                extra={
                    "okh_id": str(manifest.id),
                    "facility_id": str(facility.id),
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    def _calculate_confidence_score(
        self,
        requirements: List[Dict[str, Any]],
        capabilities: List[Dict[str, Any]],
        optimization_criteria: Optional[Dict[str, float]] = None
    ) -> float:
        """Calculate confidence score for a match"""
        try:
            # TODO: Implement actual scoring logic
            # For now, return a simple score based on requirement coverage
            matched_requirements = sum(
                1 for req in requirements
                if any(req["process_name"] == cap["process_name"] for cap in capabilities)
            )
            return matched_requirements / len(requirements) if requirements else 0.0
            
        except Exception as e:
            logger.error(
                "Error calculating confidence score",
                extra={
                    "requirement_count": len(requirements),
                    "capability_count": len(capabilities),
                    "optimization_criteria": optimization_criteria,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    async def ensure_initialized(self) -> None:
        """Ensure service is initialized"""
        if not self._initialized:
            raise RuntimeError("Matching service not initialized")