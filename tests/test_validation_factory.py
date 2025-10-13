"""
Simple tests for validation context factory.

This module tests the ValidationContextFactory class with simpler mocking.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.core.validation.factory import ValidationContextFactory


class TestValidationContextFactorySimple:
    """Test ValidationContextFactory class with simple tests"""
    
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
