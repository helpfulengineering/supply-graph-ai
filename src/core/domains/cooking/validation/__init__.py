"""
Cooking domain validation components.

This package provides domain-specific validators for the cooking domain
that integrate with the new validation framework.
"""

from .kitchen_validator import CookingKitchenValidator
from .recipe_validator import CookingRecipeValidator

__all__ = ["CookingRecipeValidator", "CookingKitchenValidator"]
