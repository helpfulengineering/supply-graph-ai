"""
Integration Tests for Capability-Centric Heuristic Rules System

This test suite focuses on integration scenarios:
- End-to-end matching workflows
- Real-world data scenarios
- Performance testing
- Configuration file integration
- API integration scenarios
"""

import pytest
import asyncio
import tempfile
import yaml
import json
import time
from pathlib import Path
from typing import Dict, List, Any

from src.core.matching.capability_rules import (
    CapabilityRule, CapabilityRuleSet, CapabilityRuleManager, CapabilityMatcher,
    CapabilityMatchResult, RuleType, RuleDirection
)


class TestEndToEndWorkflows:
    """Test complete end-to-end matching workflows"""
    
    @pytest.fixture
    async def full_system(self):
        """Create a complete system with real configuration files"""
        # Use the actual configuration files
        rules_dir = Path("src/core/matching/capability_rules")
        
        manager = CapabilityRuleManager(str(rules_dir))
        await manager.initialize()
        
        matcher = CapabilityMatcher(manager)
        await matcher.initialize()
        
        return manager, matcher
    
    @pytest.mark.asyncio
    async def test_manufacturing_workflow(self, full_system):
        """Test complete manufacturing matching workflow"""
        manager, matcher = full_system
        
        # Real-world manufacturing scenario
        requirements = [
            {"process_name": "milling", "parameters": {"tolerance": "0.001", "material": "aluminum"}},
            {"process_name": "drilling", "parameters": {"hole_diameter": "0.25", "depth": "1.0"}},
            {"process_name": "deburring", "parameters": {"finish": "smooth"}},
            {"process_name": "anodizing", "parameters": {"color": "black", "thickness": "0.001"}}
        ]
        
        capabilities = [
            {"process_name": "cnc machining", "parameters": {"max_tolerance": "0.0005", "materials": ["aluminum", "steel"]}},
            {"process_name": "manual machining", "parameters": {"max_tolerance": "0.005", "materials": ["aluminum"]}},
            {"process_name": "surface finishing", "parameters": {"finishes": ["smooth", "rough"]}},
            {"process_name": "coating", "parameters": {"types": ["anodizing", "painting"]}}
        ]
        
        # Test matching
        results = await matcher.match_requirements_to_capabilities(requirements, capabilities, "manufacturing")
        
        # Should have 16 results (4 × 4)
        assert len(results) == 16
        
        # Check specific expected matches
        milling_cnc_results = [r for r in results if r.requirement_value == "milling" and r.capability_value == "cnc machining"]
        assert len(milling_cnc_results) == 1
        assert milling_cnc_results[0].matched
        assert milling_cnc_results[0].confidence > 0.8
        
        # Check that all results have proper structure
        for result in results:
            assert isinstance(result.requirement_object, dict)
            assert isinstance(result.capability_object, dict)
            assert "process_name" in result.requirement_object
            assert "process_name" in result.capability_object
            assert result.requirement_field == "process_name"
            assert result.capability_field == "process_name"
            assert 0.0 <= result.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_cooking_workflow(self, full_system):
        """Test complete cooking matching workflow"""
        manager, matcher = full_system
        
        # Real-world cooking scenario
        requirements = [
            {"technique": "sauté", "parameters": {"heat": "medium-high", "time": "5min"}},
            {"technique": "boil", "parameters": {"heat": "high", "time": "10min"}},
            {"technique": "bake", "parameters": {"heat": "350F", "time": "30min"}},
            {"technique": "grill", "parameters": {"heat": "high", "time": "8min"}}
        ]
        
        capabilities = [
            {"technique": "sauté pan", "parameters": {"heat_range": "low-high", "capacity": "12inch"}},
            {"technique": "stock pot", "parameters": {"heat_range": "low-high", "capacity": "8qt"}},
            {"technique": "oven", "parameters": {"heat_range": "200F-500F", "capacity": "large"}},
            {"technique": "grill pan", "parameters": {"heat_range": "medium-high", "capacity": "10inch"}}
        ]
        
        # Test matching
        results = await matcher.match_requirements_to_capabilities(
            requirements, capabilities, "cooking", 
            requirement_field="technique", capability_field="technique"
        )
        
        # Should have 16 results (4 × 4)
        assert len(results) == 16
        
        # Check specific expected matches
        sauté_results = [r for r in results if r.requirement_value == "sauté" and r.capability_value == "sauté pan"]
        assert len(sauté_results) == 1
        assert sauté_results[0].matched
        assert sauté_results[0].confidence > 0.8
        
        # Check that all results have proper structure
        for result in results:
            assert isinstance(result.requirement_object, dict)
            assert isinstance(result.capability_object, dict)
            assert "technique" in result.requirement_object
            assert "technique" in result.capability_object
            assert result.requirement_field == "technique"
            assert result.capability_field == "technique"
    
    @pytest.mark.asyncio
    async def test_mixed_domain_workflow(self, full_system):
        """Test workflow with mixed domains"""
        manager, matcher = full_system
        
        # Test manufacturing domain
        manufacturing_requirements = [{"process_name": "milling"}]
        manufacturing_capabilities = [{"process_name": "cnc machining"}]
        
        manufacturing_results = await matcher.match_requirements_to_capabilities(
            manufacturing_requirements, manufacturing_capabilities, "manufacturing"
        )
        
        assert len(manufacturing_results) == 1
        assert manufacturing_results[0].matched
        assert manufacturing_results[0].domain == "manufacturing"
        
        # Test cooking domain
        cooking_requirements = [{"technique": "sauté"}]
        cooking_capabilities = [{"technique": "sauté pan"}]
        
        cooking_results = await matcher.match_requirements_to_capabilities(
            cooking_requirements, cooking_capabilities, "cooking",
            requirement_field="technique", capability_field="technique"
        )
        
        assert len(cooking_results) == 1
        assert cooking_results[0].matched
        assert cooking_results[0].domain == "cooking"
        
        # Test cross-domain (should not match)
        cross_domain_results = await matcher.match_requirements_to_capabilities(
            manufacturing_requirements, cooking_capabilities, "manufacturing"
        )
        
        assert len(cross_domain_results) == 1
        assert not cross_domain_results[0].matched


class TestRealWorldScenarios:
    """Test with real-world data scenarios"""
    
    @pytest.fixture
    async def real_world_system(self):
        """Create system with real-world configuration"""
        rules_dir = Path("src/core/matching/capability_rules")
        
        manager = CapabilityRuleManager(str(rules_dir))
        await manager.initialize()
        
        matcher = CapabilityMatcher(manager)
        await matcher.initialize()
        
        return manager, matcher
    
    @pytest.mark.asyncio
    async def test_okh_manifest_matching(self, real_world_system):
        """Test matching with OKH manifest data"""
        manager, matcher = real_world_system
        
        # Simulate OKH manifest requirements
        okh_requirements = [
            {"process_name": "cnc machining", "parameters": {"tolerance": "0.001"}},
            {"process_name": "surface treatment", "parameters": {"type": "anodizing"}},
            {"process_name": "assembly", "parameters": {"method": "mechanical"}}
        ]
        
        # Simulate facility capabilities
        facility_capabilities = [
            {"process_name": "cnc machining", "parameters": {"max_tolerance": "0.0005"}},
            {"process_name": "anodizing", "parameters": {"colors": ["black", "clear"]}},
            {"process_name": "mechanical assembly", "parameters": {"tools": ["screwdriver", "wrench"]}}
        ]
        
        results = await matcher.match_requirements_to_capabilities(okh_requirements, facility_capabilities, "manufacturing")
        
        # Check for expected matches
        cnc_matches = [r for r in results if r.requirement_value == "cnc machining" and r.capability_value == "cnc machining"]
        assert len(cnc_matches) == 1
        assert cnc_matches[0].matched
        
        # Check for surface treatment matches
        surface_matches = [r for r in results if r.requirement_value == "surface treatment" and r.capability_value == "anodizing"]
        assert len(surface_matches) == 1
        assert surface_matches[0].matched
    
    @pytest.mark.asyncio
    async def test_recipe_matching(self, real_world_system):
        """Test matching with recipe data"""
        manager, matcher = real_world_system
        
        # Simulate recipe requirements
        recipe_requirements = [
            {"equipment": "sauté pan", "parameters": {"size": "12inch"}},
            {"equipment": "oven", "parameters": {"temperature": "350F"}},
            {"equipment": "cutting board", "parameters": {"material": "wood"}}
        ]
        
        # Simulate kitchen capabilities
        kitchen_capabilities = [
            {"equipment": "sauté pan", "parameters": {"size": "10inch"}},
            {"equipment": "oven", "parameters": {"temperature_range": "200F-500F"}},
            {"equipment": "cutting board", "parameters": {"material": "plastic"}}
        ]
        
        results = await matcher.match_requirements_to_capabilities(
            recipe_requirements, kitchen_capabilities, "cooking",
            requirement_field="equipment", capability_field="equipment"
        )
        
        # Check for expected matches
        sauté_matches = [r for r in results if r.requirement_value == "sauté pan" and r.capability_value == "sauté pan"]
        assert len(sauté_matches) == 1
        assert sauté_matches[0].matched
        
        oven_matches = [r for r in results if r.requirement_value == "oven" and r.capability_value == "oven"]
        assert len(oven_matches) == 1
        assert oven_matches[0].matched
    
    @pytest.mark.asyncio
    async def test_partial_matching_scenario(self, real_world_system):
        """Test scenario where only some requirements are satisfied"""
        manager, matcher = real_world_system
        
        # Requirements that need multiple capabilities
        requirements = [
            {"process_name": "milling"},
            {"process_name": "welding"},
            {"process_name": "painting"}
        ]
        
        # Facility with only some capabilities
        capabilities = [
            {"process_name": "cnc machining"},  # Can satisfy milling
            {"process_name": "tig welding"},    # Can satisfy welding
            # No painting capability
        ]
        
        results = await matcher.match_requirements_to_capabilities(requirements, capabilities, "manufacturing")
        
        # Check results
        milling_matches = [r for r in results if r.requirement_value == "milling" and r.capability_value == "cnc machining"]
        assert len(milling_matches) == 1
        assert milling_matches[0].matched
        
        welding_matches = [r for r in results if r.requirement_value == "welding" and r.capability_value == "tig welding"]
        assert len(welding_matches) == 1
        assert welding_matches[0].matched
        
        # Painting should not match
        painting_matches = [r for r in results if r.requirement_value == "painting" and r.matched]
        assert len(painting_matches) == 0


class TestPerformance:
    """Test performance characteristics"""
    
    @pytest.fixture
    async def performance_system(self):
        """Create system for performance testing"""
        rules_dir = Path("src/core/matching/capability_rules")
        
        manager = CapabilityRuleManager(str(rules_dir))
        await manager.initialize()
        
        matcher = CapabilityMatcher(manager)
        await matcher.initialize()
        
        return manager, matcher
    
    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, performance_system):
        """Test performance with large datasets"""
        manager, matcher = performance_system
        
        # Create large datasets
        requirements = []
        capabilities = []
        
        # Generate 100 requirements
        for i in range(100):
            requirements.append({
                "process_name": f"process_{i % 10}",  # 10 different process types
                "parameters": {"id": i, "complexity": "medium"}
            })
        
        # Generate 100 capabilities
        for i in range(100):
            capabilities.append({
                "process_name": f"capability_{i % 15}",  # 15 different capability types
                "parameters": {"id": i, "capacity": "high"}
            })
        
        # Measure performance
        start_time = time.time()
        results = await matcher.match_requirements_to_capabilities(requirements, capabilities, "manufacturing")
        end_time = time.time()
        
        # Should complete in reasonable time (less than 5 seconds)
        execution_time = end_time - start_time
        assert execution_time < 5.0, f"Execution took {execution_time:.2f} seconds, expected < 5.0"
        
        # Should have correct number of results
        assert len(results) == 10000  # 100 × 100
        
        print(f"Performance test: {len(results)} matches in {execution_time:.2f} seconds")
    
    @pytest.mark.asyncio
    async def test_memory_usage(self, performance_system):
        """Test memory usage with large datasets"""
        manager, matcher = performance_system
        
        # Create moderately large datasets
        requirements = [{"process_name": f"process_{i}"} for i in range(50)]
        capabilities = [{"process_name": f"capability_{i}"} for i in range(50)]
        
        # Run multiple iterations to test memory stability
        for iteration in range(5):
            results = await matcher.match_requirements_to_capabilities(requirements, capabilities, "manufacturing")
            assert len(results) == 2500  # 50 × 50
            
            # Clear results to free memory
            del results
        
        print("Memory usage test completed successfully")


class TestConfigurationIntegration:
    """Test integration with configuration files"""
    
    @pytest.mark.asyncio
    async def test_manufacturing_config_loading(self):
        """Test loading manufacturing configuration"""
        rules_dir = Path("src/core/matching/capability_rules")
        
        manager = CapabilityRuleManager(str(rules_dir))
        await manager.initialize()
        
        # Check that manufacturing rules are loaded
        manufacturing_rules = manager.get_all_rules_for_domain("manufacturing")
        assert len(manufacturing_rules) > 0
        
        # Check for specific expected rules
        rule_ids = [rule.id for rule in manufacturing_rules]
        assert "cnc_machining_capability" in rule_ids
        assert "additive_manufacturing_capability" in rule_ids
        
        # Check rule content
        cnc_rule = manager.get_rule("manufacturing", "cnc_machining_capability")
        assert cnc_rule is not None
        assert "milling" in cnc_rule.satisfies_requirements
        assert "machining" in cnc_rule.satisfies_requirements
    
    @pytest.mark.asyncio
    async def test_cooking_config_loading(self):
        """Test loading cooking configuration"""
        rules_dir = Path("src/core/matching/capability_rules")
        
        manager = CapabilityRuleManager(str(rules_dir))
        await manager.initialize()
        
        # Check that cooking rules are loaded
        cooking_rules = manager.get_all_rules_for_domain("cooking")
        assert len(cooking_rules) > 0
        
        # Check for specific expected rules
        rule_ids = [rule.id for rule in cooking_rules]
        assert "sauté_pan_capability" in rule_ids
        assert "oven_capability" in rule_ids
        
        # Check rule content
        sauté_rule = manager.get_rule("cooking", "sauté_pan_capability")
        assert sauté_rule is not None
        assert "sauté" in sauté_rule.satisfies_requirements
        assert "pan-fry" in sauté_rule.satisfies_requirements
    
    @pytest.mark.asyncio
    async def test_config_reload(self):
        """Test configuration reloading"""
        rules_dir = Path("src/core/matching/capability_rules")
        
        manager = CapabilityRuleManager(str(rules_dir))
        await manager.initialize()
        
        # Get initial rule count
        initial_count = len(manager.get_all_rules_for_domain("manufacturing"))
        
        # Reload configuration
        await manager.reload_rules()
        
        # Should have same rule count
        reloaded_count = len(manager.get_all_rules_for_domain("manufacturing"))
        assert reloaded_count == initial_count
        
        # Rules should still work
        matcher = CapabilityMatcher(manager)
        await matcher.initialize()
        
        assert await matcher.capability_can_satisfy_requirement("cnc machining", "milling", "manufacturing")


class TestErrorRecovery:
    """Test error recovery and resilience"""
    
    @pytest.mark.asyncio
    async def test_missing_config_files(self):
        """Test handling of missing configuration files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            rules_dir = Path(temp_dir) / "capability_rules"
            rules_dir.mkdir()
            
            # Create empty directory
            manager = CapabilityRuleManager(str(rules_dir))
            await manager.initialize()
            
            # Should handle gracefully
            assert len(manager.rule_sets) == 0
            assert len(manager.get_available_domains()) == 0
    
    @pytest.mark.asyncio
    async def test_corrupted_config_files(self):
        """Test handling of corrupted configuration files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            rules_dir = Path(temp_dir) / "capability_rules"
            rules_dir.mkdir()
            
            # Create corrupted YAML file
            with open(rules_dir / "corrupted.yaml", 'w') as f:
                f.write("invalid: yaml: content: [")
            
            # Create valid file
            valid_rules = {
                "domain": "test",
                "version": "1.0.0",
                "description": "Test rules",
                "rules": {
                    "test_rule": {
                        "id": "test_rule",
                        "type": "capability_match",
                        "capability": "test capability",
                        "satisfies_requirements": ["test requirement"],
                        "confidence": 0.9,
                        "domain": "test"
                    }
                }
            }
            
            with open(rules_dir / "valid.yaml", 'w') as f:
                yaml.dump(valid_rules, f)
            
            manager = CapabilityRuleManager(str(rules_dir))
            await manager.initialize()
            
            # Should load valid rules and ignore corrupted ones
            assert len(manager.rule_sets) == 1
            assert "test" in manager.rule_sets
            assert len(manager.get_all_rules_for_domain("test")) == 1
    
    @pytest.mark.asyncio
    async def test_invalid_rule_data(self):
        """Test handling of invalid rule data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            rules_dir = Path(temp_dir) / "capability_rules"
            rules_dir.mkdir()
            
            # Create file with invalid rule data
            invalid_rules = {
                "domain": "test",
                "version": "1.0.0",
                "description": "Test rules",
                "rules": {
                    "invalid_rule": {
                        "id": "invalid_rule",
                        "type": "capability_match",
                        "capability": "",  # Invalid: empty capability
                        "satisfies_requirements": ["test requirement"],
                        "confidence": 0.9,
                        "domain": "test"
                    },
                    "valid_rule": {
                        "id": "valid_rule",
                        "type": "capability_match",
                        "capability": "valid capability",
                        "satisfies_requirements": ["test requirement"],
                        "confidence": 0.9,
                        "domain": "test"
                    }
                }
            }
            
            with open(rules_dir / "mixed.yaml", 'w') as f:
                yaml.dump(invalid_rules, f)
            
            manager = CapabilityRuleManager(str(rules_dir))
            await manager.initialize()
            
            # Should load valid rules and ignore invalid ones
            assert len(manager.rule_sets) == 1
            assert "test" in manager.rule_sets
            
            # Should have only the valid rule
            test_rules = manager.get_all_rules_for_domain("test")
            assert len(test_rules) == 1
            assert test_rules[0].id == "valid_rule"


if __name__ == "__main__":
    # Run integration tests
    print("Running capability-centric rules system integration tests...")
    
    try:
        import pytest
        pytest.main([__file__, "-v"])
    except ImportError:
        print("pytest not available, running basic integration tests...")
        
        async def run_basic_integration_tests():
            print("✓ Testing configuration loading...")
            rules_dir = Path("src/core/matching/capability_rules")
            manager = CapabilityRuleManager(str(rules_dir))
            await manager.initialize()
            
            assert len(manager.rule_sets) > 0
            print(f"✓ Loaded {len(manager.rule_sets)} rule sets")
            
            print("✓ Testing end-to-end matching...")
            matcher = CapabilityMatcher(manager)
            await matcher.initialize()
            
            requirements = [{"process_name": "milling"}]
            capabilities = [{"process_name": "cnc machining"}]
            
            results = await matcher.match_requirements_to_capabilities(requirements, capabilities, "manufacturing")
            assert len(results) == 1
            assert results[0].matched
            print("✓ End-to-end matching test passed")
            
            print("✓ All basic integration tests passed!")
        
        asyncio.run(run_basic_integration_tests())
