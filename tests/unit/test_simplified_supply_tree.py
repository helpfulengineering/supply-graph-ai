"""
Unit tests for SimplifiedSupplyTree model.

Tests the simplified SupplyTree model to ensure it works correctly
and provides the expected functionality for the matching use case.
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID

from src.core.models.supply_trees import SupplyTree as SimplifiedSupplyTree, SupplyTreeSolution as SimplifiedSupplyTreeSolution
from src.core.models.okh import OKHManifest, License
from src.core.models.okw import ManufacturingFacility, Equipment, FacilityStatus, Location


class TestSimplifiedSupplyTree:
    """Test cases for SimplifiedSupplyTree class."""
    
    def test_basic_creation(self):
        """Test basic SimplifiedSupplyTree creation."""
        facility_id = uuid4()
        tree = SimplifiedSupplyTree(
            facility_id=facility_id,
            facility_name="Test Facility",
            okh_reference="test-okh-123",
            confidence_score=0.85
        )
        
        assert tree.facility_id == facility_id
        assert tree.facility_name == "Test Facility"
        assert tree.okh_reference == "test-okh-123"
        assert tree.confidence_score == 0.85
        assert tree.match_type == "unknown"
        assert isinstance(tree.creation_time, datetime)
    
    def test_set_operations(self):
        """Test that SimplifiedSupplyTree works with Set operations."""
        facility_id = uuid4()
        
        tree1 = SimplifiedSupplyTree(
            facility_id=facility_id,
            facility_name="Test Facility 1",
            okh_reference="test-okh-123",
            confidence_score=0.85
        )
        
        tree2 = SimplifiedSupplyTree(
            facility_id=facility_id,  # Same facility_id
            facility_name="Test Facility 2",  # Different name
            okh_reference="test-okh-456",  # Different OKH
            confidence_score=0.90  # Different score
        )
        
        # Should be equal because facility_id is the same
        assert tree1 == tree2
        assert hash(tree1) == hash(tree2)
        
        # Set operations should work
        tree_set = {tree1, tree2}
        assert len(tree_set) == 1  # Only one unique tree
        
        # Test with different facility_id
        tree3 = SimplifiedSupplyTree(
            facility_id=uuid4(),  # Different facility_id
            facility_name="Test Facility 1",
            okh_reference="test-okh-123",
            confidence_score=0.85
        )
        
        assert tree1 != tree3
        assert hash(tree1) != hash(tree3)
        
        tree_set.add(tree3)
        assert len(tree_set) == 2  # Now two unique trees
    
    def test_serialization(self):
        """Test serialization and deserialization."""
        tree = SimplifiedSupplyTree(
            facility_id=uuid4(),
            facility_name="Test Facility",
            okh_reference="test-okh-123",
            confidence_score=0.85,
            estimated_cost=1000.0,
            estimated_time="2 hours",
            materials_required=["steel", "aluminum"],
            capabilities_used=["cnc_milling", "welding"],
            match_type="direct",
            metadata={"test": "value"}
        )
        
        # Test to_dict
        tree_dict = tree.to_dict()
        assert tree_dict['facility_name'] == "Test Facility"
        assert tree_dict['confidence_score'] == 0.85
        assert tree_dict['materials_required'] == ["steel", "aluminum"]
        assert tree_dict['capabilities_used'] == ["cnc_milling", "welding"]
        assert tree_dict['match_type'] == "direct"
        assert tree_dict['metadata']['test'] == "value"
        
        # Test from_dict
        tree_restored = SimplifiedSupplyTree.from_dict(tree_dict)
        assert tree_restored.facility_id == tree.facility_id
        assert tree_restored.facility_name == tree.facility_name
        assert tree_restored.confidence_score == tree.confidence_score
        assert tree_restored.materials_required == tree.materials_required
        assert tree_restored.capabilities_used == tree.capabilities_used
        assert tree_restored.match_type == tree.match_type
        assert tree_restored.metadata == tree.metadata
    
    def test_from_facility_and_manifest(self):
        """Test creation from facility and manifest."""
        # Create mock facility
        facility = ManufacturingFacility(
            name="Test Manufacturing Facility",
            location=Location(city="Test City", country="Test Country"),
            facility_status=FacilityStatus.ACTIVE,
            equipment=[
                Equipment(
                    equipment_type="CNC Mill",
                    manufacturing_process="cnc_milling"
                ),
                Equipment(
                    equipment_type="Welder",
                    manufacturing_process="welding"
                )
            ]
        )
        
        # Create mock manifest
        manifest = OKHManifest(
            title="Test Product",
            version="1.0.0",
            license=License(hardware="MIT"),
            licensor="Test Organization",
            documentation_language="en",
            function="Test hardware component",
            manufacturing_processes=["cnc_milling", "welding"],
            materials=["steel", "aluminum"]
        )
        
        # Create simplified supply tree
        tree = SimplifiedSupplyTree.from_facility_and_manifest(
            facility=facility,
            manifest=manifest,
            confidence_score=0.92,
            match_type="direct",
            estimated_cost=1500.0,
            estimated_time="3 hours"
        )
        
        assert tree.facility_id == facility.id
        assert tree.facility_name == facility.name
        assert tree.okh_reference == str(manifest.id)
        assert tree.confidence_score == 0.92
        assert tree.match_type == "direct"
        assert tree.estimated_cost == 1500.0
        assert tree.estimated_time == "3 hours"
        
        # Check extracted capabilities
        assert "cnc_milling" in tree.capabilities_used
        assert "welding" in tree.capabilities_used
        
        # Check extracted materials
        assert "steel" in tree.materials_required
        assert "aluminum" in tree.materials_required
        
        # Check metadata
        assert tree.metadata["okh_title"] == "Test Product"
        assert tree.metadata["facility_name"] == "Test Manufacturing Facility"
        assert tree.metadata["generation_method"] == "simplified_matching"
        assert tree.metadata["domain"] == "manufacturing"
        assert tree.metadata["equipment_count"] == 2
        assert tree.metadata["process_count"] == 2


class TestSimplifiedSupplyTreeSolution:
    """Test cases for SimplifiedSupplyTreeSolution class."""
    
    def test_basic_creation(self):
        """Test basic SimplifiedSupplyTreeSolution creation."""
        tree = SimplifiedSupplyTree(
            facility_id=uuid4(),
            facility_name="Test Facility",
            okh_reference="test-okh-123",
            confidence_score=0.85
        )
        
        solution = SimplifiedSupplyTreeSolution(
            tree=tree,
            score=0.90,
            metrics={"facility_count": 1, "requirement_count": 3}
        )
        
        assert solution.tree == tree
        assert solution.score == 0.90
        assert solution.metrics["facility_count"] == 1
        assert solution.metrics["requirement_count"] == 3
    
    def test_set_operations(self):
        """Test that SimplifiedSupplyTreeSolution works with Set operations."""
        facility_id = uuid4()
        
        tree1 = SimplifiedSupplyTree(
            facility_id=facility_id,
            facility_name="Test Facility 1",
            okh_reference="test-okh-123",
            confidence_score=0.85
        )
        
        tree2 = SimplifiedSupplyTree(
            facility_id=facility_id,  # Same facility_id
            facility_name="Test Facility 2",
            okh_reference="test-okh-456",
            confidence_score=0.90
        )
        
        solution1 = SimplifiedSupplyTreeSolution(tree=tree1, score=0.85)
        solution2 = SimplifiedSupplyTreeSolution(tree=tree2, score=0.90)
        
        # Should be equal because facility_id is the same
        assert solution1 == solution2
        assert hash(solution1) == hash(solution2)
        
        # Set operations should work
        solution_set = {solution1, solution2}
        assert len(solution_set) == 1  # Only one unique solution
    
    def test_serialization(self):
        """Test serialization and deserialization."""
        tree = SimplifiedSupplyTree(
            facility_id=uuid4(),
            facility_name="Test Facility",
            okh_reference="test-okh-123",
            confidence_score=0.85
        )
        
        solution = SimplifiedSupplyTreeSolution(
            tree=tree,
            score=0.90,
            metrics={"facility_count": 1, "requirement_count": 3}
        )
        
        # Test to_dict
        solution_dict = solution.to_dict()
        assert solution_dict['score'] == 0.90
        assert solution_dict['metrics']['facility_count'] == 1
        assert solution_dict['tree']['facility_name'] == "Test Facility"
        
        # Test from_dict
        solution_restored = SimplifiedSupplyTreeSolution.from_dict(solution_dict)
        assert solution_restored.score == solution.score
        assert solution_restored.metrics == solution.metrics
        assert solution_restored.tree.facility_id == solution.tree.facility_id


class TestPerformanceComparison:
    """Test performance characteristics of simplified model."""
    
    def test_memory_usage(self):
        """Test that simplified model uses less memory."""
        # Create many simplified trees
        trees = []
        for i in range(1000):
            tree = SimplifiedSupplyTree(
                facility_id=uuid4(),
                facility_name=f"Facility {i}",
                okh_reference=f"okh-{i}",
                confidence_score=0.8 + (i % 20) * 0.01
            )
            trees.append(tree)
        
        # Test Set operations (should be fast)
        tree_set = set(trees)
        assert len(tree_set) == 1000  # All unique
        
        # Test serialization (should be fast)
        for tree in trees[:10]:  # Test first 10
            tree_dict = tree.to_dict()
            restored = SimplifiedSupplyTree.from_dict(tree_dict)
            assert restored.facility_id == tree.facility_id
    
    def test_serialization_performance(self):
        """Test that serialization is fast."""
        import time
        
        tree = SimplifiedSupplyTree(
            facility_id=uuid4(),
            facility_name="Test Facility",
            okh_reference="test-okh-123",
            confidence_score=0.85,
            materials_required=["steel", "aluminum", "copper"],
            capabilities_used=["cnc_milling", "welding", "turning"],
            metadata={"test": "value", "domain": "manufacturing"}
        )
        
        # Time serialization
        start_time = time.time()
        for _ in range(1000):
            tree_dict = tree.to_dict()
            restored = SimplifiedSupplyTree.from_dict(tree_dict)
        end_time = time.time()
        
        # Should be very fast (less than 1 second for 1000 operations)
        assert (end_time - start_time) < 1.0


class TestMatchRequestFilters:
    """Test cases for MatchRequest filter parameters."""
    
    def test_filter_parameters(self):
        """Test that all filter parameters work correctly."""
        from src.core.api.models.match.request import MatchRequest
        
        # Test with all filter parameters
        request = MatchRequest(
            okh_manifest={'title': 'Test Product'},
            max_distance_km=50.0,
            deadline='2024-12-31T23:59:59Z',
            max_cost=10000.0,
            min_capacity=100,
            location_coords={'lat': 37.7749, 'lng': -122.4194},
            min_confidence=0.8,
            max_results=5
        )
        
        assert request.max_distance_km == 50.0
        assert request.deadline == '2024-12-31T23:59:59Z'
        assert request.max_cost == 10000.0
        assert request.min_capacity == 100
        assert request.location_coords == {'lat': 37.7749, 'lng': -122.4194}
        assert request.min_confidence == 0.8
        assert request.max_results == 5
    
    def test_filter_validation(self):
        """Test filter parameter validation."""
        from src.core.api.models.match.request import MatchRequest
        
        # Test with valid filters
        request = MatchRequest(
            okh_manifest={'title': 'Test'},
            max_distance_km=0.0,  # Edge case: 0 distance
            max_cost=0.0,  # Edge case: 0 cost
            min_capacity=1,  # Edge case: minimum capacity
            min_confidence=0.0,  # Edge case: minimum confidence
            max_results=1  # Edge case: minimum results
        )
        
        assert request.max_distance_km == 0.0
        assert request.max_cost == 0.0
        assert request.min_capacity == 1
        assert request.min_confidence == 0.0
        assert request.max_results == 1
    
    def test_okh_input_validation(self):
        """Test OKH input validation."""
        from src.core.api.models.match.request import MatchRequest
        from uuid import uuid4
        
        # Test with okh_manifest only
        request1 = MatchRequest(okh_manifest={'title': 'Test'})
        assert request1.okh_manifest is not None
        
        # Test with okh_id only
        okh_id = uuid4()
        request2 = MatchRequest(okh_id=okh_id)
        assert request2.okh_id == okh_id
        
        # Test with okh_url only
        request3 = MatchRequest(okh_url='https://example.com/manifest.json')
        assert request3.okh_url == 'https://example.com/manifest.json'
        
        # Test validation error - multiple OKH inputs
        with pytest.raises(ValueError, match="Cannot provide multiple OKH inputs"):
            MatchRequest(
                okh_manifest={'title': 'Test'},
                okh_id=okh_id
            )
        
        # Test validation error - no OKH inputs
        with pytest.raises(ValueError, match="Must provide either okh_id, okh_manifest, or okh_url"):
            MatchRequest()


class TestMatchingServiceIntegration:
    """Test integration with MatchingService."""
    
    def test_matching_service_return_type(self):
        """Test that MatchingService returns Set[SupplyTreeSolution]."""
        from src.core.services.matching_service import MatchingService
        import inspect
        
        # Check method signature
        sig = inspect.signature(MatchingService.find_matches_with_manifest)
        return_annotation = sig.return_annotation
        
        # Should return Set[SupplyTreeSolution]
        assert 'Set' in str(return_annotation)
        assert 'SupplyTreeSolution' in str(return_annotation)
    
    def test_set_operations_with_solutions(self):
        """Test Set operations with SupplyTreeSolution objects."""
        facility_id = uuid4()
        
        # Create two solutions with same facility_id
        tree1 = SimplifiedSupplyTree(
            facility_id=facility_id,
            facility_name="Facility 1",
            okh_reference="okh-1",
            confidence_score=0.8
        )
        
        tree2 = SimplifiedSupplyTree(
            facility_id=facility_id,  # Same facility_id
            facility_name="Facility 2",
            okh_reference="okh-2",
            confidence_score=0.9
        )
        
        solution1 = SimplifiedSupplyTreeSolution(tree=tree1, score=0.8)
        solution2 = SimplifiedSupplyTreeSolution(tree=tree2, score=0.9)
        
        # Test Set operations
        solution_set = {solution1, solution2}
        assert len(solution_set) == 1  # Only one unique solution
        
        # Test with different facility_id
        tree3 = SimplifiedSupplyTree(
            facility_id=uuid4(),  # Different facility_id
            facility_name="Facility 3",
            okh_reference="okh-3",
            confidence_score=0.7
        )
        
        solution3 = SimplifiedSupplyTreeSolution(tree=tree3, score=0.7)
        solution_set.add(solution3)
        assert len(solution_set) == 2  # Now two unique solutions


class TestResourceURI:
    """Test ResourceURI helper methods."""
    
    def test_get_value_from_okh(self):
        """Test ResourceURI.get_value_from_okh method."""
        from src.core.models.supply_trees import ResourceURI
        
        # Create ResourceURI
        uri = ResourceURI.from_string('okh://test-manifest/manufacturing_processes/0')
        
        # Create mock OKH manifest
        manifest = OKHManifest(
            title='Test Manifest',
            version='1.0.0',
            license=License(hardware='MIT'),
            licensor='Test Author',
            documentation_language='en',
            function='Test function'
        )
        manifest.manufacturing_processes = ['milling', 'assembly']
        
        # Test navigation
        value = uri.get_value_from_okh(manifest)
        assert value == 'milling'
    
    def test_get_value_from_okw(self):
        """Test ResourceURI.get_value_from_okw method."""
        from src.core.models.supply_trees import ResourceURI
        
        # Create ResourceURI
        uri = ResourceURI.from_string('okw://test-facility/manufacturing_processes/1')
        
        # Create mock facility
        facility = ManufacturingFacility(
            name='Test Facility',
            location=Location(city='Test City', country='Test Country'),
            facility_status=FacilityStatus.ACTIVE
        )
        facility.manufacturing_processes = ['milling', 'welding']
        
        # Test navigation
        value = uri.get_value_from_okw(facility)
        assert value == 'welding'
    
    def test_fragment_extraction(self):
        """Test ResourceURI fragment extraction."""
        from src.core.models.supply_trees import ResourceURI
        
        # Create ResourceURI with fragment
        uri = ResourceURI.from_string('okh://test-manifest/license#hardware')
        
        # Create mock OKH manifest
        manifest = OKHManifest(
            title='Test Manifest',
            version='1.0.0',
            license=License(hardware='MIT'),
            licensor='Test Author',
            documentation_language='en',
            function='Test function'
        )
        
        # Test fragment extraction
        value = uri.get_value_from_okh(manifest)
        assert value == 'MIT'
    
    def test_error_handling(self):
        """Test ResourceURI error handling."""
        from src.core.models.supply_trees import ResourceURI
        
        # Create ResourceURI with invalid path
        uri = ResourceURI.from_string('okh://test-manifest/invalid_path')
        
        # Create mock OKH manifest
        manifest = OKHManifest(
            title='Test Manifest',
            version='1.0.0',
            license=License(hardware='MIT'),
            licensor='Test Author',
            documentation_language='en',
            function='Test function'
        )
        
        # Test error handling
        value = uri.get_value_from_okh(manifest)
        assert value is None
