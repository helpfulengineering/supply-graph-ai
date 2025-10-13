"""
Tests for validation context.

This module tests the ValidationContext class and its integration with the domain system.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.core.validation.context import ValidationContext
from src.core.validation.exceptions import ValidationContextError


class TestValidationContext:
    """Test ValidationContext class"""
    
    @patch('src.core.registry.domain_registry.DomainRegistry')
    def test_validation_context_creation_valid_domain(self, mock_registry):
        """Test creating a validation context with a valid domain"""
        # Mock the domain registry
        mock_registry.list_domains.return_value = ["manufacturing", "cooking"]
        mock_services = MagicMock()
        mock_metadata = MagicMock()
        mock_services.metadata = mock_metadata
        mock_registry.get_domain_services.return_value = mock_services
        
        context = ValidationContext(
            name="test_context",
            domain="manufacturing",
            quality_level="professional"
        )
        
        assert context.name == "test_context"
        assert context.domain == "manufacturing"
        assert context.quality_level == "professional"
        assert context.strict_mode is False
        assert len(context.custom_rules) == 0
    
    @patch('src.core.registry.domain_registry.DomainRegistry')
    def test_validation_context_creation_invalid_domain(self, mock_registry):
        """Test creating a validation context with an invalid domain"""
        # Mock the domain registry to return empty list
        mock_registry.list_domains.return_value = []
        
        with pytest.raises(ValueError, match="Domain 'invalid_domain' is not registered"):
            ValidationContext(
                name="test_context",
                domain="invalid_domain",
                quality_level="professional"
            )
    
    @patch('src.core.registry.domain_registry.DomainRegistry')
    def test_validation_context_with_custom_rules(self, mock_registry):
        """Test creating a validation context with custom rules"""
        mock_registry.list_domains.return_value = ["manufacturing"]
        mock_services = MagicMock()
        mock_metadata = MagicMock()
        mock_services.metadata = mock_metadata
        mock_registry.get_domain_services.return_value = mock_services
        
        custom_rules = {"custom_field": "custom_value"}
        context = ValidationContext(
            name="test_context",
            domain="manufacturing",
            quality_level="professional",
            strict_mode=True,
            custom_rules=custom_rules
        )
        
        assert context.strict_mode is True
        assert context.custom_rules == custom_rules
    
    def test_is_quality_level_valid_manufacturing(self):
        """Test quality level validation for manufacturing domain"""
        with patch('src.core.registry.domain_registry.DomainRegistry') as mock_registry:
            mock_registry.list_domains.return_value = ["manufacturing"]
            mock_services = MagicMock()
            mock_metadata = MagicMock()
            mock_services.metadata = mock_metadata
            mock_registry.get_domain_services.return_value = mock_services
            
            # Test valid quality levels
            for quality_level in ["hobby", "professional", "medical"]:
                context = ValidationContext(
                    name="test",
                    domain="manufacturing",
                    quality_level=quality_level
                )
                assert context.is_quality_level_valid()
            
            # Test invalid quality level
            context = ValidationContext(
                name="test",
                domain="manufacturing",
                quality_level="invalid"
            )
            assert not context.is_quality_level_valid()
    
    def test_is_quality_level_valid_cooking(self):
        """Test quality level validation for cooking domain"""
        with patch('src.core.registry.domain_registry.DomainRegistry') as mock_registry:
            mock_registry.list_domains.return_value = ["cooking"]
            mock_services = MagicMock()
            mock_metadata = MagicMock()
            mock_services.metadata = mock_metadata
            mock_registry.get_domain_services.return_value = mock_services
            
            # Test valid quality levels
            for quality_level in ["home", "commercial", "professional"]:
                context = ValidationContext(
                    name="test",
                    domain="cooking",
                    quality_level=quality_level
                )
                assert context.is_quality_level_valid()
            
            # Test invalid quality level
            context = ValidationContext(
                name="test",
                domain="cooking",
                quality_level="invalid"
            )
            assert not context.is_quality_level_valid()
    
    def test_get_validation_strictness(self):
        """Test validation strictness calculation"""
        with patch('src.core.registry.domain_registry.DomainRegistry') as mock_registry:
            mock_registry.list_domains.return_value = ["manufacturing"]
            mock_services = MagicMock()
            mock_metadata = MagicMock()
            mock_services.metadata = mock_metadata
            mock_registry.get_domain_services.return_value = mock_services
            
            # Test strict mode
            context = ValidationContext(
                name="test",
                domain="manufacturing",
                quality_level="hobby",
                strict_mode=True
            )
            assert context.get_validation_strictness() == "strict"
            
            # Test quality level based strictness
            test_cases = [
                ("hobby", "relaxed"),
                ("professional", "standard"),
                ("medical", "strict"),
                ("home", "relaxed"),
                ("commercial", "standard"),
                ("invalid", "standard")  # Default fallback
            ]
            
            for quality_level, expected_strictness in test_cases:
                context = ValidationContext(
                    name="test",
                    domain="manufacturing",
                    quality_level=quality_level,
                    strict_mode=False
                )
                assert context.get_validation_strictness() == expected_strictness
    
    def test_to_dict(self):
        """Test converting validation context to dictionary"""
        with patch('src.core.registry.domain_registry.DomainRegistry') as mock_registry:
            mock_registry.list_domains.return_value = ["manufacturing"]
            mock_services = MagicMock()
            mock_metadata = MagicMock()
            mock_services.metadata = mock_metadata
            mock_registry.get_domain_services.return_value = mock_services
            
            context = ValidationContext(
                name="test_context",
                domain="manufacturing",
                quality_level="professional",
                strict_mode=True,
                custom_rules={"test": "value"}
            )
            
            result = context.to_dict()
            expected = {
                "name": "test_context",
                "domain": "manufacturing",
                "quality_level": "professional",
                "strict_mode": True,
                "custom_rules": {"test": "value"},
                "validation_strictness": "strict"
            }
            assert result == expected
    
    def test_from_dict(self):
        """Test creating validation context from dictionary"""
        with patch('src.core.registry.domain_registry.DomainRegistry') as mock_registry:
            mock_registry.list_domains.return_value = ["manufacturing"]
            mock_services = MagicMock()
            mock_metadata = MagicMock()
            mock_services.metadata = mock_metadata
            mock_registry.get_domain_services.return_value = mock_services
            
            data = {
                "name": "test_context",
                "domain": "manufacturing",
                "quality_level": "professional",
                "strict_mode": True,
                "custom_rules": {"test": "value"}
            }
            
            context = ValidationContext.from_dict(data)
            
            assert context.name == "test_context"
            assert context.domain == "manufacturing"
            assert context.quality_level == "professional"
            assert context.strict_mode is True
            assert context.custom_rules == {"test": "value"}
    
    def test_from_dict_with_defaults(self):
        """Test creating validation context from dictionary with default values"""
        with patch('src.core.registry.domain_registry.DomainRegistry') as mock_registry:
            mock_registry.list_domains.return_value = ["manufacturing"]
            mock_services = MagicMock()
            mock_metadata = MagicMock()
            mock_services.metadata = mock_metadata
            mock_registry.get_domain_services.return_value = mock_services
            
            data = {
                "name": "test_context",
                "domain": "manufacturing",
                "quality_level": "professional"
            }
            
            context = ValidationContext.from_dict(data)
            
            assert context.name == "test_context"
            assert context.domain == "manufacturing"
            assert context.quality_level == "professional"
            assert context.strict_mode is False  # Default value
            assert context.custom_rules == {}  # Default value
