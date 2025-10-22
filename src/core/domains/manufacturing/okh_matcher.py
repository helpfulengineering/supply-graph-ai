from typing import List, Dict, Any, Optional
from uuid import uuid4

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
        """Check if a capability can be a substitute for a requirement"""
        # Check if capability is a known substitute
        if 'substitutes_for' in capability.parameters and requirement.name in capability.parameters['substitutes_for']:
            return True
            
        # TODO: Add more sophisticated substitution rules
        return False
    
    def _create_substitution(self, 
                          requirement: OKHRequirement,
                          capability: Capability) -> Any:
        """Create a substitution record"""        
        confidence = 0.7  # Default confidence for substitutions
        
        # Adjust confidence based on substitute metadata
        if 'substitutes_for' in capability.parameters and requirement.name in capability.parameters['substitutes_for']:
            if isinstance(capability.parameters['substitutes_for'], dict) and 'confidence' in capability.parameters['substitutes_for'][requirement.name]:
                confidence = capability.parameters['substitutes_for'][requirement.name]['confidence']
        
        return Substitution(
            original=requirement,
            substitute=capability,
            confidence=confidence,
            constraints=capability.limitations,
            notes=f"Substitute {capability.name} for {requirement.name}"
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