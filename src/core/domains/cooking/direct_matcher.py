"""
Cooking Domain Direct Matcher

This module implements the CookingDirectMatcher for the cooking domain,
providing specialized direct matching for ingredients, equipment, and techniques.
"""

import re
from typing import List, Dict, Any, Set
from ...matching.direct_matcher import DirectMatcher
from ...matching.layers.base import MatchingResult, MatchMetadata, MatchQuality


class CookingDirectMatcher(DirectMatcher):
    """Direct matcher specialized for cooking domain with ingredient/equipment/technique matching."""
    
    def __init__(self, near_miss_threshold: int = 2):
        """
        Initialize the cooking direct matcher.
        
        Args:
            near_miss_threshold: Maximum character differences to consider as near-miss
        """
        super().__init__(domain="cooking", near_miss_threshold=near_miss_threshold)
        
        # Cooking-specific confidence adjustments
        self._ingredient_keywords = self._load_ingredient_keywords()
        self._equipment_keywords = self._load_equipment_keywords()
        self._technique_keywords = self._load_technique_keywords()
        self._measurement_units = self._load_measurement_units()
    
    def _load_ingredient_keywords(self) -> Set[str]:
        """Load common ingredient keywords for confidence adjustments."""
        return {
            "flour", "sugar", "salt", "pepper", "butter", "oil", "garlic", "onion",
            "tomato", "cheese", "milk", "egg", "eggs", "chicken", "beef", "pork",
            "fish", "rice", "pasta", "bread", "herbs", "spices", "vegetables",
            "fruits", "nuts", "seeds", "cream", "yogurt", "honey", "vinegar",
            "soy sauce", "olive oil", "coconut oil", "sesame oil", "lemon",
            "lime", "ginger", "basil", "oregano", "thyme", "rosemary", "parsley",
            "cilantro", "mint", "chives", "dill", "sage", "bay leaves"
        }
    
    def _load_equipment_keywords(self) -> Set[str]:
        """Load common cooking equipment keywords for confidence adjustments."""
        return {
            "knife", "cutting board", "pan", "pot", "skillet", "wok", "oven",
            "stove", "microwave", "blender", "food processor", "mixer", "whisk",
            "spatula", "tongs", "ladle", "spoon", "fork", "grater", "peeler",
            "measuring cup", "measuring spoon", "scale", "thermometer", "timer",
            "baking sheet", "muffin tin", "cake pan", "loaf pan", "casserole dish",
            "dutch oven", "slow cooker", "pressure cooker", "grill", "toaster",
            "coffee maker", "tea kettle", "colander", "strainer", "sieve"
        }
    
    def _load_technique_keywords(self) -> Set[str]:
        """Load common cooking technique keywords for confidence adjustments."""
        return {
            "chop", "dice", "mince", "slice", "grate", "peel", "cut", "trim",
            "saute", "fry", "deep fry", "stir fry", "boil", "simmer", "steam",
            "bake", "roast", "grill", "broil", "braise", "stew", "poach",
            "blanch", "sear", "caramelize", "reduce", "thicken", "emulsify",
            "whisk", "beat", "fold", "knead", "mix", "stir", "combine",
            "marinate", "season", "taste", "adjust", "garnish", "plate"
        }
    
    def _load_measurement_units(self) -> Set[str]:
        """Load common measurement units for confidence adjustments."""
        return {
            "cup", "cups", "tablespoon", "tablespoons", "tbsp", "tsp", "teaspoon",
            "teaspoons", "ounce", "ounces", "oz", "pound", "pounds", "lb", "lbs",
            "gram", "grams", "g", "kilogram", "kilograms", "kg", "milliliter",
            "milliliters", "ml", "liter", "liters", "l", "pint", "pints", "pt",
            "quart", "quarts", "qt", "gallon", "gallons", "gal", "pinch", "dash",
            "handful", "bunch", "clove", "cloves", "slice", "slices", "piece",
            "pieces", "can", "cans", "bottle", "bottles", "package", "packages"
        }
    
    def get_domain_specific_confidence_adjustments(self, requirement: str, capability: str) -> float:
        """
        Get cooking-specific confidence adjustments based on domain knowledge.
        
        Args:
            requirement: The requirement string
            capability: The capability string
            
        Returns:
            Confidence adjustment factor (0.0 to 1.0)
        """
        # Start with base confidence
        adjustment = 1.0
        
        # Check for cooking-specific patterns that increase confidence
        req_lower = requirement.lower()
        cap_lower = capability.lower()
        
        # Ingredient matching gets slight boost
        if self._contains_ingredient_keywords(req_lower) and self._contains_ingredient_keywords(cap_lower):
            adjustment += 0.05
        
        # Equipment matching gets slight boost
        if self._contains_equipment_keywords(req_lower) and self._contains_equipment_keywords(cap_lower):
            adjustment += 0.05
        
        # Technique matching gets slight boost
        if self._contains_technique_keywords(req_lower) and self._contains_technique_keywords(cap_lower):
            adjustment += 0.05
        
        # Measurement units matching gets slight boost
        if self._contains_measurement_units(req_lower) and self._contains_measurement_units(cap_lower):
            adjustment += 0.03
        
        # Penalty for obvious mismatches (e.g., ingredient vs equipment)
        if (self._contains_ingredient_keywords(req_lower) and self._contains_equipment_keywords(cap_lower)) or \
           (self._contains_equipment_keywords(req_lower) and self._contains_ingredient_keywords(cap_lower)):
            adjustment -= 0.1
        
        # Ensure adjustment stays within bounds
        return max(0.0, min(1.0, adjustment))
    
    def _contains_ingredient_keywords(self, text: str) -> bool:
        """Check if text contains ingredient keywords."""
        return any(keyword in text for keyword in self._ingredient_keywords)
    
    def _contains_equipment_keywords(self, text: str) -> bool:
        """Check if text contains equipment keywords."""
        return any(keyword in text for keyword in self._equipment_keywords)
    
    def _contains_technique_keywords(self, text: str) -> bool:
        """Check if text contains technique keywords."""
        return any(keyword in text for keyword in self._technique_keywords)
    
    def _contains_measurement_units(self, text: str) -> bool:
        """Check if text contains measurement unit keywords."""
        return any(keyword in text for keyword in self._measurement_units)
    
    def match_ingredients(self, required_ingredients: List[str], available_ingredients: List[str]) -> List[MatchingResult]:
        """
        Match required ingredients against available ingredients.
        
        Args:
            required_ingredients: List of required ingredient strings
            available_ingredients: List of available ingredient strings
            
        Returns:
            List of MatchingResult objects for ingredient matches
        """
        results = []
        for required in required_ingredients:
            ingredient_results = self.match(required, available_ingredients)
            # Add ingredient-specific metadata
            for result in ingredient_results:
                result.metadata.reasons.append("Ingredient matching")
                # Apply domain-specific confidence adjustment
                domain_adjustment = self.get_domain_specific_confidence_adjustments(
                    result.requirement, result.capability)
                result.confidence *= domain_adjustment
                result.metadata.confidence = result.confidence
            results.extend(ingredient_results)
        return results
    
    def match_equipment(self, required_equipment: List[str], available_equipment: List[str]) -> List[MatchingResult]:
        """
        Match required equipment against available equipment.
        
        Args:
            required_equipment: List of required equipment strings
            available_equipment: List of available equipment strings
            
        Returns:
            List of MatchingResult objects for equipment matches
        """
        results = []
        for required in required_equipment:
            equipment_results = self.match(required, available_equipment)
            # Add equipment-specific metadata
            for result in equipment_results:
                result.metadata.reasons.append("Equipment matching")
                # Apply domain-specific confidence adjustment
                domain_adjustment = self.get_domain_specific_confidence_adjustments(
                    result.requirement, result.capability)
                result.confidence *= domain_adjustment
                result.metadata.confidence = result.confidence
            results.extend(equipment_results)
        return results
    
    def match_techniques(self, required_techniques: List[str], available_techniques: List[str]) -> List[MatchingResult]:
        """
        Match required techniques against available techniques.
        
        Args:
            required_techniques: List of required technique strings
            available_techniques: List of available technique strings
            
        Returns:
            List of MatchingResult objects for technique matches
        """
        results = []
        for required in required_techniques:
            technique_results = self.match(required, available_techniques)
            # Add technique-specific metadata
            for result in technique_results:
                result.metadata.reasons.append("Technique matching")
                # Apply domain-specific confidence adjustment
                domain_adjustment = self.get_domain_specific_confidence_adjustments(
                    result.requirement, result.capability)
                result.confidence *= domain_adjustment
                result.metadata.confidence = result.confidence
            results.extend(technique_results)
        return results
    
    def match_recipe_requirements(self, recipe_data: Dict[str, Any], kitchen_capabilities: Dict[str, Any]) -> Dict[str, List[MatchingResult]]:
        """
        Match all recipe requirements against kitchen capabilities.
        
        Args:
            recipe_data: Recipe data containing ingredients, equipment, and techniques
            kitchen_capabilities: Kitchen capabilities containing available items
            
        Returns:
            Dictionary with match results for each category
        """
        results = {
            "ingredients": [],
            "equipment": [],
            "techniques": []
        }
        
        # Extract requirements from recipe data
        required_ingredients = recipe_data.get("ingredients", [])
        required_equipment = recipe_data.get("equipment", [])
        required_techniques = recipe_data.get("techniques", [])
        
        # Extract capabilities from kitchen data
        available_ingredients = kitchen_capabilities.get("available_ingredients", [])
        available_equipment = kitchen_capabilities.get("available_equipment", [])
        available_techniques = kitchen_capabilities.get("available_techniques", [])
        
        # Perform matching for each category
        if required_ingredients and available_ingredients:
            results["ingredients"] = self.match_ingredients(required_ingredients, available_ingredients)
        
        if required_equipment and available_equipment:
            results["equipment"] = self.match_equipment(required_equipment, available_equipment)
        
        if required_techniques and available_techniques:
            results["techniques"] = self.match_techniques(required_techniques, available_techniques)
        
        return results
