from typing import List

from src.core.models.base.base_types import (
    BaseMatcher,
    Capability,
    MatchResult,
    NormalizedCapabilities,
    NormalizedRequirements,
    Requirement,
)
from src.core.models.supply_trees import SupplyTree


def _fuzzy_match(a: str, b: str) -> bool:
    """Return True if either string is a substring of the other (case-insensitive).

    Handles common real-world mismatches:
    - Plurals: "chocolate chip" ↔ "chocolate chips"
    - Qualifiers: "sugar" ↔ "brown sugar"
    """
    a_l, b_l = a.strip().lower(), b.strip().lower()
    return a_l in b_l or b_l in a_l


def _fuzzy_split(
    original_items: List[str], available_lower: List[str]
) -> "tuple[List[str], List[str]]":
    """Split `original_items` into (matched, missing) against `available_lower`.

    Matching is fuzzy (see `_fuzzy_match`) and case-insensitive; the original
    (non-lowercased) item text is preserved in the output for display, e.g. in
    a match explanation.
    """
    matched: List[str] = []
    missing: List[str] = []
    for item in original_items:
        item_str = item if isinstance(item, str) else str(item)
        if any(_fuzzy_match(item_str, a) for a in available_lower):
            matched.append(item_str)
        else:
            missing.append(item_str)
    return matched, missing


class CookingMatcher(BaseMatcher):
    """Matcher for cooking domain - simplified version without workflows"""

    def match(
        self, requirements: List[Requirement], capabilities: List[Capability]
    ) -> MatchResult:
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
            substitutions=substitutions,
        )

    def _can_satisfy(self, requirement: Requirement, capability: Capability) -> bool:
        """Check if capability can satisfy requirement."""
        # Simple name matching for now
        # Can be enhanced with more sophisticated matching logic
        return requirement.name.lower() == capability.name.lower()

    def generate_supply_tree(
        self,
        requirements: "NormalizedRequirements",
        capabilities: "NormalizedCapabilities",
        kitchen_name: str = "Cooking Facility",
        recipe_name: str = "cooking_recipe",
    ) -> SupplyTree:
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
        # Normalize to lowercase for case-insensitive matching
        ingredients_lower = [
            i.lower() if isinstance(i, str) else str(i).lower() for i in ingredients
        ]
        available_ingredients_lower = [
            i.lower() if isinstance(i, str) else str(i).lower()
            for i in available_ingredients
        ]
        tools_lower = [
            t.lower() if isinstance(t, str) else str(t).lower() for t in tools
        ]
        available_tools_lower = [
            t.lower() if isinstance(t, str) else str(t).lower() for t in available_tools
        ]

        # Include appliances when checking tool availability — a kitchen stores
        # equipment like "Oven" under appliances, while the recipe lists it in
        # tool_list.  Merging both sets gives a more accurate overlap.
        appliances_lower = [
            a.lower() if isinstance(a, str) else str(a).lower() for a in appliances
        ]
        combined_available_tools_lower = list(
            set(available_tools_lower) | set(appliances_lower)
        )

        # Fuzzy ingredient overlap — "sugar" matches "brown sugar", "chocolate chip"
        # matches "chocolate chips", etc.  Plain set intersection is too strict for
        # real-world ingredient lists where names differ by qualifiers or plurals.
        matched_ingredients, missing_ingredients = _fuzzy_split(
            list(ingredients), available_ingredients_lower
        )
        ingredient_score = (
            len(matched_ingredients) / len(ingredients_lower)
            if ingredients_lower
            else 0.0
        )

        # Fuzzy tool / appliance availability
        matched_tools, missing_tools = _fuzzy_split(
            list(tools), combined_available_tools_lower
        )
        tool_score = len(matched_tools) / len(tools_lower) if tools_lower else 0.0

        # When the kitchen has no capability data at all (empty appliances, tools,
        # and ingredients), fall back to a moderate base confidence rather than 0.
        # A facility registered as a cooking kitchen is assumed to be generally
        # capable even if its specific inventory has not been populated yet.
        kitchen_has_capability_data = bool(
            available_ingredients_lower or combined_available_tools_lower
        )
        if not kitchen_has_capability_data:
            confidence_score = 0.5
        else:
            # Overall confidence (weighted average)
            confidence_score = ingredient_score * 0.6 + tool_score * 0.4

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
                "ingredient_overlap": len(matched_ingredients),
                "tool_overlap": len(matched_tools),
                "matched_ingredients": matched_ingredients,
                "missing_ingredients": missing_ingredients,
                "matched_tools": matched_tools,
                "missing_tools": missing_tools,
                "generation_method": "simplified_cooking_matcher",
            },
        )

        return supply_tree
