import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.core.domains.manufacturing.okh_extractor import OKHExtractor
from src.core.domains.manufacturing.okh_validator import OKHValidator
from src.core.domains.manufacturing.okh_matcher import OKHMatcher, OKHRequirement
from src.core.models.okh import (
    OKHManifest,
    License,
    PartSpec,
    ManufacturingSpec,
    MaterialSpec,
    ProcessRequirement,
)
from src.core.models.base.base_orchestrator import BaseOrchestrator, MatchStatus
from src.core.models.base.base_types import (
    NormalizedCapabilities,
    NormalizedRequirements,
    Capability,
)


class OKHOrchestrator(BaseOrchestrator):
    """
    Orchestrator for OKH matching in the manufacturing domain

    Handles the complete lifecycle of matching OKH requirements
    to manufacturing capabilities
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        modules: Optional[List] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the OKH orchestrator

        Args:
            config_path: Path to orchestrator configuration
            modules: Optional explicit module configurations
            logger: Optional custom logger
        """
        # Set domain before initializing base class
        self.domain = "manufacturing"

        super().__init__(config_path, modules, logger)

        # Initialize domain-specific components
        self.extractor = OKHExtractor()
        self.validator = OKHValidator()

    def match(
        self,
        requirements: List[NormalizedRequirements],
        capabilities: List[NormalizedCapabilities],
    ) -> Dict[str, Any]:
        """
        Execute the full matching process for OKH requirements

        Args:
            requirements: List of normalized OKH requirements
            capabilities: List of normalized manufacturing capabilities

        Returns:
            Dictionary with matching results including supply trees
        """
        # Initialize matching modules if not already done
        if not self._initialized_modules:
            self.initialize()

        # Validate input
        if not requirements or not capabilities:
            self._log_error("Cannot match: empty requirements or capabilities")
            return {
                "status": "error",
                "message": "Empty requirements or capabilities",
                "supply_trees": [],
            }

        # Update state
        self.state["status"] = MatchStatus.IN_PROGRESS
        self._log_event(
            f"Starting matching with {len(requirements)} requirements and {len(capabilities)} capabilities"
        )

        # Convert normalized requirements to OKH manifests
        okh_manifests = []
        for req in requirements:
            try:
                manifest = self._requirements_to_manifest(req)
                if manifest:
                    okh_manifests.append(manifest)
            except Exception as e:
                self._log_error(f"Error converting requirements to manifest: {str(e)}")

        if not okh_manifests:
            self._log_error("Failed to convert any requirements to OKH manifests")
            self.state["status"] = MatchStatus.ERROR
            return {
                "status": "error",
                "message": "Failed to convert requirements to OKH manifests",
                "supply_trees": [],
            }

        # Convert normalized capabilities to manufacturing facilities
        facilities = []
        for cap in capabilities:
            try:
                facility = self._capabilities_to_facility(cap)
                if facility:
                    facilities.append(facility)
            except Exception as e:
                self._log_error(f"Error converting capabilities to facility: {str(e)}")

        if not facilities:
            self._log_error(
                "Failed to convert any capabilities to manufacturing facilities"
            )
            self.state["status"] = MatchStatus.ERROR
            return {
                "status": "error",
                "message": "Failed to convert capabilities to facilities",
                "supply_trees": [],
            }

        # Generate requirements for each module
        module_requirements = self._prepare_module_requirements(okh_manifests)

        # Generate capabilities for each module
        module_capabilities = self._prepare_module_capabilities(facilities)

        # Execute matching modules
        supply_trees = []
        confidence_scores = []

        for module in self._initialized_modules:
            try:
                # Match using this module
                module_result = module.match(
                    module_requirements.get(module.__class__.__name__, []),
                    module_capabilities.get(module.__class__.__name__, []),
                )

                # Process module results
                if hasattr(module_result, "supply_tree"):
                    supply_trees.append(module_result.supply_tree)
                    confidence_scores.append(module_result.confidence)
                elif isinstance(module_result, dict) and "supply_tree" in module_result:
                    supply_trees.append(module_result["supply_tree"])
                    confidence_scores.append(module_result.get("confidence", 0.5))
            except Exception as e:
                self._log_error(
                    f"Error in matching module {module.__class__.__name__}: {str(e)}"
                )

        # If no modules generated supply trees, fall back to base matcher
        if not supply_trees:
            self._log_event(
                "No module generated supply trees, falling back to base matcher"
            )

            # Create base matcher
            base_matcher = OKHMatcher()

            # Generate supply trees for each manifest
            for manifest in okh_manifests:
                try:
                    supply_tree = base_matcher.generate_supply_tree(
                        manifest, facilities
                    )
                    supply_trees.append(supply_tree)

                    # Validate and get confidence
                    validation = self.validator.validate_supply_tree(
                        supply_tree, manifest
                    )
                    confidence_scores.append(validation.get("confidence", 0.5))
                except Exception as e:
                    self._log_error(f"Error in base matcher: {str(e)}")

        # Finalize matching process
        if supply_trees:
            self.state["status"] = (
                MatchStatus.FULLY_MATCHED
                if len(supply_trees) == len(okh_manifests)
                else MatchStatus.PARTIALLY_MATCHED
            )
            self._log_event(
                f"Matching completed with {len(supply_trees)} supply trees generated"
            )
        else:
            self.state["status"] = MatchStatus.NO_MATCH
            self._log_event("Matching failed to generate any supply trees")

        # Calculate average confidence
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0.0
        )

        # Complete state recording
        self.state["end_time"] = datetime.now()

        return {
            "status": "success" if supply_trees else "no_match",
            "message": (
                f"Generated {len(supply_trees)} supply trees"
                if supply_trees
                else "No matches found"
            ),
            "supply_trees": supply_trees,
            "confidence": avg_confidence,
        }

    def _requirements_to_manifest(
        self, requirements: NormalizedRequirements
    ) -> Optional[OKHManifest]:
        """
        Convert normalized requirements to OKH manifest

        Args:
            requirements: Normalized requirements object

        Returns:
            OKH manifest or None if conversion fails
        """
        # Check if requirements are already in OKH format
        if isinstance(requirements.content, OKHManifest):
            return requirements.content

        # Check if content has required OKH fields
        content = requirements.content
        required_fields = ["name", "version", "function"]

        if not all(field in content for field in required_fields):
            self._log_error(
                f"Missing required OKH fields in requirements: {required_fields}"
            )
            return None

        # Create basic OKH manifest

        # Create license object
        license_obj = License(
            hardware=(
                content.get("license")
                if "license" in content
                else "LicenseRef-NOASSERTION"
            ),
            documentation=(
                content.get("license")
                if "license" in content
                else "LicenseRef-NOASSERTION"
            ),
            software=(
                content.get("license")
                if "license" in content
                else "LicenseRef-NOASSERTION"
            ),
        )

        # Create manifest
        manifest = OKHManifest(
            title=content.get("name", ""),
            repo=content.get("repo", ""),
            version=content.get("version", ""),
            license=license_obj,
            licensor=content.get("licensor", ""),
            documentation_language=content.get("documentation_language", "en"),
            function=content.get("function", ""),
        )

        # Add additional fields if available
        for field in [
            "description",
            "keywords",
            "organization",
            "image",
            "tsdc",
            "manufacturing_processes",
            "tool_list",
        ]:
            if field in content:
                setattr(manifest, field, content[field])

        # Add materials
        if "materials" in content:
            materials = []
            for mat in content["materials"]:
                if isinstance(mat, dict):
                    material = MaterialSpec(
                        material_id=mat.get("material_id", ""),
                        name=mat.get("name", ""),
                        quantity=mat.get("quantity"),
                        unit=mat.get("unit"),
                        notes=mat.get("notes", ""),
                    )
                    materials.append(material)
                elif isinstance(mat, str):
                    material = MaterialSpec(material_id=mat, name=mat)
                    materials.append(material)

            manifest.materials = materials

        # Add process requirements
        if "process_requirements" in content:
            process_reqs = []
            for req in content["process_requirements"]:
                if isinstance(req, dict):
                    process_req = ProcessRequirement(
                        process_name=req.get("process_name", ""),
                        parameters=req.get("parameters", {}),
                        validation_criteria=req.get("validation_criteria", {}),
                        required_tools=req.get("required_tools", []),
                        notes=req.get("notes", ""),
                    )
                    process_reqs.append(process_req)

            # Add to manufacturing specs if available
            if (
                hasattr(manifest, "manufacturing_specs")
                and manifest.manufacturing_specs
            ):
                manifest.manufacturing_specs.process_requirements = process_reqs
            else:
                manifest.manufacturing_specs = ManufacturingSpec(
                    process_requirements=process_reqs
                )

        # Add parts
        if "parts" in content:
            parts = []
            for part_data in content["parts"]:
                if isinstance(part_data, dict):
                    part = PartSpec(
                        name=part_data.get("name", ""),
                        source=part_data.get("source", []),
                        export=part_data.get("export", []),
                        auxiliary=part_data.get("auxiliary", []),
                        image=part_data.get("image"),
                        tsdc=part_data.get("tsdc", []),
                        material=part_data.get("material"),
                        outer_dimensions=part_data.get("outer_dimensions"),
                    )

                    # Add manufacturing params if available
                    if "manufacturing_params" in part_data:
                        part.manufacturing_params = part_data["manufacturing_params"]

                    parts.append(part)

            manifest.parts = parts

        return manifest

    def _capabilities_to_facility(self, capabilities: NormalizedCapabilities) -> Any:
        """
        Convert normalized capabilities to manufacturing facility

        Args:
            capabilities: Normalized capabilities object

        Returns:
            Manufacturing facility object or None if conversion fails
        """
        # For now, we'll use a simplified approach and return capability content
        # This would be replaced with proper OKW conversion in a full implementation
        content = capabilities.content

        # Create simplified facility object with required fields for matching
        facility = type("Facility", (), {})()

        # Set basic properties
        facility.name = content.get("name", "")
        facility.id = content.get("id", "")
        facility.equipment = []
        facility.processes = content.get("processes", [])

        # Add equipment
        if "equipment" in content:
            for equip in content["equipment"]:
                # Create equipment object
                equipment = type("Equipment", (), {})()

                # Set properties
                equipment.equipment_type = equip.get("type", "")
                equipment.manufacturing_process = equip.get("processes", [])
                equipment.materials_worked = equip.get("materials", [])

                # Add to facility
                facility.equipment.append(equipment)

        return facility

    def _prepare_module_requirements(
        self, okh_manifests: List[OKHManifest]
    ) -> Dict[str, List]:
        """
        Prepare requirements for each matching module

        Args:
            okh_manifests: List of OKH manifests

        Returns:
            Dictionary mapping module names to their required input formats
        """
        module_requirements = {}

        # Convert manifests to module-specific requirements
        for module in self._initialized_modules:
            module_name = module.__class__.__name__

            # Different modules might need different formats
            if module_name.endswith("ExactModule"):
                # For exact matching, use process requirements directly
                requirements = []
                for manifest in okh_manifests:
                    requirements.extend(self._extract_exact_requirements(manifest))
                module_requirements[module_name] = requirements

            elif module_name.endswith("HeuristicModule"):
                # For heuristic matching, include substitution rules
                requirements = []
                for manifest in okh_manifests:
                    requirements.extend(self._extract_heuristic_requirements(manifest))
                module_requirements[module_name] = requirements

            elif module_name.endswith("NLPModule"):
                # For NLP matching, include text descriptions
                requirements = []
                for manifest in okh_manifests:
                    requirements.extend(self._extract_nlp_requirements(manifest))
                module_requirements[module_name] = requirements

            elif module_name.endswith("MLModule"):
                # For ML matching, include all metadata
                requirements = []
                for manifest in okh_manifests:
                    requirements.extend(self._extract_ml_requirements(manifest))
                module_requirements[module_name] = requirements

            else:
                # Default fallback - use OKH requirements
                requirements = []
                for manifest in okh_manifests:
                    process_reqs = manifest.extract_requirements()
                    requirements.extend([OKHRequirement(req) for req in process_reqs])
                module_requirements[module_name] = requirements

        return module_requirements

    def _prepare_module_capabilities(self, facilities: List) -> Dict[str, List]:
        """
        Prepare capabilities for each matching module

        Args:
            facilities: List of manufacturing facilities

        Returns:
            Dictionary mapping module names to their required input formats
        """
        module_capabilities = {}

        # Convert facilities to module-specific capabilities
        for module in self._initialized_modules:
            module_name = module.__class__.__name__

            # Different modules might need different formats
            if module_name.endswith("ExactModule"):
                # For exact matching, use equipment capabilities directly
                capabilities = []
                for facility in facilities:
                    capabilities.extend(self._extract_exact_capabilities(facility))
                module_capabilities[module_name] = capabilities

            elif module_name.endswith("HeuristicModule"):
                # For heuristic matching, include substitution rules
                capabilities = []
                for facility in facilities:
                    capabilities.extend(self._extract_heuristic_capabilities(facility))
                module_capabilities[module_name] = capabilities

            elif module_name.endswith("NLPModule"):
                # For NLP matching, include text descriptions
                capabilities = []
                for facility in facilities:
                    capabilities.extend(self._extract_nlp_capabilities(facility))
                module_capabilities[module_name] = capabilities

            elif module_name.endswith("MLModule"):
                # For ML matching, include all metadata
                capabilities = []
                for facility in facilities:
                    capabilities.extend(self._extract_ml_capabilities(facility))
                module_capabilities[module_name] = capabilities

            else:
                # Default fallback - use direct capabilities
                capabilities = []
                for facility in facilities:
                    # Add equipment capabilities
                    if hasattr(facility, "equipment"):
                        for equipment in facility.equipment:
                            capability = Capability(
                                name=getattr(equipment, "equipment_type", ""),
                                type=getattr(equipment, "equipment_type", ""),
                                parameters={
                                    "processes": getattr(
                                        equipment, "manufacturing_process", []
                                    ),
                                    "materials": getattr(
                                        equipment, "materials_worked", []
                                    ),
                                },
                                limitations={},
                            )
                            capabilities.append(capability)

                    # Add process capabilities
                    if hasattr(facility, "processes"):
                        for process in facility.processes:
                            capability = Capability(
                                name=process,
                                type=process,
                                parameters={},
                                limitations={},
                            )
                            capabilities.append(capability)

                module_capabilities[module_name] = capabilities

        return module_capabilities

    # Helper methods for extracting module-specific formats
    def _extract_exact_requirements(self, manifest: OKHManifest) -> List:
        """Extract requirements for exact matching"""
        requirements = []
        process_reqs = manifest.extract_requirements()
        requirements.extend([OKHRequirement(req) for req in process_reqs])

        return requirements

    def _extract_heuristic_requirements(self, manifest: OKHManifest) -> List:
        """Extract requirements for heuristic matching"""
        # For now, use same as exact matching
        return self._extract_exact_requirements(manifest)

    def _extract_nlp_requirements(self, manifest: OKHManifest) -> List:
        """Extract requirements for NLP matching"""
        # For now, use same as exact matching
        return self._extract_exact_requirements(manifest)

    def _extract_ml_requirements(self, manifest: OKHManifest) -> List:
        """Extract requirements for ML matching"""
        # For now, use same as exact matching
        return self._extract_exact_requirements(manifest)

    def _extract_exact_capabilities(self, facility) -> List:
        """Extract capabilities for exact matching"""
        capabilities = []

        # Add equipment capabilities
        if hasattr(facility, "equipment"):
            for equipment in facility.equipment:
                capability = Capability(
                    name=getattr(equipment, "equipment_type", ""),
                    type=getattr(equipment, "equipment_type", ""),
                    parameters={
                        "processes": getattr(equipment, "manufacturing_process", []),
                        "materials": getattr(equipment, "materials_worked", []),
                    },
                    limitations={},
                )
                capabilities.append(capability)

        # Add process capabilities
        if hasattr(facility, "processes"):
            for process in facility.processes:
                capability = Capability(
                    name=process, type=process, parameters={}, limitations={}
                )
                capabilities.append(capability)

        return capabilities

    def _extract_heuristic_capabilities(self, facility) -> List:
        """Extract capabilities for heuristic matching"""
        # For now, use same as exact matching
        return self._extract_exact_capabilities(facility)

    def _extract_nlp_capabilities(self, facility) -> List:
        """Extract capabilities for NLP matching"""
        # For now, use same as exact matching
        return self._extract_exact_capabilities(facility)

    def _extract_ml_capabilities(self, facility) -> List:
        """Extract capabilities for ML matching"""
        # For now, use same as exact matching
        return self._extract_exact_capabilities(facility)
