from uuid import uuid4
from typing import List, Optional
from src.core.models.base.base_types import (
    BaseMatcher, Requirement, Capability, MatchResult, NormalizedRequirements, NormalizedCapabilities
)
from src.core.models.supply_trees import SupplyTree

class CookingMatcher(BaseMatcher):
    """Matcher for cooking domain - simplified version without workflows"""
    
    def match(self, 
             requirements: List[Requirement],
             capabilities: List[Capability]) -> MatchResult:
        """
        Match requirements against capabilities.
        
        This is a simplified implementation that performs basic matching
        for cooking domain requirements (ingredients, tools, techniques).
        
        Args:
            requirements: List of requirements to match
            capabilities: List of capabilities to match against
            
        Returns:
            MatchResult with matched capabilities and confidence
        """
        matched_capabilities = {}
        missing_requirements = []
        substitutions = []
        
        for req in requirements:
            matched = False
            for cap in capabilities:
                if self._can_satisfy(req, cap):
                    matched_capabilities[req] = cap
                    matched = True
                    break
            
            if not matched:
                missing_requirements.append(req)
        
        # Calculate confidence
        total = len(requirements)
        matched_count = len(matched_capabilities)
        confidence = matched_count / total if total > 0 else 0.0
        
        return MatchResult(
            confidence=confidence,
            matched_capabilities=matched_capabilities,
            missing_requirements=missing_requirements,
            substitutions=substitutions
        )
    
    def _can_satisfy(self, requirement: Requirement, capability: Capability) -> bool:
        """Check if capability can satisfy requirement."""
        # Simple name matching for now
        # Can be enhanced with more sophisticated matching logic
        return requirement.name.lower() == capability.name.lower()
    
    def generate_supply_tree(self, requirements: 'NormalizedRequirements', 
                        capabilities: 'NormalizedCapabilities',
                        kitchen_name: str = "Cooking Facility",
                        recipe_name: str = "cooking_recipe") -> SupplyTree:
        """Generate a simplified cooking supply tree"""
        # Create simplified supply tree using the factory method
        # Note: This is a simplified version that doesn't create complex workflows
        
        # Extract basic information from requirements and capabilities
        steps = requirements.content.get("steps", [])
        ingredients = requirements.content.get("ingredients", [])
        tools = requirements.content.get("tools", [])
        
        # Get kitchen capabilities
        available_ingredients = capabilities.content.get("available_ingredients", [])
        available_tools = capabilities.content.get("available_tools", [])
        appliances = capabilities.content.get("appliances", [])
        
        # Calculate confidence based on capability matching
        # Check ingredient overlap
        ingredient_overlap = set(ingredients) & set(available_ingredients)
        ingredient_score = len(ingredient_overlap) / len(ingredients) if ingredients else 0.0
        
        # Check tool availability
        tool_overlap = set(tools) & set(available_tools)
        tool_score = len(tool_overlap) / len(tools) if tools else 0.0
        
        # Overall confidence (weighted average)
        confidence_score = (ingredient_score * 0.6 + tool_score * 0.4)
        
        # Create simplified supply tree
        supply_tree = SupplyTree(
            facility_name=kitchen_name,
            okh_reference=recipe_name,
            confidence_score=confidence_score,
            materials_required=list(ingredients),
            capabilities_used=list(available_tools) + list(appliances),
            match_type="cooking",
            metadata={
                "domain": "cooking",
                "step_count": len(steps),
                "ingredient_count": len(ingredients),
                "tool_count": len(tools),
                "ingredient_overlap": len(ingredient_overlap),
                "tool_overlap": len(tool_overlap),
                "generation_method": "simplified_cooking_matcher"
            }
        )
        
        return supply_tree