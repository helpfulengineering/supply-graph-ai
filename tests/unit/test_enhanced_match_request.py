"""
Unit tests for EnhancedMatchRequest with new filter parameters.

Tests the enhanced match request model to ensure the new filter parameters
work correctly and provide the expected functionality.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from src.core.api.routes.match import EnhancedMatchRequest


class TestEnhancedMatchRequest:
    """Test cases for EnhancedMatchRequest class with new filter parameters."""
    
    def test_basic_creation(self):
        """Test basic EnhancedMatchRequest creation."""
        request = EnhancedMatchRequest(
            okh_manifest={"title": "Test Product"},
            min_confidence=0.8,
            max_results=5
        )
        
        assert request.okh_manifest["title"] == "Test Product"
        assert request.min_confidence == 0.8
        assert request.max_results == 5
        assert request.include_workflows is False  # Default value
    
    def test_new_filter_parameters(self):
        """Test new filter parameters."""
        request = EnhancedMatchRequest(
            okh_manifest={"title": "Test Product"},
            max_distance_km=50.0,
            deadline="2024-12-31T23:59:59Z",
            max_cost=10000.0,
            min_capacity=100,
            location_coords={"lat": 37.7749, "lng": -122.4194},
            include_workflows=True
        )
        
        assert request.max_distance_km == 50.0
        assert request.deadline == "2024-12-31T23:59:59Z"
        assert request.max_cost == 10000.0
        assert request.min_capacity == 100
        assert request.location_coords["lat"] == 37.7749
        assert request.location_coords["lng"] == -122.4194
        assert request.include_workflows is True
    
    def test_optional_filter_parameters(self):
        """Test that filter parameters are optional."""
        request = EnhancedMatchRequest(
            okh_manifest={"title": "Test Product"}
        )
        
        # All filter parameters should be None by default
        assert request.max_distance_km is None
        assert request.deadline is None
        assert request.max_cost is None
        assert request.min_capacity is None
        assert request.location_coords is None
        assert request.include_workflows is False  # Default to False
    
    def test_serialization(self):
        """Test serialization with new parameters."""
        request = EnhancedMatchRequest(
            okh_manifest={"title": "Test Product"},
            max_distance_km=25.0,
            max_cost=5000.0,
            min_capacity=50,
            location_coords={"lat": 40.7128, "lng": -74.0060},
            include_workflows=True
        )
        
        # Test to_dict (if available) or model_dump
        if hasattr(request, 'model_dump'):
            data = request.model_dump()
        elif hasattr(request, 'to_dict'):
            data = request.to_dict()
        else:
            # Fallback to dict conversion
            data = dict(request)
        
        assert data["max_distance_km"] == 25.0
        assert data["max_cost"] == 5000.0
        assert data["min_capacity"] == 50
        assert data["location_coords"]["lat"] == 40.7128
        assert data["location_coords"]["lng"] == -74.0060
        assert data["include_workflows"] is True
    
    def test_validation(self):
        """Test validation of filter parameters."""
        # Test valid values
        request = EnhancedMatchRequest(
            okh_manifest={"title": "Test Product"},
            max_distance_km=100.0,  # Valid positive number
            max_cost=0.0,  # Valid (free)
            min_capacity=1,  # Valid positive integer
            location_coords={"lat": 0.0, "lng": 0.0}  # Valid coordinates
        )
        
        assert request.max_distance_km == 100.0
        assert request.max_cost == 0.0
        assert request.min_capacity == 1
        assert request.location_coords["lat"] == 0.0
    
    def test_backward_compatibility(self):
        """Test backward compatibility with existing parameters."""
        request = EnhancedMatchRequest(
            okh_manifest={"title": "Test Product"},
            access_type="public",
            facility_status="active",
            location="San Francisco, CA",
            capabilities=["cnc_milling", "welding"],
            materials=["steel", "aluminum"],
            min_confidence=0.9,
            max_results=3
        )
        
        # Existing parameters should still work
        assert request.access_type == "public"
        assert request.facility_status == "active"
        assert request.location == "San Francisco, CA"
        assert request.capabilities == ["cnc_milling", "welding"]
        assert request.materials == ["steel", "aluminum"]
        assert request.min_confidence == 0.9
        assert request.max_results == 3
        
        # New parameters should have defaults
        assert request.max_distance_km is None
        assert request.deadline is None
        assert request.max_cost is None
        assert request.min_capacity is None
        assert request.location_coords is None
        assert request.include_workflows is False


class TestFilterParameterTypes:
    """Test specific filter parameter types and edge cases."""
    
    def test_distance_filter_types(self):
        """Test distance filter with different numeric types."""
        # Float
        request1 = EnhancedMatchRequest(
            okh_manifest={"title": "Test"},
            max_distance_km=50.5
        )
        assert request1.max_distance_km == 50.5
        
        # Integer (should be converted to float)
        request2 = EnhancedMatchRequest(
            okh_manifest={"title": "Test"},
            max_distance_km=50
        )
        assert request2.max_distance_km == 50.0
    
    def test_cost_filter_types(self):
        """Test cost filter with different numeric types."""
        # Float
        request1 = EnhancedMatchRequest(
            okh_manifest={"title": "Test"},
            max_cost=1000.99
        )
        assert request1.max_cost == 1000.99
        
        # Integer
        request2 = EnhancedMatchRequest(
            okh_manifest={"title": "Test"},
            max_cost=1000
        )
        assert request2.max_cost == 1000.0
    
    def test_capacity_filter_types(self):
        """Test capacity filter with integer types."""
        request = EnhancedMatchRequest(
            okh_manifest={"title": "Test"},
            min_capacity=100
        )
        assert request.min_capacity == 100
        assert isinstance(request.min_capacity, int)
    
    def test_location_coords_structure(self):
        """Test location coordinates structure."""
        request = EnhancedMatchRequest(
            okh_manifest={"title": "Test"},
            location_coords={"lat": 37.7749, "lng": -122.4194}
        )
        
        coords = request.location_coords
        assert "lat" in coords
        assert "lng" in coords
        assert coords["lat"] == 37.7749
        assert coords["lng"] == -122.4194
        assert isinstance(coords["lat"], float)
        assert isinstance(coords["lng"], float)
    
    def test_deadline_format(self):
        """Test deadline format (ISO datetime string)."""
        request = EnhancedMatchRequest(
            okh_manifest={"title": "Test"},
            deadline="2024-12-31T23:59:59Z"
        )
        
        assert request.deadline == "2024-12-31T23:59:59Z"
        assert isinstance(request.deadline, str)
    
    def test_include_workflows_boolean(self):
        """Test include_workflows boolean parameter."""
        # True
        request1 = EnhancedMatchRequest(
            okh_manifest={"title": "Test"},
            include_workflows=True
        )
        assert request1.include_workflows is True
        
        # False
        request2 = EnhancedMatchRequest(
            okh_manifest={"title": "Test"},
            include_workflows=False
        )
        assert request2.include_workflows is False
        
        # Default (should be False)
        request3 = EnhancedMatchRequest(
            okh_manifest={"title": "Test"}
        )
        assert request3.include_workflows is False
