from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from src.config.settings import MAX_DEPTH

from ..domains.cooking.direct_matcher import CookingDirectMatcher
from ..domains.manufacturing.direct_matcher import MfgDirectMatcher
from ..matching.capability_rules import CapabilityMatcher, CapabilityRuleManager
from ..matching.nlp_matcher import NLPMatcher
from ..models.bom import Component
from ..models.component_match import ComponentMatch
from ..models.okh import OKHManifest
from ..models.okw import ManufacturingFacility
from ..models.supply_trees import SupplyTree, SupplyTreeSolution
from ..registry.domain_registry import DomainRegistry
from ..services.bom_resolution_service import BOMResolutionService
from ..services.domain_service import DomainDetector
from ..utils.logging import get_logger
from .okh_service import OKHService
from .okw_service import OKWService

logger = get_logger(__name__)


class MatchingService:
    """Service for matching OKH requirements to OKW capabilities"""

    _instance = None

    def __init__(self):
        """Initialize the matching service with Direct Matching layers"""
        self._initialized = False
        self.direct_matchers = {
            "manufacturing": MfgDirectMatcher(),
            "cooking": CookingDirectMatcher(),
        }
        self.capability_rule_manager = None
        self.capability_matcher = None
        self.nlp_matchers = {
            "manufacturing": NLPMatcher(domain="manufacturing"),
            "cooking": NLPMatcher(domain="cooking"),
        }
        self.okh_service: Optional[OKHService] = None
        self.okw_service: Optional[OKWService] = None

    @classmethod
    async def get_instance(
        cls,
        okh_service: Optional[OKHService] = None,
        okw_service: Optional[OKWService] = None,
    ) -> "MatchingService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
            await cls._instance.initialize(okh_service, okw_service)
        return cls._instance

    async def initialize(
        self,
        okh_service: Optional[OKHService] = None,
        okw_service: Optional[OKWService] = None,
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
                logger.info(
                    f"NLP matcher for domain '{domain}' initialized successfully"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to initialize NLP matcher for domain '{domain}': {e}"
                )

        self._initialized = True
        logger.info(
            "MatchingService initialized with Direct Matching, Capability-Centric Heuristic Matching, and NLP Matching"
        )

    async def find_matches(
        self, okh_id: UUID, optimization_criteria: Optional[Dict[str, float]] = None
    ) -> Set[SupplyTreeSolution]:
        """Find matching facilities for an OKH manifest by ID (loads manifest and facilities, then delegates)."""
        await self.ensure_initialized()
        logger.info(
            "Finding matches for OKH manifest",
            extra={
                "okh_id": str(okh_id),
                "optimization_criteria": optimization_criteria,
            },
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
                extra={"facility_count": len(facilities), "total_facilities": total},
            )
            # Delegate to the core logic
            return await self.find_matches_with_manifest(
                okh_manifest=manifest,
                facilities=facilities,
                optimization_criteria=optimization_criteria,
            )
        except Exception as e:
            logger.error(
                "Error finding matches",
                extra={"okh_id": str(okh_id), "error": str(e)},
                exc_info=True,
            )
            raise

    async def find_matches_with_manifest(
        self,
        okh_manifest: OKHManifest,
        facilities: List[ManufacturingFacility],
        optimization_criteria: Optional[Dict[str, float]] = None,
        explicit_domain: Optional[str] = None,
    ) -> Set[SupplyTreeSolution]:
        """Find matching facilities for an in-memory OKH manifest and provided facilities."""
        await self.ensure_initialized()

        logger.info(
            "Finding matches for in-memory OKH manifest",
            extra={
                "manifest_id": str(getattr(okh_manifest, "id", None)),
                "optimization_criteria": optimization_criteria,
            },
        )

        try:
            # Detect domain from the inputs
            domain = await self._detect_domain_for_matching(
                okh_manifest, facilities, explicit_domain
            )

            # Get the domain services
            domain_services = DomainRegistry.get_domain_services(domain)
            extractor = domain_services.extractor

            # Extract requirements using the domain extractor
            manifest_data = okh_manifest.to_dict()
            extraction_result = extractor.extract_requirements(manifest_data)
            requirements = (
                extraction_result.data.content.get("process_requirements", [])
                if extraction_result.data
                else []
            )

            logger.info(
                "Extracted requirements from OKH manifest",
                extra={"requirement_count": len(requirements)},
            )

            solutions = set()
            # Track processed facility IDs to avoid duplicates
            processed_facility_ids: Set[UUID] = set()

            for facility in facilities:
                # Skip if we've already processed this facility ID
                if facility.id in processed_facility_ids:
                    logger.debug(
                        f"Skipping duplicate facility {facility.id} ({facility.name})",
                        extra={
                            "facility_id": str(facility.id),
                            "facility_name": facility.name,
                        },
                    )
                    continue

                processed_facility_ids.add(facility.id)

                logger.debug(
                    "Checking facility for matches",
                    extra={
                        "facility_id": str(facility.id),
                        "facility_name": facility.name,
                    },
                )
                # Extract capabilities using the domain extractor
                facility_data = facility.to_dict()
                extraction_result = extractor.extract_capabilities(facility_data)
                capabilities = (
                    extraction_result.data.content.get("capabilities", [])
                    if extraction_result.data
                    else []
                )

                if await self._can_satisfy_requirements(
                    requirements, capabilities, domain
                ):
                    tree = await self._generate_supply_tree(
                        okh_manifest, facility, domain
                    )
                    # Use factory method for single-tree solution (backward compatible)
                    solution = SupplyTreeSolution.from_single_tree(
                        tree=tree,
                        score=tree.confidence_score,  # Use tree's confidence score
                        metrics={
                            "facility_count": 1,
                            "requirement_count": len(requirements),
                            "capability_count": len(capabilities),
                        },
                    )
                    solutions.add(solution)
                    logger.info(
                        "Found matching facility",
                        extra={
                            "facility_id": str(facility.id),
                            "confidence_score": tree.confidence_score,
                        },
                    )
            logger.info(
                "Match finding completed", extra={"solution_count": len(solutions)}
            )
            return solutions

        except Exception as e:
            logger.error(
                "Error finding matches (in-memory manifest)",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    async def _can_satisfy_requirements(
        self,
        requirements: List[Dict[str, Any]],
        capabilities: List[Dict[str, Any]],
        domain: str = "manufacturing",
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
                                "layer": "direct",
                            },
                        )
                        return True

                    # Try Layer 2: Heuristic Matching
                    if await self._heuristic_match(req_process, cap_process, domain):
                        logger.debug(
                            "Heuristic match found",
                            extra={
                                "requirement": req.get("process_name"),
                                "capability": cap.get("process_name"),
                                "layer": "heuristic",
                            },
                        )
                        return True

                    # Try Layer 3: NLP Matching
                    if await self._nlp_match(req_process, cap_process, domain):
                        logger.debug(
                            "NLP match found",
                            extra={
                                "requirement": req.get("process_name"),
                                "capability": cap.get("process_name"),
                                "layer": "nlp",
                            },
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
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def _direct_match(
        self, req_process: str, cap_process: str, domain: str = "manufacturing"
    ) -> bool:
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
                        "layer": "direct",
                    },
                )
                return True

            # Check for case-insensitive exact match
            if req_process.lower().strip() == cap_process.lower().strip():
                logger.debug(
                    "Direct case-insensitive match found",
                    extra={
                        "requirement": req_process,
                        "capability": cap_process,
                        "layer": "direct",
                    },
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
                        "layer": "direct",
                    },
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
                        "layer": "direct",
                    },
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error in Direct Matching layer: {e}", exc_info=True)
            # Fallback to simple matching
            return req_process.lower() == cap_process.lower()

    async def _heuristic_match(
        self, req_process: str, cap_process: str, domain: str = "manufacturing"
    ) -> bool:
        """Layer 2: Heuristic Matching - Using the new capability-centric heuristic rules system"""
        try:
            # Use the capability-centric heuristic matcher
            if not self.capability_matcher:
                logger.warning(
                    "Capability matcher not initialized, skipping heuristic matching"
                )
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
                capability_field="process_name",
            )

            # Check if we have any matches
            for result in results:
                if (
                    result.matched and result.confidence >= 0.7
                ):  # Use 0.7 as threshold for heuristic match
                    logger.debug(
                        "Heuristic match found using capability-centric rules",
                        extra={
                            "requirement": req_process,
                            "capability": cap_process,
                            "confidence": result.confidence,
                            "rule_used": (
                                result.rule_used.id if result.rule_used else None
                            ),
                            "domain": result.domain,
                        },
                    )
                    return True

            return False

        except Exception as e:
            logger.error(f"Error in Heuristic Matching layer: {e}", exc_info=True)
            return False

    async def _nlp_match(
        self, req_process: str, cap_process: str, domain: str = "manufacturing"
    ) -> bool:
        """Layer 3: NLP Matching - Using semantic similarity and natural language understanding"""
        try:
            # Use the NLP matcher for the specified domain
            if domain not in self.nlp_matchers:
                logger.warning(
                    f"NLP matcher not available for domain '{domain}', skipping NLP matching"
                )
                return False

            nlp_matcher = self.nlp_matchers[domain]

            # Add timeout to prevent slow NLP operations from blocking the API
            import asyncio

            try:
                results = await asyncio.wait_for(
                    nlp_matcher.match([req_process], [cap_process]),
                    timeout=0.5,  # 500ms timeout
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f"NLP matching timed out for '{req_process}' vs '{cap_process}'"
                )
                return False

            # Check if we have any matches
            for result in results:
                if (
                    result.matched and result.confidence >= 0.7
                ):  # Use 0.7 as threshold for NLP match
                    logger.debug(
                        "NLP match found using semantic similarity",
                        extra={
                            "requirement": req_process,
                            "capability": cap_process,
                            "confidence": result.confidence,
                            "similarity": (
                                result.metadata.semantic_similarity
                                if hasattr(result.metadata, "semantic_similarity")
                                else None
                            ),
                            "domain": domain,
                        },
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
        domain: str = "manufacturing",
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
                    if hasattr(equipment, "manufacturing_process"):
                        if isinstance(equipment.manufacturing_process, str):
                            facility_capabilities.append(
                                equipment.manufacturing_process
                            )
                        elif isinstance(equipment.manufacturing_process, list):
                            facility_capabilities.extend(
                                equipment.manufacturing_process
                            )
                    if hasattr(equipment, "manufacturing_processes"):
                        if isinstance(equipment.manufacturing_processes, list):
                            facility_capabilities.extend(
                                equipment.manufacturing_processes
                            )

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
                        similarity = self._calculate_process_similarity(
                            process_name, capability
                        )
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
                    if best_overall_match_type == "unknown" or best_match_type in [
                        "direct",
                        "heuristic",
                        "nlp",
                    ]:
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
                estimated_time=None,  # Could be calculated based on process complexity
            )

            logger.info(
                "Generated simplified supply tree",
                extra={
                    "okh_id": str(manifest.id),
                    "facility_id": str(facility.id),
                    "confidence_score": confidence_score,
                    "match_type": best_overall_match_type,
                    "process_count": len(process_requirements),
                },
            )

            return supply_tree

        except Exception as e:
            logger.error(
                "Error generating supply tree",
                extra={
                    "okh_id": str(manifest.id),
                    "facility_id": str(facility.id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    def _calculate_confidence_score(
        self,
        requirements: List[Dict[str, Any]],
        capabilities: List[Dict[str, Any]],
        optimization_criteria: Optional[Dict[str, float]] = None,
        match_results: Optional[List[Any]] = None,
    ) -> float:
        """
        Calculate confidence score for a match using multi-factor weighted scoring.

        Args:
            requirements: List of requirement dictionaries
            capabilities: List of capability dictionaries
            optimization_criteria: Optional weights for different factors
            match_results: Optional matching layer results for layer-specific scoring

        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            if not requirements:
                return 0.0

            # Default weights
            default_weights = {
                "process": 0.40,
                "material": 0.25,
                "equipment": 0.20,
                "scale": 0.10,
                "other": 0.05,
            }

            # Use optimization criteria if provided, otherwise use defaults
            weights = (
                optimization_criteria if optimization_criteria else default_weights
            )

            # Normalize weights to sum to 1.0
            total_weight = sum(weights.values())
            if total_weight > 0:
                weights = {k: v / total_weight for k, v in weights.items()}
            else:
                weights = default_weights

            # Calculate process matching score
            process_score = self._calculate_process_score(requirements, capabilities)

            # Calculate material matching score
            material_score = self._calculate_material_score(requirements, capabilities)

            # Calculate equipment matching score
            equipment_score = self._calculate_equipment_score(
                requirements, capabilities
            )

            # Calculate scale/capacity matching score
            scale_score = self._calculate_scale_score(requirements, capabilities)

            # Calculate other factors score
            other_score = self._calculate_other_score(
                requirements, capabilities, match_results
            )

            # Weighted combination
            confidence_score = (
                process_score * weights.get("process", 0.40)
                + material_score * weights.get("material", 0.25)
                + equipment_score * weights.get("equipment", 0.20)
                + scale_score * weights.get("scale", 0.10)
                + other_score * weights.get("other", 0.05)
            )

            # Ensure score is between 0.0 and 1.0
            confidence_score = max(0.0, min(1.0, confidence_score))

            return round(confidence_score, 2)

        except Exception as e:
            logger.error(
                "Error calculating confidence score",
                extra={
                    "requirement_count": len(requirements),
                    "capability_count": len(capabilities),
                    "optimization_criteria": optimization_criteria,
                    "error": str(e),
                },
                exc_info=True,
            )
            # Return a conservative score on error
            return 0.5

    def _calculate_process_score(
        self, requirements: List[Dict[str, Any]], capabilities: List[Dict[str, Any]]
    ) -> float:
        """Calculate process matching score."""
        if not requirements:
            return 0.0

        matched_processes = 0
        total_processes = 0

        for req in requirements:
            req_process = req.get("process_name", "").lower()
            if not req_process:
                continue

            total_processes += 1

            # Check for exact or near-match in capabilities
            for cap in capabilities:
                cap_process = cap.get("process_name", "").lower()
                if not cap_process:
                    continue

                # Exact match
                if req_process == cap_process:
                    matched_processes += 1
                    break

                # Near-match (Levenshtein distance <= 2)
                if self._levenshtein_distance(req_process, cap_process) <= 2:
                    matched_processes += 0.8  # Partial credit for near-match
                    break

        return matched_processes / total_processes if total_processes > 0 else 0.0

    def _calculate_material_score(
        self, requirements: List[Dict[str, Any]], capabilities: List[Dict[str, Any]]
    ) -> float:
        """Calculate material matching score."""
        req_materials = set()
        for req in requirements:
            materials = req.get("materials", [])
            if isinstance(materials, list):
                req_materials.update(m.lower() for m in materials if m)
            elif isinstance(materials, str):
                req_materials.add(materials.lower())

        if not req_materials:
            return 1.0  # No material requirements = perfect score

        cap_materials = set()
        for cap in capabilities:
            materials = cap.get("materials", [])
            if isinstance(materials, list):
                cap_materials.update(m.lower() for m in materials if m)
            elif isinstance(materials, str):
                cap_materials.add(materials.lower())

        # Calculate overlap
        matched_materials = req_materials.intersection(cap_materials)
        return len(matched_materials) / len(req_materials) if req_materials else 0.0

    def _calculate_equipment_score(
        self, requirements: List[Dict[str, Any]], capabilities: List[Dict[str, Any]]
    ) -> float:
        """Calculate equipment/tool matching score."""
        req_equipment = set()
        for req in requirements:
            equipment = req.get("equipment", []) or req.get("tools", [])
            if isinstance(equipment, list):
                req_equipment.update(e.lower() for e in equipment if e)
            elif isinstance(equipment, str):
                req_equipment.add(equipment.lower())

        if not req_equipment:
            return 1.0  # No equipment requirements = perfect score

        cap_equipment = set()
        for cap in capabilities:
            equipment = cap.get("equipment", []) or cap.get("tools", [])
            if isinstance(equipment, list):
                cap_equipment.update(e.lower() for e in equipment if e)
            elif isinstance(equipment, str):
                cap_equipment.add(equipment.lower())

        matched_equipment = req_equipment.intersection(cap_equipment)
        return len(matched_equipment) / len(req_equipment) if req_equipment else 0.0

    def _calculate_scale_score(
        self, requirements: List[Dict[str, Any]], capabilities: List[Dict[str, Any]]
    ) -> float:
        """Calculate scale/capacity matching score."""
        # Extract scale requirements
        req_scale = None
        for req in requirements:
            scale = req.get("scale") or req.get("quantity") or req.get("volume")
            if scale:
                req_scale = scale
                break

        if not req_scale:
            return 1.0  # No scale requirements = perfect score

        # Extract capability scale
        cap_scale = None
        for cap in capabilities:
            scale = cap.get("scale") or cap.get("capacity") or cap.get("max_volume")
            if scale:
                cap_scale = scale
                break

        if not cap_scale:
            return 0.5  # Unknown capability scale = moderate score

        # Compare scales (assuming numeric values)
        try:
            req_val = float(req_scale)
            cap_val = float(cap_scale)

            if cap_val >= req_val:
                return 1.0  # Capability can handle requirement
            else:
                # Partial credit based on ratio
                return min(1.0, cap_val / req_val)
        except (ValueError, TypeError):
            # Non-numeric scales, use string comparison
            return 0.5

    def _calculate_other_score(
        self,
        requirements: List[Dict[str, Any]],
        capabilities: List[Dict[str, Any]],
        match_results: Optional[List[Any]] = None,
    ) -> float:
        """Calculate score for other factors (match layer quality, etc.)."""
        if match_results:
            # Use match layer results to inform score
            # Higher confidence from direct matches, lower from NLP/LLM
            layer_scores = []
            for result in match_results:
                layer = getattr(result, "layer", None)
                confidence = getattr(result, "confidence", 0.5)

                # Weight by layer type
                if layer == "direct":
                    layer_scores.append(confidence * 1.0)
                elif layer == "heuristic":
                    layer_scores.append(confidence * 0.8)
                elif layer == "nlp":
                    layer_scores.append(confidence * 0.6)
                elif layer == "llm":
                    layer_scores.append(confidence * 0.7)
                else:
                    layer_scores.append(confidence * 0.5)

            if layer_scores:
                return sum(layer_scores) / len(layer_scores)

        return 0.5  # Default moderate score

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

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

        normalized = re.sub(r"[_\-]+", " ", normalized)

        # Normalize multiple spaces to single space
        normalized = re.sub(r"\s+", " ", normalized)

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
            "machining",
            "cnc",
            "mill",
            "lathe",
            "drill",
            "cut",
            "grind",
            "3d",
            "print",
            "printer",
            "assembly",
            "pcb",
            "electronics",
            "welding",
            "weld",
            "brake",
            "bend",
            "form",
            "stamp",
        }

        common_manufacturing = words1.intersection(words2).intersection(
            manufacturing_keywords
        )
        if common_manufacturing:
            jaccard_similarity += 0.2  # Boost for manufacturing keywords

        # Handle common manufacturing abbreviations and synonyms
        abbreviation_map = {
            "3dp": ["3d", "print", "printer", "fused", "filament", "fabrication"],
            "pcb": ["printed", "circuit", "board", "electronics", "assembly"],
            "cnc": ["computer", "numerical", "control", "machining"],
            "assembly": ["assembling", "putting", "together", "joining"],
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
                    "nlp_enabled": domain_id in self.nlp_matchers,
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
                    "nlp_enabled": False,
                }
                domains.append(domain_info)

        logger.info(f"Retrieved {len(domains)} available domains")
        return domains

    async def _ensure_domains_registered(self) -> None:
        """Ensure domains are registered (for fallback mode when server startup doesn't run)"""
        from ..registry.domain_registry import (
            DomainMetadata,
            DomainRegistry,
            DomainStatus,
        )

        # Check if all required domains are already registered
        required_domains = {"manufacturing", "cooking"}
        registered_domains = set(DomainRegistry.list_domains())
        if required_domains.issubset(registered_domains):
            logger.info("All required domains already registered")
            return

        logger.info("Registering domains for fallback mode...")

        try:
            # Import domain components
            from ...domains.manufacturing.okh_extractor import OKHExtractor
            from ...domains.manufacturing.okh_matcher import OKHMatcher
            from ...domains.manufacturing.validation.compatibility import (
                ManufacturingOKHValidatorCompat,
            )
            from ..domains.cooking.extractors import CookingExtractor
            from ..domains.cooking.matchers import CookingMatcher
            from ..domains.cooking.validation.compatibility import (
                CookingValidatorCompat,
            )

            # Register Cooking domain
            cooking_metadata = DomainMetadata(
                name="cooking",
                display_name="Cooking & Food Preparation",
                description="Domain for recipe and kitchen capability matching",
                version="1.0.0",
                status=DomainStatus.ACTIVE,
                supported_input_types={"recipe", "kitchen"},
                supported_output_types={"cooking_workflow", "meal_plan"},
                documentation_url="https://docs.ohm.org/domains/cooking",
                maintainer="OHM Cooking Team",
            )

            DomainRegistry.register_domain(
                domain_name="cooking",
                extractor=CookingExtractor(),
                matcher=CookingMatcher(),
                validator=CookingValidatorCompat(),
                metadata=cooking_metadata,
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
                documentation_url="https://docs.ohm.org/domains/manufacturing",
                maintainer="OHM Manufacturing Team",
            )

            DomainRegistry.register_domain(
                domain_name="manufacturing",
                extractor=OKHExtractor(),
                matcher=OKHMatcher(),
                validator=ManufacturingOKHValidatorCompat(),
                metadata=manufacturing_metadata,
            )

            logger.info("Successfully registered domains for fallback mode")

        except Exception as e:
            logger.error(f"Failed to register domains for fallback mode: {e}")
            # Don't raise the exception - let the service continue without domains

    async def ensure_initialized(self) -> None:
        """Ensure service is initialized"""
        if not self._initialized:
            raise RuntimeError("Matching service not initialized")

    async def _detect_domain_for_matching(
        self,
        okh_manifest: OKHManifest,
        facilities: List[ManufacturingFacility],
        explicit_domain: Optional[str] = None,
    ) -> str:
        """Detect domain for matching operation"""
        # 1. Check explicit domain override
        if explicit_domain:
            return explicit_domain

        # 2. Check manifest domain field
        if okh_manifest.domain:
            return okh_manifest.domain

        # 3. Check facilities domain (if all have same domain)
        facility_domains = {f.domain for f in facilities if f.domain}
        if len(facility_domains) == 1:
            return facility_domains.pop()

        # 4. Use DomainDetector for content-based detection
        # Sample a facility for detection (or use all)
        sample_facility = facilities[0] if facilities else None
        if sample_facility:
            try:
                detection_result = DomainDetector.detect_domain(
                    okh_manifest, sample_facility
                )
                return detection_result.domain
            except Exception as e:
                logger.warning(
                    f"Domain detection failed, defaulting to manufacturing: {e}",
                    extra={"error": str(e)},
                )

        # 5. Default to manufacturing for backward compatibility
        return "manufacturing"

    async def match_with_nested_components(
        self,
        okh_manifest: OKHManifest,
        facilities: List[ManufacturingFacility],
        max_depth: Optional[int] = None,
        domain: str = "manufacturing",
        okh_service: Optional[OKHService] = None,
        manifest_path: Optional[str] = None,
    ) -> SupplyTreeSolution:
        """
        Match OKH with nested components across multiple facilities.

        Algorithm:
        1. Resolve BOM and explode into component matches
        2. Sort components by depth (deepest first)
        3. For each component (in dependency order):
           a. Match component to facilities
           b. Generate SupplyTrees for each match
           c. Link parent-child relationships
        4. Build dependency graph
        5. Calculate production sequence
        6. Validate solution
        7. Return SupplyTreeSolution

        Args:
            okh_manifest: OKH manifest to match
            facilities: List of manufacturing facilities
            max_depth: Maximum nesting depth (default: 5)
            domain: Domain for matching (default: "manufacturing")
            okh_service: OKHService instance for resolving references (optional)

        Returns:
            SupplyTreeSolution with all matched components (nested if multiple trees)
        """
        await self.ensure_initialized()

        # Use configured default if max_depth not provided
        if max_depth is None:
            max_depth = MAX_DEPTH

        # Use provided okh_service or self.okh_service
        service = okh_service or self.okh_service

        logger.info(
            "Matching nested components",
            extra={
                "okh_id": str(okh_manifest.id),
                "facility_count": len(facilities),
                "max_depth": max_depth,
                "domain": domain,
            },
        )

        try:
            # Step 1: Resolve BOM and explode into component matches (with graceful fallbacks)
            bom_resolver = BOMResolutionService(service)
            # Pass manifest_path to resolve_bom for external BOM file resolution
            bom = await bom_resolver.resolve_bom(
                okh_manifest, service, manifest_path=manifest_path
            )

            if not bom.components:
                logger.warning(
                    "No components found in BOM - cannot perform nested matching. "
                    "Falling back to single-level matching.",
                    extra={"okh_id": str(okh_manifest.id)},
                )
                # Return empty solution with helpful message
                return SupplyTreeSolution.from_nested_trees(
                    all_trees=[],
                    root_trees=[],
                    component_mapping={},
                    score=0.0,
                    metrics={},
                    metadata={
                        "matching_mode": "nested",
                        "warning": "No components found in BOM for nested matching",
                        "suggestion": "Try single-level matching (max_depth=0) or ensure BOM has components",
                    },
                )

            component_matches = await bom_resolver.explode_bom(
                bom, service, max_depth=max_depth
            )

            # Count components with unresolved references
            unresolved_count = sum(
                1
                for m in component_matches
                if m.okh_manifest is None and m.component.reference
            )

            if unresolved_count > 0:
                logger.warning(
                    f"Found {unresolved_count} component(s) with unresolved references. "
                    f"Will attempt best-effort matching using component data directly.",
                    extra={
                        "okh_id": str(okh_manifest.id),
                        "unresolved_count": unresolved_count,
                        "total_components": len(component_matches),
                    },
                )

            logger.info(
                "BOM exploded into component matches",
                extra={
                    "component_count": len(component_matches),
                    "max_depth_found": (
                        max([m.depth for m in component_matches])
                        if component_matches
                        else 0
                    ),
                    "unresolved_references": unresolved_count,
                },
            )

            # Step 2: Sort by depth (deepest first) for dependency order
            component_matches.sort(key=lambda x: -x.depth)

            # Step 3: Match each component to facilities (best-effort matching)
            component_supply_trees: Dict[str, List[SupplyTree]] = {}
            unmatched_components = []
            matched_components = []

            for component_match in component_matches:
                component = component_match.component

                # Determine which OKH to use for matching
                # If component has a reference, use that OKH; otherwise use the root OKH
                manifest = component_match.okh_manifest or okh_manifest

                try:
                    # Match component to facilities (component-level matching logic)
                    component_trees = await self._match_component_to_facilities(
                        component=component,
                        component_match=component_match,
                        manifest=manifest,
                        facilities=facilities,
                        domain=domain,
                    )

                    component_supply_trees[component.id] = component_trees
                    component_match.supply_trees = component_trees
                    component_match.matched = len(component_trees) > 0

                    if component_match.matched:
                        matched_components.append(component.name)
                    else:
                        unmatched_components.append(
                            {
                                "name": component.name,
                                "id": component.id,
                                "depth": component_match.depth,
                                "path": (
                                    " > ".join(component_match.path)
                                    if component_match.path
                                    else component.name
                                ),
                            }
                        )
                except Exception as e:
                    logger.warning(
                        f"Error matching component '{component.name}' to facilities: {e}. "
                        f"Skipping this component but continuing with others.",
                        extra={
                            "component_id": component.id,
                            "component_name": component.name,
                            "depth": component_match.depth,
                            "error_type": type(e).__name__,
                        },
                    )
                    unmatched_components.append(
                        {
                            "name": component.name,
                            "id": component.id,
                            "depth": component_match.depth,
                            "path": (
                                " > ".join(component_match.path)
                                if component_match.path
                                else component.name
                            ),
                            "error": str(e),
                        }
                    )
                    # Continue with other components
                    component_supply_trees[component.id] = []
                    component_match.matched = False

                # Link to parent if exists (enhanced parent-child linking)
                if component_match.parent_component_id:
                    self._link_parent_child_relationships(
                        component_match=component_match,
                        component_trees=component_trees,
                        component_supply_trees=component_supply_trees,
                    )

            # Step 4: Build solution
            all_trees = []
            for trees in component_supply_trees.values():
                all_trees.extend(trees)

            root_trees = [tree for tree in all_trees if tree.depth == 0]

            # Calculate average score
            avg_score = (
                sum(tree.confidence_score for tree in all_trees) / len(all_trees)
                if all_trees
                else 0.0
            )

            # Use factory method for nested solutions
            solution = SupplyTreeSolution.from_nested_trees(
                all_trees=all_trees,
                root_trees=root_trees,
                component_mapping=component_supply_trees,
                score=avg_score,
                metrics={
                    "facility_count": len(facilities),
                    "component_count": len(component_matches),
                    "total_trees": len(all_trees),
                },
                metadata={
                    "okh_id": str(okh_manifest.id),
                    "okh_title": okh_manifest.title,
                    "max_depth": max_depth,
                    "domain": domain,
                    "facility_count": len(facilities),
                    "component_count": len(component_matches),
                    "matched_components": len(matched_components),
                    "unmatched_components": len(unmatched_components),
                    "warnings": (
                        []
                        if not unmatched_components
                        else [
                            f"{len(unmatched_components)} component(s) could not be matched to facilities"
                        ]
                    ),
                },
            )

            logger.info(
                "Nested component matching completed",
                extra={
                    "total_trees": len(all_trees),
                    "root_trees": len(root_trees),
                    "is_valid": (
                        solution.validation_result.is_valid
                        if solution.validation_result
                        else False
                    ),
                },
            )

            return solution

        except Exception as e:
            error_msg = (
                f"Nested matching encountered an error: {str(e)}. "
                f"This may be due to missing component references or BOM data. "
                f"Consider using single-level matching (max_depth=0) or ensuring all referenced OKH files are available."
            )
            logger.error(
                error_msg,
                extra={
                    "okh_id": str(okh_manifest.id),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            # Return a partial solution with error information rather than failing completely
            return SupplyTreeSolution.from_nested_trees(
                all_trees=[],
                root_trees=[],
                component_mapping={},
                score=0.0,
                metrics={},
                metadata={
                    "matching_mode": "nested",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "suggestion": "Try single-level matching (max_depth=0) or check BOM data availability",
                },
            )

    def _tsdc_to_process_uri(self, tsdc_code: str) -> str:
        """
        Convert TSDC code to manufacturing process URI.

        Args:
            tsdc_code: TSDC code (e.g., "3DP", "PCB", "CNC")

        Returns:
            Process URI (Wikipedia URL format)
        """
        tsdc_mapping = {
            "3DP": "https://en.wikipedia.org/wiki/Fused_filament_fabrication",
            "PCB": "https://en.wikipedia.org/wiki/Printed_circuit_board",
            "CNC": "https://en.wikipedia.org/wiki/Machining",
            "LASER": "https://en.wikipedia.org/wiki/Laser_cutting",
            "SHEET": "https://en.wikipedia.org/wiki/Sheet_metal_forming",
            "ASSEMBLY": "https://en.wikipedia.org/wiki/Assembly_line",
        }
        return tsdc_mapping.get(
            tsdc_code.upper(), f"https://en.wikipedia.org/wiki/{tsdc_code}"
        )

    def _create_component_manifest(
        self, base_manifest: OKHManifest, component: Component
    ) -> OKHManifest:
        """
        Create a component-specific manifest with component's process requirements.

        This allows component-level matching using the component's specific processes
        rather than the root manifest's processes.

        Args:
            base_manifest: Base OKH manifest
            component: Component with specific requirements

        Returns:
            Modified OKHManifest with component-specific processes
        """
        # Start with a copy of the base manifest
        import copy

        component_manifest = copy.deepcopy(base_manifest)

        # Extract component processes and convert to URIs
        component_processes = []

        # Get processes from component requirements (may be strings like "3DP", "PCB")
        component_requirements = component.requirements or {}
        req_processes = component_requirements.get("process", [])
        if isinstance(req_processes, str):
            req_processes = [req_processes]

        # Convert process strings to URIs (handle both TSDC codes and existing URIs)
        for process in req_processes:
            # If it's already a URI, use it as-is
            if process.startswith("http://") or process.startswith("https://"):
                if process not in component_processes:
                    component_processes.append(process)
            else:
                # Convert TSDC code or process name to URI
                process_uri = self._tsdc_to_process_uri(process)
                if process_uri not in component_processes:
                    component_processes.append(process_uri)

        # Convert TSDC codes from metadata to process URIs
        if component.metadata and "tsdc" in component.metadata:
            tsdc_codes = component.metadata.get("tsdc", [])
            if isinstance(tsdc_codes, list):
                for tsdc_code in tsdc_codes:
                    process_uri = self._tsdc_to_process_uri(tsdc_code)
                    if process_uri not in component_processes:
                        component_processes.append(process_uri)

        # If we found component-specific processes, use them
        # Otherwise, fall back to base manifest processes
        if component_processes:
            component_manifest.manufacturing_processes = component_processes
            logger.debug(
                f"Using component-specific processes for {component.name}: {component_processes}",
                extra={
                    "component_id": component.id,
                    "component_name": component.name,
                    "processes": component_processes,
                },
            )
        # If no component processes found, use base manifest processes (existing behavior)

        return component_manifest

    async def _match_component_to_facilities(
        self,
        component: Component,
        component_match: ComponentMatch,
        manifest: OKHManifest,
        facilities: List[ManufacturingFacility],
        domain: str,
        min_confidence: float = 0.0,
    ) -> List[SupplyTree]:
        """
        Match a component to facilities with component-specific logic.

        This method implements component-level matching by:
        1. Creating a component-specific manifest with component's process requirements
        2. Generating SupplyTrees for matching facilities using component processes
        3. Applying confidence thresholds
        4. Enhancing trees with component information

        Args:
            component: Component to match
            component_match: ComponentMatch object with metadata
            manifest: OKH manifest to use for matching (base manifest)
            facilities: List of facilities to match against
            domain: Domain for matching
            min_confidence: Minimum confidence threshold (default: 0.0, accept all)

        Returns:
            List of SupplyTrees for this component
        """
        component_trees = []

        # Create component-specific manifest with component's process requirements
        component_manifest = self._create_component_manifest(manifest, component)

        logger.info(
            f"Matching component '{component.name}' to {len(facilities)} facilities",
            extra={
                "component_id": component.id,
                "component_name": component.name,
                "component_processes": component_manifest.manufacturing_processes,
                "facility_count": len(facilities),
                "base_manifest_processes": manifest.manufacturing_processes,
            },
        )

        # Match component to each facility
        for facility in facilities:
            try:
                # Generate supply tree using component-specific manifest
                # This ensures we match based on component's processes, not root manifest's
                tree = await self._generate_supply_tree(
                    component_manifest, facility, domain
                )

                logger.debug(
                    f"Generated tree for component '{component.name}' at facility '{facility.name}': "
                    f"confidence={tree.confidence_score}",
                    extra={
                        "component_id": component.id,
                        "component_name": component.name,
                        "facility_id": str(facility.id),
                        "facility_name": facility.name,
                        "confidence": tree.confidence_score,
                        "min_confidence": min_confidence,
                    },
                )

                # Apply confidence threshold
                if tree.confidence_score < min_confidence:
                    logger.debug(
                        f"Skipping facility {facility.name} for component {component.name} "
                        f"(confidence {tree.confidence_score} < {min_confidence})",
                        extra={
                            "component_id": component.id,
                            "facility_id": str(facility.id),
                            "confidence": tree.confidence_score,
                            "threshold": min_confidence,
                        },
                    )
                    continue

                # Enhance tree with component information
                tree.component_id = component.id
                tree.component_name = component.name
                tree.component_quantity = component.quantity
                tree.component_unit = component.unit
                tree.depth = component_match.depth
                tree.component_path = component_match.path
                tree.production_stage = (
                    "component" if component_match.depth > 0 else "final"
                )

                # Add component-specific metadata
                if component.requirements:
                    tree.metadata["component_requirements"] = component.requirements
                if component.metadata:
                    tree.metadata["component_metadata"] = component.metadata

                component_trees.append(tree)

                logger.debug(
                    f"Matched component {component.name} to facility {facility.name}",
                    extra={
                        "component_id": component.id,
                        "facility_id": str(facility.id),
                        "confidence": tree.confidence_score,
                        "depth": component_match.depth,
                    },
                )

            except Exception as e:
                logger.warning(
                    f"Failed to generate supply tree for component {component.name} at facility {facility.name}: {e}",
                    extra={
                        "component_id": component.id,
                        "facility_id": str(facility.id),
                        "error": str(e),
                    },
                )
                continue

        return component_trees

    def _link_parent_child_relationships(
        self,
        component_match: ComponentMatch,
        component_trees: List[SupplyTree],
        component_supply_trees: Dict[str, List[SupplyTree]],
    ) -> None:
        """
        Link parent-child relationships between SupplyTrees.

        This method implements enhanced parent-child linking that:
        1. Links child trees to parent trees
        2. Updates parent's child_tree_ids and depends_on lists
        3. Updates child's required_by list
        4. Handles cases where a component depends on multiple parents

        Args:
            component_match: ComponentMatch for the child component
            component_trees: List of SupplyTrees for the child component
            component_supply_trees: Dictionary mapping component IDs to their SupplyTrees
        """
        parent_component_id = component_match.parent_component_id
        if not parent_component_id:
            return

        # Get parent trees
        parent_trees = component_supply_trees.get(parent_component_id, [])

        if not parent_trees:
            logger.debug(
                f"Parent component {parent_component_id} has no trees, skipping linking",
                extra={
                    "child_component_id": component_match.component.id,
                    "parent_component_id": parent_component_id,
                },
            )
            return

        # Link each child tree to each parent tree
        for parent_tree in parent_trees:
            for child_tree in component_trees:
                # Set parent reference on child
                child_tree.parent_tree_id = parent_tree.id

                # Update parent's child list (avoid duplicates)
                if child_tree.id not in parent_tree.child_tree_ids:
                    parent_tree.child_tree_ids.append(child_tree.id)

                # Update parent's dependencies (child must be completed before parent)
                if child_tree.id not in parent_tree.depends_on:
                    parent_tree.depends_on.append(child_tree.id)

                # Update child's required_by list (parent depends on child)
                if parent_tree.id not in child_tree.required_by:
                    child_tree.required_by.append(parent_tree.id)

                logger.debug(
                    f"Linked child tree {child_tree.id} to parent tree {parent_tree.id}",
                    extra={
                        "child_component": component_match.component.name,
                        "parent_component_id": parent_component_id,
                        "child_tree_id": str(child_tree.id),
                        "parent_tree_id": str(parent_tree.id),
                    },
                )
