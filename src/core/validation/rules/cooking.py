"""
Cooking domain validation rules.

This module provides validation rules for the cooking domain,
integrating with the existing domain configuration.
"""

from typing import Dict, Any, List
from .base import BaseValidationRules


class CookingValidationRules(BaseValidationRules):
    """Validation rules for cooking domain"""

    def get_supported_quality_levels(self) -> List[str]:
        """Get supported quality levels for cooking domain"""
        return ["home", "commercial", "professional"]

    def get_validation_rules(self, quality_level: str) -> Dict[str, Any]:
        """Get validation rules for a specific quality level"""
        if not self.validate_quality_level(quality_level):
            raise ValueError(
                f"Unsupported quality level '{quality_level}' for cooking domain"
            )

        base_rules = {
            "required_fields": self.get_required_fields(quality_level),
            "optional_fields": self.get_optional_fields(quality_level),
            "validation_strictness": self.get_validation_strictness(quality_level),
            "quality_levels": self.get_supported_quality_levels(),
            "domain": "cooking",
        }

        # Add quality-specific rules
        if quality_level == "home":
            base_rules.update(
                {
                    "allow_approximate_measurements": True,
                    "require_food_safety_certification": False,
                    "require_allergen_info": False,
                }
            )
        elif quality_level == "commercial":
            base_rules.update(
                {
                    "allow_approximate_measurements": False,
                    "require_food_safety_certification": True,
                    "require_allergen_info": True,
                }
            )
        elif quality_level == "professional":
            base_rules.update(
                {
                    "allow_approximate_measurements": False,
                    "require_food_safety_certification": True,
                    "require_allergen_info": True,
                    "require_nutritional_analysis": True,
                    "require_quality_standards": True,
                }
            )

        return base_rules

    def get_required_fields(self, quality_level: str) -> List[str]:
        """Get required fields for a specific quality level"""
        if not self.validate_quality_level(quality_level):
            raise ValueError(
                f"Unsupported quality level '{quality_level}' for cooking domain"
            )

        # Base required fields for all quality levels
        base_fields = ["name", "ingredients", "instructions"]

        if quality_level == "home":
            return base_fields
        elif quality_level == "commercial":
            return base_fields + ["cooking_time", "servings", "allergen_info"]
        elif quality_level == "professional":
            return base_fields + [
                "cooking_time",
                "servings",
                "allergen_info",
                "nutritional_info",
                "food_safety_notes",
            ]

        return base_fields

    def get_optional_fields(self, quality_level: str) -> List[str]:
        """Get optional fields for a specific quality level"""
        if not self.validate_quality_level(quality_level):
            raise ValueError(
                f"Unsupported quality level '{quality_level}' for cooking domain"
            )

        # Base optional fields
        base_optional = [
            "description",
            "prep_time",
            "difficulty_level",
            "cuisine_type",
            "dietary_restrictions",
            "equipment_needed",
            "tips",
            "variations",
        ]

        if quality_level == "home":
            return base_optional + [
                "cooking_time",
                "servings",
                "allergen_info",
                "nutritional_info",
            ]
        elif quality_level == "commercial":
            return base_optional + [
                "nutritional_info",
                "food_safety_notes",
                "cost_analysis",
                "storage_instructions",
                "serving_suggestions",
            ]
        elif quality_level == "professional":
            return base_optional + [
                "cost_analysis",
                "storage_instructions",
                "serving_suggestions",
                "quality_standards",
                "certifications",
                "supplier_info",
            ]

        return base_optional

    @staticmethod
    def get_recipe_validation_rules(quality_level: str = "home") -> Dict[str, Any]:
        """Get recipe validation rules based on quality level (static method for backward compatibility)"""
        rules = CookingValidationRules()
        return rules.get_validation_rules(quality_level)

    @staticmethod
    def get_kitchen_validation_rules(quality_level: str = "home") -> Dict[str, Any]:
        """Get kitchen validation rules based on quality level"""
        base_rules = {
            "required_fields": ["name", "location", "equipment"],
            "equipment_validation": {
                "required_fields": ["name", "type"],
                "optional_fields": ["specifications", "capacity", "features"],
            },
        }

        quality_specific = {
            "home": {
                "required_fields": base_rules["required_fields"],
                "optional_fields": ["description", "capacity", "amenities"],
                "validation_strictness": "relaxed",
            },
            "commercial": {
                "required_fields": base_rules["required_fields"] + ["capacity"],
                "optional_fields": ["description", "amenities", "certifications"],
                "validation_strictness": "standard",
            },
            "professional": {
                "required_fields": base_rules["required_fields"]
                + ["capacity", "certifications"],
                "optional_fields": [
                    "description",
                    "amenities",
                    "food_safety_compliance",
                ],
                "validation_strictness": "strict",
            },
        }

        result = quality_specific.get(quality_level, quality_specific["home"])
        result.update(base_rules)
        return result
