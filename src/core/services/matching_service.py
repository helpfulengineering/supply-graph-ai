from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from ..models.okh import OKHManifest
from ..models.okw import ManufacturingFacility
from ..models.supply_trees import SupplyTree, SupplyTreeSolution
from .okh_service import OKHService
from .okw_service import OKWService
from ..registry.domain_registry import DomainRegistry
from ..utils.logging import get_logger
from ..domains.manufacturing.direct_matcher import MfgDirectMatcher
from ..domains.cooking.direct_matcher import CookingDirectMatcher
from ..matching.capability_rules import CapabilityRuleManager, CapabilityMatcher
from ..models.supply_trees import Workflow, WorkflowNode, ResourceURI, ResourceType

logger = get_logger(__name__)

class MatchingService:
    """Service for matching OKH requirements to OKW capabilities"""
    
    _instance = None
    
    def __init__(self):
        """Initialize the matching service with Direct Matching layers"""
        self._initialized = False
        self.direct_matchers = {
            "manufacturing": MfgDirectMatcher(),
            "cooking": CookingDirectMatcher()
        }
        self.capability_rule_manager = None
        self.capability_matcher = None
        self.okh_service: Optional[OKHService] = None
        self.okw_service: Optional[OKWService] = None
    
    # Heuristic rules are now managed by the HeuristicRuleManager
    # and loaded from domain-specific configuration files
    
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
    
    async def initialize(
        self,
        okh_service: Optional[OKHService] = None,
        okw_service: Optional[OKWService] = None
    ) -> None:
        """Initialize the matching service with all required components"""
        if self._initialized:
            return
            
        self.okh_service = okh_service
        self.okw_service = okw_service
        
        # Initialize capability-centric heuristic matching
        self.capability_rule_manager = CapabilityRuleManager()
        await self.capability_rule_manager.initialize()
        self.capability_matcher = CapabilityMatcher(self.capability_rule_manager)
        
        self._initialized = True
        logger.info("MatchingService initialized with Direct Matching and Capability-Centric Heuristic Matching")
    
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
            # Detect domain from the inputs
            # For now, we know this is manufacturing domain from OKH/OKW
            # In the future, this could be more dynamic
            domain = "manufacturing"
            
            # Get the domain services
            domain_services = DomainRegistry.get_domain_services(domain)
            extractor = domain_services.extractor
            
            # Extract requirements using the domain extractor
            manifest_data = okh_manifest.to_dict()
            extraction_result = extractor.extract_requirements(manifest_data)
            requirements = extraction_result.data.content.get('process_requirements', []) if extraction_result.data else []
            
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
                
                if await self._can_satisfy_requirements(requirements, capabilities):
                    tree = await self._generate_supply_tree(okh_manifest, facility, domain)
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
    
    async def _can_satisfy_requirements(
        self,
        requirements: List[Dict[str, Any]],
        capabilities: List[Dict[str, Any]]
    ) -> bool:
        """Check if capabilities can satisfy requirements using multi-layered matching"""
        try:
            for req in requirements:
                req_process = req.get("process_name", "").lower().strip()
                if not req_process:
                    continue
                    
                for cap in capabilities:
                    cap_process = cap.get("process_name", "").lower().strip()
                    if not cap_process:
                        continue
                    
                    # Normalize process names for better matching
                    # This handles Wikipedia URLs and other format differences
                    req_normalized = self._normalize_process_name(req_process)
                    cap_normalized = self._normalize_process_name(cap_process)
                    
                    # Layer 1: Direct Matching (using new Direct Matching layer)
                    if await self._direct_match(req_normalized, cap_normalized, domain="manufacturing"):
                        logger.debug(
                            "Direct match found",
                            extra={
                                "requirement": req.get("process_name"),
                                "capability": cap.get("process_name"),
                                "requirement_normalized": req_normalized,
                                "capability_normalized": cap_normalized,
                                "layer": "direct"
                            }
                        )
                        return True
                    
                    # Layer 2: Heuristic Matching (using new HeuristicRuleManager)
                    if await self._heuristic_match(req_normalized, cap_normalized, domain="manufacturing"):
                        logger.debug(
                            "Heuristic match found",
                            extra={
                                "requirement": req.get("process_name"),
                                "capability": cap.get("process_name"),
                                "layer": "heuristic"
                            }
                        )
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
    
    async def _direct_match(self, req_process: str, cap_process: str, domain: str = "manufacturing") -> bool:
        """Layer 1: Direct Matching - Using the new Direct Matching layer with metadata tracking"""
        try:
            # Get the appropriate direct matcher for the domain
            direct_matcher = self.direct_matchers.get(domain)
            if not direct_matcher:
                logger.warning(f"No direct matcher available for domain: {domain}, falling back to simple matching")
                return req_process.lower() == cap_process.lower()
            
            # Use the domain-specific matcher's process matching method
            # The domain matchers have specific methods for different types of matching
            if hasattr(direct_matcher, 'match_processes'):
                # Use the process matching method (now async)
                import asyncio
                results = await direct_matcher.match_processes([req_process], [cap_process])
                
                # Check if we have any matches
                for result in results:
                    if result.matched and result.confidence >= 0.8:  # Use 0.8 as threshold for "match"
                        logger.debug(
                            "Direct match found using Direct Matching layer",
                            extra={
                                "requirement": req_process,
                                "capability": cap_process,
                                "confidence": result.confidence,
                                "quality": result.metadata.quality,
                                "method": result.metadata.method
                            }
                        )
                        return True
            else:
                # Fallback to simple string matching if no process matcher available
                logger.warning(f"Domain matcher {domain} does not have match_processes method, using simple matching")
                return req_process.lower() == cap_process.lower()
            
            return False
            
        except Exception as e:
            logger.error(f"Error in Direct Matching layer: {e}", exc_info=True)
            # Fallback to simple matching
            return req_process.lower() == cap_process.lower()
    
    async def _heuristic_match(self, req_process: str, cap_process: str, domain: str = "manufacturing") -> bool:
        """Layer 2: Heuristic Matching - Using the new capability-centric heuristic rules system"""
        try:
            # Use the capability-centric heuristic matcher
            if not self.capability_matcher:
                logger.warning("Capability matcher not initialized, skipping heuristic matching")
                return False
            
            # Create requirement and capability objects for matching
            requirements = [{"process_name": req_process}]
            capabilities = [{"process_name": cap_process}]
            
            # Use the capability-centric matcher
            results = await self.capability_matcher.match_requirements_to_capabilities(
                requirements=requirements,
                capabilities=capabilities,
                domain=domain,
                requirement_field="process_name",
                capability_field="process_name"
            )
            
            # Check if we have any matches
            for result in results:
                if result.matched and result.confidence >= 0.7:  # Use 0.7 as threshold for heuristic match
                    logger.debug(
                        "Heuristic match found using capability-centric rules",
                        extra={
                            "requirement": req_process,
                            "capability": cap_process,
                            "confidence": result.confidence,
                            "rule_used": result.rule_used.id if result.rule_used else None,
                            "domain": result.domain
                        }
                    )
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in Heuristic Matching layer: {e}", exc_info=True)
            return False
    
    async def _generate_supply_tree(
        self,
        manifest: OKHManifest,
        facility: ManufacturingFacility,
        domain: str = "manufacturing"
    ) -> SupplyTree:
        """Generate a supply tree for a manifest and facility using enhanced matching layers"""
        try:
            # Create a supply tree with proper metadata
            supply_tree = SupplyTree()
            
            # Set comprehensive metadata with fallback for empty facility names
            facility_name = facility.name or f"Facility {str(facility.id)[:8]}"
            supply_tree.metadata = {
                "name": f"{manifest.title} - {facility_name}",
                "description": f"Manufacturing solution for {manifest.title} at {facility_name}",
                "okh_id": str(manifest.id),
                "facility_id": str(facility.id),
                "okh_title": manifest.title,
                "facility_name": facility_name,
                "generation_method": "enhanced_multi_layered_matching",
                "matching_layers_used": ["direct", "heuristic"],
                "domain": domain,
                "created_at": datetime.now().isoformat()
            }
            
            # Set OKH reference
            supply_tree.okh_reference = str(manifest.id)
            # Lazy import NetworkX
            import networkx as nx
            
            primary_workflow = Workflow(
                name=f"Manufacturing Workflow for {manifest.title}",
                graph=nx.DiGraph(),
                entry_points=set(),
                exit_points=set()
            )
            
            # Extract process requirements from the manifest
            process_requirements = manifest.manufacturing_processes or []
            
            # Create nodes for each manufacturing process using enhanced matching
            previous_node_id = None
            matching_results = []
            
            for i, process_name in enumerate(process_requirements):
                # Find matching capabilities in the facility using our enhanced matching layers
                facility_capabilities = []
                for equipment in facility.equipment:
                    if hasattr(equipment, 'manufacturing_process'):
                        facility_capabilities.extend(equipment.manufacturing_process)
                    if hasattr(equipment, 'manufacturing_processes'):
                        facility_capabilities.extend(equipment.manufacturing_processes)
                
                # Use our enhanced matching layers to find the best match
                best_match_confidence = 0.0
                best_match_method = "no_match"
                best_match_capability = None
                matching_details = {}
                
                for capability in facility_capabilities:
                    # Layer 1: Direct Matching
                    if self._direct_match(process_name, capability, domain):
                        direct_matcher = self.direct_matchers.get(domain)
                        if direct_matcher:
                            direct_results = direct_matcher.match(process_name, [capability], near_miss_threshold=2)
                            for result in direct_results:
                                if result.matched and result.confidence > best_match_confidence:
                                    best_match_confidence = result.confidence
                                    best_match_method = f"direct_{result.metadata.method}"
                                    best_match_capability = capability
                                    matching_details = {
                                        "quality": result.metadata.quality,
                                        "character_difference": result.metadata.character_difference,
                                        "case_difference": result.metadata.case_difference,
                                        "whitespace_difference": result.metadata.whitespace_difference
                                    }
                    
                    # Layer 2: Heuristic Matching (only if direct matching didn't find a good match)
                    if best_match_confidence < 0.8 and await self._heuristic_match(process_name, capability, domain):
                        if self.capability_matcher:
                            heuristic_results = await self.capability_matcher.match_requirements_to_capabilities(
                                requirements=[{"process_name": process_name}],
                                capabilities=[{"process_name": capability}],
                                domain=domain,
                                requirement_field="process_name",
                                capability_field="process_name"
                            )
                            for result in heuristic_results:
                                if result.matched and result.confidence > best_match_confidence:
                                    best_match_confidence = result.confidence
                                    best_match_method = f"heuristic_{result.rule_used.id if result.rule_used else 'rule'}"
                                    best_match_capability = capability
                                    matching_details = {
                                        "rule_used": result.rule_used.id if result.rule_used else None,
                                        "transformation_details": result.transformation_details
                                    }
                
                # Create a workflow node for this process with enhanced matching information
                node_id = uuid4()
                node = WorkflowNode(
                    id=node_id,
                    name=f"{process_name} Process",
                    okh_refs=[
                        ResourceURI(
                            resource_type=ResourceType.OKH_PROCESS,
                            identifier=str(manifest.id),
                            path=["manufacturing_processes", str(i)]
                        )
                    ],
                    okw_refs=[
                        ResourceURI(
                            resource_type=ResourceType.OKW_PROCESS,
                            identifier=str(facility.id),
                            path=["manufacturing_processes", best_match_capability.lower().replace(" ", "_") if best_match_capability else process_name.lower().replace(" ", "_")]
                        )
                    ],
                    input_requirements={
                        "process": process_name,
                        "material": "as_specified_in_okh"
                    },
                    output_specifications={
                        "process": process_name,
                        "quality": "meets_okh_requirements"
                    },
                    estimated_time=timedelta(hours=2),  # Default estimation
                    assigned_facility=str(facility.id),
                    confidence_score=best_match_confidence,
                    substitution_used=best_match_method.startswith("heuristic_"),
                    metadata={
                        "process_index": i,
                        "total_processes": len(process_requirements),
                        "matching_method": best_match_method,
                        "matched_capability": best_match_capability,
                        "matching_details": matching_details,
                        "facility_capability": "verified" if best_match_confidence > 0.7 else "uncertain"
                    }
                )
                
                # Store matching result for overall confidence calculation
                matching_results.append({
                    "process": process_name,
                    "confidence": best_match_confidence,
                    "method": best_match_method
                })
                
                # Add node to workflow
                primary_workflow.graph.add_node(node_id, data=node)
                
                # Create linear workflow (each process depends on the previous one)
                if previous_node_id is not None:
                    primary_workflow.graph.add_edge(previous_node_id, node_id)
                else:
                    # First node is an entry point
                    primary_workflow.entry_points.add(node_id)
                
                # Update exit points
                primary_workflow.exit_points.discard(previous_node_id) if previous_node_id else None
                primary_workflow.exit_points.add(node_id)
                
                previous_node_id = node_id
            
            # Add the workflow to the supply tree
            supply_tree.add_workflow(primary_workflow)
            
            # Add enhanced metadata about matching results
            supply_tree.metadata.update({
                "matching_summary": {
                    "total_processes": len(process_requirements),
                    "matching_results": matching_results,
                    "average_confidence": sum(r["confidence"] for r in matching_results) / len(matching_results) if matching_results else 0.0,
                    "direct_matches": len([r for r in matching_results if r["method"].startswith("direct_")]),
                    "heuristic_matches": len([r for r in matching_results if r["method"].startswith("heuristic_")]),
                    "no_matches": len([r for r in matching_results if r["method"] == "no_match"])
                }
            })
            
            # Add snapshots of source data
            supply_tree.add_snapshot(
                f"okh://{manifest.id}",
                manifest.to_dict()
            )
            supply_tree.add_snapshot(
                f"okw://{facility.id}",
                facility.to_dict()
            )
            
            logger.info(
                "Generated supply tree with workflows and nodes",
                extra={
                    "okh_id": str(manifest.id),
                    "facility_id": str(facility.id),
                    "workflow_count": len(supply_tree.workflows),
                    "total_nodes": sum(len(wf.graph.nodes) for wf in supply_tree.workflows.values()),
                    "process_count": len(process_requirements)
                }
            )
            
            return supply_tree
            
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
    
    def _normalize_process_name(self, process_name: str) -> str:
        """
        Normalize process names for better matching.
        
        This method handles:
        - Wikipedia URLs: Extracts the process name from URLs
        - Case normalization: Converts to lowercase
        - Whitespace normalization: Removes extra whitespace
        - Special character handling: Normalizes underscores, hyphens, etc.
        
        Args:
            process_name: The process name to normalize
            
        Returns:
            Normalized process name
        """
        if not process_name:
            return ""
        
        # Handle Wikipedia URLs
        if "wikipedia.org/wiki/" in process_name.lower():
            # Extract the process name from Wikipedia URL
            # e.g., "https://en.wikipedia.org/wiki/PCB_assembly" -> "PCB_assembly"
            parts = process_name.split("/wiki/")
            if len(parts) > 1:
                process_name = parts[1]
        
        # Normalize case and whitespace
        normalized = process_name.strip().lower()
        
        # Normalize special characters
        # Replace underscores and hyphens with spaces for better matching
        import re
        normalized = re.sub(r'[_\-]+', ' ', normalized)
        
        # Normalize multiple spaces to single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()
    
    async def ensure_initialized(self) -> None:
        """Ensure service is initialized"""
        if not self._initialized:
            raise RuntimeError("Matching service not initialized")