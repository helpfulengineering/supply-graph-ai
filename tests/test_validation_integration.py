"""
Integration tests for validation framework.

This module tests the integration between different validation framework components.
"""

import pytest
from src.core.validation import (
    ValidationEngine, ValidationContext, ValidationResult, 
    ValidationError, ValidationWarning, ValidationContextFactory
)
from src.core.validation.rules.manufacturing import ManufacturingValidationRules
from src.core.validation.rules.cooking import CookingValidationRules


class TestValidationFrameworkIntegration:
    """Test integration between validation framework components"""
    
    def test_validation_result_integration(self):
        """Test ValidationResult with ValidationError and ValidationWarning"""
        result = ValidationResult(valid=True)
        
        # Add error
        result.add_error("Test error", field="test_field", code="TEST_ERROR")
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].message == "Test error"
        assert result.errors[0].field == "test_field"
        assert result.errors[0].code == "TEST_ERROR"
        
        # Add warning
        result.add_warning("Test warning", field="test_field", code="TEST_WARNING")
        assert len(result.warnings) == 1
        assert result.warnings[0].message == "Test warning"
        
        # Test to_dict conversion
        result_dict = result.to_dict()
        assert result_dict["valid"] is False
        assert len(result_dict["errors"]) == 1
        assert len(result_dict["warnings"]) == 1
    
    def test_manufacturing_validation_rules_integration(self):
        """Test ManufacturingValidationRules integration"""
        rules = ManufacturingValidationRules()
        
        # Test quality level validation
        assert rules.validate_quality_level("hobby")
        assert rules.validate_quality_level("professional")
        assert rules.validate_quality_level("medical")
        assert not rules.validate_quality_level("invalid")
        
        # Test getting validation rules
        hobby_rules = rules.get_validation_rules("hobby")
        assert hobby_rules["validation_strictness"] == "relaxed"
        assert hobby_rules["allow_incomplete_docs"] is True
        assert hobby_rules["domain"] == "manufacturing"
        
        # Test getting required fields
        hobby_fields = rules.get_required_fields("hobby")
        professional_fields = rules.get_required_fields("professional")
        assert len(professional_fields) > len(hobby_fields)
        
        # Test missing required fields detection
        data = {"title": "Test", "version": "1.0.0"}  # Missing required fields
        missing = rules.get_missing_required_fields(data, "hobby")
        assert "license" in missing
        assert "licensor" in missing
    
    def test_cooking_validation_rules_integration(self):
        """Test CookingValidationRules integration"""
        rules = CookingValidationRules()
        
        # Test quality level validation
        assert rules.validate_quality_level("home")
        assert rules.validate_quality_level("commercial")
        assert rules.validate_quality_level("professional")
        assert not rules.validate_quality_level("invalid")
        
        # Test getting validation rules
        home_rules = rules.get_validation_rules("home")
        assert home_rules["validation_strictness"] == "relaxed"
        assert home_rules["allow_approximate_measurements"] is True
        assert home_rules["domain"] == "cooking"
        
        # Test getting required fields
        home_fields = rules.get_required_fields("home")
        professional_fields = rules.get_required_fields("professional")
        assert len(professional_fields) > len(home_fields)
        
        # Test missing required fields detection
        data = {"name": "Test Recipe"}  # Missing required fields
        missing = rules.get_missing_required_fields(data, "home")
        assert "ingredients" in missing
        assert "instructions" in missing
    
    def test_validation_context_factory_integration(self):
        """Test ValidationContextFactory integration"""
        # Test quality level validation
        assert ValidationContextFactory.validate_quality_level("manufacturing", "hobby")
        assert ValidationContextFactory.validate_quality_level("manufacturing", "professional")
        assert ValidationContextFactory.validate_quality_level("cooking", "home")
        assert not ValidationContextFactory.validate_quality_level("manufacturing", "home")
        
        # Test getting available quality levels
        manufacturing_levels = ValidationContextFactory.get_available_quality_levels("manufacturing")
        cooking_levels = ValidationContextFactory.get_available_quality_levels("cooking")
        
        assert manufacturing_levels == ["hobby", "professional", "medical"]
        assert cooking_levels == ["home", "commercial", "professional"]
        
        # Test domain detection
        manufacturing_req = {"okh": "test", "manufacturing": "data"}
        cooking_req = {"recipe": "test", "cooking": "data"}
        
        detected_manufacturing = ValidationContextFactory._detect_domain(manufacturing_req, {})
        detected_cooking = ValidationContextFactory._detect_domain(cooking_req, {})
        
        assert detected_manufacturing == "manufacturing"
        assert detected_cooking == "cooking"
    
    def test_validation_engine_basic_integration(self):
        """Test ValidationEngine basic integration"""
        engine = ValidationEngine()
        
        # Test validator registration
        mock_validator = MockValidator()
        engine.register_validator("test_type", mock_validator)
        
        validators = engine.get_registered_validators("test_type")
        assert len(validators) == 1
        assert validators[0] == mock_validator
        
        # Test validator clearing
        engine.clear_validators("test_type")
        validators = engine.get_registered_validators("test_type")
        assert len(validators) == 0
    
    def test_validation_result_merge_integration(self):
        """Test ValidationResult merge functionality"""
        result1 = ValidationResult(valid=True)
        result1.add_warning("Warning 1")
        
        result2 = ValidationResult(valid=False)
        result2.add_error("Error 1")
        result2.add_warning("Warning 2")
        result2.metadata["test"] = "value"
        
        # Merge results
        result1.merge(result2)
        
        assert result1.valid is False  # Should be invalid after merge
        assert len(result1.errors) == 1
        assert len(result1.warnings) == 2
        assert result1.metadata["test"] == "value"
        assert result1.errors[0].message == "Error 1"
        assert result1.warnings[0].message == "Warning 1"
        assert result1.warnings[1].message == "Warning 2"


class MockValidator:
    """Mock validator for testing"""
    
    def validate(self, data, context=None):
        """Mock validate method"""
        return {"valid": True, "issues": [], "warnings": []}
