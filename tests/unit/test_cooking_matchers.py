"""CookingMatcher.generate_supply_tree: confidence scoring and the matched/missing
ingredient and tool breakdown used to build a per-kitchen match explanation
(see CookingMatcher usage in src/core/api/routes/match.py).
"""

from __future__ import annotations

from src.core.domains.cooking.matchers import CookingMatcher
from src.core.models.base.base_types import (
    NormalizedCapabilities,
    NormalizedRequirements,
)


def _requirements(**content) -> NormalizedRequirements:
    return NormalizedRequirements(content=content, domain="cooking")


def _capabilities(**content) -> NormalizedCapabilities:
    return NormalizedCapabilities(content=content, domain="cooking")


def test_generate_supply_tree_reports_matched_and_missing_ingredients():
    requirements = _requirements(
        ingredients=["flour", "eggs", "brown sugar", "chocolate chips"],
        tools=["oven", "spatula"],
        steps=["Bake"],
    )
    capabilities = _capabilities(
        available_ingredients=["flour", "sugar", "chocolate chips"],
        available_tools=["spatula"],
        appliances=["stove"],
    )

    tree = CookingMatcher().generate_supply_tree(
        requirements,
        capabilities,
        kitchen_name="Test Kitchen",
        recipe_name="Test Recipe",
    )

    # "brown sugar" fuzzily matches the kitchen's "sugar" (substring match).
    assert sorted(tree.metadata["matched_ingredients"]) == [
        "brown sugar",
        "chocolate chips",
        "flour",
    ]
    assert tree.metadata["missing_ingredients"] == ["eggs"]
    assert tree.metadata["matched_tools"] == ["spatula"]
    assert tree.metadata["missing_tools"] == ["oven"]
    assert tree.metadata["ingredient_overlap"] == 3
    assert tree.metadata["tool_overlap"] == 1

    # ingredient_score = 3/4 = 0.75, tool_score = 1/2 = 0.5 -> 0.75*0.6 + 0.5*0.4 = 0.65
    assert tree.confidence_score == 0.65


def test_generate_supply_tree_fuzzy_matches_qualifiers_and_plurals():
    requirements = _requirements(
        ingredients=["sugar", "chocolate chip"],
        tools=[],
        steps=[],
    )
    capabilities = _capabilities(
        available_ingredients=["brown sugar", "chocolate chips"],
        available_tools=[],
        appliances=[],
    )

    tree = CookingMatcher().generate_supply_tree(requirements, capabilities)

    assert tree.metadata["matched_ingredients"] == ["sugar", "chocolate chip"]
    assert tree.metadata["missing_ingredients"] == []


def test_generate_supply_tree_empty_kitchen_inventory_uses_moderate_default():
    requirements = _requirements(ingredients=["flour"], tools=["oven"], steps=[])
    capabilities = _capabilities(
        available_ingredients=[], available_tools=[], appliances=[]
    )

    tree = CookingMatcher().generate_supply_tree(requirements, capabilities)

    assert tree.confidence_score == 0.5
    # Kitchen data is unknown, not necessarily missing every item -- the
    # overlap fields are still reported, just as all-missing.
    assert tree.metadata["missing_ingredients"] == ["flour"]
    assert tree.metadata["missing_tools"] == ["oven"]
