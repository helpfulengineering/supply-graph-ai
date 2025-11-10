from typing import Dict, List, Optional, Any, Set
from uuid import UUID

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
from ..matching.nlp_matcher import NLPMatcher

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
        self.nlp_matchers = {
            "manufacturing": NLPMatcher(domain="manufacturing"),
            "cooking": NLPMatcher(domain="cooking")
        }
        self.okh_service: Optional[OKHService] = None
        self.okw_service: Optional[OKWService] = None
    
    
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
        
        # Ensure domains are registered (for fallback mode)
        await self._ensure_domains_registered()
        
        # Initialize capability-centric heuristic matching
        self.capability_rule_manager = CapabilityRuleManager()
        await self.capability_rule_manager.initialize()
        self.capability_matcher = CapabilityMatcher(self.capability_rule_manager)
        
        # Pre-initialize NLP matchers to avoid lazy loading delays during matching
        logger.info("Pre-initializing NLP matchers...")
        for domain, nlp_matcher in self.nlp_matchers.items():
            try:
                # Force initialization of spaCy models
                nlp_matcher._ensure_nlp_initialized()
                logger.info(f"NLP matcher for domain '{domain}' initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize NLP matcher for domain '{domain}': {e}")
        
        self._initialized = True
        logger.info("MatchingService initialized with Direct Matching, Capability-Centric Heuristic Matching, and NLP Matching")
    
    async def find_matches(
        self,
        okh_id: UUID,
        optimization_criteria: Optional[Dict[str, float]] = None
    ) -> Set[SupplyTreeSolution]:
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
    ) -> Set[SupplyTreeSolution]:
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

            solutions = set()
            
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
                
                if await self._can_satisfy_requirements(requirements, capabilities, domain):
                    tree = await self._generate_supply_tree(okh_manifest, facility, domain)
                    # Use the same confidence score from the tree to avoid duplication
                    solution = SupplyTreeSolution(
                        tree=tree,
                        score=tree.confidence_score,  # Use tree's confidence score
                        metrics={
                            "facility_count": 1,
                            "requirement_count": len(requirements),
                            "capability_count": len(capabilities)
                        }
                    )
                    solutions.add(solution)
                    logger.info(
                        "Found matching facility",
                        extra={
                            "facility_id": str(facility.id),
                            "confidence_score": tree.confidence_score
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
        capabilities: List[Dict[str, Any]],
        domain: str = "manufacturing"
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
                    
                    # Try Layer 1: Direct Matching first
                    if await self._direct_match(req_process, cap_process, domain):
                        logger.debug(
                            "Direct match found",
                            extra={
                                "requirement": req.get("process_name"),
                                "capability": cap.get("process_name"),
                                "layer": "direct"
                            }
                        )
                        return True
                    
                    # Try Layer 2: Heuristic Matching
                    if await self._heuristic_match(req_process, cap_process, domain):
                        logger.debug(
                            "Heuristic match found",
                            extra={
                                "requirement": req.get("process_name"),
                                "capability": cap.get("process_name"),
                                "layer": "heuristic"
                            }
                        )
                        return True
                    
                    # Try Layer 3: NLP Matching
                    if await self._nlp_match(req_process, cap_process, domain):
                        logger.debug(
                            "NLP match found",
                            extra={
                                "requirement": req.get("process_name"),
                                "capability": cap.get("process_name"),
                                "layer": "nlp"
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
                    "domain": domain,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    async def _direct_match(self, req_process: str, cap_process: str, domain: str = "manufacturing") -> bool:
        """Layer 1: Direct Matching - Exact and near-exact string matching with normalization"""
        try:
            # Normalize both process names for better matching
            req_normalized = self._normalize_process_name(req_process)
            cap_normalized = self._normalize_process_name(cap_process)
            
            # Check for exact match after normalization
            if req_normalized == cap_normalized:
                logger.debug(
                    "Direct exact match found",
                    extra={
                        "requirement": req_process,
                        "capability": cap_process,
                        "requirement_normalized": req_normalized,
                        "capability_normalized": cap_normalized,
                        "layer": "direct"
                    }
                )
                return True
            
            # Check for case-insensitive exact match
            if req_process.lower().strip() == cap_process.lower().strip():
                logger.debug(
                    "Direct case-insensitive match found",
                    extra={
                        "requirement": req_process,
                        "capability": cap_process,
                        "layer": "direct"
                    }
                )
                return True
            
            # Check for substring matches (one contains the other)
            if req_normalized in cap_normalized or cap_normalized in req_normalized:
                logger.debug(
                    "Direct substring match found",
                    extra={
                        "requirement": req_process,
                        "capability": cap_process,
                        "requirement_normalized": req_normalized,
                        "capability_normalized": cap_normalized,
                        "layer": "direct"
                    }
                )
                return True
            
            # Check for high similarity matches (threshold 0.3 for direct matching)
            similarity = self._calculate_process_similarity(req_process, cap_process)
            if similarity >= 0.3:
                logger.debug(
                    "Direct similarity match found",
                    extra={
                        "requirement": req_process,
                        "capability": cap_process,
                        "requirement_normalized": req_normalized,
                        "capability_normalized": cap_normalized,
                        "similarity": similarity,
                        "layer": "direct"
                    }
                )
                return True
            
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
    
    async def _nlp_match(self, req_process: str, cap_process: str, domain: str = "manufacturing") -> bool:
        """Layer 3: NLP Matching - Using semantic similarity and natural language understanding"""
        try:
            # Use the NLP matcher for the specified domain
            if domain not in self.nlp_matchers:
                logger.warning(f"NLP matcher not available for domain '{domain}', skipping NLP matching")
                return False
            
            nlp_matcher = self.nlp_matchers[domain]
            
            # Add timeout to prevent slow NLP operations from blocking the API
            import asyncio
            try:
                results = await asyncio.wait_for(
                    nlp_matcher.match([req_process], [cap_process]),
                    timeout=0.5  # 500ms timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"NLP matching timed out for '{req_process}' vs '{cap_process}'")
                return False
            
            # Check if we have any matches
            for result in results:
                if result.matched and result.confidence >= 0.7:  # Use 0.7 as threshold for NLP match
                    logger.debug(
                        "NLP match found using semantic similarity",
                        extra={
                            "requirement": req_process,
                            "capability": cap_process,
                            "confidence": result.confidence,
                            "similarity": result.metadata.semantic_similarity if hasattr(result.metadata, 'semantic_similarity') else None,
                            "domain": domain
                        }
                    )
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in NLP Matching layer: {e}", exc_info=True)
            return False
    
    async def _generate_supply_tree(
        self,
        manifest: OKHManifest,
        facility: ManufacturingFacility,
        domain: str = "manufacturing"
    ) -> SupplyTree:
        """Generate a simplified supply tree for a manifest and facility"""
        try:
            # Calculate overall confidence based on process matching
            process_requirements = manifest.manufacturing_processes or []
            total_confidence = 0.0
            match_count = 0
            best_overall_match_type = "unknown"
            
            # Check if facility can handle the processes using multi-layer matching
            for process_name in process_requirements:
                facility_capabilities = []
                for equipment in facility.equipment:
                    if hasattr(equipment, 'manufacturing_process'):
                        if isinstance(equipment.manufacturing_process, str):
                            facility_capabilities.append(equipment.manufacturing_process)
                        elif isinstance(equipment.manufacturing_process, list):
                            facility_capabilities.extend(equipment.manufacturing_process)
                    if hasattr(equipment, 'manufacturing_processes'):
                        if isinstance(equipment.manufacturing_processes, list):
                            facility_capabilities.extend(equipment.manufacturing_processes)
                
                # Use multi-layer matching for confidence calculation
                best_confidence = 0.0
                best_match_type = "unknown"
                
                for capability in facility_capabilities:
                    # Try each layer and get the best confidence
                    if await self._direct_match(process_name, capability, domain):
                        confidence = 1.0
                        match_type = "direct"
                    elif await self._heuristic_match(process_name, capability, domain):
                        confidence = 0.8
                        match_type = "heuristic"
                    elif await self._nlp_match(process_name, capability, domain):
                        confidence = 0.7
                        match_type = "nlp"
                    else:
                        # Fallback to similarity-based scoring
                        similarity = self._calculate_process_similarity(process_name, capability)
                        if similarity >= 0.3:
                            confidence = similarity * 0.6  # Partial credit
                            match_type = "partial"
                        else:
                            confidence = 0.0
                            match_type = "no_match"
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match_type = match_type
                
                # Add the best confidence found for this process
                if best_confidence > 0.0:
                    total_confidence += best_confidence
                    match_count += 1
                    # Update overall match type to the best one found so far
                    if best_overall_match_type == "unknown" or best_match_type in ["direct", "heuristic", "nlp"]:
                        best_overall_match_type = best_match_type
            
            # Calculate average confidence with better granularity
            if process_requirements:
                confidence_score = total_confidence / len(process_requirements)
                # Ensure confidence is between 0 and 1
                confidence_score = max(0.0, min(1.0, confidence_score))
            else:
                confidence_score = 0.0
            
            # Use the simplified factory method
            supply_tree = SupplyTree.from_facility_and_manifest(
                facility=facility,
                manifest=manifest,
                confidence_score=confidence_score,
                match_type=best_overall_match_type,
                estimated_cost=None,  # Could be calculated based on facility rates
                estimated_time=None   # Could be calculated based on process complexity
            )
            
            logger.info(
                "Generated simplified supply tree",
                extra={
                    "okh_id": str(manifest.id),
                    "facility_id": str(facility.id),
                    "confidence_score": confidence_score,
                    "match_type": best_overall_match_type,
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
    
    def _calculate_process_similarity(self, process1: str, process2: str) -> float:
        """
        Calculate similarity between two process names.
        
        Returns a score between 0.0 and 1.0 indicating how similar the processes are.
        """
        if not process1 or not process2:
            return 0.0
        
        # Normalize both process names
        norm1 = self._normalize_process_name(process1)
        norm2 = self._normalize_process_name(process2)
        
        # Exact match
        if norm1 == norm2:
            return 1.0
        
        # Check for substring matches
        if norm1 in norm2 or norm2 in norm1:
            return 0.8
        
        # Check for common keywords
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:
            return 0.0
        
        jaccard_similarity = intersection / union
        
        # Boost similarity for manufacturing-related keywords
        manufacturing_keywords = {
            'machining', 'cnc', 'mill', 'lathe', 'drill', 'cut', 'grind',
            '3d', 'print', 'printer', 'assembly', 'pcb', 'electronics',
            'welding', 'weld', 'brake', 'bend', 'form', 'stamp'
        }
        
        common_manufacturing = words1.intersection(words2).intersection(manufacturing_keywords)
        if common_manufacturing:
            jaccard_similarity += 0.2  # Boost for manufacturing keywords
        
        # Handle common manufacturing abbreviations and synonyms
        abbreviation_map = {
            '3dp': ['3d', 'print', 'printer', 'fused', 'filament', 'fabrication'],
            'pcb': ['printed', 'circuit', 'board', 'electronics', 'assembly'],
            'cnc': ['computer', 'numerical', 'control', 'machining'],
            'assembly': ['assembling', 'putting', 'together', 'joining']
        }
        
        # Check for abbreviation matches
        for abbr, synonyms in abbreviation_map.items():
            if abbr in words1:
                if any(syn in words2 for syn in synonyms):
                    jaccard_similarity += 0.3  # Strong boost for abbreviation matches
            elif abbr in words2:
                if any(syn in words1 for syn in synonyms):
                    jaccard_similarity += 0.3  # Strong boost for abbreviation matches
        
        return min(1.0, jaccard_similarity)
    
    async def get_available_domains(self) -> List[Dict[str, Any]]:
        """Get list of available matching domains"""
        await self.ensure_initialized()
        
        # Get domains from the domain registry
        from ..registry.domain_registry import DomainRegistry
        domains = []
        
        # Get all registered domains
        for domain_id in DomainRegistry.list_domains():
            try:
                domain_services = DomainRegistry.get_domain_services(domain_id)
                # Get matcher count - handle both single matcher and list of matchers
                matcher = self.direct_matchers.get(domain_id)
                if matcher is None:
                    matchers_available = 0
                elif isinstance(matcher, list):
                    matchers_available = len(matcher)
                else:
                    matchers_available = 1  # Single matcher object
                
                domain_info = {
                    "id": domain_id,
                    "name": domain_id.title(),
                    "description": f"{domain_id.title()} domain matching capabilities",
                    "status": "active",
                    "matchers_available": matchers_available,
                    "nlp_enabled": domain_id in self.nlp_matchers
                }
                domains.append(domain_info)
            except Exception as e:
                logger.warning(f"Failed to get domain info for {domain_id}: {e}")
                # Add basic domain info even if services fail
                domain_info = {
                    "id": domain_id,
                    "name": domain_id.title(),
                    "description": f"{domain_id.title()} domain matching capabilities",
                    "status": "error",
                    "matchers_available": 0,
                    "nlp_enabled": False
                }
                domains.append(domain_info)
        
        logger.info(f"Retrieved {len(domains)} available domains")
        return domains

    async def _ensure_domains_registered(self) -> None:
        """Ensure domains are registered (for fallback mode when server startup doesn't run)"""
        from ..registry.domain_registry import DomainRegistry, DomainMetadata, DomainStatus
        
        # Check if all required domains are already registered
        required_domains = {"manufacturing", "cooking"}
        registered_domains = set(DomainRegistry.list_domains())
        if required_domains.issubset(registered_domains):
            logger.info("All required domains already registered")
            return
        
        logger.info("Registering domains for fallback mode...")
        
        try:
            # Import domain components
            from ..domains.cooking.extractors import CookingExtractor
            from ..domains.cooking.matchers import CookingMatcher
            from ..domains.cooking.validation.compatibility import CookingValidatorCompat
            from ...domains.manufacturing.okh_extractor import OKHExtractor
            from ...domains.manufacturing.okh_matcher import OKHMatcher
            from ...domains.manufacturing.validation.compatibility import ManufacturingOKHValidatorCompat
            
            # Register Cooking domain
            cooking_metadata = DomainMetadata(
                name="cooking",
                display_name="Cooking & Food Preparation",
                description="Domain for recipe and kitchen capability matching",
                version="1.0.0",
                status=DomainStatus.ACTIVE,
                supported_input_types={"recipe", "kitchen"},
                supported_output_types={"cooking_workflow", "meal_plan"},
                documentation_url="https://docs.ome.org/domains/cooking",
                maintainer="OME Cooking Team"
            )
            
            DomainRegistry.register_domain(
                domain_name="cooking",
                extractor=CookingExtractor(),
                matcher=CookingMatcher(),
                validator=CookingValidatorCompat(),
                metadata=cooking_metadata
            )
            
            # Register Manufacturing domain
            manufacturing_metadata = DomainMetadata(
                name="manufacturing",
                display_name="Manufacturing & Hardware Production",
                description="Domain for OKH/OKW manufacturing capability matching",
                version="1.0.0",
                status=DomainStatus.ACTIVE,
                supported_input_types={"okh", "okw"},
                supported_output_types={"supply_tree", "manufacturing_plan"},
                documentation_url="https://docs.ome.org/domains/manufacturing",
                maintainer="OME Manufacturing Team"
            )
            
            DomainRegistry.register_domain(
                domain_name="manufacturing",
                extractor=OKHExtractor(),
                matcher=OKHMatcher(),
                validator=ManufacturingOKHValidatorCompat(),
                metadata=manufacturing_metadata
            )
            
            logger.info("Successfully registered domains for fallback mode")
            
        except Exception as e:
            logger.error(f"Failed to register domains for fallback mode: {e}")
            # Don't raise the exception - let the service continue without domains

    async def ensure_initialized(self) -> None:
        """Ensure service is initialized"""
        if not self._initialized:
            raise RuntimeError("Matching service not initialized")