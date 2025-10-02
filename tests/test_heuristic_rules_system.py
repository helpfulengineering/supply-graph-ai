"""
Test the new Heuristic Rules System

This test validates the modular, extensible heuristic rules system
with domain separation and configuration-based rule loading.
"""

import pytest
import asyncio
import tempfile
import yaml
from pathlib import Path

from src.core.matching.heuristic_rules import (
    HeuristicRule, HeuristicRuleSet, HeuristicRuleManager,
    RuleType, RuleDirection
)
from src.core.matching.heuristic_matcher import HeuristicMatcher


class TestHeuristicRule:
    """Test individual heuristic rule functionality"""
    
    def test_rule_creation(self):
        """Test creating a heuristic rule"""
        rule = HeuristicRule(
            id="test_rule",
            type=RuleType.SYNONYM,
            key="cnc",
            values=["computer numerical control", "cnc machining"],
            confidence=0.9,
            domain="manufacturing"
        )
        
        assert rule.id == "test_rule"
        assert rule.type == RuleType.SYNONYM
        assert rule.key == "cnc"
        assert len(rule.values) == 2
        assert rule.confidence == 0.9
        assert rule.domain == "manufacturing"
    
    def test_rule_validation(self):
        """Test rule validation"""
        # Test empty key
        with pytest.raises(ValueError):
            HeuristicRule(
                id="test",
                type=RuleType.SYNONYM,
                key="",
                values=["test"]
            )
        
        # Test empty values
        with pytest.raises(ValueError):
            HeuristicRule(
                id="test",
                type=RuleType.SYNONYM,
                key="test",
                values=[]
            )
        
        # Test invalid confidence
        with pytest.raises(ValueError):
            HeuristicRule(
                id="test",
                type=RuleType.SYNONYM,
                key="test",
                values=["test"],
                confidence=1.5
            )
    
    def test_rule_applies_to(self):
        """Test rule application logic"""
        rule = HeuristicRule(
            id="cnc_rule",
            type=RuleType.SYNONYM,
            key="cnc",
            values=["computer numerical control", "cnc machining"],
            confidence=0.9
        )
        
        # Test bidirectional matching
        assert rule.applies_to("cnc", "computer numerical control")
        assert rule.applies_to("computer numerical control", "cnc")
        assert rule.applies_to("cnc machining", "computer numerical control")
        
        # Test case insensitive
        assert rule.applies_to("CNC", "Computer Numerical Control")
        
        # Test non-matching
        assert not rule.applies_to("cnc", "milling")
        assert not rule.applies_to("drilling", "computer numerical control")
    
    def test_rule_serialization(self):
        """Test rule serialization and deserialization"""
        rule = HeuristicRule(
            id="test_rule",
            type=RuleType.ABBREVIATION,
            key="cad",
            values=["computer aided design"],
            confidence=0.95,
            domain="manufacturing",
            description="Test rule"
        )
        
        # Test to_dict
        rule_dict = rule.to_dict()
        assert rule_dict["id"] == "test_rule"
        assert rule_dict["type"] == "abbreviation"
        assert rule_dict["key"] == "cad"
        
        # Test from_dict
        restored_rule = HeuristicRule.from_dict(rule_dict)
        assert restored_rule.id == rule.id
        assert restored_rule.type == rule.type
        assert restored_rule.key == rule.key
        assert restored_rule.values == rule.values


class TestHeuristicRuleSet:
    """Test heuristic rule set functionality"""
    
    def test_rule_set_creation(self):
        """Test creating a rule set"""
        rule_set = HeuristicRuleSet(
            domain="manufacturing",
            description="Test rule set"
        )
        
        assert rule_set.domain == "manufacturing"
        assert rule_set.description == "Test rule set"
        assert len(rule_set.rules) == 0
    
    def test_add_remove_rules(self):
        """Test adding and removing rules"""
        rule_set = HeuristicRuleSet(domain="manufacturing")
        
        rule = HeuristicRule(
            id="test_rule",
            type=RuleType.SYNONYM,
            key="cnc",
            values=["computer numerical control"]
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
        """Test finding matching rules"""
        rule_set = HeuristicRuleSet(domain="manufacturing")
        
        # Add multiple rules
        rule_set.add_rule(HeuristicRule(
            id="cnc_rule",
            type=RuleType.SYNONYM,
            key="cnc",
            values=["computer numerical control"],
            confidence=0.9
        ))
        
        rule_set.add_rule(HeuristicRule(
            id="cad_rule",
            type=RuleType.SYNONYM,
            key="cad",
            values=["computer aided design"],
            confidence=0.95
        ))
        
        # Test finding matching rules
        matching_rules = rule_set.find_matching_rules("cnc", "computer numerical control")
        assert len(matching_rules) == 1
        assert matching_rules[0].id == "cnc_rule"
        
        # Test best match
        best_match = rule_set.get_best_match("cad", "computer aided design")
        assert best_match is not None
        assert best_match.id == "cad_rule"
        assert best_match.confidence == 0.95


class TestHeuristicRuleManager:
    """Test heuristic rule manager functionality"""
    
    @pytest.fixture
    def temp_rules_dir(self):
        """Create temporary directory with test rule files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            rules_dir = Path(temp_dir) / "rules"
            rules_dir.mkdir()
            
            # Create test manufacturing rules
            manufacturing_rules = {
                "domain": "manufacturing",
                "version": "1.0.0",
                "description": "Test manufacturing rules",
                "rules": {
                    "cnc_rule": {
                        "id": "cnc_rule",
                        "type": "synonym",
                        "key": "cnc",
                        "values": ["computer numerical control"],
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
                        "type": "synonym",
                        "key": "sauté",
                        "values": ["saute", "pan-fry"],
                        "confidence": 0.95,
                        "domain": "cooking"
                    }
                }
            }
            
            with open(rules_dir / "cooking.yaml", 'w') as f:
                yaml.dump(cooking_rules, f)
            
            yield str(rules_dir)
    
    @pytest.mark.asyncio
    async def test_rule_manager_initialization(self, temp_rules_dir):
        """Test rule manager initialization"""
        manager = HeuristicRuleManager(temp_rules_dir)
        await manager.initialize()
        
        assert manager._initialized
        assert len(manager.rule_sets) == 2
        assert "manufacturing" in manager.rule_sets
        assert "cooking" in manager.rule_sets
    
    @pytest.mark.asyncio
    async def test_find_matching_rule(self, temp_rules_dir):
        """Test finding matching rules"""
        manager = HeuristicRuleManager(temp_rules_dir)
        await manager.initialize()
        
        # Test manufacturing rule
        rule = manager.find_matching_rule("cnc", "computer numerical control", "manufacturing")
        assert rule is not None
        assert rule.id == "cnc_rule"
        assert rule.confidence == 0.9
        
        # Test cooking rule
        rule = manager.find_matching_rule("sauté", "saute", "cooking")
        assert rule is not None
        assert rule.id == "sauté_rule"
        assert rule.confidence == 0.95
        
        # Test no match
        rule = manager.find_matching_rule("cnc", "baking", "cooking")
        assert rule is None
    
    @pytest.mark.asyncio
    async def test_rule_confidence(self, temp_rules_dir):
        """Test getting rule confidence"""
        manager = HeuristicRuleManager(temp_rules_dir)
        await manager.initialize()
        
        # Test matching confidence
        confidence = manager.get_rule_confidence("cnc", "computer numerical control", "manufacturing")
        assert confidence == 0.9
        
        # Test non-matching confidence
        confidence = manager.get_rule_confidence("cnc", "baking", "manufacturing")
        assert confidence == 0.0
    
    @pytest.mark.asyncio
    async def test_is_heuristic_match(self, temp_rules_dir):
        """Test heuristic match detection"""
        manager = HeuristicRuleManager(temp_rules_dir)
        await manager.initialize()
        
        # Test positive match
        assert manager.is_heuristic_match("cnc", "computer numerical control", "manufacturing", 0.8)
        
        # Test negative match (below threshold)
        assert not manager.is_heuristic_match("cnc", "computer numerical control", "manufacturing", 0.95)
        
        # Test no match
        assert not manager.is_heuristic_match("cnc", "baking", "manufacturing", 0.8)


class TestHeuristicMatcher:
    """Test heuristic matcher functionality"""
    
    @pytest.fixture
    def temp_rules_dir(self):
        """Create temporary directory with test rule files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            rules_dir = Path(temp_dir) / "rules"
            rules_dir.mkdir()
            
            # Create test rules
            rules = {
                "domain": "manufacturing",
                "version": "1.0.0",
                "description": "Test rules",
                "rules": {
                    "cnc_rule": {
                        "id": "cnc_rule",
                        "type": "synonym",
                        "key": "cnc",
                        "values": ["computer numerical control", "cnc machining"],
                        "confidence": 0.9,
                        "domain": "manufacturing"
                    }
                }
            }
            
            with open(rules_dir / "manufacturing.yaml", 'w') as f:
                yaml.dump(rules, f)
            
            yield str(rules_dir)
    
    @pytest.mark.asyncio
    async def test_heuristic_matcher_initialization(self, temp_rules_dir):
        """Test heuristic matcher initialization"""
        from src.core.matching.heuristic_rules import HeuristicRuleManager
        
        rule_manager = HeuristicRuleManager(temp_rules_dir)
        await rule_manager.initialize()
        
        matcher = HeuristicMatcher(rule_manager)
        await matcher.initialize()
        
        assert matcher._initialized
        assert matcher.rule_manager is not None
    
    @pytest.mark.asyncio
    async def test_heuristic_matching(self, temp_rules_dir):
        """Test heuristic matching functionality"""
        from src.core.matching.heuristic_rules import HeuristicRuleManager
        
        rule_manager = HeuristicRuleManager(temp_rules_dir)
        await rule_manager.initialize()
        
        matcher = HeuristicMatcher(rule_manager)
        await matcher.initialize()
        
        # Test matching
        results = await matcher.match(
            "cnc",
            ["computer numerical control", "milling", "cnc machining"],
            "manufacturing"
        )
        
        assert len(results) == 3
        
        # Check first result (should match)
        assert results[0].matched
        assert results[0].confidence == 0.9
        assert results[0].rule_used is not None
        assert results[0].rule_used.id == "cnc_rule"
        
        # Check second result (should not match)
        assert not results[1].matched
        assert results[1].confidence == 0.0
        
        # Check third result (should match)
        assert results[2].matched
        assert results[2].confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_is_match(self, temp_rules_dir):
        """Test is_match method"""
        from src.core.matching.heuristic_rules import HeuristicRuleManager
        
        rule_manager = HeuristicRuleManager(temp_rules_dir)
        await rule_manager.initialize()
        
        matcher = HeuristicMatcher(rule_manager)
        await matcher.initialize()
        
        # Test positive match
        assert await matcher.is_match("cnc", "computer numerical control", "manufacturing")
        
        # Test negative match
        assert not await matcher.is_match("cnc", "baking", "manufacturing")
    
    @pytest.mark.asyncio
    async def test_get_confidence(self, temp_rules_dir):
        """Test get_confidence method"""
        from src.core.matching.heuristic_rules import HeuristicRuleManager
        
        rule_manager = HeuristicRuleManager(temp_rules_dir)
        await rule_manager.initialize()
        
        matcher = HeuristicMatcher(rule_manager)
        await matcher.initialize()
        
        # Test matching confidence
        confidence = await matcher.get_confidence("cnc", "computer numerical control", "manufacturing")
        assert confidence == 0.9
        
        # Test non-matching confidence
        confidence = await matcher.get_confidence("cnc", "baking", "manufacturing")
        assert confidence == 0.0


if __name__ == "__main__":
    # Run a simple test to verify the system works
    async def simple_test():
        """Simple test to verify the heuristic rules system works"""
        print("Testing Heuristic Rules System...")
        
        # Test rule creation
        rule = HeuristicRule(
            id="test_rule",
            type=RuleType.SYNONYM,
            key="cnc",
            values=["computer numerical control"],
            confidence=0.9,
            domain="manufacturing"
        )
        
        print(f"✓ Created rule: {rule.id}")
        
        # Test rule application
        assert rule.applies_to("cnc", "computer numerical control")
        print("✓ Rule application works")
        
        # Test rule set
        rule_set = HeuristicRuleSet(domain="manufacturing")
        rule_set.add_rule(rule)
        
        best_match = rule_set.get_best_match("cnc", "computer numerical control")
        assert best_match is not None
        print("✓ Rule set functionality works")
        
        print("✓ All basic tests passed!")
    
    asyncio.run(simple_test())
