"""_build_cooking_match_explanation: turns CookingMatcher's ingredient/tool
overlap into a MatchExplanation the frontend can render as real coverage
("Missing N of M requirements") instead of "Coverage unknown".

Regression coverage for the bug where cooking-domain match results never got
an `explanation.requirement_matches`, because that block was gated to
`domain == "manufacturing"` in src/core/api/routes/match.py.
"""

from __future__ import annotations

from src.core.api.routes.match import _build_cooking_match_explanation
from src.core.domains.cooking.matchers import CookingMatcher
from src.core.models.base.base_types import (
    NormalizedCapabilities,
    NormalizedRequirements,
)
from src.core.models.match_explanation import MatchStatus


def _supply_tree(
    matched_ingredients, missing_ingredients, matched_tools, missing_tools
):
    requirements = NormalizedRequirements(
        content={
            "ingredients": matched_ingredients + missing_ingredients,
            "tools": matched_tools + missing_tools,
            "steps": [],
        },
        domain="cooking",
    )
    capabilities = NormalizedCapabilities(
        content={
            "available_ingredients": matched_ingredients,
            "available_tools": matched_tools,
            "appliances": [],
        },
        domain="cooking",
    )
    return CookingMatcher().generate_supply_tree(requirements, capabilities)


def test_explanation_reports_matched_and_missing_requirements():
    tree = _supply_tree(
        matched_ingredients=["flour", "sugar"],
        missing_ingredients=["eggs"],
        matched_tools=["oven"],
        missing_tools=["mixer"],
    )

    explanation = _build_cooking_match_explanation(tree, "kitchen-1", "Test Kitchen")

    values_by_status = {
        (m.requirement_value, m.status) for m in explanation.requirement_matches
    }
    assert (("flour", MatchStatus.MATCHED)) in values_by_status
    assert (("sugar", MatchStatus.MATCHED)) in values_by_status
    assert (("eggs", MatchStatus.NOT_MATCHED)) in values_by_status
    assert (("oven", MatchStatus.MATCHED)) in values_by_status
    assert (("mixer", MatchStatus.NOT_MATCHED)) in values_by_status
    assert len(explanation.requirement_matches) == 5

    assert explanation.overall_status == MatchStatus.NOT_MATCHED
    assert explanation.missing_capabilities == ["eggs", "mixer"]
    assert explanation.overall_confidence == tree.confidence_score


def test_explanation_matched_status_when_nothing_missing():
    tree = _supply_tree(
        matched_ingredients=["flour"],
        missing_ingredients=[],
        matched_tools=["oven"],
        missing_tools=[],
    )

    explanation = _build_cooking_match_explanation(tree, "kitchen-2", "Full Kitchen")

    assert explanation.overall_status == MatchStatus.MATCHED
    assert explanation.missing_capabilities == []
    assert all(m.status == MatchStatus.MATCHED for m in explanation.requirement_matches)


def test_explanation_to_dict_has_requirement_matches_frontend_expects():
    tree = _supply_tree(
        matched_ingredients=["flour"],
        missing_ingredients=["eggs"],
        matched_tools=[],
        missing_tools=[],
    )

    explanation = _build_cooking_match_explanation(tree, "kitchen-3", "Some Kitchen")
    as_dict = explanation.to_dict()

    # Shape expected by frontend/src/features/match/nearMiss.ts requirementStats().
    assert "requirement_matches" in as_dict
    for match in as_dict["requirement_matches"]:
        assert "status" in match
        assert "requirement_value" in match
