"""
Comprehensive Test Suite for Capability-Centric Heuristic Rules System

This test suite provides thorough coverage of all components:
- CapabilityRule validation and functionality
- CapabilityRuleSet management
- CapabilityRuleManager loading and retrieval
- CapabilityMatcher matching logic
- Configuration file loading
- Integration scenarios
- Error handling and edge cases
"""

import pytest
import asyncio
import tempfile
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any

from src.core.matching.capability_rules import (
    CapabilityRule, CapabilityRuleSet, CapabilityRuleManager, CapabilityMatcher,
    CapabilityMatchResult, RuleType, RuleDirection
)


class TestCapabilityRule:
    """Comprehensive tests for CapabilityRule class"""
    
    def test_rule_creation_valid(self):
        """Test creating valid capability rules"""
        rule = CapabilityRule(
            id="test_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling", "machining"],
            confidence=0.9,
            domain="manufacturing"
        )
        
        assert rule.id == "test_rule"
        assert rule.type == RuleType.CAPABILITY_MATCH
        assert rule.capability == "cnc machining"
        assert rule.satisfies_requirements == ["milling", "machining"]
        assert rule.confidence == 0.9
        assert rule.domain == "manufacturing"
    
    def test_rule_validation_errors(self):
        """Test rule validation catches errors"""
        # Empty capability
        with pytest.raises(ValueError, match="capability and satisfies_requirements cannot be empty"):
            CapabilityRule(
                id="test",
                type=RuleType.CAPABILITY_MATCH,
                capability="",
                satisfies_requirements=["milling"]
            )
        
        # Empty requirements
        with pytest.raises(ValueError, match="capability and satisfies_requirements cannot be empty"):
            CapabilityRule(
                id="test",
                type=RuleType.CAPABILITY_MATCH,
                capability="cnc machining",
                satisfies_requirements=[]
            )
        
        # Invalid confidence
        with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
            CapabilityRule(
                id="test",
                type=RuleType.CAPABILITY_MATCH,
                capability="cnc machining",
                satisfies_requirements=["milling"],
                confidence=1.5
            )
        
        # Negative confidence
        with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
            CapabilityRule(
                id="test",
                type=RuleType.CAPABILITY_MATCH,
                capability="cnc machining",
                satisfies_requirements=["milling"],
                confidence=-0.1
            )
    
    def test_can_satisfy_requirement(self):
        """Test requirement satisfaction logic"""
        rule = CapabilityRule(
            id="cnc_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling", "machining", "material removal"],
            confidence=0.9
        )
        
        # Positive cases
        assert rule.can_satisfy_requirement("milling")
        assert rule.can_satisfy_requirement("MACHINING")  # Case insensitive
        assert rule.can_satisfy_requirement("  material removal  ")  # Whitespace handling
        
        # Negative cases
        assert not rule.can_satisfy_requirement("welding")
        assert not rule.can_satisfy_requirement("")
        assert not rule.can_satisfy_requirement("3d printing")
    
    def test_requirement_can_be_satisfied_by(self):
        """Test bidirectional matching logic"""
        rule = CapabilityRule(
            id="additive_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="3d printing",
            satisfies_requirements=["additive manufacturing", "rapid prototyping"],
            confidence=0.9
        )
        
        # Positive cases
        assert rule.requirement_can_be_satisfied_by("additive manufacturing", "3d printing")
        assert rule.requirement_can_be_satisfied_by("RAPID PROTOTYPING", "3D PRINTING")  # Case insensitive
        
        # Negative cases
        assert not rule.requirement_can_be_satisfied_by("milling", "3d printing")
        assert not rule.requirement_can_be_satisfied_by("additive manufacturing", "cnc machining")
        assert not rule.requirement_can_be_satisfied_by("", "3d printing")
        assert not rule.requirement_can_be_satisfied_by("additive manufacturing", "")
    
    def test_serialization(self):
        """Test rule serialization and deserialization"""
        rule = CapabilityRule(
            id="test_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling", "machining"],
            confidence=0.95,
            domain="manufacturing",
            description="Test rule",
            source="Test source",
            tags={"machining", "automation"}
        )
        
        # Test to_dict
        rule_dict = rule.to_dict()
        assert rule_dict["id"] == "test_rule"
        assert rule_dict["type"] == "capability_match"
        assert rule_dict["capability"] == "cnc machining"
        assert rule_dict["satisfies_requirements"] == ["milling", "machining"]
        assert rule_dict["confidence"] == 0.95
        assert rule_dict["domain"] == "manufacturing"
        assert rule_dict["description"] == "Test rule"
        assert rule_dict["source"] == "Test source"
        assert set(rule_dict["tags"]) == {"machining", "automation"}
        
        # Test from_dict
        restored_rule = CapabilityRule.from_dict(rule_dict)
        assert restored_rule.id == rule.id
        assert restored_rule.type == rule.type
        assert restored_rule.capability == rule.capability
        assert restored_rule.satisfies_requirements == rule.satisfies_requirements
        assert restored_rule.confidence == rule.confidence
        assert restored_rule.domain == rule.domain
        assert restored_rule.description == rule.description
        assert restored_rule.source == rule.source
        assert restored_rule.tags == rule.tags


class TestCapabilityRuleSet:
    """Comprehensive tests for CapabilityRuleSet class"""
    
    def test_rule_set_creation(self):
        """Test creating rule sets"""
        rule_set = CapabilityRuleSet(
            domain="manufacturing",
            version="1.0.0",
            description="Test rule set"
        )
        
        assert rule_set.domain == "manufacturing"
        assert rule_set.version == "1.0.0"
        assert rule_set.description == "Test rule set"
        assert len(rule_set.rules) == 0
    
    def test_add_remove_rules(self):
        """Test adding and removing rules"""
        rule_set = CapabilityRuleSet(domain="manufacturing")
        
        rule1 = CapabilityRule(
            id="rule1",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling"],
            confidence=0.9
        )
        
        rule2 = CapabilityRule(
            id="rule2",
            type=RuleType.CAPABILITY_MATCH,
            capability="3d printing",
            satisfies_requirements=["additive manufacturing"],
            confidence=0.9
        )
        
        # Add rules
        rule_set.add_rule(rule1)
        rule_set.add_rule(rule2)
        
        assert len(rule_set.rules) == 2
        assert "rule1" in rule_set.rules
        assert "rule2" in rule_set.rules
        
        # Remove rule
        assert rule_set.remove_rule("rule1")
        assert len(rule_set.rules) == 1
        assert "rule1" not in rule_set.rules
        assert "rule2" in rule_set.rules
        
        # Remove non-existent rule
        assert not rule_set.remove_rule("nonexistent")
        assert len(rule_set.rules) == 1
    
    def test_rule_retrieval(self):
        """Test rule retrieval methods"""
        rule_set = CapabilityRuleSet(domain="manufacturing")
        
        rule1 = CapabilityRule(
            id="cnc_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling"],
            confidence=0.9,
            tags={"machining"}
        )
        
        rule2 = CapabilityRule(
            id="additive_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="3d printing",
            satisfies_requirements=["additive manufacturing"],
            confidence=0.9,
            tags={"additive"}
        )
        
        rule_set.add_rule(rule1)
        rule_set.add_rule(rule2)
        
        # Test get_rule
        assert rule_set.get_rule("cnc_rule") == rule1
        assert rule_set.get_rule("nonexistent") is None
        
        # Test get_rules_by_type
        capability_rules = rule_set.get_rules_by_type(RuleType.CAPABILITY_MATCH)
        assert len(capability_rules) == 2
        assert rule1 in capability_rules
        assert rule2 in capability_rules
        
        # Test get_rules_by_tag
        machining_rules = rule_set.get_rules_by_tag("machining")
        assert len(machining_rules) == 1
        assert rule1 in machining_rules
        
        additive_rules = rule_set.get_rules_by_tag("additive")
        assert len(additive_rules) == 1
        assert rule2 in additive_rules
        
        # Test get_all_rules
        all_rules = rule_set.get_all_rules()
        assert len(all_rules) == 2
        assert rule1 in all_rules
        assert rule2 in all_rules
    
    def test_find_rules_for_capability_requirement(self):
        """Test finding rules for capability-requirement pairs"""
        rule_set = CapabilityRuleSet(domain="manufacturing")
        
        rule1 = CapabilityRule(
            id="cnc_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling", "machining"],
            confidence=0.9
        )
        
        rule2 = CapabilityRule(
            id="additive_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="3d printing",
            satisfies_requirements=["additive manufacturing"],
            confidence=0.9
        )
        
        rule_set.add_rule(rule1)
        rule_set.add_rule(rule2)
        
        # Test finding matching rules
        matching_rules = rule_set.find_rules_for_capability_requirement("cnc machining", "milling")
        assert len(matching_rules) == 1
        assert matching_rules[0] == rule1
        
        matching_rules = rule_set.find_rules_for_capability_requirement("3d printing", "additive manufacturing")
        assert len(matching_rules) == 1
        assert matching_rules[0] == rule2
        
        # Test no match
        no_match = rule_set.find_rules_for_capability_requirement("cnc machining", "additive manufacturing")
        assert len(no_match) == 0
        
        # Test case insensitive
        matching_rules = rule_set.find_rules_for_capability_requirement("CNC MACHINING", "MILLING")
        assert len(matching_rules) == 1
        assert matching_rules[0] == rule1
    
    def test_serialization(self):
        """Test rule set serialization and deserialization"""
        rule_set = CapabilityRuleSet(
            domain="manufacturing",
            version="1.0.0",
            description="Test rule set"
        )
        
        rule = CapabilityRule(
            id="test_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling"],
            confidence=0.9
        )
        
        rule_set.add_rule(rule)
        
        # Test to_dict
        rule_set_dict = rule_set.to_dict()
        assert rule_set_dict["domain"] == "manufacturing"
        assert rule_set_dict["version"] == "1.0.0"
        assert rule_set_dict["description"] == "Test rule set"
        assert len(rule_set_dict["rules"]) == 1
        assert "test_rule" in rule_set_dict["rules"]
        
        # Test from_dict
        restored_rule_set = CapabilityRuleSet.from_dict(rule_set_dict)
        assert restored_rule_set.domain == rule_set.domain
        assert restored_rule_set.version == rule_set.version
        assert restored_rule_set.description == rule_set.description
        assert len(restored_rule_set.rules) == 1
        assert "test_rule" in restored_rule_set.rules


class TestCapabilityRuleManager:
    """Comprehensive tests for CapabilityRuleManager class"""
    
    @pytest.fixture
    def temp_rules_dir(self):
        """Create temporary directory with test rule files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            rules_dir = Path(temp_dir) / "capability_rules"
            rules_dir.mkdir()
            
            # Create test manufacturing rules
            manufacturing_rules = {
                "domain": "manufacturing",
                "version": "1.0.0",
                "description": "Test manufacturing rules",
                "rules": {
                    "cnc_rule": {
                        "id": "cnc_rule",
                        "type": "capability_match",
                        "capability": "cnc machining",
                        "satisfies_requirements": ["milling", "machining"],
                        "confidence": 0.9,
                        "domain": "manufacturing"
                    },
                    "additive_rule": {
                        "id": "additive_rule",
                        "type": "capability_match",
                        "capability": "3d printing",
                        "satisfies_requirements": ["additive manufacturing"],
                        "confidence": 0.9,
                        "domain": "manufacturing"
                    }
                }
            }
            
            with open(rules_dir / "manufacturing.yaml", 'w') as f:
                yaml.dump(manufacturing_rules, f)
            
            # Create test cooking rules
            cooking_rules = {
                "domain": "cooking",
                "version": "1.0.0",
                "description": "Test cooking rules",
                "rules": {
                    "sauté_rule": {
                        "id": "sauté_rule",
                        "type": "capability_match",
                        "capability": "sauté pan",
                        "satisfies_requirements": ["sauté", "pan-fry"],
                        "confidence": 0.95,
                        "domain": "cooking"
                    }
                }
            }
            
            with open(rules_dir / "cooking.yaml", 'w') as f:
                yaml.dump(cooking_rules, f)
            
            yield str(rules_dir)
    
    @pytest.mark.asyncio
    async def test_initialization(self, temp_rules_dir):
        """Test rule manager initialization"""
        manager = CapabilityRuleManager(temp_rules_dir)
        await manager.initialize()
        
        assert manager._initialized
        assert len(manager.rule_sets) == 2
        assert "manufacturing" in manager.rule_sets
        assert "cooking" in manager.rule_sets
    
    @pytest.mark.asyncio
    async def test_rule_loading(self, temp_rules_dir):
        """Test loading rules from files"""
        manager = CapabilityRuleManager(temp_rules_dir)
        await manager.initialize()
        
        # Test manufacturing rules
        manufacturing_rules = manager.get_all_rules_for_domain("manufacturing")
        assert len(manufacturing_rules) == 2
        
        cnc_rule = manager.get_rule("manufacturing", "cnc_rule")
        assert cnc_rule is not None
        assert cnc_rule.capability == "cnc machining"
        assert "milling" in cnc_rule.satisfies_requirements
        
        additive_rule = manager.get_rule("manufacturing", "additive_rule")
        assert additive_rule is not None
        assert additive_rule.capability == "3d printing"
        assert "additive manufacturing" in additive_rule.satisfies_requirements
        
        # Test cooking rules
        cooking_rules = manager.get_all_rules_for_domain("cooking")
        assert len(cooking_rules) == 1
        
        sauté_rule = manager.get_rule("cooking", "sauté_rule")
        assert sauté_rule is not None
        assert sauté_rule.capability == "sauté pan"
        assert "sauté" in sauté_rule.satisfies_requirements
    
    @pytest.mark.asyncio
    async def test_rule_retrieval(self, temp_rules_dir):
        """Test rule retrieval methods"""
        manager = CapabilityRuleManager(temp_rules_dir)
        await manager.initialize()
        
        # Test get_available_domains
        domains = manager.get_available_domains()
        assert "manufacturing" in domains
        assert "cooking" in domains
        
        # Test get_rule_set
        manufacturing_set = manager.get_rule_set("manufacturing")
        assert manufacturing_set is not None
        assert manufacturing_set.domain == "manufacturing"
        
        nonexistent_set = manager.get_rule_set("nonexistent")
        assert nonexistent_set is None
        
        # Test get_rules_by_type
        capability_rules = manager.get_rules_by_type("manufacturing", RuleType.CAPABILITY_MATCH)
        assert len(capability_rules) == 2
        
        # Test get_rules_by_tag
        # (No tags in test data, so should return empty)
        tagged_rules = manager.get_rules_by_tag("manufacturing", "machining")
        assert len(tagged_rules) == 0
    
    @pytest.mark.asyncio
    async def test_find_rules_for_capability_requirement(self, temp_rules_dir):
        """Test finding rules for capability-requirement pairs"""
        manager = CapabilityRuleManager(temp_rules_dir)
        await manager.initialize()
        
        # Test finding matching rules
        rules = manager.find_rules_for_capability_requirement("manufacturing", "cnc machining", "milling")
        assert len(rules) == 1
        assert rules[0].id == "cnc_rule"
        
        rules = manager.find_rules_for_capability_requirement("manufacturing", "3d printing", "additive manufacturing")
        assert len(rules) == 1
        assert rules[0].id == "additive_rule"
        
        # Test no match
        rules = manager.find_rules_for_capability_requirement("manufacturing", "cnc machining", "additive manufacturing")
        assert len(rules) == 0
        
        # Test nonexistent domain
        rules = manager.find_rules_for_capability_requirement("nonexistent", "cnc machining", "milling")
        assert len(rules) == 0
    
    @pytest.mark.asyncio
    async def test_rule_statistics(self, temp_rules_dir):
        """Test rule statistics"""
        manager = CapabilityRuleManager(temp_rules_dir)
        await manager.initialize()
        
        stats = manager.get_rule_statistics()
        
        assert stats["total_domains"] == 2
        assert stats["total_rules"] == 3
        assert "manufacturing" in stats["domains"]
        assert "cooking" in stats["domains"]
        assert stats["rule_types"]["capability_match"] == 3
        assert stats["rules_directory"] == temp_rules_dir
    
    @pytest.mark.asyncio
    async def test_rule_set_management(self):
        """Test adding and removing rule sets"""
        manager = CapabilityRuleManager()
        
        # Create test rule set
        rule_set = CapabilityRuleSet(domain="test")
        rule = CapabilityRule(
            id="test_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="test capability",
            satisfies_requirements=["test requirement"],
            confidence=0.9
        )
        rule_set.add_rule(rule)
        
        # Test add_rule_set
        manager.add_rule_set(rule_set)
        assert "test" in manager.rule_sets
        assert len(manager.get_all_rules_for_domain("test")) == 1
        
        # Test remove_rule_set
        assert manager.remove_rule_set("test")
        assert "test" not in manager.rule_sets
        assert len(manager.get_all_rules_for_domain("test")) == 0
        
        # Test remove nonexistent
        assert not manager.remove_rule_set("nonexistent")
    
    @pytest.mark.asyncio
    async def test_reload_rules(self, temp_rules_dir):
        """Test reloading rules"""
        manager = CapabilityRuleManager(temp_rules_dir)
        await manager.initialize()
        
        # Verify initial state
        assert len(manager.rule_sets) == 2
        
        # Reload rules
        await manager.reload_rules()
        
        # Verify state after reload
        assert len(manager.rule_sets) == 2
        assert "manufacturing" in manager.rule_sets
        assert "cooking" in manager.rule_sets


class TestCapabilityMatcher:
    """Comprehensive tests for CapabilityMatcher class"""
    
    @pytest.fixture
    def sample_rules(self):
        """Create sample rules for testing"""
        return [
            CapabilityRule(
                id="cnc_rule",
                type=RuleType.CAPABILITY_MATCH,
                capability="cnc machining",
                satisfies_requirements=["milling", "machining", "material removal"],
                confidence=0.9,
                domain="manufacturing"
            ),
            CapabilityRule(
                id="additive_rule",
                type=RuleType.CAPABILITY_MATCH,
                capability="3d printing",
                satisfies_requirements=["additive manufacturing", "rapid prototyping"],
                confidence=0.9,
                domain="manufacturing"
            ),
            CapabilityRule(
                id="sauté_rule",
                type=RuleType.CAPABILITY_MATCH,
                capability="sauté pan",
                satisfies_requirements=["sauté", "pan-fry"],
                confidence=0.95,
                domain="cooking"
            )
        ]
    
    @pytest.fixture
    async def matcher(self, sample_rules):
        """Create a matcher with sample rules"""
        rule_manager = CapabilityRuleManager()
        
        # Add manufacturing rules
        manufacturing_set = CapabilityRuleSet(domain="manufacturing")
        for rule in sample_rules[:2]:
            manufacturing_set.add_rule(rule)
        rule_manager.add_rule_set(manufacturing_set)
        
        # Add cooking rules
        cooking_set = CapabilityRuleSet(domain="cooking")
        cooking_set.add_rule(sample_rules[2])
        rule_manager.add_rule_set(cooking_set)
        
        matcher = CapabilityMatcher(rule_manager)
        await matcher.initialize()
        
        return matcher
    
    @pytest.mark.asyncio
    async def test_capability_can_satisfy_requirement(self, matcher):
        """Test capability to requirement matching"""
        # Test positive cases
        assert await matcher.capability_can_satisfy_requirement("cnc machining", "milling", "manufacturing")
        assert await matcher.capability_can_satisfy_requirement("3d printing", "additive manufacturing", "manufacturing")
        assert await matcher.capability_can_satisfy_requirement("sauté pan", "sauté", "cooking")
        
        # Test negative cases
        assert not await matcher.capability_can_satisfy_requirement("cnc machining", "additive manufacturing", "manufacturing")
        assert not await matcher.capability_can_satisfy_requirement("3d printing", "milling", "manufacturing")
        assert not await matcher.capability_can_satisfy_requirement("cnc machining", "sauté", "cooking")
        
        # Test case insensitive
        assert await matcher.capability_can_satisfy_requirement("CNC MACHINING", "MILLING", "manufacturing")
        assert await matcher.capability_can_satisfy_requirement("cnc machining", "MILLING", "manufacturing")
        
        # Test nonexistent domain
        assert not await matcher.capability_can_satisfy_requirement("cnc machining", "milling", "nonexistent")
    
    @pytest.mark.asyncio
    async def test_requirement_can_be_satisfied_by(self, matcher):
        """Test requirement to capability matching"""
        # Test positive cases
        assert await matcher.requirement_can_be_satisfied_by("milling", "cnc machining", "manufacturing")
        assert await matcher.requirement_can_be_satisfied_by("additive manufacturing", "3d printing", "manufacturing")
        assert await matcher.requirement_can_be_satisfied_by("sauté", "sauté pan", "cooking")
        
        # Test negative cases
        assert not await matcher.requirement_can_be_satisfied_by("additive manufacturing", "cnc machining", "manufacturing")
        assert not await matcher.requirement_can_be_satisfied_by("milling", "3d printing", "manufacturing")
        assert not await matcher.requirement_can_be_satisfied_by("milling", "sauté pan", "cooking")
    
    @pytest.mark.asyncio
    async def test_match_requirements_to_capabilities(self, matcher):
        """Test matching requirement objects to capability objects"""
        # Test data similar to what the matching service uses
        requirements = [
            {"process_name": "milling", "parameters": {"tolerance": "0.001"}},
            {"process_name": "additive manufacturing", "parameters": {"layer_height": "0.1"}},
            {"process_name": "welding", "parameters": {"current": "100A"}}
        ]
        
        capabilities = [
            {"process_name": "cnc machining", "parameters": {"max_tolerance": "0.0005"}},
            {"process_name": "3d printing", "parameters": {"layer_height": "0.05"}},
            {"process_name": "tig welding", "parameters": {"max_current": "200A"}}
        ]
        
        results = await matcher.match_requirements_to_capabilities(requirements, capabilities, "manufacturing")
        
        # Should have 9 results (3 requirements × 3 capabilities)
        assert len(results) == 9
        
        # Check specific matches
        milling_cnc_results = [r for r in results if r.requirement_value == "milling" and r.capability_value == "cnc machining"]
        assert len(milling_cnc_results) == 1
        assert milling_cnc_results[0].matched
        assert milling_cnc_results[0].confidence == 0.9
        assert milling_cnc_results[0].rule_used.id == "cnc_rule"
        
        additive_3d_results = [r for r in results if r.requirement_value == "additive manufacturing" and r.capability_value == "3d printing"]
        assert len(additive_3d_results) == 1
        assert additive_3d_results[0].matched
        assert additive_3d_results[0].confidence == 0.9
        assert additive_3d_results[0].rule_used.id == "additive_rule"
        
        # Check non-matches
        milling_3d_results = [r for r in results if r.requirement_value == "milling" and r.capability_value == "3d printing"]
        assert len(milling_3d_results) == 1
        assert not milling_3d_results[0].matched
        assert milling_3d_results[0].confidence == 0.0
        
        # Check that full objects are preserved
        for result in results:
            assert isinstance(result.requirement_object, dict)
            assert isinstance(result.capability_object, dict)
            assert "process_name" in result.requirement_object
            assert "process_name" in result.capability_object
    
    @pytest.mark.asyncio
    async def test_match_with_different_fields(self, matcher):
        """Test matching with different field names"""
        requirements = [
            {"material": "stainless steel", "grade": "304"},
            {"material": "aluminum", "grade": "6061"}
        ]
        
        capabilities = [
            {"material": "304 stainless", "grade": "304"},
            {"material": "aluminum", "grade": "6061"}
        ]
        
        # This should work but won't find matches since we don't have material rules
        results = await matcher.match_requirements_to_capabilities(
            requirements, capabilities, "manufacturing", 
            requirement_field="material", capability_field="material"
        )
        
        assert len(results) == 4  # 2 × 2
        # All should be non-matches since we don't have material rules
        for result in results:
            assert not result.matched
            assert result.requirement_field == "material"
            assert result.capability_field == "material"
    
    @pytest.mark.asyncio
    async def test_match_with_empty_values(self, matcher):
        """Test matching with empty values"""
        requirements = [
            {"process_name": "milling"},
            {"process_name": ""},  # Empty
            {"process_name": "   "},  # Whitespace only
            {}  # Missing field
        ]
        
        capabilities = [
            {"process_name": "cnc machining"},
            {"process_name": ""},  # Empty
            {"process_name": "   "},  # Whitespace only
            {}  # Missing field
        ]
        
        results = await matcher.match_requirements_to_capabilities(requirements, capabilities, "manufacturing")
        
        assert len(results) == 16  # 4 × 4
        
        # Check that empty/missing values result in non-matches
        for result in results:
            if not result.requirement_value or not result.capability_value:
                assert not result.matched
                assert result.confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test matcher initialization"""
        rule_manager = CapabilityRuleManager()
        matcher = CapabilityMatcher(rule_manager)
        
        assert not matcher._initialized
        
        await matcher.initialize()
        
        assert matcher._initialized
    
    @pytest.mark.asyncio
    async def test_ensure_initialized(self):
        """Test ensure_initialized method"""
        rule_manager = CapabilityRuleManager()
        matcher = CapabilityMatcher(rule_manager)
        
        assert not matcher._initialized
        
        await matcher.ensure_initialized()
        
        assert matcher._initialized


class TestCapabilityMatchResult:
    """Comprehensive tests for CapabilityMatchResult class"""
    
    def test_result_creation(self):
        """Test creating match results"""
        requirement_obj = {"process_name": "milling", "parameters": {"tolerance": "0.001"}}
        capability_obj = {"process_name": "cnc machining", "parameters": {"max_tolerance": "0.0005"}}
        
        rule = CapabilityRule(
            id="test_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling"],
            confidence=0.9
        )
        
        result = CapabilityMatchResult(
            requirement_object=requirement_obj,
            capability_object=capability_obj,
            requirement_field="process_name",
            capability_field="process_name",
            requirement_value="milling",
            capability_value="cnc machining",
            matched=True,
            confidence=0.9,
            rule_used=rule,
            domain="manufacturing",
            transformation_details=["Capability 'cnc machining' can satisfy requirement 'milling'"]
        )
        
        assert result.requirement_object == requirement_obj
        assert result.capability_object == capability_obj
        assert result.requirement_field == "process_name"
        assert result.capability_field == "process_name"
        assert result.requirement_value == "milling"
        assert result.capability_value == "cnc machining"
        assert result.matched
        assert result.confidence == 0.9
        assert result.rule_used == rule
        assert result.domain == "manufacturing"
        assert len(result.transformation_details) == 1
    
    def test_serialization(self):
        """Test result serialization"""
        requirement_obj = {"process_name": "milling"}
        capability_obj = {"process_name": "cnc machining"}
        
        rule = CapabilityRule(
            id="test_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling"],
            confidence=0.9
        )
        
        result = CapabilityMatchResult(
            requirement_object=requirement_obj,
            capability_object=capability_obj,
            requirement_field="process_name",
            capability_field="process_name",
            requirement_value="milling",
            capability_value="cnc machining",
            matched=True,
            confidence=0.9,
            rule_used=rule,
            domain="manufacturing"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["requirement_object"] == requirement_obj
        assert result_dict["capability_object"] == capability_obj
        assert result_dict["requirement_field"] == "process_name"
        assert result_dict["capability_field"] == "process_name"
        assert result_dict["requirement_value"] == "milling"
        assert result_dict["capability_value"] == "cnc machining"
        assert result_dict["matched"]
        assert result_dict["confidence"] == 0.9
        assert result_dict["rule_used"] is not None
        assert result_dict["domain"] == "manufacturing"


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_invalid_configuration_files(self):
        """Test handling of invalid configuration files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            rules_dir = Path(temp_dir) / "capability_rules"
            rules_dir.mkdir()
            
            # Create invalid YAML file
            with open(rules_dir / "invalid.yaml", 'w') as f:
                f.write("invalid: yaml: content: [")
            
            # Create file with missing required fields
            invalid_rules = {
                "domain": "test",
                "rules": {
                    "invalid_rule": {
                        "id": "invalid_rule",
                        # Missing required fields
                    }
                }
            }
            
            with open(rules_dir / "missing_fields.yaml", 'w') as f:
                yaml.dump(invalid_rules, f)
            
            # Should handle errors gracefully
            manager = CapabilityRuleManager(str(rules_dir))
            
            # Should not raise exception, but should log errors
            await manager.initialize()
            
            # Should have no rule sets due to errors
            assert len(manager.rule_sets) == 0
    
    @pytest.mark.asyncio
    async def test_nonexistent_rules_directory(self):
        """Test handling of nonexistent rules directory"""
        manager = CapabilityRuleManager("/nonexistent/directory")
        
        # Should handle gracefully
        await manager.initialize()
        
        # Should have no rule sets
        assert len(manager.rule_sets) == 0
    
    def test_rule_validation_edge_cases(self):
        """Test rule validation with edge cases"""
        # Test with None values
        with pytest.raises(ValueError):
            CapabilityRule(
                id="test",
                type=RuleType.CAPABILITY_MATCH,
                capability=None,
                satisfies_requirements=["milling"]
            )
        
        with pytest.raises(ValueError):
            CapabilityRule(
                id="test",
                type=RuleType.CAPABILITY_MATCH,
                capability="cnc machining",
                satisfies_requirements=None
            )
        
        # Test with whitespace-only values
        with pytest.raises(ValueError):
            CapabilityRule(
                id="test",
                type=RuleType.CAPABILITY_MATCH,
                capability="   ",
                satisfies_requirements=["milling"]
            )
        
        with pytest.raises(ValueError):
            CapabilityRule(
                id="test",
                type=RuleType.CAPABILITY_MATCH,
                capability="cnc machining",
                satisfies_requirements=["   "]
            )


if __name__ == "__main__":
    # Run a simple test to verify the system works
    print("Running comprehensive capability-centric rules system tests...")
    
    # This will run the tests if pytest is available
    try:
        import pytest
        pytest.main([__file__, "-v"])
    except ImportError:
        print("pytest not available, running basic tests...")
        
        # Run basic tests manually
        async def run_basic_tests():
            print("✓ Testing basic rule creation...")
            rule = CapabilityRule(
                id="test_rule",
                type=RuleType.CAPABILITY_MATCH,
                capability="cnc machining",
                satisfies_requirements=["milling"],
                confidence=0.9
            )
            assert rule.can_satisfy_requirement("milling")
            print("✓ Basic rule creation passed")
            
            print("✓ Testing rule set...")
            rule_set = CapabilityRuleSet(domain="manufacturing")
            rule_set.add_rule(rule)
            assert len(rule_set.rules) == 1
            print("✓ Rule set test passed")
            
            print("✓ Testing rule manager...")
            rule_manager = CapabilityRuleManager()
            rule_manager.add_rule_set(rule_set)
            assert len(rule_manager.rule_sets) == 1
            print("✓ Rule manager test passed")
            
            print("✓ Testing matcher...")
            matcher = CapabilityMatcher(rule_manager)
            await matcher.initialize()
            assert await matcher.capability_can_satisfy_requirement("cnc machining", "milling", "manufacturing")
            print("✓ Matcher test passed")
            
            print("✓ All basic tests passed!")
        
        asyncio.run(run_basic_tests())
