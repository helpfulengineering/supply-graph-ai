"""Characterization tests for capability_rules.py.

These tests capture current behavior as a regression guard.
They document what the code does, not necessarily what it should do.
Bugs found are noted inline but not fixed here.
"""

from __future__ import annotations

import pytest

from src.core.matching.capability_rules import (
    CapabilityMatcher,
    CapabilityMatchResult,
    CapabilityRule,
    CapabilityRuleManager,
    CapabilityRuleSet,
    RuleDirection,
    RuleType,
    create_capability_matcher,
    create_rule_manager,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rule(
    id="r1",
    capability="cnc machining",
    satisfies=None,
    confidence=0.9,
    domain="manufacturing",
    direction=RuleDirection.BIDIRECTIONAL,
    tags=None,
):
    return CapabilityRule(
        id=id,
        type=RuleType.CAPABILITY_MATCH,
        capability=capability,
        satisfies_requirements=satisfies or ["milling", "machining"],
        direction=direction,
        confidence=confidence,
        domain=domain,
        tags=tags or set(),
    )


def _ruleset(domain="manufacturing", rules=None):
    r = rules or {"r1": _rule()}
    return CapabilityRuleSet(domain=domain, rules=r)


# ---------------------------------------------------------------------------
# CapabilityRule — construction & validation
# ---------------------------------------------------------------------------


class TestCapabilityRuleConstruction:
    def test_valid_rule_creates_without_error(self):
        rule = _rule()
        assert rule.id == "r1"
        assert rule.capability == "cnc machining"
        assert rule.confidence == 0.9

    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="Rule ID cannot be empty"):
            CapabilityRule(
                id="",
                type=RuleType.CAPABILITY_MATCH,
                capability="milling",
                satisfies_requirements=["x"],
            )

    def test_whitespace_id_raises(self):
        with pytest.raises(ValueError, match="Rule ID cannot be empty"):
            CapabilityRule(
                id="   ",
                type=RuleType.CAPABILITY_MATCH,
                capability="milling",
                satisfies_requirements=["x"],
            )

    def test_empty_capability_raises(self):
        with pytest.raises(ValueError, match="capability cannot be empty"):
            CapabilityRule(
                id="r1",
                type=RuleType.CAPABILITY_MATCH,
                capability="",
                satisfies_requirements=["x"],
            )

    def test_empty_satisfies_list_raises(self):
        with pytest.raises(ValueError, match="satisfies_requirements cannot be empty"):
            CapabilityRule(
                id="r1",
                type=RuleType.CAPABILITY_MATCH,
                capability="milling",
                satisfies_requirements=[],
            )

    def test_non_string_requirement_raises(self):
        with pytest.raises(ValueError, match="must be a string"):
            CapabilityRule(
                id="r1",
                type=RuleType.CAPABILITY_MATCH,
                capability="milling",
                satisfies_requirements=[42],
            )

    def test_empty_string_requirement_raises(self):
        with pytest.raises(ValueError, match="cannot be empty or whitespace"):
            CapabilityRule(
                id="r1",
                type=RuleType.CAPABILITY_MATCH,
                capability="milling",
                satisfies_requirements=[""],
            )

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValueError, match="confidence must be between"):
            CapabilityRule(
                id="r1",
                type=RuleType.CAPABILITY_MATCH,
                capability="milling",
                satisfies_requirements=["x"],
                confidence=-0.1,
            )

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValueError, match="confidence must be between"):
            CapabilityRule(
                id="r1",
                type=RuleType.CAPABILITY_MATCH,
                capability="milling",
                satisfies_requirements=["x"],
                confidence=1.1,
            )

    def test_empty_domain_raises(self):
        with pytest.raises(ValueError, match="domain cannot be empty"):
            CapabilityRule(
                id="r1",
                type=RuleType.CAPABILITY_MATCH,
                capability="milling",
                satisfies_requirements=["x"],
                domain="",
            )

    def test_boundary_confidence_zero_and_one_allowed(self):
        r0 = _rule(confidence=0.0)
        r1 = _rule(id="r2", confidence=1.0)
        assert r0.confidence == 0.0
        assert r1.confidence == 1.0


# ---------------------------------------------------------------------------
# CapabilityRule — can_satisfy_requirement
# ---------------------------------------------------------------------------


class TestCanSatisfyRequirement:
    def test_matching_requirement_returns_true(self):
        rule = _rule(satisfies=["milling", "machining"])
        assert rule.can_satisfy_requirement("milling") is True

    def test_case_insensitive_match(self):
        rule = _rule(satisfies=["Milling"])
        assert rule.can_satisfy_requirement("milling") is True
        assert rule.can_satisfy_requirement("MILLING") is True

    def test_no_match_returns_false(self):
        rule = _rule(satisfies=["milling"])
        assert rule.can_satisfy_requirement("welding") is False

    def test_empty_requirement_returns_false(self):
        rule = _rule(satisfies=["milling"])
        assert rule.can_satisfy_requirement("") is False

    def test_whitespace_stripped(self):
        rule = _rule(satisfies=["milling"])
        assert rule.can_satisfy_requirement("  milling  ") is True


# ---------------------------------------------------------------------------
# CapabilityRule — requirement_can_be_satisfied_by
# ---------------------------------------------------------------------------


class TestRequirementCanBeSatisfiedBy:
    def test_matching_pair_returns_true(self):
        rule = _rule(capability="cnc machining", satisfies=["milling"])
        assert rule.requirement_can_be_satisfied_by("milling", "cnc machining") is True

    def test_wrong_capability_returns_false(self):
        rule = _rule(capability="cnc machining", satisfies=["milling"])
        assert rule.requirement_can_be_satisfied_by("milling", "laser cutting") is False

    def test_empty_capability_returns_false(self):
        rule = _rule(satisfies=["milling"])
        assert rule.requirement_can_be_satisfied_by("milling", "") is False

    def test_empty_requirement_returns_false(self):
        rule = _rule(satisfies=["milling"])
        assert rule.requirement_can_be_satisfied_by("", "cnc machining") is False


# ---------------------------------------------------------------------------
# CapabilityRule — to_dict / from_dict
# ---------------------------------------------------------------------------


class TestCapabilityRuleSerialisation:
    def test_to_dict_returns_expected_keys(self):
        rule = _rule(tags={"machining"})
        d = rule.to_dict()
        assert set(d.keys()) == {
            "id",
            "type",
            "capability",
            "satisfies_requirements",
            "direction",
            "confidence",
            "domain",
            "description",
            "source",
            "tags",
        }

    def test_to_dict_with_metadata_includes_timestamps(self):
        rule = _rule()
        d = rule.to_dict(include_metadata=True)
        assert "created_at" in d
        assert "updated_at" in d

    def test_from_dict_roundtrip(self):
        rule = _rule(tags={"machining", "cnc"})
        d = rule.to_dict()
        restored = CapabilityRule.from_dict(d)
        assert restored.id == rule.id
        assert restored.capability == rule.capability
        assert restored.satisfies_requirements == rule.satisfies_requirements
        assert restored.confidence == rule.confidence

    def test_from_dict_missing_id_raises(self):
        with pytest.raises(ValueError, match="Invalid rule data"):
            CapabilityRule.from_dict(
                {
                    "type": "capability_match",
                    "capability": "x",
                    "satisfies_requirements": ["y"],
                }
            )

    def test_from_dict_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Invalid rule data"):
            CapabilityRule.from_dict(
                {
                    "id": "r1",
                    "type": "bogus_type",
                    "capability": "x",
                    "satisfies_requirements": ["y"],
                }
            )


# ---------------------------------------------------------------------------
# CapabilityRuleSet — construction & validation
# ---------------------------------------------------------------------------


class TestCapabilityRuleSetConstruction:
    def test_valid_ruleset_creates(self):
        rs = _ruleset()
        assert rs.domain == "manufacturing"
        assert len(rs.rules) == 1

    def test_empty_domain_raises(self):
        with pytest.raises(ValueError, match="domain cannot be empty"):
            CapabilityRuleSet(domain="", rules={"r1": _rule()})

    def test_empty_rules_raises(self):
        with pytest.raises(ValueError, match="must contain at least one rule"):
            CapabilityRuleSet(domain="manufacturing", rules={})


# ---------------------------------------------------------------------------
# CapabilityRuleSet — CRUD
# ---------------------------------------------------------------------------


class TestCapabilityRuleSetCRUD:
    def test_add_rule_increases_count(self):
        rs = _ruleset()
        assert len(rs.rules) == 1
        rs.add_rule(_rule(id="r2", capability="laser cutting", satisfies=["cutting"]))
        assert len(rs.rules) == 2

    def test_remove_existing_rule_returns_true(self):
        rs = _ruleset()
        assert rs.remove_rule("r1") is True
        assert "r1" not in rs.rules

    def test_remove_missing_rule_returns_false(self):
        rs = _ruleset()
        assert rs.remove_rule("nonexistent") is False

    def test_get_rule_returns_correct_rule(self):
        rs = _ruleset()
        rule = rs.get_rule("r1")
        assert rule is not None
        assert rule.id == "r1"

    def test_get_rule_missing_returns_none(self):
        rs = _ruleset()
        assert rs.get_rule("missing") is None

    def test_get_rules_by_type_returns_matching(self):
        rs = _ruleset()
        results = rs.get_rules_by_type(RuleType.CAPABILITY_MATCH)
        assert len(results) == 1

    def test_get_rules_by_tag_returns_matching(self):
        r = _rule(tags={"machining"})
        rs = CapabilityRuleSet(domain="manufacturing", rules={"r1": r})
        assert len(rs.get_rules_by_tag("machining")) == 1
        assert len(rs.get_rules_by_tag("welding")) == 0

    def test_get_all_rules_returns_list(self):
        rs = _ruleset()
        rules = rs.get_all_rules()
        assert isinstance(rules, list)
        assert len(rules) == 1


# ---------------------------------------------------------------------------
# CapabilityRuleSet — find_rules_for_capability_requirement
# ---------------------------------------------------------------------------


class TestFindRulesForCapabilityRequirement:
    def test_finds_matching_rule(self):
        rs = _ruleset()
        results = rs.find_rules_for_capability_requirement("cnc machining", "milling")
        assert len(results) == 1
        assert results[0].id == "r1"

    def test_no_match_returns_empty_list(self):
        rs = _ruleset()
        results = rs.find_rules_for_capability_requirement("cnc machining", "welding")
        assert results == []

    def test_wrong_capability_returns_empty(self):
        rs = _ruleset()
        results = rs.find_rules_for_capability_requirement("laser cutting", "milling")
        assert results == []


# ---------------------------------------------------------------------------
# CapabilityRuleSet — to_dict / from_dict
# ---------------------------------------------------------------------------


class TestCapabilityRuleSetSerialisation:
    def test_to_dict_keys(self):
        rs = _ruleset()
        d = rs.to_dict()
        assert "domain" in d
        assert "rules" in d
        assert "version" in d

    def test_from_dict_roundtrip(self):
        rs = _ruleset()
        d = rs.to_dict()
        restored = CapabilityRuleSet.from_dict(d)
        assert restored.domain == rs.domain
        assert list(restored.rules.keys()) == list(rs.rules.keys())

    def test_from_dict_missing_domain_raises(self):
        with pytest.raises(ValueError, match="Invalid rule set data"):
            CapabilityRuleSet.from_dict({"rules": {"r1": _rule().to_dict()}})


# ---------------------------------------------------------------------------
# CapabilityRuleManager — in-memory operations (no file I/O)
# ---------------------------------------------------------------------------


class TestCapabilityRuleManagerInMemory:
    def _manager_with_ruleset(self):
        mgr = CapabilityRuleManager(rules_directory="/tmp/nonexistent")
        mgr.rule_sets["manufacturing"] = _ruleset()
        return mgr

    def test_get_rule_set_returns_correct(self):
        mgr = self._manager_with_ruleset()
        rs = mgr.get_rule_set("manufacturing")
        assert rs is not None
        assert rs.domain == "manufacturing"

    def test_get_rule_set_missing_returns_none(self):
        mgr = self._manager_with_ruleset()
        assert mgr.get_rule_set("cooking") is None

    def test_get_available_domains(self):
        mgr = self._manager_with_ruleset()
        assert "manufacturing" in mgr.get_available_domains()

    def test_add_rule_set(self):
        mgr = create_rule_manager()
        rs = _ruleset(domain="cooking", rules={"c1": _rule(id="c1", domain="cooking")})
        mgr.add_rule_set(rs)
        assert "cooking" in mgr.get_available_domains()

    def test_remove_rule_set_existing_returns_true(self):
        mgr = self._manager_with_ruleset()
        assert mgr.remove_rule_set("manufacturing") is True
        assert mgr.get_rule_set("manufacturing") is None

    def test_remove_rule_set_missing_returns_false(self):
        mgr = self._manager_with_ruleset()
        assert mgr.remove_rule_set("cooking") is False

    def test_get_rule_returns_correct(self):
        mgr = self._manager_with_ruleset()
        rule = mgr.get_rule("manufacturing", "r1")
        assert rule is not None
        assert rule.id == "r1"

    def test_get_rule_unknown_domain_returns_none(self):
        mgr = self._manager_with_ruleset()
        assert mgr.get_rule("cooking", "r1") is None

    def test_get_rules_by_type(self):
        mgr = self._manager_with_ruleset()
        rules = mgr.get_rules_by_type("manufacturing", RuleType.CAPABILITY_MATCH)
        assert len(rules) == 1

    def test_get_rules_by_type_unknown_domain_returns_empty(self):
        mgr = self._manager_with_ruleset()
        assert mgr.get_rules_by_type("cooking", RuleType.CAPABILITY_MATCH) == []

    def test_get_rules_by_tag(self):
        r = _rule(tags={"machining"})
        rs = CapabilityRuleSet(domain="manufacturing", rules={"r1": r})
        mgr = create_rule_manager()
        mgr.add_rule_set(rs)
        assert len(mgr.get_rules_by_tag("manufacturing", "machining")) == 1
        assert mgr.get_rules_by_tag("manufacturing", "nope") == []

    def test_get_all_rules_for_domain(self):
        mgr = self._manager_with_ruleset()
        rules = mgr.get_all_rules_for_domain("manufacturing")
        assert len(rules) == 1

    def test_get_all_rules_unknown_domain_empty(self):
        mgr = self._manager_with_ruleset()
        assert mgr.get_all_rules_for_domain("cooking") == []

    def test_find_rules_for_capability_requirement(self):
        mgr = self._manager_with_ruleset()
        rules = mgr.find_rules_for_capability_requirement(
            "manufacturing", "cnc machining", "milling"
        )
        assert len(rules) == 1

    def test_find_rules_unknown_domain_returns_empty(self):
        mgr = self._manager_with_ruleset()
        assert mgr.find_rules_for_capability_requirement("cooking", "x", "y") == []

    def test_get_rule_statistics_shape(self):
        mgr = self._manager_with_ruleset()
        stats = mgr.get_rule_statistics()
        assert stats["total_domains"] == 1
        assert stats["total_rules"] == 1
        assert "manufacturing" in stats["domains"]
        assert "rules_directory" in stats


# ---------------------------------------------------------------------------
# CapabilityMatchResult — to_dict
# ---------------------------------------------------------------------------


class TestCapabilityMatchResult:
    def test_to_dict_no_rule(self):
        result = CapabilityMatchResult(
            requirement_object={"process_name": "milling"},
            capability_object={"process_name": "cnc machining"},
            requirement_field="process_name",
            capability_field="process_name",
            requirement_value="milling",
            capability_value="cnc machining",
            matched=False,
            confidence=0.0,
        )
        d = result.to_dict()
        assert d["matched"] is False
        assert d["rule_used"] is None
        assert d["confidence"] == 0.0

    def test_to_dict_with_rule(self):
        rule = _rule()
        result = CapabilityMatchResult(
            requirement_object={},
            capability_object={},
            requirement_field="process_name",
            capability_field="process_name",
            requirement_value="milling",
            capability_value="cnc machining",
            matched=True,
            confidence=0.9,
            rule_used=rule,
        )
        d = result.to_dict()
        assert d["matched"] is True
        assert d["rule_used"] is not None
        assert d["rule_used"]["id"] == "r1"


# ---------------------------------------------------------------------------
# CapabilityMatcher — async matching (in-memory rules)
# ---------------------------------------------------------------------------


class TestCapabilityMatcher:
    def _matcher(self):
        mgr = create_rule_manager(rules_directory="/tmp/nonexistent")
        mgr.rule_sets["manufacturing"] = _ruleset()
        mgr._initialized = True
        matcher = create_capability_matcher(mgr)
        matcher._initialized = True
        return matcher

    @pytest.mark.asyncio
    async def test_capability_can_satisfy_requirement_match(self):
        matcher = self._matcher()
        result = await matcher.capability_can_satisfy_requirement(
            "cnc machining", "milling", "manufacturing"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_capability_can_satisfy_requirement_no_match(self):
        matcher = self._matcher()
        result = await matcher.capability_can_satisfy_requirement(
            "cnc machining", "welding", "manufacturing"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_requirement_can_be_satisfied_by_delegates(self):
        matcher = self._matcher()
        result = await matcher.requirement_can_be_satisfied_by(
            "milling", "cnc machining", "manufacturing"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_match_requirements_to_capabilities_finds_match(self):
        matcher = self._matcher()
        results = await matcher.match_requirements_to_capabilities(
            requirements=[{"process_name": "milling"}],
            capabilities=[{"process_name": "cnc machining"}],
            domain="manufacturing",
        )
        assert len(results) == 1
        assert results[0].matched is True
        assert results[0].confidence == 0.9

    @pytest.mark.asyncio
    async def test_match_requirements_to_capabilities_no_match(self):
        matcher = self._matcher()
        results = await matcher.match_requirements_to_capabilities(
            requirements=[{"process_name": "welding"}],
            capabilities=[{"process_name": "cnc machining"}],
            domain="manufacturing",
        )
        assert len(results) == 1
        assert results[0].matched is False
        assert results[0].confidence == 0.0

    @pytest.mark.asyncio
    async def test_match_empty_field_produces_unmatched(self):
        matcher = self._matcher()
        results = await matcher.match_requirements_to_capabilities(
            requirements=[{"process_name": ""}],
            capabilities=[{"process_name": "cnc machining"}],
            domain="manufacturing",
        )
        assert results[0].matched is False

    @pytest.mark.asyncio
    async def test_match_picks_highest_confidence_rule(self):
        r_low = _rule(id="low", confidence=0.5, satisfies=["milling"])
        r_high = _rule(id="high", confidence=0.95, satisfies=["milling"])
        rs = CapabilityRuleSet(
            domain="manufacturing", rules={"low": r_low, "high": r_high}
        )
        mgr = create_rule_manager()
        mgr.add_rule_set(rs)
        mgr._initialized = True
        matcher = create_capability_matcher(mgr)
        matcher._initialized = True

        results = await matcher.match_requirements_to_capabilities(
            requirements=[{"process_name": "milling"}],
            capabilities=[{"process_name": "cnc machining"}],
            domain="manufacturing",
        )
        assert results[0].confidence == 0.95
        assert results[0].rule_used.id == "high"
