"""
Real integration tests for validation framework.

This module tests the validation framework with actual domain services
and real system components, not mocks.
"""

import pytest
import asyncio
from src.core.validation import (
    ValidationEngine, ValidationContext, ValidationResult, 
    ValidationError, ValidationWarning, ValidationContextFactory
)
from src.core.validation.rules.manufacturing import ManufacturingValidationRules
from src.core.validation.rules.cooking import CookingValidationRules
from src.core.domains.manufacturing.validation.okh_validator import ManufacturingOKHValidator
from src.core.domains.cooking.validation.recipe_validator import CookingRecipeValidator


class TestRealValidationIntegration:
    """Test validation framework with real domain services"""
    
    def test_validation_rules_with_real_data(self):
        """Test validation rules with real OKH data"""
        rules = ManufacturingValidationRules()
        
        # Test with real OKH data structure
        real_okh_data = {
            "title": "Arduino-based IoT Sensor Node",
            "version": "1.2.4",
            "license": {
                "hardware": "MIT",
                "documentation": "MIT", 
                "software": "MIT"
            },
            "licensor": "Open Hardware Community",
            "documentation_language": "en",
            "function": "Environmental monitoring sensor node",
            "description": "A complete IoT sensor node for environmental monitoring",
            "manufacturing_processes": [
                "https://en.wikipedia.org/wiki/3D_printing",
                "https://en.wikipedia.org/wiki/PCB_assembly"
            ],
            "materials": [
                {
                    "material_type": "https://en.wikipedia.org/wiki/PLA",
                    "manufacturer": "Generic PLA",
                    "brand": "Standard"
                }
            ],
            "tool_list": [
                "3D printer",
                "Soldering iron",
                "Multimeter"
            ],
            "manufacturing_specs": {
                "tolerance": "0.1mm",
                "layer_height": "0.2mm",
                "infill_percentage": 20
            }
        }
        
        # Test hobby level validation
        hobby_required = rules.get_required_fields("hobby")
        hobby_missing = rules.get_missing_required_fields(real_okh_data, "hobby")
        assert len(hobby_missing) == 0, f"Hobby level missing fields: {hobby_missing}"
        
        # Test professional level validation
        professional_required = rules.get_required_fields("professional")
        professional_missing = rules.get_missing_required_fields(real_okh_data, "professional")
        assert len(professional_missing) == 0, f"Professional level missing fields: {professional_missing}"
        
        # Test medical level validation (should have missing fields)
        medical_required = rules.get_required_fields("medical")
        medical_missing = rules.get_missing_required_fields(real_okh_data, "medical")
        assert len(medical_missing) > 0, f"Medical level should have missing fields: {medical_missing}"
        assert "quality_standards" in medical_missing
        assert "certifications" in medical_missing
    
    def test_cooking_validation_rules_with_real_data(self):
        """Test cooking validation rules with real recipe data"""
        rules = CookingValidationRules()
        
        # Test with real recipe data
        real_recipe_data = {
            "name": "Chocolate Chip Cookies",
            "ingredients": [
                {"name": "flour", "amount": "2 cups"},
                {"name": "sugar", "amount": "1 cup"},
                {"name": "chocolate chips", "amount": "1 cup"}
            ],
            "instructions": [
                "Mix dry ingredients",
                "Add wet ingredients",
                "Bake at 350°F for 12 minutes"
            ],
            "cooking_time": 12,
            "servings": 24,
            "description": "Classic chocolate chip cookies"
        }
        
        # Test home level validation
        home_required = rules.get_required_fields("home")
        home_missing = rules.get_missing_required_fields(real_recipe_data, "home")
        assert len(home_missing) == 0, f"Home level missing fields: {home_missing}"
        
        # Test commercial level validation
        commercial_required = rules.get_required_fields("commercial")
        commercial_missing = rules.get_missing_required_fields(real_recipe_data, "commercial")
        assert len(commercial_missing) == 0, f"Commercial level missing fields: {commercial_missing}"
        
        # Test professional level validation
        professional_required = rules.get_required_fields("professional")
        professional_missing = rules.get_missing_required_fields(real_recipe_data, "professional")
        assert len(professional_missing) == 0, f"Professional level missing fields: {professional_missing}"
    
    @pytest.mark.asyncio
    async def test_manufacturing_okh_validator_with_real_data(self):
        """Test ManufacturingOKHValidator with real OKH data"""
        validator = ManufacturingOKHValidator()
        
        # Test with complete OKH data
        complete_okh_data = {
            "title": "Professional IoT Sensor Node",
            "version": "2.0.0",
            "license": {
                "hardware": "MIT",
                "documentation": "MIT",
                "software": "MIT"
            },
            "licensor": "Professional Hardware Corp",
            "documentation_language": "en",
            "function": "Industrial IoT sensor node for environmental monitoring",
            "description": "A complete IoT sensor node for professional environmental monitoring",
            "manufacturing_processes": [
                "https://en.wikipedia.org/wiki/3D_printing",
                "https://en.wikipedia.org/wiki/PCB_assembly"
            ],
            "materials": [
                {
                    "material_type": "https://en.wikipedia.org/wiki/PLA",
                    "manufacturer": "Professional Materials Inc",
                    "brand": "ProPLA"
                }
            ],
            "tool_list": [
                "3D printer",
                "Soldering iron",
                "Multimeter",
                "Oscilloscope"
            ],
            "manufacturing_specs": {
                "tolerance": "0.1mm",
                "layer_height": "0.2mm",
                "infill_percentage": 20
            },
            "quality_standards": ["ISO 9001"],
            "certifications": ["CE marking"]
        }
        
        # Test professional level validation
        context = ValidationContext(
            name="test_professional",
            domain="manufacturing",
            quality_level="professional"
        )
        
        result = await validator.validate(complete_okh_data, context)
        assert isinstance(result, ValidationResult)
        assert result.valid is True, f"Professional validation failed: {result.errors}"
        assert result.metadata.get("completeness_score", 0) > 0.8
        
        # Test with incomplete data (hobby level)
        incomplete_okh_data = {
            "title": "Simple Sensor",
            "version": "1.0",
            "license": {"hardware": "MIT", "documentation": "MIT", "software": "MIT"},
            "licensor": "Maker",
            "documentation_language": "en",
            "function": "Basic sensor"
        }
        
        hobby_context = ValidationContext(
            name="test_hobby",
            domain="manufacturing", 
            quality_level="hobby"
        )
        
        result = await validator.validate(incomplete_okh_data, hobby_context)
        assert isinstance(result, ValidationResult)
        assert result.valid is True, f"Hobby validation failed: {result.errors}"
        assert len(result.warnings) > 0, "Should have warnings for missing optional fields"
    
    @pytest.mark.asyncio
    async def test_cooking_recipe_validator_with_real_data(self):
        """Test CookingRecipeValidator with real recipe data"""
        validator = CookingRecipeValidator()
        
        # Test with complete recipe data
        complete_recipe_data = {
            "name": "Professional Chocolate Chip Cookies",
            "ingredients": [
                {"name": "all-purpose flour", "amount": "2.25 cups", "type": "dry"},
                {"name": "baking soda", "amount": "1 tsp", "type": "leavening"},
                {"name": "salt", "amount": "1 tsp", "type": "seasoning"},
                {"name": "butter", "amount": "1 cup", "type": "fat"},
                {"name": "brown sugar", "amount": "0.75 cup", "type": "sweetener"},
                {"name": "granulated sugar", "amount": "0.75 cup", "type": "sweetener"},
                {"name": "vanilla extract", "amount": "2 tsp", "type": "flavoring"},
                {"name": "eggs", "amount": "2 large", "type": "binder"},
                {"name": "chocolate chips", "amount": "2 cups", "type": "mix-in"}
            ],
            "instructions": [
                "Preheat oven to 375°F (190°C)",
                "Mix flour, baking soda, and salt in a bowl",
                "Cream butter and sugars until light and fluffy",
                "Beat in vanilla and eggs one at a time",
                "Gradually blend in flour mixture",
                "Stir in chocolate chips",
                "Drop rounded tablespoons onto ungreased cookie sheets",
                "Bake 9-11 minutes until golden brown",
                "Cool on baking sheet for 2 minutes before removing"
            ],
            "cooking_time": 11,
            "servings": 48,
            "description": "Professional-grade chocolate chip cookies with precise measurements",
            "nutritional_info": {
                "calories_per_serving": 95,
                "fat": "5g",
                "carbs": "12g",
                "protein": "1g"
            },
            "allergen_info": ["gluten", "dairy", "eggs"]
        }
        
        # Test professional level validation
        context = ValidationContext(
            name="test_professional_cooking",
            domain="cooking",
            quality_level="professional"
        )
        
        result = await validator.validate(complete_recipe_data, context)
        assert isinstance(result, ValidationResult)
        assert result.valid is True, f"Professional cooking validation failed: {result.errors}"
        
        # Test with basic recipe data (home level)
        basic_recipe_data = {
            "name": "Simple Cookies",
            "ingredients": [
                {"name": "flour", "amount": "2 cups"},
                {"name": "sugar", "amount": "1 cup"},
                {"name": "chocolate chips", "amount": "1 cup"}
            ],
            "instructions": [
                "Mix ingredients",
                "Bake at 350°F for 12 minutes"
            ]
        }
        
        home_context = ValidationContext(
            name="test_home_cooking",
            domain="cooking",
            quality_level="home"
        )
        
        result = await validator.validate(basic_recipe_data, home_context)
        assert isinstance(result, ValidationResult)
        assert result.valid is True, f"Home cooking validation failed: {result.errors}"
    
    def test_validation_context_factory_with_real_domains(self):
        """Test ValidationContextFactory with real domain detection"""
        # Test domain keyword detection
        manufacturing_data = {
            "okh": "test",
            "manufacturing": "data",
            "cnc": "machine",
            "3d_printing": "process"
        }
        
        detected_domain = ValidationContextFactory.detect_domain_from_keywords(manufacturing_data)
        assert detected_domain == "manufacturing", f"Expected 'manufacturing', got '{detected_domain}'"
        
        cooking_data = {
            "recipe": "test",
            "cooking": "data",
            "oven": "appliance",
            "ingredients": "list"
        }
        
        detected_domain = ValidationContextFactory.detect_domain_from_keywords(cooking_data)
        assert detected_domain == "cooking", f"Expected 'cooking', got '{detected_domain}'"
        
        # Test quality level validation
        assert ValidationContextFactory.validate_quality_level("manufacturing", "hobby") is True
        assert ValidationContextFactory.validate_quality_level("manufacturing", "professional") is True
        assert ValidationContextFactory.validate_quality_level("manufacturing", "medical") is True
        assert ValidationContextFactory.validate_quality_level("manufacturing", "invalid") is False
        
        assert ValidationContextFactory.validate_quality_level("cooking", "home") is True
        assert ValidationContextFactory.validate_quality_level("cooking", "commercial") is True
        assert ValidationContextFactory.validate_quality_level("cooking", "professional") is True
        assert ValidationContextFactory.validate_quality_level("cooking", "invalid") is False
        
        # Test available quality levels
        manufacturing_levels = ValidationContextFactory.get_available_quality_levels("manufacturing")
        assert manufacturing_levels == ["hobby", "professional", "medical"]
        
        cooking_levels = ValidationContextFactory.get_available_quality_levels("cooking")
        assert cooking_levels == ["home", "commercial", "professional"]
    
    @pytest.mark.asyncio
    async def test_validation_engine_with_real_validators(self):
        """Test ValidationEngine with real domain validators"""
        engine = ValidationEngine()
        
        # Register real validators
        okh_validator = ManufacturingOKHValidator()
        recipe_validator = CookingRecipeValidator()
        
        engine.register_validator("okh_manifest", okh_validator, priority=100)
        engine.register_validator("recipe", recipe_validator, priority=100)
        
        # Test OKH validation
        okh_data = {
            "title": "Test OKH",
            "version": "1.0",
            "license": {"hardware": "MIT", "documentation": "MIT", "software": "MIT"},
            "licensor": "Test",
            "documentation_language": "en",
            "function": "Test function"
        }
        
        context = ValidationContext(
            name="test_okh",
            domain="manufacturing",
            quality_level="hobby"
        )
        
        result = await engine.validate(okh_data, "okh_manifest", context)
        assert isinstance(result, ValidationResult)
        assert result.valid is True, f"OKH validation failed: {result.errors}"
        
        # Test recipe validation
        recipe_data = {
            "name": "Test Recipe",
            "ingredients": [{"name": "flour", "amount": "1 cup"}],
            "instructions": ["Mix and bake"]
        }
        
        recipe_context = ValidationContext(
            name="test_recipe",
            domain="cooking",
            quality_level="home"
        )
        
        result = await engine.validate(recipe_data, "recipe", recipe_context)
        assert isinstance(result, ValidationResult)
        assert result.valid is True, f"Recipe validation failed: {result.errors}"
        
        # Test validation without context
        result = await engine.validate(okh_data, "okh_manifest")
        assert isinstance(result, ValidationResult)
        assert result.valid is True, f"OKH validation without context failed: {result.errors}"
    
    def test_validation_result_operations_with_real_data(self):
        """Test ValidationResult operations with real validation data"""
        result1 = ValidationResult(valid=True)
        result1.add_warning("Missing optional field: description", field="description", code="optional_field_missing")
        
        result2 = ValidationResult(valid=True)
        result2.add_error("Missing required field: version", field="version", code="required_field_missing")
        
        # Test merging results
        result1.merge(result2)
        assert result1.valid is False, "Merged result should be invalid"
        assert len(result1.errors) == 1, f"Expected 1 error, got {len(result1.errors)}"
        assert len(result1.warnings) == 1, f"Expected 1 warning, got {len(result1.warnings)}"
        
        # Test to_dict conversion
        result_dict = result1.to_dict()
        assert "valid" in result_dict
        assert "errors" in result_dict
        assert "warnings" in result_dict
        assert "metadata" in result_dict
        assert len(result_dict["errors"]) == 1
        assert len(result_dict["warnings"]) == 1
        
        # Test error and warning details
        error = result_dict["errors"][0]
        assert error["message"] == "Missing required field: version"
        assert error["field"] == "version"
        assert error["code"] == "required_field_missing"
        
        warning = result_dict["warnings"][0]
        assert warning["message"] == "Missing optional field: description"
        assert warning["field"] == "description"
        assert warning["code"] == "optional_field_missing"
