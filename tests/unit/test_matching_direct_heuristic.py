"""Characterization tests for DirectMatcher and HeuristicMatcher.

Captures current matching behavior as a regression guard.
"""

from __future__ import annotations

import pytest

from src.core.matching.capability_rules import (
    CapabilityRule,
    CapabilityRuleManager,
    CapabilityRuleSet,
    RuleType,
)
from src.core.matching.direct_matcher import DirectMatcher
from src.core.matching.heuristic_matcher import HeuristicMatcher
from src.core.matching.layers.base import MatchingLayer, MatchQuality

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rule(id="r1", capability="cnc machining", satisfies=None, confidence=0.9):
    return CapabilityRule(
        id=id,
        type=RuleType.CAPABILITY_MATCH,
        capability=capability,
        satisfies_requirements=satisfies or ["milling", "machining"],
        confidence=confidence,
    )


def _manager_with_rules():
    """Pre-initialised CapabilityRuleManager with one manufacturing rule."""
    mgr = CapabilityRuleManager(rules_directory="/tmp/nonexistent")
    rs = CapabilityRuleSet(domain="manufacturing", rules={"r1": _rule()})
    mgr.rule_sets["manufacturing"] = rs
    mgr._initialized = True
    return mgr


# ---------------------------------------------------------------------------
# DirectMatcher
# ---------------------------------------------------------------------------


class TestDirectMatcherInit:
    def test_layer_type_is_direct(self):
        m = DirectMatcher()
        assert m.layer_type == MatchingLayer.DIRECT

    def test_default_threshold_is_two(self):
        m = DirectMatcher()
        assert m.near_miss_threshold == 2

    def test_custom_threshold(self):
        m = DirectMatcher(near_miss_threshold=5)
        assert m.near_miss_threshold == 5


class TestDirectMatcherExactMatch:
    @pytest.mark.asyncio
    async def test_identical_strings_match(self):
        m = DirectMatcher()
        results = await m.match(["milling"], ["milling"])
        assert len(results) == 1
        assert results[0].matched is True
        assert results[0].confidence == 1.0
        assert results[0].metadata.quality == MatchQuality.PERFECT

    @pytest.mark.asyncio
    async def test_case_insensitive_match(self):
        m = DirectMatcher()
        results = await m.match(["Milling"], ["milling"])
        assert results[0].matched is True
        assert results[0].confidence == 0.95
        assert results[0].metadata.quality == MatchQuality.CASE_DIFFERENCE

    @pytest.mark.asyncio
    async def test_double_space_is_near_miss_not_whitespace_match(self):
        # BUG: DirectMatcher._match_single only enters the whitespace-difference
        # branch when lowercased strings are identical. "cnc  machining" ≠
        # "cnc machining" after lower(), so the extra space falls through to
        # Levenshtein (distance=1) → NEAR_MISS, not WHITESPACE_DIFFERENCE.
        m = DirectMatcher()
        results = await m.match(["cnc  machining"], ["cnc machining"])
        assert results[0].matched is False
        assert results[0].metadata.quality == MatchQuality.NEAR_MISS

    @pytest.mark.asyncio
    async def test_case_and_double_space_is_near_miss(self):
        # Same root cause as above — case + extra whitespace → Levenshtein path.
        m = DirectMatcher()
        results = await m.match(["CNC  Machining"], ["cnc machining"])
        assert results[0].matched is False
        assert results[0].metadata.quality == MatchQuality.NEAR_MISS


class TestDirectMatcherNearMiss:
    @pytest.mark.asyncio
    async def test_one_char_diff_is_near_miss(self):
        m = DirectMatcher(near_miss_threshold=2)
        results = await m.match(["milling"], ["millinG"])
        # "milling" vs "milling" lowercased → exact match
        # Use a true 1-char diff
        results = await m.match(["millin"], ["milling"])
        assert results[0].matched is False
        assert results[0].metadata.quality == MatchQuality.NEAR_MISS

    @pytest.mark.asyncio
    async def test_beyond_threshold_is_no_match(self):
        m = DirectMatcher(near_miss_threshold=2)
        results = await m.match(["milling"], ["welding"])
        assert results[0].matched is False
        assert results[0].metadata.quality == MatchQuality.NO_MATCH


class TestDirectMatcherInputValidation:
    @pytest.mark.asyncio
    async def test_empty_requirements_returns_empty(self):
        m = DirectMatcher()
        results = await m.match([], ["cnc machining"])
        assert results == []

    @pytest.mark.asyncio
    async def test_none_requirements_returns_empty(self):
        m = DirectMatcher()
        results = await m.match(None, ["cnc machining"])
        assert results == []

    @pytest.mark.asyncio
    async def test_empty_string_requirement_returns_empty(self):
        m = DirectMatcher()
        results = await m.match([""], ["cnc machining"])
        assert results == []


class TestDirectMatcherCrossProduct:
    @pytest.mark.asyncio
    async def test_two_reqs_two_caps_produces_four_results(self):
        m = DirectMatcher()
        results = await m.match(["milling", "welding"], ["milling", "cutting"])
        assert len(results) == 4

    @pytest.mark.asyncio
    async def test_metrics_populated_after_match(self):
        m = DirectMatcher()
        await m.match(["milling"], ["milling"])
        assert m.metrics is not None
        assert m.metrics.success is True
        assert m.metrics.matches_found == 1


class TestDirectMatcherDomainAdjustment:
    def test_domain_adjustment_returns_one(self):
        m = DirectMatcher(domain="manufacturing")
        adj = m.get_domain_specific_confidence_adjustments("milling", "cnc machining")
        assert adj == 1.0


# ---------------------------------------------------------------------------
# HeuristicMatcher
# ---------------------------------------------------------------------------


class TestHeuristicMatcherInit:
    def test_layer_type_is_heuristic(self):
        m = HeuristicMatcher()
        assert m.layer_type == MatchingLayer.HEURISTIC

    def test_creates_default_rule_manager_when_none_passed(self):
        m = HeuristicMatcher()
        assert m.rule_manager is not None

    def test_accepts_explicit_rule_manager(self):
        mgr = _manager_with_rules()
        m = HeuristicMatcher(domain="manufacturing", rule_manager=mgr)
        assert m.rule_manager is mgr


class TestHeuristicMatcherMatch:
    def _matcher(self):
        mgr = _manager_with_rules()
        m = HeuristicMatcher(domain="manufacturing", rule_manager=mgr)
        m._initialized = True
        return m

    @pytest.mark.asyncio
    async def test_rule_match_returns_matched_true(self):
        m = self._matcher()
        results = await m.match(["milling"], ["cnc machining"])
        assert len(results) == 1
        assert results[0].matched is True
        assert results[0].confidence == 0.9
        assert results[0].metadata.quality == MatchQuality.RULE_MATCH

    @pytest.mark.asyncio
    async def test_no_rule_returns_matched_false(self):
        m = self._matcher()
        results = await m.match(["welding"], ["cnc machining"])
        assert len(results) == 1
        assert results[0].matched is False
        assert results[0].confidence == 0.0
        assert results[0].metadata.quality == MatchQuality.NO_MATCH

    @pytest.mark.asyncio
    async def test_rule_id_recorded_in_metadata(self):
        m = self._matcher()
        results = await m.match(["milling"], ["cnc machining"])
        assert results[0].metadata.rule_used == "r1"

    @pytest.mark.asyncio
    async def test_invalid_inputs_returns_empty(self):
        m = self._matcher()
        results = await m.match([], ["cnc machining"])
        assert results == []

    @pytest.mark.asyncio
    async def test_cross_product_two_by_two(self):
        m = self._matcher()
        results = await m.match(
            ["milling", "welding"], ["cnc machining", "laser cutting"]
        )
        assert len(results) == 4

    @pytest.mark.asyncio
    async def test_metrics_set_after_match(self):
        m = self._matcher()
        await m.match(["milling"], ["cnc machining"])
        assert m.metrics is not None
        assert m.metrics.success is True
        assert m.metrics.matches_found == 1


class TestHeuristicMatcherHelpers:
    def _matcher(self):
        mgr = _manager_with_rules()
        m = HeuristicMatcher(domain="manufacturing", rule_manager=mgr)
        m._initialized = True
        return m

    @pytest.mark.asyncio
    async def test_capability_can_satisfy_requirement_true(self):
        m = self._matcher()
        assert (
            await m.capability_can_satisfy_requirement("cnc machining", "milling")
            is True
        )

    @pytest.mark.asyncio
    async def test_capability_can_satisfy_requirement_false(self):
        m = self._matcher()
        assert (
            await m.capability_can_satisfy_requirement("cnc machining", "welding")
            is False
        )

    @pytest.mark.asyncio
    async def test_get_matching_rules_returns_list(self):
        m = self._matcher()
        rules = await m.get_matching_rules("cnc machining", "milling")
        assert len(rules) == 1
        assert rules[0].id == "r1"

    @pytest.mark.asyncio
    async def test_get_matching_rules_no_match_empty(self):
        m = self._matcher()
        rules = await m.get_matching_rules("cnc machining", "welding")
        assert rules == []

    def test_get_rule_statistics_shape(self):
        m = self._matcher()
        stats = m.get_rule_statistics()
        assert "total_rules" in stats
        assert stats["total_rules"] == 1
