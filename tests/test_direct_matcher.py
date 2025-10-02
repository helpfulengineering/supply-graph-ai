"""
Unit tests for Direct Matching Layer

This module contains comprehensive unit tests for the Direct Matching layer,
covering edge cases, confidence scoring, and domain-specific functionality.
"""

import pytest
import time
from datetime import datetime
from typing import List, Dict, Any

from src.core.matching.direct_matcher import (
    DirectMatcher, DirectMatchResult, MatchMetadata, MatchQuality
)
from src.core.domains.cooking.direct_matcher import CookingDirectMatcher
from src.core.domains.manufacturing.direct_matcher import MfgDirectMatcher


class TestDirectMatcher:
    """Test cases for the base DirectMatcher class."""
    
    def test_levenshtein_distance(self):
        """Test Levenshtein distance calculation."""
        matcher = CookingDirectMatcher()
        
        # Test identical strings
        assert matcher._levenshtein_distance("hello", "hello") == 0
        
        # Test single character difference
        assert matcher._levenshtein_distance("hello", "hallo") == 1
        
        # Test multiple character differences
        assert matcher._levenshtein_distance("hello", "world") == 4
        
        # Test empty strings
        assert matcher._levenshtein_distance("", "") == 0
        assert matcher._levenshtein_distance("hello", "") == 5
        assert matcher._levenshtein_distance("", "hello") == 5
        
        # Test case sensitivity (should be case-sensitive)
        assert matcher._levenshtein_distance("Hello", "hello") == 1
    
    def test_whitespace_difference_detection(self):
        """Test whitespace difference detection."""
        matcher = CookingDirectMatcher()
        
        # Test identical strings
        assert not matcher._has_whitespace_difference("hello world", "hello world")
        
        # Test different whitespace
        assert matcher._has_whitespace_difference("hello world", "hello  world")  # Double space
        assert matcher._has_whitespace_difference("hello world", "hello\tworld")  # Tab vs space
        assert matcher._has_whitespace_difference("hello world", "hello\nworld")  # Newline vs space
        
        # Test leading/trailing whitespace
        assert matcher._has_whitespace_difference("hello world", " hello world")
        assert matcher._has_whitespace_difference("hello world", "hello world ")
        
        # Test multiple spaces normalized
        assert not matcher._has_whitespace_difference("hello   world", "hello world")
    
    def test_perfect_match(self):
        """Test perfect match detection."""
        matcher = CookingDirectMatcher()
        results = matcher.match("flour", ["flour"])
        
        assert len(results) == 1
        result = results[0]
        assert result.matched is True
        assert result.confidence == 1.0
        assert result.metadata.quality == MatchQuality.PERFECT
        assert result.metadata.case_difference is False
        assert result.metadata.whitespace_difference is False
    
    def test_case_difference_match(self):
        """Test case difference match detection."""
        matcher = CookingDirectMatcher()
        results = matcher.match("flour", ["Flour"])
        
        assert len(results) == 1
        result = results[0]
        assert result.matched is True
        assert result.confidence == 0.95
        assert result.metadata.quality == MatchQuality.CASE_DIFFERENCE
        assert result.metadata.case_difference is True
        assert result.metadata.whitespace_difference is False
    
    def test_whitespace_difference_match(self):
        """Test whitespace difference match detection."""
        matcher = CookingDirectMatcher()
        results = matcher.match("flour", [" flour "])
        
        assert len(results) == 1
        result = results[0]
        assert result.matched is True
        assert result.confidence == 0.95
        assert result.metadata.quality == MatchQuality.WHITESPACE_DIFFERENCE
        assert result.metadata.case_difference is False
        assert result.metadata.whitespace_difference is True
    
    def test_near_miss_detection(self):
        """Test near miss detection with typos."""
        matcher = CookingDirectMatcher()
        results = matcher.match("flour", ["flor"])  # 1 character difference
        
        assert len(results) == 1
        result = results[0]
        assert result.matched is False  # Not considered a match by direct matcher
        assert result.confidence == 0.8
        assert result.metadata.quality == MatchQuality.NEAR_MISS
        assert result.metadata.character_difference == 1
    
    def test_near_miss_threshold(self):
        """Test near miss threshold configuration."""
        matcher = CookingDirectMatcher(near_miss_threshold=1)
        results = matcher.match("flour", ["flor"])  # 1 character difference
        
        assert len(results) == 1
        result = results[0]
        assert result.matched is False
        assert result.confidence == 0.8
        assert result.metadata.quality == MatchQuality.NEAR_MISS
        
        # Test beyond threshold
        results = matcher.match("flour", ["flo"])  # 2 character differences
        assert len(results) == 1
        result = results[0]
        assert result.matched is False
        assert result.confidence == 0.0
        assert result.metadata.quality == MatchQuality.NO_MATCH
    
    def test_no_match(self):
        """Test no match detection."""
        matcher = CookingDirectMatcher()
        results = matcher.match("flour", ["sugar"])
        
        assert len(results) == 1
        result = results[0]
        assert result.matched is False
        assert result.confidence == 0.0
        assert result.metadata.quality == MatchQuality.NO_MATCH
        assert result.metadata.character_difference > 2
    
    def test_multiple_capabilities(self):
        """Test matching against multiple capabilities."""
        matcher = CookingDirectMatcher()
        results = matcher.match("flour", ["flour", "Flour", "sugar", "flor"])
        
        assert len(results) == 4
        
        # Check perfect match
        perfect_match = next(r for r in results if r.capability == "flour")
        assert perfect_match.matched is True
        assert perfect_match.confidence == 1.0
        
        # Check case difference match
        case_match = next(r for r in results if r.capability == "Flour")
        assert case_match.matched is True
        assert case_match.confidence == 0.95
        
        # Check no match
        no_match = next(r for r in results if r.capability == "sugar")
        assert no_match.matched is False
        assert no_match.confidence == 0.0
        
        # Check near miss
        near_miss = next(r for r in results if r.capability == "flor")
        assert near_miss.matched is False
        assert near_miss.confidence == 0.8
    
    def test_metadata_tracking(self):
        """Test comprehensive metadata tracking."""
        matcher = CookingDirectMatcher()
        results = matcher.match("flour", ["Flour"])
        
        assert len(results) == 1
        result = results[0]
        metadata = result.metadata
        
        # Check metadata fields
        assert metadata.method == "direct_match_cooking"
        assert metadata.confidence == 0.95
        assert len(metadata.reasons) > 0
        assert metadata.case_difference is True
        assert metadata.whitespace_difference is False
        assert metadata.quality == MatchQuality.CASE_DIFFERENCE
        assert metadata.processing_time_ms > 0
        assert isinstance(metadata.timestamp, datetime)
    
    def test_serialization(self):
        """Test result serialization to dictionary."""
        matcher = CookingDirectMatcher()
        results = matcher.match("flour", ["Flour"])
        
        assert len(results) == 1
        result = results[0]
        result_dict = result.to_dict()
        
        # Check result serialization
        assert result_dict["requirement"] == "flour"
        assert result_dict["capability"] == "Flour"
        assert result_dict["matched"] is True
        assert result_dict["confidence"] == 0.95
        
        # Check metadata serialization
        metadata_dict = result_dict["metadata"]
        assert metadata_dict["method"] == "direct_match_cooking"
        assert metadata_dict["confidence"] == 0.95
        assert metadata_dict["case_difference"] is True
        assert metadata_dict["quality"] == "case_diff"
        assert "timestamp" in metadata_dict


class TestCookingDirectMatcher:
    """Test cases for the CookingDirectMatcher class."""
    
    def test_ingredient_matching(self):
        """Test ingredient-specific matching."""
        matcher = CookingDirectMatcher()
        results = matcher.match_ingredients(
            ["flour", "sugar"],
            ["flour", "Flour", "sugar", "salt"]
        )
        
        assert len(results) == 8  # 2 requirements × 4 capabilities
        
        # Check flour matches
        flour_matches = [r for r in results if r.requirement == "flour"]
        assert len(flour_matches) == 4
        
        perfect_flour = next(r for r in flour_matches if r.capability == "flour")
        assert perfect_flour.matched is True
        assert perfect_flour.confidence == 1.0
        
        case_flour = next(r for r in flour_matches if r.capability == "Flour")
        assert case_flour.matched is True
        assert case_flour.confidence == 0.95
    
    def test_equipment_matching(self):
        """Test equipment-specific matching."""
        matcher = CookingDirectMatcher()
        results = matcher.match_equipment(
            ["knife", "cutting board"],
            ["knife", "Knife", "cutting board", "pan"]
        )
        
        assert len(results) == 8  # 2 requirements × 4 capabilities
        
        # Check knife matches
        knife_matches = [r for r in results if r.requirement == "knife"]
        assert len(knife_matches) == 4
        
        perfect_knife = next(r for r in knife_matches if r.capability == "knife")
        assert perfect_knife.matched is True
        assert perfect_knife.confidence == 1.0
    
    def test_technique_matching(self):
        """Test technique-specific matching."""
        matcher = CookingDirectMatcher()
        results = matcher.match_techniques(
            ["chop", "dice"],
            ["chop", "Chop", "dice", "slice"]
        )
        
        assert len(results) == 8  # 2 requirements × 4 capabilities
        
        # Check chop matches
        chop_matches = [r for r in results if r.requirement == "chop"]
        assert len(chop_matches) == 4
        
        perfect_chop = next(r for r in chop_matches if r.capability == "chop")
        assert perfect_chop.matched is True
        assert perfect_chop.confidence == 1.0
    
    def test_recipe_requirements_matching(self):
        """Test complete recipe requirements matching."""
        matcher = CookingDirectMatcher()
        
        recipe_data = {
            "ingredients": ["flour", "sugar"],
            "equipment": ["knife", "cutting board"],
            "techniques": ["chop", "dice"]
        }
        
        kitchen_capabilities = {
            "available_ingredients": ["flour", "sugar", "salt"],
            "available_equipment": ["knife", "cutting board", "pan"],
            "available_techniques": ["chop", "dice", "slice"]
        }
        
        results = matcher.match_recipe_requirements(recipe_data, kitchen_capabilities)
        
        # Check all categories are present
        assert "ingredients" in results
        assert "equipment" in results
        assert "techniques" in results
        
        # Check ingredients results
        ingredient_results = results["ingredients"]
        assert len(ingredient_results) == 6  # 2 requirements × 3 capabilities
        
        # Check equipment results
        equipment_results = results["equipment"]
        assert len(equipment_results) == 6  # 2 requirements × 3 capabilities
        
        # Check techniques results
        technique_results = results["techniques"]
        assert len(technique_results) == 6  # 2 requirements × 3 capabilities
    
    def test_domain_specific_confidence_adjustments(self):
        """Test domain-specific confidence adjustments."""
        matcher = CookingDirectMatcher()
        
        # Test ingredient matching gets boost
        adjustment = matcher.get_domain_specific_confidence_adjustments("flour", "sugar")
        assert adjustment > 1.0  # Should get boost for ingredient keywords
        
        # Test equipment matching gets boost
        adjustment = matcher.get_domain_specific_confidence_adjustments("knife", "cutting board")
        assert adjustment > 1.0  # Should get boost for equipment keywords
        
        # Test technique matching gets boost
        adjustment = matcher.get_domain_specific_confidence_adjustments("chop", "dice")
        assert adjustment > 1.0  # Should get boost for technique keywords
        
        # Test measurement unit matching gets boost
        adjustment = matcher.get_domain_specific_confidence_adjustments("1 cup flour", "2 cups sugar")
        assert adjustment > 1.0  # Should get boost for measurement keywords
        
        # Test mismatch penalty
        adjustment = matcher.get_domain_specific_confidence_adjustments("flour", "knife")
        assert adjustment < 1.0  # Should get penalty for ingredient vs equipment mismatch


class TestMfgDirectMatcher:
    """Test cases for the MfgDirectMatcher class."""
    
    def test_material_matching(self):
        """Test material-specific matching."""
        matcher = MfgDirectMatcher()
        results = matcher.match_materials(
            ["steel", "aluminum"],
            ["steel", "Steel", "aluminum", "copper"]
        )
        
        assert len(results) == 8  # 2 requirements × 4 capabilities
        
        # Check steel matches
        steel_matches = [r for r in results if r.requirement == "steel"]
        assert len(steel_matches) == 4
        
        perfect_steel = next(r for r in steel_matches if r.capability == "steel")
        assert perfect_steel.matched is True
        assert perfect_steel.confidence == 1.0
    
    def test_component_matching(self):
        """Test component-specific matching."""
        matcher = MfgDirectMatcher()
        results = matcher.match_components(
            ["bolt", "screw"],
            ["bolt", "Bolt", "screw", "nut"]
        )
        
        assert len(results) == 8  # 2 requirements × 4 capabilities
        
        # Check bolt matches
        bolt_matches = [r for r in results if r.requirement == "bolt"]
        assert len(bolt_matches) == 4
        
        perfect_bolt = next(r for r in bolt_matches if r.capability == "bolt")
        assert perfect_bolt.matched is True
        assert perfect_bolt.confidence == 1.0
    
    def test_tool_matching(self):
        """Test tool-specific matching."""
        matcher = MfgDirectMatcher()
        results = matcher.match_tools(
            ["drill", "mill"],
            ["drill", "Drill", "mill", "lathe"]
        )
        
        assert len(results) == 8  # 2 requirements × 4 capabilities
        
        # Check drill matches
        drill_matches = [r for r in results if r.requirement == "drill"]
        assert len(drill_matches) == 4
        
        perfect_drill = next(r for r in drill_matches if r.capability == "drill")
        assert perfect_drill.matched is True
        assert perfect_drill.confidence == 1.0
    
    def test_process_matching(self):
        """Test process-specific matching."""
        matcher = MfgDirectMatcher()
        results = matcher.match_processes(
            ["machining", "turning"],
            ["machining", "Machining", "turning", "milling"]
        )
        
        assert len(results) == 8  # 2 requirements × 4 capabilities
        
        # Check machining matches
        machining_matches = [r for r in results if r.requirement == "machining"]
        assert len(machining_matches) == 4
        
        perfect_machining = next(r for r in machining_matches if r.capability == "machining")
        assert perfect_machining.matched is True
        assert perfect_machining.confidence == 1.0
    
    def test_okh_requirements_matching(self):
        """Test complete OKH requirements matching."""
        matcher = MfgDirectMatcher()
        
        okh_data = {
            "materials": ["steel", "aluminum"],
            "components": ["bolt", "screw"],
            "tools": ["drill", "mill"],
            "processes": ["machining", "turning"]
        }
        
        okw_capabilities = {
            "available_materials": ["steel", "aluminum", "copper"],
            "available_components": ["bolt", "screw", "nut"],
            "available_tools": ["drill", "mill", "lathe"],
            "available_processes": ["machining", "turning", "milling"]
        }
        
        results = matcher.match_okh_requirements(okh_data, okw_capabilities)
        
        # Check all categories are present
        assert "materials" in results
        assert "components" in results
        assert "tools" in results
        assert "processes" in results
        
        # Check materials results
        material_results = results["materials"]
        assert len(material_results) == 6  # 2 requirements × 3 capabilities
        
        # Check components results
        component_results = results["components"]
        assert len(component_results) == 6  # 2 requirements × 3 capabilities
        
        # Check tools results
        tool_results = results["tools"]
        assert len(tool_results) == 6  # 2 requirements × 3 capabilities
        
        # Check processes results
        process_results = results["processes"]
        assert len(process_results) == 6  # 2 requirements × 3 capabilities
    
    def test_domain_specific_confidence_adjustments(self):
        """Test manufacturing domain-specific confidence adjustments."""
        matcher = MfgDirectMatcher()
        
        # Test material matching gets boost
        adjustment = matcher.get_domain_specific_confidence_adjustments("steel", "aluminum")
        assert adjustment > 1.0  # Should get boost for material keywords
        
        # Test component matching gets boost
        adjustment = matcher.get_domain_specific_confidence_adjustments("bolt", "screw")
        assert adjustment > 1.0  # Should get boost for component keywords
        
        # Test tool matching gets boost
        adjustment = matcher.get_domain_specific_confidence_adjustments("drill", "mill")
        assert adjustment > 1.0  # Should get boost for tool keywords
        
        # Test process matching gets boost
        adjustment = matcher.get_domain_specific_confidence_adjustments("machining", "turning")
        assert adjustment > 1.0  # Should get boost for process keywords
        
        # Test specification matching gets boost
        adjustment = matcher.get_domain_specific_confidence_adjustments("0.1mm tolerance", "0.2mm tolerance")
        assert adjustment > 1.0  # Should get boost for specification keywords
        
        # Test mismatch penalty
        adjustment = matcher.get_domain_specific_confidence_adjustments("steel", "drill")
        assert adjustment < 1.0  # Should get penalty for material vs tool mismatch


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_inputs(self):
        """Test handling of empty inputs."""
        matcher = CookingDirectMatcher()
        
        # Test empty requirement
        results = matcher.match("", ["flour"])
        assert len(results) == 1
        assert results[0].matched is False
        assert results[0].confidence == 0.0
        
        # Test empty capabilities
        results = matcher.match("flour", [])
        assert len(results) == 0
        
        # Test both empty
        results = matcher.match("", [])
        assert len(results) == 0
    
    def test_special_characters(self):
        """Test handling of special characters."""
        matcher = CookingDirectMatcher()
        
        # Test with punctuation
        results = matcher.match("flour,", ["flour,"])
        assert len(results) == 1
        assert results[0].matched is True
        assert results[0].confidence == 1.0
        
        # Test with numbers
        results = matcher.match("flour 1kg", ["flour 1kg"])
        assert len(results) == 1
        assert results[0].matched is True
        assert results[0].confidence == 1.0
        
        # Test with unicode characters
        results = matcher.match("café", ["café"])
        assert len(results) == 1
        assert results[0].matched is True
        assert results[0].confidence == 1.0
    
    def test_very_long_strings(self):
        """Test handling of very long strings."""
        matcher = CookingDirectMatcher()
        
        # Create very long strings
        long_req = "flour " * 1000
        long_cap = "flour " * 1000
        
        results = matcher.match(long_req, [long_cap])
        assert len(results) == 1
        assert results[0].matched is True
        assert results[0].confidence == 1.0
    
    def test_unicode_normalization(self):
        """Test handling of unicode normalization."""
        matcher = CookingDirectMatcher()
        
        # Test with different unicode representations
        results = matcher.match("café", ["café"])  # Different unicode representations
        assert len(results) == 1
        # The result depends on how Python handles unicode normalization
        # This test documents the current behavior
    
    def test_whitespace_edge_cases(self):
        """Test various whitespace edge cases."""
        matcher = CookingDirectMatcher()
        
        # Test with only whitespace
        results = matcher.match("   ", ["   "])
        assert len(results) == 1
        assert results[0].matched is True
        assert results[0].confidence == 1.0
        
        # Test with mixed whitespace
        results = matcher.match("flour\t\n", ["flour \t\n"])
        assert len(results) == 1
        assert results[0].matched is True
        assert results[0].confidence == 0.95  # Whitespace difference


class TestPerformance:
    """Test performance characteristics."""
    
    def test_large_capability_list(self):
        """Test performance with large capability lists."""
        matcher = CookingDirectMatcher()
        
        # Create large capability list
        capabilities = [f"ingredient_{i}" for i in range(1000)]
        
        start_time = time.time()
        results = matcher.match("ingredient_500", capabilities)
        end_time = time.time()
        
        # Should complete in reasonable time (less than 1 second)
        assert end_time - start_time < 1.0
        
        # Should find the exact match
        exact_match = next((r for r in results if r.capability == "ingredient_500"), None)
        assert exact_match is not None
        assert exact_match.matched is True
        assert exact_match.confidence == 1.0
    
    def test_multiple_requirements(self):
        """Test performance with multiple requirements."""
        matcher = CookingDirectMatcher()
        
        requirements = [f"req_{i}" for i in range(100)]
        capabilities = [f"cap_{i}" for i in range(100)]
        
        start_time = time.time()
        all_results = []
        for req in requirements:
            results = matcher.match(req, capabilities)
            all_results.extend(results)
        end_time = time.time()
        
        # Should complete in reasonable time
        assert end_time - start_time < 2.0
        
        # Should have correct number of results
        assert len(all_results) == 100 * 100  # 100 requirements × 100 capabilities
    
    def test_processing_time_tracking(self):
        """Test that processing time is tracked accurately."""
        matcher = CookingDirectMatcher()
        
        # Test with small input (should be very fast)
        results = matcher.match("flour", ["flour"])
        assert len(results) == 1
        assert results[0].metadata.processing_time_ms < 100  # Should be less than 100ms
        
        # Test with larger input
        capabilities = [f"cap_{i}" for i in range(100)]
        results = matcher.match("flour", capabilities)
        assert len(results) == 100
        # All results should have processing time tracked
        for result in results:
            assert result.metadata.processing_time_ms >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
