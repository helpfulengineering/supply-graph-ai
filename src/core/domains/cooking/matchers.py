from uuid import uuid4
from src.core.models.base.base_types import NormalizedRequirements, NormalizedCapabilities
from src.core.models.supply_trees import SupplyTree

class CookingMatcher:
    """Matcher for cooking domain - simplified version without workflows"""
    
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