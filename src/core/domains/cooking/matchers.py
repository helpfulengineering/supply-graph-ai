from uuid import uuid4
from src.core.models.base.base_types import NormalizedRequirements, NormalizedCapabilities
from src.core.models.supply_trees import SupplyTree

class CookingMatcher:
    """Matcher for cooking domain - simplified version without workflows"""
    
    def generate_supply_tree(self, requirements: 'NormalizedRequirements', 
                        capabilities: 'NormalizedCapabilities') -> SupplyTree:
        """Generate a simplified cooking supply tree"""
        # Create simplified supply tree using the factory method
        # Note: This is a simplified version that doesn't create complex workflows
        
        # Extract basic information from requirements and capabilities
        steps = requirements.content.get("steps", [])
        kitchen_capabilities = capabilities.content.get("capabilities", [])
        
        # Calculate confidence based on capability matching
        confidence_score = 0.8  # Default confidence for cooking domain
        
        # Create simplified supply tree
        supply_tree = SupplyTree(
            facility_id=uuid4(),  # Generate a temporary facility ID for cooking
            facility_name="Cooking Facility",
            okh_reference="cooking_recipe",
            confidence_score=confidence_score,
            materials_required=[step for step in steps if isinstance(step, str)],
            capabilities_used=kitchen_capabilities,
            match_type="cooking",
            metadata={
                "domain": "cooking",
                "step_count": len(steps),
                "capability_count": len(kitchen_capabilities),
                "generation_method": "simplified_cooking_matcher"
            }
        )
        
        return supply_tree