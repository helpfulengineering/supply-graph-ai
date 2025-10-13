"""
Tests for Phase 2 domain-specific validators.

This module tests the new domain-specific validators that integrate
with the validation framework.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from src.core.domains.manufacturing.validation.okh_validator import ManufacturingOKHValidator
from src.core.domains.manufacturing.validation.okw_validator import ManufacturingOKWValidator
from src.core.domains.cooking.validation.recipe_validator import CookingRecipeValidator
from src.core.domains.cooking.validation.kitchen_validator import CookingKitchenValidator
from src.core.validation.context import ValidationContext
from src.core.validation.result import ValidationResult
from src.core.models.okh import OKHManifest
from src.core.models.okw import ManufacturingFacility


class TestManufacturingOKHValidator:
    """Test ManufacturingOKHValidator"""
    
    @pytest.fixture
    def validator(self):
        return ManufacturingOKHValidator()
    
    @pytest.fixture
    def sample_okh_data(self):
        return {
            "title": "Test OKH Manifest",
            "version": "1.0.0",
            "license": "MIT",
            "licensor": "Test Author",
            "documentation_language": "en",
            "function": "Test function description",
            "description": "Test description",
            "manufacturing_processes": ["https://en.wikipedia.org/wiki/3D_printing"],
            "materials": ["PLA"],
            "tool_list": ["3D printer"]
        }
    
    def test_validation_type(self, validator):
        """Test validation type property"""
        assert validator.validation_type == "okh_manifest"
    
    def test_priority(self, validator):
        """Test priority property"""
        assert validator.priority == 100
    
    @pytest.mark.asyncio
    async def test_validate_dict_data(self, validator, sample_okh_data):
        """Test validation with dictionary data"""
        result = await validator.validate(sample_okh_data)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert 'completeness_score' in result.metadata
    
    @pytest.mark.asyncio
    async def test_validate_with_context(self, validator, sample_okh_data):
        """Test validation with validation context"""
        context = ValidationContext(
            name="test_context",
            domain="manufacturing",
            quality_level="professional"
        )
        
        result = await validator.validate(sample_okh_data, context)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
    
    @pytest.mark.asyncio
    async def test_validate_missing_required_fields(self, validator):
        """Test validation with missing required fields"""
        incomplete_data = {
            "title": "Test OKH",
            # Missing required fields
        }
        
        result = await validator.validate(incomplete_data)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_validate_invalid_data_type(self, validator):
        """Test validation with invalid data type"""
        result = await validator.validate("invalid data")
        
        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert len(result.errors) > 0
    
    def test_legacy_validate_okh_manifest(self, validator, sample_okh_data):
        """Test legacy validate_okh_manifest method"""
        # Create a mock OKHManifest
        okh_manifest = Mock()
        okh_manifest.to_dict.return_value = sample_okh_data
        
        result = validator.validate_okh_manifest(okh_manifest)
        
        assert isinstance(result, dict)
        assert 'completeness_score' in result


class TestManufacturingOKWValidator:
    """Test ManufacturingOKWValidator"""
    
    @pytest.fixture
    def validator(self):
        return ManufacturingOKWValidator()
    
    @pytest.fixture
    def sample_okw_data(self):
        return {
            "name": "Test Manufacturing Facility",
            "location": "123 Test St, Test City, TC 12345",
            "facility_status": "operational",
            "equipment": [
                {
                    "name": "Test CNC Mill",
                    "type": "cnc_mill",
                    "specifications": {"capacity": "1000x500x300mm"}
                }
            ],
            "manufacturing_processes": ["https://en.wikipedia.org/wiki/CNC_mill"],
            "typical_materials": [
                {
                    "material_type": "https://en.wikipedia.org/wiki/Aluminum",
                    "manufacturer": "Test Manufacturer",
                    "brand": "Test Brand"
                }
            ]
        }
    
    def test_validation_type(self, validator):
        """Test validation type property"""
        assert validator.validation_type == "okw_facility"
    
    def test_priority(self, validator):
        """Test priority property"""
        assert validator.priority == 90
    
    @pytest.mark.asyncio
    async def test_validate_dict_data(self, validator, sample_okw_data):
        """Test validation with dictionary data"""
        result = await validator.validate(sample_okw_data)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert 'capability_score' in result.metadata
    
    @pytest.mark.asyncio
    async def test_validate_with_context(self, validator, sample_okw_data):
        """Test validation with validation context"""
        context = ValidationContext(
            name="test_context",
            domain="manufacturing",
            quality_level="professional"
        )
        
        result = await validator.validate(sample_okw_data, context)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
    
    @pytest.mark.asyncio
    async def test_validate_missing_required_fields(self, validator):
        """Test validation with missing required fields"""
        incomplete_data = {
            "name": "Test Facility",
            # Missing required fields
        }
        
        result = await validator.validate(incomplete_data)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_validate_invalid_facility_status(self, validator, sample_okw_data):
        """Test validation with invalid facility status"""
        sample_okw_data["facility_status"] = "invalid_status"
        
        result = await validator.validate(sample_okw_data)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert len(result.errors) > 0


class TestCookingRecipeValidator:
    """Test CookingRecipeValidator"""
    
    @pytest.fixture
    def validator(self):
        return CookingRecipeValidator()
    
    @pytest.fixture
    def sample_recipe_data(self):
        return {
            "name": "Test Recipe",
            "ingredients": [
                {
                    "name": "Flour",
                    "quantity": "2",
                    "unit": "cups"
                },
                {
                    "name": "Sugar",
                    "quantity": "1",
                    "unit": "cup"
                }
            ],
            "instructions": [
                {
                    "description": "Mix flour and sugar together",
                    "time": "5 minutes"
                },
                {
                    "description": "Bake at 350°F for 30 minutes",
                    "temperature": "350°F"
                }
            ],
            "cooking_time": "35 minutes",
            "servings": 4
        }
    
    def test_validation_type(self, validator):
        """Test validation type property"""
        assert validator.validation_type == "recipe"
    
    def test_priority(self, validator):
        """Test priority property"""
        assert validator.priority == 80
    
    @pytest.mark.asyncio
    async def test_validate_dict_data(self, validator, sample_recipe_data):
        """Test validation with dictionary data"""
        result = await validator.validate(sample_recipe_data)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert 'completeness_score' in result.metadata
    
    @pytest.mark.asyncio
    async def test_validate_with_context(self, validator, sample_recipe_data):
        """Test validation with validation context"""
        context = ValidationContext(
            name="test_context",
            domain="cooking",
            quality_level="home"
        )
        
        result = await validator.validate(sample_recipe_data, context)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
    
    @pytest.mark.asyncio
    async def test_validate_missing_required_fields(self, validator):
        """Test validation with missing required fields"""
        incomplete_data = {
            "name": "Test Recipe",
            # Missing ingredients and instructions
        }
        
        result = await validator.validate(incomplete_data)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_validate_empty_ingredients(self, validator):
        """Test validation with empty ingredients"""
        data = {
            "name": "Test Recipe",
            "ingredients": [],
            "instructions": ["Test instruction"]
        }
        
        result = await validator.validate(data)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert len(result.errors) > 0


class TestCookingKitchenValidator:
    """Test CookingKitchenValidator"""
    
    @pytest.fixture
    def validator(self):
        return CookingKitchenValidator()
    
    @pytest.fixture
    def sample_kitchen_data(self):
        return {
            "name": "Test Kitchen",
            "location": "123 Test St, Test City, TC 12345",
            "equipment": [
                {
                    "name": "Test Stove",
                    "type": "stove",
                    "specifications": {"burners": 4}
                },
                {
                    "name": "Test Oven",
                    "type": "oven",
                    "specifications": {"capacity": "30L"}
                }
            ],
            "capacity": 8,
            "amenities": ["refrigerator", "dishwasher", "microwave"]
        }
    
    def test_validation_type(self, validator):
        """Test validation type property"""
        assert validator.validation_type == "kitchen"
    
    def test_priority(self, validator):
        """Test priority property"""
        assert validator.priority == 70
    
    @pytest.mark.asyncio
    async def test_validate_dict_data(self, validator, sample_kitchen_data):
        """Test validation with dictionary data"""
        result = await validator.validate(sample_kitchen_data)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert 'capability_score' in result.metadata
    
    @pytest.mark.asyncio
    async def test_validate_with_context(self, validator, sample_kitchen_data):
        """Test validation with validation context"""
        context = ValidationContext(
            name="test_context",
            domain="cooking",
            quality_level="home"
        )
        
        result = await validator.validate(sample_kitchen_data, context)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
    
    @pytest.mark.asyncio
    async def test_validate_missing_required_fields(self, validator):
        """Test validation with missing required fields"""
        incomplete_data = {
            "name": "Test Kitchen",
            # Missing location and equipment
        }
        
        result = await validator.validate(incomplete_data)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_validate_empty_equipment(self, validator):
        """Test validation with empty equipment"""
        data = {
            "name": "Test Kitchen",
            "location": "123 Test St",
            "equipment": []
        }
        
        result = await validator.validate(data)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert len(result.errors) > 0


class TestValidatorIntegration:
    """Test integration between validators and validation framework"""
    
    @pytest.mark.asyncio
    async def test_manufacturing_validators_integration(self):
        """Test that manufacturing validators work with validation framework"""
        okh_validator = ManufacturingOKHValidator()
        okw_validator = ManufacturingOKWValidator()
        
        # Test OKH validator
        okh_data = {
            "title": "Test OKH",
            "version": "1.0.0",
            "license": "MIT",
            "licensor": "Test Author",
            "documentation_language": "en",
            "function": "Test function"
        }
        
        okh_result = await okh_validator.validate(okh_data)
        assert isinstance(okh_result, ValidationResult)
        
        # Test OKW validator
        okw_data = {
            "name": "Test Facility",
            "location": "123 Test St",
            "facility_status": "operational",
            "equipment": [{"name": "Test Equipment", "type": "cnc_mill"}]
        }
        
        okw_result = await okw_validator.validate(okw_data)
        assert isinstance(okw_result, ValidationResult)
    
    @pytest.mark.asyncio
    async def test_cooking_validators_integration(self):
        """Test that cooking validators work with validation framework"""
        recipe_validator = CookingRecipeValidator()
        kitchen_validator = CookingKitchenValidator()
        
        # Test recipe validator
        recipe_data = {
            "name": "Test Recipe",
            "ingredients": [{"name": "Flour", "quantity": "2", "unit": "cups"}],
            "instructions": ["Mix ingredients"]
        }
        
        recipe_result = await recipe_validator.validate(recipe_data)
        assert isinstance(recipe_result, ValidationResult)
        
        # Test kitchen validator
        kitchen_data = {
            "name": "Test Kitchen",
            "location": "123 Test St",
            "equipment": [{"name": "Test Stove", "type": "stove"}]
        }
        
        kitchen_result = await kitchen_validator.validate(kitchen_data)
        assert isinstance(kitchen_result, ValidationResult)
    
    @pytest.mark.asyncio
    async def test_quality_level_validation(self):
        """Test that validators respect quality levels"""
        okh_validator = ManufacturingOKHValidator()
        
        # Test with professional quality level
        context_professional = ValidationContext(
            name="professional_context",
            domain="manufacturing",
            quality_level="professional"
        )
        
        # Test with hobby quality level
        context_hobby = ValidationContext(
            name="hobby_context",
            domain="manufacturing",
            quality_level="hobby"
        )
        
        # Same data should have different validation results based on quality level
        data = {
            "title": "Test OKH",
            "version": "1.0.0",
            "license": "MIT",
            "licensor": "Test Author",
            "documentation_language": "en",
            "function": "Test function"
        }
        
        professional_result = await okh_validator.validate(data, context_professional)
        hobby_result = await okh_validator.validate(data, context_hobby)
        
        # Both should be valid, but may have different completeness scores
        assert isinstance(professional_result, ValidationResult)
        assert isinstance(hobby_result, ValidationResult)
