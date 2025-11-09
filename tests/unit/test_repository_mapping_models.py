"""
Unit tests for RepositoryRoutingTable and RepositoryAssessment data models.

Tests the data models for repository mapping and routing.
Following TDD approach: write tests first, then implement.
"""

import pytest
from src.core.generation.models import (
    RepositoryRoutingTable,
    RepositoryAssessment,
    FileInfo
)
from src.core.generation.utils.file_categorization import FileCategorizationResult
from src.core.models.okh import DocumentationType


class TestRepositoryAssessment:
    """Test the RepositoryAssessment data model."""
    
    def test_assessment_exists(self):
        """Test that RepositoryAssessment class exists."""
        assert RepositoryAssessment is not None
    
    def test_assessment_initialization(self):
        """Test that RepositoryAssessment can be initialized."""
        assessment = RepositoryAssessment(
            total_files=100,
            total_directories=10,
            file_types={},
            directory_tree={}
        )
        assert assessment is not None
        assert assessment.total_files == 100
        assert assessment.total_directories == 10
    
    def test_assessment_defaults(self):
        """Test that RepositoryAssessment has proper defaults."""
        assessment = RepositoryAssessment()
        assert assessment.total_files == 0
        assert assessment.total_directories == 0
        assert assessment.file_types == {}
        assert assessment.directory_tree == {}
    
    def test_assessment_file_types(self):
        """Test that RepositoryAssessment tracks file types."""
        assessment = RepositoryAssessment(
            total_files=50,
            total_directories=5,
            file_types={
                "markdown": 20,
                "python": 15,
                "text": 10,
                "other": 5
            },
            directory_tree={}
        )
        assert assessment.file_types["markdown"] == 20
        assert assessment.file_types["python"] == 15
    
    def test_assessment_directory_tree(self):
        """Test that RepositoryAssessment tracks directory tree."""
        assessment = RepositoryAssessment(
            total_files=30,
            total_directories=3,
            file_types={},
            directory_tree={
                "docs": ["README.md", "manual.md"],
                "src": ["main.py", "utils.py"],
                "tests": ["test_main.py"]
            }
        )
        assert "docs" in assessment.directory_tree
        assert "README.md" in assessment.directory_tree["docs"]


class TestRepositoryRoutingTable:
    """Test the RepositoryRoutingTable data model."""
    
    def test_routing_table_exists(self):
        """Test that RepositoryRoutingTable class exists."""
        assert RepositoryRoutingTable is not None
    
    def test_routing_table_initialization(self):
        """Test that RepositoryRoutingTable can be initialized."""
        routing_table = RepositoryRoutingTable(
            routes={},
            metadata={}
        )
        assert routing_table is not None
    
    def test_routing_table_defaults(self):
        """Test that RepositoryRoutingTable has proper defaults."""
        routing_table = RepositoryRoutingTable()
        assert routing_table.routes == {}
        assert routing_table.metadata == {}
    
    def test_routing_table_add_route(self):
        """Test adding a route to the routing table."""
        routing_table = RepositoryRoutingTable()
        
        routing_table.add_route(
            source_path="docs/manual.md",
            destination_type=DocumentationType.MAKING_INSTRUCTIONS,
            destination_path="making-instructions/manual.md",
            confidence=0.8
        )
        
        assert "docs/manual.md" in routing_table.routes
        route = routing_table.routes["docs/manual.md"]
        assert route.destination_type == DocumentationType.MAKING_INSTRUCTIONS
        assert route.destination_path == "making-instructions/manual.md"
        assert route.confidence == 0.8
    
    def test_routing_table_get_route(self):
        """Test getting a route from the routing table."""
        routing_table = RepositoryRoutingTable()
        routing_table.add_route(
            source_path="docs/manual.md",
            destination_type=DocumentationType.MAKING_INSTRUCTIONS,
            destination_path="making-instructions/manual.md",
            confidence=0.8
        )
        
        route = routing_table.get_route("docs/manual.md")
        assert route is not None
        assert route.destination_type == DocumentationType.MAKING_INSTRUCTIONS
    
    def test_routing_table_get_route_not_found(self):
        """Test getting a route that doesn't exist."""
        routing_table = RepositoryRoutingTable()
        
        route = routing_table.get_route("nonexistent.md")
        assert route is None
    
    def test_routing_table_update_route(self):
        """Test updating an existing route."""
        routing_table = RepositoryRoutingTable()
        routing_table.add_route(
            source_path="docs/manual.md",
            destination_type=DocumentationType.MAKING_INSTRUCTIONS,
            destination_path="making-instructions/manual.md",
            confidence=0.8
        )
        
        # Update with higher confidence
        routing_table.add_route(
            source_path="docs/manual.md",
            destination_type=DocumentationType.MAKING_INSTRUCTIONS,
            destination_path="making-instructions/manual.md",
            confidence=0.9
        )
        
        route = routing_table.get_route("docs/manual.md")
        assert route.confidence == 0.9
    
    def test_routing_table_metadata(self):
        """Test that routing table can store metadata."""
        routing_table = RepositoryRoutingTable(
            routes={},
            metadata={
                "created_at": "2025-01-01",
                "last_updated": "2025-01-02",
                "version": "1.0"
            }
        )
        
        assert routing_table.metadata["created_at"] == "2025-01-01"
        assert routing_table.metadata["version"] == "1.0"
    
    def test_routing_table_get_routes_by_type(self):
        """Test getting all routes for a specific documentation type."""
        routing_table = RepositoryRoutingTable()
        routing_table.add_route(
            source_path="docs/manual.md",
            destination_type=DocumentationType.MAKING_INSTRUCTIONS,
            destination_path="making-instructions/manual.md",
            confidence=0.8
        )
        routing_table.add_route(
            source_path="docs/assembly.md",
            destination_type=DocumentationType.MAKING_INSTRUCTIONS,
            destination_path="making-instructions/assembly.md",
            confidence=0.9
        )
        routing_table.add_route(
            source_path="design/part.scad",
            destination_type=DocumentationType.DESIGN_FILES,
            destination_path="design-files/part.scad",
            confidence=0.95
        )
        
        making_routes = routing_table.get_routes_by_type(DocumentationType.MAKING_INSTRUCTIONS)
        assert len(making_routes) == 2
        assert all(route.destination_type == DocumentationType.MAKING_INSTRUCTIONS 
                  for route in making_routes.values())

