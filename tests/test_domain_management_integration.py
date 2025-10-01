#!/usr/bin/env python3
"""
Comprehensive integration test for the domain management system

This test verifies that the unified domain management system works end-to-end,
including domain registration, detection, validation, and API integration.

Run with: pytest tests/test_domain_management_integration.py -v
"""

import pytest
import asyncio
import sys
import os
from typing import Dict, Any
from unittest.mock import Mock

# Add the project root to the Python path
# Get the directory containing this test file, then go up one level to get project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# Import the domain management components
from src.core.registry.domain_registry import (
    DomainRegistry, 
    DomainMetadata, 
    DomainStatus, 
    DomainServices
)
from src.core.services.domain_service import (
    DomainDetector, 
    DomainDetectionResult
)
from src.core.domains.cooking.extractors import CookingExtractor
from src.core.domains.cooking.matchers import CookingMatcher
from src.core.domains.cooking.validators import CookingValidator
from src.core.domains.manufacturing.okh_extractor import OKHExtractor
from src.core.domains.manufacturing.okh_matcher import OKHMatcher
from src.core.domains.manufacturing.okh_validator import OKHValidator


class MockRequirements:
    """Mock requirements object for testing"""
    def __init__(self, domain: str = None, type: str = None, content: Dict[str, Any] = None):
        self.domain = domain
        self.type = type
        self.content = content or {}

class MockCapabilities:
    """Mock capabilities object for testing"""
    def __init__(self, domain: str = None, type: str = None, content: Dict[str, Any] = None):
        self.domain = domain
        self.type = type
        self.content = content or {}


class TestDomainRegistry:
    """Test the unified domain registry system"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        # Clear any existing registrations
        DomainRegistry._domains.clear()
        DomainRegistry._type_mappings.clear()
    
    def teardown_method(self):
        """Clean up after each test"""
        # Clear registrations
        DomainRegistry._domains.clear()
        DomainRegistry._type_mappings.clear()
    
    def test_domain_registration(self):
        """Test registering domains with all components"""
        # Register cooking domain
        cooking_metadata = DomainMetadata(
            name="cooking",
            display_name="Cooking & Food Preparation",
            description="Domain for recipe and kitchen capability matching",
            version="1.0.0",
            status=DomainStatus.ACTIVE,
            supported_input_types={"recipe", "kitchen"},
            supported_output_types={"cooking_workflow", "meal_plan"},
            documentation_url="https://docs.ome.org/domains/cooking",
            maintainer="OME Cooking Team"
        )
        
        DomainRegistry.register_domain(
            domain_name="cooking",
            extractor=CookingExtractor(),
            matcher=CookingMatcher(),
            validator=CookingValidator(),
            metadata=cooking_metadata
        )
        
        # Verify registration
        domains = DomainRegistry.list_domains()
        assert "cooking" in domains
        assert len(domains) == 1
        
        # Verify domain services
        cooking_services = DomainRegistry.get_domain_services("cooking")
        assert cooking_services.extractor is not None
        assert cooking_services.matcher is not None
        assert cooking_services.validator is not None
        assert cooking_services.metadata.name == "cooking"
    
    def test_multiple_domain_registration(self):
        """Test registering multiple domains"""
        # Register cooking domain
        cooking_metadata = DomainMetadata(
            name="cooking",
            display_name="Cooking & Food Preparation",
            description="Domain for recipe and kitchen capability matching",
            version="1.0.0",
            status=DomainStatus.ACTIVE,
            supported_input_types={"recipe", "kitchen"},
            supported_output_types={"cooking_workflow", "meal_plan"}
        )
        
        DomainRegistry.register_domain(
            domain_name="cooking",
            extractor=CookingExtractor(),
            matcher=CookingMatcher(),
            validator=CookingValidator(),
            metadata=cooking_metadata
        )
        
        # Register manufacturing domain
        manufacturing_metadata = DomainMetadata(
            name="manufacturing",
            display_name="Manufacturing & Hardware Production",
            description="Domain for OKH/OKW manufacturing capability matching",
            version="1.0.0",
            status=DomainStatus.ACTIVE,
            supported_input_types={"okh", "okw"},
            supported_output_types={"supply_tree", "manufacturing_plan"}
        )
        
        DomainRegistry.register_domain(
            domain_name="manufacturing",
            extractor=OKHExtractor(),
            matcher=OKHMatcher(),
            validator=OKHValidator(),
            metadata=manufacturing_metadata
        )
        
        # Verify both domains are registered
        domains = DomainRegistry.list_domains()
        assert "cooking" in domains
        assert "manufacturing" in domains
        assert len(domains) == 2
        
        # Verify type mappings
        assert DomainRegistry.infer_domain_from_type("recipe") == "cooking"
        assert DomainRegistry.infer_domain_from_type("okh") == "manufacturing"
    
    def test_domain_metadata_retrieval(self):
        """Test retrieving domain metadata"""
        # Register a domain
        metadata = DomainMetadata(
            name="test_domain",
            display_name="Test Domain",
            description="A test domain",
            version="1.0.0",
            status=DomainStatus.ACTIVE,
            supported_input_types={"test_input"},
            supported_output_types={"test_output"}
        )
        
        DomainRegistry.register_domain(
            domain_name="test_domain",
            extractor=CookingExtractor(),
            matcher=CookingMatcher(),
            validator=CookingValidator(),
            metadata=metadata
        )
        
        # Test metadata retrieval
        retrieved_metadata = DomainRegistry.get_domain_metadata("test_domain")
        assert retrieved_metadata.name == "test_domain"
        assert retrieved_metadata.display_name == "Test Domain"
        assert retrieved_metadata.status == DomainStatus.ACTIVE
        
        # Test all metadata retrieval
        all_metadata = DomainRegistry.get_all_metadata()
        assert "test_domain" in all_metadata
        assert len(all_metadata) == 1
    
    def test_type_support_validation(self):
        """Test type support validation"""
        # Register domain with specific types
        metadata = DomainMetadata(
            name="test_domain",
            display_name="Test Domain",
            description="A test domain",
            version="1.0.0",
            status=DomainStatus.ACTIVE,
            supported_input_types={"recipe", "kitchen"},
            supported_output_types={"workflow"}
        )
        
        DomainRegistry.register_domain(
            domain_name="test_domain",
            extractor=CookingExtractor(),
            matcher=CookingMatcher(),
            validator=CookingValidator(),
            metadata=metadata
        )
        
        # Test valid types
        assert DomainRegistry.validate_type_support("test_domain", "recipe")
        assert DomainRegistry.validate_type_support("test_domain", "kitchen")
        
        # Test invalid types
        assert not DomainRegistry.validate_type_support("test_domain", "okh")
        assert not DomainRegistry.validate_type_support("test_domain", "unknown")
    
    def test_domain_compatibility_validation(self):
        """Test domain compatibility validation"""
        # Test same domain compatibility
        assert DomainRegistry.validate_domain_compatibility("cooking", "cooking")
        assert DomainRegistry.validate_domain_compatibility("manufacturing", "manufacturing")
        
        # Test different domain compatibility (should fail for now)
        assert not DomainRegistry.validate_domain_compatibility("cooking", "manufacturing")
    
    def test_health_check(self):
        """Test domain health check functionality"""
        # Register a domain
        metadata = DomainMetadata(
            name="test_domain",
            display_name="Test Domain",
            description="A test domain",
            version="1.0.0",
            status=DomainStatus.ACTIVE,
            supported_input_types={"test_input"},
            supported_output_types={"test_output"}
        )
        
        DomainRegistry.register_domain(
            domain_name="test_domain",
            extractor=CookingExtractor(),
            matcher=CookingMatcher(),
            validator=CookingValidator(),
            metadata=metadata
        )
        
        # Run health check
        health_status = DomainRegistry.health_check()
        
        # Verify health check structure
        assert "total_domains" in health_status
        assert "active_domains" in health_status
        assert "domains" in health_status
        
        assert health_status["total_domains"] == 1
        assert health_status["active_domains"] == 1
        
        # Verify domain health
        assert "test_domain" in health_status["domains"]
        domain_health = health_status["domains"]["test_domain"]
        assert domain_health["status"] == "active"
        assert "extractor" in domain_health
        assert "matcher" in domain_health
        assert "validator" in domain_health
    
    def test_domain_not_found_error(self):
        """Test error handling for non-existent domains"""
        with pytest.raises(ValueError, match="Domain 'nonexistent' not found"):
            DomainRegistry.get_domain_services("nonexistent")
        
        with pytest.raises(ValueError, match="Domain 'nonexistent' not found"):
            DomainRegistry.get_domain_metadata("nonexistent")


class TestDomainDetector:
    """Test the domain detection system"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        # Register domains for testing
        cooking_metadata = DomainMetadata(
            name="cooking",
            display_name="Cooking & Food Preparation",
            description="Domain for recipe and kitchen capability matching",
            version="1.0.0",
            status=DomainStatus.ACTIVE,
            supported_input_types={"recipe", "kitchen"},
            supported_output_types={"cooking_workflow", "meal_plan"}
        )
        
        DomainRegistry.register_domain(
            domain_name="cooking",
            extractor=CookingExtractor(),
            matcher=CookingMatcher(),
            validator=CookingValidator(),
            metadata=cooking_metadata
        )
        
        manufacturing_metadata = DomainMetadata(
            name="manufacturing",
            display_name="Manufacturing & Hardware Production",
            description="Domain for OKH/OKW manufacturing capability matching",
            version="1.0.0",
            status=DomainStatus.ACTIVE,
            supported_input_types={"okh", "okw"},
            supported_output_types={"supply_tree", "manufacturing_plan"}
        )
        
        DomainRegistry.register_domain(
            domain_name="manufacturing",
            extractor=OKHExtractor(),
            matcher=OKHMatcher(),
            validator=OKHValidator(),
            metadata=manufacturing_metadata
        )
    
    def teardown_method(self):
        """Clean up after each test"""
        DomainRegistry._domains.clear()
        DomainRegistry._type_mappings.clear()
    
    def test_explicit_domain_detection(self):
        """Test explicit domain detection"""
        req = MockRequirements(domain="cooking", type="recipe")
        cap = MockCapabilities(domain="cooking", type="kitchen")
        
        result = DomainDetector.detect_domain(req, cap)
        
        assert result.domain == "cooking"
        assert result.confidence == 1.0
        assert result.method == "explicit"
    
    def test_explicit_domain_mismatch(self):
        """Test explicit domain mismatch detection"""
        req = MockRequirements(domain="cooking", type="recipe")
        cap = MockCapabilities(domain="manufacturing", type="okw")
        
        with pytest.raises(ValueError, match="Domain mismatch"):
            DomainDetector.detect_domain(req, cap)
    
    def test_type_based_detection(self):
        """Test type-based domain detection"""
        req = MockRequirements(type="okh")
        cap = MockCapabilities(type="okw")
        
        result = DomainDetector.detect_domain(req, cap)
        
        assert result.domain == "manufacturing"
        assert result.confidence == 0.9
        assert result.method == "type_mapping"
    
    def test_content_based_detection(self):
        """Test content-based domain detection"""
        req = MockRequirements(content={
            "ingredients": ["flour", "eggs", "sugar"],
            "instructions": ["mix ingredients", "bake at 350°F"]
        })
        cap = MockCapabilities(content={
            "tools": ["oven", "mixer", "whisk"],
            "appliances": ["stove", "refrigerator"]
        })
        
        result = DomainDetector.detect_domain(req, cap)
        
        assert result.domain == "cooking"
        assert result.method == "content_analysis"
        assert result.confidence > 0.0
    
    def test_content_based_detection_manufacturing(self):
        """Test content-based detection for manufacturing domain"""
        req = MockRequirements(content={
            "manufacturing_processes": ["CNC machining", "3D printing"],
            "materials": ["aluminum", "steel"]
        })
        cap = MockCapabilities(content={
            "equipment": ["CNC mill", "3D printer"],
            "capabilities": ["precision machining", "additive manufacturing"]
        })
        
        result = DomainDetector.detect_domain(req, cap)
        
        assert result.domain == "manufacturing"
        assert result.method == "content_analysis"
        assert result.confidence > 0.0
    
    def test_domain_validation_consistency(self):
        """Test domain validation consistency"""
        req = MockRequirements(domain="cooking")
        cap = MockCapabilities(domain="cooking")
        
        # Should pass validation
        result = DomainDetector.validate_domain_consistency(req, cap, "cooking")
        assert result is True
        
        # Should fail validation
        with pytest.raises(ValueError, match="doesn't match detected domain"):
            DomainDetector.validate_domain_consistency(req, cap, "manufacturing")
    
    def test_detect_and_validate_domain(self):
        """Test combined detection and validation"""
        req = MockRequirements(domain="cooking", type="recipe")
        cap = MockCapabilities(domain="cooking", type="kitchen")
        
        domain = DomainDetector.detect_and_validate_domain(req, cap)
        assert domain == "cooking"
    
    def test_domain_detection_with_alternatives(self):
        """Test domain detection with alternative suggestions"""
        req = MockRequirements(content={
            "ingredients": ["flour"],  # Only one cooking keyword
            "processes": ["machining"]  # One manufacturing keyword
        })
        cap = MockCapabilities(content={
            "tools": ["mixer"],
            "equipment": ["CNC mill"]
        })
        
        result = DomainDetector.detect_domain(req, cap)
        
        # Should detect a domain (whichever has higher score)
        assert result.domain in ["cooking", "manufacturing"]
        assert result.method == "content_analysis"
        assert len(result.alternative_domains) > 0


class TestDomainServiceIntegration:
    """Test integration between domain registry and domain service"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        # Register domains
        cooking_metadata = DomainMetadata(
            name="cooking",
            display_name="Cooking & Food Preparation",
            description="Domain for recipe and kitchen capability matching",
            version="1.0.0",
            status=DomainStatus.ACTIVE,
            supported_input_types={"recipe", "kitchen"},
            supported_output_types={"cooking_workflow", "meal_plan"}
        )
        
        DomainRegistry.register_domain(
            domain_name="cooking",
            extractor=CookingExtractor(),
            matcher=CookingMatcher(),
            validator=CookingValidator(),
            metadata=cooking_metadata
        )
    
    def teardown_method(self):
        """Clean up after each test"""
        DomainRegistry._domains.clear()
        DomainRegistry._type_mappings.clear()
    
    def test_domain_service_component_retrieval(self):
        """Test retrieving domain components through domain service"""
        # Test extractor retrieval
        extractor = DomainDetector.get_domain_extractor("cooking")
        assert extractor is not None
        assert isinstance(extractor, CookingExtractor)
        
        # Test matcher retrieval
        matcher = DomainDetector.get_domain_matcher("cooking")
        assert matcher is not None
        assert isinstance(matcher, CookingMatcher)
        
        # Test validator retrieval
        validator = DomainDetector.get_domain_validator("cooking")
        assert validator is not None
        assert isinstance(validator, CookingValidator)
    
    def test_domain_services_retrieval(self):
        """Test retrieving all domain services"""
        services = DomainDetector.get_domain_services("cooking")
        
        assert services.extractor is not None
        assert services.matcher is not None
        assert services.validator is not None
        assert services.metadata.name == "cooking"


class TestDomainManagementEndToEnd:
    """End-to-end integration test for the complete domain management system"""
    
    def setup_method(self):
        """Set up complete domain management system"""
        # Register both domains
        cooking_metadata = DomainMetadata(
            name="cooking",
            display_name="Cooking & Food Preparation",
            description="Domain for recipe and kitchen capability matching",
            version="1.0.0",
            status=DomainStatus.ACTIVE,
            supported_input_types={"recipe", "kitchen"},
            supported_output_types={"cooking_workflow", "meal_plan"},
            documentation_url="https://docs.ome.org/domains/cooking",
            maintainer="OME Cooking Team"
        )
        
        DomainRegistry.register_domain(
            domain_name="cooking",
            extractor=CookingExtractor(),
            matcher=CookingMatcher(),
            validator=CookingValidator(),
            metadata=cooking_metadata
        )
        
        manufacturing_metadata = DomainMetadata(
            name="manufacturing",
            display_name="Manufacturing & Hardware Production",
            description="Domain for OKH/OKW manufacturing capability matching",
            version="1.0.0",
            status=DomainStatus.ACTIVE,
            supported_input_types={"okh", "okw"},
            supported_output_types={"supply_tree", "manufacturing_plan"},
            documentation_url="https://docs.ome.org/domains/manufacturing",
            maintainer="OME Manufacturing Team"
        )
        
        DomainRegistry.register_domain(
            domain_name="manufacturing",
            extractor=OKHExtractor(),
            matcher=OKHMatcher(),
            validator=OKHValidator(),
            metadata=manufacturing_metadata
        )
    
    def teardown_method(self):
        """Clean up after each test"""
        DomainRegistry._domains.clear()
        DomainRegistry._type_mappings.clear()
    
    def test_complete_workflow_cooking(self):
        """Test complete workflow for cooking domain"""
        # 1. Detect domain
        req = MockRequirements(type="recipe", content={"ingredients": ["flour", "eggs"]})
        cap = MockCapabilities(type="kitchen", content={"tools": ["oven", "mixer"]})
        
        domain = DomainDetector.detect_and_validate_domain(req, cap)
        assert domain == "cooking"
        
        # 2. Get domain services
        services = DomainRegistry.get_domain_services(domain)
        assert services.metadata.name == "cooking"
        
        # 3. Verify components
        assert isinstance(services.extractor, CookingExtractor)
        assert isinstance(services.matcher, CookingMatcher)
        assert isinstance(services.validator, CookingValidator)
        
        # 4. Test type support
        assert DomainRegistry.validate_type_support("cooking", "recipe")
        assert DomainRegistry.validate_type_support("cooking", "kitchen")
    
    def test_complete_workflow_manufacturing(self):
        """Test complete workflow for manufacturing domain"""
        # 1. Detect domain
        req = MockRequirements(type="okh", content={"manufacturing_processes": ["CNC"]})
        cap = MockCapabilities(type="okw", content={"equipment": ["CNC mill"]})
        
        domain = DomainDetector.detect_and_validate_domain(req, cap)
        assert domain == "manufacturing"
        
        # 2. Get domain services
        services = DomainRegistry.get_domain_services(domain)
        assert services.metadata.name == "manufacturing"
        
        # 3. Verify components
        assert isinstance(services.extractor, OKHExtractor)
        assert isinstance(services.matcher, OKHMatcher)
        assert isinstance(services.validator, OKHValidator)
        
        # 4. Test type support
        assert DomainRegistry.validate_type_support("manufacturing", "okh")
        assert DomainRegistry.validate_type_support("manufacturing", "okw")
    
    def test_system_health_check(self):
        """Test complete system health check"""
        health_status = DomainRegistry.health_check()
        
        # Verify structure
        assert "total_domains" in health_status
        assert "active_domains" in health_status
        assert "domains" in health_status
        
        # Verify counts
        assert health_status["total_domains"] == 2
        assert health_status["active_domains"] == 2
        
        # Verify both domains are healthy
        assert "cooking" in health_status["domains"]
        assert "manufacturing" in health_status["domains"]
        
        cooking_health = health_status["domains"]["cooking"]
        assert cooking_health["status"] == "active"
        assert "extractor" in cooking_health
        assert "matcher" in cooking_health
        assert "validator" in cooking_health
        
        manufacturing_health = health_status["domains"]["manufacturing"]
        assert manufacturing_health["status"] == "active"
        assert "extractor" in manufacturing_health
        assert "matcher" in manufacturing_health
        assert "validator" in manufacturing_health
    
    def test_domain_metadata_completeness(self):
        """Test that all domain metadata is complete and accessible"""
        all_metadata = DomainRegistry.get_all_metadata()
        
        assert len(all_metadata) == 2
        assert "cooking" in all_metadata
        assert "manufacturing" in all_metadata
        
        # Test cooking metadata
        cooking_meta = all_metadata["cooking"]
        assert cooking_meta.name == "cooking"
        assert cooking_meta.display_name == "Cooking & Food Preparation"
        assert cooking_meta.status == DomainStatus.ACTIVE
        assert "recipe" in cooking_meta.supported_input_types
        assert "kitchen" in cooking_meta.supported_input_types
        assert cooking_meta.documentation_url is not None
        assert cooking_meta.maintainer is not None
        
        # Test manufacturing metadata
        manufacturing_meta = all_metadata["manufacturing"]
        assert manufacturing_meta.name == "manufacturing"
        assert manufacturing_meta.display_name == "Manufacturing & Hardware Production"
        assert manufacturing_meta.status == DomainStatus.ACTIVE
        assert "okh" in manufacturing_meta.supported_input_types
        assert "okw" in manufacturing_meta.supported_input_types
        assert manufacturing_meta.documentation_url is not None
        assert manufacturing_meta.maintainer is not None


if __name__ == "__main__":
    # Run the tests if executed directly
    pytest.main([__file__, "-v", "--tb=short"])
