"""
Test-Driven Development for Capability-Centric Heuristic Rules

This test file defines the new rule structure and matching logic
for capability-centric heuristic rules that match requirements to capabilities.
"""

import pytest
import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Set
from enum import Enum

# We'll implement these classes based on the tests
from src.core.matching.capability_rules import (
    CapabilityRule, CapabilityRuleSet, CapabilityRuleManager, 
    CapabilityMatcher, RuleType, RuleDirection
)


class TestCapabilityRuleStructure:
    """Test the new capability-centric rule structure"""
    
    def test_capability_rule_creation(self):
        """Test creating a capability-centric rule"""
        rule = CapabilityRule(
            id="cnc_machining_capability",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling", "machining", "material removal"],
            confidence=0.9,
            domain="manufacturing",
            description="CNC machining can satisfy various milling requirements"
        )
        
        assert rule.id == "cnc_machining_capability"
        assert rule.type == RuleType.CAPABILITY_MATCH
        assert rule.capability == "cnc machining"
        assert rule.satisfies_requirements == ["milling", "machining", "material removal"]
        assert rule.confidence == 0.9
        assert rule.domain == "manufacturing"
    
    def test_capability_rule_validation(self):
        """Test rule validation"""
        # Test empty capability
        with pytest.raises(ValueError):
            CapabilityRule(
                id="test",
                type=RuleType.CAPABILITY_MATCH,
                capability="",
                satisfies_requirements=["milling"]
            )
        
        # Test empty requirements
        with pytest.raises(ValueError):
            CapabilityRule(
                id="test",
                type=RuleType.CAPABILITY_MATCH,
                capability="cnc machining",
                satisfies_requirements=[]
            )
        
        # Test invalid confidence
        with pytest.raises(ValueError):
            CapabilityRule(
                id="test",
                type=RuleType.CAPABILITY_MATCH,
                capability="cnc machining",
                satisfies_requirements=["milling"],
                confidence=1.5
            )
    
    def test_capability_rule_serialization(self):
        """Test rule serialization and deserialization"""
        rule = CapabilityRule(
            id="test_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="3d printing",
            satisfies_requirements=["additive manufacturing", "rapid prototyping"],
            confidence=0.95,
            domain="manufacturing"
        )
        
        # Test to_dict
        rule_dict = rule.to_dict()
        assert rule_dict["id"] == "test_rule"
        assert rule_dict["type"] == "capability_match"
        assert rule_dict["capability"] == "3d printing"
        assert rule_dict["satisfies_requirements"] == ["additive manufacturing", "rapid prototyping"]
        
        # Test from_dict
        restored_rule = CapabilityRule.from_dict(rule_dict)
        assert restored_rule.id == rule.id
        assert restored_rule.capability == rule.capability
        assert restored_rule.satisfies_requirements == rule.satisfies_requirements


class TestCapabilityMatching:
    """Test the capability-centric matching logic"""
    
    def test_capability_can_satisfy_requirement(self):
        """Test checking if a capability can satisfy a requirement"""
        rule = CapabilityRule(
            id="cnc_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling", "machining", "material removal"],
            confidence=0.9
        )
        
        # Test positive cases
        assert rule.can_satisfy_requirement("milling")
        assert rule.can_satisfy_requirement("MACHINING")  # Case insensitive
        assert rule.can_satisfy_requirement("material removal")
        
        # Test negative cases
        assert not rule.can_satisfy_requirement("3d printing")
        assert not rule.can_satisfy_requirement("welding")
        assert not rule.can_satisfy_requirement("")
    
    def test_requirement_can_be_satisfied_by_capability(self):
        """Test checking if a requirement can be satisfied by a capability"""
        rule = CapabilityRule(
            id="additive_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="3d printing",
            satisfies_requirements=["additive manufacturing", "rapid prototyping"],
            confidence=0.9
        )
        
        # Test positive cases
        assert rule.requirement_can_be_satisfied_by("additive manufacturing", "3d printing")
        assert rule.requirement_can_be_satisfied_by("RAPID PROTOTYPING", "3D PRINTING")  # Case insensitive
        
        # Test negative cases
        assert not rule.requirement_can_be_satisfied_by("milling", "3d printing")
        assert not rule.requirement_can_be_satisfied_by("additive manufacturing", "cnc machining")


class TestCapabilityRuleSet:
    """Test the capability rule set functionality"""
    
    def test_rule_set_creation(self):
        """Test creating a capability rule set"""
        rule_set = CapabilityRuleSet(domain="manufacturing")
        
        assert rule_set.domain == "manufacturing"
        assert len(rule_set.rules) == 0
    
    def test_add_remove_rules(self):
        """Test adding and removing rules"""
        rule_set = CapabilityRuleSet(domain="manufacturing")
        
        rule = CapabilityRule(
            id="test_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling"],
            confidence=0.9
        )
        
        # Add rule
        rule_set.add_rule(rule)
        assert len(rule_set.rules) == 1
        assert "test_rule" in rule_set.rules
        
        # Remove rule
        assert rule_set.remove_rule("test_rule")
        assert len(rule_set.rules) == 0
        assert not rule_set.remove_rule("nonexistent")
    
    def test_find_matching_rules(self):
        """Test finding rules that match capability-requirement pairs"""
        rule_set = CapabilityRuleSet(domain="manufacturing")
        
        # Add multiple rules
        rule_set.add_rule(CapabilityRule(
            id="cnc_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling", "machining"],
            confidence=0.9
        ))
        
        rule_set.add_rule(CapabilityRule(
            id="additive_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="3d printing",
            satisfies_requirements=["additive manufacturing"],
            confidence=0.9
        ))
        
        # Test finding matching rules
        matching_rules = rule_set.find_rules_for_capability_requirement("cnc machining", "milling")
        assert len(matching_rules) == 1
        assert matching_rules[0].id == "cnc_rule"
        
        # Test no match
        no_match = rule_set.find_rules_for_capability_requirement("cnc machining", "additive manufacturing")
        assert len(no_match) == 0


class TestCapabilityMatcher:
    """Test the capability matcher functionality"""
    
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
            )
        ]
    
    @pytest.mark.asyncio
    async def test_capability_can_satisfy_requirement(self, sample_rules):
        """Test checking if a capability can satisfy a requirement"""
        rule_manager = CapabilityRuleManager()
        rule_set = CapabilityRuleSet(domain="manufacturing")
        
        for rule in sample_rules:
            rule_set.add_rule(rule)
        
        rule_manager.add_rule_set(rule_set)
        matcher = CapabilityMatcher(rule_manager)
        await matcher.initialize()
        
        # Test positive cases
        assert await matcher.capability_can_satisfy_requirement("cnc machining", "milling", "manufacturing")
        assert await matcher.capability_can_satisfy_requirement("3d printing", "additive manufacturing", "manufacturing")
        
        # Test negative cases
        assert not await matcher.capability_can_satisfy_requirement("cnc machining", "additive manufacturing", "manufacturing")
        assert not await matcher.capability_can_satisfy_requirement("3d printing", "milling", "manufacturing")
    
    @pytest.mark.asyncio
    async def test_requirement_can_be_satisfied_by_capability(self, sample_rules):
        """Test checking if a requirement can be satisfied by a capability"""
        rule_manager = CapabilityRuleManager()
        rule_set = CapabilityRuleSet(domain="manufacturing")
        
        for rule in sample_rules:
            rule_set.add_rule(rule)
        
        rule_manager.add_rule_set(rule_set)
        matcher = CapabilityMatcher(rule_manager)
        await matcher.initialize()
        
        # Test positive cases
        assert await matcher.requirement_can_be_satisfied_by("milling", "cnc machining", "manufacturing")
        assert await matcher.requirement_can_be_satisfied_by("additive manufacturing", "3d printing", "manufacturing")
        
        # Test negative cases
        assert not await matcher.requirement_can_be_satisfied_by("additive manufacturing", "cnc machining", "manufacturing")
        assert not await matcher.requirement_can_be_satisfied_by("milling", "3d printing", "manufacturing")
    
    @pytest.mark.asyncio
    async def test_match_requirements_to_capabilities(self, sample_rules):
        """Test matching a list of requirements to a list of capabilities"""
        rule_manager = CapabilityRuleManager()
        rule_set = CapabilityRuleSet(domain="manufacturing")
        
        for rule in sample_rules:
            rule_set.add_rule(rule)
        
        rule_manager.add_rule_set(rule_set)
        matcher = CapabilityMatcher(rule_manager)
        await matcher.initialize()
        
        requirements = ["milling", "additive manufacturing"]
        capabilities = ["cnc machining", "3d printing", "welding"]
        
        results = await matcher.match_requirements_to_capabilities(requirements, capabilities, "manufacturing")
        
        # Should find matches for milling->cnc machining and additive manufacturing->3d printing
        assert len(results) == 2
        
        # Check specific matches
        milling_matches = [r for r in results if r.requirement == "milling"]
        assert len(milling_matches) == 1
        assert milling_matches[0].capability == "cnc machining"
        assert milling_matches[0].matched
        
        additive_matches = [r for r in results if r.requirement == "additive manufacturing"]
        assert len(additive_matches) == 1
        assert additive_matches[0].capability == "3d printing"
        assert additive_matches[0].matched


class TestConfigurationFileFormat:
    """Test the new configuration file format"""
    
    def test_manufacturing_rules_config(self):
        """Test loading manufacturing rules from configuration"""
        config_data = {
            "domain": "manufacturing",
            "version": "1.0.0",
            "description": "Capability-centric rules for manufacturing domain",
            "rules": {
                "cnc_machining_capability": {
                    "id": "cnc_machining_capability",
                    "type": "capability_match",
                    "capability": "cnc machining",
                    "satisfies_requirements": ["milling", "machining", "material removal"],
                    "confidence": 0.9,
                    "domain": "manufacturing",
                    "description": "CNC machining can satisfy various milling requirements"
                },
                "additive_manufacturing_capability": {
                    "id": "additive_manufacturing_capability",
                    "type": "capability_match",
                    "capability": "3d printing",
                    "satisfies_requirements": ["additive manufacturing", "rapid prototyping"],
                    "confidence": 0.9,
                    "domain": "manufacturing",
                    "description": "3D printing can satisfy additive manufacturing requirements"
                }
            }
        }
        
        rule_set = CapabilityRuleSet.from_dict(config_data)
        
        assert rule_set.domain == "manufacturing"
        assert len(rule_set.rules) == 2
        
        # Check specific rules
        cnc_rule = rule_set.get_rule("cnc_machining_capability")
        assert cnc_rule is not None
        assert cnc_rule.capability == "cnc machining"
        assert "milling" in cnc_rule.satisfies_requirements
        
        additive_rule = rule_set.get_rule("additive_manufacturing_capability")
        assert additive_rule is not None
        assert additive_rule.capability == "3d printing"
        assert "additive manufacturing" in additive_rule.satisfies_requirements


if __name__ == "__main__":
    # Run a simple test to verify the structure
    print("Testing Capability-Centric Rule Structure...")
    
    # This will fail until we implement the classes
    try:
        rule = CapabilityRule(
            id="test_rule",
            type=RuleType.CAPABILITY_MATCH,
            capability="cnc machining",
            satisfies_requirements=["milling"],
            confidence=0.9
        )
        print(f"✓ Created rule: {rule.id}")
        print(f"✓ Capability: {rule.capability}")
        print(f"✓ Can satisfy: {rule.satisfies_requirements}")
        print("✓ Basic capability-centric rule structure test passed!")
    except ImportError:
        print("✗ Classes not yet implemented - this is expected")
        print("✓ Test structure is ready for implementation")
