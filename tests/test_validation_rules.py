"""
Tests for validation rules.

This module tests the BaseValidationRules, ManufacturingValidationRules, and CookingValidationRules classes.
"""

import pytest
from src.core.validation.rules.base import BaseValidationRules
from src.core.validation.rules.manufacturing import ManufacturingValidationRules
from src.core.validation.rules.cooking import CookingValidationRules


class TestBaseValidationRules:
    """Test BaseValidationRules abstract class"""
    
    def test_get_validation_strictness(self):
        """Test validation strictness mapping"""
        # Create a concrete implementation for testing
        class TestValidationRules(BaseValidationRules):
            def get_validation_rules(self, quality_level: str):
                return {}
            
            def get_required_fields(self, quality_level: str):
                return []
            
            def get_optional_fields(self, quality_level: str):
                return []
            
            def get_supported_quality_levels(self):
                return ["hobby", "professional", "medical"]
        
        rules = TestValidationRules()
        
        assert rules.get_validation_strictness("hobby") == "relaxed"
        assert rules.get_validation_strictness("home") == "relaxed"
        assert rules.get_validation_strictness("professional") == "standard"
        assert rules.get_validation_strictness("commercial") == "standard"
        assert rules.get_validation_strictness("medical") == "strict"
        assert rules.get_validation_strictness("unknown") == "standard"
    
    def test_get_all_fields(self):
        """Test getting all fields (required + optional)"""
        class TestValidationRules(BaseValidationRules):
            def get_validation_rules(self, quality_level: str):
                return {}
            
            def get_required_fields(self, quality_level: str):
                return ["field1", "field2"]
            
            def get_optional_fields(self, quality_level: str):
                return ["field2", "field3"]  # field2 is in both
            
            def get_supported_quality_levels(self):
                return ["test"]
        
        rules = TestValidationRules()
        all_fields = rules.get_all_fields("test")
        
        # Should contain all unique fields
        assert set(all_fields) == {"field1", "field2", "field3"}
    
    def test_get_missing_required_fields(self):
        """Test getting missing required fields"""
        class TestValidationRules(BaseValidationRules):
            def get_validation_rules(self, quality_level: str):
                return {}
            
            def get_required_fields(self, quality_level: str):
                return ["field1", "field2", "field3"]
            
            def get_optional_fields(self, quality_level: str):
                return []
            
            def get_supported_quality_levels(self):
                return ["test"]
        
        rules = TestValidationRules()
        
        # Test with missing fields
        data = {"field1": "value1", "field2": None, "field4": "value4"}
        missing = rules.get_missing_required_fields(data, "test")
        assert set(missing) == {"field2", "field3"}
        
        # Test with all fields present
        data = {"field1": "value1", "field2": "value2", "field3": "value3"}
        missing = rules.get_missing_required_fields(data, "test")
        assert missing == []
    
    def test_get_present_optional_fields(self):
        """Test getting present optional fields"""
        class TestValidationRules(BaseValidationRules):
            def get_validation_rules(self, quality_level: str):
                return {}
            
            def get_required_fields(self, quality_level: str):
                return []
            
            def get_optional_fields(self, quality_level: str):
                return ["field1", "field2", "field3"]
            
            def get_supported_quality_levels(self):
                return ["test"]
        
        rules = TestValidationRules()
        
        # Test with some optional fields present
        data = {"field1": "value1", "field2": None, "field4": "value4"}
        present = rules.get_present_optional_fields(data, "test")
        assert present == ["field1"]


class TestManufacturingValidationRules:
    """Test ManufacturingValidationRules class"""
    
    def test_get_supported_quality_levels(self):
        """Test getting supported quality levels"""
        rules = ManufacturingValidationRules()
        levels = rules.get_supported_quality_levels()
        assert levels == ["hobby", "professional", "medical"]
    
    def test_validate_quality_level(self):
        """Test quality level validation"""
        rules = ManufacturingValidationRules()
        
        # Valid levels
        assert rules.validate_quality_level("hobby")
        assert rules.validate_quality_level("professional")
        assert rules.validate_quality_level("medical")
        
        # Invalid levels
        assert not rules.validate_quality_level("home")
        assert not rules.validate_quality_level("invalid")
    
    def test_get_required_fields_hobby(self):
        """Test getting required fields for hobby level"""
        rules = ManufacturingValidationRules()
        fields = rules.get_required_fields("hobby")
        
        expected_base = ['title', 'version', 'license', 'licensor', 'documentation_language', 'function']
        assert fields == expected_base
    
    def test_get_required_fields_professional(self):
        """Test getting required fields for professional level"""
        rules = ManufacturingValidationRules()
        fields = rules.get_required_fields("professional")
        
        expected = ['title', 'version', 'license', 'licensor', 'documentation_language', 'function',
                   'manufacturing_specs', 'materials', 'manufacturing_processes']
        assert fields == expected
    
    def test_get_required_fields_medical(self):
        """Test getting required fields for medical level"""
        rules = ManufacturingValidationRules()
        fields = rules.get_required_fields("medical")
        
        expected = ['title', 'version', 'license', 'licensor', 'documentation_language', 'function',
                   'manufacturing_specs', 'materials', 'manufacturing_processes',
                   'quality_standards', 'certifications', 'regulatory_compliance']
        assert fields == expected
    
    def test_get_validation_rules_hobby(self):
        """Test getting validation rules for hobby level"""
        rules = ManufacturingValidationRules()
        validation_rules = rules.get_validation_rules("hobby")
        
        assert validation_rules['validation_strictness'] == 'relaxed'
        assert validation_rules['allow_incomplete_docs'] is True
        assert validation_rules['require_certifications'] is False
        assert validation_rules['domain'] == 'manufacturing'
    
    def test_get_validation_rules_medical(self):
        """Test getting validation rules for medical level"""
        rules = ManufacturingValidationRules()
        validation_rules = rules.get_validation_rules("medical")
        
        assert validation_rules['validation_strictness'] == 'strict'
        assert validation_rules['allow_incomplete_docs'] is False
        assert validation_rules['require_certifications'] is True
        assert validation_rules['require_regulatory_compliance'] is True
        assert validation_rules['require_traceability'] is True
    
    def test_static_okh_validation_rules(self):
        """Test static OKH validation rules method"""
        rules = ManufacturingValidationRules.get_okh_validation_rules("professional")
        assert 'required_fields' in rules
        assert 'validation_strictness' in rules
        assert rules['domain'] == 'manufacturing'
    
    def test_static_okw_validation_rules(self):
        """Test static OKW validation rules method"""
        rules = ManufacturingValidationRules.get_okw_validation_rules("professional")
        assert 'required_fields' in rules
        assert 'equipment_validation' in rules
        assert 'process_validation' in rules
        assert 'validation_strictness' in rules


class TestCookingValidationRules:
    """Test CookingValidationRules class"""
    
    def test_get_supported_quality_levels(self):
        """Test getting supported quality levels"""
        rules = CookingValidationRules()
        levels = rules.get_supported_quality_levels()
        assert levels == ["home", "commercial", "professional"]
    
    def test_validate_quality_level(self):
        """Test quality level validation"""
        rules = CookingValidationRules()
        
        # Valid levels
        assert rules.validate_quality_level("home")
        assert rules.validate_quality_level("commercial")
        assert rules.validate_quality_level("professional")
        
        # Invalid levels
        assert not rules.validate_quality_level("hobby")
        assert not rules.validate_quality_level("invalid")
    
    def test_get_required_fields_home(self):
        """Test getting required fields for home level"""
        rules = CookingValidationRules()
        fields = rules.get_required_fields("home")
        
        expected = ['name', 'ingredients', 'instructions']
        assert fields == expected
    
    def test_get_required_fields_professional(self):
        """Test getting required fields for professional level"""
        rules = CookingValidationRules()
        fields = rules.get_required_fields("professional")
        
        expected = ['name', 'ingredients', 'instructions', 'cooking_time', 'servings', 
                   'allergen_info', 'nutritional_info', 'food_safety_notes']
        assert fields == expected
    
    def test_get_validation_rules_home(self):
        """Test getting validation rules for home level"""
        rules = CookingValidationRules()
        validation_rules = rules.get_validation_rules("home")
        
        assert validation_rules['validation_strictness'] == 'relaxed'
        assert validation_rules['allow_approximate_measurements'] is True
        assert validation_rules['require_food_safety_certification'] is False
        assert validation_rules['domain'] == 'cooking'
    
    def test_get_validation_rules_professional(self):
        """Test getting validation rules for professional level"""
        rules = CookingValidationRules()
        validation_rules = rules.get_validation_rules("professional")
        
        assert validation_rules['validation_strictness'] == 'standard'
        assert validation_rules['allow_approximate_measurements'] is False
        assert validation_rules['require_food_safety_certification'] is True
        assert validation_rules['require_nutritional_analysis'] is True
        assert validation_rules['require_quality_standards'] is True
    
    def test_static_recipe_validation_rules(self):
        """Test static recipe validation rules method"""
        rules = CookingValidationRules.get_recipe_validation_rules("home")
        assert 'required_fields' in rules
        assert 'validation_strictness' in rules
        assert rules['domain'] == 'cooking'
    
    def test_static_kitchen_validation_rules(self):
        """Test static kitchen validation rules method"""
        rules = CookingValidationRules.get_kitchen_validation_rules("home")
        assert 'required_fields' in rules
        assert 'equipment_validation' in rules
        assert 'validation_strictness' in rules
