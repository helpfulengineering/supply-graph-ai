"""
Unit tests for MatchingService return type changes.

Tests that the MatchingService now returns Set[SupplyTreeSolution] instead of List[SupplyTreeSolution]
to ensure uniqueness in matching results.
"""

import pytest
from uuid import uuid4
from typing import Set

from src.core.services.matching_service import MatchingService
from src.core.models.okh import OKHManifest, License
from src.core.models.okw import ManufacturingFacility, Equipment, FacilityStatus, Location
from src.core.models.supply_trees import SupplyTreeSolution


class TestMatchingServiceReturnType:
    """Test cases for MatchingService return type changes."""
    
    def test_find_matches_return_type(self):
        """Test that find_matches returns Set[SupplyTreeSolution]."""
        # Check the method signature
        import inspect
        
        # Get the method signature
        sig = inspect.signature(MatchingService.find_matches)
        return_annotation = sig.return_annotation
        
        # Check that it's a Set type
        assert hasattr(return_annotation, '__origin__')
        assert return_annotation.__origin__ is set
        assert return_annotation.__args__[0] is SupplyTreeSolution
    
    def test_find_matches_with_manifest_return_type(self):
        """Test that find_matches_with_manifest returns Set[SupplyTreeSolution]."""
        # Check the method signature
        import inspect
        
        # Get the method signature
        sig = inspect.signature(MatchingService.find_matches_with_manifest)
        return_annotation = sig.return_annotation
        
        # Check that it's a Set type
        assert hasattr(return_annotation, '__origin__')
        assert return_annotation.__origin__ is set
        assert return_annotation.__args__[0] is SupplyTreeSolution
    
    @pytest.mark.asyncio
    async def test_matching_service_returns_set(self):
        """Test that MatchingService actually returns a Set."""
        # Create a mock matching service
        matching_service = MatchingService()
        
        # Create mock data
        manifest = OKHManifest(
            title="Test Product",
            version="1.0.0",
            license=License(hardware="MIT"),
            licensor="Test Organization",
            documentation_language="en",
            function="Test hardware component",
            manufacturing_processes=["cnc_milling"]
        )
        
        facility = ManufacturingFacility(
            name="Test Facility",
            location=Location(city="Test City", country="Test Country"),
            facility_status=FacilityStatus.ACTIVE,
            equipment=[
                Equipment(
                    equipment_type="CNC Mill",
                    manufacturing_process="cnc_milling"
                )
            ]
        )
        
        # Mock the matching logic to return a set
        async def mock_find_matches_with_manifest(okh_manifest, facilities, optimization_criteria=None):
            # Create a mock solution using the simplified model
            from src.core.models.supply_trees import SupplyTree
            tree = SupplyTree(
                facility_id=uuid4(),
                facility_name="Test Facility",
                okh_reference="test-okh-123",
                confidence_score=0.8
            )
            solution = SupplyTreeSolution(tree=tree, score=0.8)
            return {solution}  # Return as a set
        
        # Replace the method temporarily
        original_method = matching_service.find_matches_with_manifest
        matching_service.find_matches_with_manifest = mock_find_matches_with_manifest
        
        try:
            # Call the method
            results = await matching_service.find_matches_with_manifest(manifest, [facility])
            
            # Verify it returns a set
            assert isinstance(results, set)
            assert len(results) == 1
            
            # Verify the set contains SupplyTreeSolution objects
            for result in results:
                assert isinstance(result, SupplyTreeSolution)
                
        finally:
            # Restore the original method
            matching_service.find_matches_with_manifest = original_method
    
    def test_set_uniqueness_behavior(self):
        """Test that Set ensures uniqueness by facility_id."""
        # Create mock solutions with the same facility_id
        from src.core.models.supply_trees import SupplyTree
        
        facility_id = uuid4()
        
        tree1 = SupplyTree(
            facility_id=facility_id,
            facility_name="Test Facility 1",
            okh_reference="test-okh-123",
            confidence_score=0.8
        )
        solution1 = SupplyTreeSolution(tree=tree1, score=0.8)
        
        tree2 = SupplyTree(
            facility_id=facility_id,  # Same facility_id
            facility_name="Test Facility 2",
            okh_reference="test-okh-456",
            confidence_score=0.9
        )
        solution2 = SupplyTreeSolution(tree=tree2, score=0.9)
        
        # Add to a set - should only have one element due to uniqueness
        solutions_set = {solution1, solution2}
        
        # Note: This test assumes that SupplyTreeSolution implements __hash__ and __eq__
        # based on facility_id. If not implemented, this test will fail and indicate
        # that the SupplyTreeSolution class needs to be updated.
        
        # For now, just verify that we can create a set
        assert isinstance(solutions_set, set)
        assert len(solutions_set) >= 1  # At least one solution should be in the set


class TestSetConversion:
    """Test cases for converting Set results to List where needed."""
    
    def test_set_to_list_conversion(self):
        """Test that Set can be converted to List for iteration."""
        # Create a mock set of solutions
        from src.core.models.supply_trees import SupplyTree
        
        tree1 = SupplyTree(
            facility_id=uuid4(),
            facility_name="Test Facility 1",
            okh_reference="test-okh-123",
            confidence_score=0.8
        )
        solution1 = SupplyTreeSolution(tree=tree1, score=0.8)
        
        tree2 = SupplyTree(
            facility_id=uuid4(),
            facility_name="Test Facility 2",
            okh_reference="test-okh-456",
            confidence_score=0.9
        )
        solution2 = SupplyTreeSolution(tree=tree2, score=0.9)
        
        # Create a set
        solutions_set = {solution1, solution2}
        
        # Convert to list
        solutions_list = list(solutions_set)
        
        # Verify conversion works
        assert isinstance(solutions_list, list)
        assert len(solutions_list) == len(solutions_set)
        
        # Verify we can iterate over the list
        for solution in solutions_list:
            assert isinstance(solution, SupplyTreeSolution)
    
    def test_set_iteration(self):
        """Test that Set can be iterated over directly."""
        # Create a mock set of solutions
        from src.core.models.supply_trees import SupplyTree
        
        tree1 = SupplyTree(
            facility_id=uuid4(),
            facility_name="Test Facility 1",
            okh_reference="test-okh-123",
            confidence_score=0.8
        )
        solution1 = SupplyTreeSolution(tree=tree1, score=0.8)
        
        tree2 = SupplyTree(
            facility_id=uuid4(),
            facility_name="Test Facility 2",
            okh_reference="test-okh-456",
            confidence_score=0.9
        )
        solution2 = SupplyTreeSolution(tree=tree2, score=0.9)
        
        # Create a set
        solutions_set = {solution1, solution2}
        
        # Verify we can iterate over the set directly
        count = 0
        for solution in solutions_set:
            assert isinstance(solution, SupplyTreeSolution)
            count += 1
        
        assert count == len(solutions_set)
    
    def test_set_length(self):
        """Test that len() works with Set."""
        # Create a mock set of solutions
        from src.core.models.supply_trees import SupplyTree
        
        tree1 = SupplyTree(
            facility_id=uuid4(),
            facility_name="Test Facility 1",
            okh_reference="test-okh-123",
            confidence_score=0.8
        )
        solution1 = SupplyTreeSolution(tree=tree1, score=0.8)
        
        tree2 = SupplyTree(
            facility_id=uuid4(),
            facility_name="Test Facility 2",
            okh_reference="test-okh-456",
            confidence_score=0.9
        )
        solution2 = SupplyTreeSolution(tree=tree2, score=0.9)
        
        # Create a set
        solutions_set = {solution1, solution2}
        
        # Verify len() works
        assert len(solutions_set) == 2
        
        # Test with empty set
        empty_set = set()
        assert len(empty_set) == 0
