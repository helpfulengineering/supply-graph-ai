from typing import List, Dict, Any, Optional
from uuid import uuid4
import re

from src.core.models.base.base_types import BaseMatcher, Requirement, Capability, MatchResult, ResourceType, Substitution
from src.core.models.supply_trees import SupplyTree
from src.core.models.okh import OKHManifest, ProcessRequirement

class OKHRequirement(Requirement):
    """OKH-specific requirement implementation"""
    
    def __init__(self, process_req: ProcessRequirement):
        super().__init__(
            name=process_req.process_name,
            type="process",
            parameters=process_req.parameters,
            constraints=process_req.validation_criteria
        )
        self.process_requirement = process_req
        self.required_tools = process_req.required_tools

class OKHMatcher(BaseMatcher):
    """Implementation of BaseMatcher for OKH data"""
    
    def match(self, 
             requirements: List[Requirement],
             capabilities: List[Capability]) -> MatchResult:
        """Match OKH requirements against capabilities"""
        matched_capabilities = {}
        missing_requirements = []
        substitutions = []
        
        for req in requirements:
            # Skip non-OKH requirements
            if not isinstance(req, OKHRequirement):
                continue
                
            # Find matching capability
            matched = False
            for capability in capabilities:
                # Check if capability can satisfy requirement
                if self._can_satisfy(req, capability):
                    matched_capabilities[req] = capability
                    matched = True
                    break
                    
                # Check for possible substitution
                elif self._can_substitute(req, capability):
                    substitution = self._create_substitution(req, capability)
                    substitutions.append(substitution)
            
            # Add to missing if not matched
            if not matched:
                missing_requirements.append(req)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(
            matched_capabilities, 
            missing_requirements,
            substitutions,
            len(requirements)
        )
        
        return MatchResult(
            confidence=confidence,
            matched_capabilities=matched_capabilities,
            missing_requirements=missing_requirements,
            substitutions=substitutions
        )
    
    def generate_supply_tree(self, 
                           okh_manifest: OKHManifest,
                           capabilities: List[Capability]) -> SupplyTree:
        """Generate a simplified SupplyTree from OKH manifest and capabilities"""
        # Extract process requirements and convert to OKHRequirements
        process_reqs = okh_manifest.extract_requirements()
        requirements = [OKHRequirement(req) for req in process_reqs]
        
        # Match requirements to capabilities
        match_result = self.match(requirements, capabilities)
        
        # Calculate overall confidence based on matching results
        total_confidence = 0.0
        match_count = 0
        materials_required = []
        capabilities_used = []
        
        for req in requirements:
            if req in match_result.matched_capabilities:
                capability = match_result.matched_capabilities[req]
                total_confidence += 1.0
                match_count += 1
                capabilities_used.append(capability.name)
            elif any(sub.original == req for sub in match_result.substitutions):
                # Find substitution
                for sub in match_result.substitutions:
                    if sub.original == req:
                        total_confidence += sub.confidence
                        match_count += 1
                        capabilities_used.append(sub.substitute.name)
                        break
        
        # Calculate average confidence
        confidence_score = total_confidence / len(requirements) if requirements else 0.0
        
        # Extract materials from manifest
        if hasattr(okh_manifest, 'materials') and okh_manifest.materials:
            materials_required = [str(material) for material in okh_manifest.materials]
        
        # Create simplified supply tree
        supply_tree = SupplyTree(
            facility_id=uuid4(),  # Generate a temporary facility ID
            facility_name="Manufacturing Facility",
            okh_reference=str(okh_manifest.id),
            confidence_score=confidence_score,
            materials_required=materials_required,
            capabilities_used=capabilities_used,
            match_type="okh_matcher",
            metadata={
                "okh_title": okh_manifest.title,
                "total_requirements": len(requirements),
                "matched_requirements": match_count,
                "substitution_count": len(match_result.substitutions),
                "generation_method": "simplified_okh_matcher"
            }
        )
        
        return supply_tree
    
    # Note: _add_part_workflows method removed as it used workflow classes that are no longer available
    
    def _find_capability(self, 
                      requirement: OKHRequirement, 
                      capabilities: List[Capability]) -> Optional[Capability]:
        """Find a capability that can satisfy a requirement"""
        for capability in capabilities:
            if self._can_satisfy(requirement, capability):
                return capability
        return None
    
    def _can_satisfy(self, 
                   requirement: OKHRequirement, 
                   capability: Capability) -> bool:
        """Check if a capability can satisfy a requirement"""
        # Check if process name matches capability type
        if requirement.name == capability.type:
            return True
            
        # Check if capability parameters include this process
        if 'processes' in capability.parameters and requirement.name in capability.parameters['processes']:
            return True
            
        return False
    
    def _can_substitute(self, 
                      requirement: OKHRequirement, 
                      capability: Capability) -> bool:
        """
        Check if a capability can be a substitute for a requirement.
        
        Uses multiple factors to determine substitution viability:
        - Explicit substitution declarations
        - Material compatibility
        - Process similarity
        - Tool/equipment compatibility
        - Specification matching
        
        Args:
            requirement: The requirement to find substitute for
            capability: The capability to check as substitute
            
        Returns:
            True if capability can substitute for requirement
        """
        # Check explicit substitution declaration (highest priority)
        if 'substitutes_for' in capability.parameters:
            substitutes = capability.parameters['substitutes_for']
            if isinstance(substitutes, list) and requirement.name in substitutes:
                return True
            elif isinstance(substitutes, dict) and requirement.name in substitutes:
                return True
            elif isinstance(substitutes, str) and requirement.name == substitutes:
                return True
        
        # Check material compatibility
        if self._check_material_compatibility(requirement, capability):
            return True
        
        # Check process similarity
        if self._check_process_similarity(requirement, capability):
            return True
        
        # Check tool/equipment compatibility
        if self._check_tool_compatibility(requirement, capability):
            return True
        
        # Check specification matching
        if self._check_specification_match(requirement, capability):
            return True
        
        return False
    
    def _create_substitution(self, 
                          requirement: OKHRequirement,
                          capability: Capability) -> Any:
        """Create a substitution record with confidence scoring"""
        # Start with base confidence
        confidence = 0.7
        
        # Boost confidence for explicit substitution
        if 'substitutes_for' in capability.parameters:
            confidence = 0.9
        
        # Adjust based on matching factors
        factors_matched = 0
        if self._check_material_compatibility(requirement, capability):
            factors_matched += 1
        if self._check_process_similarity(requirement, capability):
            factors_matched += 1
        if self._check_tool_compatibility(requirement, capability):
            factors_matched += 1
        if self._check_specification_match(requirement, capability):
            factors_matched += 1
        
        # Increase confidence based on number of matching factors
        if factors_matched >= 3:
            confidence = min(0.95, confidence + 0.15)
        elif factors_matched >= 2:
            confidence = min(0.90, confidence + 0.10)
        elif factors_matched >= 1:
            confidence = min(0.85, confidence + 0.05)
        
        # Use explicit confidence if provided
        if 'substitutes_for' in capability.parameters:
            substitutes = capability.parameters['substitutes_for']
            if isinstance(substitutes, dict) and requirement.name in substitutes:
                if 'confidence' in substitutes[requirement.name]:
                    confidence = substitutes[requirement.name]['confidence']
        
        return Substitution(
            original=requirement,
            substitute=capability,
            confidence=confidence,
            constraints=capability.limitations,
            notes=f"Substitute {capability.name} for {requirement.name} (matched {factors_matched} factors)"
        )
    
    def _calculate_confidence(self, 
                           matched: Dict[Requirement, Capability],
                           missing: List[Requirement],
                           substitutions: List[Any],
                           total_count: int) -> float:
        """Calculate overall match confidence"""
        if total_count == 0:
            return 0.0
            
        # Weight exact matches higher than substitutions
        exact_matches = len(matched)
        sub_matches = len(substitutions)
        
        # Calculate weighted match ratio
        weighted_matches = exact_matches + 0.7 * sub_matches
        
        # Calculate base confidence from match ratio
        base_confidence = weighted_matches / total_count
        
        # Adjust confidence based on missing critical requirements
        if missing:
            # Check if any missing requirements are critical
            critical_missing = any(req.is_required for req in missing)
            if critical_missing:
                # Reduce confidence significantly for missing critical requirements
                base_confidence *= 0.5
        
        return base_confidence
    
    def _check_material_compatibility(self, requirement: OKHRequirement, capability: Capability) -> bool:
        """
        Check if materials are compatible for substitution.
        
        Args:
            requirement: Requirement with material specifications
            capability: Capability with material capabilities
            
        Returns:
            True if materials are compatible
        """
        # Extract materials from requirement
        req_materials = self._extract_materials(requirement)
        if not req_materials:
            return False
        
        # Extract materials from capability
        cap_materials = self._extract_materials(capability)
        if not cap_materials:
            return False
        
        # Check for compatible material types
        # Material compatibility rules (can be extended)
        material_compatibility = {
            # Steel types
            "steel": {"stainless_steel", "carbon_steel", "alloy_steel"},
            "stainless_steel": {"steel", "stainless_steel_304", "stainless_steel_316"},
            "carbon_steel": {"steel", "mild_steel"},
            
            # Aluminum types
            "aluminum": {"aluminum_6061", "aluminum_7075", "aluminum_alloy"},
            "aluminum_6061": {"aluminum", "aluminum_alloy"},
            
            # Plastic types
            "plastic": {"abs", "pla", "petg", "nylon"},
            "abs": {"plastic", "thermoplastic"},
            "pla": {"plastic", "bioplastic"},
        }
        
        for req_mat in req_materials:
            req_mat_lower = req_mat.lower().replace(" ", "_")
            for cap_mat in cap_materials:
                cap_mat_lower = cap_mat.lower().replace(" ", "_")
                
                # Exact match
                if req_mat_lower == cap_mat_lower:
                    return True
                
                # Check compatibility mapping
                if req_mat_lower in material_compatibility:
                    if cap_mat_lower in material_compatibility[req_mat_lower]:
                        return True
                
                # Check reverse mapping
                if cap_mat_lower in material_compatibility:
                    if req_mat_lower in material_compatibility[cap_mat_lower]:
                        return True
        
        return False
    
    def _check_process_similarity(self, requirement: OKHRequirement, capability: Capability) -> bool:
        """
        Check if processes are similar enough for substitution.
        
        Args:
            requirement: Requirement with process specifications
            capability: Capability with process capabilities
            
        Returns:
            True if processes are similar
        """
        req_process = requirement.name.lower() if requirement.name else ""
        cap_process = capability.name.lower() if capability.name else ""
        
        if not req_process or not cap_process:
            return False
        
        # Process similarity groups
        process_groups = {
            "machining": {"milling", "turning", "drilling", "cnc_machining", "machining"},
            "milling": {"cnc_milling", "manual_milling", "machining"},
            "turning": {"cnc_turning", "manual_turning", "lathe", "machining"},
            "3d_printing": {"fdm", "sla", "sls", "additive_manufacturing", "3d_printing"},
            "cutting": {"laser_cutting", "waterjet_cutting", "plasma_cutting", "cutting"},
            "welding": {"tig_welding", "mig_welding", "arc_welding", "welding"},
        }
        
        # Normalize process names (remove common suffixes)
        def normalize_process_name(name: str) -> str:
            """Remove common suffixes from process names."""
            suffixes = ["_capability", "_service", "_process"]
            for suffix in suffixes:
                if name.endswith(suffix):
                    return name[:-len(suffix)]
            return name
        
        req_normalized = normalize_process_name(req_process)
        cap_normalized = normalize_process_name(cap_process)
        
        # Check if processes are in same group
        for group, processes in process_groups.items():
            # Check both original and normalized names
            req_in_group = req_process in processes or req_normalized in processes
            cap_in_group = cap_process in processes or cap_normalized in processes
            if req_in_group and cap_in_group:
                return True
        
        # Check for substring matches (e.g., "cnc_milling" contains "milling")
        # Only check if one process name contains the other (not normalized versions)
        if req_process in cap_process or cap_process in req_process:
            return True
        # Also check normalized versions against each other
        if req_normalized in cap_normalized or cap_normalized in req_normalized:
            # But only if they're not the same (avoid false positives)
            if req_normalized != cap_normalized:
                return True
        
        return False
    
    def _check_tool_compatibility(self, requirement: OKHRequirement, capability: Capability) -> bool:
        """
        Check if tools/equipment are compatible.
        
        Args:
            requirement: Requirement with tool specifications
            capability: Capability with tool capabilities
            
        Returns:
            True if tools are compatible
        """
        req_tools = requirement.required_tools or []
        if not req_tools:
            return False
        
        # Extract tools from capability
        cap_tools = []
        if 'tools' in capability.parameters:
            cap_tools = capability.parameters['tools']
            if isinstance(cap_tools, str):
                cap_tools = [cap_tools]
        elif 'equipment' in capability.parameters:
            cap_tools = capability.parameters['equipment']
            if isinstance(cap_tools, str):
                cap_tools = [cap_tools]
        
        if not cap_tools:
            return False
        
        # Check for tool matches
        for req_tool in req_tools:
            req_tool_lower = req_tool.lower()
            for cap_tool in cap_tools:
                cap_tool_lower = str(cap_tool).lower()
                
                # Exact or substring match
                if req_tool_lower in cap_tool_lower or cap_tool_lower in req_tool_lower:
                    return True
        
        return False
    
    def _check_specification_match(self, requirement: OKHRequirement, capability: Capability) -> bool:
        """
        Check if specifications match closely enough for substitution.
        
        Args:
            requirement: Requirement with specifications
            capability: Capability with specifications
            
        Returns:
            True if specifications match closely
        """
        # Extract specifications from requirement
        req_specs = requirement.parameters or {}
        
        # Extract specifications from capability
        cap_specs = capability.parameters or {}
        
        # Check for tolerance matching
        if 'tolerance' in req_specs and 'tolerance' in cap_specs:
            req_tol = self._parse_tolerance(req_specs['tolerance'])
            cap_tol = self._parse_tolerance(cap_specs['tolerance'])
            
            if req_tol and cap_tol:
                # Capability tolerance should be equal or better (smaller)
                if cap_tol <= req_tol:
                    return True
        
        # Check for dimension matching (within reasonable range)
        if 'dimensions' in req_specs and 'dimensions' in cap_specs:
            req_dims = req_specs['dimensions']
            cap_dims = cap_specs['dimensions']
            
            if self._dimensions_compatible(req_dims, cap_dims):
                return True
        
        return False
    
    def _extract_materials(self, obj) -> List[str]:
        """Extract material names from requirement or capability."""
        materials = []
        
        if hasattr(obj, 'materials') and obj.materials:
            if isinstance(obj.materials, list):
                materials.extend(obj.materials)
            elif isinstance(obj.materials, str):
                materials.append(obj.materials)
        
        if hasattr(obj, 'parameters') and obj.parameters:
            if 'materials' in obj.parameters:
                mats = obj.parameters['materials']
                if isinstance(mats, list):
                    materials.extend(mats)
                elif isinstance(mats, str):
                    materials.append(mats)
        
        return materials
    
    def _parse_tolerance(self, tolerance_str: str) -> Optional[float]:
        """Parse tolerance string to float value."""
        try:
            # Extract numeric value from tolerance string (e.g., "±0.1mm" -> 0.1)
            match = re.search(r'[\d.]+', str(tolerance_str))
            if match:
                return float(match.group())
        except (ValueError, AttributeError):
            pass
        return None
    
    def _dimensions_compatible(self, req_dims: Any, cap_dims: Any) -> bool:
        """Check if dimensions are compatible (within 10% difference)."""
        try:
            # Simple compatibility check - can be enhanced
            if isinstance(req_dims, dict) and isinstance(cap_dims, dict):
                # Check if key dimensions match
                for key in ['width', 'length', 'height', 'diameter']:
                    if key in req_dims and key in cap_dims:
                        req_val = float(req_dims[key])
                        cap_val = float(cap_dims[key])
                        # Within 10% difference
                        if abs(req_val - cap_val) / max(req_val, cap_val) <= 0.1:
                            return True
        except (ValueError, TypeError, KeyError):
            pass
        return False