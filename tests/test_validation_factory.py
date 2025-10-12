"""
Tests for validation context factory.

This module tests the ValidationContextFactory class.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.core.validation.factory import ValidationContextFactory
from src.core.validation.context import ValidationContext
from src.core.validation.exceptions import ValidationContextError


class TestValidationContextFactory:
    """Test ValidationContextFactory class"""
    
    @patch('src.core.validation.context.DomainRegistry')
    @patch('src.core.validation.factory.DomainRegistry')
    def test_create_context_valid_domain(self, mock_factory_registry, mock_context_registry):
        """Test creating context with valid domain"""
        # Mock domain registry
        mock_factory_registry.list_domains.return_value = ["manufacturing", "cooking"]
        mock_context_registry.list_domains.return_value = ["manufacturing", "cooking"]
        mock_metadata = MagicMock()
        mock_factory_registry.get_domain_metadata.return_value = mock_metadata
        
        context = ValidationContextFactory.create_context(
            domain_name="manufacturing",
            quality_level="professional",
            strict_mode=True
        )
        
        assert isinstance(context, ValidationContext)
        assert context.name == "manufacturing_professional"
        assert context.domain == "manufacturing"
        assert context.quality_level == "professional"
        assert context.strict_mode is True
    
    @patch('src.core.validation.factory.DomainRegistry')
    def test_create_context_invalid_domain(self, mock_registry):
        """Test creating context with invalid domain"""
        # Mock domain registry to return empty list
        mock_registry.list_domains.return_value = []
        
        with pytest.raises(ValidationContextError, match="Domain 'invalid_domain' not found"):
            ValidationContextFactory.create_context("invalid_domain")
    
    @patch('src.core.validation.factory.DomainRegistry')
    def test_create_manufacturing_context(self, mock_registry):
        """Test creating manufacturing context"""
        mock_registry.list_domains.return_value = ["manufacturing"]
        mock_metadata = MagicMock()
        mock_registry.get_domain_metadata.return_value = mock_metadata
        
        context = ValidationContextFactory.create_manufacturing_context(
            quality_level="hobby",
            strict_mode=False
        )
        
        assert isinstance(context, ValidationContext)
        assert context.domain == "manufacturing"
        assert context.quality_level == "hobby"
        assert context.strict_mode is False
    
    @patch('src.core.validation.factory.DomainRegistry')
    def test_create_cooking_context(self, mock_registry):
        """Test creating cooking context"""
        mock_registry.list_domains.return_value = ["cooking"]
        mock_metadata = MagicMock()
        mock_registry.get_domain_metadata.return_value = mock_metadata
        
        context = ValidationContextFactory.create_cooking_context(
            quality_level="commercial",
            strict_mode=True
        )
        
        assert isinstance(context, ValidationContext)
        assert context.domain == "cooking"
        assert context.quality_level == "commercial"
        assert context.strict_mode is True
    
    def test_create_context_from_detection_manufacturing(self):
        """Test creating context from detection with manufacturing keywords"""
        requirements = {"okh": "test", "manufacturing": "data"}
        capabilities = {"cnc": "machine"}
        
        with patch('src.core.validation.factory.DomainRegistry') as mock_registry:
            mock_registry.list_domains.return_value = ["manufacturing"]
            mock_metadata = MagicMock()
            mock_registry.get_domain_metadata.return_value = mock_metadata
            
            context = ValidationContextFactory.create_context_from_detection(
                requirements, capabilities, "professional"
            )
            
            assert isinstance(context, ValidationContext)
            assert context.domain == "manufacturing"
            assert context.quality_level == "professional"
    
    def test_create_context_from_detection_cooking(self):
        """Test creating context from detection with cooking keywords"""
        requirements = {"recipe": "test", "cooking": "data"}
        capabilities = {"oven": "appliance"}
        
        with patch('src.core.validation.factory.DomainRegistry') as mock_registry:
            mock_registry.list_domains.return_value = ["cooking"]
            mock_metadata = MagicMock()
            mock_registry.get_domain_metadata.return_value = mock_metadata
            
            context = ValidationContextFactory.create_context_from_detection(
                requirements, capabilities, "home"
            )
            
            assert isinstance(context, ValidationContext)
            assert context.domain == "cooking"
            assert context.quality_level == "home"
    
    def test_create_context_from_detection_default(self):
        """Test creating context from detection with no clear domain"""
        requirements = {"unknown": "data"}
        capabilities = {"unknown": "capability"}
        
        with patch('src.core.validation.factory.DomainRegistry') as mock_registry:
            mock_registry.list_domains.return_value = ["manufacturing"]
            mock_metadata = MagicMock()
            mock_registry.get_domain_metadata.return_value = mock_metadata
            
            context = ValidationContextFactory.create_context_from_detection(
                requirements, capabilities, "professional"
            )
            
            assert isinstance(context, ValidationContext)
            assert context.domain == "manufacturing"  # Default fallback
            assert context.quality_level == "professional"
    
    def test_get_available_quality_levels(self):
        """Test getting available quality levels for domains"""
        manufacturing_levels = ValidationContextFactory.get_available_quality_levels("manufacturing")
        assert manufacturing_levels == ["hobby", "professional", "medical"]
        
        cooking_levels = ValidationContextFactory.get_available_quality_levels("cooking")
        assert cooking_levels == ["home", "commercial", "professional"]
        
        unknown_levels = ValidationContextFactory.get_available_quality_levels("unknown")
        assert unknown_levels == []
    
    def test_validate_quality_level(self):
        """Test validating quality levels for domains"""
        # Valid quality levels
        assert ValidationContextFactory.validate_quality_level("manufacturing", "hobby")
        assert ValidationContextFactory.validate_quality_level("manufacturing", "professional")
        assert ValidationContextFactory.validate_quality_level("manufacturing", "medical")
        assert ValidationContextFactory.validate_quality_level("cooking", "home")
        assert ValidationContextFactory.validate_quality_level("cooking", "commercial")
        assert ValidationContextFactory.validate_quality_level("cooking", "professional")
        
        # Invalid quality levels
        assert not ValidationContextFactory.validate_quality_level("manufacturing", "home")
        assert not ValidationContextFactory.validate_quality_level("cooking", "hobby")
        assert not ValidationContextFactory.validate_quality_level("manufacturing", "invalid")
        assert not ValidationContextFactory.validate_quality_level("unknown", "professional")
    
    def test_detect_domain_manufacturing_keywords(self):
        """Test domain detection with manufacturing keywords"""
        requirements = {"okh": "test", "manufacturing": "data"}
        capabilities = {"cnc": "machine"}
        
        detected = ValidationContextFactory._detect_domain(requirements, capabilities)
        assert detected == "manufacturing"
    
    def test_detect_domain_cooking_keywords(self):
        """Test domain detection with cooking keywords"""
        requirements = {"recipe": "test", "cooking": "data"}
        capabilities = {"oven": "appliance"}
        
        detected = ValidationContextFactory._detect_domain(requirements, capabilities)
        assert detected == "cooking"
    
    def test_detect_domain_no_match(self):
        """Test domain detection with no matching keywords"""
        requirements = {"unknown": "data"}
        capabilities = {"unknown": "capability"}
        
        detected = ValidationContextFactory._detect_domain(requirements, capabilities)
        assert detected is None
