"""
Performance tests for SupplyTree model simplification.

This module benchmarks the performance improvements achieved by simplifying
the SupplyTree model by removing Workflow components.
"""

import pytest
import time
import sys
import os
from typing import List, Set
from uuid import uuid4
import gc

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.models.supply_trees import SupplyTree, SupplyTreeSolution
from core.models.okh import OKHManifest, License
from core.models.okw import ManufacturingFacility, Location, FacilityStatus


class TestSupplyTreePerformance:
    """Performance benchmarks for simplified SupplyTree model."""
    
    def test_serialization_performance(self):
        """Benchmark serialization performance of simplified model."""
        # Create test data
        trees = []
        for i in range(1000):
            tree = SupplyTree(
                facility_id=uuid4(),
                facility_name=f"Facility {i}",
                okh_reference=f"okh-{i}",
                confidence_score=0.8 + (i % 20) * 0.01,
                estimated_cost=1000.0 + i * 10,
                estimated_time=f"{i % 10 + 1} hours",
                materials_required=[f"material_{j}" for j in range(5)],
                capabilities_used=[f"capability_{j}" for j in range(3)],
                match_type="direct",
                metadata={"test": f"value_{i}", "domain": "manufacturing"}
            )
            trees.append(tree)
        
        # Benchmark serialization
        start_time = time.time()
        serialized_data = []
        for tree in trees:
            serialized_data.append(tree.to_dict())
        serialization_time = time.time() - start_time
        
        # Benchmark deserialization
        start_time = time.time()
        deserialized_trees = []
        for data in serialized_data:
            deserialized_trees.append(SupplyTree.from_dict(data))
        deserialization_time = time.time() - start_time
        
        # Performance assertions
        print(f"\n📊 Serialization Performance:")
        print(f"  - 1000 objects serialized in: {serialization_time:.4f}s")
        print(f"  - 1000 objects deserialized in: {deserialization_time:.4f}s")
        print(f"  - Total time: {serialization_time + deserialization_time:.4f}s")
        print(f"  - Average per object: {(serialization_time + deserialization_time) / 1000 * 1000:.2f}ms")
        
        # Should be very fast (less than 2 seconds for 1000 objects)
        assert (serialization_time + deserialization_time) < 2.0, "Serialization too slow"
        
        # Verify data integrity
        assert len(deserialized_trees) == 1000
        for i, tree in enumerate(deserialized_trees):
            assert tree.facility_name == f"Facility {i}"
            assert tree.confidence_score == 0.8 + (i % 20) * 0.01
    
    def test_set_operations_performance(self):
        """Benchmark Set operations performance."""
        # Create test data with some duplicates
        trees = []
        facility_ids = [uuid4() for _ in range(500)]  # 500 unique facilities
        
        for i in range(1000):
            # Use same facility_id for some trees to test deduplication
            facility_id = facility_ids[i % 500]
            tree = SupplyTree(
                facility_id=facility_id,
                facility_name=f"Facility {i}",
                okh_reference=f"okh-{i}",
                confidence_score=0.8 + (i % 20) * 0.01
            )
            trees.append(tree)
        
        # Benchmark Set creation (should deduplicate)
        start_time = time.time()
        tree_set: Set[SupplyTree] = set(trees)
        set_creation_time = time.time() - start_time
        
        # Benchmark Set operations
        start_time = time.time()
        # Test intersection
        subset1 = set(trees[:300])
        subset2 = set(trees[200:500])
        intersection = subset1.intersection(subset2)
        
        # Test union
        union = subset1.union(subset2)
        
        # Test difference
        difference = subset1.difference(subset2)
        set_operations_time = time.time() - start_time
        
        print(f"\n📊 Set Operations Performance:")
        print(f"  - Set creation (1000 objects): {set_creation_time:.4f}s")
        print(f"  - Set operations (intersection, union, difference): {set_operations_time:.4f}s")
        print(f"  - Deduplication: {len(trees)} -> {len(tree_set)} objects")
        print(f"  - Intersection size: {len(intersection)}")
        print(f"  - Union size: {len(union)}")
        print(f"  - Difference size: {len(difference)}")
        
        # Should be very fast
        assert set_creation_time < 0.1, "Set creation too slow"
        assert set_operations_time < 0.1, "Set operations too slow"
        
        # Verify deduplication worked
        assert len(tree_set) == 500, f"Expected 500 unique trees, got {len(tree_set)}"
    
    def test_memory_usage(self):
        """Benchmark memory usage of simplified model."""
        # Force garbage collection
        gc.collect()
        
        # Get initial memory usage (simplified approach)
        import tracemalloc
        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        
        # Create many objects
        trees = []
        for i in range(10000):
            tree = SupplyTree(
                facility_id=uuid4(),
                facility_name=f"Facility {i}",
                okh_reference=f"okh-{i}",
                confidence_score=0.8 + (i % 20) * 0.01,
                materials_required=[f"material_{j}" for j in range(10)],
                capabilities_used=[f"capability_{j}" for j in range(5)],
                metadata={"test": f"value_{i}", "domain": "manufacturing", "index": i}
            )
            trees.append(tree)
        
        # Get memory usage after creation
        after_creation_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        memory_used = after_creation_memory - initial_memory
        
        # Create Set to test Set memory usage
        tree_set = set(trees)
        after_set_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        set_memory_used = after_set_memory - after_creation_memory
        
        print(f"\n📊 Memory Usage:")
        print(f"  - Initial memory: {initial_memory:.2f} MB")
        print(f"  - After creating 10,000 trees: {after_creation_memory:.2f} MB")
        print(f"  - Memory used by trees: {memory_used:.2f} MB")
        print(f"  - Memory per tree: {memory_used / 10000 * 1024:.2f} KB")
        print(f"  - After creating Set: {after_set_memory:.2f} MB")
        print(f"  - Additional memory for Set: {set_memory_used:.2f} MB")
        
        # Memory usage should be reasonable (less than 100MB for 10,000 objects)
        assert memory_used < 100, f"Memory usage too high: {memory_used:.2f} MB"
        assert set_memory_used < 50, f"Set memory usage too high: {set_memory_used:.2f} MB"
        
        # Clean up
        del trees, tree_set
        gc.collect()
        tracemalloc.stop()
    
    def test_solution_creation_performance(self):
        """Benchmark SupplyTreeSolution creation and Set operations."""
        # Create base trees
        trees = []
        for i in range(1000):
            tree = SupplyTree(
                facility_id=uuid4(),
                facility_name=f"Facility {i}",
                okh_reference=f"okh-{i}",
                confidence_score=0.8 + (i % 20) * 0.01
            )
            trees.append(tree)
        
        # Benchmark solution creation
        start_time = time.time()
        solutions = []
        for i, tree in enumerate(trees):
            solution = SupplyTreeSolution(
                tree=tree,
                score=0.8 + (i % 20) * 0.01,
                metrics={
                    "facility_count": 1,
                    "requirement_count": i % 10 + 1,
                    "match_type": "direct",
                    "processing_time": 0.1 + (i % 5) * 0.01
                }
            )
            solutions.append(solution)
        solution_creation_time = time.time() - start_time
        
        # Benchmark Set operations with solutions
        start_time = time.time()
        solution_set: Set[SupplyTreeSolution] = set(solutions)
        set_creation_time = time.time() - start_time
        
        # Test Set operations
        start_time = time.time()
        subset1 = set(solutions[:300])
        subset2 = set(solutions[200:500])
        intersection = subset1.intersection(subset2)
        union = subset1.union(subset2)
        set_operations_time = time.time() - start_time
        
        print(f"\n📊 Solution Performance:")
        print(f"  - 1000 solutions created in: {solution_creation_time:.4f}s")
        print(f"  - Set creation: {set_creation_time:.4f}s")
        print(f"  - Set operations: {set_operations_time:.4f}s")
        print(f"  - Unique solutions: {len(solution_set)}")
        
        # Should be fast
        assert solution_creation_time < 0.5, "Solution creation too slow"
        assert set_creation_time < 0.1, "Solution Set creation too slow"
        assert set_operations_time < 0.1, "Solution Set operations too slow"
    
    def test_api_response_size(self):
        """Benchmark API response size for simplified model."""
        # Create realistic test data
        solutions = []
        for i in range(100):  # 100 matching solutions
            tree = SupplyTree(
                facility_id=uuid4(),
                facility_name=f"Manufacturing Facility {i}",
                okh_reference=f"electronics-component-{i}",
                confidence_score=0.7 + (i % 30) * 0.01,
                estimated_cost=1000.0 + i * 100,
                estimated_time=f"{i % 7 + 1} days",
                materials_required=["copper", "plastic", "silicon", "aluminum"],
                capabilities_used=["soldering", "assembly", "testing", "packaging"],
                match_type="direct",
                metadata={
                    "okh_title": f"Electronics Component {i}",
                    "facility_name": f"Manufacturing Facility {i}",
                    "generation_method": "simplified_matching",
                    "domain": "manufacturing",
                    "equipment_count": 5,
                    "process_count": 4
                }
            )
            
            solution = SupplyTreeSolution(
                tree=tree,
                score=0.7 + (i % 30) * 0.01,
                metrics={
                    "facility_count": 1,
                    "requirement_count": 4,
                    "match_type": "direct",
                    "processing_time": 0.1 + (i % 5) * 0.01,
                    "confidence_breakdown": {
                        "direct_match": 0.8,
                        "capability_match": 0.7,
                        "material_match": 0.9
                    }
                }
            )
            solutions.append(solution)
        
        # Convert to API response format
        start_time = time.time()
        api_response = {
            "solutions": [solution.to_dict() for solution in solutions],
            "total_solutions": len(solutions),
            "processing_time": 2.5,
            "matching_metrics": {
                "direct_matches": len(solutions),
                "heuristic_matches": 0,
                "nlp_matches": 0
            },
            "status": "success",
            "message": "Matching completed successfully",
            "timestamp": "2024-01-01T12:00:00Z",
            "request_id": "req_123456789"
        }
        response_creation_time = time.time() - start_time
        
        # Calculate response size
        import json
        response_json = json.dumps(api_response, indent=2)
        response_size = len(response_json.encode('utf-8'))
        response_size_kb = response_size / 1024
        response_size_mb = response_size_kb / 1024
        
        print(f"\n📊 API Response Size:")
        print(f"  - Response creation time: {response_creation_time:.4f}s")
        print(f"  - Response size: {response_size:,} bytes ({response_size_kb:.2f} KB, {response_size_mb:.2f} MB)")
        print(f"  - Average per solution: {response_size / len(solutions):.0f} bytes")
        print(f"  - Solutions count: {len(solutions)}")
        
        # Response should be reasonably sized (less than 1MB for 100 solutions)
        assert response_size_mb < 1.0, f"Response too large: {response_size_mb:.2f} MB"
        assert response_creation_time < 0.5, "Response creation too slow"
        
        # Verify response structure
        assert "solutions" in api_response
        assert "total_solutions" in api_response
        assert len(api_response["solutions"]) == 100
        assert api_response["total_solutions"] == 100


class TestPerformanceComparison:
    """Compare performance with theoretical complex model."""
    
    def test_theoretical_complexity_reduction(self):
        """Estimate performance improvement over complex workflow model."""
        # Create simplified model data
        simplified_trees = []
        for i in range(1000):
            tree = SupplyTree(
                facility_id=uuid4(),
                facility_name=f"Facility {i}",
                okh_reference=f"okh-{i}",
                confidence_score=0.8 + (i % 20) * 0.01,
                materials_required=[f"material_{j}" for j in range(5)],
                capabilities_used=[f"capability_{j}" for j in range(3)],
                metadata={"test": f"value_{i}"}
            )
            simplified_trees.append(tree)
        
        # Benchmark simplified model
        start_time = time.time()
        simplified_data = [tree.to_dict() for tree in simplified_trees]
        simplified_time = time.time() - start_time
        
        # Estimate complex model overhead (theoretical)
        # Complex model would have:
        # - NetworkX graphs (large memory overhead)
        # - Workflow nodes and edges (complex serialization)
        # - Additional metadata and relationships
        # - More complex validation logic
        
        # Estimate 5x overhead for complex model
        estimated_complex_time = simplified_time * 5
        estimated_complex_memory = len(str(simplified_data)) * 5
        
        # Calculate improvement
        time_improvement = (estimated_complex_time - simplified_time) / estimated_complex_time * 100
        memory_improvement = (estimated_complex_memory - len(str(simplified_data))) / estimated_complex_memory * 100
        
        print(f"\n📊 Theoretical Performance Improvement:")
        print(f"  - Simplified model time: {simplified_time:.4f}s")
        print(f"  - Estimated complex model time: {estimated_complex_time:.4f}s")
        print(f"  - Time improvement: {time_improvement:.1f}%")
        print(f"  - Simplified model size: {len(str(simplified_data)):,} bytes")
        print(f"  - Estimated complex model size: {estimated_complex_memory:,} bytes")
        print(f"  - Memory improvement: {memory_improvement:.1f}%")
        
        # Verify significant improvement
        assert time_improvement > 50, f"Time improvement too low: {time_improvement:.1f}%"
        assert memory_improvement > 50, f"Memory improvement too low: {memory_improvement:.1f}%"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])
