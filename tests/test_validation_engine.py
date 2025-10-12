"""
Tests for validation engine.

This module tests the ValidationEngine class and its integration with the domain system.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.core.validation.engine import ValidationEngine
from src.core.validation.context import ValidationContext
from src.core.validation.result import ValidationResult
from src.core.validation.exceptions import ValidationEngineError, DomainValidationError


class TestValidationEngine:
    """Test ValidationEngine class"""
    
    def test_validation_engine_creation(self):
        """Test creating a validation engine"""
        engine = ValidationEngine()
        assert engine.validators == {}
        assert engine.domain_registry is not None
    
    @pytest.mark.asyncio
    async def test_validate_without_context(self):
        """Test validation without context"""
        engine = ValidationEngine()
        data = {"test": "data"}
        
        result = await engine.validate(data, "test_type")
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    @pytest.mark.asyncio
    @patch('src.core.registry.domain_registry.DomainRegistry')
    async def test_validate_with_context(self, mock_registry):
        """Test validation with context"""
        # Mock domain registry
        mock_services = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate.return_value = {"valid": True, "issues": [], "warnings": []}
        mock_services.validator = mock_validator
        mock_registry.get_domain_services.return_value = mock_services
        
        engine = ValidationEngine()
        context = ValidationContext(
            name="test_context",
            domain="manufacturing",
            quality_level="professional"
        )
        data = {"test": "data"}
        
        result = await engine.validate(data, "test_type", context)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is True
        mock_validator.validate.assert_called_once_with(data)
    
    @pytest.mark.asyncio
    @patch('src.core.registry.domain_registry.DomainRegistry')
    async def test_validate_with_domain_validation_failure(self, mock_registry):
        """Test validation with domain validation failure"""
        # Mock domain registry
        mock_services = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate.return_value = {
            "valid": False, 
            "issues": ["Test validation failed"], 
            "warnings": []
        }
        mock_services.validator = mock_validator
        mock_registry.get_domain_services.return_value = mock_services
        
        engine = ValidationEngine()
        context = ValidationContext(
            name="test_context",
            domain="manufacturing",
            quality_level="professional"
        )
        data = {"test": "data"}
        
        result = await engine.validate(data, "test_type", context)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].message == "Test validation failed"
    
    @pytest.mark.asyncio
    @patch('src.core.registry.domain_registry.DomainRegistry')
    async def test_validate_with_invalid_quality_level(self, mock_registry):
        """Test validation with invalid quality level"""
        # Mock domain registry
        mock_services = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate.return_value = {"valid": True, "issues": [], "warnings": []}
        mock_services.validator = mock_validator
        mock_registry.get_domain_services.return_value = mock_services
        
        engine = ValidationEngine()
        context = ValidationContext(
            name="test_context",
            domain="manufacturing",
            quality_level="invalid_level"
        )
        data = {"test": "data"}
        
        result = await engine.validate(data, "test_type", context)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert len(result.errors) == 1
        assert "Invalid quality level" in result.errors[0].message
    
    @pytest.mark.asyncio
    @patch('src.core.registry.domain_registry.DomainRegistry')
    async def test_validate_with_custom_rules(self, mock_registry):
        """Test validation with custom rules"""
        # Mock domain registry
        mock_services = MagicMock()
        mock_validator = MagicMock()
        mock_validator.validate.return_value = {"valid": True, "issues": [], "warnings": []}
        mock_services.validator = mock_validator
        mock_registry.get_domain_services.return_value = mock_services
        
        engine = ValidationEngine()
        context = ValidationContext(
            name="test_context",
            domain="manufacturing",
            quality_level="professional",
            custom_rules={
                "required_fields": {
                    "required": ["title", "version"]
                }
            }
        )
        data = {"title": "Test"}  # Missing "version" field
        
        result = await engine.validate(data, "test_type", context)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert len(result.errors) == 1
        assert "Required field 'version' is missing" in result.errors[0].message
    
    def test_register_validator(self):
        """Test registering a validator"""
        engine = ValidationEngine()
        mock_validator = MagicMock()
        
        engine.register_validator("test_type", mock_validator)
        
        assert "test_type" in engine.validators
        assert len(engine.validators["test_type"]) == 1
        assert engine.validators["test_type"][0] == mock_validator
    
    def test_register_validator_with_priority(self):
        """Test registering a validator with priority"""
        engine = ValidationEngine()
        mock_validator1 = MagicMock()
        mock_validator2 = MagicMock()
        
        engine.register_validator("test_type", mock_validator1, priority=0)
        engine.register_validator("test_type", mock_validator2, priority=0)
        
        assert len(engine.validators["test_type"]) == 2
        assert engine.validators["test_type"][0] == mock_validator2  # Higher priority
        assert engine.validators["test_type"][1] == mock_validator1
    
    def test_get_registered_validators(self):
        """Test getting registered validators"""
        engine = ValidationEngine()
        mock_validator = MagicMock()
        
        engine.register_validator("test_type", mock_validator)
        validators = engine.get_registered_validators("test_type")
        
        assert len(validators) == 1
        assert validators[0] == mock_validator
    
    def test_clear_validators(self):
        """Test clearing validators"""
        engine = ValidationEngine()
        mock_validator = MagicMock()
        
        engine.register_validator("test_type", mock_validator)
        assert len(engine.validators["test_type"]) == 1
        
        engine.clear_validators("test_type")
        assert "test_type" not in engine.validators
    
    def test_clear_all_validators(self):
        """Test clearing all validators"""
        engine = ValidationEngine()
        mock_validator1 = MagicMock()
        mock_validator2 = MagicMock()
        
        engine.register_validator("test_type1", mock_validator1)
        engine.register_validator("test_type2", mock_validator2)
        
        engine.clear_validators()
        assert len(engine.validators) == 0
    
    def test_convert_dict_to_validation_result(self):
        """Test converting dictionary to ValidationResult"""
        engine = ValidationEngine()
        
        validation_dict = {
            "valid": False,
            "issues": ["Error 1", {"message": "Error 2", "field": "test_field", "code": "TEST_ERROR"}],
            "warnings": ["Warning 1"],
            "completeness_score": 0.8,
            "confidence": 0.9
        }
        
        result = engine._convert_dict_to_validation_result(validation_dict)
        
        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert len(result.errors) == 2
        assert result.errors[0].message == "Error 1"
        assert result.errors[1].message == "Error 2"
        assert result.errors[1].field == "test_field"
        assert result.errors[1].code == "TEST_ERROR"
        assert len(result.warnings) == 1
        assert result.warnings[0].message == "Warning 1"
        assert result.metadata["completeness_score"] == 0.8
        assert result.metadata["confidence"] == 0.9
